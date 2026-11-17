"""Download free-licence stills for a production and record credits.

  python fetch_assets.py <assets.json> <out_dir>
  python fetch_assets.py portrait "<name>" [--out dir] [--key Stem] [--alias "other name"] [--dry-run] [--all]

assets.json: {"key": {"src": "nasa"|"wiki", "q": "search query", "must": ["word", ...]}, ...}
          or {"key": {"src": "url", "url": "https://...jpg", "credit": "credit line"}}
          or {"key": {"src": "portrait", "name": "Maarten Schmidt", "alias": ["M. Schmidt"]}}
- nasa: images-api.nasa.gov (generally public domain); picks the first hit whose title contains
  every "must" word, downloads ~large/~orig jpg.
- wiki: Wikimedia Commons; only CC0 / Public domain / CC BY / CC BY-SA files are accepted. It rate-limits the
  container's shared IP (429): never route around it. For people use "portrait" instead.
- url: a fixed file with a known free licence (e.g. ESO / ESA images, CC BY 4.0); give the credit line.
- portrait: a photo of a named person, see below.
Writes <out_dir>/<key>.jpg and <out_dir>/credits.json. Existing files are skipped.

portrait: asks, in this order, the NASA Image Library (public domain), the Library of Congress (only items whose
rights advisory says "No known restrictions"), the ESO image archive (CC BY 4.0, credit line from the image page)
and the Internet Archive (only items whose licence URL is CC BY / CC BY-SA / CC0 / Public Domain Mark), and stops
at the first source with a photo whose title (or keywords / subject, or a "this photograph shows" caption
sentence) names the person. It never requests a Wikimedia, Wikipedia, Flickr or Openverse host (refused in
code, redirects included), keeps each host's crawl delay (loc.gov: 5 s) and stops the run on a 429 from any host.
Writes <out>/<Key>.jpg, the credit line (title, author, licence, source, page) into <out>/credits.json under
<Key>, the full record into <out>/portraits.json and every request into <out>/portrait_requests.log.
--dry-run prints the candidates and the pick without downloading; --all asks every source, not just up to the
first hit. Exit code 2 = stopped on a 429; 1 = nothing found.
"""
import argparse, html, io, json, os, re, sys, time, unicodedata
from urllib.parse import urljoin, urlparse
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


# ---------------------------------------------------------------- portraits of people (no Wikimedia, no Flickr)
BLOCKED = re.compile(r"(^|\.)(wikimedia\.org|wikipedia\.org|wikidata\.org|flickr\.com|staticflickr\.com|flic\.kr|"
                     r"openverse\.org|openverse\.engineering)$", re.I)
ALLOWED = re.compile(r"(^|\.)(nasa\.gov|loc\.gov|eso\.org|archive\.org)$", re.I)
DELAY = {"www.loc.gov": 5.0, "tile.loc.gov": 1.0, "www.eso.org": 2.0, "cdn.eso.org": 1.0,
         "images-api.nasa.gov": 0.5, "images-assets.nasa.gov": 0.5}  # seconds between requests (loc.gov Crawl-Delay: 5)
PHOTO_WORDS = re.compile(r"\b(photograph|photo|pictured|portrait|poses?|posing|speaks|stands)\b|"
                         r"[(,]\s*(far )?(left|right|center|centre)\b")  # "X (left) and Y", "X, right, ..."
QUOTE = re.compile(r"\b(said|says|explained|according to)\b|&quot;|\"|\u201c")  # a quote is not a photo caption
NOT_FREE = re.compile(r"©|\(c\)|copyright|courtesy|all rights reserved|getty|reuters|associated press|\bap photo", re.I)
CC_URL = re.compile(r"creativecommons\.org/(licenses/(by|by-sa)/([\d.]+)|publicdomain/(zero|mark)/([\d.]+))", re.I)
MIN_SIDE = 400  # px on the short side; smaller downloads are dropped


