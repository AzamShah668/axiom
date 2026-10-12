"""Split library proxies into shots and QC every shot: burned-in text, black frames, motion, duplicates,
plus CLIP embeddings for matching shots to narration.

  python build_shots.py <library_dir> [--workers 4]

Reads <library_dir>/clips/*.mp4 + sources.json, writes <library_dir>/shots.json and shots_emb.npz.
Per shot: {id, clip, start, end, crop, usable: [[a, b], ...], motion, text_secs, dup_of}
  usable = seconds that are text-free (inside the auto-crop), not black and visibly moving
  dup_of = id of an earlier shot showing the same footage (perceptual hash) -> never used
Already-processed clips are kept; delete a clip's shots from shots.json to redo it.
"""
import argparse, glob, json, os, sys
from multiprocessing import Pool
import numpy as np, cv2

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "video"))
from clip_qc import best_crop  # noqa: E402

SW, SH = 512, 288
MIN_SHOT = 2.0      # seconds; shorter shots can't carry a scene
MOTION_MIN = 0.6    # mean abs grey difference over 0.5 s (0-255) below which a second counts as frozen
TEXT_STEP = 2.0


def shots_of(path):
    from scenedetect import detect, ContentDetector
    cap = cv2.VideoCapture(path)
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30)
    cap.release()
    cuts = detect(path, ContentDetector(threshold=27, min_scene_len=12))
    spans = [(s.get_seconds(), e.get_seconds()) for s, e in cuts] or [(0.0, dur)]
    return [(a, b) for a, b in spans if b - a >= MIN_SHOT], dur


