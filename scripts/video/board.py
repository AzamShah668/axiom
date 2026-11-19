"""Evidence-board scenes (owner 2026-11-19, from the kaz-documentary plugin): one continuous camera over a dark board with
pinned photos and typed papers, red strings, hand-drawn red circles, black-tape labels that type on, a stamp, a year
card and a "thesis" card (old idea struck through, new answer). For the history beats of a video (people, years,
results), 1-2 scenes of 15-40 s per video; the space footage stays the base.

Use: edit.spec  `G <trigger> @ board:<name>`  ->  make_edit.py inlines productions/<NN>/boards/<name>.json
     render_v3.plan() resolves every time in it (spoken triggers) to seconds from the scene start (resolve()), adds the
     scene's sounds (cues()), and render_video.gfx draws each frame with frame().

Board file (times: a number = seconds from the scene start, or a Devanagari trigger from the section's narration,
optionally "+0.3"/"-0.2"; every trigger is searched from the G line's trigger on):
{
 "cards": [                     # pos/w/h in board units (the board is about 4200 x 3300; R = 2 px per unit)
   {"id": "teamA", "at": "...", "pos": [750, 1050], "rot": -3, "w": 640, "h": 520,
    "paper": [["SUPERNOVA", 34], ["", 12], ["LEAD: SAUL PERLMUTTER", 30]]},          # a typed note
   {"id": "riess", "at": 3.0, "pos": [3330, 830], "rot": 4, "w": 420, "photo": "Riess", "crop": [330, 60, 1050, 800]},
                                 # assets/photos/<photo>.jpg, credit in assets/photos/credits.json or assets/credits.json
   {"id": "graph", "draw": "hubble", "w": 860, "h": 620, ...},                       # a hand-plotted "farther = dimmer" chart
   {"id": "pie", "draw": "pie", "title": "TODAY'S UNIVERSE", "pct": 68, "fill_at": "...", "w": 620, "h": 640, ...}
 ],
 "camera": [{"at": 0, "look": "all"}, {"at": "...", "look": "graph", "zoom": 1.05, "rot": -1}, ...],
            # look: "all" | a card id | [x, y]; zoom: optional (fits the target); each move takes "move" s (0.7)
            # then drifts in by "drift" (1.08) until the next move
 "tags": [{"on": "riess", "uv": [0.5, 0], "text": "ADAM RIESS", "at": 3.5, "off": [-330, -150]}],
            # black-tape label typing on at 22 chars/s with a red leader line; fades after 7 s, returns at "reveal"
 "strings": [{"from": "teamA", "to": "graph", "at": 3.6}],
 "circles": [{"on": "graph", "uv": [0.76, 0.47], "r": [230, 150], "at": "..."}],      # uv: 0..1 across the card
 "underlines": [{"on": "nobel", "uv": [[0.07, 0.8], [0.89, 0.8]], "at": "..."}],
 "stamp": {"text": "DARK ENERGY", "at": "...", "pos": [2350, 1760], "rot": -10},
 "year": {"at": 0.35, "end": 2.6, "kicker": "THE DATA ARRIVES", "from": 1990, "year": 1998},
 "thesis": {"at": "...", "end": "...", "old": "THE UNIVERSE IS SLOWING DOWN", "strike": "...",
            "new": "IT IS SPEEDING UP", "new_at": "..."},
 "reveal": 39.5                  # pull-out: every label comes back
}
Test one board without a render:  python board.py <board.json resolved> <assets_dir> <fonts_dir> <out.mp4> [t1,t2,..]
"""
import math
import os
import re
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
R = 2.0
RED = (208, 49, 45)
INK = (40, 36, 32)
_FONT_FILES = {"mono": ("FreeMonoBold.ttf", "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"),
               "serif": ("Caladea-Bold.ttf", "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf")}