class Halt(Exception):
    """A host answered 429: stop the whole run (never retry around a rate limit)."""


class Net:
    def __init__(self, log_path=None):
        self.s, self.last, self.log_path = requests.Session(), {}, log_path
        self.s.headers.update(UA)

    def get(self, url, params=None, timeout=60):
        for _ in range(6):  # follow redirects by hand so every hop is checked against the host rules
            host = urlparse(url).hostname or ""
            if BLOCKED.search(host) or not ALLOWED.search(host):
                raise ValueError(f"refusing host {host}")
            wait = DELAY.get(host, 1.0) - (time.time() - self.last.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            r = self.s.get(url, params=params, timeout=timeout, allow_redirects=False)
            self.last[host] = time.time()
            line = f"{time.strftime('%H:%M:%S')} GET {r.status_code} {host} {urlparse(r.url).path[:100]}"
            print("    > " + line, file=sys.stderr)
            if self.log_path:
                with open(self.log_path, "a") as f:
                    f.write(line + "\n")
            if r.status_code == 429:
                raise Halt(f"429 from {host}; stopping (do not route around rate limits)")
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                url, params = urljoin(r.url, r.headers["location"]), None
                continue
            return r
        raise ValueError(f"too many redirects: {url}")

    def json(self, url, params=None):
        r = self.get(url, params)
        if r.status_code == 503:  # loc.gov sends 503 when busy: one slow retry, then skip the source
            time.sleep(15)
            r = self.get(url, params)
        r.raise_for_status()
        return r.json()


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().replace("’", "'").split())


def names_in(text, names):
    """True if the text names one of the names: the surname as a word plus the first name or its initial."""
    t = norm(text)
    for n in names:
        toks = norm(n).replace(".", " ").split()
        last = re.escape(toks[-1])
        if not re.search(rf"\b{last}\b", t):
            continue
        if len(toks) == 1 or re.search(rf"\b{re.escape(toks[0])}\b", t) or \
                re.search(rf"\b{re.escape(toks[0][0])}\.?\s+([a-z]\.?\s+)*{last}\b", t):
            return True
    return False


def caption_names(desc, names):
    """True if a sentence of the caption both names the person and says it is a photo of them."""
    t = re.sub(r"\b(dr|prof|mr|mrs|ms|st|jr|sr|vs|[a-z])\.", r"\1", norm(desc)[:1500])  # "Dr." ends no sentence
    for sent in re.split(r"(?<=[.!?])\s+", t):
        if names_in(sent, names) and PHOTO_WORDS.search(sent) and not QUOTE.search(sent):
            return True
    return False


def queries(names):
    """The names as given, then the first name's surname alone (hits still have to pass names_in)."""
    return list(dict.fromkeys(names + [names[0].split()[-1]]))


def solo(title):
    """1 when the person looks like the photo's only subject, else 0 (ranking only)."""
    t = norm(title)
    return 0 if re.search(r"\b(and|with|team|group|crew|members|visit|visiting|ceremony|panel)\b|,", t) else 1


def text(v, sep=" "):
    return v if isinstance(v, str) else sep.join(map(str, v or []))


def src_nasa(net, names):
    out = []
    for q in queries(names):
        d = net.json("https://images-api.nasa.gov/search", {"q": q, "media_type": "image"})
        for it in d["collection"]["items"][:100]:
            x = it["data"][0]
            title, desc, kw = x.get("title", ""), x.get("description", ""), text(x.get("keywords"), " ; ")
            score = 3 if names_in(title, names) or names_in(kw, names) else 2 if caption_names(desc, names) else 0
            if not score:
                continue
            rank = score + solo(title)
            if score < 3 or title == x["nasa_id"] or not names_in(title, names):  # "201007270004HQ", "Space Science"
                title = re.split(r"(?<=[a-z]{3}[.!?])\s", " ".join(desc.split()))[0][:140]  # caption's first sentence
            author = x.get("photographer") or x.get("secondary_creator") or f"NASA/{x.get('center', '')}".rstrip("/")
            free = not NOT_FREE.search(" ".join([desc[:600], author]))
            out.append({"source": "NASA Image and Video Library", "id": x["nasa_id"], "title": title, "author": author,
                        "licence": "Public domain (NASA)" if free else "", "rights": "credit/copyright note in caption",
                        "score": rank, "page": f"https://images.nasa.gov/details/{x['nasa_id']}",
                        "href": it["href"], "date": x.get("date_created", "")[:10]})
    return out


