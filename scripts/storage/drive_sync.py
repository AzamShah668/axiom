"""Keep the heavy production files on Google Drive instead of the cloud container.

Everything big (footage library, narration audio, renders, thumbnails, media) is pushed to one Drive folder,
"axiom-science-channel", after each video and deleted locally; a later render pulls back only what it needs.

Credentials live in config/.env (gitignored), never in the repo:
  YT_CLIENT_ID, YT_CLIENT_SECRET   the same OAuth client as the YouTube uploader
                                   (the Google Drive API must be enabled in its Cloud project)
  DRIVE_REFRESH_TOKEN              scope drive.file: the app only sees files it created itself

  python drive_sync.py auth-url                         # sign in with the Google account whose Drive holds the files
  python drive_sync.py exchange "<redirect URL or code>"
  python drive_sync.py quota                            # account, used / total storage
  python drive_sync.py ls <remote/path>
  python drive_sync.py push <local_dir> <remote/path> [--pack thumbs,shot_thumbs] [--exclude clips] [--delete]
  python drive_sync.py pull <remote/path> <local_dir> [--only a.mp4,b.mp4 | --only-list names.txt] [--exclude clips]

push uploads every file under local_dir that is not already on Drive with the same size. Sub-directories named in
--pack go up as one "<name>.pack.tar" each (thousands of small thumbnails would take one API call per file).
--delete removes each local file after Drive reports the same MD5 as the local copy.
pull downloads into local_dir (unpacking *.pack.tar); --only / --only-list limit it to some top-level names,
e.g. just the clips a cutlist uses.
"""
import argparse, concurrent.futures as cf, hashlib, json, os, shutil, sys, tarfile, time, urllib.parse
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "youtube"))
from upload_youtube import env, save_env  # noqa: E402  (shared config/.env helpers)

SCOPE = "https://www.googleapis.com/auth/drive.file"
REDIRECT = "http://localhost"
TOP = "axiom-science-channel"
API = "https://www.googleapis.com/drive/v3"
UP = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
CHUNK = 32 * 1024 * 1024


