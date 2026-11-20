"""Motion-graphics Short (owner 2026-11-20): one continuous journey of own animation, 1080x1920, every sentence a
zoom in or out, timed to the voice. First use: video 09 Short "rip" (the owner's script).

  python short_motion.py <timeline.json> <voice.wav> <captions.txt> <music.mp3> <fonts_dir> <out.mp4> [--speed 1.1]

captions.txt: the owner's Roman (Hinglish) script, one word per spoken word, used for the one-word gold captions.
"""
import argparse, json, math, os, re, subprocess, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes as S  # noqa: E402
import sfx as fx    # noqa: E402

W, H, FPS = 1080, 1920, 30
S.W, S.H = W, H
AMBER, ICE, RIP = (66, 194, 245), (255, 220, 150), (60, 110, 255)
cl, ss, eo, ei = S.cl, S.ss, S.eo, S.ei


def words(tl, speed):
    s = tl["sections"][0]
    txt = "".join(s["chars"])
    return [(s["char_start"][m.start()] / speed, m.group()) for m in re.finditer(r"\S+", txt)]


# ------------------------------------------------------------------ shots (each draws in its own local time u)
def sky(t, seed=1, dim=0.8):
    return S.background(t, push=0.0, dim=dim, seed=seed)


def shot_orbit(u, T, f):
    """A star with planets; the blue planet breaks free on T['free'] and drifts towards us."""
    cx, cy = W / 2, H * 0.47
    z = 1 + 0.05 * u
    S.glow(f, cx, cy, 150 * z, (120, 200, 255), 0.5)
    S.glow(f, cx, cy, 46 * z, (230, 245, 255), 2.2)
    for R, w, c, r, key in ((190, 1.4, (150, 150, 200), 15, 0), (320, 0.9, (255, 170, 80), 28, 1), (450, 0.6, (120, 160, 220), 20, 0)):
        R *= z
        ry = R * 0.38
        cv2.ellipse(f, (int(cx), int(cy)), (int(R), int(ry)), 0, 0, 360, (80, 80, 80), 1, cv2.LINE_AA)
        th = w * u + key
        if key == 1 and u > T["free"]:
            th0 = w * T["free"] + 1
            x0, y0 = cx + R * math.cos(th0), cy + ry * math.sin(th0)
            vx, vy = -R * w * math.sin(th0), ry * w * math.cos(th0)
            k = u - T["free"]
            x, y = x0 + vx * k * (1 + 1.5 * k), y0 + vy * k * (1 + 1.5 * k)
            r = r * (1 + 0.9 * k)
            cv2.line(f, (int(x0), int(y0)), (int(x), int(y)), (255, 170, 80), 2, cv2.LINE_AA)
        else:
            x, y = cx + R * math.cos(th), cy + ry * math.sin(th)
        cv2.circle(f, (int(x), int(y)), int(r * z), c, -1, cv2.LINE_AA)
        S.glow(f, x, y, r * z, c, 0.5)


def shot_cluster(u, T, f):
    """Far out: a cluster of galaxies, scattering on T['scatter']."""
    r0, a, zz, col, size = S._galaxies(160)
    cx, cy = W / 2, H * 0.47
    e = 1 + (2.2 * ei(cl((u - T["scatter"]) / 1.6)) if u > T["scatter"] else 0) + 0.04 * u
    for i in range(len(r0)):
        rr = r0[i] * 420 * e / zz[i]
        x, y = cx + rr * math.cos(a[i]), cy + rr * math.sin(a[i]) * 1.2
        if -50 < x < W + 50 and -50 < y < H + 50:
            cv2.ellipse(f, (int(x), int(y)), (int(size[i] * 3), int(size[i] * 1.4)), (a[i] * 57) % 180, 0, 360,
                        tuple(float(v) for v in col[i]), -1, cv2.LINE_AA)
    f += cv2.GaussianBlur(f, (0, 0), 4) * 0.6


