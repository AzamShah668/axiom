"""Scan footage proxies for burned-in text / logos and black frames; output usable clean ranges.

  python clip_qc.py <clips_dir> <out_dir> [--workers 3]

For each <name>.mp4 (1080p proxy): samples 1 frame every 2 s, runs the CRAFT text detector (EasyOCR,
detection only) and a black-frame check. When the text sits only in a corner or band (credit labels,
captions), an auto-crop (16:9, zoom <= 1.33x) that cuts it out is chosen and those seconds count as clean.
Seconds with text inside the crop (+/-1 s margin) or black frames are excluded.
Writes <out_dir>/catalog.json {name: {"dur", "crop": [x0, y0, x1, y1] | null, "clean": [[a, b], ...],
"text_secs", "dark_secs"}} and <out_dir>/strips/<name>.jpg (8 thumbnails; red border = text in frame,
grey = black, green box = crop). The renderer applies "crop" from the catalog.
Already-scanned clips are kept (delete an entry to rescan).
"""
import argparse, glob, json, os
from multiprocessing import Pool
import numpy as np, cv2

MIN_CLEAN = 1.5
STEP = 2  # seconds between sampled frames
SW, SH = 512, 288


def best_crop(hits, secs):
    """Pick the 16:9 crop (anchored at a corner, edge or the centre) that leaves the fewest text seconds."""
    best, best_score, best_bad = None, None, None
    for s in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75):
        anchors = [(0, 0)] if s == 1.0 else [(ax, ay) for ax in (0, 0.5, 1) for ay in (0, 0.5, 1)]
        for ax, ay in anchors:
            x0, y0 = ax * (1 - s), ay * (1 - s)
            x1, y1 = x0 + s, y0 + s
            bad = {t for t, (a, b, c, d) in hits if a < x1 and c > x0 and b < y1 and d > y0}
            score = len(bad) + (1 - s) * secs * 0.25  # small penalty for zooming in
            if best_score is None or score < best_score - 1e-6:
                best = None if s == 1.0 else [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]
                best_score, best_bad = score, bad
    return best, best_bad


def scan(path):
    import torch
    torch.set_num_threads(1)
    import easyocr
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur = n / fps
    secs = int(dur)
    hits, dark, thumbs = [], set(), []
    for s in range(0, secs, STEP):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int((s + 0.5) * fps))
        ok, fr = cap.read()
        if not ok:
            dark.add(s)
            continue
        small = cv2.resize(fr, (SW, SH))
        if small.mean() < 3:  # black / fade (dark star fields are fine)
            dark.update(range(s, s + STEP))
        else:
            horiz, free = reader.detect(small, min_size=8, text_threshold=0.7, low_text=0.45)
            for x0, x1, y0, y1 in horiz[0]:
                hits.append((s, (x0 / SW, y0 / SH, x1 / SW, y1 / SH)))
            for poly in free[0]:
                p = np.array(poly)
                hits.append((s, (p[:, 0].min() / SW, p[:, 1].min() / SH, p[:, 0].max() / SW, p[:, 1].max() / SH)))
        thumbs.append((s, cv2.resize(fr, (240, 135))))
    crop, bad_s = best_crop(hits, secs)
    text = set()
    for s in bad_s:
        text.update(range(max(0, s - 1), s + STEP + 1))  # +/- margin around a hit
    bad = sorted(text | dark)
    clean, start = [], 0.0
    for b in bad + [secs + 1]:
        a, z = start, min(b, dur - 0.2)
        if z - a >= MIN_CLEAN:
            clean.append([round(a, 2), round(z, 2)])
        start = b + 1.0
    # thumbnail strip
    hit_s = {s for s, _ in hits}
    pick = [thumbs[int(i)] for i in np.linspace(0, len(thumbs) - 1, min(8, len(thumbs)))] if thumbs else []
    tiles = []
    for s, im in pick:
        im = im.copy()
        col = (0, 0, 255) if s in hit_s else (128, 128, 128) if s in dark else None
        if col:
            cv2.rectangle(im, (0, 0), (239, 134), col, 6)
        if crop:
            cv2.rectangle(im, (int(crop[0] * 240), int(crop[1] * 135)), (int(crop[2] * 240) - 1, int(crop[3] * 135) - 1), (0, 255, 0), 2)
        cv2.putText(im, f"{s}s", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        tiles.append(im)
    strip = np.hstack(tiles) if tiles else np.zeros((135, 240, 3), np.uint8)
    info = {"dur": round(dur, 2), "crop": crop, "clean": clean, "text_secs": len(text), "dark_secs": len(dark)}
    return os.path.basename(path)[:-4], info, strip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "strips"), exist_ok=True)
    cpath = os.path.join(a.out, "catalog.json")
    cat = json.load(open(cpath)) if os.path.exists(cpath) else {}
    todo = [p for p in sorted(glob.glob(os.path.join(a.clips, "*.mp4")))
            if ".part" not in p and os.path.basename(p)[:-4] not in cat]
    with Pool(a.workers) as pool:
        for name, info, strip in pool.imap_unordered(scan, todo):
            cat[name] = info
            cv2.imwrite(os.path.join(a.out, "strips", f"{name}.jpg"), strip, [cv2.IMWRITE_JPEG_QUALITY, 80])
            json.dump(cat, open(cpath, "w"), indent=1)
            usable = sum(b - a_ for a_, b in info["clean"])
            print(f"{name:40s} dur {info['dur']:6.1f}  text {info['text_secs']:3d}s  dark {info['dark_secs']:3d}s  "
                  f"usable {usable:6.1f}s  crop {info['crop']}", flush=True)


if __name__ == "__main__":
    main()
