"""Give every footage item of the edit its own shot: CLIP match between the item's visual queries and the
library shots, solved as one global assignment so no shot - and no other shot showing the same image - is
used twice.

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
import render_v3  # noqa: E402

PAD = 0.8          # extra seconds of footage per item (transition overlap)
DARK_PENALTY = 0.05


def luma(lib, s):
    """Mean brightness (0-255) of the shot's 3 review frames."""
    if s.get("luma") is not None:
        return s["luma"]
    im = cv2.imread(os.path.join(lib, "shot_thumbs", s["id"].replace("#", "_") + ".jpg"), cv2.IMREAD_GRAYSCALE)
    return float(im.mean()) if im is not None else 40.0


# Two shots count as the same footage when any frame of the part that will be shown looks the same: CLIP
# similarity above SAME_CLIP and perceptual-hash distance within SAME_HASH (same image, maybe re-zoomed).
SAME_RULES = ((0.95, 14), (0.975, 26))   # (min CLIP similarity, max hash distance): either one = same footage


def segment_signatures(lib, pool, cache_path):
    """3 frames around the middle of each shot's longest usable range (the part assign uses):
    CLIP embeddings (n, 3, 512) and 64-bit phashes (n, 3)."""
    import imagehash
    from PIL import Image
    cache = dict(np.load(cache_path, allow_pickle=True)) if os.path.exists(cache_path) else {}
    old = {k: (e, h) for k, e, h in zip(cache.get("keys", []), cache.get("emb", []), cache.get("hash", []))}
    keys, todo, frames = [], [], []
    for s in pool:
        r0, r1 = max(s["usable"], key=lambda rr: rr[1] - rr[0])
        m = (r0 + r1) / 2
        key = f"{s['id']}@{m:.2f}@{s.get('crop')}"
        keys.append(key)
        if key in old:
            continue
        cap = cv2.VideoCapture(os.path.join(lib, "clips", s["clip"] + ".mp4"))
        for t in (max(r0, m - 1.2), m, min(r1, m + 1.2)):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, f = cap.read()
            f = f if ok else np.zeros((1080, 1920, 3), np.uint8)
            if s.get("crop"):
                x0, y0, x1, y1 = s["crop"]
                f = f[int(y0 * 1080):int(y1 * 1080), int(x0 * 1920):int(x1 * 1920)]
            frames.append(cv2.cvtColor(cv2.resize(f, (384, 216)), cv2.COLOR_BGR2RGB))
        cap.release()
        todo.append(key)
    if todo:
        E = clip_model.embed_images(frames).reshape(len(todo), 3, -1)
        H = np.array([[int(str(imagehash.phash(Image.fromarray(frames[3 * k + q]))), 16) for q in range(3)]
                      for k in range(len(todo))], dtype=np.uint64)
        for k, key in enumerate(todo):
            old[key] = (E[k], H[k])
        np.savez(cache_path, keys=np.array(list(old)), emb=np.stack([v[0] for v in old.values()]),
                 hash=np.stack([v[1] for v in old.values()]))
    return np.stack([old[k][0] for k in keys]), np.stack([old[k][1] for k in keys])


def same_footage(SE, SH, j, others):
    """Indices in `others` whose shown frames look like shot j's."""
    if not others:
        return []
    o = np.array(others)
    sim = np.einsum("ad,nbd->nab", SE[j], SE[o]).reshape(len(o), -1).max(1)
    x = SH[j][:, None, None] ^ SH[o].T[None, :, :]                         # (3, 3, n) xor of hashes
    ham = np.vectorize(lambda v: bin(int(v)).count("1"))(x).reshape(9, len(o)).min(0)
    hit = np.zeros(len(o), bool)
    for c_min, h_max in SAME_RULES:
        hit |= (sim > c_min) & (ham <= h_max)
    return list(o[hit])


_OCR = {}


def _ocr_init():
    import torch, easyocr
    torch.set_num_threads(1)
    cv2.setNumThreads(1)
    _OCR["r"] = easyocr.Reader(["en"], gpu=False, verbose=False)


