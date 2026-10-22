"""Rank footage for a Short's spoken hook: shots that match the hook AND move a lot (the first seconds must not
look frozen). Writes a numbered contact sheet; put the chosen ids in the spec's `hook_shots:` line.

  python hook_shots.py <library_dir> <out.jpg> --q "a star torn apart by a black hole" [--q ...]
                       [--clips-from cutlist.json] [--skip short.plan.json] [--n 24]

--clips-from limits the pool to clips a published video used; --skip leaves out shots the Short already shows.
Score = CLIP match x motion; motion = mean optical-flow speed (px/frame at 320 px wide) over the shot's best 3 s.
"""
import argparse, json, os, sys

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "footage"))
import clip_model  # noqa: E402


def motion(path, a, b, win=3.0):
    """(speed, start of the best `win` seconds) of the clip between a and b: mean optical-flow magnitude."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    cap.set(cv2.CAP_PROP_POS_MSEC, a * 1000)
    step, prev, sp, ts = max(1, round(fps / 8)), None, [], []
    n = 0
    while n <= (b - a) * fps:
        ok, f = cap.read()
        if not ok:
            break
        if n % step == 0:
            g = cv2.cvtColor(cv2.resize(f, (320, int(320 * f.shape[0] / f.shape[1]))), cv2.COLOR_BGR2GRAY)
            if prev is not None:
                fl = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                sp.append(float(np.linalg.norm(fl, axis=2).mean()) / step)
                ts.append(a + n / fps)
            prev = g
        n += 1
    if not sp:
        return 0.0, a
    k = max(1, int(win * 8))
    roll = np.convolve(sp, np.ones(k) / k, "valid") if len(sp) >= k else np.array([np.mean(sp)])
    i = int(np.argmax(roll))
    return float(roll[i]), max(a, ts[i] - 1 / 8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("out")
    ap.add_argument("--q", action="append", required=True)
    ap.add_argument("--clips-from", default="")
    ap.add_argument("--skip", default="")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--top-clip", type=int, default=60, help="measure motion of this many best CLIP matches")
    a = ap.parse_args()
    shots = [s for s in json.load(open(os.path.join(a.lib, "shots.json"))) if s["usable"] and not s["dup_of"]]
    shots = [s for s in shots if os.path.exists(os.path.join(a.lib, "clips", s["clip"] + ".mp4"))]
    if a.clips_from:
        own = {it["clip"] for it in json.load(open(a.clips_from))["items"] if it.get("clip")}
        shots = [s for s in shots if s["clip"] in own]
    if a.skip:
        used = {it["clip"].split("@")[0] for it in json.load(open(a.skip))["items"] if it.get("clip")}
        shots = [s for s in shots if s["clip"] not in used]
    z = np.load(os.path.join(a.lib, "shots_emb.npz"), allow_pickle=True)
    emb = dict(zip(z["ids"], z["emb"]))
    shots = [s for s in shots if s["id"] in emb]
    E = np.stack([emb[s["id"]] for s in shots])
    Q = clip_model.embed_texts([f"a photo of {q}" for q in a.q])
    sim = (E @ Q.T).max(1)
    order = np.argsort(-sim)[:a.top_clip]
    rows = []
    for i in order:
        s = shots[i]
        x0, x1 = max(s["usable"], key=lambda r: r[1] - r[0])
        sp, t = motion(os.path.join(a.lib, "clips", s["clip"] + ".mp4"), x0, x1)  # usable = clip seconds
        rows.append((float(sim[i]) * min(sp, 3.0) ** 0.5, float(sim[i]), sp, t, s))
    rows.sort(key=lambda r: -r[0])
    rows = rows[:a.n]
    tiles = []
    for k, (score, cs, sp, t, s) in enumerate(rows):
        cap = cv2.VideoCapture(os.path.join(a.lib, "clips", s["clip"] + ".mp4"))
        cap.set(cv2.CAP_PROP_POS_MSEC, (t + 1.0) * 1000)
        ok, f = cap.read()
        f = cv2.resize(f if ok else np.zeros((180, 320, 3), np.uint8), (320, 180))
        f = np.vstack([f, np.zeros((40, 320, 3), np.uint8)])
        cv2.putText(f, f"{k} {s['id'][:30]}", (4, 196), 0, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(f, f"clip {cs:.2f}  motion {sp:.2f}  @{t:.1f}s", (4, 214), 0, 0.42, (0, 220, 255), 1, cv2.LINE_AA)
        tiles.append(f)
        print(f"{k:2d} {s['id']:34s} clip {cs:.3f} motion {sp:5.2f} best@{t:5.1f}s  score {score:.3f}")
    while len(tiles) % 6:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(a.out, np.vstack([np.hstack(tiles[r:r + 6]) for r in range(0, len(tiles), 6)]))


if __name__ == "__main__":
    main()
