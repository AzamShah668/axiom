"""Literal animated scenes (owner 2026-11-19: "whatever the speaker is saying, it should be shown"). Each scene shows
exactly what its line says, timed to the spoken words, where archive footage cannot (the last star going out, three
paths branching, an atom bursting, the universe swallowing itself...).

edit.spec:  G <trigger> @ scene:<kind>[;<param>=<value>...]
  values are seconds from the scene start or Devanagari triggers of that section (searched from the G trigger on),
  optionally "+0.2"; render_v3.plan() resolves them (resolve()), adds the scene's sounds (cues()), and
  render_video.gfx draws each frame with frame().

kinds and params:
  last_star   out=<t>                         stars go out one by one; the last one dies on <t>
  three_paths split=<t> [mode=a|b|c] [hi=<t>] a line from TODAY splits into THE BIG RIP / FREEZE / CRUNCH on <t>
                                              (mode b: already split, pulses on hi; mode c: endings shown as icons)
  survey      flip=<t> [label=..]             a 3D galaxy survey map turning; it flips over on <t>
  atom_rip    atom=<t> burst=<t>              space stretches; an atom appears on atom= and bursts on burst=
  bh_vanish   gone=<t>                        a black hole shrinks, leaking light, and vanishes on gone=
  crunch      shrink=<t> swallow=<t>          galaxies rush inwards from shrink=; everything is swallowed on swallow=
  dark_force  force=<t> year=<t> [yr=1998]    galaxies pushed apart by an invisible force; FOUND IN <yr> on year=
"""
import math
import os
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
FONTS = {"dir": ""}
_CACHE = {}
AMBER = (66, 194, 245)
ICE = (255, 220, 150)
RIP = (60, 110, 255)
GOLD = (90, 200, 255)


# ------------------------------------------------------------------ helpers
def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def ss(x): x = cl(x); return x * x * (3 - 2 * x)
def eo(x): x = cl(x); return 1 - (1 - x) ** 3          # ease out
def ei(x): x = cl(x); return x ** 3                      # ease in


def parse(name):
    """scene:<kind>;k=v;... -> {"kind": .., k: v}"""
    parts = name.split(":", 1)[1].split(";")
    d = {"kind": parts[0].strip()}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            d[k.strip()] = v.strip()
    return d


TIME_KEYS = {"out", "split", "hi", "flip", "atom", "burst", "gone", "shrink", "swallow", "force", "year"}


def resolve(sc, when):
    out = {}
    for k, v in sc.items():
        if k in TIME_KEYS:
            try:
                out[k] = float(v)
            except ValueError:
                m = re.match(r"^(.*?)\s*([+-]\s*\d+(?:\.\d+)?)?$", v)
                out[k] = when(m.group(1).strip()) + (float(m.group(2).replace(" ", "")) if m.group(2) else 0.0)
        else:
            out[k] = v
    return out


def cues(sc):
    k = sc["kind"]
    c = []
    if k == "last_star":
        c += [("riser", sc["out"] - 1.6, -4, {"d": 1.6}), ("kz_thud", sc["out"], 0, {})]
    elif k == "three_paths":
        s = sc.get("split", 0)
        if s > 0:
            c += [("kz_whoosh", s - 0.15 + 0.25 * i, -2, {}) for i in range(3)]
        if sc.get("hi") is not None:
            c.append(("kz_thud", sc["hi"], -6, {}))
    elif k == "survey":
        c += [("kz_whoosh", sc["flip"] - 0.2, 0, {}), ("kz_thud", sc["flip"] + 0.35, -3, {})]
    elif k == "atom_rip":
        c += [("kz_whoosh", sc["atom"] - 0.3, -2, {}), ("riser", sc["burst"] - 1.0, -4, {"d": 1.0}), ("kz_shot", sc["burst"], 0, {})]
    elif k == "bh_vanish":
        c += [("kz_thud", sc["gone"], -2, {})]
    elif k == "crunch":
        c += [("riser", sc["swallow"] - 1.8, -2, {"d": 1.8}), ("kz_shot", sc["swallow"], 0, {}), ("sub_drop", sc["swallow"] + 0.05, -2, {})]
    elif k == "dark_force":
        c += [("kz_whoosh", sc["force"] - 0.2, 0, {}), ("kz_thud", sc["year"], 0, {})]
    return c


