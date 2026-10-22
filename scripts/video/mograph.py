"""Motion-graphics kit for the v3 science-channel style: typography, kinetic text and animated data cards.

Everything is drawn on BGR uint8 W x H frames: 1920x1080, or 1080x1920 for Shorts (render_short.py sets W, H and
LAYOUT before rendering). Fonts come from $MEDIA/fonts (fetch_media.sh):
Anton (condensed display), Montserrat (variable: Light ... ExtraBold), Cinzel (serif, variable).

Templates (see docs/style-guide.md for when to use which):
  headline(...)   kinetic stacked headline: kicker + 1-4 lines revealed from a mask, timed to the spoken words
  keyline(...)    one-line key phrase (names, years, numbers) revealed word by word, centre
  number cards    card(frame, spec, t, D) with spec["template"] in:
                  hero | thermo | gauge | line | scale | fact | equation | progress | chart
  overlays        the same call: callout (ring + leader + label on an object), route (map line with a counter),
                  hud (telescope/camera viewfinder), name (lower third for a person)
  chapter(...)    FACT #n card with countdown progress
  title(...)      title card
  footer(...), logo(...)  persistent journey footer and channel bug
  endcard(...)    Shorts end card: FULL VIDEO BELOW with a bouncing arrow (on screen only, never spoken)
Counts ease out and land exactly on spec["land_t"] (seconds into the card): the renderer sets it from the
narration timeline, so a number stops on the syllable that says it.
"""
import math, os, re
from functools import lru_cache
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
FONTS = {"dir": ""}
LAYOUT = {"name_y": 0.8, "logo": "right", "logo_y": 40, "label_w": 0.0}  # Shorts: name_y 0.62, logo left, labels fit

WHITE = (255, 255, 255)
GOLD = ((255, 214, 102), (236, 120, 30))       # top, bottom (RGB) for key words and hero numbers
PEACH = ((255, 228, 186), (240, 122, 30))
SILVER = ((255, 255, 255), (196, 200, 210))
KICKER = (255, 181, 71)
GLOW = (255, 140, 40)


def set_fonts(d):
    FONTS["dir"] = d


# ------------------------------------------------------------------ easing
def clamp01(p):
    return min(max(p, 0.0), 1.0)


def ease_out(p):
    p = clamp01(p)
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    p = clamp01(p)
    return p * p * (3 - 2 * p)


def ease_back(p, s=1.6):
    p = clamp01(p)
    return 1 + (s + 1) * (p - 1) ** 3 + s * (p - 1) ** 2


# ------------------------------------------------------------------ text layers
@lru_cache(maxsize=64)
def _font(name, size, weight):
    f = ImageFont.truetype(os.path.join(FONTS["dir"], f"{name}.ttf"), int(size))
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:  # noqa: BLE001  (static font)
            pass
    return f


def _measure(text, f, track):
    if not track:
        b = f.getbbox(text)
        return b[2] - b[0], b
    w = sum(f.getlength(ch) for ch in text) + track * f.size * max(0, len(text) - 1)
    b = f.getbbox(text)
    return int(w), (0, b[1], int(w), b[3])