def url_nasa(net, c):
    files = net.json(c["href"])
    pick = next((f for pref in ("~large.jpg", "~orig.jpg", "~medium.jpg", "~large.png", "~orig.png")
                 for f in files if f.endswith(pref)), None)
    return pick.replace("http://", "https://") if pick else None


def src_loc(net, names):
    out = []
    for q in queries(names):
        d = net.json("https://www.loc.gov/photos/", {"q": q, "fo": "json", "c": 50})
        for r in d.get("results") or d.get("content", {}).get("results") or []:
            it, title = r.get("item") or {}, r.get("title", "")
            if not names_in(title + " " + text(r.get("description")), names):
                continue
            rights = text(it.get("rights_advisory"))
            author = text(it.get("contributor_names"), ", ") or text(it.get("creator")) or "unknown photographer"
            out.append({"source": "Library of Congress, Prints & Photographs Division", "id": it.get("id") or r.get("id"),
                        "title": title.strip("[]"), "author": author, "page": r.get("url") or r.get("id"),
                        "licence": "No known restrictions on publication (Library of Congress)"
                        if rights.lower().startswith("no known restrictions") else "",
                        "rights": rights[:120], "score": 3 + solo(title),
                        "imgs": [u for u in (r.get("image_url") or []) if "tile.loc.gov" in u],
                        "medium": it.get("service_medium"), "date": text(it.get("date"))[:20]})
    return out


def url_loc(net, c):
    best = max(c["imgs"], key=lambda u: int((re.search(r"[#&]w=(\d+)", u) or [0, 0])[1]), default=None)
    m = c.get("medium") or ""
    if re.search(r"r\.jpg$", m):  # pnp files: <id>r.jpg (~640 px) -> <id>v.jpg (~1024 px)
        return re.sub(r"r\.jpg$", "v.jpg", m)
    return best.split("#")[0] if best else None


def src_eso(net, names):
    out = []
    for q in queries(names):
        r = net.get("https://www.eso.org/public/images/", {"search": q})
        r.raise_for_status()
        for m in re.finditer(r"id:\s*'([^']+)',\s*title:\s*'((?:[^'\\]|\\.)*)',\s*width:\s*(\d+),\s*height:\s*(\d+)", r.text):
            iid, title = m.group(1), html.unescape(m.group(2).replace("\\'", "'"))
            if names_in(title, names):
                out.append({"source": "ESO", "id": iid, "title": title, "page": f"https://www.eso.org/public/images/{iid}/",
                            "licence": "CC BY 4.0", "author": "ESO", "score": 3 + solo(title),
                            "w": int(m.group(3)), "h": int(m.group(4))})
    return out


def url_eso(net, c):
    r = net.get(c["page"])
    r.raise_for_status()
    m = re.search(r'<div class="credit">(.*?)</div>', r.text, re.S)
    credit = " ".join(html.unescape(re.sub("<[^>]+>", " ", m.group(1))).split()) if m else ""
    if not credit or NOT_FREE.search(credit) or "eso" not in credit.lower():  # third-party pictures are not CC BY
        c["licence"], c["author"] = "", credit or "unknown"
        return None
    c["author"] = credit
    return f"https://cdn.eso.org/images/large/{c['id']}.jpg"


