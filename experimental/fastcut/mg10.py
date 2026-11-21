"""Custom motion graphics for the fast-cut 10 (separate project). Each renders a short 1920x1080/30 fps clip in our
documentary look (dark space, amber accents, Anton/Montserrat), placed into the edit like a Flow clip.
  python experimental/fastcut/mg10.py <out_dir> [name ...]
"""
import math, os, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
FONTS = "/home/user/axiom/work/media/fonts"
AMBER, WHITE, BLUE, RED, GREY = (66, 194, 245), (245, 245, 245), (255, 190, 110), (70, 70, 230), (150, 150, 150)
rng = np.random.default_rng(3)
STARS = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.3, 1.0)) for _ in range(500)]
_F = {}


def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = cl(x); return x * x * (3 - 2 * x)
def eo(x): x = cl(x); return 1 - (1 - x) ** 3


def font(name, size):
    k = (name, size)
    if k not in _F:
        _F[k] = ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), size)
    return _F[k]


_BG = {}


def bg(t):
    if "base" not in _BG:
        yy, xx = np.mgrid[0:H, 0:W]
        _BG["base"] = ((np.exp(-(((xx - W / 2) / 900) ** 2 + ((yy - H / 2) / 600) ** 2)) * 22)[..., None]
                       * np.array([1.0, 0.6, 0.35])).astype(np.float32)
    f = _BG["base"].copy()
    for x, y, b in STARS:
        tw = 0.6 + 0.4 * math.sin(t * 2 + x)
        xi, yi = int((x + t * 6) % W), int(y)
        f[yi, xi] = 255 * b * tw
    return f


def glow(f, x, y, r, col, amt):
    r = max(1.0, r); pad = int(r * 3.5)
    xa, ya, xb, yb = max(0, int(x) - pad), max(0, int(y) - pad), min(W, int(x) + pad), min(H, int(y) + pad)
    if xa >= xb or ya >= yb: return
    lay = np.zeros((yb - ya, xb - xa, 3), np.float32)
    cv2.circle(lay, (int(x) - xa, int(y) - ya), int(r), col, -1, cv2.LINE_AA)
    f[ya:yb, xa:xb] += cv2.GaussianBlur(lay, (0, 0), max(1, r * 0.8)) * amt


_TX = {}


def text(f, s, x, y, size, col=WHITE, fnt="Anton", alpha=1.0, anchor="mm"):
    if alpha <= 0.01: return
    k = (s, size, fnt)
    if k not in _TX:   # rasterise each string once, as a tight alpha mask
        fo = font(fnt, size)
        l, tp, r, b = fo.getbbox(s, anchor="lt")
        im = Image.new("L", (r - l + 4, b - tp + 4), 0)
        ImageDraw.Draw(im).text((2 - l, 2 - tp), s, font=fo, fill=255, anchor="lt")
        _TX[k] = np.asarray(im, np.float32) / 255.0
    m = _TX[k]; h, w = m.shape
    x0 = int(x - w / 2) if anchor[0] == "m" else int(x - w) if anchor[0] == "r" else int(x)
    y0 = int(y - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    a = (m[ya - y0:yb - y0, xa - x0:xb - x0] * alpha)[..., None]
    f[ya:yb, xa:xb] = f[ya:yb, xa:xb] * (1 - a) + np.array(col, np.float32) * a


def arrow(f, p0, p1, col, th=6):
    cv2.arrowedLine(f, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), col, th, cv2.LINE_AA, tipLength=0.3)


