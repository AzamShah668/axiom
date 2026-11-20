"""Space motion-graphics toolkit (owner 2026-11-20: "use every capability of motion graphics, smooth and engaging";
no Blender). A perspective 3D camera over a field of procedural spiral galaxies, layered twinkling stars, a nebula,
motion blur by sub-frame accumulation, filmic bloom, lens flare, shockwaves, chromatic aberration, camera shake,
glossy spheres and tubes, and kinetic type. Frames are float32 BGR 0..255 (values above 255 bloom).
"""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FONTS = {"dir": ""}
_C = {}


def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def ss(x): x = cl(x); return x * x * (3 - 2 * x)
def eo(x): x = cl(x); return 1 - (1 - x) ** 3
def ei(x): x = cl(x); return x ** 3
def eio(x): x = cl(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, s=1.9): x = cl(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2


# ------------------------------------------------------------------ procedural textures
def _noise(shape, octaves, seed, base=4):
    rng = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        g = base * 2 ** o
        n = rng.random((g + 2, int(g * w / h) + 2)).astype(np.float32)
        out += cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        tot += amp
        amp *= 0.55
    return out / tot


def nebula(seed=1, palette=((90, 30, 60), (160, 60, 120), (200, 140, 60))):
    """A big nebula texture (2x the frame), colour from a 3-stop BGR palette."""
    key = ("neb", seed, palette)
    if key not in _C:
        h, w = H, W * 2
        n = _noise((h, w), 6, seed)
        m = _noise((h, w), 4, seed + 7)
        n = np.clip((n - 0.42) * 2.6, 0, 1) ** 1.6
        p = np.array(palette, np.float32)
        col = p[0] * (1 - m[..., None]) + p[1] * m[..., None]
        col = col * n[..., None] + p[2] * (n[..., None] ** 3) * 0.6
        _C[key] = cv2.GaussianBlur(col, (0, 0), 3).astype(np.float32)
    return _C[key]


def galaxy_sprite(seed, size=320):
    """RGBA-like (bgr, alpha) float sprite of a spiral galaxy: log-spiral arms, dust lane, bulge."""
    key = ("gal", seed, size)
    if key not in _C:
        rng = np.random.default_rng(seed)
        yy, xx = np.mgrid[-1:1:size * 1j, -1:1:size * 1j].astype(np.float32)
        r = np.sqrt(xx ** 2 + yy ** 2) + 1e-4
        th = np.arctan2(yy, xx)
        arms = rng.integers(2, 4)
        pitch = rng.uniform(3.0, 5.0)
        spiral = np.cos(arms * (th - pitch * np.log(r)) + rng.uniform(0, 6.28))
        n = _noise((size, size), 5, seed + 3, base=6)
        armd = np.clip(spiral * 0.5 + 0.5, 0, 1) ** 2.2 * (0.6 + 0.8 * n)
        disk = np.exp(-r / 0.32) * (0.25 + 1.1 * armd)
        bulge = np.exp(-(r / 0.09) ** 2) * 2.4
        dust = 1 - 0.55 * np.clip(-spiral * 0.5 + 0.1, 0, 1) * np.exp(-r / 0.45)
        clumps = (rng.random((size, size)) > 0.996).astype(np.float32)
        clumps = cv2.GaussianBlur(clumps, (0, 0), 1.2) * 60 * armd * np.exp(-r / 0.5)
        lum = disk * dust + bulge
        warm = np.exp(-r / 0.18)
        bgr = np.stack([lum * (0.95 - 0.5 * warm) + clumps * 0.8, lum * (0.85 - 0.1 * warm) + clumps * 0.6,
                        lum * (0.75 + 0.35 * warm) + clumps * 0.9], -1)
        a = np.clip(lum * 1.6, 0, 1) * np.clip((1 - r) * 3, 0, 1)
        _C[key] = (bgr * 255 * 0.9, a)
    return _C[key]


def sphere_sprite(color, size=200):
    """A glossy sphere: diffuse shading + rim + specular highlight (bgr, alpha)."""
    key = ("sph", color, size)
    if key not in _C:
        yy, xx = np.mgrid[-1:1:size * 1j, -1:1:size * 1j].astype(np.float32)
        r2 = xx ** 2 + yy ** 2
        a = np.clip((1 - np.sqrt(r2)) * size * 0.5, 0, 1)
        z = np.sqrt(np.clip(1 - r2, 0, 1))
        L = np.array([-0.45, -0.55, 0.7]); L = L / np.linalg.norm(L)
        diff = np.clip(xx * L[0] + yy * L[1] + z * L[2], 0, 1)
        spec = np.clip(xx * L[0] + yy * L[1] + z * L[2], 0, 1) ** 40 * 1.6
        rim = (1 - z) ** 3 * 0.6
        c = np.array(color, np.float32)
        bgr = c * (0.12 + 0.95 * diff[..., None]) + 255 * spec[..., None] + c * rim[..., None]
        _C[key] = (bgr, a)
    return _C[key]


# ------------------------------------------------------------------ compositing
def put(f, spr, x, y, scale=1.0, angle=0.0, alpha=1.0, add=True, tilt=1.0):
    """Place a sprite centred at (x, y); additive (light) or alpha-over."""
    bgr, a = spr
    h, w = a.shape
    s = scale
    if s * max(h, w) < 1.5 or alpha <= 0.01:
        return
    ca, sa_ = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    A = np.array([[ca, sa_], [-sa_ * tilt, ca * tilt]], np.float32) * s       # rotate, then squash (tilt), then scale
    out_w, out_h = int(w * s * 1.45) + 4, int(h * s * 1.45) + 4
    M = np.zeros((2, 3), np.float32)
    M[:, :2] = A
    M[:, 2] = np.array([out_w / 2, out_h / 2], np.float32) - A @ np.array([w / 2, h / 2], np.float32)
    x0, y0 = int(x - out_w / 2), int(y - out_h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + out_w), min(H, y0 + out_h)
    if xa >= xb or ya >= yb:
        return
    sb = cv2.warpAffine(bgr, M, (out_w, out_h), flags=cv2.INTER_LINEAR)[ya - y0:yb - y0, xa - x0:xb - x0]
    sa = cv2.warpAffine(a, M, (out_w, out_h), flags=cv2.INTER_LINEAR)[ya - y0:yb - y0, xa - x0:xb - x0, None] * alpha
    reg = f[ya:yb, xa:xb]
    if add:
        reg += sb * sa
    else:
        reg[:] = reg * (1 - sa) + sb * sa


_SPR = {}


def glow(f, x, y, r, color, amt):
    if amt <= 0.003 or r < 0.5:
        return
    r = max(1, int(r))
    if r not in _SPR:
        k = np.arange(-3 * r, 3 * r + 1, dtype=np.float32)
        _SPR[r] = np.exp(-(k[:, None] ** 2 + k[None, :] ** 2) / (2 * r * r))
    g = _SPR[r]
    n = g.shape[0] // 2
    x, y = int(round(x)), int(round(y))
    x0, y0 = x - n, y - n
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + g.shape[1]), min(H, y0 + g.shape[0])
    if xa >= xb or ya >= yb:
        return
    f[ya:yb, xa:xb] += g[ya - y0:yb - y0, xa - x0:xb - x0, None] * (np.array(color, np.float32) * amt)