def ia_licence(url, rights):
    m = CC_URL.search(url or "")
    if m:
        if m.group(2):
            return f"CC {m.group(2).upper()} {m.group(3)}"
        return "CC0 1.0" if m.group(4).lower() == "zero" else "Public domain (PD Mark)"
    if re.search(r"\bpublic domain\b|\bcc0\b", rights or "", re.I) and not NOT_FREE.search(rights):
        return "Public domain (per the item's rights field)"
    return ""


def src_ia(net, names):
    out = []
    for q in queries(names):
        d = net.json("https://archive.org/advancedsearch.php", {
            "q": f'"{q}" AND mediatype:(image)', "rows": 50, "output": "json",
            "fl[]": ["identifier", "title", "subject", "creator", "licenseurl", "rights", "date"]})
        for x in d["response"]["docs"]:
            title, subj = text(x.get("title")), text(x.get("subject"), " ; ")
            if not (names_in(title, names) or names_in(subj, names)):
                continue
            rights = text(x.get("rights"))
            out.append({"source": "Internet Archive", "id": x["identifier"], "title": title,
                        "author": text(x.get("creator"), ", ") or "unknown",
                        "licence": ia_licence(text(x.get("licenseurl")), rights), "rights": rights[:120] or "no licence",
                        "page": f"https://archive.org/details/{x['identifier']}", "score": 3 + solo(title),
                        "date": text(x.get("date"))[:10]})
    return out


def url_ia(net, c):
    md = net.json(f"https://archive.org/metadata/{c['id']}")
    files = [f for f in md.get("files", []) if re.search(r"\.(jpe?g|png)$", f.get("name", ""), re.I)
             and "thumb" not in f["name"].lower() and f.get("source") == "original"]
    if not files:
        return None
    f = max(files, key=lambda f: int(f.get("size") or 0))
    return f"https://archive.org/download/{c['id']}/{f['name']}"


SOURCES = [("nasa", src_nasa, url_nasa), ("loc", src_loc, url_loc), ("eso", src_eso, url_eso), ("ia", src_ia, url_ia)]


def credit_line(name, c):
    return f"{name} (\"{c['title']}\"): {c['author']}, {c['licence']} ({c['source']}, {c['page']})"


def save_jpg(data, dst):
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    im.load()  # an error page or a truncated file fails here
    if im.format == "JPEG" and im.mode in ("RGB", "L"):
        open(dst, "wb").write(data)
    else:
        im.convert("RGB").save(dst, quality=92)
    return im.size


def portrait(name, out, key=None, aliases=(), dry=False, every=False, net=None):
    """Find (and unless dry, download) a free-licence photo of a person. Returns the chosen record or None."""
    names = [name] + [a for a in aliases if a]
    key = key or re.sub(r"\W+", "_", norm(name).title()).strip("_")
    os.makedirs(out, exist_ok=True)
    net = net or Net(os.path.join(out, "portrait_requests.log"))
    print(f"portrait {name!r} -> {key}")
    picks = []
    for tag, find, locate in SOURCES:
        try:
            cands = find(net, names)
        except Halt:
            raise
        except Exception as e:  # source down or changed: note it and ask the next one
            print(f"  {tag}: ERR {e}")
            continue
        seen, uniq = set(), []
        for c in sorted(cands, key=lambda c: -c["score"]):
            if c["id"] not in seen:
                seen.add(c["id"])
                uniq.append(c)
        print(f"  {tag}: {len(uniq)} candidate(s)")
        for c in uniq[:6]:
            print(f"    [{c['score']}] {c['id']} | {c['title'][:70]} | {c['licence'] or 'NOT FREE: ' + c.get('rights', '?')}")
        for c in uniq:
            if not c["licence"]:
                continue
            try:
                url = locate(net, c)
            except Halt:
                raise
            except Exception as e:
                print(f"    {c['id']}: ERR {e}")
                continue
            if not url or not c["licence"]:
                print(f"    {c['id']}: no usable file or licence ({c['author'][:60]})")
                continue
            c["url"], c["credit"] = url, credit_line(name, c)
            if dry:
                print(f"  PICK (dry run) {c['credit']}\n       {url}")
                picks.append(c)
                break
            dst = os.path.join(out, f"{key}.jpg")
            try:
                size = save_jpg(net.get(url, timeout=180).content, dst)
            except Halt:
                raise
            except Exception as e:
                print(f"    {c['id']}: {url} sent no image ({e}); skipped")
                continue
            if min(size) < MIN_SIDE:
                os.remove(dst)
                print(f"    {c['id']}: only {size[0]}x{size[1]} px; skipped")
                continue
            c["size"] = list(size)
            rec = {k: c[k] for k in ("source", "id", "title", "author", "licence", "page", "url", "credit", "size", "date")
                   if k in c}
            rec.update(name=name, file=f"{key}.jpg", fetched=time.strftime("%Y-%m-%d"))
            for fn, val in (("credits.json", c["credit"]), ("portraits.json", rec)):
                p = os.path.join(out, fn)
                d = json.load(open(p)) if os.path.exists(p) else {}
                d[key] = val
                json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
            print(f"  ok   {key}.jpg {size[0]}x{size[1]}: {c['credit']}")
            picks.append(c)
            break
        if picks and not every:
            break
    if not picks:
        print(f"  MISS {name}: no free-licence photo in NASA / LoC / ESO / Internet Archive")
    return picks[0] if picks else None


