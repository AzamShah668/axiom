"""Upload a finished science-channel video to YouTube (YouTube Data API v3, resumable upload).

Credentials live in config/.env (gitignored), never in the repo:
  YT_CLIENT_ID, YT_CLIENT_SECRET   OAuth client of type "Desktop app" (the client_secret_*.json values)
  YT_REFRESH_TOKEN                 refresh token for the channel's Google account

  python upload_youtube.py auth-url                         # print the consent link (sign in with the CHANNEL's account)
  python upload_youtube.py exchange "<code or full redirect URL>"   # store YT_REFRESH_TOKEN in config/.env
  python upload_youtube.py whoami                           # which channel the token belongs to
  python upload_youtube.py upload <video.mp4> <youtube.md> [--thumbnail t.jpg] [--comment credits_full.txt]
                                  [--privacy public|unlisted|private] [--publish-at 2026-10-16T12:00:00Z]

youtube.md is the production's package file: **Title** line, **Description** ``` block, **Tags** line.
Note: projects that have not passed YouTube's API audit get uploads locked to private; custom thumbnails need
a verified channel. The pinned comment is posted but YouTube's API cannot pin it - pin it in YouTube Studio.
"""
import argparse, json, os, re, sys, time, urllib.parse
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV = os.path.join(ROOT, "config", ".env")
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"
REDIRECT = "http://localhost"


def env():
    vals = {}
    if os.path.exists(ENV):
        for ln in open(ENV):
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                vals[k.strip()] = v.strip().strip('"')
    vals.update({k: v for k, v in os.environ.items() if k.startswith("YT_")})
    return vals


def save_env(key, value):
    lines = open(ENV).read().splitlines() if os.path.exists(ENV) else []
    lines = [ln for ln in lines if not ln.startswith(key + "=")] + [f"{key}={value}"]
    os.makedirs(os.path.dirname(ENV), exist_ok=True)
    open(ENV, "w").write("\n".join(lines) + "\n")


def access_token(e):
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": e["YT_CLIENT_ID"], "client_secret": e["YT_CLIENT_SECRET"],
        "refresh_token": e["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"token refresh failed: {r.status_code} {r.text[:300]}")
    return r.json()["access_token"]


def parse_package(path):
    s = open(path, encoding="utf-8").read()
    title = re.search(r"\*\*Title\*\*\s*\n(.+)", s).group(1).strip()
    desc = re.search(r"\*\*Description\*\*\s*\n```\n(.*?)\n```", s, re.S).group(1).strip()
    tags = [t.strip() for t in re.search(r"\*\*Tags\*\*\s*\n(.+)", s).group(1).split(",") if t.strip()]
    if len(title) > 100:
        raise SystemExit(f"title is {len(title)} chars (YouTube max 100)")
    if len(desc.encode()) > 5000 or "<" in desc or ">" in desc:
        raise SystemExit("description must be < 5000 bytes and contain no < or >")
    while len(",".join(tags)) > 480:
        tags.pop()
    return title, desc, tags


def upload(a, e):
    title, desc, tags = parse_package(a.package)
    tok = access_token(e)
    status = {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False, "embeddable": True}
    if a.publish_at:
        status.update(privacyStatus="private", publishAt=a.publish_at)
    meta = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "28",
                        "defaultLanguage": "en", "defaultAudioLanguage": "hi"}, "status": status}
    size = os.path.getsize(a.video)
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      data=json.dumps(meta), timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"upload init failed: {r.status_code} {r.text[:500]}")
    url, pos, chunk = r.headers["Location"], 0, 16 * 1024 * 1024
    with open(a.video, "rb") as f:
        while pos < size:
            f.seek(pos)
            data = f.read(chunk)
            for attempt in range(6):
                try:
                    r = requests.put(url, data=data, timeout=300, headers={
                        "Authorization": f"Bearer {tok}", "Content-Length": str(len(data)),
                        "Content-Range": f"bytes {pos}-{pos + len(data) - 1}/{size}"})
                    break
                except requests.RequestException:
                    time.sleep(2 ** attempt)
            else:
                raise SystemExit("upload failed after retries")
            if r.status_code in (200, 201):
                pos = size
            elif r.status_code == 308:
                rng = r.headers.get("Range")
                pos = int(rng.split("-")[1]) + 1 if rng else 0
            elif r.status_code == 401:
                tok = access_token(e)
            else:
                raise SystemExit(f"upload error {r.status_code}: {r.text[:500]}")
            print(f"  uploaded {pos * 100 // size}%", flush=True)
    video = r.json()
    vid = video["id"]
    print(f"video: https://youtu.be/{vid}  status: {video['status'].get('privacyStatus')} "
          f"upload: {video['status'].get('uploadStatus')}")
    if a.thumbnail:
        t = requests.post(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}",
                          headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/jpeg"},
                          data=open(a.thumbnail, "rb").read(), timeout=120)
        print("thumbnail:", "set" if t.status_code == 200 else f"not set ({t.status_code}: {t.text[:200]})")
    if a.comment:
        text = open(a.comment, encoding="utf-8").read().strip()
        c = requests.post("https://www.googleapis.com/youtube/v3/commentThreads?part=snippet",
                          headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                          data=json.dumps({"snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": text}}}}),
                          timeout=60)
        print("credits comment:", "posted (pin it in YouTube Studio)" if c.status_code == 200 else
              f"not posted ({c.status_code}: {c.text[:200]})")
    return vid


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth-url")
    ex = sub.add_parser("exchange")
    ex.add_argument("code")
    sub.add_parser("whoami")
    up = sub.add_parser("upload")
    up.add_argument("video")
    up.add_argument("package")
    up.add_argument("--thumbnail", default="")
    up.add_argument("--comment", default="")
    up.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    up.add_argument("--publish-at", default="")
    a = ap.parse_args()
    e = env()
    if a.cmd == "auth-url":
        print("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": e["YT_CLIENT_ID"], "redirect_uri": REDIRECT, "response_type": "code",
            "scope": SCOPES, "access_type": "offline", "prompt": "consent"}))
    elif a.cmd == "exchange":
        code = a.code
        if code.startswith("http"):
            code = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)["code"][0]
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "code": code, "client_id": e["YT_CLIENT_ID"], "client_secret": e["YT_CLIENT_SECRET"],
            "redirect_uri": REDIRECT, "grant_type": "authorization_code"}, timeout=30)
        if r.status_code != 200 or "refresh_token" not in r.json():
            raise SystemExit(f"exchange failed: {r.status_code} {r.text[:300]}")
        save_env("YT_REFRESH_TOKEN", r.json()["refresh_token"])
        print("refresh token saved to config/.env")
    elif a.cmd == "whoami":
        tok = access_token(e)
        r = requests.get("https://www.googleapis.com/youtube/v3/channels?part=snippet,status&mine=true",
                         headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        for ch in r.json().get("items", []):
            print(ch["id"], ch["snippet"]["title"], ch.get("status", {}).get("longUploadsStatus"))
    else:
        upload(a, e)


if __name__ == "__main__":
    sys.exit(main())
