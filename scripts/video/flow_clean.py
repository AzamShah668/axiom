"""Remove the Gemini sparkle from a Google Flow clip (owner's verified box) and strip its audio.
1920x1080 landscape: box x 1685, y 850, w 110, h 115, OpenCV TELEA inpaint, radius 5 (scaled for other sizes).
The invisible SynthID mark is never touched; clips are never presented as filmed footage.
  python scripts/video/flow_clean.py in.mp4 out.mp4
"""
import subprocess, sys
import cv2, numpy as np

src, dst = sys.argv[1], sys.argv[2]
cap = cv2.VideoCapture(src)
fps, w, h = cap.get(cv2.CAP_PROP_FPS) or 24, int(cap.get(3)), int(cap.get(4))
sx, sy = w / 1920, h / 1080
x, y, bw, bh = int(1685 * sx), int(850 * sy), int(110 * sx), int(115 * sy)
mask = np.zeros((h, w), np.uint8)
mask[y:y + bh, x:x + bw] = 255
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                       "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
n = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    ff.stdin.write(cv2.inpaint(f, mask, 5, cv2.INPAINT_TELEA).tobytes())
    n += 1
ff.stdin.close(); ff.wait()
print(dst, n, "frames")
