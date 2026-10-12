"""Give every footage item of the edit its own shot: CLIP match between the item's visual queries and the
library shots, solved as one global assignment so no shot (and no near-identical shot) is used twice.

  python assign_shots.py <edit.json> <timeline.json> <library_dir> <out cutlist.json> [--review <dir>]

edit.json may hold: "pin" {"<section>/<n>": "<shot id>"} to force a shot onto the n-th item of a section
(numbers as printed on the review sheets), "ban" ["<shot id>" | "<clip name>", ...] to keep footage out,
"exclude" {"<clip>": [[from_s, to_s], ...]} to cut seconds out, "crops" {"<clip>": [x0, y0, x1, y1]}.
Review sheets show every item's chosen frame with its query and score - look at them before rendering.
"""
import argparse, json, os, sys
import numpy as np, cv2
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "video"))
import clip_model  # noqa: E402
import render_v2  # noqa: E402

PAD = 0.8          # extra seconds of footage per item (transition overlap)
DARK_PENALTY = 0.05


def luma(lib, s):
    """Mean brightness (0-255) of the shot's 3 review frames."""
    if s.get("luma") is not None:
        return s["luma"]
    im = cv2.imread(os.path.join(lib, "shot_thumbs", s["id"].replace("#", "_") + ".jpg"), cv2.IMREAD_GRAYSCALE)
    return float(im.mean()) if im is not None else 40.0
SAME = 0.93        # CLIP image similarity above which two shots count as the same footage


def main():
    ap = argparse.ArgumentParser()
    for x in ("edit", "timeline", "lib", "out"):
        ap.add_argument(x)
    ap.add_argument("--review", default="")
    ap.add_argument("--avoid", default="", help="productions dir: never reuse shots other productions' cutlist.json used")
    ap.add_argument("--plan-only", action="store_true", help="only check the edit against the narration")
    a = ap.parse_args()
    edit, tl = json.load(open(a.edit)), json.load(open(a.timeline))
    items, caps, sfx, total, off = render_v2.plan(edit, tl)
    if a.plan_only:
        kinds = {k: sum(1 for it in items if it["kind"] == k) for k in ("clip", "gfx", "card", "title")}
        lens = np.array([it["t1"] - it["t0"] for it in items if it["kind"] == "clip"])
        print(f"edit OK: {len(items)} items {kinds}, {len(caps)} captions, {total:.1f}s; "
              f"scene length median {np.median(lens):.2f}s, max {lens.max():.2f}s -> needs {len(items)} different shots")
        return
    shots = json.load(open(os.path.join(a.lib, "shots.json")))
    sources = json.load(open(os.path.join(a.lib, "sources.json")))
    z = np.load(os.path.join(a.lib, "shots_emb.npz"), allow_pickle=True)
    emb = dict(zip(z["ids"], z["emb"]))
    ban = set(edit.get("ban", []))
    if a.avoid:  # footage already published in other productions stays out of this one
        here = os.path.dirname(os.path.abspath(a.edit))
        for d in sorted(os.listdir(a.avoid)):
            f = os.path.join(a.avoid, d, "cutlist.json")
            if os.path.exists(f) and os.path.abspath(os.path.join(a.avoid, d)) != here:
                ban |= {it["shot"] for it in json.load(open(f))["items"] if it.get("shot")}
    for s in shots:  # manual fixes from edit.base.json: cut seconds out of a clip, force a crop
        for x0, x1 in edit.get("exclude", {}).get(s["clip"], []):
            s["usable"] = [r for a_, z in s["usable"] for r in ([a_, min(z, x0)], [max(a_, x1), z]) if r[1] - r[0] >= 1.5]
        if s["clip"] in edit.get("crops", {}):
            s["crop"] = edit["crops"][s["clip"]]
    pool = [s for s in shots if s["usable"] and not s["dup_of"] and s["id"] not in ban and s["clip"] not in ban]
    if len(pool) < len(items):
        raise SystemExit(f"library has {len(pool)} usable shots but the edit needs {len(items)} different ones: add footage")
    E = np.stack([emb[s["id"]] for s in pool])
    L = np.array([max(r[1] - r[0] for r in s["usable"]) for s in pool])
    titles = sorted({sources[s["clip"]]["title"] for s in pool})
    T = clip_model.embed_texts([f"a video of {t}" for t in titles])
    ti = {t: i for i, t in enumerate(titles)}
    Tshot = T[[ti[sources[s["clip"]]["title"]] for s in pool]]
    qs = sorted({q for it in items for q in it["q"]})
    Q = clip_model.embed_texts([f"a photo of {q}" for q in qs])
    qi = {q: i for i, q in enumerate(qs)}
    SQ = 0.75 * (Q @ E.T) + 0.25 * (Q @ Tshot.T)
    S = np.stack([SQ[[qi[q] for q in it["q"]]].max(0) for it in items])  # items x shots
    # near-black star fields are dull as main footage (fine behind cards and graphics): small penalty
    lum = np.array([luma(a.lib, s) for s in pool])
    dull = DARK_PENALTY * np.clip((28 - lum) / 20, 0, 1)
    S = S - np.array([[1.0] if it["kind"] == "clip" else [0.0] for it in items]) * dull[None, :]
    need = np.array([it["t1"] - it["t0"] + PAD for it in items])
    cost = -S + 100.0 * (L[None, :] < need[:, None])
    # pins
    sec_n = {}
    for i, it in enumerate(items):
        sec_n[i] = f"{it['sec']}/{sum(1 for j in range(i) if items[j]['sec'] == it['sec'])}"
    ids = [s["id"] for s in pool]
    for i, key in sec_n.items():
        if key in edit.get("pin", {}):
            sid = edit["pin"][key]
            if sid in ids:
                cost[i, :] += 50.0
                cost[i, ids.index(sid)] -= 50.0
    sim = E @ E.T
    blocked = np.zeros_like(cost)
    for rnd in range(8):
        r, c = linear_sum_assignment(cost + blocked)
        clash = 0
        order = sorted(range(len(r)), key=lambda k: cost[r[k], c[k]])  # best matches keep their shot
        kept = []
        for k in order:
            i, j = r[k], c[k]
            if any(sim[j, j2] > SAME for j2 in kept):
                blocked[i, j] = 100.0
                clash += 1
            else:
                kept.append(j)
        if not clash:
            break
    bad = [i for i, j in zip(r, c) if cost[i, j] > 50]
    if bad:
        raise SystemExit(f"{len(bad)} items have no shot long enough, e.g. {[sec_n[i] for i in bad[:5]]}: add footage")
    for i, j in zip(r, c):
        it, s = items[i], pool[j]
        r0, r1 = max(s["usable"], key=lambda rr: rr[1] - rr[0])
        ss = r0 + max(0.0, (r1 - r0 - need[i]) / 2)
        it.update(shot=s["id"], clip=s["clip"], ss=round(ss, 2), crop=s["crop"], score=round(float(S[i, j]), 4),
                  ref=sec_n[i], title=sources[s["clip"]]["title"])
    used = [it["shot"] for it in items]
    assert len(used) == len(set(used)), "a shot was used twice"
    json.dump({"total": total, "off": off, "clips_dir": os.path.abspath(os.path.join(a.lib, "clips")),
               "items": items, "caps": caps, "sfx": sfx}, open(a.out, "w"), indent=1, ensure_ascii=False)
    sc = np.array([it["score"] for it in items if it["kind"] == "clip"])
    print(f"{len(items)} items -> {len(set(used))} different shots from {len({it['clip'] for it in items})} videos "
          f"(library {len(pool)} usable shots); clip score median {np.median(sc):.3f}, lowest {np.sort(sc)[:5].round(3)}")
    if a.review:
        review(items, os.path.join(a.lib, "clips"), a.review)