_FONTS, _BOARDS = {}, {}


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ss(x): x = clamp(x); return x * x * (3 - 2 * x)
def ease(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def backout(x, s=1.7): x = clamp(x) - 1; return 1 + (s + 1) * x ** 3 + s * x ** 2


def font(kind, size, fonts_dir=""):
    key = (kind, int(size))
    if key not in _FONTS:
        name, system = _FONT_FILES[kind]
        p = os.path.join(fonts_dir, name) if fonts_dir and os.path.exists(os.path.join(fonts_dir, name)) else system
        _FONTS[key] = ImageFont.truetype(p, int(size))
    return _FONTS[key]


# ------------------------------------------------------------------ times: triggers -> scene seconds
def resolve(spec, when):
    """Copy of a board spec with every time turned into seconds from the scene start. when(trigger) -> seconds."""
    def tv(v):
        if isinstance(v, (int, float)):
            return float(v)
        m = re.match(r"^(.*?)\s*([+-]\s*\d+(?:\.\d+)?)?$", str(v).strip())
        return when(m.group(1).strip()) + (float(m.group(2).replace(" ", "")) if m.group(2) else 0.0)

    def walk(o, key=""):
        if isinstance(o, dict):
            return {k: (tv(v) if k in ("at", "end", "strike", "new_at", "fill_at", "reveal") and v is not None else walk(v, k))
                    for k, v in o.items()}
        if isinstance(o, list):
            return [walk(x, key) for x in o]
        return o
    return walk(spec)


def cues(spec):
    """The board's sounds (kaz-documentary kit in sfx.py), times in scene seconds: (kind, t, gain, kwargs)."""
    out = []
    for c in spec.get("camera", [])[1:]:
        out.append(("kz_whoosh", c["at"] - 0.1, 0, {}))
    for tg in spec.get("tags", []):
        out.append(("kz_typing", tg["at"], 0, {"n": len(tg["text"])}))
    for c in spec.get("circles", []) + spec.get("underlines", []):
        out.append(("kz_scratch", c["at"], 0, {"d": 0.45}))
    if "stamp" in spec:
        out.append(("kz_thud", spec["stamp"]["at"], 0, {}))
    if "year" in spec:
        y = spec["year"]
        out += [("kz_thud", y["at"], -3, {}), ("kz_typing", y["at"] + 0.4, 0, {"n": len(y.get("kicker", ""))})]
    if "thesis" in spec:
        th = spec["thesis"]
        out.append(("kz_typing", th["at"] + 0.3, 0, {"n": len(th["old"])}))
        if th.get("strike") is not None:
            out.append(("kz_scratch", th["strike"], 0, {"d": 0.45}))
        if th.get("new_at") is not None:
            out.append(("kz_thud", th["new_at"], -6, {}))
    return out


def photos(spec):
    return sorted({c["photo"] for c in spec.get("cards", []) if c.get("photo")})


# ------------------------------------------------------------------ building the board (once per process)
def _shadowed(pw, ph):
    pad = int(50 * R)
    c = Image.new("RGBA", (pw + 2 * pad, ph + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", c.size, 0)
    ImageDraw.Draw(sh).rectangle([pad, pad + 16 * R, pad + pw, pad + ph + 16 * R], fill=130)
    c.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(14 * R)))
    return c, pad


def _hubble(d, pw, ph, fd):
    ox, oy, ex, ey = 70 * R, ph - 70 * R, pw - 40 * R, 120 * R
    d.line([(ox, oy), (ex, oy)], fill=INK, width=4)
    d.line([(ox, oy), (ox, ey)], fill=INK, width=4)
    fm = font("mono", 20 * R, fd)
    d.text((ex - 300 * R, oy + 12 * R), "DISTANCE ->", font=fm, fill=INK)
    d.text((ox + 10 * R, ey - 50 * R), "DIMMER ^", font=fm, fill=INK)
    curve = lambda u, lift=0.0: (ox + (ex - ox) * u, oy - (oy - ey) * (0.55 * u ** 0.8 + lift))
    pts = [curve(u) for u in np.linspace(0.02, 1, 40)]
    for i in range(0, len(pts) - 1, 2):
        d.line([pts[i], pts[i + 1]], fill=(90, 84, 76), width=5)
    d.text((pts[-1][0] - 250 * R, pts[-1][1] + 12 * R), "EXPECTED", font=fm, fill=(90, 84, 76))
    for u, lift in [(u, 0) for u in (0.08, 0.14, 0.2, 0.27, 0.34)] + [(.62, .1), (.7, .13), (.78, .15), (.86, .17), (.93, .2)]:
        x, y = curve(u, lift)
        d.ellipse([x - 7 * R, y - 7 * R, x + 7 * R, y + 7 * R], fill=INK)


def _pie(d, pw, ph, fd):
    cx, cy, r = pw / 2, ph / 2 + 40 * R, 210 * R
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=6)