def flare(f, x, y, amt, color=(255, 210, 160)):
    """Anamorphic lens flare: a long horizontal streak + a soft ring of ghosts."""
    if amt <= 0.01:
        return
    lay = np.zeros((H // 4, W // 4, 3), np.float32)
    cv2.line(lay, (0, int(y / 4)), (W // 4, int(y / 4)), color, 2, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), sigmaX=2, sigmaY=1.2)
    f += cv2.resize(lay, (W, H)) * amt * 2.2
    glow(f, x, y, 60, color, amt * 1.5)
    for k, s in ((0.6, 30), (1.4, 18), (1.9, 45)):
        gx, gy = W / 2 + (W / 2 - x) * k, H / 2 + (H / 2 - y) * k
        glow(f, gx, gy, s, (160, 200, 255), amt * 0.25)


def shockwave(f, x, y, rad, width, amt, color=(255, 230, 200)):
    if amt <= 0.01:
        return
    lay = np.zeros((H, W, 3), np.float32)
    cv2.circle(lay, (int(x), int(y)), int(rad), color, int(width), cv2.LINE_AA)
    f += cv2.GaussianBlur(lay, (0, 0), width * 0.8) * amt * 2 + lay * amt * 0.6


def chroma(f, amt):
    """Chromatic aberration: red and blue channels pushed apart radially."""
    if amt < 0.3:
        return f
    s = 1 + amt * 0.004
    Mr = cv2.getRotationMatrix2D((W / 2, H / 2), 0, s)
    Mb = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 / s)
    f[..., 2] = cv2.warpAffine(f[..., 2], Mr, (W, H), borderMode=cv2.BORDER_REFLECT)
    f[..., 0] = cv2.warpAffine(f[..., 0], Mb, (W, H), borderMode=cv2.BORDER_REFLECT)
    return f


def post(f, t, bloom=0.7, vign=0.45, grain=3.5):
    """Filmic finish: two-level bloom, soft highlight roll-off, vignette, grain -> uint8."""
    small = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = np.clip(small - 120, 0, None)
    b = cv2.GaussianBlur(br, (0, 0), 5) * 0.8 + cv2.GaussianBlur(br, (0, 0), 18) * 0.9 + cv2.GaussianBlur(br, (0, 0), 50) * 0.5
    f = f + cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR) * bloom
    f = 255 * (1 - np.exp(-f / 200.0)) * 1.06                      # filmic roll-off
    if "vig" not in _C:
        yy, xx = np.ogrid[:H, :W]
        _C["vig"] = (1 - vign * np.clip(((xx - W / 2) / (W * 0.7)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2, 0, 1))[..., None].astype(np.float32)
        _C["grain"] = [np.random.default_rng(i).normal(0, grain, (H, W, 1)).astype(np.float32) for i in range(6)]
    f = f * _C["vig"] + _C["grain"][int(t * 30) % 6]
    return np.clip(f, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ 3D camera and worlds
class Cam:
    """Pinhole camera at `pos` looking along -z rotated by yaw/pitch/roll (radians); focal in pixels."""
    def __init__(self, pos=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0, focal=900.0, cx=None, cy=None):
        self.pos = np.array(pos, np.float32)
        cy_, sy_ = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cr, sr = math.cos(roll), math.sin(roll)
        Ry = np.array([[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]])
        Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
        Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
        self.R = (Rz @ Rx @ Ry).astype(np.float32)
        self.f = focal
        self.cx = W / 2 if cx is None else cx
        self.cy = H / 2 if cy is None else cy

    def project(self, P):
        q = (P - self.pos) @ self.R.T
        z = -q[:, 2]
        ok = z > 0.05
        zz = np.where(ok, z, 1)
        return self.cx + q[:, 0] / zz * self.f, self.cy + q[:, 1] / zz * self.f, z, ok


def star_field(n=2500, seed=2, spread=60.0):
    key = ("stars3", n, seed)
    if key not in _C:
        rng = np.random.default_rng(seed)
        P = rng.uniform(-spread, spread, (n, 3)).astype(np.float32)
        b = rng.power(3, n).astype(np.float32)
        tw = rng.uniform(0, 6.28, n).astype(np.float32)
        col = np.stack([rng.uniform(210, 255, n), rng.uniform(215, 245, n), rng.uniform(220, 255, n)], 1).astype(np.float32)
        _C[key] = (P, b, tw, col)
    return _C[key]


def draw_stars(f, cam, t, amt=1.0, seed=2):
    P, b, tw, col = star_field(seed=seed)
    x, y, z, ok = cam.project(P)
    ok &= (x > -2) & (x < W + 2) & (y > -2) & (y < H + 2)
    img = np.zeros((H, W, 3), np.float32)
    tws = 0.75 + 0.25 * np.sin(t * 3 + tw)
    v = (b * tws * np.clip(30 / np.maximum(z, 1), 0.15, 2.2))[ok, None] * col[ok] * amt
    np.add.at(img, (y[ok].astype(int).clip(0, H - 1), x[ok].astype(int).clip(0, W - 1)), v)
    f += cv2.GaussianBlur(img, (0, 0), 0.8) * 2.0


def galaxy_field(n=420, seed=5, spread=30.0):
    """3D galaxies: positions, sprite ids, sizes, spin angles, tilts, tint."""
    key = ("gfield", n, seed)
    if key not in _C:
        rng = np.random.default_rng(seed)
        P = (rng.normal(0, 1, (n, 3)) * spread * np.array([1, 1, 1])).astype(np.float32)
        sid = rng.integers(0, 8, n)
        size = rng.uniform(0.6, 1.6, n).astype(np.float32)
        ang = rng.uniform(0, 360, n).astype(np.float32)
        tilt = rng.uniform(0.35, 1.0, n).astype(np.float32)
        _C[key] = (P, sid, size, ang, tilt, rng.uniform(0.35, 1.0, n).astype(np.float32))
    return _C[key]


def draw_galaxies(f, cam, scale_factor=1.0, t=0.0, amt=1.0, n=280, seed=5, center=(0, 0, 0), heat=0.0, blur_from=None):
    """Draw the galaxy field at cosmic scale factor `scale_factor` (positions scaled about `center`).
    blur_from: previous scale factor -> motion streak towards/away from the centre."""
    P, sid, size, ang, tilt, bri = galaxy_field(n, seed)
    C = np.array(center, np.float32)
    Q = C + (P - C) * scale_factor
    x, y, z, ok = cam.project(Q)
    order = np.argsort(-z)
    if blur_from is not None:
        x0, y0, _, _ = cam.project(C + (P - C) * blur_from)
    for i in order:
        if not ok[i] or z[i] < 0.6:
            continue
        s = size[i] * cam.f / z[i] / 320 * 13.0
        if s * 320 < 2 or x[i] < -300 or x[i] > W + 300 or y[i] < -300 or y[i] > H + 300:
            continue
        spr = galaxy_sprite(int(sid[i]))
        a = amt * bri[i] * cl((z[i] - 0.6) / 2.0) * cl(1.5 - z[i] / 90)
        if blur_from is not None and abs(x[i] - x0[i]) + abs(y[i] - y0[i]) > 4:
            steps = 5
            for k in range(steps):
                u = k / (steps - 1)
                put(f, spr, x0[i] + (x[i] - x0[i]) * u, y0[i] + (y[i] - y0[i]) * u, s, ang[i] + t * 6, a * (0.35 + 0.65 * u) / steps * 2.2, True, tilt[i])
        else:
            put(f, spr, x[i], y[i], s, ang[i] + t * 6, a, True, tilt[i])
        if heat > 0:
            glow(f, x[i], y[i], max(2, s * 60), (120, 170, 255), heat * a * 0.5)


# ------------------------------------------------------------------ kinetic type
def _font(name, size, weight=None):
    key = ("font", name, int(size), weight)
    if key not in _C:
        fn = ImageFont.truetype(os.path.join(FONTS["dir"], f"{name}.ttf"), int(size))
        if weight:
            try:
                fn.set_variation_by_name(weight)
            except Exception:
                pass
        _C[key] = fn
    return _C[key]


def _text_layer(s, size, font, weight):
    key = ("tl", s, int(size), font, weight)
    if key not in _C:
        fnt = _font(font, size, weight)
        b = fnt.getbbox(s)
        pad = int(size * 0.5)
        w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).text((pad - b[0], pad - b[1]), s, font=fnt, fill=255)
        a = np.array(m, np.float32) / 255
        if len(_C) > 4000:
            for k in [k for k in _C if k[0] == "tl"][:500]:
                _C.pop(k, None)
        _C[key] = a
    return _C[key]


def ktext(f, s, x, y, size, color, t, t_in, font="Anton", weight=None, glow_amt=0.6, out=None, anchor="mm"):
    """Kinetic text: pops in with overshoot (scale 0.6 -> 1), fades, soft glow and shadow; out = fade-out time."""
    if t < t_in or not s:
        return
    p = cl((t - t_in) / 0.32)
    sc = 0.55 + 0.45 * back(p)
    op = eo(p) * (1 - ss((t - out) / 0.25) if out is not None else 1)
    if op <= 0.01:
        return
    a = _text_layer(s, size, font, weight)
    h, w = a.shape
    if abs(sc - 1) > 0.01:
        a = cv2.resize(a, (max(2, int(w * sc)), max(2, int(h * sc))), interpolation=cv2.INTER_LINEAR)
    h, w = a.shape
    x0 = int(x - w / 2) if anchor == "mm" else int(x)
    y0 = int(y - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    A = a[ya - y0:yb - y0, xa - x0:xb - x0, None] * op
    sh = cv2.GaussianBlur(A, (0, 0), size * 0.07)
    if sh.ndim == 2:
        sh = sh[..., None]
    reg = f[ya:yb, xa:xb]
    reg *= 1 - 0.8 * sh
    if glow_amt:
        gl = cv2.GaussianBlur(A, (0, 0), size * 0.18)
        if gl.ndim == 2:
            gl = gl[..., None]
        reg += gl * np.array(color, np.float32) * glow_amt
    reg[:] = reg * (1 - A) + np.array(color, np.float32) * 1.05 * A
