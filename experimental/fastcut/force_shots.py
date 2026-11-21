"""Give deliberately chosen short clips (our motion graphics with labels, sub-2 s film clips) one whole-clip shot with an
embedding, so a pin can place them. Uses build_shots.embed read-only.
  python experimental/fastcut/force_shots.py <lib> <clip> [<clip> ...]
"""
import json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "footage"))
import build_shots  # noqa: E402

lib, clips = sys.argv[1], sys.argv[2:]
spath, epath = os.path.join(lib, "shots.json"), os.path.join(lib, "shots_emb.npz")
shots = json.load(open(spath))
z = dict(np.load(epath, allow_pickle=True)); emb = dict(zip(z["ids"], z["emb"]))
shots = [s for s in shots if s["clip"] not in clips]
new = []
for c in clips:
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              os.path.join(lib, "clips", c + ".mp4")], capture_output=True, text=True).stdout)
    new.append({"id": f"{c}#0", "clip": c, "start": 0.0, "end": round(d, 2), "crop": None, "usable": [[0.0, round(d - 0.05, 2)]],
                "text_secs": 0, "still_secs": 0, "dark_secs": 0, "phash": [], "luma": 60.0, "dup_of": None})
E = build_shots.embed(new, os.path.join(lib, "clips"))
for s, e in zip(new, E):
    emb[s["id"]] = e
shots += new
ids = [s["id"] for s in shots]
np.savez(epath, ids=np.array(ids), emb=np.stack([emb[i] for i in ids]))
json.dump(shots, open(spath, "w"), indent=1)
print("forced", len(new), "shots")
