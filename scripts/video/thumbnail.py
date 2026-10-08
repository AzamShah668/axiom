"""Science-Time-style thumbnail: black left half with huge rounded title, one space image on the right.

  python thumbnail.py <image.jpg> <fonts_dir> <out.jpg> "10 FACTS" "about" "DARK MATTER" [--halo]
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


def main():
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