def _font(name, size, weight=None):
    key = (name, int(size), weight)
    if key not in _CACHE:
        f = ImageFont.truetype(os.path.join(FONTS["dir"], f"{name}.ttf"), int(size))
        if weight:
            try:
                f.set_variation_by_name(weight)
            except Exception:
                pass
        _CACHE[key] = f
    return _CACHE[key]


def text(f, s, x, y, size, font="Anton", color=(255, 255, 255), op=1.0, anchor="lt", weight=None, track=0):
    """Draw text on a float BGR frame (op 0..1), with a soft shadow."""
    if op <= 0.01 or not s:
        return
    fnt = _font(font, size, weight)
    if track:
        s = (" " * 0).join(s)
    b = fnt.getbbox(s)
    pad = int(size * 0.4)
    w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((pad - b[0], pad - b[1]), s, font=fnt, fill=255)
    a = np.array(m, np.float32) / 255
    sh = cv2.GaussianBlur(a, (0, 0), max(1.5, size * 0.08)) * 0.75
    if anchor == "mm":
        x0, y0 = int(x - w / 2), int(y - h / 2)
    elif anchor == "rt":
        x0, y0 = int(x - w + pad), int(y - pad)
    else:
        x0, y0 = int(x - pad), int(y - pad)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    A = a[ya - y0:yb - y0, xa - x0:xb - x0, None] * op
    S = sh[ya - y0:yb - y0, xa - x0:xb - x0, None] * op
    reg = f[ya:yb, xa:xb]
    reg *= 1 - S
    reg[:] = reg * (1 - A) + np.array(color, np.float32) * A


def label(f, t, t0, kicker, title, color):
    """The path label, top-left, like the K headlines: small spaced kicker + big Anton title."""
    p = eo((t - t0) / 0.45)
    if p <= 0:
        return
    dx = (1 - p) * -40
    text(f, kicker, 110 + dx, 104, 30, "Montserrat", (225, 225, 225), p, weight="Bold")
    text(f, title, 104 + dx, 146, 112, "Anton", color, p)


_SPR = {}


def sprite(r):
    r = max(1, int(r))
    if r not in _SPR:
        k = np.arange(-3 * r, 3 * r + 1, dtype=np.float32)
        g = np.exp(-(k[:, None] ** 2 + k[None, :] ** 2) / (2 * r * r))
        _SPR[r] = g
    return _SPR[r]


def glow(f, x, y, r, color, amt):
    """Additive gaussian glow (color BGR 0..255, amt multiplier)."""
    if amt <= 0.003:
        return
    g = sprite(r)
    n = g.shape[0] // 2
    x, y = int(round(x)), int(round(y))
    x0, y0 = x - n, y - n
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + g.shape[1]), min(H, y0 + g.shape[0])
    if xa >= xb or ya >= yb:
        return
    f[ya:yb, xa:xb] += g[ya - y0:yb - y0, xa - x0:xb - x0, None] * (np.array(color, np.float32) * amt)


def bloom(f, k=0.55):
    small = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bright = np.clip(small - 150, 0, None)
    b = cv2.GaussianBlur(bright, (0, 0), 6) + cv2.GaussianBlur(bright, (0, 0), 18)
    f += cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR) * k