DRAW = {"hubble": _hubble, "pie": _pie}


def _card(c, assets, fd, rng):
    """BGRA image of one card, and the size (board units) of its content area."""
    if c.get("photo"):
        im = Image.open(os.path.join(assets, "photos", c["photo"] + ".jpg")).convert("RGB")
        if c.get("crop"):
            im = im.crop(tuple(c["crop"]))
        pw = int(c["w"] * R)
        ph = int(im.height * pw / im.width)
        im = im.resize((pw, ph), Image.LANCZOS)
        b = int(14 * R)
        cv_, pad = _shadowed(pw + 2 * b, ph + 2 * b)
        paper = Image.new("RGBA", (pw + 2 * b, ph + 2 * b), (234, 227, 210, 255))
        paper.paste(im, (b, b))
        cv_.alpha_composite(paper, (pad, pad))
        size = (c["w"] + 28, ph / R + 28)
    else:
        pw, ph = int(c["w"] * R), int(c["h"] * R)
        cv_, pad = _shadowed(pw, ph)
        p = Image.new("RGBA", (pw, ph), (228, 218, 196, 255))
        d = ImageDraw.Draw(p)
        for i in range(0, ph, int(26 * R)):
            d.line([(0, i), (pw, i)], fill=(205, 196, 176), width=2)
        lines = list(c.get("paper", []))
        if c.get("title"):
            lines = [[c["title"], 30]] + lines
        y = 40 * R
        for txt, sz in lines:
            d.text((36 * R, y), txt, font=font("mono", sz * R, fd), fill=INK)
            y += sz * R * 1.7
        if c.get("draw"):
            DRAW[c["draw"]](d, pw, ph, fd)
        cv_.alpha_composite(p, (pad, pad))
        size = (c["w"], c["h"])
    return cv2.cvtColor(np.array(cv_), cv2.COLOR_RGBA2BGRA), size


