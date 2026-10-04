"""Flag media scenes whose imagery (outside the caption band) is nearly black."""
import json, subprocess, sys
import numpy as np
part, first = sys.argv[1], int(sys.argv[2])
W, H, STEP = 192, 108, 6
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', part, '-vf', "select='not(mod(n\\,%d))',scale=%d:%d,format=gray" % (STEP, W, H),
                      '-vsync', '0', '-f', 'rawvideo', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
bands = np.concatenate([fr[:, :int(H * .38), :], fr[:, int(H * .62):, :]], axis=1).reshape(len(fr), -1)
p90 = np.percentile(bands, 90, axis=1)
e = json.load(open('remotion/src/edit.json'))
for s in e['scenes']:
    if s['kind'] != 'media': continue
    a, b = s['from'] - first, s['from'] + s['dur'] - first
    idx = [k for k in range(len(fr)) if a <= k * STEP < b]
    if idx and p90[idx].max() < 40:
        print('%7.2fs  p90=%5.1f  grade=%-5s %s' % (s['from'] / 30, p90[idx].max(), s.get('grade'), s['src']))
print('frames sampled:', len(fr))