def shot_grip(u, T, f):
    """Back in the star system: space stretching (grid), gravity lines thinning, snapping on T['lose']."""
    cx, cy = W / 2, H * 0.47
    grow = math.exp(0.18 * u)
    sp = 120 * grow
    grid = np.zeros((H, W, 3), np.float32)
    for k in range(-20, 21):
        gx, gy = cx + k * sp, cy + k * sp
        if 0 <= gx < W:
            cv2.line(grid, (int(gx), 0), (int(gx), H), (170, 110, 60), 1, cv2.LINE_AA)
        if 0 <= gy < H:
            cv2.line(grid, (0, int(gy)), (W, int(gy)), (170, 110, 60), 1, cv2.LINE_AA)
    f += grid * 0.45 * ss((u - T["grow"] + 0.4) / 0.6)
    S.glow(f, cx, cy, 90, (120, 200, 255), 0.5)
    S.glow(f, cx, cy, 28, (230, 245, 255), 2.0)
    pre = cl((u - T["grav"]) / max(0.5, T["lose"] - T["grav"]))
    for i, (R, w, c) in enumerate(((200, 1.2, (150, 150, 200)), (330, 0.8, (255, 170, 80)), (450, 0.55, (200, 190, 160)))):
        ry = R * 0.38
        if u < T["lose"]:
            th = w * u + i * 2
            x, y = cx + R * math.cos(th), cy + ry * math.sin(th)
            th_ = max(1, int(8 * (1 - pre)))
            lay = np.zeros((H, W, 3), np.float32)
            cv2.line(lay, (int(cx), int(cy)), (int(x), int(y)), (110, 200, 255), th_, cv2.LINE_AA)
            f += (lay + cv2.GaussianBlur(lay, (0, 0), 6)) * (0.9 - 0.5 * pre) * ss((u - T["grav"] + 0.3) / 0.4)
        else:
            th0 = w * T["lose"] + i * 2
            x0, y0 = cx + R * math.cos(th0), cy + ry * math.sin(th0)
            k = u - T["lose"]
            x = x0 - R * w * math.sin(th0) * k * (1 + 2 * k)
            y = y0 + ry * w * math.cos(th0) * k * (1 + 2 * k)
        cv2.circle(f, (int(x), int(y)), 22, c, -1, cv2.LINE_AA)
        S.glow(f, x, y, 22, c, 0.5)
    if u < T["lose"] and u > T["grav"] - 0.2:
        S.text(f, "GRAVITY", W / 2, cy - 290, 64, "Anton", (110, 200, 255), ss((u - T["grav"]) / 0.4) * (1 - 0.6 * pre), "mm")
    if T["lose"] < u < T["lose"] + 0.25:
        f += 70 * (1 - (u - T["lose"]) / 0.25)


def shot_dive(u, T, f):
    """Dive into the planet: sphere -> soil -> grains -> one atom (exponential zoom, arriving on T['atom'])."""
    D = T["atom"]
    k = cl(u / D)
    z = math.exp(6.5 * ei(k))                     # total zoom ~ x660
    cx, cy = W / 2, H * 0.47
    if z < 6:                                      # the planet, growing until its surface fills the screen
        R = 260 * z
        lay = np.zeros((H, W, 3), np.float32)
        cv2.circle(lay, (int(cx), int(cy)), int(R), (210, 150, 70), -1, cv2.LINE_AA)
        rng = np.random.default_rng(3)
        for _ in range(40):
            a, r, s = rng.uniform(0, 6.28), rng.uniform(0, 0.9), rng.uniform(0.05, 0.2)
            cv2.circle(lay, (int(cx + R * r * math.cos(a)), int(cy + R * r * math.sin(a))), int(R * s), (80, 120, 170), -1, cv2.LINE_AA)
        f[:] = f * (1 - (lay.sum(-1, keepdims=True) > 0)) + lay
        S.glow(f, cx - R * 0.3, cy - R * 0.3, R * 0.5, (255, 255, 255), 0.15)
    if z > 3:                                      # soil grains
        op = ss((z - 3) / 6) * (1 - ss((z - 120) / 80))
        rng = np.random.default_rng(4)
        g = z / 20
        for _ in range(140):
            x, y = rng.uniform(-1, 1), rng.uniform(-1, 1)
            px, py = cx + x * 600 * g, cy + y * 1000 * g
            r = rng.uniform(20, 60) * g
            if -r < px < W + r and -r < py < H + r:
                cv2.circle(f, (int(px), int(py)), int(r), tuple(float(v) * op for v in (90, 130, 170)), -1, cv2.LINE_AA)
    if z > 60:                                     # the atom appears at the centre
        op = ss((z - 60) / 200)
        S.glow(f, cx, cy, 30, (120, 170, 255), 1.4 * op)
        S.glow(f, cx, cy, 10, (255, 255, 255), 2.0 * op)
        lay = np.zeros((H, W, 3), np.float32)
        for j in range(3):
            cv2.ellipse(lay, (int(cx), int(cy)), (260, 90), j * 60 + 15, 0, 360, (255, 220, 160), 3, cv2.LINE_AA)
        f += (lay + cv2.GaussianBlur(lay, (0, 0), 5)) * op


