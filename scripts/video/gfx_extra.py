"""Explainer graphics absorbed from the owner's "documentary-2d-animation" skill (owner, 2026-11-19), drawn the way
the rest of our graphics are (OpenCV + PIL, no new dependencies). Used from edit.spec G lines; render_video.gfx()
hands these names over. Items separated by ";" (the G line keeps everything after " @ ").

  G <trigger> @ countdown:<KICKER>;<VALUE>=<label>;<VALUE>=<label>;...
        3-5 cards in a row that appear one by one over dimmed footage, joined by an arrow (a progression / countdown).
        e.g. countdown:THE BIG RIP COUNTDOWN;60 MILLION YEARS=Milky Way torn apart;3 MONTHS=planets fly off;
             30 MINUTES=Earth explodes;A SPLIT SECOND=atoms break
  G <trigger> @ stamp:<WORD>[;<small line>]
        a rubber stamp that slams onto the footage. Colour by word: CONFIRMED/PROVEN/TRUE/SACH green,
        DEBUNKED/MYTH/WRONG/FALSE red, anything else (NOT CONFIRMED YET, OPEN QUESTION, HINT) amber.
  G <trigger> @ journal:<date>;<line>;<line>;...
        a cream notebook page over a dark desk: the date (italic serif) and the lines write on one by one; a line
        wrapped in *stars* gets a crimson ink underline. Dates as "14 July 1916". Good for history beats and quotes,
        and in place of a photo when no free-licence portrait exists.
  G <trigger> @ compare:<object>;<label>[;<size label>]
        a glowing amber wireframe of an everyday Indian object with a size bar (Indian comparisons, science-script-v2
        §3c). Objects: auto (auto-rickshaw), swift (Maruti Swift), pitch (cricket pitch), coach (Mumbai local train
        coach), ball (cricket ball, thrown up and falling back). The size label is your verified number
        (e.g. "~3.8 M LONG").
  blueprint backdrop: dark navy engineering grid with corner brackets; `G ... @ blueprint:<TITLE>` draws it alone, and
        bp(frame) can be used by other diagrams.
"""
import math, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

FONTS = {"dir": ""}
W, H = 1920, 1080
AMBER = (66, 194, 245)      # BGR of #F5C242
NAVY = (41, 27, 8)          # BGR of #081B29
CRIMSON = (43, 59, 201)     # BGR of #C93B2B
CREAM = (211, 234, 242)     # BGR of #F2EAD3
NAMES = ("countdown", "stamp", "journal", "compare", "blueprint")


def ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def ease_back(p, s=1.7):
    p = min(max(p, 0.0), 1.0) - 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def _font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS["dir"], f"{name}.ttf"), int(size))
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


def text_layer(text, size, font="Anton", color=(255, 255, 255), weight=None, shadow=True):
    """(bgr float, alpha float) of text; color is BGR."""
    f = _font(font, size, weight)
    b = f.getbbox(text)
    pad = int(size * 0.3)
    w, h = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((pad - b[0], pad - b[1]), text, font=f, fill=255)
    a = np.array(m, np.float32) / 255
    bgr = np.empty((h, w, 3), np.float32)
    bgr[:] = color
    if shadow:
        sh = cv2.GaussianBlur(np.roll(a, (int(size * 0.04), int(size * 0.03)), (0, 1)), (0, 0), max(1, size * 0.05)) * 0.7
        bgr = bgr * (a / np.maximum(a + sh * (1 - a), 1e-4))[..., None]
        a = a + sh * (1 - a)
    return bgr, a


def blit(f, layer, cx, cy, op=1.0, scale=1.0, angle=0.0):
    bgr, a = layer
    if scale <= 0.02 or op <= 0.01:
        return
    if abs(scale - 1) > 1e-3 or abs(angle) > 1e-3:
        h, w = a.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
        c, s = abs(M[0, 0]), abs(M[0, 1])
        nw, nh = int(h * s + w * c) + 2, int(h * c + w * s) + 2
        M[0, 2] += nw / 2 - w / 2
        M[1, 2] += nh / 2 - h / 2
        bgr = cv2.warpAffine(bgr, M, (nw, nh))
        a = cv2.warpAffine(a, M, (nw, nh))
    h, w = a.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(f.shape[1], x0 + w), min(f.shape[0], y0 + h)
    if xa >= xb or ya >= yb:
        return
    A = a[ya - y0:yb - y0, xa - x0:xb - x0, None] * op
    reg = f[ya:yb, xa:xb].astype(np.float32)
    f[ya:yb, xa:xb] = np.clip(reg * (1 - A) + bgr[ya - y0:yb - y0, xa - x0:xb - x0] * A, 0, 255).astype(np.uint8)


