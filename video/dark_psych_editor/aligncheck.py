"""Check that hard cuts in a rendered part land on their scheduled frames."""
import json, subprocess, sys
import numpy as np
part, A = sys.argv[1], int(sys.argv[2])
e = json.load(open('remotion/src/edit.json'))
W, H = 96, 54
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', part, '-vf', 'scale=%d:%d,format=gray' % (W, H), '-f', 'rawvideo', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
res = {}
for s in e['scenes']:
    F = s['from']; k = F - A
    if s['kind'] not in ('media', 'word', 'gfx', 'card') or k < 2 or k + 2 >= len(fr): continue
    d = {o: float(np.abs(fr[k + o] - fr[k + o - 1]).mean()) for o in (-1, 0, 1)}
    if max(d.values()) < 15: continue
    res[F] = max(d, key=d.get)
bad = [(F, round(F / 30, 2), o) for F, o in res.items() if o != 0]
print('%s: %d frames, %d decisive cuts, %d aligned, off: %s' % (part.split('/')[-1], len(fr), len(res), len(res) - len(bad), bad[:8]))