def _atom(f, u, cx, cy, stretch=1.0, jit=0.0, op=1.0):
    S.glow(f, cx + jit, cy, 32, (120, 170, 255), 1.4 * op)
    S.glow(f, cx + jit, cy, 11, (255, 255, 255), 2.2 * op)
    lay = np.zeros((H, W, 3), np.float32)
    for j in range(3):
        ang = j * 60 + 15
        ax = (int(260 * stretch), 90)
        cv2.ellipse(lay, (int(cx + jit), int(cy)), ax, ang, 0, 360, (255, 220, 160), 3, cv2.LINE_AA)
        th = u * 3.5 + j * 2.1
        ex, ey = ax[0] * math.cos(th), ax[1] * math.sin(th)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        S.glow(f, cx + jit + ex * ca - ey * sa, cy + ex * sa + ey * ca, 9, (255, 230, 180), 2.0 * op)
    f += (lay + cv2.GaussianBlur(lay, (0, 0), 5)) * op


def shot_break(u, T, f):
    """The atom, stretched by space; cracks on T['tod']."""
    cx, cy = W / 2, H * 0.47
    k = ei(cl(u / max(0.5, T["tod"] + 0.6)))
    jit = 10 * k * math.sin(u * 70)
    _atom(f, u, cx, cy, 1 + 0.9 * k, jit)
    if u > T["tod"]:
        rng = np.random.default_rng(5)
        a = eo((u - T["tod"]) / 0.3)
        for _ in range(7):
            ang = rng.uniform(0, 6.28)
            L = rng.uniform(120, 300) * a
            cv2.line(f, (int(cx), int(cy)), (int(cx + L * math.cos(ang)), int(cy + L * math.sin(ang))), (255, 255, 255), 3, cv2.LINE_AA)
    S.text(f, "?", W / 2, H * 0.75, 260, "Anton", AMBER, ss((u - T["tod"] - 0.2) / 0.3), "mm")


def shot_gauge(u, T, f):
    """A dark-energy gauge: the needle swings into PHANTOM on T['khas']; the atom waits, small, above it."""
    _atom(f, u, W / 2, H * 0.27, 0.55, 0, 0.8)
    cx, cy, R = W / 2, H * 0.62, 330
    for a0, a1, c in ((180, 300, (200, 160, 120)), (300, 360, (110, 80, 230))):
        cv2.ellipse(f, (int(cx), int(cy)), (R, R), 0, a0, a1, c, 26, cv2.LINE_AA)
    S.text(f, "DARK ENERGY", cx, cy - R - 90, 70, "Anton", (255, 255, 255), eo(u / 0.4), "mm")
    S.text(f, "PHANTOM", cx + 230, cy - 150, 48, "Anton", (130, 110, 255), eo((u - T["khas"]) / 0.4), "mm")
    ang = math.radians(200 + 130 * eo((u - T["khas"] + 0.3) / 0.8) + 4 * math.sin(u * 9))
    cv2.line(f, (int(cx), int(cy)), (int(cx + (R - 40) * math.cos(ang)), int(cy + (R - 40) * math.sin(ang))), (255, 255, 255), 8, cv2.LINE_AA)
    S.glow(f, cx, cy, 16, (255, 255, 255), 1.6)


def shot_end(u, T, f):
    p = eo(u / 0.4)
    S.text(f, "WATCH THE", W / 2, H * 0.40, 120, "Anton", (255, 255, 255), p, "mm")
    S.text(f, "FULL VIDEO", W / 2, H * 0.48, 150, "Anton", AMBER, eo((u - 0.15) / 0.4), "mm")
    y = H * 0.60 + 30 * math.sin(u * 6)
    a = eo((u - 0.3) / 0.4)
    cv2.arrowedLine(f, (int(W / 2), int(y)), (int(W / 2), int(y + 220)), tuple(float(v) * a for v in AMBER), 14, cv2.LINE_AA, tipLength=0.35)