def fit(layer, maxw):
    return min(1.0, maxw / max(1, layer[1].shape[1]))


def box(f, x0, y0, x1, y1, color=(20, 14, 8), op=0.72, r=18, border=None):
    ov = f.copy()
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    cv2.rectangle(ov, (x0 + r, y0), (x1 - r, y1), color, -1)
    cv2.rectangle(ov, (x0, y0 + r), (x1, y1 - r), color, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(ov, (cx, cy), r, color, -1, cv2.LINE_AA)
    cv2.addWeighted(ov, op, f, 1 - op, 0, f)
    if border:
        cv2.rectangle(f, (x0, y0), (x1, y1), border, 2, cv2.LINE_AA)


# ------------------------------------------------------------------ blueprint backdrop
def bp(f, op=1.0, t=0.0):
    """Dark navy engineering grid with four corner brackets over the frame."""
    g = np.zeros_like(f)
    g[:] = NAVY
    for x in range(0, W, 60):
        cv2.line(g, (x, 0), (x, H), (70, 52, 30) if x % 300 else (95, 72, 42), 1)
    for y in range(0, H, 60):
        cv2.line(g, (0, y), (W, y), (70, 52, 30) if y % 300 else (95, 72, 42), 1)
    m, L = 60, 80
    for sx, sy in ((m, m), (W - m, m), (m, H - m), (W - m, H - m)):
        dx, dy = (1 if sx < W / 2 else -1), (1 if sy < H / 2 else -1)
        cv2.line(g, (sx, sy), (sx + dx * L, sy), (255, 255, 255), 3, cv2.LINE_AA)
        cv2.line(g, (sx, sy), (sx, sy + dy * L), (255, 255, 255), 3, cv2.LINE_AA)
    cv2.addWeighted(g, op, f, 1 - op, 0, f)
    return f


# ------------------------------------------------------------------ countdown / progression cards
def countdown(f, args, t, D):
    kicker, steps = (args[0], args[1:]) if args and "=" not in args[0] else ("", args)
    steps = [s.split("=", 1) if "=" in s else (s, "") for s in steps][:5]
    n = max(1, len(steps))
    f[:] = (f.astype(np.float32) * 0.55).astype(np.uint8)
    gap = 40
    cw = min(420, (W - 160 - gap * (n - 1)) / n)
    total = n * cw + (n - 1) * gap
    x0, cy, ch = (W - total) / 2, H * 0.53, 300
    if kicker:
        k = text_layer(kicker.upper(), 46, "Montserrat", (255, 255, 255), "Bold")
        blit(f, k, W / 2, H * 0.26, ease(t / 0.3), fit(k, W - 200))
    span = max(0.6, D * 0.78)
    for i, (val, lab) in enumerate(steps):
        t0 = 0.25 + span * i / n
        p = (t - t0) / 0.3
        if p <= 0:
            continue
        x = x0 + i * (cw + gap)
        e = ease_back(p)
        box(f, x, cy - ch / 2, x + cw, cy + ch / 2, op=0.75 * min(1, p * 2), border=AMBER if i == n - 1 else (120, 120, 120))
        v = text_layer(val.strip().upper(), 78, "Anton", AMBER)
        blit(f, v, x + cw / 2, cy - 45, min(1, p * 2), fit(v, cw - 40) * (0.8 + 0.2 * e))
        if lab:
            words, lines, cur = lab.strip().split(), [], ""
            for w_ in words:  # wrap the label in two lines at most
                if len(cur) + len(w_) > 18 and cur:
                    lines.append(cur)
                    cur = w_
                else:
                    cur = (cur + " " + w_).strip()
            lines.append(cur)
            for j, ln in enumerate(lines[:2]):
                L = text_layer(ln, 40, "Montserrat", (235, 235, 235), "SemiBold")
                blit(f, L, x + cw / 2, cy + 55 + j * 50, min(1, p * 2), fit(L, cw - 30))
        if i < n - 1 and t > t0 + 0.3:  # arrow to the next card
            q = ease((t - t0 - 0.3) / 0.25)
            ax = int(x + cw + 6)
            cv2.arrowedLine(f, (ax, int(cy)), (int(ax + (gap - 12) * q), int(cy)), AMBER, 4, cv2.LINE_AA, tipLength=0.5)
    return f


# ------------------------------------------------------------------ rubber stamp
def stamp(f, args, t, D):
    word = (args[0] if args else "CONFIRMED").strip().upper()
    sub = args[1].strip() if len(args) > 1 else ""
    green = {"CONFIRMED", "PROVEN", "TRUE", "SACH", "FACT"}
    red = {"DEBUNKED", "MYTH", "WRONG", "FALSE", "JHOOTH"}
    col = (70, 175, 60) if word in green else (50, 50, 215) if word in red else (40, 170, 245)
    f[:] = (f.astype(np.float32) * 0.62).astype(np.uint8)
    t0 = 0.2
    if t < t0:
        return f
    p = (t - t0) / 0.18
    sc = 2.4 - 1.4 * ease(p) if p < 1 else 1.0 + 0.01 * (t - t0)
    lay = text_layer(word, 150, "Anton", col, shadow=False)
    h, w = lay[1].shape
    pad = 34
    canvas = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
    canvas[pad:pad + h, pad:pad + w] = lay[1]
    cv2.rectangle(canvas, (8, 8), (canvas.shape[1] - 9, canvas.shape[0] - 9), 1.0, 10)
    cv2.rectangle(canvas, (24, 24), (canvas.shape[1] - 25, canvas.shape[0] - 25), 1.0, 3)
    rng = np.random.default_rng(len(word))  # worn ink: speckle holes
    holes = cv2.GaussianBlur((rng.random(canvas.shape) > 0.86).astype(np.float32), (0, 0), 1.6)
    canvas = np.clip(canvas * (1 - holes * 0.9), 0, 1)
    bgr = np.empty(canvas.shape + (3,), np.float32)
    bgr[:] = col
    s = min(1.0, (W * 0.62) / canvas.shape[1])
    blit(f, (bgr, canvas * 0.92), W / 2, H * 0.47, min(1, p * 3), sc * s, angle=12)
    if sub and t > t0 + 0.4:
        L = text_layer(sub, 44, "Montserrat", (240, 240, 240), "SemiBold")
        blit(f, L, W / 2, H * 0.47 + canvas.shape[0] * s * 0.62 + 30, ease((t - t0 - 0.4) / 0.3), fit(L, W - 300))
    return f


# ------------------------------------------------------------------ journal card
def journal(f, args, t, D):
    date, lines = (args[0].strip() if args else ""), [a.strip() for a in args[1:]]
    f[:] = (f.astype(np.float32) * 0.3).astype(np.uint8)
    pw, ph = 1180, 700
    page = np.full((ph, pw, 3), CREAM, np.uint8)
    for y in range(150, ph - 30, 64):
        cv2.line(page, (50, y), (pw - 50, y), (190, 175, 165), 2, cv2.LINE_AA)
    cv2.line(page, (120, 0), (120, ph), (160, 160, 225), 2, cv2.LINE_AA)
    n = max(1, len(lines))
    span = max(0.8, D * 0.75)

    def put(txt, size, font, x, y, frac, color=(55, 40, 30)):
        k = int(round(len(txt) * min(1.0, max(0.0, frac))))
        if k <= 0:
            return None
        bgr, a = text_layer(txt[:k], size, font, color, shadow=False)
        h_, w_ = min(a.shape[0], ph - y), min(a.shape[1], pw - x)
        if h_ > 0 and w_ > 0:
            reg = page[y:y + h_, x:x + w_].astype(np.float32)
            A = a[:h_, :w_, None]
            page[y:y + h_, x:x + w_] = (reg * (1 - A) + bgr[:h_, :w_] * A).astype(np.uint8)
        full = text_layer(txt, size, font, color, shadow=False)[1]
        return full.shape[1]
    if date:
        put(date, 58, "LoraItalic", 150, 38, (t - 0.1) / 0.5)
    for i, ln in enumerate(lines[:6]):
        und = ln.startswith("*") and ln.endswith("*")
        txt = ln.strip("*")
        t0 = 0.5 + span * i / n
        size = 70 if len(txt) < 30 else 58
        y = 105 + i * 64 + (64 - size) // 2
        wpx = put(txt, size, "Caveat", 150, y, (t - t0) / (span / n * 0.8))
        if und and wpx and t > t0 + span / n * 0.8:
            q = ease((t - t0 - span / n * 0.8) / 0.4)
            yy = y + int(size * 1.15)
            pts = np.array([[150 + int(k), yy + int(3 * math.sin(k / 40))] for k in np.linspace(0, (wpx - 30) * q, 40)], np.int32)
            if len(pts) > 1:
                cv2.polylines(page, [pts], False, CRIMSON, 5, cv2.LINE_AA)
    z = 1.0 + 0.04 * ease(t / D)
    M = cv2.getRotationMatrix2D((pw / 2, ph / 2), -2.5 + 1.5 * ease(t / D), z)
    M[0, 2] += W / 2 - pw / 2
    M[1, 2] += H / 2 - ph / 2
    mask = cv2.warpAffine(np.full((ph, pw), 255, np.uint8), M, (W, H)).astype(np.float32) / 255
    img = cv2.warpAffine(page, M, (W, H))
    sh = cv2.GaussianBlur(cv2.warpAffine(np.full((ph, pw), 255, np.uint8), M + [[0, 0, 18], [0, 0, 26]], (W, H)), (0, 0), 22)
    f[:] = (f * (1 - sh[..., None] / 255 * 0.6)).astype(np.uint8)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)  # desk-lamp vignette
    vig = np.clip(1.25 - np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 1.6, 0.35, 1)[..., None]
    out = f * (1 - mask[..., None]) + img * mask[..., None]
    f[:] = np.clip(out * vig, 0, 255).astype(np.uint8)
    return f


