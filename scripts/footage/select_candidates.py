"""Pick which 4K candidate videos to download for an edit: score every candidate's preview frame and title
against every footage item's visual queries with CLIP, then keep the best matches per item.

  python select_candidates.py <candidates.json> <edit.json> <timeline.json> <work_dir> <out picks.json>
                              [--per-item 2] [--max 420]

Thumbnails are cached in <work_dir>/thumbs, embeddings in <work_dir>/cand_emb.npz.
picks.json: [{key, url, title, source, page, cap_s, best_q, score}] sorted by score.
cap_s = seconds to transcode: long for multi-shot episodes (ESOcast, Hubblecast, produced videos),
short for single-shot zooms/pans/animations, where one 2-3 s use is all the edit can take.
"""
import argparse, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np, requests

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "video"))
import clip_model  # noqa: E402

MULTI = re.compile(r"(esocast|hubblecast|webbcast|episode|chapter|space sparks|feature|explained|trailer|highlights)", re.I)


def thumb_url(c):
    if c.get("thumb"):
        return c["thumb"]
    if c["source"] == "svs":
        try:
            d = requests.get(f"https://svs.gsfc.nasa.gov/api/{c['id']}", timeout=30).json()
            return ((d.get("main_image") or {}).get("url") or "").replace("http://", "https://")
        except Exception:
            return ""
    return {"eso": "https://cdn.eso.org/videos/videoframe/{id}.jpg",
            "esahubble": "https://cdn.esahubble.org/archives/videos/videoframe/{id}.jpg",
            "esawebb": "https://cdn.esawebb.org/archives/videos/videoframe/{id}.jpg"}[c["source"]].format(id=c["id"])


def fetch(args):
    key, url, path = args
    if os.path.exists(path) or not url:
        return key, os.path.exists(path)
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and len(r.content) > 2000:
            open(path, "wb").write(r.content)
            return key, True
    except requests.RequestException:
        pass
    return key, False


def item_queries(edit, tl):
    import render_v2
    items, *_ = render_v2.plan(edit, tl)
    return items


def main():
    ap = argparse.ArgumentParser()
    for x in ("candidates", "edit", "timeline", "work", "out"):
        ap.add_argument(x)
    ap.add_argument("--per-item", type=int, default=2)
    ap.add_argument("--max", type=int, default=420)
    a = ap.parse_args()
    from PIL import Image
    cand = json.load(open(a.candidates))
    edit, tl = json.load(open(a.edit)), json.load(open(a.timeline))
    os.makedirs(os.path.join(a.work, "thumbs"), exist_ok=True)
    keys = sorted(cand)
    jobs = [(k, thumb_url(cand[k]), os.path.join(a.work, "thumbs", k.replace(":", "_") + ".jpg")) for k in keys]
    with ThreadPoolExecutor(12) as ex:
        ok = dict(ex.map(fetch, jobs))
    keys = [k for k in keys if ok.get(k)]
    print(f"{len(keys)} candidates with preview frames", flush=True)
    cache = os.path.join(a.work, "cand_emb.npz")
    old = dict(np.load(cache, allow_pickle=True)) if os.path.exists(cache) else {}
    have = {k: (old["img"][i], old["txt"][i]) for i, k in enumerate(old.get("keys", []))}
    new = [k for k in keys if k not in have]
    if new:
        imgs = [np.array(Image.open(os.path.join(a.work, "thumbs", k.replace(":", "_") + ".jpg")).convert("RGB")) for k in new]
        ie = clip_model.embed_images(imgs)
        te = clip_model.embed_texts([f"a video of {cand[k]['title']}" for k in new])
        for k, i_, t_ in zip(new, ie, te):
            have[k] = (i_, t_)
        np.savez(cache, keys=np.array(list(have)), img=np.stack([v[0] for v in have.values()]), txt=np.stack([v[1] for v in have.values()]))
    I = np.stack([have[k][0] for k in keys])
    T = np.stack([have[k][1] for k in keys])
    items = [it for it in item_queries(edit, tl)]
    qs = sorted({q for it in items for q in it["q"]})
    Q = clip_model.embed_texts([f"a photo of {q}" for q in qs])
    qi = {q: i for i, q in enumerate(qs)}
    S = 0.7 * (Q @ I.T) + 0.3 * (Q @ T.T)  # queries x candidates
    picked, why = {}, {}
    # every item takes its top candidates that no earlier item took (mirrors the one-use-per-shot rule)
    for it in sorted(items, key=lambda x: x["kind"] != "clip"):
        sc = np.max(S[[qi[q] for q in it["q"]]], 0)
        n = 0
        for j in np.argsort(-sc):
            k = keys[j]
            if k in picked:
                continue
            picked[k], why[k] = float(sc[j]), it["q"][0]
            n += 1
            if n >= a.per_item:
                break
    ranked = sorted(picked, key=lambda k: -picked[k])[:a.max]
    out = []
    for k in ranked:
        c = cand[k]
        multi = bool(MULTI.search(c["title"])) or (c["source"] == "svs" and "produced" in c.get("desc", "").lower())
        out.append({"key": k, "url": c["url"], "title": c["title"], "source": c["source"], "page": c.get("page", ""),
                    "cap_s": 150 if multi else 22, "best_q": why[k], "score": round(picked[k], 4)})
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(items)} items, {len(qs)} queries -> {len(out)} picks "
          f"({sum(o['cap_s'] > 30 for o in out)} multi-shot); {sum(o['cap_s'] for o in out)} s to transcode")


if __name__ == "__main__":
    main()