# ------------------------------------------------------------------ Short "crunch" (owner's script, 2026-11-20)
def _gal(f, x, y, s, c, ang=20, op=1.0):
    cv2.ellipse(f, (int(x), int(y)), (int(s * 2.2), int(s)), ang, 0, 360, tuple(float(v) * op for v in c), -1, cv2.LINE_AA)
    S.glow(f, x, y, s * 1.4, c, 0.6 * op)
    S.glow(f, x, y, max(2, s * 0.35), (255, 255, 255), 1.4 * op)


def shot_shrink(u, T, f):
    """The whole universe shrinking: galaxies pulled in towards the centre."""
    r0, a, zz, col, size = S._galaxies(260)
    cx, cy = W / 2, H * 0.47
    e = 1.5 - 1.1 * ei(cl((u - T["shrink"] + 0.6) / 2.2))
    for i in range(len(r0)):
        rr = r0[i] * 520 * e / zz[i]
        x, y = cx + rr * math.cos(a[i] + 0.4 * (1.5 - e)), cy + rr * math.sin(a[i] + 0.4 * (1.5 - e)) * 1.25
        _gal(f, x, y, size[i] * 1.6, col[i], (a[i] * 57) % 180)
    S.glow(f, cx, cy, 60 + 120 * (1.5 - e), (180, 220, 255), 0.4 + 1.2 * (1.5 - e))


def _band(f, u, T, morph=None):
    """A rubber band between two pegs with two dots: stretched apart on stretch->door, released on chhodo."""
    cy = H * 0.50
    d0, d1 = 130, 400
    if T.get("stretch") is not None and u < T.get("chhodo", 1e9):
        d = d0 + (d1 - d0) * eo((u - T["stretch"]) / max(0.4, T["door"] - T["stretch"] + 0.3))
    elif T.get("chhodo") is not None and u >= T["chhodo"]:
        k = u - T["chhodo"]
        d = d0 + (d1 - d0) * math.exp(-k * 3.2) * math.cos(k * 7)
    else:
        d = d0
    th = max(5, int(26 * (d0 / d)))
    lay = np.zeros((H, W, 3), np.float32)
    pts = np.array([(W / 2 - d - 60, cy), (W / 2 - d, cy - 8), (W / 2, cy + (6 if d > 300 else 14)), (W / 2 + d, cy - 8), (W / 2 + d + 60, cy)], np.int32)
    cv2.polylines(lay, [pts], False, (60, 120, 230), th, cv2.LINE_AA)
    f += lay + cv2.GaussianBlur(lay, (0, 0), 4) * 0.6
    for sgn in (-1, 1):
        x = W / 2 + sgn * d
        if morph is not None and u > morph:
            op = eo((u - morph) / 0.5)
            cv2.circle(f, (int(x), int(cy - 10)), 18, tuple(float(v) * (1 - op) for v in (255, 255, 255)), -1, cv2.LINE_AA)
            _gal(f, x, cy - 10, 60, (255, 210, 180) if sgn < 0 else (200, 225, 255), 25 * sgn, op)
        else:
            cv2.circle(f, (int(x), int(cy - 10)), 30, (255, 255, 255), -1, cv2.LINE_AA)
            S.glow(f, x, cy - 10, 30, (255, 255, 255), 0.6)
    return d


def shot_band(u, T, f):
    d = _band(f, u, T)
    if T.get("stretch") is not None and u > T["stretch"] and u < T["chhodo"]:
        S.text(f, "STRETCH", W / 2, H * 0.36, 90, "Anton", (255, 255, 255), eo((u - T["stretch"]) / 0.3), "mm")
    if u > T["chhodo"]:
        S.text(f, "RELEASE", W / 2, H * 0.36, 90, "Anton", AMBER, eo((u - T["chhodo"]) / 0.3), "mm")


def shot_band_gal(u, T, f):
    _band(f, u, {}, morph=T["gal"])
    S.text(f, "GALAXIES", W / 2, H * 0.36, 90, "Anton", AMBER, eo((u - T["gal"]) / 0.4), "mm")