# ------------------------------------------------------------------ wireframe comparisons (Indian objects)
def _wire(img, pts, closed=True, th=3):
    cv2.polylines(img, [np.array(pts, np.int32)], closed, AMBER, th, cv2.LINE_AA)


def _obj(kind, cx, cy, s):
    """Draw the object's wireframe on its own layer; returns (layer, width in px)."""
    lay = np.zeros((H, W, 3), np.uint8)
    P = lambda x, y: (int(cx + x * s), int(cy + y * s))  # noqa: E731
    if kind == "auto":  # auto-rickshaw, side view (about 2.6 m long)
        _wire(lay, [P(-130, 40), P(-130, -40), P(-90, -95), P(70, -95), P(120, -40), P(130, 40)])
        _wire(lay, [P(-60, -88), P(-60, -20), P(40, -20), P(60, -88)])
        _wire(lay, [P(70, -95), P(120, -40), P(70, -40)], closed=False)
        for x in (-95, 95):
            cv2.circle(lay, P(x, 45), int(28 * s), AMBER, 3, cv2.LINE_AA)
        w = 260
    elif kind == "swift":  # hatchback, side view (about 3.85 m)
        _wire(lay, [P(-190, 35), P(-195, -10), P(-150, -25), P(-90, -80), P(60, -82), P(130, -30), P(190, -20), P(195, 35)])
        _wire(lay, [P(-80, -70), P(-20, -70), P(-20, -30), P(-130, -30)])
        _wire(lay, [P(-5, -70), P(55, -72), P(110, -30), P(-5, -30)])
        for x in (-120, 120):
            cv2.circle(lay, P(x, 40), int(32 * s), AMBER, 3, cv2.LINE_AA)
        w = 390
    elif kind == "pitch":  # cricket pitch from above, 22 yards (20.12 m) by 3.05 m, with creases and stumps
        _wire(lay, [P(-300, -40), P(300, -40), P(300, 40), P(-300, 40)])
        for x in (-262, 262):
            cv2.line(lay, P(x, -40), P(x, 40), AMBER, 2, cv2.LINE_AA)
            for y in (-8, 0, 8):
                cv2.circle(lay, P(x + (6 if x < 0 else -6), y), max(2, int(3 * s)), AMBER, -1, cv2.LINE_AA)
        w = 600
    elif kind == "coach":  # local train coach, side view (about 20 m), windows and doors
        _wire(lay, [P(-320, -70), P(320, -70), P(330, 50), P(-330, 50)])
        for i in range(-5, 6):
            x = i * 55
            if i in (-4, 0, 4):
                _wire(lay, [P(x - 18, -60), P(x + 18, -60), P(x + 18, 45), P(x - 18, 45)])
            else:
                _wire(lay, [P(x - 16, -50), P(x + 16, -50), P(x + 16, -15), P(x - 16, -15)], th=2)
        for x in (-260, -200, 200, 260):
            cv2.circle(lay, P(x, 58), int(12 * s), AMBER, 2, cv2.LINE_AA)
        w = 660
    else:  # cricket ball (drawn by compare() along its arc)
        w = 60
    return lay, w


