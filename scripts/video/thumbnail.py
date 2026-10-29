"""Thumbnails, 1280x720.

  Science Time style: black left half with a huge rounded title, one space image on the right
    python thumbnail.py <image.jpg> <fonts_dir> <out.jpg> "10 FACTS" "about" "DARK MATTER" [--halo]
  Full-bleed hook (v3 packaging test): the image fills the frame, a 2-line hook bottom-left, *keyword* in yellow
    python thumbnail.py <image.jpg> <fonts_dir> <out.jpg> --fullbleed "A TEASPOON WEIGHS" "*1 BILLION TONS*" \
        [--label "NEUTRON STARS"] [--focus 0.65]   (focus = horizontal position of the subject, 0-1)
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1280, 720


def font(fonts, size, weight=700):
    f = ImageFont.truetype(f"{fonts}/Fredoka.ttf", size)
    try:
        f.set_variation_by_axes([weight, 100])
    except Exception:
        pass
    return f


def fit_size(fonts, text, max_w, start):
    s = start
    while s > 20 and font(fonts, s).getbbox(text)[2] > max_w:
        s -= 4
    return s


def anton(fonts, size):
    return ImageFont.truetype(f"{fonts}/Anton.ttf", size)


def fullbleed(img_path, fonts, out, line1, line2, label="", focus=0.62):
    """Full-bleed image, punchy grade, dark gradient bottom-left, white line + yellow keyword line."""
    im = Image.open(img_path).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x0 = int(np.clip(focus * im.width - W / 2, 0, im.width - W))
    im = im.crop((x0, (im.height - H) // 2, x0 + W, (im.height - H) // 2 + H))
    a = np.array(im, np.float32) / 255
    a = np.clip((a - 0.5) * 1.18 + 0.5, 0, 1) ** 0.95                        # contrast
    g = a.mean(2, keepdims=True)
    a = np.clip(g + (a - g) * 1.35, 0, 1)                                     # saturation
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    shade = np.clip(1 - xx / (W * 0.75), 0, 1) ** 1.3 * 0.75 + np.clip((yy - H * 0.35) / (H * 0.65), 0, 1) ** 1.5 * 0.55
    a *= (1 - np.clip(shade, 0, 0.88))[..., None]
    canvas = Image.fromarray((a * 255).astype(np.uint8))
    d = ImageDraw.Draw(canvas)
    key = line2.startswith("*") and line2.endswith("*")
    line2 = line2.strip("*")
    max_w = int(W * 0.62)
    s1 = 120
    while s1 > 40 and anton(fonts, s1).getbbox(line1)[2] > max_w:
        s1 -= 4
    s2 = 190
    while s2 > 40 and anton(fonts, s2).getbbox(line2)[2] > max_w:
        s2 -= 4
    x, y2 = 56, H - 60 - s2
    y1 = y2 - int(s1 * 1.08)
    for (txt, sz, yy_, col) in ((line1, s1, y1, (255, 255, 255)), (line2, s2, y2, (255, 212, 0) if key else (255, 255, 255))):
        f = anton(fonts, sz)
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).text((x + 5, yy_ + 7), txt, font=f, fill=200)
        canvas.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(9)))
        d.text((x, yy_), txt, font=f, fill=col)
    if label:
        fl = ImageFont.truetype(f"{fonts}/Montserrat.ttf", 34)
        try:
            fl.set_variation_by_name("ExtraBold")
        except Exception:
            pass
        lab = " ".join(label.upper())
        bw = fl.getbbox(lab)[2]
        d.rectangle([(48, 44), (48 + bw + 36, 44 + 58)], fill=(255, 255, 255))
        d.text((48 + 18, 44 + 9), lab, font=fl, fill=(10, 10, 10))
    canvas.save(out, quality=92)
    print("wrote", out)


def main():
    if "--fullbleed" in sys.argv:
        args = [x for x in sys.argv[1:] if x != "--fullbleed"]
        label = args[args.index("--label") + 1] if "--label" in args else ""
        focus = float(args[args.index("--focus") + 1]) if "--focus" in args else 0.62
        pos = [x for i, x in enumerate(args) if not x.startswith("--") and (i == 0 or args[i - 1] not in ("--label", "--focus"))]
        return fullbleed(pos[0], pos[1], pos[2], pos[3], pos[4], label, focus)
    img_path, fonts, out, top, mid, bottom = sys.argv[1:7]
    halo = "--halo" in sys.argv
    canvas = Image.new("RGB", (W, H), "black")
    im = Image.open(img_path).convert("RGB")
    s = max(720 / im.height, 760 / im.width)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    im = im.crop(((im.width - 760) // 2, (im.height - 720) // 2, (im.width - 760) // 2 + 760, (im.height - 720) // 2 + 720))
    if halo:
        g = Image.new("RGB", im.size, (0, 0, 0))
        yy, xx = np.mgrid[0:720, 0:760]
        d = np.sqrt((xx - 380) ** 2 + (yy - 360) ** 2) / 360
        a = np.clip(1 - d, 0, 1) ** 1.3 * 0.75
        glow = (np.array([200, 90, 255])[None, None] * a[..., None]).astype(np.float32)
        im = Image.fromarray(np.clip(np.array(im, np.float32) + glow, 0, 255).astype(np.uint8))
    mask = Image.fromarray((np.clip(np.linspace(0, 1.6, 760), 0, 1)[None, :].repeat(720, 0) * 255).astype(np.uint8))
    canvas.paste(im, (W - 760, 0), mask)
    d = ImageDraw.Draw(canvas)
    left_w = 600
    s_top = fit_size(fonts, top, left_w, 150)
    s_bot = fit_size(fonts, bottom, left_w, 150)
    f_top, f_bot, f_mid = font(fonts, s_top), font(fonts, s_bot), font(fonts, 46, 500)
    cx = 40 + left_w // 2
    y = 360 - (s_top + s_bot + 70) // 2
    d.text((cx, y), top, font=f_top, fill="white", anchor="mt")
    y += int(s_top * 1.05)
    d.text((cx, y + 4), mid, font=f_mid, fill="white", anchor="mt")
    mw = f_mid.getbbox(mid)[2]
    for sgn in (-1, 1):
        x0 = cx + sgn * (mw // 2 + 18)
        d.line([(x0, y + 30), (x0 + sgn * 70, y + 30)], fill="white", width=4)
    y += 70
    d.text((cx, y), bottom, font=f_bot, fill="white", anchor="mt")
    canvas.save(out, quality=92)
    print("wrote", out)


if __name__ == "__main__":
    main()