def shot_stop(u, T, f):
    """Galaxies flying apart, slowing until the expansion stops on T['band']."""
    r0, a, zz, col, size = S._galaxies(160)
    cx, cy = W / 2, H * 0.47
    k = cl(u / max(0.5, T["band"]))
    e = 0.7 + 0.6 * (1 - (1 - k) ** 2)
    for i in range(len(r0)):
        rr = r0[i] * 520 * e / zz[i]
        x, y = cx + rr * math.cos(a[i]), cy + rr * math.sin(a[i]) * 1.25
        _gal(f, x, y, size[i] * 1.6, col[i], (a[i] * 57) % 180)
        if i % 5 == 0 and k < 1:
            L = 90 * (1 - k)
            cv2.arrowedLine(f, (int(x), int(y)), (int(x + L * math.cos(a[i])), int(y + L * math.sin(a[i]) * 1.25)), (120, 200, 255), 3, cv2.LINE_AA, tipLength=0.35)
    S.text(f, "EXPANSION STOPS", W / 2, H * 0.70, 84, "Anton", (255, 255, 255), eo((u - T["band"]) / 0.4), "mm")


def shot_together(u, T, f):
    """Then galaxies start coming back together."""
    r0, a, zz, col, size = S._galaxies(160)
    cx, cy = W / 2, H * 0.47
    e = 1.3 - 0.8 * ei(cl(u / 3.0))
    for i in range(len(r0)):
        rr = r0[i] * 520 * e / zz[i]
        x, y = cx + rr * math.cos(a[i]), cy + rr * math.sin(a[i]) * 1.25
        _gal(f, x, y, size[i] * 1.6, col[i], (a[i] * 57) % 180)
        if i % 5 == 0:
            L = 40 + 80 * ei(cl(u / 3.0))
            cv2.arrowedLine(f, (int(x), int(y)), (int(x - L * math.cos(a[i])), int(y - L * math.sin(a[i]) * 1.25)), (90, 170, 255), 3, cv2.LINE_AA, tipLength=0.35)


def shot_bigcrunch(u, T, f):
    """Everything falls into one blazing point: BIG CRUNCH, then the time: 20 billion years."""
    r0, a, zz, col, size = S._galaxies(300)
    cx, cy = W / 2, H * 0.47
    k = ei(cl(u / max(0.5, T["bc"] + 0.4)))
    for i in range(len(r0)):
        rr = r0[i] * 520 * (1 - 0.97 * k) / zz[i]
        x, y = cx + rr * math.cos(a[i] + 2 * k), cy + rr * math.sin(a[i] + 2 * k) * 1.25
        cv2.circle(f, (int(x), int(y)), max(1, int(size[i])), tuple(float(v) for v in col[i]), -1, cv2.LINE_AA)
    S.glow(f, cx, cy, 30 + 120 * k, (180, 220, 255), 0.4 + 1.3 * k)
    if u > T["bc"]:
        f += 120 * math.exp(-(u - T["bc"]) * 6)
        S.text(f, "BIG CRUNCH", W / 2, H * 0.24, 130, "Anton", (255, 255, 255), eo((u - T["bc"]) / 0.3), "mm")
    if u > T["crore"] - 0.4:
        p = eo((u - T["crore"] + 0.4) / 0.4)
        S.text(f, "20 BILLION YEARS", W / 2, H * 0.64, 100, "Anton", AMBER, p, "mm")
        S.text(f, "(2,000 CRORE SAAL)", W / 2, H * 0.70, 52, "Montserrat", (230, 230, 230), p, "mm", "Bold")


def shot_light(u, T, f):
    """Space shrinking squeezes light: the wave's wavelength gets shorter and it shifts towards blue-white."""
    k = ei(cl((u - T["light"] + 0.6) / 2.4))
    lam = 420 * (1 - 0.75 * k)
    c = np.array([60, 80, 255]) * (1 - k) + np.array([255, 220, 160]) * k
    lay = np.zeros((H, W, 3), np.float32)
    pts = [(x, H * 0.47 + 140 * math.sin(2 * math.pi * (x / lam) - u * 6)) for x in range(0, W, 4)]
    cv2.polylines(lay, [np.array(pts, np.int32)], False, tuple(float(v) for v in c), 8, cv2.LINE_AA)
    f += lay + cv2.GaussianBlur(lay, (0, 0), 10) * 1.5
    S.text(f, "LIGHT", W / 2, H * 0.30, 100, "Anton", tuple(float(v) for v in c), eo((u - T["light"]) / 0.3), "mm")
    S.text(f, "?", W / 2, H * 0.70, 240, "Anton", AMBER, eo((u - T["kya"]) / 0.3), "mm")


