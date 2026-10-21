"""Contact sheets of a rendered video for review.

  python review_sheet.py <video.mp4> <out_dir> [--every 6]              one frame every N seconds, 30 per sheet
  python review_sheet.py <video.mp4> <out_dir> --cutlist cutlist.json   one frame per item (its middle), 24 per sheet,
                                                                         labelled "<n> <section>/<k> <kind> m:ss"

Per-item sheets show every shot as rendered (grade, move, overlays), so nothing hides between two samples.
Look for: text or logos inside footage, white/black frames, insets/split screens/mosaic edges, overlays running
over a card or a graphic, captions clashing with graphics, shapes that read as something silly, repeated shots.
"""
import argparse, glob, json, os, subprocess
import numpy as np, cv2


def flag(im, t, flags):
    if im.mean() > 170 or im.mean() < 4:
        flags.append(round(t))


def write_sheets(ims, out, per, cols, quality):
    for k in range(0, len(ims), per):
        page = ims[k:k + per]
        while len(page) % cols:
            page.append(np.zeros_like(ims[0]))
        cv2.imwrite(os.path.join(out, f"sheet_{k // per:02d}.jpg"),
                    np.vstack([np.hstack(page[i:i + cols]) for i in range(0, len(page), cols)]), [cv2.IMWRITE_JPEG_QUALITY, quality])
    return (len(ims) + per - 1) // per


def per_item(video, out, cutlist):
    items = json.load(open(cutlist))["items"]
    cap = cv2.VideoCapture(video)
    ims, flags, seen = [], [], {}
    for n, it in enumerate(items):
        k = seen[it["sec"]] = seen.get(it["sec"], -1) + 1
        t = (it["t0"] + it["t1"]) / 2
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, im = cap.read()
        if not ok:
            continue
        im = cv2.resize(im, (480, 270))
        flag(im, t, flags)
        cv2.rectangle(im, (0, 0), (480, 22), (0, 0, 0), -1)
        cv2.putText(im, f"{n} {it['sec']}/{k} {it['kind']} {int(t // 60)}:{t % 60:04.1f}", (4, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        ims.append(im)
    return len(ims), write_sheets(ims, out, 24, 4, 85), flags


def every(video, out, step):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps=1/{step},scale=320:180",
                    os.path.join(out, "f_%04d.jpg")], check=True)
    fs = sorted(glob.glob(os.path.join(out, "f_*.jpg")))
    ims, flags = [], []
    for f in fs:
        im = cv2.imread(f)
        t = (int(os.path.basename(f)[2:6]) - 1) * step + step / 2
        flag(im, t, flags)
        cv2.putText(im, f"{int(t // 60)}:{int(t % 60):02d}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        ims.append(im)
    return len(ims), write_sheets(ims, out, 30, 5, 75), flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=6.0)
    ap.add_argument("--cutlist", default="", help="one frame per item of this cutlist instead of a fixed step")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for f in glob.glob(os.path.join(a.out, "f_*.jpg")) + glob.glob(os.path.join(a.out, "sheet_*.jpg")):
        os.remove(f)
    n, sheets, flags = per_item(a.video, a.out, a.cutlist) if a.cutlist else every(a.video, a.out, a.every)
    print(f"{n} frames -> {sheets} sheets in {a.out}; near-white/black frames at {flags or 'none'}")


if __name__ == "__main__":
    main()