# ------------------------------------------------------------------ the graphics (t in seconds, D = length)
def bh_vs_wh(t, D):
    f = bg(t)
    a = eo(t / 0.4)
    lx, rx, cy = W * 0.28, W * 0.72, H * 0.48
    # black hole: dark disc, ring, arrows flowing IN
    glow(f, lx, cy, 150, (60, 120, 240), 0.5 * a)
    cv2.circle(f, (int(lx), int(cy)), 120, (0, 0, 0), -1, cv2.LINE_AA)
    cv2.circle(f, (int(lx), int(cy)), 126, (90, 170, 255), 4, cv2.LINE_AA)
    # white hole: bright core, arrows flowing OUT
    glow(f, rx, cy, 170, (230, 240, 255), 1.4 * a)
    cv2.circle(f, (int(rx), int(cy)), 95, (250, 250, 255), -1, cv2.LINE_AA)
    for k in range(10):
        ang = k * 2 * math.pi / 10
        c, s = math.cos(ang), math.sin(ang)
        ph = (t * 0.9 + k * 0.13) % 1.0
        r_in0, r_in1 = 380 - 230 * ph, 330 - 230 * ph
        arrow(f, (lx + c * r_in0, cy + s * r_in0), (lx + c * max(135, r_in1), cy + s * max(135, r_in1)), AMBER, 5)
        r_o0, r_o1 = 115 + 230 * ph, 165 + 230 * ph
        arrow(f, (rx + c * r_o0, cy + s * r_o0), (rx + c * r_o1, cy + s * r_o1), WHITE, 5)
    text(f, "BLACK HOLE", lx, H * 0.85, 64, AMBER, "Anton", a)
    text(f, "EVERYTHING GOES IN", lx, H * 0.92, 34, WHITE, alpha=a)
    text(f, "WHITE HOLE", rx, H * 0.85, 64, WHITE, "Anton", ease((t - 0.5) / 0.3))
    text(f, "EVERYTHING COMES OUT", rx, H * 0.92, 34, WHITE, alpha=ease((t - 0.5) / 0.3))
    return f


def kruskal(t, D):
    f = bg(t)
    cx, cy, R = W / 2, H * 0.47, 330
    pts = {"top": (cx, cy - R), "bot": (cx, cy + R), "l": (cx - R * 1.6, cy), "r": (cx + R * 1.6, cy)}
    p = eo(t / 0.8)
    # the diamond map drawn in, then its four regions labelled
    for a_, b_ in (("l", "top"), ("top", "r"), ("r", "bot"), ("bot", "l")):
        x0, y0 = pts[a_]; x1, y1 = pts[b_]
        cv2.line(f, (int(x0), int(y0)), (int(x0 + (x1 - x0) * p), int(y0 + (y1 - y0) * p)), GREY, 3, cv2.LINE_AA)
    cv2.line(f, (int(cx - R * 0.8), int(cy - R / 2)), (int(cx + R * 0.8), int(cy + R / 2)), (110, 110, 110), 2, cv2.LINE_AA)
    cv2.line(f, (int(cx - R * 0.8), int(cy + R / 2)), (int(cx + R * 0.8), int(cy - R / 2)), (110, 110, 110), 2, cv2.LINE_AA)
    sing = ease((t - 0.6) / 0.4)
    for yy in (cy - R * 0.62, cy + R * 0.62):  # singularities (wiggly lines)
        xs = np.linspace(cx - R * 0.75, cx + R * 0.75, 60)
        ys = yy + 6 * np.sin(xs / 12)
        cv2.polylines(f, [np.stack([xs, ys], 1).astype(np.int32)], False, (int(80 * sing), int(80 * sing), int(255 * sing)), 3, cv2.LINE_AA)
    lab = ease((t - 0.9) / 0.3)
    text(f, "OUR UNIVERSE", cx + R * 0.95, cy, 34, WHITE, alpha=lab)
    text(f, "ANOTHER UNIVERSE", cx - R * 0.95, cy, 34, GREY, alpha=lab)
    text(f, "BLACK HOLE", cx, cy - R * 0.33, 40, AMBER, "Anton", lab)
    wh = ease((t - 1.8) / 0.4)  # the hidden second part lights up
    glow(f, cx, cy + R * 0.35, 120, (230, 240, 255), 1.3 * wh)
    text(f, "WHITE HOLE", cx, cy + R * 0.33, 46, WHITE, "Anton", max(lab * 0.35, wh))
    text(f, "KRUSKAL-SZEKERES MAP, 1960", cx, H * 0.92, 32, GREY, alpha=lab)
    return f