def _stamp(text, fd, rng, size=110):
    f = font("serif", size * R, fd)
    tw, th = f.getbbox(text)[2] + 60 * R, size * 1.45 * R
    c = Image.new("RGBA", (int(tw), int(th)), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rectangle([6 * R, 6 * R, tw - 6 * R, th - 6 * R], outline=RED + (235,), width=int(9 * R))
    d.text((30 * R, 10 * R), text, font=f, fill=RED + (235,))
    a = np.array(c)
    a[..., 3] = a[..., 3] * (rng.random(a.shape[:2]) > .22)
    return cv2.cvtColor(a, cv2.COLOR_RGBA2BGRA)


def _build(spec, assets, fd):
    rng = np.random.default_rng(1)
    WW, WH = spec.get("world", [4200, 3300])
    bg = np.zeros((WH, WW, 3), np.float32) + np.array(spec.get("bg", [38, 26, 18]), np.float32)  # BGR deep navy
    n = cv2.resize(rng.random((WH // 40, WW // 40)).astype(np.float32), (WW, WH), interpolation=cv2.INTER_CUBIC)
    bg += (n[..., None] - .5) * 14
    for g in range(0, WW, 250):
        bg[:, g:g + 2] += 7
    for g in range(0, WH, 250):
        bg[g:g + 2, :] += 7
    bg[rng.random((WH, WW)) > .9993] += 70
    B = {"bg": np.clip(bg, 0, 255).astype(np.uint8), "cards": {}, "order": []}
    for c in spec.get("cards", []):
        img, size = _card(c, assets, fd, rng)
        B["cards"][c["id"]] = dict(c, img=img, size=size, rot=c.get("rot", 0))
        B["order"].append(c["id"])
    if "stamp" in spec:
        B["stamp"] = _stamp(spec["stamp"]["text"], fd, rng)
    yy, xx = np.ogrid[:H, :W]
    B["vig"] = (1 - .45 * np.clip(((xx - W / 2) / (W * .62)) ** 2 + ((yy - H / 2) / (H * .62)) ** 2, 0, 1))[..., None].astype(np.float32)
    B["grain"] = [rng.normal(0, 7, (H, W, 1)).astype(np.float32) for _ in range(6)]
    B["keys"] = _camera_keys(spec, B)
    return B


# ------------------------------------------------------------------ geometry
def card_pt(cd, uv):
    """A point given as 0..1 across a card (u right, v down), in board units, with the card's rotation."""
    w, h = cd["size"]
    x, y = (uv[0] - .5) * w, (uv[1] - .5) * h
    a = math.radians(cd["rot"])
    return (cd["pos"][0] + x * math.cos(a) - y * math.sin(a), cd["pos"][1] + x * math.sin(a) + y * math.cos(a))


def where(B, on, uv=(0.5, 0.5)):
    return card_pt(B["cards"][on], uv) if isinstance(on, str) else tuple(on)


def edge_toward(cd, p):
    """Where the line from a card's centre to p leaves the card (strings start at the card's edge)."""
    cx, cy = cd["pos"]
    w, h = cd["size"]
    dx, dy = p[0] - cx, p[1] - cy
    k = min(abs((w / 2 - 20) / dx) if dx else 1e9, abs((h / 2 - 20) / dy) if dy else 1e9, 1.0)
    return cx + dx * k, cy + dy * k


def _camera_keys(spec, B):
    """(t, cx, cy, zoom, rot) pairs: each camera entry -> a move key and a slow drift key before the next move."""
    cards = B["cards"]

    def fit(ids, margin=1.0):
        xs, ys = [], []
        for i in ids:
            cd = cards[i]
            w, h = cd["size"]
            xs += [cd["pos"][0] - w / 2, cd["pos"][0] + w / 2]
            ys += [cd["pos"][1] - h / 2, cd["pos"][1] + h / 2]
        bw, bh = max(xs) - min(xs) + 260, max(ys) - min(ys) + 260
        return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(W / bw, H / bh) * margin)

    cam = spec.get("camera") or [{"at": 0, "look": "all"}]
    keys = []
    for i, c in enumerate(cam):
        look = c.get("look", "all")
        if look == "all":
            cx, cy, z = fit(B["order"])
        elif isinstance(look, str):
            cx, cy, z = fit([look], 0.8)
        else:
            cx, cy, z = look[0], look[1], 0.6
        z = c.get("zoom", z)
        t0 = c["at"] if i else 0.0
        t_move = t0 + (c.get("move", 0.7) if i else 0.0)
        t_next = cam[i + 1]["at"] if i + 1 < len(cam) else 1e4
        keys.append((t_move, cx, cy, z, c.get("rot", 0)))
        keys.append((max(t_move + 0.1, t_next), cx + c.get("pan", [0, 0])[0], cy + c.get("pan", [0, 0])[1],
                     z * c.get("drift", 1.08), c.get("rot", 0)))
    return keys


def cam(B, t):
    K = B["keys"]
    if t <= K[0][0]:
        return K[0][1:]
    for a, b in zip(K, K[1:]):
        if a[0] <= t <= b[0]:
            u = ease((t - a[0]) / (b[0] - a[0]))
            z = math.exp(math.log(a[3]) + (math.log(b[3]) - math.log(a[3])) * u)
            return (a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u, z, a[4] + (b[4] - a[4]) * u)
    return K[-1][1:]


def to_screen(p, C):
    cx, cy, z, r = C
    a = math.radians(-r)
    x, y = (p[0] - cx) * z, (p[1] - cy) * z
    return (x * math.cos(a) - y * math.sin(a) + W / 2, x * math.sin(a) + y * math.cos(a) + H / 2)


def world_M(C):
    cx, cy, z, r = C
    a = math.radians(-r)
    c, s = math.cos(a) * z, math.sin(a) * z
    return np.array([[c, -s, W / 2 - c * cx + s * cy], [s, c, H / 2 - s * cx - c * cy]], np.float32)


def blend(frame, bgra, M):
    w = cv2.warpAffine(bgra, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    a = w[..., 3:4].astype(np.float32) / 255
    frame[:] = frame * (1 - a) + w[..., :3] * a


def card_M(img, pos, rot, C, scale=1.0, dy=0.0):
    h, w = img.shape[:2]
    rr = math.radians(rot)
    k = scale / R
    c, s = math.cos(rr) * k, math.sin(rr) * k
    Lm = np.array([[c, -s, pos[0] - (c * w / 2 - s * h / 2)], [s, c, pos[1] + dy - (s * w / 2 + c * h / 2)], [0, 0, 1]])
    return (np.vstack([world_M(C), [0, 0, 1]]) @ Lm)[:2].astype(np.float32)


def wobble(c, rx, ry, frac, C, seed=0.0):
    pts = []
    for i in range(int(90 * frac) + 2):
        th = -2.3 + 2 * math.pi * 1.08 * (i / 89)
        j = 1 + .04 * math.sin(i * .7 + seed)
        pts.append(to_screen((c[0] + rx * j * math.cos(th), c[1] + ry * j * math.sin(th)), C))
    return pts


# ------------------------------------------------------------------ drawing
def _marks(img, spec, B, t, C, fd):
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil, "RGBA")
    z = C[2]
    for c in spec.get("cards", []):   # pie: the red share sweeps in on its word
        if c.get("draw") == "pie" and c.get("fill_at") is not None and t > c["fill_at"] - .1:
            cd = B["cards"][c["id"]]
            u = ease((t - c["fill_at"] + .1) / 1.1)
            cx, cy = to_screen(card_pt(cd, (0.5, 0.5 + 40 / cd["size"][1])), C)
            r = 200 * z
            share = c.get("pct", 50) / 100
            d.pieslice([cx - r, cy - r, cx + r, cy + r], -90 + cd["rot"], -90 + cd["rot"] + 360 * share * u, fill=RED + (225,))
            if u >= 1:
                fn = font("serif", 95 * z, fd)
                s = f"{c.get('pct')}%"
                bb = fn.getbbox(s)
                a_ = math.radians(-90 + cd["rot"] + 360 * share / 2)
                d.text((cx + .55 * r * math.cos(a_) - bb[2] / 2, cy + .55 * r * math.sin(a_) - bb[3] / 2), s, font=fn,
                       fill=(242, 238, 228, 255))
    for ul in spec.get("underlines", []):
        if t > ul["at"] - .1:
            u = ease((t - ul["at"] + .1) / .5)
            a = to_screen(where(B, ul["on"], ul["uv"][0]), C)
            b = to_screen(where(B, ul["on"], ul["uv"][1]), C)
            d.line([a, (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)], fill=RED + (240,), width=max(4, int(7 * z)))
    for c in spec.get("circles", []):
        if t >= c["at"]:
            rx, ry = c.get("r", [120, 90])
            d.line(wobble(where(B, c["on"], c.get("uv", (.5, .5))), rx, ry, clamp((t - c["at"]) / c.get("dur", .45)), C, c["at"]),
                   fill=RED + (240,), width=max(3, int(6 * z)), joint="curve")
    for s_ in spec.get("strings", []):
        if t < s_["at"]:
            continue
        pa = where(B, s_["from"], s_.get("from_uv", (.5, .5)))
        pb = where(B, s_["to"], s_.get("to_uv", (.5, .5)))
        if isinstance(s_["from"], str) and "from_uv" not in s_:
            pa = edge_toward(B["cards"][s_["from"]], pb)
        if isinstance(s_["to"], str) and "to_uv" not in s_:
            pb = edge_toward(B["cards"][s_["to"]], pa)
        u = ease((t - s_["at"]) / s_.get("dur", .7))
        a, b0 = to_screen(pa, C), to_screen(pb, C)
        b = (a[0] + (b0[0] - a[0]) * u, a[1] + (b0[1] - a[1]) * u + math.sin(u * math.pi) * 25 * z)
        d.line([a, b], fill=RED + (230,), width=max(2, int(4 * z)))
        for p in (a, b):
            d.ellipse([p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7], fill=RED + (255,))
    fm = font("mono", 32, fd)
    rv_ = spec.get("reveal")
    for tg in spec.get("tags", []):
        if t < tg["at"]:
            continue
        life = 1 - ss((t - tg["at"] - 7) / .5)
        if rv_ is not None and t > rv_:
            life = max(life, ss((t - rv_) / .6))
        if life <= 0:
            continue
        LA = int(235 * life)
        txt = tg["text"]
        n = min(len(txt), int((t - tg["at"]) * 22))
        s = txt[:n] + ("_" if n < len(txt) or (int(t * 2.5) % 2 == 0 and t - tg["at"] < 3) else "")
        p = to_screen(where(B, tg["on"], tg.get("uv", (.5, .5))), C)
        off = tg.get("off", [60, -60])
        q = (p[0] + off[0], p[1] + off[1])
        if not (-400 < q[0] < W + 100 and -100 < q[1] < H + 100):
            continue
        tw = fm.getbbox(txt + "_")[2]
        d.line([p, (q[0], q[1] + 22)], fill=RED + (LA,), width=2)
        d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=RED + (LA,))
        d.rectangle([q[0] - 10, q[1] - 4, q[0] + tw + 10, q[1] + 46], fill=(14, 14, 14, LA))
        d.text((q[0], q[1] + 2), s, font=fm, fill=(235, 235, 228, LA))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def _center(d, y, s, f, fill):
    d.text(((W - f.getbbox(s)[2]) / 2, y), s, font=f, fill=fill)


def _screen(img, spec, t, fd):
    out = img.astype(np.float32)
    y = spec.get("year")
    if y and y["at"] < t < y["end"]:
        a = ss((t - y["at"]) / .3) * (1 - ss((t - y["end"] + .4) / .4))
        out *= 1 - .5 * a
        fl = math.exp(-(t - y["at"]) * 5) * a
        yy, xx = np.ogrid[:H, :W]
        g = np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - H / 2) / 400) ** 2))
        out += (g * fl * 120)[..., None] * np.array([40, 120, 230]) / 230
        pil = Image.fromarray(cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(pil, "RGBA")
        y0, y1 = int(y.get("from", y["year"])), int(y["year"])
        yr = str(y0 + round((y1 - y0) * clamp((t - y["at"] - .15) / .7)))
        al = int(255 * a)
        if y.get("kicker"):
            _center(d, 340, y["kicker"], font("mono", 44, fd), (220, 220, 210, al))
        _center(d, 420, yr, font("serif", 190, fd), (240, 236, 225, al))
        d.line([(560, 640), (860, 640)], fill=(200, 200, 190, al), width=2)
        d.line([(1060, 640), (1360, 640)], fill=(200, 200, 190, al), width=2)
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    th = spec.get("thesis")
    if th and th["at"] < t < th["end"]:
        a = ss((t - th["at"]) / .5) * (1 - ss((t - th["end"] + .5) / .5))
        out *= 1 - .6 * a
        pil = Image.fromarray(cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB))
        d = ImageDraw.Draw(pil, "RGBA")
        al = int(255 * a)
        f1 = font("mono", 56, fd)
        s1 = th["old"]
        n = min(len(s1), int(max(0, t - th["at"] - .3) * 20))
        w1 = f1.getbbox(s1)[2]
        x1 = (W - w1) / 2
        d.text((x1, 380), s1[:n], font=f1, fill=(220, 220, 212, al))
        if th.get("strike") is not None and t > th["strike"]:
            u = ease((t - th["strike"]) / .45)
            d.line([(x1 - 10, 414), (x1 - 10 + (w1 + 20) * u, 414)], fill=RED + (al,), width=7)
        if th.get("new") and th.get("new_at") is not None and t > th["new_at"]:
            f2 = font("serif", 140, fd)
            s2 = th["new"]
            n2 = min(len(s2), int((t - th["new_at"]) * 16))
            w2 = f2.getbbox(s2 + ".")[2]
            d.text(((W - w2) / 2, 490), s2[:n2], font=f2, fill=(242, 238, 228, al))
            if n2 == len(s2):
                d.text(((W - w2) / 2 + f2.getbbox(s2)[2], 490), ".", font=f2, fill=RED + (al,))
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return np.clip(out, 0, 255).astype(np.uint8)


