"""Contact sheets of a rendered video for review: one frame every N seconds, 30 frames per sheet.

  python review_sheet.py <video.mp4> <out_dir> [--every 6]

Look for: text or logos inside footage, white/black frames, captions clashing with graphics, repeated shots.
"""
import argparse, glob, os, subprocess
import numpy as np, cv2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=6.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for f in glob.glob(os.path.join(a.out, "f_*.jpg")):
        os.remove(f)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", f"fps=1/{a.every},scale=320:180",
                    os.path.join(a.out, "f_%04d.jpg")], check=True)
    fs = sorted(glob.glob(os.path.join(a.out, "f_*.jpg")))
    flags = []
    for k in range(0, len(fs), 30):
        ims = []
        for f in fs[k:k + 30]:
            im = cv2.imread(f)
            n = int(os.path.basename(f)[2:6])
            t = (n - 1) * a.every + a.every / 2
            if im.mean() > 170 or im.mean() < 4:
                flags.append(round(t))
            cv2.putText(im, f"{int(t // 60)}:{int(t % 60):02d}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            ims.append(im)
        while len(ims) % 5:
            ims.append(np.zeros_like(ims[0]))
        cv2.imwrite(os.path.join(a.out, f"sheet_{k // 30:02d}.jpg"),
                    np.vstack([np.hstack(ims[i:i + 5]) for i in range(0, len(ims), 5)]), [cv2.IMWRITE_JPEG_QUALITY, 75])
    print(f"{len(fs)} frames -> {(len(fs) + 29) // 30} sheets in {a.out}; near-white/black frames at {flags or 'none'}")


if __name__ == "__main__":
    main()