PLANS = {
    "rip": {"title": ("COULD SPACE", "TEAR AN ATOM?"),
            "shots": [shot_orbit, shot_cluster, shot_grip, shot_dive, shot_break, shot_gauge, shot_end],
            "zoom": [None, False, True, True, True, False, False],
            "starts": ["", "Big", "फिर", "अब", "क्या", "इसके", "वो"],
            "events": {"free": "छूट", "scatter": "बिखरने", "grow": "फैलाव", "grav": "gravity", "lose": "खो", "atom": "zoom",
                       "tod": "तोड़", "khas": "ख़ास"},
            "hits": [("kz_thud", "@0", 0.0), ("kz_shot", "free", -6), ("kz_whoosh", "s1", -2), ("kz_whoosh", "scatter", -6),
                     ("kz_whoosh", "s2", -2), ("kz_shot", "lose", -3), ("kz_whoosh", "s3", -2), ("kz_thud", "atom", -4),
                     ("kz_scratch", "tod", -4), ("kz_whoosh", "s5", -4), ("kz_thud", "khas", -6), ("bell", "s6", -6)]},
    "crunch": {"title": ("WILL THE UNIVERSE", "SHRINK BACK?"),
               "shots": [shot_shrink, shot_band, shot_band_gal, shot_stop, shot_together, shot_bigcrunch, shot_light, shot_end],
               "zoom": [None, True, False, False, True, True, True, False],
               "starts": ["", "Rubber", "अब", "एक", "फिर", "उस", "और", "नीचे"],
               "events": {"shrink": "shrink", "stretch": "Stretch", "door": "दूर", "chhodo": "छोड़ो", "gal": "galaxies@2",
                          "band": "बंद", "bc": "Crunch", "crore": "करोड़", "light": "light", "kya": "क्या"},
               "hits": [("kz_thud", "@0", 0.0), ("kz_whoosh", "s1", -2), ("kz_whoosh", "stretch", -4), ("kz_thud", "chhodo", -4),
                        ("kz_whoosh", "s2", -3), ("kz_whoosh", "s3", -3), ("kz_thud", "band", -6), ("kz_whoosh", "s4", -3),
                        ("kz_shot", "bc", -2), ("kz_thud", "crore", -6), ("kz_whoosh", "s6", -3), ("bell", "s7", -6)]},
}
PLAN = PLANS["rip"]


def build_timing(wd):
    """Shot starts on sentence starts (first word, searched after the previous start); events from the words.
    An event word 'x@k' is searched from shot k's start."""
    def at(word, after=0.0):
        for t, w in wd:
            if t >= after - 1e-6 and word in w:
                return t
        raise SystemExit(f"word not found: {word}")
    starts = [0.0]
    for w in PLAN["starts"][1:]:
        starts.append(at(w, starts[-1] + 0.01))
    ev = {}
    for k, w in PLAN["events"].items():
        word, _, sh = w.partition("@")
        ev[k] = at(word, starts[int(sh)] if sh else 0.0)
    return starts, ev