@lru_cache(maxsize=160)
def layer(text, name="Anton", size=120, weight=None, fill=WHITE, grad=None, track=0.0, glow=None, shadow=0.55):
    """Rendered text as uint8 BGRA. grad = ((r,g,b) top, (r,g,b) bottom); glow = ((r,g,b), radius, strength);
    track = extra letter spacing in em. The layer has padding for glow and shadow; anchor = its centre."""
    f = _font(name, size, weight)
    w, b = _measure(text, f, track)
    pad = int(size * 0.35) + (int(glow[1] * 2) if glow else 0)
    tw, th = w + 2 * pad, (b[3] - b[1]) + 2 * pad
    mask = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(mask)
    x, y = pad - (b[0] if not track else 0), pad - b[1]
    if track:
        for ch in text:
            d.text((x, y), ch, font=f, fill=255)
            x += f.getlength(ch) + track * f.size
    else:
        d.text((x, y), text, font=f, fill=255)
    m = np.array(mask).astype(np.float32) / 255
    if grad:
        rows = np.where(m.max(1) > 0)[0]
        y0, y1 = (rows[0], rows[-1]) if len(rows) else (0, th - 1)
        k = np.clip((np.arange(th) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
        top, bot = np.array(grad[0], np.float32)[::-1], np.array(grad[1], np.float32)[::-1]
        col = np.broadcast_to(top + (bot - top) * k, (th, tw, 3))
    else:
        col = np.broadcast_to(np.array(fill, np.float32)[::-1], (th, tw, 3))
    out_c = col * m[..., None]
    out_a = m.copy()
    if glow:
        gc, gr, gs = glow
        small = cv2.resize(m, (max(1, tw // 4), max(1, th // 4)), interpolation=cv2.INTER_AREA)
        g = cv2.resize(cv2.GaussianBlur(small, (0, 0), max(1, gr / 4)), (tw, th)) * gs
        g = np.clip(g, 0, 1) * (1 - m)
        out_c = out_c + np.array(gc, np.float32)[::-1] * g[..., None]
        out_a = np.clip(out_a + g, 0, 1)
    if shadow:
        small = cv2.resize(np.roll(m, (int(size * 0.03), int(size * 0.02)), (0, 1)), (max(1, tw // 4), max(1, th // 4)),
                           interpolation=cv2.INTER_AREA)
        sh = cv2.resize(cv2.GaussianBlur(small, (0, 0), max(0.5, size * 0.015)), (tw, th)) * shadow
        sh = sh * (1 - out_a)
        out_a = np.clip(out_a + sh, 0, 1)  # shadow colour is black: adds alpha only
    bgra = np.dstack([np.clip(out_c / np.maximum(out_a[..., None], 1e-4), 0, 255), out_a * 255]).astype(np.uint8)
    return bgra


def paste(fr, bgra, cx, cy, op=1.0, scale=1.0, clip=None, anchor="c"):
    """Alpha-blend a layer centred at (cx, cy) (anchor "l" = left edge at cx). clip = (x0, y0, x1, y1) in frame px."""
    if op <= 0.002:
        return
    if scale != 1.0:
        bgra = cv2.resize(bgra, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = bgra.shape[:2]
    x = int(round(cx - (w / 2 if anchor == "c" else 0)))
    y = int(round(cy - h / 2))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if clip:
        x0, y0, x1, y1 = max(x0, int(clip[0])), max(y0, int(clip[1])), min(x1, int(clip[2])), min(y1, int(clip[3]))
    if x1 <= x0 or y1 <= y0:
        return
    src = bgra[y0 - y:y1 - y, x0 - x:x1 - x]
    a = src[..., 3:].astype(np.float32) * (op / 255)
    reg = fr[y0:y1, x0:x1].astype(np.float32)
    fr[y0:y1, x0:x1] = (reg + (src[..., :3] - reg) * a).astype(np.uint8)


def text_w(bgra, size):
    """Visible width of a layer (without its padding)."""
    a = bgra[..., 3]
    cols = np.where(a.max(0) > 128)[0]
    return (cols[-1] - cols[0]) if len(cols) else 0


def fit_size(text, name, size, maxw, weight=None, track=0.0):
    while size > 24:
        if _measure(text, _font(name, size, weight), track)[0] <= maxw:
            return size
        size = int(size * 0.92)
    return size


def fmt_number(v, like):
    """Format v with the decimals and the grouping style of the target string `like` ('150,000,000', '4.6')."""
    dec = len(like.split(".")[1]) if "." in like else 0
    s = f"{v:,.{dec}f}"
    return s if "," in like or abs(v) >= 10000 else s.replace(",", "")


def parse_num(s):
    s = str(s).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


# ------------------------------------------------------------------ shading helpers
@lru_cache(maxsize=8)
def _left_shade(strength, reach):
    x = np.linspace(0, 1, W, dtype=np.float32)
    g = np.clip(1 - x / reach, 0, 1) ** 1.6 * strength
    return np.repeat(g[None, :, None], H, 0)


def shade_left(fr, op=1.0, strength=0.72, reach=0.62):
    m = _left_shade(strength, reach) * op
    fr[:] = (fr.astype(np.float32) * (1 - m)).astype(np.uint8)


@lru_cache(maxsize=16)
def _ellipse(w, h):
    yy, xx = np.mgrid[-h:h, -w:w].astype(np.float32)
    d = (xx / w) ** 2 + (yy / h) ** 2
    return (np.clip(1 - d, 0, 1) ** 1.8)[..., None]  # soft edge: no visible rim on bright footage


def shade_box(fr, cx, cy, w, h, op=1.0, strength=0.6):
    m = _ellipse(int(w), int(h)) * strength * op
    x0, y0 = int(cx - w), int(cy - h)
    xs0, ys0 = max(0, -x0), max(0, -y0)
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(W, x0 + 2 * int(w)), min(H, y0 + 2 * int(h))
    if x1c <= x0c or y1c <= y0c:
        return
    mm = m[ys0:ys0 + (y1c - y0c), xs0:xs0 + (x1c - x0c)]
    reg = fr[y0c:y1c, x0c:x1c].astype(np.float32)
    fr[y0c:y1c, x0c:x1c] = (reg * (1 - mm)).astype(np.uint8)


def glow_dot(fr, cx, cy, r, color=(255, 230, 190), op=1.0):
    R = int(r * 4)
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    d = np.sqrt(xx ** 2 + yy ** 2)
    a = (np.clip(1 - d / R, 0, 1) ** 3 * 0.8 + (d < r) * 1.0)
    a = np.clip(a, 0, 1)[..., None] * op
    x0, y0 = int(cx) - R, int(cy) - R
    xa, ya = max(0, -x0), max(0, -y0)
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x0 + 2 * R + 1), min(H, y0 + 2 * R + 1)
    if x1c <= x0c or y1c <= y0c:
        return
    aa = a[ya:ya + (y1c - y0c), xa:xa + (x1c - x0c)]
    reg = fr[y0c:y1c, x0c:x1c].astype(np.float32)
    col = np.array(color[::-1], np.float32)
    fr[y0c:y1c, x0c:x1c] = np.clip(reg + (col - reg) * aa, 0, 255).astype(np.uint8)


def line_aa(fr, p0, p1, color=(255, 255, 255), op=1.0, thick=2, dash=0):
    ov = fr.copy()
    if dash:
        n = int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / dash)
        for k in range(0, n, 2):
            a = (p0[0] + (p1[0] - p0[0]) * k / n, p0[1] + (p1[1] - p0[1]) * k / n)
            b = (p0[0] + (p1[0] - p0[0]) * (k + 1) / n, p0[1] + (p1[1] - p0[1]) * (k + 1) / n)
            cv2.line(ov, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), color[::-1], thick, cv2.LINE_AA)
    else:
        cv2.line(ov, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), color[::-1], thick, cv2.LINE_AA)
    cv2.addWeighted(ov, op, fr, 1 - op, 0, fr)


# ------------------------------------------------------------------ kinetic text
def _line_spec(text):
    """'*GOLDEN*' (optionally followed by punctuation) -> gold gradient text."""
    m = re.match(r"^\*(.+)\*([,.;:!?]*)$", text)
    return (m.group(1) + m.group(2), True) if m else (text, False)


def headline(fr, spec, t):
    """spec: {lines: [{text, t}], kicker, kicker_t, sub, sub_t, t1, pos} with times in seconds on the video timeline.
    Each line rises out of its own slot in 0.18 s at its time; everything fades out over 0.25 s before t1."""
    out = clamp01((spec["t1"] - t) / 0.25)
    t_first = min([ln["t"] for ln in spec["lines"]] + [spec.get("kicker_t", 1e9)])
    if t < t_first - 0.05 or out <= 0:
        return
    pos = spec.get("pos", "left")
    shade_left(fr, min(1, (t - t_first + 0.05) / 0.3) * out) if pos == "left" else None
    x = W * 0.075 if pos == "left" else W / 2
    anchor = "l" if pos == "left" else "c"
    rows = []
    if spec.get("kicker"):
        rows.append(("kicker", spec["kicker"], spec.get("kicker_t", t_first), layer(spec["kicker"].upper(), "Montserrat", 34, "SemiBold", KICKER, track=0.35, shadow=0.4)))
    maxw = W * (0.55 if pos == "left" else 0.86)
    for ln in spec["lines"]:
        txt, gold = _line_spec(ln["text"])
        size = fit_size(txt.upper(), "Anton", spec.get("size", 190), maxw)
        rows.append(("line", txt, ln["t"], layer(txt.upper(), "Anton", size, None, grad=GOLD if gold else SILVER, shadow=0.5)))
    if spec.get("sub"):
        rows.append(("sub", spec["sub"], spec.get("sub_t", spec["lines"][-1]["t"] + 0.2), layer(spec["sub"], "Montserrat", 46, "Bold", WHITE, shadow=0.6)))
    pad = [int(r[3].shape[0] * 0.18) for r in rows]
    hs = [r[3].shape[0] - 2 * p for r, p in zip(rows, pad)]
    gap = 6
    total = sum(hs) + gap * (len(rows) - 1)
    if pos != "left":  # centred: a soft dark ellipse keeps gold text readable on bright footage
        wmax = max(text_w(r[3], 0) for r in rows)
        shade_box(fr, W / 2, H * 0.5, wmax / 2 + 220, total / 2 + 110, op=min(1, (t - t_first + 0.05) / 0.3) * out, strength=0.55)
    y = H * 0.5 - total / 2
    for (kind, txt, t0, lay), h, p in zip(rows, hs, pad):
        cy = y + h / 2
        e = ease_out((t - t0) / 0.18)
        if t >= t0 - 0.01:
            slot = (0, y - 4, W, y + h + 6)
            off = (1 - e) * h * 0.95
            xx = x - (p * 1.0 if anchor == "l" else 0)
            paste(fr, lay, xx, cy + off, op=out * min(1, 0.4 + e), clip=slot, anchor=anchor)
        y += h + gap


def keyline(fr, spec, t):
    """One centred key phrase (a name, a year, a number): words rise in, 0.07 s apart, from spec t0; out at t1."""
    t0, t1 = spec["t"], spec["t1"]
    out = clamp01((t1 - t) / 0.2)
    if t < t0 or out <= 0:
        return
    words = spec["text"].split()
    size = fit_size(spec["text"].upper(), "Anton", 150, W * 0.8)
    lays = []
    for w_ in words:
        txt, gold = _line_spec(w_)
        gold = gold or bool(re.search(r"\d", txt))
        lays.append(layer(txt.upper(), "Anton", size, None, grad=GOLD if gold else SILVER, shadow=0.55))
    sp = layer(" ", "Anton", size)[..., 3].shape[1] * 0.25
    widths = [text_w(l_, size) for l_ in lays]
    total = sum(widths) + sp * (len(lays) - 1)
    cy = H * 0.5
    shade_box(fr, W / 2, cy, total / 2 + 320, size * 1.5, op=min(1, (t - t0) / 0.25) * out, strength=0.6)
    x = W / 2 - total / 2
    for i, (lay, wd) in enumerate(zip(lays, widths)):
        e = ease_out((t - t0 - 0.07 * i) / 0.2)
        if e > 0:
            h = lay.shape[0]
            pad = (lay.shape[1] - wd) / 2
            paste(fr, lay, x - pad, cy + (1 - e) * size * 0.5, op=out * e, anchor="l",
                  clip=(0, cy - size * 0.62, W, cy + size * 0.62))
        x += wd + sp


# ------------------------------------------------------------------ number cards
def _count(spec, t):
    """Current value: ease-out from `from` to `value`, landing at land_t (s into the card)."""
    v1 = parse_num(spec["value"])
    v0 = parse_num(spec.get("from", 0)) or 0.0
    if v1 is None:
        return spec["value"], 1.0
    t_land = spec.get("land_t", 1.3)
    t_start = max(0.0, t_land - spec.get("count_s", 1.3))
    p = clamp01((t - t_start) / max(0.05, t_land - t_start))
    e = ease_out(p)
    if spec.get("log") and v0 > 0 and v1 > 0:
        v = math.exp(math.log(v0) + (math.log(v1) - math.log(v0)) * e)
    else:
        v = v0 + (v1 - v0) * e
    return fmt_number(v if p < 1 else v1, str(spec["value"])), p


def _hero_number(fr, txt, cx, cy, size, op, scale=1.0):
    lay = layer(txt, "Anton", size, None, grad=PEACH, glow=(GLOW, 22, 0.7), shadow=0.3)
    paste(fr, lay, cx, cy, op=op, scale=scale)
    return lay


def card(fr, spec, t, D):
    tp = spec.get("template", "hero")
    fn = {"hero": _hero, "thermo": _thermo, "gauge": _gauge, "line": _line, "scale": _scale, "fact": _fact,
          "equation": _equation, "progress": _progress, "chart": _chart, "callout": _callout, "route": _route,
          "hud": _hud, "name": _name}.get(tp, _hero)
    fn(fr, spec, t, D)
    return fr


def fit_layer(lay):
    """Shrink a label layer that is wider than LAYOUT["label_w"] of the frame (Shorts: 1080 px wide)."""
    if not LAYOUT["label_w"] or lay.shape[1] <= W * LAYOUT["label_w"]:
        return lay
    k = W * LAYOUT["label_w"] / lay.shape[1]
    return cv2.resize(lay, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)


def _labels(fr, spec, t, cy_num, size, cx=None):
    cx = W / 2 if cx is None else cx
    fade = ease_out((t - 0.1) / 0.35)
    if spec.get("kicker"):
        paste(fr, fit_layer(layer(spec["kicker"].upper(), "Montserrat", 34, "SemiBold", WHITE, track=0.45, shadow=0.4)),
              cx, cy_num - size * 0.7, op=fade)
    _, p = _count(spec, t)
    if spec.get("unit"):
        paste(fr, fit_layer(layer(spec["unit"].upper(), "Montserrat", 52, "Bold", WHITE, track=0.4, shadow=0.5)),
              cx, cy_num + size * 0.58, op=ease_out((p - 0.35) / 0.3))
    if spec.get("foot"):
        paste(fr, fit_layer(layer(spec["foot"].upper(), "Montserrat", 30, "SemiBold", (230, 230, 230), track=0.3, shadow=0.5)),
              cx, cy_num + size * 0.58 + 74, op=0.9 * ease_out((t - spec.get("land_t", 1.3) - 0.1) / 0.4))


def _hero(fr, spec, t, D):
    txt, p = _count(spec, t)
    size = fit_size(str(spec["value"]), "Anton", spec.get("size", 300), W * 0.82)
    cy = H * 0.46
    shade_box(fr, W / 2, cy, W * 0.42, size * 0.95, strength=0.45)
    sc = 0.94 + 0.06 * ease_out(t / 0.3)
    _hero_number(fr, txt, W / 2, cy, size, ease_out(t / 0.2), sc)
    _labels(fr, spec, t, cy, size)


def _scale(fr, spec, t, D):
    """×N comparison: the multiplier pops in with overshoot and counts up."""
    txt, p = _count(spec, t)
    size = fit_size(str(spec["value"]), "Anton", spec.get("size", 340), W * 0.7)
    cy = H * 0.47
    shade_box(fr, W / 2, cy, W * 0.36, size * 0.95, strength=0.45)
    sc = ease_back(t / 0.35) * 0.15 + 0.85
    lay_x = layer("×", "Anton", int(size * 0.62), None, grad=GOLD, glow=(GLOW, 18, 0.6), shadow=0.3)
    lay_n = layer(txt, "Anton", size, None, grad=PEACH, glow=(GLOW, 22, 0.7), shadow=0.3)
    wn = text_w(lay_n, size)
    paste(fr, lay_x, W / 2 - wn / 2 - size * 0.22, cy + size * 0.06, op=ease_out(t / 0.2), scale=sc)
    paste(fr, lay_n, W / 2 + size * 0.1, cy, op=ease_out(t / 0.2), scale=sc)
    _labels(fr, spec, t, cy, size)


def _thermo(fr, spec, t, D):
    txt, p = _count(spec, t)
    x0, ytop, ybot = 170, 150, 880
    tube = np.zeros_like(fr)
    cv2.rectangle(tube, (x0 - 22, ytop), (x0 + 22, ybot - 40), (255, 255, 255), 3, cv2.LINE_AA)
    cv2.circle(tube, (x0, ybot), 46, (255, 255, 255), 3, cv2.LINE_AA)
    cv2.addWeighted(tube, 0.55 * ease_out(t / 0.3), fr, 1, 0, fr)
    v0, v1 = parse_num(spec.get("from", 0)) or 0.0, parse_num(spec["value"]) or 1.0
    lo, hi = (math.log10(max(v0, 1)), math.log10(max(v1, 10))) if spec.get("log", True) else (v0, v1)
    vref = parse_num(spec.get("ref"))
    level = lambda v: (math.log10(max(v, 1)) if spec.get("log", True) else v)
    span = max(1e-6, (hi + (hi - lo) * 0.08) - (lo - (hi - lo) * 0.25))
    base = lo - (hi - lo) * 0.25
    cur = parse_num(txt) or v1
    frac = clamp01((level(cur) - base) / span)
    yfill = (ybot - 40) - frac * ((ybot - 40) - ytop - 10)
    merc = np.zeros_like(fr)
    cv2.rectangle(merc, (x0 - 12, int(yfill)), (x0 + 12, ybot - 30), (40, 70, 235), -1, cv2.LINE_AA)
    cv2.circle(merc, (x0, ybot), 36, (40, 70, 235), -1, cv2.LINE_AA)
    fr[:] = np.maximum(fr, merc)
    glow_dot(fr, x0, yfill, 10, (255, 120, 60), 0.8)
    if vref:
        yr = (ybot - 40) - clamp01((level(vref) - base) / span) * ((ybot - 40) - ytop - 10)
        line_aa(fr, (x0 + 26, yr), (x0 + 50, yr), op=0.8, thick=2)
        paste(fr, layer(spec.get("ref_label", fmt_number(vref, spec["ref"])), "Montserrat", 26, "SemiBold", WHITE, shadow=0.4),
              x0 + 60, yr, op=0.85, anchor="l")
    size = fit_size(str(spec["value"]) + "°C", "Anton", spec.get("size", 250), W * 0.62)
    cx = W * 0.58
    shade_box(fr, cx, H * 0.45, W * 0.36, size, strength=0.4)
    lay = layer(txt, "Anton", size, None, grad=SILVER if p < 1 else PEACH, glow=(GLOW, 20, 0.35 + 0.35 * p), shadow=0.35)
    wn = text_w(lay, size)
    paste(fr, lay, cx - 40, H * 0.42, op=ease_out(t / 0.2))
    if spec.get("unit"):
        paste(fr, layer(spec["unit"], "Anton", int(size * 0.5), None, grad=GOLD, shadow=0.3), cx - 40 + wn / 2 + size * 0.22, H * 0.42 + size * 0.12,
              op=ease_out(t / 0.2))
    if spec.get("kicker"):
        paste(fr, layer(spec["kicker"].upper(), "Montserrat", 40, "SemiBold", WHITE, track=0.35, shadow=0.5), cx - 40, H * 0.42 + size * 0.62,
              op=ease_out((t - 0.2) / 0.3))
    if spec.get("foot"):
        paste(fr, layer(spec["foot"].upper(), "Anton", 110, None, grad=GOLD, shadow=0.4), cx - 40, H * 0.42 + size * 0.62 + 110,
              op=ease_out((t - spec.get("land_t", 1.3)) / 0.25))


def _gauge(fr, spec, t, D):
    txt, p = _count(spec, t)
    cx, cy, R = W / 2, H * 0.47, 330
    a0, a1 = 210, -30  # degrees, clockwise sweep through the top
    shade_box(fr, cx, cy, R * 1.5, R * 1.25, strength=0.5)
    v0, v1 = parse_num(spec.get("from", 0)) or 0.0, parse_num(spec["value"]) or 1.0
    vmax = parse_num(spec.get("max", 100)) or 100.0
    cur = parse_num(txt) if parse_num(txt) is not None else v1
    a_cur = a0 + (a1 - a0) * clamp01(cur / vmax)
    arc = np.zeros_like(fr)
    cv2.ellipse(arc, (int(cx), int(cy)), (R, R), 0, -a0, -a1, (110, 110, 110), 3, cv2.LINE_AA)
    cv2.addWeighted(arc, 0.6 * ease_out(t / 0.3), fr, 1, 0, fr)
    lit = np.zeros_like(fr)
    if a_cur < a0 - 0.5:
        cv2.ellipse(lit, (int(cx), int(cy)), (R, R), 0, -a0, -a_cur, (60, 170, 255), 6, cv2.LINE_AA)
        lit = cv2.GaussianBlur(lit, (0, 0), 4) * 1.5 + lit
        fr[:] = np.clip(fr.astype(np.float32) + lit, 0, 255).astype(np.uint8)
    ang = math.radians(a_cur)
    glow_dot(fr, cx + R * math.cos(ang), cy - R * math.sin(ang), 9, (255, 236, 200), ease_out(t / 0.3))
    size = fit_size(str(spec["value"]), "Anton", spec.get("size", 240), R * 1.6)
    _hero_number(fr, txt, cx, cy - 10, size, ease_out(t / 0.2))
    if spec.get("kicker"):
        paste(fr, layer(spec["kicker"].upper(), "Montserrat", 30, "SemiBold", WHITE, track=0.45, shadow=0.4),
              cx, cy - size * 0.72, op=ease_out((t - 0.1) / 0.35))
    if spec.get("unit"):
        paste(fr, layer(spec["unit"].upper(), "Montserrat", 44, "Bold", WHITE, track=0.35, shadow=0.5),
              cx, cy + R * 0.5 + 40, op=ease_out((p - 0.35) / 0.3))
    if spec.get("foot"):
        paste(fr, layer(spec["foot"].upper(), "Montserrat", 30, "SemiBold", (230, 230, 230), track=0.3, shadow=0.5),
              cx, cy + R * 0.5 + 104, op=0.9 * ease_out((t - spec.get("land_t", 1.3) - 0.1) / 0.4))


def _line(fr, spec, t, D):
    """Dot-on-a-line: a glowing dot travels from the left label to the right one while the number counts."""
    txt, p = _count(spec, t)
    y, xa, xb = H * 0.66, W * 0.12, W * 0.88
    reveal = ease_out(t / 0.6)
    shade_box(fr, W / 2, H * 0.5, W * 0.48, H * 0.36, strength=0.5)
    line_aa(fr, (xa, y), (xa + (xb - xa) * reveal, y), op=0.6, thick=2, dash=14)
    glow_dot(fr, xa, y, 12, (255, 200, 120), ease_out(t / 0.3))
    glow_dot(fr, xb, y, 12, (150, 200, 255), ease_out((t - 0.3) / 0.3))
    glow_dot(fr, xa + (xb - xa) * ease_out(p), y, 7, (255, 245, 220), 1.0)
    for lab, xx in ((spec.get("left", ""), xa), (spec.get("right", ""), xb)):
        if lab:
            paste(fr, layer(lab.upper(), "Montserrat", 26, "SemiBold", (230, 230, 230), track=0.4, shadow=0.4), xx, y + 52, op=0.8)
    size = fit_size(str(spec["value"]), "Anton", spec.get("size", 240), W * 0.8)
    _hero_number(fr, txt, W / 2, H * 0.36, size, ease_out(t / 0.2))
    if spec.get("unit"):
        paste(fr, layer(spec["unit"].upper(), "Montserrat", 46, "Bold", WHITE, track=0.4, shadow=0.5), W / 2, H * 0.36 + size * 0.58,
              op=ease_out((p - 0.35) / 0.3))
    if spec.get("foot"):
        paste(fr, layer(spec["foot"].upper(), "Montserrat", 30, "SemiBold", (230, 230, 230), track=0.3, shadow=0.5), W / 2, y + 120,
              op=0.85 * ease_out((t - spec.get("land_t", 1.3) - 0.1) / 0.4))


def _fact(fr, spec, t, D):
    """Serif fact card: a big pale-gold serif line, tracked small caps under it, thin rules both sides."""
    e = ease_out(t / 0.45)
    size = fit_size(spec["value"], "Cinzel", spec.get("size", 150), W * 0.8, "SemiBold")
    lay = layer(spec["value"], "Cinzel", size, "SemiBold", grad=((255, 236, 200), (226, 186, 120)), glow=(GLOW, 16, 0.25), shadow=0.4)
    cy = H * 0.47
    shade_box(fr, W / 2, cy, W * 0.4, size * 1.1, op=e, strength=0.45)
    blur = int((1 - e) * 12) * 2 + 1
    if blur > 1:
        lay = cv2.GaussianBlur(lay, (blur, blur), 0)
    paste(fr, lay, W / 2, cy, op=e)
    if spec.get("sub"):
        sub = layer(spec["sub"].upper(), "Montserrat", 30, "SemiBold", (240, 230, 210), track=0.45, shadow=0.4)
        paste(fr, sub, W / 2, cy + size * 0.75, op=ease_out((t - 0.3) / 0.4))
        wsub = text_w(sub, 30)
        for sgn in (-1, 1):
            xa = W / 2 + sgn * (wsub / 2 + 30)
            line_aa(fr, (xa, cy + size * 0.75), (xa + sgn * 160 * ease_out((t - 0.3) / 0.5), cy + size * 0.75), op=0.6, thick=1)


def _equation(fr, spec, t, D):
    """Elegant data panel: A  × B  = RESULT with tracked labels (e.g. 'YOUR MASS 60 kg × 28 = 1,680 kg')."""
    cy = H * 0.42
    shade_box(fr, W / 2, H * 0.5, W * 0.42, H * 0.36, strength=0.45)
    parts = [("a", spec.get("a", ""), spec.get("a_label", "")), ("b", spec.get("b", ""), spec.get("b_label", ""))]
    for k, (key, val, lab) in enumerate(parts):
        x = W * (0.37 if k == 0 else 0.63)
        paste(fr, layer(lab.upper(), "Montserrat", 24, "SemiBold", (215, 215, 215), track=0.4, shadow=0.3), x, cy - 90,
              op=ease_out((t - 0.15 * k) / 0.35))
        paste(fr, layer(val, "Montserrat", 110, "Light", WHITE if k == 0 else KICKER, shadow=0.4), x, cy,
              op=ease_out((t - 0.15 * k) / 0.35))
    paste(fr, layer(spec.get("op", "→"), "Montserrat", 90, "Light", (235, 235, 235), shadow=0.4), W / 2, cy,
          op=ease_out((t - 0.1) / 0.35))
    line_aa(fr, (W * 0.25, cy + 95), (W * 0.25 + W * 0.5 * ease_out((t - 0.4) / 0.5), cy + 95), op=0.5, thick=1)
    spec2 = dict(spec, value=spec["value"])
    txt, p = _count(spec2, t)
    paste(fr, layer(txt + (" " + spec["unit"] if spec.get("unit") else ""), "Montserrat", 170, "Light",
                    grad=((255, 232, 190), (232, 184, 110)), shadow=0.4), W / 2, cy + 230, op=ease_out((t - 0.5) / 0.3))
    if spec.get("foot"):
        paste(fr, layer(spec["foot"].upper(), "Montserrat", 24, "SemiBold", (220, 220, 220), track=0.4, shadow=0.3), W / 2, cy + 360,
              op=ease_out((t - spec.get("land_t", 1.3)) / 0.4))


def _fxy(spec, kx, ky, dx=0.5, dy=0.5):
    return float(spec.get(kx, dx)) * W, float(spec.get(ky, dy)) * H


def _progress(fr, spec, t, D):
    """Segmented progress bar filling to value / max (e.g. '1' of 100 %), big number above, labels at the ends."""
    txt, p = _count(spec, t)
    vmax = parse_num(spec.get("max", 100)) or 100.0
    cur = parse_num(txt) if parse_num(txt) is not None else 0.0
    y, xa, xb, n = H * 0.6, W * 0.18, W * 0.82, 40
    shade_box(fr, W / 2, H * 0.5, W * 0.45, H * 0.3, strength=0.45)
    seg = (xb - xa) / n
    fill = clamp01(cur / vmax) * n
    bars = np.zeros_like(fr)
    for k in range(n):
        x0 = int(xa + k * seg + 2)
        col = (255, 215, 90) if k < fill else (90, 90, 90)
        cv2.rectangle(bars, (x0, int(y)), (int(x0 + seg - 4), int(y + 10)), col, -1)
        if k < fill < k + 1:  # partly lit segment
            cv2.rectangle(bars, (x0, int(y)), (int(x0 + (seg - 4) * (fill - k)), int(y + 10)), (255, 215, 90), -1)
    cv2.addWeighted(bars, 0.9 * ease_out(t / 0.3), fr, 1, 0, fr)
    size = fit_size(str(spec["value"]) + "%", "Anton", spec.get("size", 200), W * 0.5)
    lay = layer(txt + spec.get("unit", "%"), "Anton", size, None, grad=SILVER, glow=(GLOW, 16, 0.3), shadow=0.4)
    paste(fr, lay, W / 2, y - size * 0.55, op=ease_out(t / 0.2))
    for lab, xx in ((spec.get("left", ""), xa), (spec.get("right", ""), xb)):
        if lab:
            paste(fr, layer(lab.upper(), "Montserrat", 26, "SemiBold", (230, 230, 230), track=0.4, shadow=0.4), xx, y + 50, op=0.85)
    if spec.get("kicker"):
        paste(fr, layer(spec["kicker"].upper(), "Montserrat", 30, "SemiBold", KICKER, track=0.45, shadow=0.4),
              W / 2, y - size * 1.15, op=ease_out((t - 0.1) / 0.3))


def _chart(fr, spec, t, D):
    """One glowing line drawn left to right over 2 s on a faint grid, markers popping on `marks` (indices).
    points="y0,y1,..." (or "x:y,..."); xlabel/ylabel/label; the line colour follows the gold palette."""
    pts = [q.split(":") for q in str(spec["points"]).split(",")]
    xs = np.array([float(q[0]) if len(q) > 1 else i for i, q in enumerate(pts)])
    ys = np.array([float(q[-1]) for q in pts])
    if spec.get("log"):
        ys = np.log10(np.maximum(ys, 1e-9))
    x0, x1, y0, y1 = W * 0.14, W * 0.86, H * 0.78, H * 0.26
    shade_box(fr, W / 2, H * 0.52, W * 0.46, H * 0.4, strength=0.5)
    grid = np.zeros_like(fr)
    for k in range(6):
        yy = int(y0 + (y1 - y0) * k / 5)
        cv2.line(grid, (int(x0), yy), (int(x1), yy), (90, 90, 90), 1, cv2.LINE_AA)
    cv2.line(grid, (int(x0), int(y0)), (int(x0), int(y1)), (150, 150, 150), 1, cv2.LINE_AA)
    cv2.addWeighted(grid, 0.6 * ease_out(t / 0.4), fr, 1, 0, fr)
    px = x0 + (xs - xs.min()) / max(1e-9, np.ptp(xs)) * (x1 - x0)
    py = y0 + (ys - ys.min()) / max(1e-9, np.ptp(ys)) * (y1 - y0)
    p = ease_in_out((t - 0.2) / float(spec.get("draw", 2.0)))
    xe = x0 + (x1 - x0) * p
    dense_x = np.linspace(x0, xe, max(2, int(400 * p)))
    dense_y = np.interp(dense_x, px, py)
    line = np.zeros_like(fr)
    poly = np.stack([dense_x, dense_y], 1).astype(np.int32)
    cv2.polylines(line, [poly], False, (40, 150, 255), 4, cv2.LINE_AA)
    glow = cv2.GaussianBlur(line, (0, 0), 6)
    fr[:] = np.clip(fr.astype(np.int16) + glow.astype(np.int16) + line.astype(np.int16), 0, 255).astype(np.uint8)
    if p > 0:
        glow_dot(fr, dense_x[-1], dense_y[-1], 7, (255, 240, 210), 1.0)
    for m in [int(v) for v in str(spec.get("marks", "")).split(",") if v.strip()]:
        if 0 <= m < len(px) and px[m] <= xe:
            glow_dot(fr, px[m], py[m], 10, (255, 90, 70), ease_back((xe - px[m]) / 60))
    for lab, (xx, yy, anc) in ((spec.get("xlabel"), (W / 2, y0 + 50, "c")), (spec.get("ylabel"), (x0, y1 - 40, "l"))):
        if lab:
            paste(fr, layer(lab.upper(), "Montserrat", 24, "SemiBold", (220, 220, 220), track=0.35, shadow=0.4), xx, yy, op=0.85, anchor=anc)
    if spec.get("label"):
        paste(fr, layer(spec["label"].upper(), "Montserrat", 34, "SemiBold", KICKER, track=0.4, shadow=0.4), W / 2, y1 - 90,
              op=ease_out(t / 0.4))


def _callout(fr, spec, t, D):
    """Ring around an object in the footage (x, y as frame fractions, r px), a leader line and a label box."""
    cx, cy = _fxy(spec, "x", "y")
    r = float(spec.get("r", 90))
    e = ease_back(t / 0.35)
    ring = np.zeros_like(fr)
    cv2.circle(ring, (int(cx), int(cy)), int(r * (0.6 + 0.4 * e)), (255, 255, 255), 2, cv2.LINE_AA)
    a0 = -90 + 360 * ease_out((t - 0.05) / 0.5)
    cv2.ellipse(ring, (int(cx), int(cy)), (int(r * 1.18), int(r * 1.18)), 0, -90, a0, (90, 200, 255), 2, cv2.LINE_AA)
    cv2.addWeighted(ring, 0.9 * clamp01(t / 0.15), fr, 1, 0, fr)
    side = 1 if cx < W * 0.6 else -1
    lx, ly = cx + side * (r * 1.2 + 140), cy - r * 0.9
    pl = ease_out((t - 0.3) / 0.3)
    if pl > 0:
        ex, ey = cx + side * r * 0.85, cy - r * 0.62
        line_aa(fr, (ex, ey), (ex + (lx - ex) * pl, ey + (ly - ey) * pl), op=0.9, thick=2)
    el = ease_out((t - 0.55) / 0.3)
    if el > 0:
        lab = layer(spec.get("label", "").upper(), "Montserrat", 34, "Bold", WHITE, track=0.2, shadow=0.6)
        w = text_w(lab, 34)
        x = lx + 14 if side > 0 else lx - 14 - w
        paste(fr, lab, x - (lab.shape[1] - w) / 2, ly - 8, op=el, anchor="l", clip=(min(lx, x - 20), 0, max(lx, x + w + 20), H))
        if spec.get("sub"):
            sub = layer(spec["sub"].upper(), "Montserrat", 22, "SemiBold", KICKER, track=0.35, shadow=0.5)
            ws = text_w(sub, 22)
            xs_ = lx + 14 if side > 0 else lx - 14 - ws
            paste(fr, sub, xs_ - (sub.shape[1] - ws) / 2, ly + 30, op=ease_out((t - 0.75) / 0.3), anchor="l")


def _route(fr, spec, t, D):
    """Map line: a glowing line draws from (x0, y0) to (x1, y1) while a counter box counts the value."""
    ax, ay = _fxy(spec, "x0", "y0", 0.2, 0.6)
    bx, by = _fxy(spec, "x1", "y1", 0.8, 0.4)
    txt, p = _count(spec, t)
    e = ease_in_out(p if spec.get("value") else t / 1.5)
    glow_dot(fr, ax, ay, 9, (255, 220, 160), ease_out(t / 0.2))
    line = np.zeros_like(fr)
    cv2.line(line, (int(ax), int(ay)), (int(ax + (bx - ax) * e), int(ay + (by - ay) * e)), (40, 150, 255), 3, cv2.LINE_AA)
    fr[:] = np.clip(fr.astype(np.int16) + cv2.GaussianBlur(line, (0, 0), 5).astype(np.int16) + line.astype(np.int16), 0, 255).astype(np.uint8)
    glow_dot(fr, ax + (bx - ax) * e, ay + (by - ay) * e, 7, (255, 245, 225), 1.0)
    if e >= 0.99:
        glow_dot(fr, bx, by, 9, (150, 200, 255), 1.0)
    for lab, (xx, yy) in ((spec.get("left", ""), (ax, ay)), (spec.get("right", ""), (bx, by))):
        if lab:
            paste(fr, layer(lab.upper(), "Montserrat", 26, "Bold", WHITE, track=0.35, shadow=0.6), xx, yy + 42, op=0.9)
    if spec.get("value"):
        mx, my = (ax + bx) / 2, min(ay, by) - 90
        box = layer(txt + (" " + spec["unit"] if spec.get("unit") else ""), "Montserrat", 44, "Bold", WHITE, shadow=0.5)
        w = text_w(box, 44)
        shade_box(fr, mx, my, w * 0.75 + 40, 50, strength=0.55, op=ease_out(t / 0.3))
        paste(fr, box, mx, my, op=ease_out(t / 0.3))


def _hud(fr, spec, t, D):
    """Telescope / camera viewfinder: corner brackets, a blinking REC dot, tracked mono-style labels and a target
    ring; optional zoom counter (value, unit '×')."""
    e = ease_out(t / 0.4)
    ov = np.zeros_like(fr)
    m, L = 70, 70
    k = int((1 - e) * 40)
    for sx, sy in ((m, m), (W - m, m), (m, H - m), (W - m, H - m)):
        dx, dy = (1 if sx < W / 2 else -1), (1 if sy < H / 2 else -1)
        x, y = sx - dx * k, sy - dy * k
        cv2.line(ov, (x, y), (x + dx * L, y), (255, 255, 255), 2, cv2.LINE_AA)
        cv2.line(ov, (x, y), (x, y + dy * L), (255, 255, 255), 2, cv2.LINE_AA)
    cx, cy = _fxy(spec, "x", "y")
    rr = int(60 + 30 * (1 - e))
    cv2.circle(ov, (int(cx), int(cy)), rr, (255, 255, 255), 1, cv2.LINE_AA)
    for a in (0, 90, 180, 270):
        ca, sa = math.cos(math.radians(a + 25 * t)), math.sin(math.radians(a + 25 * t))
        cv2.line(ov, (int(cx + ca * rr * 0.75), int(cy + sa * rr * 0.75)), (int(cx + ca * rr * 1.25), int(cy + sa * rr * 1.25)),
                 (255, 255, 255), 1, cv2.LINE_AA)
    cv2.addWeighted(ov, 0.75 * e, fr, 1, 0, fr)
    if int(t * 2) % 2 == 0:
        glow_dot(fr, m + 30, m + 50, 6, (255, 60, 60), e)
    paste(fr, layer("REC", "Montserrat", 22, "SemiBold", WHITE, track=0.3, shadow=0.4), m + 48, m + 50, op=0.85 * e, anchor="l")
    if spec.get("label"):
        lab = layer(spec["label"].upper(), "Montserrat", 22, "SemiBold", WHITE, track=0.35, shadow=0.4)
        paste(fr, lab, W - m - 30 - lab.shape[1], m + 50, op=0.85 * e, anchor="l")
    if spec.get("sub"):
        paste(fr, layer(spec["sub"].upper(), "Montserrat", 20, "Medium", (210, 230, 235), track=0.35, shadow=0.4),
              m + 30, H - m - 40, op=0.8 * e, anchor="l")
    if spec.get("value"):
        txt, p = _count(spec, t)
        z = layer(txt + spec.get("unit", "×"), "Montserrat", 40, "SemiBold", (150, 230, 255), shadow=0.5)
        paste(fr, z, W - m - 30 - z.shape[1] * 0.85, H - m - 40, op=0.9 * e, anchor="l")


def _name(fr, spec, t, D):
    """Lower third for a person: a gold bar grows, the name rises out of a mask, the role line fades in."""
    x, y = W * 0.075, H * LAYOUT["name_y"]
    out = clamp01((float(spec.get("dur", D)) - t) / 0.3)
    shade_left(fr, 0.6 * ease_out(t / 0.3) * out, strength=0.55, reach=0.45)
    bar = ease_out(t / 0.35)
    ov = np.zeros_like(fr)
    cv2.rectangle(ov, (int(x), int(y - 52)), (int(x + 6), int(y - 52 + 100 * bar)), (90, 200, 255), -1)
    cv2.addWeighted(ov, out, fr, 1, 0, fr)
    nm = layer(spec["value"].upper(), "Anton", 76, None, grad=SILVER, shadow=0.5)
    e = ease_out((t - 0.12) / 0.25)
    pad = (nm.shape[1] - text_w(nm, 76)) / 2
    paste(fr, nm, x + 26 - pad, y - 12 + (1 - e) * 60, op=out, anchor="l", clip=(0, y - 60, W, y + 36))
    if spec.get("sub"):
        sub = layer(spec["sub"].upper(), "Montserrat", 26, "SemiBold", KICKER, track=0.35, shadow=0.5)
        paste(fr, sub, x + 26 - (sub.shape[1] - text_w(sub, 26)) / 2, y + 48, op=out * ease_out((t - 0.35) / 0.3), anchor="l")


# ------------------------------------------------------------------ captions (Shorts)
CAPTION = {"y": 0.8, "size": 76, "maxw": 0.8}  # centre line (of H), font px, widest line (of W)


@lru_cache(maxsize=1024)
def _cap_word(text, gold, size):
    """One caption word as BGRA: Montserrat ExtraBold, white (or gold, the word being spoken), black outline."""
    f = _font("Montserrat", size, "ExtraBold")
    sw = max(3, size // 11)
    b = f.getbbox(text, stroke_width=sw)
    pad = int(size * 0.3)
    tw, th = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    xy = (pad - b[0], pad - b[1])
    full, fill = Image.new("L", (tw, th), 0), Image.new("L", (tw, th), 0)
    ImageDraw.Draw(full).text(xy, text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    ImageDraw.Draw(fill).text(xy, text, font=f, fill=255)
    m, mf = np.array(full, np.float32) / 255, np.array(fill, np.float32) / 255
    if gold:
        rows = np.where(mf.max(1) > 0)[0]
        y0, y1 = (rows[0], rows[-1]) if len(rows) else (0, th - 1)
        k = np.clip((np.arange(th) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
        top, bot = np.array(GOLD[0], np.float32)[::-1], np.array(GOLD[1], np.float32)[::-1]
        col = np.broadcast_to(top + (bot - top) * k, (th, tw, 3))
    else:
        col = np.full((th, tw, 3), 255, np.float32)
    rgb = col * mf[..., None]  # the outline is black: colour only where the letter fills
    sh = cv2.GaussianBlur(np.roll(m, (int(size * 0.05), int(size * 0.03)), (0, 1)), (0, 0), size * 0.06) * 0.6
    a = np.clip(m + sh * (1 - m), 0, 1)
    return np.dstack([np.clip(rgb / np.maximum(a[..., None], 1e-4), 0, 255), a * 255]).astype(np.uint8)


def captions(fr, spec, t):
    """Burned-in captions: the line being spoken, a few words at a time, the current word gold with a small pop.
    spec["chunks"] = [{"t0", "t1", "words": [[t, text], ...]}] on the video clock."""
    ch = next((c for c in spec["chunks"] if c["t0"] <= t < c["t1"]), None)
    if ch is None:
        return
    size = CAPTION["size"]
    ws = ch["words"]
    cur = max([i for i, (wt, _) in enumerate(ws) if wt <= t + 0.02] or [0])
    lay = [_cap_word(x, False, size) for _, x in ws]
    wid = [text_w(l_, size) for l_ in lay]
    sp = size * 0.3
    lines, row, wrow = [], [], 0.0  # one line, or two when the words do not fit
    for i, w_ in enumerate(wid):
        if row and wrow + sp + w_ > CAPTION["maxw"] * W:
            lines.append(row)
            row, wrow = [], 0.0
        row.append(i)
        wrow += (sp if len(row) > 1 else 0) + w_
    lines.append(row)
    lh = size * 1.18
    yc = H * CAPTION["y"] - lh * (len(lines) - 1) / 2
    e = ease_out((t - ch["t0"]) / 0.12)
    wide = max(sum(wid[i] for i in r) + sp * (len(r) - 1) for r in lines)
    shade_box(fr, W / 2, yc + lh * (len(lines) - 1) / 2, wide / 2 + 70, lh * len(lines) / 2 + 40, op=e, strength=0.4)
    for k, r in enumerate(lines):
        x = W / 2 - (sum(wid[i] for i in r) + sp * (len(r) - 1)) / 2
        y = yc + k * lh + (1 - e) * 14
        for i in r:
            gold = i == cur
            l_ = _cap_word(ws[i][1], True, size) if gold else lay[i]
            pop = 1.0 + (0.1 * max(0.0, 1 - (t - ws[i][0]) / 0.16) if gold else 0.0)
            paste(fr, l_, x + wid[i] / 2, y, op=e, scale=pop)
            x += wid[i] + sp


# ------------------------------------------------------------------ cards, title, footer, logo
def chapter(fr, num, n_total, title, t, D):
    """FACT #n card: tracked 'FACT', a big gold number rising in, the title revealed word by word,
    a countdown bar (n_total segments, the current one lit)."""
    shade_box(fr, W / 2, H * 0.5, W * 0.6, H * 0.5, strength=0.55)
    paste(fr, layer("FACT", "Montserrat", 40, "SemiBold", WHITE, track=0.8, shadow=0.4), W / 2, H * 0.24, op=ease_out(t / 0.3))
    e = ease_out((t - 0.1) / 0.3)
    lay = layer(f"#{num}", "Anton", 260, None, grad=GOLD, glow=(GLOW, 22, 0.55), shadow=0.3)
    paste(fr, lay, W / 2, H * 0.41 + (1 - e) * 120, op=e, clip=(0, H * 0.27, W, H * 0.56))
    words = title.split()
    size = fit_size(title.upper(), "Anton", 92, W * 0.82)
    lays = [layer(_line_spec(w_)[0].upper(), "Anton", size, None, grad=GOLD if _line_spec(w_)[1] else SILVER, shadow=0.5)
            for w_ in words]
    widths = [text_w(l_, size) for l_ in lays]
    sp = size * 0.28
    x = W / 2 - (sum(widths) + sp * (len(words) - 1)) / 2
    cy = H * 0.66
    for i, (l_, wd) in enumerate(zip(lays, widths)):
        ew = ease_out((t - 0.45 - 0.06 * i) / 0.2)
        if ew > 0:
            paste(fr, l_, x - (l_.shape[1] - wd) / 2, cy + (1 - ew) * size * 0.5, op=ew, anchor="l",
                  clip=(0, cy - size * 0.62, W, cy + size * 0.62))
        x += wd + sp
    # countdown bar: segments for n_total .. 1, the current one lit
    bw, gap, y = 64, 10, H * 0.8
    x0 = W / 2 - (n_total * bw + (n_total - 1) * gap) / 2
    done = n_total - int(num) if str(num).isdigit() else 0
    bars = np.zeros_like(fr)
    for k in range(n_total):
        col = (40, 160, 255) if k < done else ((90, 200, 255) if k == done else (110, 110, 110))
        cv2.rectangle(bars, (int(x0 + k * (bw + gap)), int(y)), (int(x0 + k * (bw + gap) + bw), int(y + 6)), col, -1)
    cv2.addWeighted(bars, 0.9 * ease_out((t - 0.3) / 0.4), fr, 1, 0, fr)
    glow_dot(fr, x0 + done * (bw + gap) + bw / 2, y + 3, 5, (255, 220, 160), ease_out((t - 0.5) / 0.3))


def title(fr, kicker, main, t, D):
    """Title card: tracked kicker blur-fades in, the main line slides in from the left with motion blur, a thin
    gold rule grows from the centre."""
    shade_box(fr, W / 2, H * 0.5, W * 0.55, H * 0.4, strength=0.5)
    ek = ease_out(t / 0.6)
    kl = layer(kicker.upper(), "Montserrat", 58, "ExtraBold", WHITE, track=0.6, shadow=0.4)
    b = int((1 - ek) * 10) * 2 + 1
    paste(fr, cv2.GaussianBlur(kl, (b, b), 0) if b > 1 else kl, W / 2, H * 0.4, op=ek)
    em = ease_out((t - 0.45) / 0.6)
    size = fit_size(main.upper(), "Montserrat", 118, W * 0.86, "ExtraBold")
    ml = layer(main.upper(), "Montserrat", size, "ExtraBold", grad=SILVER, shadow=0.5)
    if em > 0:
        k = int((1 - em) * 60) + 1
        mb = cv2.blur(ml, (k, 1)) if k > 1 else ml
        paste(fr, mb, W / 2 - (1 - em) * 260, H * 0.53, op=em)
    rule = ease_out((t - 0.9) / 0.5)
    if rule > 0:
        line_aa(fr, (W / 2 - 320 * rule, H * 0.62), (W / 2 + 320 * rule, H * 0.62), (232, 190, 110), op=0.9, thick=2)


def footer(fr, left, right, op=0.5):
    paste(fr, layer(left.upper(), "Montserrat", 22, "SemiBold", WHITE, track=0.35, shadow=0.5), W * 0.035, H * 0.955, op=op, anchor="l")
    if right:
        lay = layer(right.upper(), "Montserrat", 22, "SemiBold", WHITE, track=0.35, shadow=0.5)
        paste(fr, lay, W * 0.965 - lay.shape[1], H * 0.955, op=op, anchor="l")


@lru_cache(maxsize=2)
def _logo():
    a = layer("SCIENCE", "Montserrat", 26, "ExtraBold", (15, 15, 15), track=0.12, shadow=0)
    b = layer("GUY", "Montserrat", 26, "ExtraBold", WHITE, track=0.12, shadow=0.5)
    wa, wb = text_w(a, 26), text_w(b, 26)
    h = 44
    img = np.zeros((h, wa + wb + 46, 4), np.uint8)
    cv2.rectangle(img, (0, 0), (wa + 22, h - 1), (255, 255, 255, 235), -1)
    return img, a, b, wa, wb


def logo(fr, op=0.85):
    img, a, b, wa, wb = _logo()
    x, y = (W - 48 - img.shape[1] if LAYOUT["logo"] == "right" else 48), LAYOUT["logo_y"]
    paste(fr, img, x + img.shape[1] / 2, y + img.shape[0] / 2, op=op)
    paste(fr, a, x + 11 + wa / 2 + 1, y + img.shape[0] / 2 + 1, op=op)
    paste(fr, b, x + wa + 34 + wb / 2, y + img.shape[0] / 2 + 1, op=op)


def endcard(fr, t, t0, t1, top="FULL VIDEO", bottom="*BELOW*"):
    """Shorts end card: two stacked lines rise in, a chevron arrow bounces under them toward the related-video link.
    Written only: the narration never says it (channel rule)."""
    if t < t0:
        return
    out = clamp01((t1 - t) / 0.2) if t1 - t < 0.2 else 1.0
    e = ease_out((t - t0) / 0.3)
    cy = H * 0.5
    shade_box(fr, W / 2, cy + 40, W * 0.48, 330, op=e * out, strength=0.6)
    y = cy - 130
    for txt in (top, bottom):
        word, gold = _line_spec(txt)
        size = fit_size(word.upper(), "Anton", 170, W * 0.8)
        lay = layer(word.upper(), "Anton", size, None, grad=GOLD if gold else SILVER, shadow=0.55)
        h = lay.shape[0] * 0.64
        k = ease_out((t - t0 - (0.12 if txt is bottom else 0)) / 0.25)
        paste(fr, lay, W / 2, y + h / 2 + (1 - k) * h * 0.9, op=out * k, clip=(0, y - 6, W, y + h + 8))
        y += h + 8
    bounce = abs(math.sin((t - t0) * math.pi * 1.6)) * 26
    ay, aw = y + 70 + bounce, 64
    ov = np.zeros_like(fr)
    for dy in (0, 44):
        pts = np.array([[W / 2 - aw, ay + dy - aw * 0.55], [W / 2, ay + dy], [W / 2 + aw, ay + dy - aw * 0.55]], np.int32)
        cv2.polylines(ov, [pts], False, (40, 190, 255) if dy else (255, 255, 255), 14, cv2.LINE_AA)
    a = ease_out((t - t0 - 0.3) / 0.3) * out
    if a > 0:
        m = ov.any(2)
        fr[m] = (fr[m] * (1 - a) + ov[m] * a).astype(np.uint8)