def grab(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, fr = cap.read()
    return fr if ok else None


_R = {}


def init_worker():
    import torch
    torch.set_num_threads(1)
    cv2.setNumThreads(1)
    import easyocr
    _R["ocr"] = easyocr.Reader(["en"], gpu=False, verbose=False)


def scan_clip(path):
    import imagehash
    from PIL import Image
    reader = _R["ocr"]
    name = os.path.basename(path)[:-4]
    spans, dur = shots_of(path)
    cap = cv2.VideoCapture(path)
    out = []
    for k, (a, b) in enumerate(spans):
        a2, b2 = a + 0.15, b - 0.15  # stay clear of the cut itself
        secs = np.arange(a2, b2 - 0.5, 1.0)
        hits, dark, still, frames = [], set(), set(), []
        for t in secs:
            f0, f1 = grab(cap, t), grab(cap, t + 0.5)
            if f0 is None or f1 is None:
                dark.add(round(t, 2))
                continue
            g0 = cv2.cvtColor(cv2.resize(f0, (256, 144)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            g1 = cv2.cvtColor(cv2.resize(f1, (256, 144)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            if g0.mean() < 3:
                dark.add(round(t, 2))
            if np.abs(g0 - g1).mean() < MOTION_MIN:
                still.add(round(t, 2))
            frames.append((t, f0))
        for t, f in frames[::int(TEXT_STEP)]:
            small = cv2.resize(f, (SW, SH))
            horiz, free = reader.detect(small, min_size=8, text_threshold=0.7, low_text=0.45)
            for x0, x1, y0, y1 in horiz[0]:
                hits.append((round(t, 2), (x0 / SW, y0 / SH, x1 / SW, y1 / SH)))
            for poly in free[0]:
                p = np.array(poly)
                hits.append((round(t, 2), (p[:, 0].min() / SW, p[:, 1].min() / SH, p[:, 0].max() / SW, p[:, 1].max() / SH)))
        crop, bad_text = best_crop(hits, len(secs))
        bad = set(dark) | set(still)
        for t in bad_text:
            bad.update(round(x, 2) for x in secs if abs(x - t) <= TEXT_STEP + 0.01)
        usable, run = [], None
        for t in secs:
            if round(t, 2) in bad:
                if run and run[1] - run[0] >= MIN_SHOT:
                    usable.append([round(run[0], 2), round(run[1], 2)])
                run = None
            else:
                run = [t, min(t + 1.0, b2)] if run is None else [run[0], min(t + 1.0, b2)]
        if run and run[1] - run[0] >= MIN_SHOT:
            usable.append([round(run[0], 2), round(run[1], 2)])
        mids = [f for _, f in frames] or [None]
        pick = [mids[int(i)] for i in np.linspace(0, len(mids) - 1, 3)] if mids[0] is not None else []
        ph = [str(imagehash.phash(Image.fromarray(cv2.cvtColor(cv2.resize(f, (320, 180)), cv2.COLOR_BGR2RGB)))) for f in pick]
        thumbs = [cv2.resize(f, (224, 126)) for f in pick]
        out.append({"id": f"{name}#{k}", "clip": name, "start": round(a, 2), "end": round(b, 2), "crop": crop,
                    "usable": usable, "text_secs": len(bad_text), "still_secs": len(still), "dark_secs": len(dark),
                    "phash": ph, "_thumbs": thumbs})
    cap.release()
    return name, out


def embed(shots, clips_dir):
    """CLIP image embedding per shot: mean of 3 frames inside its longest usable range (crop applied)."""
    import clip_model
    imgs, owners = [], []
    for i, s in enumerate(shots):
        if not s["usable"]:
            continue
        a, b = max(s["usable"], key=lambda r: r[1] - r[0])
        cap = cv2.VideoCapture(os.path.join(clips_dir, s["clip"] + ".mp4"))
        for t in np.linspace(a + 0.2, b - 0.2, 3):
            f = grab(cap, t)
            if f is None:
                continue
            if s["crop"]:
                x0, y0, x1, y1 = s["crop"]
                h, w = f.shape[:2]
                f = f[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
            imgs.append(cv2.cvtColor(cv2.resize(f, (384, 216)), cv2.COLOR_BGR2RGB))
            owners.append(i)
        cap.release()
    E = clip_model.embed_images(imgs)
    out = np.zeros((len(shots), E.shape[1] if len(E) else 512), np.float32)
    for e, i in zip(E, owners):
        out[i] += e
    n = np.linalg.norm(out, axis=1, keepdims=True)
    return out / np.maximum(n, 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    import imagehash
    clips_dir = os.path.join(a.lib, "clips")
    spath, epath = os.path.join(a.lib, "shots.json"), os.path.join(a.lib, "shots_emb.npz")
    shots = json.load(open(spath)) if os.path.exists(spath) else []
    done = {s["clip"] for s in shots}
    todo = [p for p in sorted(glob.glob(os.path.join(clips_dir, "*.mp4"))) if ".part" not in p and os.path.basename(p)[:-4] not in done]
    os.makedirs(os.path.join(a.lib, "shot_thumbs"), exist_ok=True)
    new = []
    with Pool(a.workers, initializer=init_worker) as pool:
        for k, (name, ss) in enumerate(pool.imap_unordered(scan_clip, todo)):
            for s in ss:
                th = s.pop("_thumbs")
                if th:
                    cv2.imwrite(os.path.join(a.lib, "shot_thumbs", s["id"].replace("#", "_") + ".jpg"), np.hstack(th), [cv2.IMWRITE_JPEG_QUALITY, 80])
            new += ss
            print(f"[{k + 1}/{len(todo)}] {name:40s} shots {len(ss):3d}  usable {sum(len(s['usable']) > 0 for s in ss):3d}", flush=True)
    # duplicates: same footage reused in another video (perceptual hash of 3 frames)
    allshots = shots + new
    seen = []
    for s in allshots:
        s.setdefault("dup_of", None)
        if not s["phash"] or s["dup_of"]:
            continue
        hs = [imagehash.hex_to_hash(h) for h in s["phash"]]
        for o, ohs in seen:
            if sum(min(h - oh for oh in ohs) <= 10 for h in hs) >= 2:
                s["dup_of"] = o
                break
        else:
            seen.append((s["id"], hs))
    old = dict(np.load(epath, allow_pickle=True)) if os.path.exists(epath) and shots else {}
    have = {i: e for i, e in zip(old.get("ids", []), old.get("emb", []))}
    need = [s for s in allshots if s["id"] not in have]
    if need:
        E = embed(need, clips_dir)
        have.update({s["id"]: e for s, e in zip(need, E)})
    ids = [s["id"] for s in allshots]
    np.savez(epath, ids=np.array(ids), emb=np.stack([have[i] for i in ids]))
    json.dump(allshots, open(spath, "w"), indent=1)
    ok = [s for s in allshots if s["usable"] and not s["dup_of"]]
    print(f"{len(allshots)} shots, {len(ok)} usable unique shots, {sum(1 for s in allshots if s['dup_of'])} duplicates")


if __name__ == "__main__":
    main()