def _ocr_job(job):
    """True if any of the frames that will actually be shown carries text (finer than the library scan)."""
    path, times, crop = job
    cap = cv2.VideoCapture(path)
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        if crop:
            x0, y0, x1, y1 = crop
            f = f[int(y0 * 1080):int(y1 * 1080), int(x0 * 1920):int(x1 * 1920)]
        horiz, free = _OCR["r"].detect(cv2.resize(f, (768, 432)), min_size=10, text_threshold=0.7, low_text=0.45)
        if (horiz and horiz[0]) or (free and free[0]):
            return True
        # small print (timestamps, credit lines) lives in the top and bottom strips: read them at full resolution
        hh = f.shape[0]
        for strip in (f[:int(hh * 0.16)], f[int(hh * 0.84):]):
            horiz, free = _OCR["r"].detect(strip, min_size=8, text_threshold=0.7, low_text=0.4)
            if (horiz and horiz[0]) or (free and free[0]):
                return True
    return False


def text_gate(lib, items, pool, r, c, need, cache_path, workers=4):
    """Indices k (into r/c) whose shown segment has text. Results cached per (shot, start, length)."""
    from multiprocessing import Pool
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    jobs, keys = [], []
    for k, (i, j) in enumerate(zip(r, c)):
        s = pool[j]
        r0, r1 = max(s["usable"], key=lambda rr: rr[1] - rr[0])
        ss = r0 + max(0.0, (r1 - r0 - need[i]) / 2)
        d = need[i] - 0.8
        key = f"{s['id']}@{ss:.2f}+{d:.2f}" + (f"/crop{list(s['crop'])}" if s.get("crop") else "") + "/strips"
        keys.append(key)
        if key not in cache:
            jobs.append((key, (os.path.join(lib, "clips", s["clip"] + ".mp4"),
                               [ss + 0.1 + d * q for q in (0, 0.25, 0.5, 0.75, 1.0)][:-1] + [ss + d - 0.1], s.get("crop"))))
    if jobs:
        with Pool(workers, initializer=_ocr_init) as p:
            for (key, _), hit in zip(jobs, p.map(_ocr_job, [j for _, j in jobs])):
                cache[key] = hit
        json.dump(cache, open(cache_path, "w"))
    return [k for k, key in enumerate(keys) if cache[key]]


