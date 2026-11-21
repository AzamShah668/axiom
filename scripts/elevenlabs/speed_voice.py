"""Make a full video's voice play at another speed (owner picks 1.0x or 1.1x per video at the end; 10 chose 1.1x).
Time-stretches narration.wav (pitch kept) and scales every time in timeline.json, keeping the originals as
narration_1.0x.wav / timeline_1.0x.json so it can be redone at any speed.

  python scripts/elevenlabs/speed_voice.py work/NN-slug/voice 1.1
"""
import json, os, shutil, subprocess, sys

d, speed = sys.argv[1], float(sys.argv[2])
wav, tl = os.path.join(d, "narration.wav"), os.path.join(d, "timeline.json")
w0, t0 = os.path.join(d, "narration_1.0x.wav"), os.path.join(d, "timeline_1.0x.json")
if not os.path.exists(w0):
    shutil.copy(wav, w0)
    shutil.copy(tl, t0)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", w0, "-af", f"atempo={speed}", "-ar", "44100", "-ac", "1", wav], check=True)
t = json.load(open(t0))
k = 1 / speed
t["total"] = round(t["total"] * k, 3)
for s in t["sections"]:
    s["start"], s["end"] = round(s["start"] * k, 3), round(s["end"] * k, 3)
    s["char_start"] = [round(x * k, 3) for x in s["char_start"]]
for b in t.get("bites", []):
    for key in ("at", "start", "end", "t"):
        if isinstance(b.get(key), (int, float)):
            b[key] = round(b[key] * k, 3)
t["speed"] = speed
json.dump(t, open(tl, "w"), ensure_ascii=False)
print(f"{wav} and {tl} now at {speed}x ({t['total']:.1f} s); originals kept as *_1.0x")