def review(items, clips_dir, out_dir, per=48, cols=6):
    os.makedirs(out_dir, exist_ok=True)
    tiles = []
    for n, it in enumerate(items):
        cap = cv2.VideoCapture(os.path.join(clips_dir, it["clip"] + ".mp4"))
        cap.set(cv2.CAP_PROP_POS_MSEC, (it["ss"] + (it["t1"] - it["t0"]) / 2) * 1000)
        ok, f = cap.read()
        cap.release()
        f = f if ok else np.zeros((1080, 1920, 3), np.uint8)
        if it.get("crop"):
            x0, y0, x1, y1 = it["crop"]
            f = f[int(y0 * 1080):int(y1 * 1080), int(x0 * 1920):int(x1 * 1920)]
        f = cv2.resize(f, (320, 180))
        band = np.zeros((44, 320, 3), np.uint8)
        label = it.get("gfx") or it["kind"] if it["kind"] != "clip" else it["q"][0]
        cv2.putText(band, f"{n} {it['ref']} {it['score']:.2f}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1)
        cv2.putText(band, label[:46], (3, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)
        tiles.append(np.vstack([f, band]))
    for p in range(0, len(tiles), per):
        page = tiles[p:p + per]
        while len(page) % cols:
            page.append(np.zeros_like(tiles[0]))
        cv2.imwrite(os.path.join(out_dir, f"review_{p // per:02d}.jpg"),
                    np.vstack([np.hstack(page[i:i + cols]) for i in range(0, len(page), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 72])


if __name__ == "__main__":
    main()