def _stars(seed=1, n=1400):
    key = ("stars", seed, n)
    if key not in _CACHE:
        rng = np.random.default_rng(seed)
        x, y = rng.uniform(0, W, n), rng.uniform(0, H, n)
        mag = rng.power(4, n)               # mostly faint
        col = np.stack([rng.uniform(200, 255, n), rng.uniform(205, 245, n), rng.uniform(210, 255, n)], 1)
        base = np.zeros((H, W, 3), np.float32)
        for i in range(n):
            if mag[i] < 0.75:
                xi, yi = int(x[i]), int(y[i])
                base[yi, xi] += col[i] * (0.25 + mag[i])
        base = cv2.GaussianBlur(base, (0, 0), 0.7) * 1.6
        # faint nebula haze
        hz = cv2.resize(rng.random((9, 16)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
        hz2 = cv2.resize(rng.random((5, 9)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
        haze = np.stack([hz * 14 + 6, hz2 * 6 + 2, hz2 * 10 + 6], -1)
        _CACHE[key] = (x, y, mag, col, base, haze)
    return _CACHE[key]


def background(t, push=0.04, dim=1.0, seed=1):
    x, y, mag, col, base, haze = _stars(seed)
    s = 1 + push * t
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0.4 * t, s)
    f = cv2.warpAffine(base + haze, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return f * dim


def finish(f, t):
    yy, xx = np.ogrid[:H, :W]
    key = "vig"
    if key not in _CACHE:
        _CACHE[key] = (1 - 0.42 * np.clip(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2, 0, 1))[..., None].astype(np.float32)
        _CACHE["grain"] = [np.random.default_rng(i).normal(0, 4, (H, W, 1)).astype(np.float32) for i in range(4)]
    f *= _CACHE[key]
    f += _CACHE["grain"][int(t * FPS) % 4]
    return np.clip(f, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ scenes
def last_star(t, D, p):
    out = p["out"]
    x, y, mag, col, base, haze = _stars(7, 900)
    rng = np.random.default_rng(11)
    f = haze * (1 - 0.6 * ss((t - out) / 0.5)) * 1.0
    s = 1 + 0.05 * t
    cx, cy = W / 2, H / 2
    die = rng.uniform(0.15, max(0.3, out - 0.5), len(x))    # every other star dies before the last one
    for i in range(len(x)):
        a = 1 - ss((t - die[i]) / 0.35)
        if a <= 0.01:
            continue
        if t > die[i] - 0.25:
            a *= 0.6 + 0.4 * math.sin(t * 60 + i)          # flicker before dying
        px, py = cx + (x[i] - cx) * s, cy + (y[i] - cy) * s
        r = 1 + 2.2 * mag[i]
        glow(f, px, py, r, col[i], 0.55 * a * (0.3 + mag[i]))
    # the last star: warm white, pulsing; reddens and shrinks, then goes out on `out`
    k = ss((t - (out - 0.9)) / 0.9)
    alive = 1 - ss((t - out) / 0.12)
    pulse = 1 + 0.06 * math.sin(t * 5)
    colr = np.array([200, 225, 255]) * (1 - k) + np.array([60, 90, 255]) * k
    rad = (34 - 20 * k) * pulse
    glow(f, cx, cy, rad * 2.6, colr, 0.35 * alive)
    glow(f, cx, cy, rad, colr, 1.6 * alive)
    glow(f, cx, cy, max(2, rad * 0.25), (255, 255, 255), 2.2 * alive * (1 - 0.7 * k))
    if alive > 0.05:   # diffraction spikes
        L = int(220 * alive * (1 - 0.5 * k))
        spike = np.zeros((H, W, 3), np.float32)
        cv2.line(spike, (int(cx - L), int(cy)), (int(cx + L), int(cy)), tuple(float(c) for c in colr), 2, cv2.LINE_AA)
        cv2.line(spike, (int(cx), int(cy - L)), (int(cx), int(cy + L)), tuple(float(c) for c in colr), 2, cv2.LINE_AA)
        f += cv2.GaussianBlur(spike, (0, 0), 2.5) * 0.9 * alive
    if out < t < out + 0.25:        # the last flicker of light
        glow(f, cx, cy, 120, (120, 150, 255), 0.5 * (1 - (t - out) / 0.25))
    bloom(f)
    return finish(f, t)


def _branch_pts(i, n=60):
    x0, y0 = W * 0.36, H * 0.55
    ys = [H * 0.28, H * 0.55, H * 0.82][i]
    x1 = W * 0.70
    u = np.linspace(0, 1, n)
    xs = x0 + (x1 - x0) * u
    yy = y0 + (ys - y0) * (u * u * (3 - 2 * u))
    return np.stack([xs, yy], 1)


NAMES3 = [("THE BIG RIP", RIP), ("THE BIG FREEZE", ICE), ("THE BIG CRUNCH", GOLD)]


def _icon(f, i, x, y, t, op):
    c = NAMES3[i][1]
    if op <= 0:
        return
    if i == 0:       # atom bursting: nucleus + shards flying out
        glow(f, x, y, 10, c, 1.2 * op)
        for k in range(10):
            a = k * 0.628 + 0.3
            r = 22 + 10 * (0.5 + 0.5 * math.sin(t * 4 + k))
            cv2.line(f, (int(x + 12 * math.cos(a)), int(y + 12 * math.sin(a))), (int(x + r * math.cos(a)), int(y + r * math.sin(a))),
                     tuple(float(v * op) for v in c), 2, cv2.LINE_AA)
    elif i == 1:     # snowflake
        for k in range(6):
            a = k * math.pi / 3 + t * 0.3
            ex, ey = x + 26 * math.cos(a), y + 26 * math.sin(a)
            cv2.line(f, (int(x), int(y)), (int(ex), int(ey)), tuple(float(v * op) for v in c), 2, cv2.LINE_AA)
            for sgn in (-1, 1):
                bx, by = x + 16 * math.cos(a), y + 16 * math.sin(a)
                cv2.line(f, (int(bx), int(by)), (int(bx + 8 * math.cos(a + sgn * 0.8)), int(by + 8 * math.sin(a + sgn * 0.8))),
                         tuple(float(v * op) for v in c), 2, cv2.LINE_AA)
        glow(f, x, y, 8, c, 0.6 * op)
    else:            # collapse: arrows to a point
        for k in range(8):
            a = k * math.pi / 4
            r0, r1 = 30, 12 + 4 * (0.5 + 0.5 * math.sin(t * 5))
            cv2.arrowedLine(f, (int(x + r0 * math.cos(a)), int(y + r0 * math.sin(a))), (int(x + r1 * math.cos(a)), int(y + r1 * math.sin(a))),
                            tuple(float(v * op) for v in c), 2, cv2.LINE_AA, tipLength=0.4)
        glow(f, x, y, 7, (255, 255, 255), 1.0 * op)


def three_paths(t, D, p):
    mode = p.get("mode", "a")
    split = p.get("split", 0.0)
    f = background(t, push=0.02, dim=0.75, seed=3)
    x0, y0 = W * 0.10, H * 0.55
    xs = W * 0.36
    trunk = 1.0 if split <= 0 else eo((t - (split - 0.9)) / 0.9)
    tx = x0 + (xs - x0) * trunk
    cv2.line(f, (int(x0), int(y0)), (int(tx), int(y0)), (235, 235, 235), 4, cv2.LINE_AA)
    glow(f, x0, y0, 9, (255, 255, 255), 1.6)
    text(f, "TODAY", x0, y0 + 30, 28, "Montserrat", (220, 220, 220), 1.0, "lt", "Bold")
    hi = p.get("hi")
    for i in range(3):
        st = (split + 0.25 * i) if split > 0 else -10
        u = eo((t - st) / 0.6)
        if u <= 0:
            continue
        pts = _branch_pts(i)
        m = max(2, int(len(pts) * u))
        name, c = NAMES3[i]
        lit = 1.0 + (0.8 * math.exp(-max(0, t - hi) * 2.5) if hi is not None and t > hi else 0)
        layer = np.zeros((H, W, 3), np.float32)
        cv2.polylines(layer, [pts[:m].astype(np.int32)], False, tuple(float(v) for v in c), 4, cv2.LINE_AA)
        f += layer * lit + cv2.GaussianBlur(layer, (0, 0), 6) * 0.9 * lit
        # a pulse travelling along the branch
        q = ((t * 0.6 + i * 0.33) % 1.0) * (m - 1)
        glow(f, pts[int(q)][0], pts[int(q)][1], 6, c, 1.4 * lit)
        if u >= 0.98:
            ex, ey = pts[-1]
            op = eo((t - st - 0.55) / 0.4)
            if mode == "c":
                _icon(f, i, ex + 50, ey, t, op)
                text(f, name, ex + 100, ey - 46, 84, "Anton", c, op)
            else:
                glow(f, ex, ey, 8, c, 1.4 * op)
                text(f, name, ex + 30, ey - 46, 84, "Anton", c, op)
    if split > 0 and t > split - 0.2:
        a = eo((t - split + 0.2) / 0.4) * (1 - ss((t - split - 1.6) / 0.5))
        text(f, "3", xs, y0 - 150, 150, "Anton", AMBER, a, "mm")
    bloom(f, 0.4)
    return finish(f, t)


def _survey_pts(n=9000):
    if "survey" not in _CACHE:
        rng = np.random.default_rng(5)
        r = rng.power(2.2, n)
        ang = rng.uniform(-0.62, 0.62, n)
        el = rng.normal(0, 0.05, n)
        # cosmic web: clump the points into filaments
        cl_ = rng.uniform(0, 1, (60, 3))
        pick = rng.integers(0, 60, n)
        mix = rng.random(n) < 0.55
        r = np.where(mix, cl_[pick, 0] * 0.95 + rng.normal(0, 0.02, n), r)
        ang = np.where(mix, (cl_[pick, 1] - 0.5) * 1.24 + rng.normal(0, 0.03, n), ang)
        x = r * np.sin(ang)
        y = r * np.cos(ang)
        z = el * r
        col = np.stack([255 - 200 * r, 160 + 40 * np.sin(r * 3), 90 + 165 * r], 1)   # BGR: blue near -> red far
        _CACHE["survey"] = (np.stack([x, y, z], 1), col, rng.random(n))
    return _CACHE["survey"]


def survey(t, D, p):
    flip = p["flip"]
    P, col, br = _survey_pts()
    f = background(t, push=0.01, dim=0.45, seed=4)
    yaw = 0.25 * t - 0.6
    roll = math.pi * eo((t - flip) / 0.9)            # the map flips over
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    x = P[:, 0] * cy_ - P[:, 2] * sy_
    z = P[:, 0] * sy_ + P[:, 2] * cy_
    y = P[:, 1]
    cr, sr = math.cos(roll), math.sin(roll)
    y2 = y * cr - z * sr
    z2 = y * sr + z * cr
    reveal = eo(t / 1.2)
    ys = y2 - 0.5 * cr
    d = 2.6 + z2
    sx = W / 2 + x / d * 2400 * (0.9 + 0.1 * reveal)
    sy = H / 2 + 60 + ys / d * 2400
    show = br < reveal
    img = np.zeros((H, W, 3), np.float32)
    ix, iy = sx[show].astype(int), sy[show].astype(int)
    ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    np.add.at(img, (iy[ok], ix[ok]), col[show][ok] * 1.3)
    f += cv2.GaussianBlur(img, (0, 0), 1.0) * 2.2 + cv2.GaussianBlur(img, (0, 0), 4) * 1.4
    glow(f, W / 2, H / 2 + 60 - 0.5 * cr / 2.6 * 2400, 10, (255, 255, 255), 1.5)     # us, at the tip of the cone
    text(f, p.get("label", "DESI GALAXY MAP"), 110, 104, 30, "Montserrat", (225, 225, 225), eo(t / 0.5), weight="Bold")
    text(f, "2026 DATA", 104, 146, 112, "Anton", AMBER, eo((t - 0.4) / 0.5))
    if t > flip:
        text(f, "FLIPPED", 104, 270, 64, "Anton", (255, 255, 255), eo((t - flip - 0.5) / 0.4))
    bloom(f, 0.4)
    return finish(f, t)


def atom_rip(t, D, p):
    atom, burst = p["atom"], p["burst"]
    f = background(t, push=0.0, dim=0.6, seed=6)
    # 1. space stretching: a grid whose spacing grows ever faster, galaxies riding it apart
    grow = math.exp(0.55 * t) * (1 + 3 * ei((t - burst + 1.0) / 1.0))
    grid = np.zeros((H, W, 3), np.float32)
    sp = 90 * grow
    gop = 1 - 0.6 * ss((t - atom) / 0.6)
    for k in range(-40, 41):
        gx = W / 2 + k * sp
        gy = H / 2 + k * sp
        if -10 < gx < W + 10:
            cv2.line(grid, (int(gx), 0), (int(gx), H), (180, 120, 60), 1, cv2.LINE_AA)
        if -10 < gy < H + 10:
            cv2.line(grid, (0, int(gy)), (W, int(gy)), (180, 120, 60), 1, cv2.LINE_AA)
    f += grid * 0.55 * gop
    rng = np.random.default_rng(9)
    for i in range(70):
        gx, gy = rng.uniform(-6, 6), rng.uniform(-3.4, 3.4)
        px, py = W / 2 + gx * 90 * grow, H / 2 + gy * 90 * grow
        glow(f, px, py, 4, (255, 200, 170), 0.9 * gop)
    # 2. the atom, stretched by the expansion, then bursting
    if t > atom - 0.1:
        a = eo((t - atom + 0.1) / 0.4) * (1 - ss((t - burst) / 0.15))
        stretch = 1 + 1.4 * ei((t - atom) / max(0.3, burst - atom))
        jit = 6 * ei((t - atom) / max(0.3, burst - atom)) * math.sin(t * 80)
        cx, cy = W / 2 + jit, H / 2
        glow(f, cx, cy, 26, (120, 170, 255), 1.4 * a)
        glow(f, cx, cy, 9, (255, 255, 255), 2.2 * a)
        lay = np.zeros((H, W, 3), np.float32)
        for k in range(3):
            ang = k * 60 + 15
            axes = (int(200 * stretch), 70)
            cv2.ellipse(lay, (int(cx), int(cy)), axes, ang, 0, 360, (255, 220, 160), 2, cv2.LINE_AA)
            th = t * 3.2 + k * 2.1
            ex = axes[0] * math.cos(th)
            ey = axes[1] * math.sin(th)
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            glow(f, cx + ex * ca - ey * sa, cy + ex * sa + ey * ca, 7, (255, 230, 180), 1.8 * a)
        f += (lay + cv2.GaussianBlur(lay, (0, 0), 5)) * a
    if t > burst:   # the burst: flash + shards
        u = t - burst
        fl = math.exp(-u * 7)
        f += fl * 220
        rng = np.random.default_rng(12)
        for i in range(160):
            a0 = rng.uniform(0, 2 * math.pi)
            sp_ = rng.uniform(300, 1400)
            r = sp_ * (1 - math.exp(-u * 2.2))
            x, y = W / 2 + r * math.cos(a0), H / 2 + r * math.sin(a0) * 0.8
            r2 = max(0, r - 60)
            x2, y2 = W / 2 + r2 * math.cos(a0), H / 2 + r2 * math.sin(a0) * 0.8
            c = (255, 210, 150) if i % 3 else (120, 170, 255)
            cv2.line(f, (int(x2), int(y2)), (int(x), int(y)), tuple(float(v) * math.exp(-u * 0.8) for v in c), 2, cv2.LINE_AA)
    label(f, t, 0.1, "PATH 1", "THE BIG RIP", RIP)
    bloom(f)
    return finish(f, t)


def bh_vanish(t, D, p):
    gone = p["gone"]
    f = background(t, push=0.03, dim=0.8, seed=8)
    k = cl(t / max(0.5, gone))
    alive = 1 - ss((t - gone) / 0.15)
    r = 150 * (1 - 0.85 * ei(k)) + 4
    cx, cy = W / 2, H / 2
    if alive > 0.02:
        ring = np.zeros((H, W, 3), np.float32)
        cv2.circle(ring, (int(cx), int(cy)), int(r * 1.12), (80, 170, 255), max(2, int(r * 0.12)), cv2.LINE_AA)
        f += (cv2.GaussianBlur(ring, (0, 0), max(3, r * 0.15)) * 2.2 + ring * 0.8) * alive
        cv2.circle(f, (int(cx), int(cy)), int(r), (0, 0, 0), -1, cv2.LINE_AA)
        rng = np.random.default_rng(14)          # Hawking light leaking away
        for i in range(90):
            a0 = rng.uniform(0, 2 * math.pi)
            ph = (t * rng.uniform(0.4, 1.0) + rng.random()) % 1.0
            rr = r * 1.15 + ph * 420
            glow(f, cx + rr * math.cos(a0), cy + rr * math.sin(a0), 2, (255, 240, 220), 1.4 * (1 - ph) * alive)
    if gone < t < gone + 0.6:
        glow(f, cx, cy, 70, (255, 255, 255), 2.5 * (1 - (t - gone) / 0.6))
    bloom(f)
    return finish(f, t)


def _galaxies(n=1600):
    if "gal" not in _CACHE:
        rng = np.random.default_rng(21)
        r = rng.uniform(0.15, 1.0, n) ** 0.7
        a = rng.uniform(0, 2 * math.pi, n)
        z = rng.uniform(0.4, 1.6, n)
        col = rng.choice(np.array([[255, 210, 180], [200, 220, 255], [150, 190, 255], [255, 240, 230]], np.float32), n)
        _CACHE["gal"] = (r, a, z, col, rng.uniform(1.5, 4.5, n))
    return _CACHE["gal"]


def crunch(t, D, p):
    shrink, sw = p["shrink"], p["swallow"]
    f = background(t, push=0.0, dim=0.5 * (1 - ss((t - sw) / 0.3)), seed=12)
    r0, a, z, col, size = _galaxies()
    u = cl((t - shrink) / max(0.3, sw - shrink))
    u2 = cl((t - 1 / FPS - shrink) / max(0.3, sw - shrink))
    s = 1 - ei(u) * 0.995
    s2 = 1 - ei(u2) * 0.995
    cx, cy = W / 2, H / 2
    heat = ei(u)
    if t < sw:
        lay = np.zeros((H, W, 3), np.float32)
        R = W * 0.62
        for i in range(len(r0)):
            rr = r0[i] * R * s / z[i]
            rp = r0[i] * R * s2 / z[i]
            x, y = cx + rr * math.cos(a[i] + 0.3 * u), cy + rr * math.sin(a[i] + 0.3 * u) * 0.66
            xp, yp = cx + rp * math.cos(a[i] + 0.3 * u2), cy + rp * math.sin(a[i] + 0.3 * u2) * 0.66
            c = col[i] * (1 - heat) + np.array([120, 190, 255]) * heat
            if abs(xp - x) + abs(yp - y) > 3:
                cv2.line(lay, (int(xp), int(yp)), (int(x), int(y)), tuple(float(v) * 0.7 for v in c), 2, cv2.LINE_AA)
            else:
                cv2.circle(lay, (int(x), int(y)), max(1, int(size[i] * 0.9)), tuple(float(v) for v in c), -1, cv2.LINE_AA)
        f += lay * 1.4 + cv2.GaussianBlur(lay, (0, 0), 3) * 1.6
        glow(f, cx, cy, 30 + 160 * heat, (180, 220, 255), 0.6 + 2.5 * heat)
    else:
        v = t - sw
        f += 255 * math.exp(-v * 3.0)
        glow(f, cx, cy, 6, (255, 255, 255), 2.0 * math.exp(-v * 0.8))
    label(f, t, 0.1, "PATH 3", "THE BIG CRUNCH", GOLD)
    bloom(f)
    return finish(f, t)


def dark_force(t, D, p):
    force, year = p["force"], p["year"]
    f = background(t, push=0.0, dim=0.55, seed=15)
    r0, a, z, col, size = _galaxies(900)
    cx, cy = W / 2, H / 2
    e = 1 + 0.10 * t + 0.25 * ei((t - force) / 2.5) * (t - force > 0) * (t - force)
    # the invisible force: a violet field breathing out from the centre
    yy, xx = np.ogrid[:H, :W]
    if "df" not in _CACHE:
        _CACHE["df"] = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2).astype(np.float32)
    d = _CACHE["df"]
    wave = np.exp(-((d - ((t - force) * 0.35) % 0.9) / 0.05) ** 2) * (t > force)
    field = (0.35 + 0.25 * math.sin(t * 2)) * np.exp(-d * 2.2)
    f += (field[..., None] * np.array([130, 40, 110], np.float32) + wave[..., None] * np.array([200, 90, 180], np.float32) * 0.6)
    lay = np.zeros((H, W, 3), np.float32)
    for i in range(len(r0)):
        rr = r0[i] * W * 0.5 * e / z[i]
        x, y = cx + rr * math.cos(a[i]), cy + rr * math.sin(a[i]) * 0.62
        if 0 <= x < W and 0 <= y < H:   # small elliptical galaxies, bright cores
            cv2.ellipse(lay, (int(x), int(y)), (int(size[i] * 1.6), int(size[i] * 0.8)), (a[i] * 57) % 180, 0, 360,
                        tuple(float(v) for v in col[i]), -1, cv2.LINE_AA)
    f += lay * 1.3 + cv2.GaussianBlur(lay, (0, 0), 4) * 1.6
    if t > force:
        op = eo((t - force) / 0.4)
        s = "AN UNKNOWN FORCE"
        n = min(len(s), int((t - force) * 24))
        text(f, s[:n], W / 2, H * 0.20, 96, "Anton", (255, 255, 255), op, "mm")
    if t > year:
        op = eo((t - year) / 0.35)
        text(f, "FOUND IN " + p.get("yr", "1998"), W / 2, H * 0.80, 84, "Anton", AMBER, op, "mm")
    bloom(f, 0.45)
    return finish(f, t)


KINDS = {"last_star": last_star, "three_paths": three_paths, "survey": survey, "atom_rip": atom_rip,
         "bh_vanish": bh_vanish, "crunch": crunch, "dark_force": dark_force}


def frame(sc, t, D, fonts_dir=""):
    FONTS["dir"] = fonts_dir
    return KINDS[sc["kind"]](t, D, sc)