def compare(f, args, t, D):
    kind = (args[0] if args else "auto").strip().lower()
    label = args[1].strip() if len(args) > 1 else ""
    size = args[2].strip() if len(args) > 2 else ""
    f[:] = (f.astype(np.float32) * 0.5).astype(np.uint8)
    e = ease(t / 0.6)
    if kind == "ball":  # thrown straight up: slows, stops, falls back (the expectation before 1998)
        gx, gy = W / 2, H * 0.84
        cv2.line(f, (int(W * 0.3), int(gy + 30)), (int(W * 0.7), int(gy + 30)), AMBER, 2, cv2.LINE_AA)
        T = max(1.0, D * 0.8)
        for k in range(0, 24):  # ghost trail
            tk = t - k * 0.06
            if tk < 0:
                break
            ph_ = min(tk / T, 1.0)
            y = gy - 4 * 520 * ph_ * (1 - ph_)
            cv2.circle(f, (int(gx), int(y)), max(4, 26 - k), AMBER, 2 if k else -1, cv2.LINE_AA)
    else:
        s = 1.25
        lay, w = _obj(kind, W / 2, H * 0.5, s)
        glow = cv2.GaussianBlur(lay, (0, 0), 9)
        k = ease(t / 0.8)  # draw on from the left
        cut = int(W / 2 - w * s / 2 + w * s * k) + 20
        lay[:, cut:] = 0
        glow[:, cut:] = 0
        f[:] = np.clip(f.astype(np.float32) + glow * 1.2 + lay, 0, 255).astype(np.uint8)
        if size and t > 0.7:  # dimension bar under it
            q = ease((t - 0.7) / 0.4)
            y = int(H * 0.5 + 120 * s)
            x0, x1 = int(W / 2 - w * s / 2), int(W / 2 - w * s / 2 + w * s * q)
            cv2.line(f, (x0, y), (x1, y), (255, 255, 255), 2, cv2.LINE_AA)
            cv2.line(f, (x0, y - 14), (x0, y + 14), (255, 255, 255), 2, cv2.LINE_AA)
            if q > 0.98:
                cv2.line(f, (x1, y - 14), (x1, y + 14), (255, 255, 255), 2, cv2.LINE_AA)
            L = text_layer(size.upper(), 44, "Montserrat", (255, 255, 255), "Bold")
            blit(f, L, W / 2, y + 50, q)
    if label:
        L = text_layer(label.upper(), 64, "Anton", (255, 255, 255))
        blit(f, L, W / 2, H * 0.18, e, fit(L, W - 240))
    return f


def draw(name, t, D, f, fonts_dir):
    if not FONTS["dir"]:
        FONTS["dir"] = fonts_dir
    kind, _, rest = name.partition(":")
    args = [a for a in rest.split(";")] if rest else []
    if kind == "blueprint":
        bp(f, 1.0, t)
        if args:
            L = text_layer(args[0].upper(), 70, "Anton", (255, 255, 255))
            blit(f, L, W / 2, H * 0.12, ease(t / 0.4))
        return f
    return {"countdown": countdown, "stamp": stamp, "journal": journal, "compare": compare}[kind](f, args, t, D)