class Drive:
    def __init__(self):
        self.e = env()
        self.tok, self.exp = None, 0
        self.ids = {}

    def h(self):
        if time.time() > self.exp - 120:
            r = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": self.e["YT_CLIENT_ID"], "client_secret": self.e["YT_CLIENT_SECRET"],
                "refresh_token": self.e["DRIVE_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
            if r.status_code != 200:
                raise SystemExit(f"token refresh failed: {r.status_code} {r.text[:300]}")
            self.tok, self.exp = r.json()["access_token"], time.time() + r.json().get("expires_in", 3600)
        return {"Authorization": f"Bearer {self.tok}"}

    def call(self, method, url, **kw):
        for attempt in range(6):
            try:
                r = requests.request(method, url, headers={**self.h(), **kw.pop("headers", {})}, timeout=120, **kw)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                raise SystemExit(f"Drive API {r.status_code}: {r.text[:400]}")
            return r
        raise SystemExit(f"Drive API kept failing: {url}")

    def children(self, fid):
        out, page = {}, None
        while True:
            q = {"q": f"'{fid}' in parents and trashed=false", "pageSize": 1000,
                 "fields": "nextPageToken,files(id,name,size,mimeType,md5Checksum)"}
            if page:
                q["pageToken"] = page
            d = self.call("GET", f"{API}/files?" + urllib.parse.urlencode(q)).json()
            out.update({f["name"]: f for f in d["files"]})
            page = d.get("nextPageToken")
            if not page:
                return out

    def folder(self, path, create=True):
        """Folder id for TOP/path ('' = TOP itself)."""
        parts = [TOP] + [p for p in path.strip("/").split("/") if p]
        fid, cur = "root", ""
        for p in parts:
            cur += "/" + p
            if cur not in self.ids:
                q = (f"name='{p}' and mimeType='{FOLDER}' and '{fid}' in parents and trashed=false")
                found = self.call("GET", f"{API}/files?" + urllib.parse.urlencode({"q": q, "fields": "files(id)"})).json()["files"]
                if found:
                    self.ids[cur] = found[0]["id"]
                elif create:
                    self.ids[cur] = self.call("POST", f"{API}/files", json={"name": p, "mimeType": FOLDER, "parents": [fid]}).json()["id"]
                else:
                    raise SystemExit(f"not on Drive: {path}")
            fid = self.ids[cur]
        return fid

    def upload(self, local, name, parent):
        size = os.path.getsize(local)
        r = self.call("POST", f"{UP}?uploadType=resumable&fields=id,size,md5Checksum",
                      json={"name": name, "parents": [parent]},
                      headers={"X-Upload-Content-Type": "application/octet-stream", "X-Upload-Content-Length": str(size)})
        url, pos, md5 = r.headers["Location"], 0, hashlib.md5()
        with open(local, "rb") as f:
            while True:
                data = f.read(CHUNK)
                end = pos + len(data) - 1
                rng = f"bytes {pos}-{end}/{size}" if data else f"bytes */{size}"
                for attempt in range(6):
                    try:
                        r = requests.put(url, data=data, timeout=600, headers={**self.h(), "Content-Range": rng})
                        if r.status_code in (200, 201, 308):
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(2 ** attempt)
                else:
                    raise SystemExit(f"upload failed: {local}")
                md5.update(data)
                pos += len(data)
                if r.status_code in (200, 201):
                    meta = r.json()
                    if meta.get("md5Checksum") != md5.hexdigest():
                        raise SystemExit(f"checksum mismatch after upload: {local}")
                    return meta
                if not data:
                    raise SystemExit(f"upload did not finish: {local}")

    def download(self, fid, local):
        os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
        with requests.get(f"{API}/files/{fid}?alt=media", headers=self.h(), stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(local + ".part", "wb") as f:
                shutil.copyfileobj(r.raw, f, 8 * 1024 * 1024)
        os.replace(local + ".part", local)


def md5sum(path):
    m = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            m.update(b)
    return m.hexdigest()


def push(d, a):
    pack = {p for p in a.pack.split(",") if p}
    exclude = {p for p in a.exclude.split(",") if p}
    jobs, total = [], 0
    for cur, dirs, files in os.walk(a.local):
        rel = os.path.relpath(cur, a.local)
        rel = "" if rel == "." else rel
        for dn in list(dirs):
            if dn in exclude or dn in pack:
                dirs.remove(dn)
            if dn in pack:
                tar = os.path.join(a.local, f".{dn}.pack.tar")
                with tarfile.open(tar, "w") as t:
                    t.add(os.path.join(cur, dn), arcname=dn)
                jobs.append((tar, rel, f"{dn}.pack.tar", os.path.join(cur, dn)))
        for fn in files:
            if fn.endswith(".pack.tar") and fn.startswith("."):
                continue
            jobs.append((os.path.join(cur, fn), rel, fn, None))
    listing = {}

    def one(job):
        local, rel, name, packed_dir = job
        remote = f"{a.remote}/{rel}".strip("/")
        parent = d.folder(remote)
        if remote not in listing:
            listing[remote] = d.children(parent)
        have = listing[remote].get(name)
        size = os.path.getsize(local)
        if have and int(have.get("size", -1)) == size:
            ok = have.get("md5Checksum") == md5sum(local) if a.delete else True
            meta = have if ok else d.upload(local, name, parent)
        else:
            meta = d.upload(local, name, parent)
        if packed_dir:
            os.remove(local)
            if a.delete:
                shutil.rmtree(packed_dir)
        elif a.delete:
            os.remove(local)
        return size, name, meta["id"]

    for remote in sorted({f"{a.remote}/{j[1]}".strip("/") for j in jobs}, key=len):
        listing[remote] = d.children(d.folder(remote))  # create folders up front, in order
    with cf.ThreadPoolExecutor(4) as ex:
        for k, (size, name, _) in enumerate(ex.map(one, jobs), 1):
            total += size
            if k % 25 == 0 or k == len(jobs):
                print(f"  pushed {k}/{len(jobs)} files, {total / 1e9:.2f} GB", flush=True)
    if a.delete:
        for cur, dirs, files in os.walk(a.local, topdown=False):
            if not files and not dirs and cur != a.local:
                os.rmdir(cur)


def pull(d, a):
    only = {x for x in a.only.split(",") if x}
    if a.only_list:
        only |= {ln.strip() for ln in open(a.only_list) if ln.strip()}
    exclude = {p for p in a.exclude.split(",") if p}
    jobs = []

    def walk(fid, rel, top):
        for name, f in d.children(fid).items():
            if top and ((only and name not in only and name.replace(".pack.tar", "") not in only) or name in exclude):
                continue
            if f["mimeType"] == FOLDER:
                walk(f["id"], os.path.join(rel, name), False)
            else:
                dst = os.path.join(a.local, rel, name)
                if not (os.path.exists(dst) and os.path.getsize(dst) == int(f.get("size", -1))):
                    jobs.append((f["id"], dst))
    walk(d.folder(a.remote, create=False), "", True)
    with cf.ThreadPoolExecutor(4) as ex:
        for k, _ in enumerate(ex.map(lambda j: d.download(*j), jobs), 1):
            if k % 25 == 0 or k == len(jobs):
                print(f"  pulled {k}/{len(jobs)}", flush=True)
    for cur, _, files in os.walk(a.local):
        for fn in files:
            if fn.endswith(".pack.tar"):
                with tarfile.open(os.path.join(cur, fn)) as t:
                    t.extractall(cur)
                os.remove(os.path.join(cur, fn))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth-url")
    ex = sub.add_parser("exchange")
    ex.add_argument("code")
    sub.add_parser("quota")
    ls = sub.add_parser("ls")
    ls.add_argument("remote", nargs="?", default="")
    ps = sub.add_parser("push")
    ps.add_argument("local")
    ps.add_argument("remote")
    ps.add_argument("--pack", default="")
    ps.add_argument("--exclude", default="")
    ps.add_argument("--delete", action="store_true")
    pl = sub.add_parser("pull")
    pl.add_argument("remote")
    pl.add_argument("local")
    pl.add_argument("--only", default="")
    pl.add_argument("--only-list", default="")
    pl.add_argument("--exclude", default="")
    a = ap.parse_args()
    e = env()
    if a.cmd == "auth-url":
        print("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": e["YT_CLIENT_ID"], "redirect_uri": REDIRECT, "response_type": "code",
            "scope": SCOPE, "access_type": "offline", "prompt": "consent"}))
        return
    if a.cmd == "exchange":
        code = a.code
        if code.startswith("http"):
            code = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)["code"][0]
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": e["YT_CLIENT_ID"], "client_secret": e["YT_CLIENT_SECRET"],
            "redirect_uri": REDIRECT, "grant_type": "authorization_code"}, timeout=30)
        if r.status_code != 200 or "refresh_token" not in r.json():
            raise SystemExit(f"exchange failed: {r.status_code} {r.text[:300]}")
        save_env("DRIVE_REFRESH_TOKEN", r.json()["refresh_token"])
        print("Drive refresh token saved to config/.env")
        return
    d = Drive()
    if a.cmd == "quota":
        q = d.call("GET", f"{API}/about?fields=user(emailAddress),storageQuota").json()
        s = q["storageQuota"]
        lim = int(s["limit"]) / 1e9 if "limit" in s else float("inf")
        print(f"{q['user']['emailAddress']}: {int(s['usage']) / 1e9:.1f} GB used of {lim:.0f} GB")
    elif a.cmd == "ls":
        for name, f in sorted(d.children(d.folder(a.remote, create=False)).items()):
            print(f"{int(f.get('size', 0)) / 1e6:10.1f} MB  {name}{'/' if f['mimeType'] == FOLDER else ''}")
    elif a.cmd == "push":
        push(d, a)
    else:
        pull(d, a)


if __name__ == "__main__":
    main()
