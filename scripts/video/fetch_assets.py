"""Download free-licence stills for a production and record credits.

  python fetch_assets.py <assets.json> <out_dir>

assets.json: {"key": {"src": "nasa"|"wiki", "q": "search query", "must": ["word", ...]}, ...}
- nasa: images-api.nasa.gov (generally public domain); picks the first hit whose title contains
  every "must" word, downloads ~large/~orig jpg.
- wiki: Wikimedia Commons; only CC0 / Public domain / CC BY / CC BY-SA files are accepted.
Writes <out_dir>/<key>.jpg and <out_dir>/credits.json. Existing files are skipped.
"""
import json, os, re, sys
import requests

UA = {"User-Agent": "axiom-doc-pipeline/1.0 (educational documentary)"}
OK_LICENSE = re.compile(r"(cc0|public domain|pd|cc by(-sa)? ?\d)", re.I)


def nasa(q, must):
    r = requests.get("https://images-api.nasa.gov/search", params={"q": q, "media_type": "image"}, headers=UA, timeout=60)
    for it in r.json()["collection"]["items"][:40]:
        d = it["data"][0]
        title = d.get("title", "")
        if all(m.lower() in (title + " " + d.get("description", "")[:200]).lower() for m in must):
            files = requests.get(it["href"], headers=UA, timeout=60).json()
            pick = next((f for pref in ("~large.jpg", "~orig.jpg", "~medium.jpg") for f in files if f.endswith(pref)), None)
            if pick:
                credit = d.get("secondary_creator") or d.get("photographer") or d.get("center") or "NASA"
                return pick.replace("http://", "https://"), f"{title} (NASA image library, {credit}, {d.get('nasa_id')})"
    return None, None


def wiki(q, must):
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=60, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 30,
        "gsrsearch": f"{q} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 2400})
    pages = sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for p in pages:
        ii = p["imageinfo"][0]
        md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        if ii.get("width", 0) < 1200 or not OK_LICENSE.search(lic):
            continue
        if not all(m.lower() in p["title"].lower() for m in must):
            continue
        artist = re.sub("<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()
        return ii.get("thumburl") or ii["url"], f"{p['title'][5:]} by {artist or 'unknown'}, {lic} (Wikimedia Commons)"
    return None, None


def main():
    spec, out = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cpath = os.path.join(out, "credits.json")
    credits = json.load(open(cpath)) if os.path.exists(cpath) else {}
    for key, s in spec.items():
        dst = os.path.join(out, f"{key}.jpg")
        if os.path.exists(dst):
            continue
        try:
            url, credit = (nasa if s["src"] == "nasa" else wiki)(s["q"], s.get("must", []))
        except Exception as e:  # rate limits / bad JSON: skip this asset, keep going
            url, credit = None, None
            print(f"ERR  {key}: {e}")
        if not url:
            print(f"MISS {key}: {s['q']}")
            continue
        data = requests.get(url, headers=UA, timeout=180).content
        open(dst, "wb").write(data)
        credits[key] = credit
        print(f"ok   {key}: {credit[:110]}")
        json.dump(credits, open(cpath, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