def frame(t, starts, ev, total, caps, fonts):
    S.FONTS["dir"] = fonts
    i = max(k for k in range(len(starts)) if starts[k] <= t)
    def draw(j, tt):
        g = S.background(tt, push=0.0, dim=0.8 if j != 1 else 0.6, seed=1 + j)
        u = tt - starts[j]
        T = {k: v - starts[j] for k, v in ev.items()}
        PLAN["shots"][j](u, T, g)
        return g
    f = draw(i, t)
    tr = 0.4
    if i > 0 and t - starts[i] < tr:                  # zoom transition from the previous shot
        p = eo((t - starts[i]) / tr)
        prev = draw(i - 1, t)
        zin = PLAN["zoom"][i]
        s_prev = 1 + (2.2 * p if zin else -0.6 * p)
        s_new = (0.45 + 0.55 * p) if zin else (1.8 - 0.8 * p)
        Mp = cv2.getRotationMatrix2D((W / 2, H * 0.47), 0, s_prev)
        Mn = cv2.getRotationMatrix2D((W / 2, H * 0.47), 0, s_new)
        f = cv2.warpAffine(prev, Mp, (W, H)) * (1 - p) + cv2.warpAffine(f, Mn, (W, H)) * p
    S.bloom(f, 0.45) if False else None
    # bloom at portrait size
    small = cv2.resize(f, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = np.clip(small - 150, 0, None)
    f = f + cv2.resize(cv2.GaussianBlur(br, (0, 0), 6) + cv2.GaussianBlur(br, (0, 0), 16), (W, H)) * 0.5
    # top title band + one-word gold captions
    band = np.zeros((H, W, 1), np.float32)
    band[:330] = 0.55
    f = f * (1 - band)
    S.text(f, PLAN["title"][0], W / 2, 120, 92, "Anton", (255, 255, 255), 1.0, "mm")
    S.text(f, PLAN["title"][1], W / 2, 230, 104, "Anton", AMBER, 1.0, "mm")
    if t < starts[-1]:
        cur = [w for (wt, w) in caps if wt <= t]
        if cur:
            S.text(f, cur[-1].upper().strip(",.?"), W / 2, H * 0.83, 110, "Anton", AMBER, 1.0, "mm")
    pb = np.zeros((H, W, 3), np.float32)                          # progress bar
    cv2.rectangle(pb, (0, H - 14), (int(W * min(1, t / total)), H), AMBER, -1)
    f = np.maximum(f, pb)
    return S.finish(f, t)


def main():
    ap = argparse.ArgumentParser()
    for a in ("timeline", "voice", "captions", "music", "fonts", "out"):
        ap.add_argument(a)
    ap.add_argument("--speed", type=float, default=1.1)
    ap.add_argument("--kind", default="rip", help=", ".join(PLANS))
    ap.add_argument("--tail", type=float, default=1.6)
    a = ap.parse_args()
    global PLAN
    PLAN = PLANS[a.kind]
    tl = json.load(open(a.timeline))
    wd = words(tl, a.speed)
    roman = open(a.captions).read().split()
    caps = list(zip([t for t, _ in wd], roman)) if len(roman) == len(wd) else [(t, w) for t, w in wd]
    starts, ev = build_timing(wd)
    total = tl["total"] / a.speed + a.tail
    work = os.path.splitext(a.out)[0] + "_work"
    os.makedirs(work, exist_ok=True)
    # audio: voice at speed, music bed (Darkest Child from 32 s, low), sound hits on the events
    vw = os.path.join(work, "voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.voice, "-af", f"atempo={a.speed},loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-ac", "1", vw], check=True)
    import soundfile as sf
    v, sr = sf.read(vw)
    n = int((total + 0.5) * sr)
    mix = np.zeros((n, 2), np.float32)
    mix[:len(v), 0] += v[:n]
    mix[:len(v), 1] += v[:n]
    mw = os.path.join(work, "music.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "32", "-i", a.music, "-t", str(total + 0.5), "-af",
                    f"loudnorm=I=-31:TP=-6,afade=t=out:st={total - 1.2}:d=1.2", "-ar", "44100", "-ac", "2", mw], check=True)
    m, _ = sf.read(mw)
    mix[:len(m)] += m[:n]
    def when(k):
        return 0.0 if k == "@0" else (starts[int(k[1:])] - 0.2 if k[0] == "s" and k[1:].isdigit() else ev[k])
    hits = [(kind, when(k), g) for kind, k, g in PLAN["hits"]]
    for kind, t0, g in hits:
        x, pl = fx.make(kind) if kind != "riser" else fx.make(kind, d=1.2)
        x = x * 10 ** ((-16 + fx.LEVEL.get(kind, -15) + g + 3 - pl) / 20)
        i = int(max(0, t0) * sr)
        mix[i:i + len(x)] += x[:max(0, n - i)]
    mix *= 10 ** (2 / 20)
    aw = os.path.join(work, "mix.wav")
    sf.write(aw, np.clip(mix, -1, 1), sr)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", aw, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                           "-af", "loudnorm=I=-14:TP=-1.5", "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for k in range(int(total * FPS)):
        ff.stdin.write(frame(k / FPS, starts, ev, total, caps, a.fonts).tobytes())
    ff.stdin.close()
    ff.wait()
    print("wrote", a.out, f"{total:.1f}s")


if __name__ == "__main__":
    main()