def frame(spec, t, D, assets, fonts_dir="", key=None):
    """One BGR frame (W x H) of a resolved board spec at scene time t (scene length D)."""
    key = key or id(spec)
    if key not in _BOARDS:
        _BOARDS[key] = _build(spec, assets, fonts_dir)
    B = _BOARDS[key]
    C = list(cam(B, t))
    st = spec.get("stamp")
    if st and st["at"] < t < st["at"] + .35:   # the stamp shakes the board
        k = (1 - (t - st["at"]) / .35) * 14
        C[0] += k * math.sin(t * 90) / C[2]
        C[1] += k * math.cos(t * 77) / C[2]
    fr = cv2.warpAffine(B["bg"], world_M(C), (W, H), flags=cv2.INTER_LINEAR, borderValue=(30, 22, 16)).astype(np.float32)
    for cid in B["order"]:
        cd = B["cards"][cid]
        if t < cd.get("at", 0):
            continue
        u = (t - cd.get("at", 0)) / .45
        p = to_screen(cd["pos"], C)
        r = max(cd["img"].shape[:2]) / R * C[2]
        if p[0] + r < 0 or p[0] - r > W or p[1] + r < 0 or p[1] - r > H:
            continue
        im = cd["img"]
        if u < 1:
            im = im.copy()
            im[..., 3] = (im[..., 3] * ss(u * 1.6)).astype(np.uint8)
        blend(fr, im, card_M(im, cd["pos"], cd["rot"], C, 1.12 - .12 * backout(u), -60 * (1 - ease(u))))
    if st and t > st["at"]:
        u = (t - st["at"]) / .2
        blend(fr, B["stamp"], card_M(B["stamp"], st["pos"], st.get("rot", -10), C, 1.6 - .6 * backout(u, 2.2)))
    img = _screen(_marks(np.clip(fr, 0, 255).astype(np.uint8), spec, B, t, C, fonts_dir), spec, t, fonts_dir)
    f = img.astype(np.float32)
    if st and st["at"] < t < st["at"] + .2:      # RGB split on the slam
        f[..., 2] = np.roll(f[..., 2], 10, axis=1)
        f[..., 0] = np.roll(f[..., 0], -10, axis=1)
    f = f * B["vig"] + B["grain"][int(t * FPS) % 6]
    return np.clip(f, 0, 255).astype(np.uint8)


if __name__ == "__main__":   # preview: python board.py board.json assets fonts out.mp4 [t1,t2,...]
    import json
    import subprocess
    sp = json.load(open(sys.argv[1]))
    D = float(sp.get("duration", 40))
    ts = [float(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else [i / FPS for i in range(int(D * FPS))]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r",
                           str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                           sys.argv[4]], stdin=subprocess.PIPE)
    for t in ts:
        ff.stdin.write(frame(sp, t, D, sys.argv[2], sys.argv[3]).tobytes())
    ff.stdin.close()
    ff.wait()