def portrait_cli(argv):
    ap = argparse.ArgumentParser(prog="fetch_assets.py portrait")
    ap.add_argument("name")
    ap.add_argument("--out", default=".", help="folder for <Key>.jpg, credits.json, portraits.json and the log")
    ap.add_argument("--key", help="file stem (default: the name, e.g. Maarten_Schmidt)")
    ap.add_argument("--alias", action="append", default=[], help="another spelling to search (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="list candidates and the pick; download nothing")
    ap.add_argument("--all", action="store_true", help="ask every source, not just up to the first hit")
    a = ap.parse_args(argv)
    if a.key and os.path.exists(os.path.join(a.out, f"{a.key}.jpg")) and not a.dry_run:
        print(f"{a.key}.jpg exists; skipped")
        return 0
    try:
        hit = portrait(a.name, a.out, a.key, a.alias, a.dry_run, a.all)
    except Halt as e:
        print(f"STOP {e}")
        return 2
    return 0 if hit else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "portrait":
        sys.exit(portrait_cli(sys.argv[2:]))
    spec, out = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    cpath = os.path.join(out, "credits.json")
    credits = json.load(open(cpath)) if os.path.exists(cpath) else {}
    net = None
    for key, s in spec.items():
        dst = os.path.join(out, f"{key}.jpg")
        if os.path.exists(dst):
            continue
        if s["src"] == "portrait":  # writes its own line into credits.json
            net = net or Net(os.path.join(out, "portrait_requests.log"))
            try:
                portrait(s["name"], out, key, s.get("alias", []), net=net)
            except Halt as e:
                print(f"STOP {e}")
                sys.exit(2)
            credits = json.load(open(cpath)) if os.path.exists(cpath) else {}
            continue
        try:
            if s["src"] == "url":
                url, credit = s["url"], s["credit"]
            else:
                url, credit = (nasa if s["src"] == "nasa" else wiki)(s["q"], s.get("must", []))
        except Exception as e:  # rate limits / bad JSON: skip this asset, keep going
            url, credit = None, None
            print(f"ERR  {key}: {e}")
        if not url:
            print(f"MISS {key}: {s['q']}")
            continue
        data = requests.get(url, headers=UA, timeout=180).content
        if not data.startswith((b"\xff\xd8", b"\x89PNG")):  # an error page (e.g. Wikimedia rate limit), not an image
            print(f"BAD  {key}: {url} sent no image ({data[:40]!r}); skipped")
            continue
        open(dst, "wb").write(data)
        credits[key] = credit
        print(f"ok   {key}: {credit[:110]}")
        json.dump(credits, open(cpath, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
