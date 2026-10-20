"""Keep the heavy production files on Google Drive instead of the cloud container.

Everything big (footage library, narration audio, renders, thumbnails, media) is pushed to one Drive folder,
"axiom-science-channel", after each video and deleted locally; a later render pulls back only what it needs.

Credentials live in config/.env (gitignored) or in environment variables of the same name, never in the repo:
  YT_CLIENT_ID, YT_CLIENT_SECRET   the same OAuth client as the YouTube uploader
                                   (the Google Drive API must be enabled in its Cloud project)
  DRIVE_REFRESH_TOKEN              scope drive.file: the app only sees files it created itself

  python drive_sync.py auth-url                         # sign in with the Google account whose Drive holds the files
  python drive_sync.py exchange "<redirect URL or code>"
  python drive_sync.py quota                            # account, used / total storage
  python drive_sync.py ls <remote/path>
  python drive_sync.py push <local_dir> <remote/path> [--pack thumbs,shot_thumbs] [--exclude clips] [--delete]
                                [--names names.json]
  python drive_sync.py pull <remote/path> <local_dir> [--only a.mp4,b.mp4 | --only-list names.txt] [--exclude clips]
  python drive_sync.py put <local_file> <remote/dir> [--as "Name on Drive.mp4"]
  python drive_sync.py copy <remote/file> <remote/dir> --as "New name"     # server-side copy, nothing downloaded
  python drive_sync.py rename <remote/path> <new name>
  python drive_sync.py rename-map <remote/dir> <names.json>   # {"<id>.mp4": "<new Drive name>"}, renames in place

push uploads every file under local_dir that is not already on Drive with the same size. Sub-directories named in
--pack go up as one "<name>.pack.tar" each (thousands of small thumbnails would take one API call per file).
--delete removes each local file after Drive reports the same MD5 as the local copy.
--names maps local paths (relative to local_dir) to descriptive Drive names, e.g. footage clips get
"<category>__<title>__<clip>.mp4" (scripts/footage/catalog.py writes that map). pull reverses it: any
"...__<id>.mp4" on Drive is saved locally as "<id>.mp4", so the pipeline keeps its short clip ids.
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
                last = ""
                for attempt in range(7):
                    try:
                        r = requests.put(url, data=data, timeout=600, headers={**self.h(), "Content-Range": rng})
                        if r.status_code in (200, 201, 308):
                            break
                        last = f"{r.status_code} {r.text[:200]}"
                        if r.status_code == 404:  # upload session expired: start this file again
                            return self.upload(local, name, parent)
                    except requests.RequestException as ex:
                        last = repr(ex)[:200]
                    time.sleep(2 ** attempt)
                else:
                    raise SystemExit(f"upload failed: {local}: {last}")
                md5.update(data)
                pos += len(data)
                if r.status_code in (200, 201):
                    meta = r.json()
                    if meta.get("md5Checksum") != md5.hexdigest():
                        raise SystemExit(f"checksum mismatch after upload: {local}")
                    return meta
                if not data:
                    raise SystemExit(f"upload did not finish: {local}")

    def download(self, fid, local, md5=None):
        os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
        for attempt in range(4):
            m = hashlib.md5()
            with requests.get(f"{API}/files/{fid}?alt=media", headers=self.h(), stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(local + ".part", "wb") as f:
                    for b in r.iter_content(8 * 1024 * 1024):
                        f.write(b)
                        m.update(b)
            if md5 is None or m.hexdigest() == md5:
                os.replace(local + ".part", local)
                return
            time.sleep(2 ** attempt)
        raise SystemExit(f"checksum mismatch after download: {local}")


def md5sum(path):
    m = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            m.update(b)
    return m.hexdigest()


def local_name(name):
    """Drive name -> local name: descriptive clip names "<category>__<title>__<id>.mp4" become "<id>.mp4"."""
    return name.rsplit("__", 1)[1] if name.endswith(".mp4") and "__" in name else name


def push(d, a):
    names = json.load(open(a.names)) if a.names else {}
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
            jobs.append((os.path.join(cur, fn), rel, names.get(os.path.join(rel, fn), fn), None))
    listing = {}

    def one(job):
        local, rel, name, packed_dir = job
        remote = f"{a.remote}/{rel}".strip("/")
        parent = d.folder(remote)
        if remote not in listing:
            listing[remote] = d.children(parent)
        have = listing[remote].get(name)
        if have is None:  # uploaded earlier under another name (e.g. before it got a descriptive one): rename it
            old = next((f for n, f in listing[remote].items() if n != name and local_name(n) == os.path.basename(local)), None)
            if old:
                d.call("PATCH", f"{API}/files/{old['id']}?fields=id,name,size,md5Checksum", json={"name": name})
                have = old
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
            lname = local_name(name)
            if top and ((only and lname not in only and lname.replace(".pack.tar", "") not in only) or lname in exclude):
                continue
            if f["mimeType"] == FOLDER:
                walk(f["id"], os.path.join(rel, name), False)
            else:
                dst = os.path.join(a.local, rel, lname)
                if not (os.path.exists(dst) and os.path.getsize(dst) == int(f.get("size", -1))):
                    jobs.append((f["id"], dst, f.get("md5Checksum")))
    walk(d.folder(a.remote, create=False), "", True)
    with cf.ThreadPoolExecutor(4) as ex:
        for k, _ in enumerate(ex.map(lambda j: d.download(*j), jobs), 1):
            if k % 25 == 0 or k == len(jobs):
                print(f"  pulled {k}/{len(jobs)}", flush=True)
    for cur, _, files in os.walk(a.local):
        for fn in files:
            if fn.endswith(".pack.tar"):
                with tarfile.open(os.path.join(cur, fn)) as t:
                    t.extractall(cur, filter="data")
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
    ps.add_argument("--names", default="", help="json {local relative path: name on Drive}")
    pt = sub.add_parser("put")
    pt.add_argument("local")
    pt.add_argument("remote")
    pt.add_argument("--as", dest="name", default="")
    cp = sub.add_parser("copy")
    cp.add_argument("remote")
    cp.add_argument("dest")
    cp.add_argument("--as", dest="name", required=True)
    rm_ = sub.add_parser("rename-map")
    rm_.add_argument("remote")
    rm_.add_argument("names")
    rn = sub.add_parser("rename")
    rn.add_argument("remote")
    rn.add_argument("name")
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
    elif a.cmd == "put":
        parent = d.folder(a.remote)
        name = a.name or os.path.basename(a.local)
        old = d.children(parent).get(name)
        if old and int(old.get("size", -1)) == os.path.getsize(a.local) and old.get("md5Checksum") == md5sum(a.local):
            print(f"already on Drive: {a.remote}/{name}")
        else:
            d.upload(a.local, name, parent)
            print(f"uploaded {a.remote}/{name}")
    elif a.cmd == "rename-map":
        names, n = json.load(open(a.names)), 0
        for name, f in d.children(d.folder(a.remote, create=False)).items():
            want = names.get(local_name(name))
            if want and want != name:
                d.call("PATCH", f"{API}/files/{f['id']}", json={"name": want})
                n += 1
        print(f"renamed {n} files in {a.remote}")
    elif a.cmd in ("copy", "rename"):
        head, _, tail = a.remote.rstrip("/").rpartition("/")
        f = d.children(d.folder(head, create=False)).get(tail)
        if not f:
            raise SystemExit(f"not on Drive: {a.remote}")
        if a.cmd == "rename":
            d.call("PATCH", f"{API}/files/{f['id']}", json={"name": a.name})
            d.ids = {}
            print(f"renamed {a.remote} -> {a.name}")
        else:
            dest = d.folder(a.dest)
            if a.name in d.children(dest):
                print(f"already on Drive: {a.dest}/{a.name}")
            else:
                d.call("POST", f"{API}/files/{f['id']}/copy", json={"name": a.name, "parents": [dest]})
                print(f"copied {a.remote} -> {a.dest}/{a.name}")
    else:
        pull(d, a)


if __name__ == "__main__":
    main()