def timeline(t, D):
    f = bg(t)
    years = [1915, 1960, 1964, 1974, 2006, 2011, 2014, 2018]
    x0, x1, y = 170, W - 170, H * 0.55
    xs = {yv: x0 + (x1 - x0) * (yv - 1915) / (2018 - 1915) for yv in years}
    p = eo(t / 0.7)
    cv2.line(f, (x0, int(y)), (int(x0 + (x1 - x0) * p), int(y)), GREY, 4, cv2.LINE_AA)
    for k, yv in enumerate(years):
        a = ease((t - 0.15 - 0.07 * k) / 0.2)
        if a <= 0: continue
        cv2.circle(f, (int(xs[yv]), int(y)), 9, AMBER if yv in (1974, 2006) else WHITE, -1, cv2.LINE_AA)
        text(f, str(yv), xs[yv], y + (60 if k % 2 == 0 else -60), 38, AMBER if yv in (1974, 2006) else WHITE, "Anton", a)
    g = ease((t - 1.2) / 0.8)  # the gap between Narlikar's idea and the first strange burst
    if g > 0:
        xa, xb = xs[1974], xs[1974] + (xs[2006] - xs[1974]) * g
        lay = np.zeros_like(f)
        cv2.line(lay, (int(xa), int(y)), (int(xb), int(y)), AMBER, 14, cv2.LINE_AA)
        f += cv2.GaussianBlur(lay, (0, 0), 9) * 1.4 + lay * 0.6
        text(f, f"{int(round(32 * g))} YEARS", (xa + xs[2006]) / 2, y - 230, 80, AMBER, "Anton", g)
        text(f, "NO SUCH BLAST CAUGHT", (xa + xs[2006]) / 2, y - 160, 36, WHITE, alpha=ease((t - 2.0) / 0.3))
    return f


def burst_bars(t, D):
    f = bg(t)
    rows = [("SHORT BURST", 2, "UNDER 2 SECONDS", WHITE), ("LONG BURST", 30, "+ SUPERNOVA", BLUE), ("2006 BURST", 102, "NO SUPERNOVA?", AMBER)]
    x0, x1 = 560, W - 220
    for k, (lab, v, note, col) in enumerate(rows):
        y = H * 0.32 + k * 200
        a = ease((t - 0.25 * k) / 0.3)
        if a <= 0: continue
        text(f, lab, x0 - 40, y, 48, col, "Anton", a, "rm")
        L = (x1 - x0) * (v / 110.0) * eo((t - 0.25 * k - 0.1) / 0.9)
        cv2.rectangle(f, (x0, int(y - 34)), (int(x0 + max(4, L)), int(y + 34)), col, -1, cv2.LINE_AA)
        if k == 2:
            n = int(round(102 * eo((t - 0.6) / 0.9)))
            text(f, f"{n} SECONDS", x0 + max(4, L) - 20, y, 44, (20, 20, 20), "Anton", a, "rm")
        text(f, note, x0 + max(4, L) + 24, y, 34, col, alpha=ease((t - 0.25 * k - 0.8) / 0.3), anchor="lm") if k < 2 else None
        if k == 2 and t > 1.7:
            text(f, note, W / 2, H * 0.9, 60, AMBER, "Anton", ease((t - 1.7) / 0.25))
    return f


