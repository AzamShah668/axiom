"""Raw cut for the owner's approval (Flow rulebook, step 4): every clip trimmed to its exact voice window, the full
voice underneath, no captions, no grade, no music, no polish. Where a photo, graphic or chapter card will go, a plain
dark card names it, so placement and timing can be judged before the full render.

  python scripts/video/raw_cut.py work/NN-slug/cutlist.json work/NN-slug/voice/narration.wav out.mp4 [--lib work/library] [--lead 0.5]
"""
import json, os, subprocess, sys, tempfile

a = sys.argv[1:]
cut, voice, out = a[:3]
lib = a[a.index("--lib") + 1] if "--lib" in a else "work/library"
W, H, FPS = 1280, 720, 30
items = json.load(open(cut))["items"]
tmp = tempfile.mkdtemp(prefix="rawcut-")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def esc(s):
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "").replace("%", "\\%").replace(",", "\\,")


def dur_of(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout or 0)


parts = []
for k, it in enumerate(items):
    d = it["t1"] - it["t0"]
    seg = os.path.join(tmp, f"{k:04d}.mp4")
    label = None
    if it["kind"] == "card":
        label = "CHAPTER CARD"
    elif it["kind"] == "gfx":
        g = it.get("gfx", "")
        label = ("PHOTO: " + g.split(":", 1)[1]) if g.startswith("photo:") else ("GRAPHIC: " + g.split(";")[0])
    clip = os.path.join(lib, "clips", (it.get("clip") or "") + ".mp4")
    tag = f"{it.get('ref', '')}  {'FLOW ' + it['clip'][7:] if str(it.get('clip', '')).startswith('flow10_') else ''}"
    if label or not os.path.exists(clip):
        label = label or "MISSING CLIP"
        vf = (f"drawtext=fontfile={FONT}:text='{esc(label[:60])}':fontcolor=white:fontsize=40:x=(w-tw)/2:y=(h-th)/2,"
              f"drawtext=fontfile={FONT}:text='{esc(tag)}':fontcolor=yellow:fontsize=22:x=20:y=20")
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x101418:s={W}x{H}:r={FPS}", "-t", f"{d:.3f}",
               "-vf", vf]
    else:
        ss = float(it.get("ss") or 0)
        avail = max(0.1, dur_of(clip) - ss)
        slow = max(1.0, d / avail)                       # a slightly short clip plays a little slower, never looped
        crop = it.get("crop")
        cf = f"crop=iw*{crop[2]-crop[0]}:ih*{crop[3]-crop[1]}:iw*{crop[0]}:ih*{crop[1]}," if crop else ""
        vf = (f"{cf}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts={slow:.4f}*PTS,fps={FPS},"
              f"drawtext=fontfile={FONT}:text='{esc(tag)}':fontcolor=yellow:fontsize=22:x=20:y=20")
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", clip, "-t", f"{d:.3f}", "-an", "-vf", vf]
    cmd += ["-frames:v", str(max(1, round(d * FPS))), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", seg]
    subprocess.run(cmd, check=True)
    parts.append(seg)
with open(os.path.join(tmp, "list.txt"), "w") as f:
    f.writelines(f"file '{p}'\n" for p in parts)
vid = os.path.join(tmp, "video.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy", vid], check=True)
lead = float(a[a.index("--lead") + 1]) if "--lead" in a else 0.5   # edit.base "lead_in": the voice starts this late
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-itsoffset", f"{lead:.3f}", "-i", voice, "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
print("wrote", out, f"{len(items)} items, {dur_of(out):.1f} s")
