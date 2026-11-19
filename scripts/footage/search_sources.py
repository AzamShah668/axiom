"""Find 4K space footage for a topic: ESO, ESA/Hubble, ESA/Webb (djangoplicity archives) and NASA SVS.

  python search_sources.py <terms.txt | "term1,term2"> <out candidates.json> [--pages 3] [--svs-limit 40]

Every candidate gets a verified 4K (>= 3840 px wide) download URL or is dropped:
  - ESO / ESA/Hubble / ESA/Webb: the archive's "ultra_hd" file must exist (HEAD 200)
  - NASA SVS: the page must list an mp4 movie at >= 3840 px width
Output (merged with an existing file): {key: {source, id, title, desc, page, url, bytes, terms}}
Licences: ESO, ESA/Hubble, ESA/Webb = CC BY 4.0 (credit the archive); NASA SVS = public domain, credit NASA.
"""
import argparse, html, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

UA = {"User-Agent": "Mozilla/5.0 (footage research; educational documentary)"}
DJANGO = {
    "eso": ("https://www.eso.org/public/videos/list/{p}/?search={q}", "https://www.eso.org/public/videos/{id}/", "https://cdn.eso.org/videos/ultra_hd/{id}.mp4"),
    "esahubble": ("https://esahubble.org/videos/page/{p}/?search={q}", "https://esahubble.org/videos/{id}/", "https://cdn.esahubble.org/archives/videos/ultra_hd/{id}.mp4"),
    "esawebb": ("https://esawebb.org/videos/page/{p}/?search={q}", "https://esawebb.org/videos/{id}/", "https://cdn.esawebb.org/archives/videos/ultra_hd/{id}.mp4"),
}
THUMB = {"eso": "https://cdn.eso.org/videos/videoframe/{id}.jpg",
         "esahubble": "https://cdn.esahubble.org/archives/videos/videoframe/{id}.jpg",
         "esawebb": "https://cdn.esawebb.org/archives/videos/videoframe/{id}.jpg"}
SKIP_ID = re.compile(r"(-FD|fulldome|dome|_vr|360|-vr)", re.I)  # fulldome / VR renders are not 16:9


def get(url, **kw):
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=30, **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    return None


def django_search(src, term, pages):
    tpl = DJANGO[src][0]
    out = {}
    for p in range(1, pages + 1):
        r = get(tpl.format(p=p, q=requests.utils.quote(term)))
        if r is None:
            break
        found = re.findall(r'data-title="([^"]*)" data-url="/(?:public/)?videos/([^"/]+)/"', r.text)
        if not found:  # ESA/Webb template: YouTube modal title followed by the video link
            found = re.findall(r'title="([^"]+)"\s+allow="accelerometer[^>]*></iframe>.*?href="/videos/([^"/]+)/"', r.text, re.S)
        for title, vid in found:
            if not SKIP_ID.search(vid):
                out[vid] = html.unescape(title)
        if len(found) < 20:  # last page (asking for the next one only costs a slow 404)
            break
    return out


def head_ok(url):
    for i in range(3):
        try:
            r = requests.head(url, headers=UA, timeout=20, allow_redirects=True)
            if r.status_code == 200:
                return int(r.headers.get("content-length", 0))
            if r.status_code in (403, 404):
                return 0
        except requests.RequestException:
            time.sleep(1 + i)
    return 0


def svs_search(term, limit):
    r = get(f"https://svs.gsfc.nasa.gov/api/search/?search={requests.utils.quote(term)}&limit={limit}")
    return [(x["id"], x["title"]) for x in (r.json()["results"] if r else [])]


def svs_4k(sid):
    r = get(f"https://svs.gsfc.nasa.gov/api/{sid}")
    if r is None:
        return None
    d = r.json()
    best = None
    for g in d.get("media_groups", []):
        for it in g.get("items", []):
            m = it.get("instance") or it
            fn = (m.get("filename") or "").lower()
            if m.get("media_type") != "Movie" or not fn.endswith(".mp4") or (m.get("width") or 0) < 3840:
                continue
            if any(k in fn for k in ("text", "caption", "print", "_sbs", "360", "dome", "vr")):
                continue
            size = m.get("file_size") or m.get("filesize") or 0
            if best is None or (size and size < best[1]):
                best = (m["url"].replace("http://", "https://"), size)
    if best is None:
        return None
    desc = re.sub(r"\s*\|\|.*", "", d.get("description") or "", flags=re.S)
    thumb = ((d.get("main_image") or {}).get("url") or "").replace("http://", "https://")
    return {"url": best[0], "bytes": best[1], "desc": desc[:400], "thumb": thumb,
            "kw": [k.get("title", "") if isinstance(k, dict) else str(k) for k in d.get("keywords", [])][:12]}


def env_key(name):
    """An API key from the environment or the git-ignored config/.env (never printed)."""
    k = os.environ.get(name)
    env = os.path.join(os.path.dirname(__file__), "..", "..", "config", ".env")
    if not k and os.path.exists(env):
        for ln in open(env):
            if ln.startswith(name + "="):
                k = ln.split("=", 1)[1].strip()
    return k


def pexels_key():
    return env_key("PEXELS_API_KEY")