def two_clocks(t, D):
    f = bg(t)
    for k, (cx, lab) in enumerate(((W * 0.3, "INSIDE"), (W * 0.7, "OUTSIDE"))):
        cy, R = H * 0.46, 210
        cv2.circle(f, (int(cx), int(cy)), R, WHITE, 5, cv2.LINE_AA)
        for m in range(12):
            a = m * math.pi / 6
            cv2.line(f, (int(cx + math.sin(a) * R * 0.86), int(cy - math.cos(a) * R * 0.86)),
                     (int(cx + math.sin(a) * R * 0.97), int(cy - math.cos(a) * R * 0.97)), GREY, 4, cv2.LINE_AA)
        if k == 0:  # one tick and it is over
            ang = 2 * math.pi * eo(t / 0.9)
            note, col = "ONE MOMENT", WHITE
        else:       # outside, time races on
            ang = t * 2 * math.pi * 6
            note, col = "", AMBER
        cv2.line(f, (int(cx), int(cy)), (int(cx + math.sin(ang) * R * 0.8), int(cy - math.cos(ang) * R * 0.8)), col, 8, cv2.LINE_AA)
        cv2.circle(f, (int(cx), int(cy)), 12, col, -1, cv2.LINE_AA)
        text(f, lab, cx, cy - R - 60, 56, col, "Anton")
        if k == 0:
            text(f, note, cx, cy + R + 70, 44, WHITE, "Anton", ease((t - 0.9) / 0.3))
        else:
            yrs = 10 ** (9.3 * eo(t / (D * 0.85)))
            s = f"{yrs / 1e9:.1f} BILLION YEARS" if yrs >= 1e9 else f"{yrs / 1e6:,.0f} MILLION YEARS" if yrs >= 1e6 else f"{yrs:,.0f} YEARS"
            text(f, s, cx, cy + R + 70, 44, AMBER, "Anton")
    return f


def atom_speck(t, D):
    f = bg(t)
    z = 1.0 + 0.6 * ease(t / D)  # slow push in
    cx, cy = W * 0.4, H * 0.48
    glow(f, cx, cy, 30 * z, (120, 180, 255), 1.0)
    cv2.circle(f, (int(cx), int(cy)), int(18 * z), (140, 190, 255), -1, cv2.LINE_AA)
    for k in range(3):
        ang = k * math.pi / 3 + t * 0.4
        cv2.ellipse(f, (int(cx), int(cy)), (int(260 * z), int(90 * z)), math.degrees(ang), 0, 360, (200, 200, 200), 2, cv2.LINE_AA)
        e = t * (2.4 + k * 0.5) + k
        ex = cx + math.cos(e) * 260 * z * math.cos(ang) - math.sin(e) * 90 * z * math.sin(ang)
        ey = cy + math.cos(e) * 260 * z * math.sin(ang) + math.sin(e) * 90 * z * math.cos(ang)
        glow(f, ex, ey, 10 * z, (255, 220, 160), 1.2)
    a = ease((t - 0.8) / 0.4)  # the leftover white hole: a speck far smaller than the atom
    sx, sy = W * 0.72, H * 0.48
    glow(f, sx, sy, 14, (240, 245, 255), 2.2 * a)
    cv2.circle(f, (int(sx), int(sy)), 3, (255, 255, 255), -1, cv2.LINE_AA)
    if a > 0:
        cv2.circle(f, (int(sx), int(sy)), int(40 + 10 * math.sin(t * 6)), (255, 255, 255), 2, cv2.LINE_AA)
    return f


GFX = {"bh_vs_wh": (bh_vs_wh, 3.0), "kruskal": (kruskal, 3.6), "timeline": (timeline, 3.2), "burst_bars": (burst_bars, 3.6),
       "two_clocks": (two_clocks, 3.6), "atom_speck": (atom_speck, 2.6)}


def render(name, out):
    fn, D = GFX[name]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out],
                          stdin=subprocess.PIPE)
    for k in range(int(D * FPS)):
        ff.stdin.write(np.clip(fn(k / FPS, D), 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close(); ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    od = sys.argv[1]; os.makedirs(od, exist_ok=True)
    for n in (sys.argv[2:] or GFX):
        render(n, os.path.join(od, f"mg10_{n}.mp4"))