def main():
    ap = argparse.ArgumentParser()
    for x in ("edit", "timeline", "lib", "out"):
        ap.add_argument(x)
    ap.add_argument("--review", default="")
    ap.add_argument("--changed", default="", help="previous cutlist.json: review sheets show only items whose shot changed")
    ap.add_argument("--keep", default="", help="previous (reviewed) cutlist.json: items keep their shot unless it is now banned")
    ap.add_argument("--avoid", default="", help="productions dir: never reuse shots other productions' cutlist.json used")
    ap.add_argument("--plan-only", action="store_true", help="only check the edit against the narration")
    ap.add_argument("--local-only", action="store_true", help="use only shots whose clip file is on disk (re-renders)")
    ap.add_argument("--clips-from", default="", help="cutlist.json: use only clips it used (a re-cut of a published video)")
    a = ap.parse_args()
    edit, tl = json.load(open(a.edit)), json.load(open(a.timeline))
    v3 = edit.get("style") == "v3"
    if v3:  # v3 plan: scenes snapped to the voice, overlays, moments (scripts/video/render_v3.py)
        P = render_v3.plan(edit, tl, os.path.join(os.path.dirname(os.path.abspath(a.timeline)), "narration.wav"))
        items, caps, sfx, total, off = P["items"], P["caps"], P["sfx"], P["total"], P["off"]
    else:
        items, caps, sfx, total, off = render_v2.plan(edit, tl)
    if a.plan_only:
        kinds = {k: sum(1 for it in items if it["kind"] == k) for k in ("clip", "gfx", "num", "card", "title")}
        lens = np.array([it["t1"] - it["t0"] for it in items if it["kind"] == "clip"])
        print(f"edit OK: {len(items)} items {kinds}, {len(caps)} captions, {total:.1f}s; "
              f"scene length median {np.median(lens):.2f}s, max {lens.max():.2f}s -> needs {len(items)} different shots")
        if v3:
            print(f"  v3: {len(P['ovl'])} overlays {dict((k, sum(o['kind'] == k for o in P['ovl'])) for k in ('headline', 'keyline', 'num', 'footer'))}, "
                  f"{len(P['breaths'])} breaths, {len(sfx)} sfx ({len(sfx) / total * 60:.0f}/min), "
                  f"cuts/min {60 * (len(items) - 1) / total:.1f}, scene p10-p90 {np.percentile(lens, 10):.1f}-{np.percentile(lens, 90):.1f}s")
        return
    shots = json.load(open(os.path.join(a.lib, "shots.json")))
    sources = json.load(open(os.path.join(a.lib, "sources.json")))
    bite_pins = set()  # a real recording's scene shows its own clip (bite_<name>), in sync with its sound
    for i, it in enumerate(items):
        if it.get("bite"):
            clip = "bite_" + it["bite"]
            own = [s for s in shots if s["clip"] == clip]
            if not own:
                raise SystemExit(f"{clip}: not in the library (scripts/footage/add_archive.py bites <bites.json>)")
            it["clip_ss"] = round(max(0.0, sources[clip].get("bite_pre", 0.0) - it["bite_lead"]), 3)
            sid = next((s["id"] for s in own if s["start"] <= it["clip_ss"] < s["end"]), own[0]["id"])
            edit.setdefault("pin", {})[f"{it['sec']}/{sum(1 for j in range(i) if items[j]['sec'] == it['sec'])}"] = sid
            bite_pins.add(sid)
    for s in shots:  # a pin is a deliberate choice: real archive footage keeps its on-screen text and dark frames
        if s["id"] in set(edit.get("pin", {}).values()) | bite_pins:
            s["dup_of"] = None
            if not s["usable"] and s["end"] - s["start"] > 0.6:
                s["usable"], s["crop"] = [[s["start"] + 0.15, s["end"] - 0.15]], None
    z = np.load(os.path.join(a.lib, "shots_emb.npz"), allow_pickle=True)
    emb = dict(zip(z["ids"], z["emb"]))
    ban, avoided = set(edit.get("ban", [])), set()
    if a.avoid:  # footage already published in other productions stays out of this one
        here = os.path.dirname(os.path.abspath(a.edit))
        for d in sorted(os.listdir(a.avoid)):
            f = os.path.join(a.avoid, d, "cutlist.json")
            if os.path.exists(f) and os.path.abspath(os.path.join(a.avoid, d)) != here:
                avoided |= {it["shot"] for it in json.load(open(f))["items"] if it.get("shot")}
        ban |= avoided
    for s in shots:  # manual fixes from edit.base.json: cut seconds out of a clip, force a crop
        for x0, x1 in edit.get("exclude", {}).get(s["clip"], []):
            s["usable"] = [r for a_, z in s["usable"] for r in ([a_, min(z, x0)], [max(a_, x1), z]) if r[1] - r[0] >= 1.5]
        if s["clip"] in edit.get("crops", {}):
            s["crop"] = edit["crops"][s["clip"]]
    pool = [s for s in shots if s["usable"] and not s["dup_of"] and s["id"] not in ban and s["clip"] not in ban]
    pool = [s for s in pool if not s["clip"].startswith("bite_")] + [s for s in shots if s["id"] in bite_pins]
    if a.local_only:
        pool = [s for s in pool if os.path.exists(os.path.join(a.lib, "clips", s["clip"] + ".mp4"))]
        print(f"local only: {len(pool)} usable shots with their clip on disk")
    if a.clips_from:
        own = {it["clip"] for it in json.load(open(a.clips_from))["items"] if it.get("clip")}
        pinned = set(edit.get("pin", {}).values())  # a pin is a deliberate choice: it may come from elsewhere
        pool = [s for s in pool if s["clip"] in own or s["id"] in pinned]
        print(f"clips from {a.clips_from}: {len(pool)} usable shots")
    if avoided:  # near-identical copies of footage earlier productions showed (same image, re-zoomed) stay out too
        prev = [s for s in shots if s["id"] in avoided and s["usable"]]
        sig = os.path.join(a.lib, "segments_sig.npz")
        PE, PH = segment_signatures(a.lib, prev, sig)
        CE, CH = segment_signatures(a.lib, pool, sig)
        AE, AH = np.concatenate([CE, PE]), np.concatenate([CH, PH])
        keep = [k for k in range(len(pool)) if not same_footage(AE, AH, k, range(len(pool), len(pool) + len(prev)))]
        print(f"avoid: {len(prev)} shots from earlier productions; {len(pool) - len(keep)} look-alikes removed")
        pool = [pool[k] for k in keep]
    own_rows = {i for i, it in enumerate(items) if render_v3.own_gfx(it)}
    n_vis = len(pool)
    if avoided and own_rows:  # own graphics show no footage: their unseen placeholder can be a shot an earlier video used
        spare = [s for s in shots if s["id"] in avoided and s["usable"] and not s["dup_of"]
                 and os.path.exists(os.path.join(a.lib, "clips", s["clip"] + ".mp4"))]
        pool = pool + spare[:len(own_rows)]
    if len(pool) < len(items):
        raise SystemExit(f"library has {n_vis} usable shots (+{len(pool) - n_vis} placeholders for own graphics) but the "
                         f"edit needs {len(items)} different ones: add footage")
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
    # near-black star fields and washed-out white frames are poor main footage (fine behind cards/graphics)
    lum = np.array([luma(a.lib, s) for s in pool])
    dull = DARK_PENALTY * np.clip((28 - lum) / 20, 0, 1) + DARK_PENALTY * np.clip((lum - 120) / 40, 0, 1)  # or washed out
    S = S - np.array([[1.0] if it["kind"] == "clip" else [0.0] for it in items]) * dull[None, :]
    if len(pool) > n_vis:  # placeholders only ever stand behind our own graphics
        hid, vis = np.arange(n_vis, len(pool)), np.array([i not in own_rows for i in range(len(items))])
        S[np.ix_(vis, hid)], S[np.ix_(~vis, hid)] = -1000.0, 1.0
    # our own full-frame graphics show no footage: any shot will do as their (unseen) placeholder
    need = np.array([(min(it["t1"] - it["t0"], 1.0) if render_v3.own_gfx(it) or it.get("bite") else it["t1"] - it["t0"]) + PAD
                     for it in items])
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
    pinned_rows = {i for i, key in sec_n.items() if key in edit.get("pin", {})}  # pins win every clash check
    if a.keep and os.path.exists(a.keep):  # converge review rounds: only re-solve items whose shot was banned
        old = {(o["sec"], round(o["t0"], 2)): o.get("shot") for o in json.load(open(a.keep))["items"]}
        kept = 0
        pinned = set(edit.get("pin", {}).values())  # a pinned shot is never held by another item
        for i, it in enumerate(items):
            sid = old.get((it["sec"], round(it["t0"], 2)))
            if sid in ids and sec_n[i] not in edit.get("pin", {}) and sid not in pinned:
                cost[i, :] += 50.0
                cost[i, ids.index(sid)] -= 50.0
                kept += 1
        print(f"kept {kept} reviewed items")
    SE, SH = segment_signatures(a.lib, pool, os.path.join(a.lib, "segments_sig.npz"))
    blocked = np.zeros_like(cost)
    for rnd in range(30):
        r, c = linear_sum_assignment(cost + blocked)
        clash = 0
        order = sorted(range(len(r)), key=lambda k: (r[k] not in pinned_rows, cost[r[k], c[k]]))  # pins, then best matches
        chosen = []
        for k in order:
            i, j = r[k], c[k]
            if i not in pinned_rows and same_footage(SE, SH, j, chosen):
                blocked[i, j] = 100.0
                clash += 1
            else:
                chosen.append(j)
        print(f"round {rnd}: {clash} near-identical clashes", flush=True)
        if not clash:
            break
    else:  # still clashing: give the remaining items the best free shot that shows nothing already chosen
        r, c = list(r), list(c)
        order = sorted(range(len(r)), key=lambda k: (r[k] not in pinned_rows, cost[r[k], c[k]]))
        chosen, used = [], set()
        for k in order:
            i, j = r[k], c[k]
            if i not in pinned_rows and same_footage(SE, SH, j, chosen):
                for j2 in np.argsort(cost[i] + blocked[i]):
                    if j2 not in used and j2 not in c and cost[i, j2] < 50 and not same_footage(SE, SH, j2, chosen):
                        c[k] = j = int(j2)
                        break
            chosen.append(j)
            used.add(j)
        print("greedy pass resolved the remaining clashes", flush=True)
    # final gate: OCR the frames each item will really show; text -> that shot is out, re-solve the rest in place
    for rnd in range(40):  # every re-solve is checked again: the result never skips the gate
        hits = text_gate(a.lib, items, pool, r, c, need, os.path.join(a.lib, "text_gate.json"))
        hits = [k for k in hits if sec_n[r[k]] not in edit.get("pin", {})]  # a pin is a deliberate choice
        print(f"text gate {rnd}: {len(hits)} shown segments with text", flush=True)
        if not hits:
            break
        if rnd == 39:
            raise SystemExit("text gate did not converge: ban the clips it keeps hitting or add footage")
        for k in hits:
            cost[:, c[k]] += 100.0  # the shot is out for every item
        for k in range(len(r)):
            if k not in hits:  # everyone else keeps their shot
                cost[r[k], :] += 50.0
                cost[r[k], c[k]] -= 50.0
        r, c = linear_sum_assignment(cost + blocked)
        r, c = list(r), list(c)
        chosen = []
        for k in sorted(range(len(r)), key=lambda k: (r[k] not in pinned_rows, cost[r[k], c[k]])):
            i, j = r[k], c[k]
            if i not in pinned_rows and same_footage(SE, SH, j, chosen):
                for j2 in np.argsort(cost[i] + blocked[i]):
                    if j2 not in c and cost[i, j2] < 50 and not same_footage(SE, SH, j2, chosen):
                        c[k] = j = int(j2)
                        break
            chosen.append(j)
    bad = [i for i, j in zip(r, c) if L[j] < need[i]]
    if bad:
        raise SystemExit(f"{len(bad)} items have no shot long enough, e.g. {[sec_n[i] for i in bad[:5]]}: add footage")
    for i, j in zip(r, c):
        it, s = items[i], pool[j]
        if it.get("bite"):  # plays from the frame that matches its sound
            ss = it.pop("clip_ss")
        else:
            r0, r1 = max(s["usable"], key=lambda rr: rr[1] - rr[0])
            ss = r0 + max(0.0, (r1 - r0 - need[i]) / 2)
        it.update(shot=s["id"], clip=s["clip"], ss=round(ss, 2), crop=s["crop"], score=round(float(S[i, j]), 4),
                  ref=sec_n[i], title=sources[s["clip"]]["title"])
    used = [it["shot"] for it in items]
    assert len(used) == len(set(used)), "a shot was used twice"
    out = {**(P if v3 else {}), "total": total, "off": off, "clips_dir": os.path.abspath(os.path.join(a.lib, "clips")),
           "items": items, "caps": caps, "sfx": sfx}
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    sc = np.array([it["score"] for it in items if it["kind"] == "clip"])
    print(f"{len(items)} items -> {len(set(used))} different shots from {len({it['clip'] for it in items})} videos "
          f"(library {len(pool)} usable shots); clip score median {np.median(sc):.3f}, lowest {np.sort(sc)[:5].round(3)}")
    if a.review:
        keep = None
        if a.changed and os.path.exists(a.changed):
            old = {(o["sec"], round(o["t0"], 2)): o.get("shot") for o in json.load(open(a.changed))["items"]}
            keep = {n for n, it in enumerate(items) if old.get((it["sec"], round(it["t0"], 2))) != it["shot"]}
            print(f"review: {len(keep)} changed items")
        review(items, os.path.join(a.lib, "clips"), a.review, keep=keep)


def review(items, clips_dir, out_dir, per=48, cols=6, keep=None):
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.startswith("review_"):
            os.remove(os.path.join(out_dir, f))
    tiles = []
    for n, it in enumerate(items):
        if keep is not None and n not in keep:
            continue
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
    if not tiles:
        return
    for p in range(0, len(tiles), per):
        page = tiles[p:p + per]
        while len(page) % cols:
            page.append(np.zeros_like(tiles[0]))
        cv2.imwrite(os.path.join(out_dir, f"review_{p // per:02d}.jpg"),
                    np.vstack([np.hstack(page[i:i + cols]) for i in range(0, len(page), cols)]), [cv2.IMWRITE_JPEG_QUALITY, 72])


if __name__ == "__main__":
    main()