def pixabay_search(term, limit=20):
    """Pixabay stock video (owner, 2026-11-19: more variety for what the voice names: places, objects, people at work).
    Only landscape files at least 3840 px wide; Pixabay Content License (free, no attribution required; credited
    anyway). The key goes in the query string, so it lives in config/.env as PIXABAY_API_KEY."""
    k = env_key("PIXABAY_API_KEY")
    if not k:
        return {}
    try:
        r = requests.get("https://pixabay.com/api/videos/", timeout=30,
                         params={"key": k, "q": term[:100], "per_page": max(3, min(limit, 200)), "safesearch": "true"})
        hits = r.json().get("hits", []) if r.ok else []
    except Exception:
        return {}
    out = {}
    for v in hits:
        f = (v.get("videos") or {}).get("large") or {}
        if (f.get("width") or 0) < 3840 or (f.get("height") or 0) >= (f.get("width") or 0) or not f.get("url"):
            continue
        out[str(v["id"])] = {"title": (v.get("tags") or term).replace(",", ""), "url": f["url"], "page": v.get("pageURL", ""),
                             "thumb": f.get("thumbnail", ""), "desc": f"by {v.get('user', '')}", "bytes": f.get("size", 0)}
    return out


def pexels_search(term, limit=15):
    """Pexels stock video (owner, 2026-11-09: an extra source, used where the space archives have nothing).
    Only landscape files at least 3840 px wide; Pexels License (free, no attribution required; credited anyway)."""
    k = pexels_key()
    if not k:
        return {}
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": k}, timeout=30,
                         params={"query": term, "per_page": limit, "orientation": "landscape", "size": "large"})
        vids = r.json().get("videos", []) if r.ok else []
    except Exception:
        return {}
    out = {}
    for v in vids:
        files = [f for f in v.get("video_files", []) if (f.get("width") or 0) >= 3840 and (f.get("height") or 0) < (f.get("width") or 0)]
        if not files:
            continue
        f = min(files, key=lambda f: f["width"])
        slug = re.sub(r"-\d+/?$", "", (v.get("url") or "").rstrip("/").rsplit("/", 1)[-1]).replace("-", " ")
        out[str(v["id"])] = {"title": slug or term, "url": f["link"], "page": v.get("url", ""), "thumb": v.get("image", ""),
                             "desc": f"by {(v.get('user') or {}).get('name', '')}", "bytes": 0}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("terms")
    ap.add_argument("out")
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--svs-limit", type=int, default=40)
    ap.add_argument("--sources", default="eso,esahubble,esawebb,svs")
    a = ap.parse_args()
    terms = [t.strip() for t in (open(a.terms).read().splitlines() if os.path.exists(a.terms) else a.terms.split(",")) if t.strip()]
    cand = json.load(open(a.out)) if os.path.exists(a.out) else {}
    found = {}
    global PEX
    PEX = {}

    def one(job):
        term, src = job
        if src == "svs":
            return term, src, {str(i): t for i, t in svs_search(term, a.svs_limit)}
        if src in ("pexels", "pixabay"):
            hits = (pexels_search if src == "pexels" else pixabay_search)(term)
            PEX.update({f"{src}:{i}": h for i, h in hits.items()})
            return term, src, {i: h["title"] for i, h in hits.items()}
        return term, src, django_search(src, term, a.pages)

    jobs = [(t, s) for t in terms for s in a.sources.split(",")]
    with ThreadPoolExecutor(12) as ex:
        for n, (term, src, hits) in enumerate(ex.map(one, jobs)):
            for vid, title in hits.items():
                found.setdefault(f"{src}:{vid}", {"source": src, "id": vid, "title": title, "terms": []})["terms"].append(term)
            if src == jobs[-1][1]:
                print(f"{term:32s} total candidates {len(found)}", flush=True)
    todo = [k for k in found if k not in cand]

    def resolve(k):
        c = found[k]
        if c["source"] in ("pexels", "pixabay"):
            h = PEX.get(f"{c['source']}:{c['id']}")
            if not h:
                return k, None
            c.update(url=h["url"], bytes=h["bytes"], desc=h["desc"], page=h["page"], thumb=h["thumb"])
            return k, c
        if c["source"] == "svs":
            info = svs_4k(c["id"])
            if not info:
                return k, None
            c.update(url=info["url"], bytes=info["bytes"], desc=info["desc"], kw=info["kw"], thumb=info["thumb"],
                     page=f"https://svs.gsfc.nasa.gov/{c['id']}/")
            return k, c
        _, page, cdn = DJANGO[c["source"]]
        url = cdn.format(id=c["id"])
        size = head_ok(url)
        if not size:
            return k, None
        c.update(url=url, bytes=size, page=page.format(id=c["id"]), thumb=THUMB[c["source"]].format(id=c["id"]))
        return k, c

    with ThreadPoolExecutor(8) as ex:
        for k, c in ex.map(resolve, todo):
            if c:
                cand[k] = c
    for k, c in found.items():  # remember which terms hit already-known candidates
        if k in cand:
            cand[k]["terms"] = sorted(set(cand[k].get("terms", [])) | set(c["terms"]))
    json.dump(cand, open(a.out, "w"), indent=1, ensure_ascii=False)
    by = {}
    for c in cand.values():
        by[c["source"]] = by.get(c["source"], 0) + 1
    print(f"4K candidates: {len(cand)} {by}")


if __name__ == "__main__":
    sys.exit(main())
