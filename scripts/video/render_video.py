"""Science-Time-style documentary renderer.

  python render_video.py <shots.json> <timeline.json> <narration.wav> <assets_dir> <fonts_dir> <out.mp4>
        [--check] [--only N] [--workers 4]

Builds the full video from a shot list keyed to narration words:
- photos: slow zoom/pan (Ken Burns), optional purple-halo / ring overlay
- procedural graphics (starfield, orbits, rotation curve, pie, collision, cosmic web, ...)
- English labels appear at the spoken word (character timings from ElevenLabs), each with a soft "pop"
- title card + chapter cards in the narration gaps (whoosh), booms on key moments
- original synthesized score: cold-open pad + sub-bass space drone; master at -14 LUFS
--check validates every trigger and prints the shot plan without rendering.
"""
import argparse, json, math, os, subprocess, sys, tempfile
from functools import lru_cache
from multiprocessing import Pool
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
SR = 44100
PURPLE = (200, 90, 255)  # RGB
G = {}  # per-process globals


# ---------------------------------------------------------------- planning
def load_plan(shots_path, timeline_path):
    spec = json.load(open(shots_path))
    tl = json.load(open(timeline_path))
    off = spec.get("lead_in", 0.0)
    secs = {s["id"]: s for s in tl["sections"]}
    order = [s["id"] for s in tl["sections"]]

    def t_of(sec, trig):
        s = secs[sec]
        text = "".join(s["chars"])
        occ = 1
        if "#" in trig[1:]:
            trig, occ = trig.rsplit("#", 1)
            occ = int(occ)
        i = -1
        for _ in range(occ):
            i = text.find(trig, i + 1)
        if i < 0:
            raise SystemExit(f"[{sec}] trigger not found: {trig!r}")
        return s["char_start"][i] + off

    shots, sfx = [], []
    total = tl["total"] + off + 3.0
    for k, sid in enumerate(order):
        s = secs[sid]
        start, end = s["start"] + off, s["end"] + off
        if sid in spec["cards"]:
            prev_end = secs[order[k - 1]]["end"] + off
            card_start = prev_end
            if k == 1:  # title card first, then chapter card
                tdur = 2.4
                shots.append({"kind": "title", "t0": prev_end, "t1": prev_end + tdur, "text": spec["title_card"]})
                sfx.append(("boom", prev_end + 0.05))
                card_start = prev_end + tdur
            shots.append({"kind": "card", "t0": card_start, "t1": start + 1.0, "text": spec["cards"][sid]})
            sfx.append(("whoosh", card_start))
            first_t0 = start + 1.0
        else:
            first_t0 = 0.0 if k == 0 else start
        lst = spec["sections"][sid]
        t0s = [first_t0] + [t_of(sid, sh["at"]) for sh in lst[1:]]
        for j, sh in enumerate(lst):
            t0 = max(t0s[j], first_t0)
            t1 = t0s[j + 1] if j + 1 < len(lst) else (end if k + 1 < len(order) else total)
            labels = []
            for lb in sh.get("labels", []):
                lt = max(t_of(sid, lb["at"]), t0)
                if lt >= t1 - 0.3:
                    raise SystemExit(f"[{sid}] label {lb['text']!r} falls outside its shot")
                labels.append({**lb, "t": lt - t0})
                sfx.append(("pop", lt))
            for fx in sh.get("sfx", []):
                sfx.append((fx["type"], t_of(sid, fx["at"])))
            shots.append({"kind": "img" if "img" in sh else "gfx", **sh, "t0": t0, "t1": t1, "labels": labels, "sec": sid})
    # frame-exact boundaries
    for sh in shots:
        sh["f0"], sh["f1"] = round(sh["t0"] * FPS), round(sh["t1"] * FPS)
    return shots, sfx, total, off


# ---------------------------------------------------------------- text
@lru_cache(maxsize=512)
def text_rgba(text, size, font="Anton", color=(255, 255, 255)):
    f = ImageFont.truetype(os.path.join(G["fonts"], f"{font}.ttf"), size)
    if font == "Montserrat":
        f.set_variation_by_name("SemiBold")
    bbox = f.getbbox(text)
    w, h = bbox[2] - bbox[0] + 40, bbox[3] - bbox[1] + 40
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((20 - bbox[0] + 3, 20 - bbox[1] + 4), text, font=f, fill=(0, 0, 0, 200))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    ImageDraw.Draw(sh).text((20 - bbox[0], 20 - bbox[1]), text, font=f, fill=tuple(color) + (255,))
    a = np.array(sh).astype(np.float32)
    return a[..., [2, 1, 0]], a[..., 3:] / 255.0  # BGR, alpha


def blit(frame, bgr, alpha, x, y, op=1.0):
    h, w = alpha.shape[:2]
    x, y = int(x), int(y)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    a = alpha[y0 - y:y1 - y, x0 - x:x1 - x] * op
    reg = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (reg * (1 - a) + bgr[y0 - y:y1 - y, x0 - x:x1 - x] * a).astype(np.uint8)


ANCHOR = {"center": (0.5, 0.5), "lower": (0.5, 0.66), "top": (0.5, 0.12), "bottom": (0.5, 0.86),
          "tl": (0.06, 0.1), "tr": (0.94, 0.1), "bl": (0.06, 0.86), "br": (0.94, 0.86)}


def draw_text(frame, text, size, pos, op=1.0, color=(255, 255, 255), font="Anton", stack=0, align=None):
    bgr, a = text_rgba(text, size, font, tuple(color))
    h, w = a.shape[:2]
    ax, ay = ANCHOR[pos] if isinstance(pos, str) else pos
    align = align or ("left" if ax < 0.3 else "right" if ax > 0.7 else "center")
    x = ax * W - {"left": 0, "right": w, "center": w / 2}[align]
    y = ay * H - h / 2 + stack * (size * 1.15)
    blit(frame, bgr, a, x - {"left": 20, "right": -20, "center": w * 0}[align], y, op)


def draw_labels(frame, shot, t):
    seen = {}
    for lb in shot["labels"]:
        if t < lb["t"]:
            continue
        pos = lb.get("pos", "bottom")
        k = seen.get(pos, 0)
        seen[pos] = k + 1
        op = min(1.0, (t - lb["t"]) / 0.3)
        draw_text(frame, lb["text"], lb.get("size", 64), pos, op, lb.get("color", (255, 255, 255)), stack=k)


# ---------------------------------------------------------------- helpers
def ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


@lru_cache(maxsize=256)
def glow_sprite(r, color, power=2.0):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(xx ** 2 + yy ** 2) / r
    a = np.clip(1 - d, 0, 1) ** power
    bgr = np.zeros(a.shape + (3,), np.float32)
    bgr[:] = color[::-1]
    return bgr, a[..., None]


def add_glow(frame, cx, cy, r, color, op=1.0, power=2.0):
    r = max(int(r), 2)
    if r > 24:
        r = int(round(r / 6) * 6)
    bgr, a = glow_sprite(r, tuple(color), power)
    x, y = int(cx - r), int(cy - r)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + 2 * r + 1, W), min(y + 2 * r + 1, H)
    if x1 <= x0 or y1 <= y0:
        return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x] * op
    reg = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = np.clip(reg + bgr[y0 - y:y1 - y, x0 - x:x1 - x] * aa, 0, 255).astype(np.uint8)


def paste(frame, bgr, alpha, x, y):
    """Alpha-blend bgr (h,w,3) with alpha (h,w) at (x, y), clipped to the frame."""
    h, w = alpha.shape[:2]
    x, y = int(x), int(y)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    a = alpha[y0 - y:y1 - y, x0 - x:x1 - x, None]
    reg = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (reg * (1 - a) + bgr[y0 - y:y1 - y, x0 - x:x1 - x] * a).astype(np.uint8)


def bh(frame, cx, cy, r, op=1.0, hot=(255, 170, 80)):
    """A black hole: warm haze, a bright photon ring and a black shadow."""
    if r < 2 or op <= 0:
        return
    add_glow(frame, cx, cy, r * 3.0, hot, 0.32 * op, 2.2)
    R = int(r * 1.6) + 6
    layer = np.zeros((2 * R, 2 * R, 3), np.float32)
    cv2.circle(layer, (R, R), int(r * 1.12), tuple(float(c) for c in hot[::-1]), max(2, int(r * 0.14)), cv2.LINE_AA)
    layer = cv2.GaussianBlur(layer, (0, 0), max(1.5, r * 0.07))
    x, y = int(cx - R), int(cy - R)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + 2 * R, W), min(y + 2 * R, H)
    if x1 <= x0 or y1 <= y0:
        return
    reg = frame[y0:y1, x0:x1].astype(np.float32) + layer[y0 - y:y1 - y, x0 - x:x1 - x] * 1.6 * op
    m = np.zeros((2 * R, 2 * R), np.float32)
    cv2.circle(m, (R, R), int(r), 1.0, -1, cv2.LINE_AA)
    reg *= 1 - m[y0 - y:y1 - y, x0 - x:x1 - x, None] * op
    frame[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)



def starfield_canvas(seed=7):
    rng = np.random.default_rng(seed)
    c = np.zeros((H * 2, W * 2, 3), np.float32)
    n = 5200
    xs, ys = rng.integers(0, W * 2, n), rng.integers(0, H * 2, n)
    br = rng.power(4, n) * 255
    tint = rng.uniform(0.85, 1.0, (n, 3))
    c[ys, xs] = br[:, None] * tint
    big = rng.choice(n, 140, replace=False)
    for i in big:
        cv2.circle(c, (int(xs[i]), int(ys[i])), int(rng.integers(1, 3)), (br[i],) * 3, -1, cv2.LINE_AA)
    c = cv2.GaussianBlur(c, (0, 0), 0.6) * 1.6
    haze = cv2.GaussianBlur(rng.random((H * 2 // 16, W * 2 // 16)).astype(np.float32), (0, 0), 3)
    haze = cv2.resize(haze, (W * 2, H * 2)) ** 3 * 38
    c[..., 0] += haze * 1.0
    c[..., 2] += haze * 0.7
    return np.clip(c, 0, 255).astype(np.uint8)


def starfield(t, speed=12.0, dim=1.0):
    c = G["stars"]
    x = int(W / 2 + t * speed) % W
    y = int(H / 2 + t * speed * 0.35) % H
    f = c[y:y + H, x:x + W].copy()
    return f if dim == 1.0 else (f * dim).astype(np.uint8)


def remove_hlines(im, min_len=41):
    """Inpaint thin horizontal annotation lines (diagram pointers) out of a still."""
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    nb = (np.roll(g, 4, 0) + np.roll(g, -4, 0)) / 2
    mask = ((g - nb) > 35).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((1, min_len), np.uint8))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    return cv2.inpaint(im, mask, 3, cv2.INPAINT_TELEA) if mask.any() else im


def load_img(name, crop=None):
    key = (name, tuple(crop) if crop else None)
    if key not in G["imgs"]:
        im = cv2.imread(os.path.join(G["assets"], f"{name}.jpg"))
        if name == "milkyway":  # the ESA diagram has a pointer line from the core to a side panel
            im = remove_hlines(im)
        if crop:
            h, w = im.shape[:2]
            im = im[int(crop[1] * h):int(crop[3] * h), int(crop[0] * w):int(crop[2] * w)]
        G["imgs"][key] = im
    return G["imgs"][key]


def ken_burns(img, p, motion, fit="cover"):
    ih, iw = img.shape[:2]
    cover = max(W / iw, H / ih) if fit == "cover" else min(W / iw, H / ih) * 0.92
    e = ease(p)
    z, cx, cy = 1.0, iw / 2, ih / 2
    if motion == "in":
        z = 1.0 + 0.13 * e
    elif motion == "out":
        z = 1.13 - 0.13 * e
    elif motion in ("left", "right"):
        z = 1.12
        span = max(iw - W / (cover * z), 0) / 2 * 0.85
        cx = iw / 2 + (span if motion == "left" else -span) * (1 - 2 * e)
    s = cover * z
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    border = cv2.BORDER_CONSTANT if fit == "contain" else cv2.BORDER_REFLECT
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border, borderValue=(0, 0, 0))


def overlay(frame, kind, p):
    if kind == "halo":
        add_glow(frame, W / 2, H / 2, 620, PURPLE, 0.55 * ease(p * 1.6), power=1.6)
    elif kind == "ring":
        a = 0.75 * ease(p * 2)
        if "ring" not in G:
            ring = np.zeros((H, W, 3), np.uint8)
            cv2.circle(ring, (W // 2, H // 2), 300, (255, 170, 80), 38, cv2.LINE_AA)
            G["ring"] = cv2.GaussianBlur(ring, (0, 0), 26).astype(np.float32)
        ring = G["ring"]
        np.copyto(frame, np.clip(frame.astype(np.float32) + ring * a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- graphics
def gfx(name, t, D, sh):
    p = t / D
    f = starfield(t, dim=0.8)
    if name == "starfield":
        return f
    if name == "flyapart":
        rng = np.random.default_rng(3)
        n = 70
        ang, rad = rng.uniform(0, 2 * np.pi, n), rng.uniform(40, 330, n)
        sp = rng.uniform(25, 60, n)
        add_glow(f, W / 2, H / 2, 380, (255, 210, 150), 0.25)
        for a_, r_, s_ in zip(ang, rad, sp):
            r = r_ + s_ * t
            x, y = W / 2 + r * math.cos(a_), H / 2 + r * math.sin(a_) * 0.75
            add_glow(f, x, y, 9, (255, 235, 210), 0.9)
            x2, y2 = W / 2 + (r + 70) * math.cos(a_), H / 2 + (r + 70) * math.sin(a_) * 0.75
            cv2.arrowedLine(f, (int(x + 12 * math.cos(a_)), int(y + 12 * math.sin(a_))), (int(x2), int(y2)),
                            (120, 200, 255), 2, cv2.LINE_AA, tipLength=0.25)
        return f
    if name.startswith("year_counter"):  # year_counter or year_counter:<from>:<to>
        y0, y1 = (int(v) for v in name.split(":")[1:3]) if ":" in name else (1933, 1970)
        year = y0 + int(round((y1 - y0) * ease(p * 1.15)))
        draw_text(f, str(year), 260, "center")
        return f
    if name == "orbits":
        cx, cy = W / 2, H / 2 + 40
        add_glow(f, cx, cy, 90, (255, 200, 90), 1.0, 1.2)
        for r, w_, col, nm in ((200, 0.9, (90, 160, 255), "EARTH"), (470, 0.16, (255, 200, 120), "NEPTUNE")):
            cv2.ellipse(f, (int(cx), int(cy)), (r, int(r * 0.42)), 0, 0, 360, (110, 110, 110), 1, cv2.LINE_AA)
            a_ = t * w_ + (0.0 if nm == "EARTH" else 2.0)
            x, y = cx + r * math.cos(a_), cy + r * 0.42 * math.sin(a_)
            add_glow(f, x, y, 24, col[::-1] if False else col, 1.0, 1.0)
            draw_text(f, nm, 34, (x / W, (y - 40) / H), 0.9, font="Montserrat")
        return f
    if name == "rotation_curve":
        f = starfield(t, dim=0.45)
        x0, y0, x1, y1 = 300, 790, 1640, 190
        cv2.line(f, (x0, y0), (x1, y0), (200, 200, 200), 2, cv2.LINE_AA)
        cv2.line(f, (x0, y0), (x0, y1), (200, 200, 200), 2, cv2.LINE_AA)
        draw_text(f, "DISTANCE FROM CENTER", 34, ((x0 + x1) / 2 / W, (y0 + 45) / H), font="Montserrat")
        draw_text(f, "SPEED", 34, ((x0 - 20) / W, (y1 - 40) / H), font="Montserrat")
        xs = np.linspace(0.02, 1, 300)
        exp_v = xs / (xs ** 2 + 0.02) ** 0.75
        exp_v = exp_v / exp_v.max()
        obs_v = 1 - np.exp(-xs / 0.07)
        for curve, a0, a1, col, lab in ((exp_v, 0.05, 0.4, (170, 170, 170), "EXPECTED"),
                                        (obs_v * 0.95, 0.5, 0.85, (255, 120, 210), "OBSERVED")):
            q = ease((p - a0) / (a1 - a0))
            if q <= 0:
                continue
            m = max(2, int(len(xs) * q))
            pts = np.stack([x0 + xs[:m] * (x1 - x0), y0 - curve[:m] * (y0 - y1) * 0.9], 1).astype(np.int32)
            cv2.polylines(f, [pts], False, col, 5, cv2.LINE_AA)
            if q > 0.95:
                draw_text(f, lab, 52, ((pts[-1][0] - 90) / W, (pts[-1][1] - 50) / H), color=col[::-1])
        return f
    if name == "mw_spiral":
        mw = load_img("milkyway", [0.0, 0.08, 0.43, 0.92])
        z = 0.95 + 0.12 * ease(p)
        ih, iw = mw.shape[:2]
        s = min(W / iw, H / ih) * z
        M = cv2.getRotationMatrix2D((iw / 2, ih / 2), -6 * t, s)
        M[:, 2] += (W / 2 - iw / 2, H / 2 - ih / 2)
        layer = cv2.warpAffine(mw, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
        return np.maximum(f, layer)
    if name in ("halo_expand", "halo_full"):
        mw = load_img("milkyway", [0.0, 0.08, 0.43, 0.92])
        if name == "halo_expand":
            disk = 760 - 640 * ease((p - 0.15) / 0.7)
            ratio = 1.15 + 9.35 * ease((p - 0.1) / 0.75)
        else:
            disk, ratio = 120 + 20 * p, 10.5
        add_glow(f, W / 2, H / 2, disk * ratio / 2, PURPLE, 0.55, 1.3)
        ih, iw = mw.shape[:2]
        s = disk / iw
        M = np.float32([[s, 0, W / 2 - s * iw / 2], [0, s, H / 2 - s * ih / 2]])
        layer = cv2.warpAffine(mw, M, (W, H), flags=cv2.INTER_AREA, borderValue=(0, 0, 0))
        return np.maximum(f, layer)
    if name == "spectrum":
        f = (ken_burns(load_img("chandra_tel"), p, "in") * 0.45).astype(np.uint8)
        bands = ["RADIO", "MICROWAVE", "INFRARED", "VISIBLE", "UV", "X-RAY", "GAMMA"]
        cols = [(120, 60, 200), (200, 80, 160), (255, 90, 90), (255, 230, 120), (190, 120, 255), (120, 200, 255), (220, 240, 255)]
        bw, y = 240, 760
        x0 = (W - bw * 7) // 2
        scan = ease(p / 0.8) * 7
        for i, (b, c) in enumerate(zip(bands, cols)):
            lit = 1.0 if scan > i else 0.25
            cv2.rectangle(f, (x0 + i * bw + 4, y), (x0 + (i + 1) * bw - 4, y + 70), tuple(int(v * lit) for v in c[::-1]), -1)
            draw_text(f, b, 30, ((x0 + i * bw + bw / 2) / W, (y + 110) / H), font="Montserrat", op=0.5 + 0.5 * lit)
        cv2.rectangle(f, (int(x0 + min(scan, 7) * bw) - 3, y - 20), (int(x0 + min(scan, 7) * bw) + 3, y + 90), (255, 255, 255), -1)
        return f
    if name == "spacetime":
        f = starfield(t, dim=0.5)
        depth = 230 * ease(p * 2)
        cx, cy = W / 2, H / 2 + 60
        for i in range(-12, 13):
            for horiz in (True, False):
                u = np.linspace(-1, 1, 120)
                gx, gz = (u, np.full_like(u, i / 12)) if horiz else (np.full_like(u, i / 12), u)
                r2 = gx ** 2 + gz ** 2
                dip = depth * np.exp(-r2 / 0.08)
                sx = cx + gx * 900 / (1.6 + gz * 0.6)
                sy = cy + gz * 300 + dip
                pts = np.stack([sx, sy], 1).astype(np.int32)
                cv2.polylines(f, [pts], False, (230, 170, 90), 1, cv2.LINE_AA)
        add_glow(f, cx, cy + depth * 0.55, 70, (255, 160, 220), 1.0, 1.0)
        q = ease((p - 0.35) / 0.5)
        if q > 0:
            xs = np.linspace(0, W, 200)
            ys = cy - 330 + 260 * np.exp(-((xs - cx) / 260) ** 2) + (xs - cx) * 0.05
            m = max(2, int(200 * q))
            cv2.polylines(f, [np.stack([xs[:m], ys[:m]], 1).astype(np.int32)], False, (180, 245, 255), 4, cv2.LINE_AA)
        return f
    if name == "collision":
        f = starfield(t, dim=0.6)
        c = ease(p / 0.45)
        after = ease((p - 0.45) / 0.55)
        for side in (-1, 1):
            blue_x = W / 2 + side * (620 * (1 - c) + 380 * after)
            pink_x = W / 2 + side * (620 * (1 - c) * 1.0 + 110 * after)
            add_glow(f, blue_x, H / 2, 300, (90, 140, 255), 0.6, 1.4)
            add_glow(f, pink_x, H / 2, 210, (255, 90, 190), 0.75, 1.5)
            rng = np.random.default_rng(10 + side)
            for dx, dy in rng.normal(0, 85, (16, 2)):
                add_glow(f, blue_x + dx, H / 2 + dy, 8, (255, 240, 220), 0.9)
        if 0.4 < p < 0.6:
            add_glow(f, W / 2, H / 2, 500, (255, 255, 255), (1 - abs(p - 0.47) / 0.13) * 0.8, 1.2)
        return f
    if name == "balance":
        f = starfield(t, dim=0.5)
        ang = math.radians(13 * ease((p - 0.2) / 0.5))
        px, py, L = W / 2, 400, 520
        lx, ly = px - L * math.cos(ang), py - L * math.sin(ang)
        rx, ry = px + L * math.cos(ang), py + L * math.sin(ang)
        cv2.line(f, (int(px), int(py)), (int(px), 860), (200, 200, 200), 6, cv2.LINE_AA)
        cv2.line(f, (int(lx), int(ly)), (int(rx), int(ry)), (230, 230, 230), 8, cv2.LINE_AA)
        for x, y, kg, nm, col in ((lx, ly, "1 kg", "NORMAL MATTER", (255, 220, 150)), (rx, ry, "5 kg", "DARK MATTER", PURPLE)):
            cv2.line(f, (int(x), int(y)), (int(x), int(y + 170)), (200, 200, 200), 2, cv2.LINE_AA)
            cv2.ellipse(f, (int(x), int(y + 180)), (150, 26), 0, 0, 180, (220, 220, 220), 4, cv2.LINE_AA)
            add_glow(f, x, y + 140, 70 if kg == "1 kg" else 120, col, 0.8, 1.2)
            draw_text(f, kg, 70, (x / W, (y + 270) / H))
            draw_text(f, nm, 34, (x / W, (y + 340) / H), font="Montserrat", color=col)
        return f
    if name == "pie":
        f = starfield(t, dim=0.45)
        cx, cy, r = 640, 560, 330
        parts = [(0.05, (255, 210, 120), "NORMAL MATTER  5%"), (0.27, PURPLE, "DARK MATTER  27%"), (0.68, (70, 110, 200), "DARK ENERGY  68%")]
        sweep = 360 * ease(p / 0.7)
        a0 = -90
        for i, (frac, col, lab) in enumerate(parts):
            a1 = a0 + 360 * frac
            if sweep + -90 > a0:
                cv2.ellipse(f, (cx, cy), (r, r), 0, a0, min(a1, -90 + sweep), col[::-1], -1, cv2.LINE_AA)
                cv2.rectangle(f, (1140, 380 + i * 130), (1190, 430 + i * 130), col[::-1], -1)
                draw_text(f, lab, 62, (1215 / W, (405 + i * 130) / H), align="left")
            a0 = a1
        return f
    if name in ("cosmic_web", "cosmic_web_glow"):
        web = G.get("web")
        if web is None:
            web = G["web"] = make_web()
        f = ken_burns(web, p, "in" if name == "cosmic_web" else "out")
        if name == "cosmic_web_glow":
            rng = np.random.default_rng(5)
            for x, y in rng.uniform(0, 1, (60, 2)):
                add_glow(f, x * W, y * H, 14, (255, 240, 220), ease(p * 1.5) * 0.9)
        return f
    if name == "galactic_orbit":
        mw = load_img("milkyway", [0.0, 0.08, 0.43, 0.92])
        ih, iw = mw.shape[:2]
        s = H * 0.95 / ih
        M = cv2.getRotationMatrix2D((iw / 2, ih / 2), -4 * t, s)
        M[:, 2] += (W / 2 - iw / 2, H / 2 - ih / 2)
        f = np.maximum(f, cv2.warpAffine(mw, M, (W, H), borderValue=(0, 0, 0)))
        a_ = -0.6 + 0.35 * t / D
        R = 0.55 * H * 0.95 / 2
        cv2.ellipse(f, (W // 2, H // 2), (int(R), int(R)), 0, 0, 360, (90, 220, 255), 2, cv2.LINE_AA)
        x, y = W / 2 + R * math.cos(a_), H / 2 + R * math.sin(a_)
        add_glow(f, x, y, 26, (255, 230, 120), 1.0, 1.0)
        draw_text(f, "SUN", 40, (x / W, (y - 50) / H), font="Montserrat")
        return f
    if name == "wind":
        f = starfield(t, dim=0.5)
        earth = load_img("earth", [0.08, 0.08, 0.92, 0.92])
        d = 460
        e = cv2.resize(earth, (d, d), interpolation=cv2.INTER_AREA)
        mask = np.zeros((d, d), np.uint8)
        cv2.circle(mask, (d // 2, d // 2), d // 2 - 2, 255, -1, cv2.LINE_AA)
        ex, ey = W // 2 - d // 2, H // 2 - d // 2 + 30
        reg = f[ey:ey + d, ex:ex + d]
        m = (mask / 255.0)[..., None]
        f[ey:ey + d, ex:ex + d] = (reg * (1 - m) + e * m).astype(np.uint8)
        rng = np.random.default_rng(11)
        n = 260
        ys, x0s, sp = rng.uniform(80, H - 60, n), rng.uniform(0, W, n), rng.uniform(500, 900, n)
        ov = np.zeros_like(f)
        for y, x0, s in zip(ys, x0s, sp):
            x = (x0 + s * t) % (W + 200) - 100
            cv2.line(ov, (int(x - 60), int(y)), (int(x), int(y)), (255, 120, 210), 2, cv2.LINE_AA)
            cv2.circle(ov, (int(x), int(y)), 3, (255, 180, 240), -1, cv2.LINE_AA)
        return np.clip(f.astype(np.float32) + cv2.GaussianBlur(ov, (0, 0), 1.2) * 0.8, 0, 255).astype(np.uint8)
    if name in ("lz_tank", "lz_flash"):
        f = starfield(t, dim=0.35)  # dimmed moving footage when rendered by render_v2
        cx, top, bot, rw = W // 2, 250, 860, 250
        if "lzfill" not in G:
            fill = np.zeros((H, W, 3), np.uint8)
            cv2.rectangle(fill, (cx - rw, top + 60), (cx + rw, bot), (140, 70, 20), -1)
            G["lzfill"] = cv2.GaussianBlur(fill, (0, 0), 6).astype(np.float32)
        f = np.clip(f.astype(np.float32) + G["lzfill"] * (0.75 + 0.1 * math.sin(t * 2)), 0, 255).astype(np.uint8)
        for y in (top, bot):
            cv2.ellipse(f, (cx, y), (rw, 45), 0, 0, 360, (255, 220, 140), 3, cv2.LINE_AA)
        cv2.line(f, (cx - rw, top), (cx - rw, bot), (255, 220, 140), 3, cv2.LINE_AA)
        cv2.line(f, (cx + rw, top), (cx + rw, bot), (255, 220, 140), 3, cv2.LINE_AA)
        if name == "lz_flash":
            tf = sh["flash_t"]
            if t > tf:
                k = math.exp(-(t - tf) * 1.6)
                add_glow(f, cx + 40, (top + bot) / 2 + 60, 60 + 260 * (1 - k), (190, 230, 255), k, 1.0)
        return f
    if name == "probability":
        f = starfield(t, dim=0.45)
        g1 = ease(p / 0.35)
        cv2.rectangle(f, (220, 380), (220 + int(1480 * g1), 460), (255, 160, 90), -1)
        draw_text(f, "CHANCE IT'S A FLUKE:  1 IN 200", 60, (220 / W, 320 / H), op=min(1, p * 4), align="left")
        if p > 0.45:
            cv2.rectangle(f, (220, 700), (224, 780), (120, 230, 120), -1)
            draw_text(f, "NEEDED FOR A DISCOVERY:  1 IN 3,500,000", 60, (220 / W, 640 / H), op=min(1, (p - 0.45) * 4), align="left")
        return f
    if name == "observatory":
        f = starfield(t * 0.4, dim=1.0)
        if "ridge" not in G:
            rng = np.random.default_rng(4)
            xs = np.arange(W)
            y = 820 + 60 * np.sin(xs / 210) + 35 * np.sin(xs / 77 + 1) + np.cumsum(rng.normal(0, 1.2, W))
            y = cv2.GaussianBlur(y.reshape(1, -1).astype(np.float32), (0, 0), 6).ravel()
            G["ridge"] = y
        y = G["ridge"]
        mask = np.arange(H)[:, None] > y[None, :]
        f[mask] = 8
        px = int(W * 0.62)
        py = int(y[px])
        cv2.rectangle(f, (px - 60, py - 70), (px + 60, py), (14, 14, 14), -1)
        cv2.ellipse(f, (px, py - 70), (60, 55), 0, 180, 360, (18, 18, 18), -1)
        return f
    # ---- production 02: black holes
    if name == "bh_shrink":  # Sun -> a 6 km black hole, then Earth -> a marble-sized one
        for k, (cx, lab, small, img) in enumerate(((W * 0.3, "SUN", "6 km", None), (W * 0.7, "EARTH", "1.8 cm", "earth"))):
            q = ease((p - 0.08 - 0.45 * k) / 0.3)
            if p < 0.45 * k:
                continue
            r = 230 * (1 - q) + 6
            cy = H * 0.42
            if img is None:
                add_glow(f, cx, cy, r * 1.9, (255, 190, 90), 0.8 * (1 - q) + 0.1, 1.6)
                cv2.circle(f, (int(cx), int(cy)), int(r), (110, 215, 255), -1, cv2.LINE_AA)
            else:
                d = max(int(2 * r), 4)
                e = cv2.resize(load_img("earth", [0.08, 0.08, 0.92, 0.92]), (d, d), interpolation=cv2.INTER_AREA)
                m = np.zeros((d, d), np.float32)
                cv2.circle(m, (d // 2, d // 2), d // 2 - 1, 1.0, -1, cv2.LINE_AA)
                paste(f, e, m * (1 - q * 0.9), cx - d / 2, cy - d / 2)
            if q > 0.85:
                bh(f, cx, cy, 18 if k == 0 else 12, ease((q - 0.85) / 0.15))
            draw_text(f, lab, 40, (cx / W, (cy - 290) / H), font="Montserrat")
            if q > 0.9:
                draw_text(f, small, 64, (cx / W, (cy + 120) / H), op=ease((q - 0.9) / 0.1))
        return f
    if name == "dark_star":  # Michell: light leaves the star and falls back
        cx, cy, R = W / 2, H * 0.78, 190
        dim = 1 - 0.75 * ease((p - 0.35) / 0.5)
        add_glow(f, cx, cy, R * 2.2, (255, 150, 80), 0.6 * dim, 1.5)
        cv2.circle(f, (int(cx), int(cy)), R, tuple(int(c * dim) for c in (80, 150, 255)), -1, cv2.LINE_AA)
        rng = np.random.default_rng(21)
        for i in range(26):
            ang = math.radians(rng.uniform(-70, 70))
            period, ph = rng.uniform(1.6, 2.6), rng.uniform(0, 1)
            for trail in range(6):
                s = ((t - trail * 0.03) / period + ph) % 1.0
                h = 4 * s * (1 - s)  # rises, slows, falls back
                x = cx + math.sin(ang) * (R + 330 * h * 0.55) + math.sin(ang) * 120 * s
                y = cy - math.cos(ang) * R - 520 * h * math.cos(ang) ** 0.5
                add_glow(f, x, y, 16 - 2 * trail, (255, 245, 200), (1.0 - trail * 0.14) * (0.5 + 0.5 * dim), 1.2)
        return f
    if name == "hidden_companion":  # a bright star circling something that cannot be seen
        cx, cy = W / 2, H * 0.43
        a_, b_ = 540, 210
        cv2.ellipse(f, (int(cx), int(cy)), (a_, b_), 0, 0, 360, (120, 120, 120), 1, cv2.LINE_AA)
        for k in range(0, 360, 24):
            cv2.ellipse(f, (int(cx), int(cy)), (34, 34), 0, k, k + 12, (200, 200, 200), 2, cv2.LINE_AA)
        draw_text(f, "?", 54, (cx / W, cy / H), op=0.8)
        ang = 0.9 * t
        for trail in range(10, -1, -1):
            a2 = ang - trail * 0.05
            add_glow(f, cx + a_ * math.cos(a2), cy + b_ * math.sin(a2), 40 - 2.5 * trail, (150, 200, 255), 1.0 - trail * 0.09, 1.2)
        return f
    if name == "collapse":  # a dying giant star collapses into a black hole
        cx, cy = W / 2, H * 0.44
        q = ease((p - 0.15) / 0.5)
        if p < 0.68:
            r = 300 * (1 - q) + 8
            add_glow(f, cx, cy, r * 1.8 + 20, (255, 140, 60), 0.75, 1.5)
            add_glow(f, cx, cy, r, (255, 230, 170), 1.0, 0.8)
        else:
            k = ease((p - 0.68) / 0.25)
            bh(f, cx, cy, 30 + 90 * k, 1.0)
        if 0.6 < p < 0.8:
            add_glow(f, cx, cy, 520, (255, 255, 255), (1 - abs(p - 0.68) / 0.12) * 0.7, 1.4)
        return f
    if name == "zeros" or name.startswith("zeros:"):  # 10^67 years written out; "zeros:43:of one second"
        part = name.split(":", 2)
        nz, unit = (int(part[1]), part[2].upper()) if len(part) == 3 else (67, "YEARS")
        n = int(round(nz * ease((p - 0.05) / 0.75)))
        digits = "1" + "0" * n
        per, size = 23, 92
        fw = text_rgba("0" * per, size, "Anton", (255, 255, 255))[1].shape[1]
        for li in range(3):
            seg = digits[li * per:(li + 1) * per]
            if seg:
                draw_text(f, seg, size, ((W - fw) / 2 / W + 0.012, (0.24 + 0.15 * li)), align="left")
        if p > 0.82:
            draw_text(f, unit, 70, (0.5, 0.72), op=ease((p - 0.82) / 0.1), color=(255, 200, 120))
        return f
    if name == "evaporate":  # Hawking radiation: particles leak away, the hole slowly shrinks
        cx, cy = W / 2, H * 0.44
        r = 170 - 70 * ease(p)
        rng = np.random.default_rng(8)
        for i in range(70):
            ang, t0, sp = rng.uniform(0, 2 * np.pi), rng.uniform(0, D), rng.uniform(90, 200)
            s = (t - t0) % 3.0
            d = r * 1.08 + sp * s
            add_glow(f, cx + d * math.cos(ang), cy + d * math.sin(ang), 13, (220, 235, 255), max(0, 1.0 - s / 3.0), 1.3)
        bh(f, cx, cy, r, 1.0)
        return f
    if name == "tidal":  # the near side is pulled harder: spaghettification
        bx, by = 330, H * 0.43
        e = ease(p / 0.9)
        ox = 1380 - 560 * e
        rng = np.random.default_rng(12)
        pts = rng.normal(0, 1, (160, 2))
        pts /= np.maximum(np.linalg.norm(pts, axis=1, keepdims=True), 1e-6)
        pts *= rng.uniform(0, 1, (160, 1)) ** 0.5 * 120
        bh(f, bx, by, 95, 1.0)
        for dx, dy in pts:
            sx = dx * (1 + 3.2 * e) - 140 * e * (dx < 0) * (abs(dx) / 120) ** 2
            add_glow(f, ox + sx, by + dy * (1 - 0.7 * e), 9, (255, 220, 160), 0.9)
        for fx, ln in ((-1, 1.0), (0, 0.6), (1, 0.35)):
            x = ox + fx * 120 * (1 + 3.2 * e)
            L = 70 + 130 * ln * (0.5 + e)
            cv2.arrowedLine(f, (int(x), int(by - 210)), (int(x - L), int(by - 210)), (120, 200, 255), 4, cv2.LINE_AA, tipLength=0.25)
        return f
    if name == "redshift_fall":  # seen from far away, a falling light slows, reddens and fades at the horizon
        cx, cy, r = 700, H * 0.44, 150
        edge = cx + r * 1.06
        for trail in range(14, -1, -1):
            tt = max(t - trail * 0.06, 0)
            x = edge + (1700 - edge) * math.exp(-tt / (D * 0.38))
            q = min(1.0, tt / D)
            col = (int(200 + 55 * q), int(230 - 190 * q), int(255 - 225 * q))
            add_glow(f, x, cy, 30 - 1.5 * trail, col, (1 - q ** 1.5) * (1 - trail / 15), 1.2)
        bh(f, cx, cy, r, 1.0)
        return f
    if name == "s2_orbit":  # S2 on its 16-year orbit around Sagittarius A*
        e_, a_ = 0.88, 440
        b_ = a_ * math.sqrt(1 - e_ ** 2)
        fx, fy = W / 2 - 240, H * 0.43
        ocx = fx + a_ * e_
        rng = np.random.default_rng(31)
        for k in range(4):  # other S-stars
            aa, ee, rot = rng.uniform(180, 380), rng.uniform(0.3, 0.8), rng.uniform(0, 180)
            bb = aa * math.sqrt(1 - ee ** 2)
            M = 2 * math.pi * (t / rng.uniform(7, 14) + rng.uniform(0, 1))
            E = M
            for _ in range(8):
                E = M + ee * math.sin(E)
            x, y = aa * (math.cos(E) - ee), bb * math.sin(E)
            c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            add_glow(f, fx + c * x - s * y, fy + s * x + c * y, 12, (200, 210, 255), 0.7)
        cv2.ellipse(f, (int(ocx), int(fy)), (int(a_), int(b_)), 0, 0, 360, (150, 150, 150), 1, cv2.LINE_AA)
        add_glow(f, fx, fy, 60, (230, 170, 255), 0.9, 1.4)
        draw_text(f, "SGR A*", 38, (fx / W, (fy + 70) / H), font="Montserrat", color=(230, 190, 255))
        for trail in range(12, -1, -1):
            M = math.pi + 2 * math.pi * max(t - trail * 0.05, 0) / max(D, 1)
            E = M
            for _ in range(12):
                E = M + e_ * math.sin(E)
            x, y = ocx + a_ * math.cos(E), fy + b_ * math.sin(E)
            add_glow(f, x, y, 26 - 1.5 * trail, (170, 210, 255), 1 - trail * 0.075, 1.2)
        draw_text(f, "S2", 40, (x / W, (y - 55) / H), font="Montserrat")
        return f
    if name == "ripples":  # spacetime itself ripples outward
        f = starfield(t, dim=0.5)
        cx, cy = W / 2, H / 2 + 20
        for i in range(-12, 13):
            for horiz in (True, False):
                u = np.linspace(-1, 1, 140)
                gx, gz = (u, np.full_like(u, i / 12)) if horiz else (np.full_like(u, i / 12), u)
                rr = np.sqrt(gx ** 2 + (gz * 1.2) ** 2)
                dz = 60 * np.sin(rr * 22 - t * 5.0) / (0.4 + rr * 2.0)
                sx = cx + gx * 900 / (1.6 + gz * 0.6)
                sy = cy + gz * 300 + dz
                cv2.polylines(f, [np.stack([sx, sy], 1).astype(np.int32)], False, (230, 170, 90), 1, cv2.LINE_AA)
        for k in (0, 1):
            a2 = t * 3.0 + k * math.pi
            add_glow(f, cx + 34 * math.cos(a2), cy + 12 * math.sin(a2), 26, (255, 200, 140), 0.9, 1.2)
        return f
    if name == "inspiral":  # two black holes spiral in, merge and ring down; the chirp is drawn on top
        cx, cy = W / 2, H * 0.52
        Tm = D * 0.72
        tau = max(Tm - t, 0.0)
        x0, x1, yc = 260, 1660, 175

        def wave(tt):
            ta = np.maximum(Tm - tt, Tm * 0.015)
            ph = -2.6 * Tm ** 0.375 * ta ** 0.625 / 0.625
            amp = (Tm / ta) ** 0.25
            h = np.where(tt < Tm, amp * np.cos(2 * ph), (Tm / (Tm * 0.015)) ** 0.25 * np.exp(-(tt - Tm) / 0.12) * np.cos(40 * (tt - Tm)))
            return h / (Tm / (Tm * 0.015)) ** 0.25
        ts = np.linspace(0, t, max(2, int(500 * t / D)))
        ys = yc - 80 * wave(ts)
        xs = x0 + (x1 - x0) * ts / D
        cv2.polylines(f, [np.stack([xs, ys], 1).astype(np.int32)], False, (255, 230, 150), 3, cv2.LINE_AA)
        if tau > 0:
            sep = 330 * (tau / Tm) ** 0.25 + 50
            ph = -2.6 * Tm ** 0.375 * max(tau, 1e-3) ** 0.625 / 0.625
            for k in range(1, 7):  # outgoing ripples
                rr = ((t * 140) + k * 120) % 720
                cv2.ellipse(f, (int(cx), int(cy)), (int(rr), int(rr * 0.42)), 0, 0, 360, (200, 160, 90), 2, cv2.LINE_AA)
            for m, sgn in ((36, 1), (29, -1)):
                rr = sep * (65 - m) / 65
                bh(f, cx + sgn * rr * math.cos(ph), cy + sgn * rr * math.sin(ph) * 0.42, m * 1.25, 1.0)
        else:
            k = t - Tm
            bh(f, cx, cy, 62 * (1 + 0.12 * math.exp(-k / 0.3) * math.sin(k * 30)), 1.0)
            if k < 0.6:
                add_glow(f, cx, cy, 560, (255, 255, 255), (1 - k / 0.6) * 0.8, 1.3)
        return f
    if name == "ligo":  # an L-shaped detector; a passing wave stretches one arm and squeezes the other
        f = starfield(t, dim=0.5)
        ox, oy, Lx, Ly = 560, 740, 900, 520
        env = math.exp(-((p - 0.5) / 0.22) ** 2)
        s = 0.1 * env * math.sin(t * 9)
        ax, ay = int(ox + Lx * (1 + s)), int(oy - Ly * (1 - s))
        for (x2, y2) in ((ax, oy), (ox, ay)):
            cv2.line(f, (ox, oy), (x2, y2), (150, 150, 150), 26, cv2.LINE_AA)
            cv2.line(f, (ox, oy), (x2, y2), (60, 60, 255), 3, cv2.LINE_AA)
            add_glow(f, x2, y2, 30, (255, 230, 200), 0.9)
        add_glow(f, ox, oy, 40, (255, 120, 120), 0.9)
        draw_text(f, "4 km", 46, ((ox + Lx / 2) / W, (oy - 60) / H), font="Montserrat")
        draw_text(f, "4 km", 46, ((ox - 40) / W, (oy - Ly / 2) / H), font="Montserrat", align="right")
        for k in range(5):
            xx = (t * 260 + k * 420) % (W + 400) - 200
            cv2.ellipse(f, (int(xx), int(H * 0.45)), (60, 520), 0, -60, 60, (200, 160, 90), 2, cv2.LINE_AA)
        return f
    if name == "eht_globe":  # radio dishes across the Earth act as one Earth-sized telescope (glass globe, chords)
        cx, cy, R = W / 2, 460, 320
        lam0, phi0 = math.radians(-115 + 60 * ease(p)), math.radians(-12)

        def proj(lat, lon):
            la, lo = math.radians(lat), math.radians(lon)
            cosc = math.sin(phi0) * math.sin(la) + math.cos(phi0) * math.cos(la) * math.cos(lo - lam0)
            x = math.cos(la) * math.sin(lo - lam0)
            y = math.cos(phi0) * math.sin(la) - math.sin(phi0) * math.cos(la) * math.cos(lo - lam0)
            return cx + R * x, cy - R * y, cosc
        add_glow(f, cx, cy, R * 1.25, (80, 140, 255), 0.3, 1.2)
        tint = np.zeros_like(f)
        cv2.circle(tint, (int(cx), int(cy)), R, (90, 50, 20), -1, cv2.LINE_AA)
        f = cv2.add(f, tint)
        cv2.circle(f, (int(cx), int(cy)), R, (200, 150, 90), 2, cv2.LINE_AA)
        grid = [[proj(lat, lo) for lo in range(-180, 181, 4)] for lat in range(-60, 90, 30)] + \
               [[proj(la, lon) for la in range(-90, 91, 4)] for lon in range(-180, 180, 30)]
        for pts in grid:
            for (x1_, y1_, c1), (x2_, y2_, c2) in zip(pts, pts[1:]):
                col = (150, 110, 70) if c1 > 0 and c2 > 0 else (70, 50, 35)
                cv2.line(f, (int(x1_), int(y1_)), (int(x2_), int(y2_)), col, 1, cv2.LINE_AA)
        sites = [("HAWAII", 19.8, -155.5), ("ARIZONA", 32.7, -109.9), ("MEXICO", 19.0, -97.3),
                 ("CHILE", -23.0, -67.8), ("SPAIN", 37.1, -3.4), ("SOUTH POLE", -89.9, 0.0)]
        vis = [(n, *proj(la, lo)) for n, la, lo in sites]
        lk = ease((p - 0.2) / 0.4)
        if lk > 0:
            for i in range(len(vis)):
                for j in range(i + 1, len(vis)):
                    cv2.line(f, (int(vis[i][1]), int(vis[i][2])), (int(vis[j][1]), int(vis[j][2])),
                             (int(140 * lk), int(230 * lk), int(255 * lk)), 2, cv2.LINE_AA)
        for n, x, y, c in vis:
            op = 1.0 if c > 0 else 0.45
            add_glow(f, x, y, 22, (255, 230, 120), op, 1.0)
            draw_text(f, n, 28, (x / W, (y - 34) / H), op=op, font="Montserrat")
        return f
    if name in ("eht_m87", "eht_sgra"):
        img = load_img(name, [0.2, 0.0, 0.8, 1.0] if name == "eht_m87" else None)
        layer = ken_burns(img, p, "in", fit="contain")
        if "vignette" not in G:  # fade the square image edges into the background
            yy, xx = np.mgrid[0:H, 0:W]
            d = np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2)
            G["vignette"] = np.clip((540 - d) / 200, 0, 1).astype(np.float32)[..., None]
        layer = (layer * G["vignette"]).astype(np.uint8)
        return np.maximum((f * 0.6).astype(np.uint8), layer)
    if name == "area_theorem":  # two horizons merge into one with a larger total area
        cx, cy = W / 2, H * 0.47
        m = ease((p - 0.42) / 0.16)
        if p < 0.55:
            for sgn in (-1, 1):
                bh(f, cx + sgn * 420 * (1 - m), cy, 95, 1.0)
            draw_text(f, "BEFORE: ~240,000 km²", 56, (0.5, 0.16), op=1 - m, font="Montserrat")
        else:
            k = ease((p - 0.55) / 0.2)
            bh(f, cx, cy, 95 + 78 * k, 1.0)
            draw_text(f, "AFTER: ~400,000 km²", 56, (0.5, 0.16), op=k, font="Montserrat", color=(255, 210, 130))
        if 0.5 < p < 0.66:
            add_glow(f, cx, cy, 520, (255, 255, 255), (1 - abs(p - 0.56) / 0.1) * 0.75, 1.3)
        return f
    if name == "bh_share":  # QSO1: the black hole is two-thirds of all the mass
        cx, cy, r = 640, 470, 300
        sweep = 360 * ease(p / 0.6)
        cv2.circle(f, (cx, cy), r, (60, 60, 60), 2, cv2.LINE_AA)
        if sweep > 0:
            cv2.ellipse(f, (cx, cy), (r, r), 0, -90, -90 + min(sweep, 240), (10, 10, 10), -1, cv2.LINE_AA)
            cv2.ellipse(f, (cx, cy), (r, r), 0, -90, -90 + min(sweep, 240), (80, 170, 255), 6, cv2.LINE_AA)
        if sweep > 240:
            cv2.ellipse(f, (cx, cy), (r, r), 0, 150, -90 + sweep, (230, 170, 120), -1, cv2.LINE_AA)
        op = ease((p - 0.55) / 0.2)
        draw_text(f, "BLACK HOLE  2/3", 62, (1080 / W, 380 / H), op=op, align="left", color=(255, 180, 90))
        draw_text(f, "STARS + GAS  1/3", 62, (1080 / W, 520 / H), op=op, align="left", color=(130, 180, 240))
        return f
    if name == "tv_static":  # an old TV's snow: about 1 % of it is the Big Bang's light
        f = (f * 0.35).astype(np.uint8)
        x0, y0, tw, th = 510, 150, 900, 600
        snow = np.random.default_rng(int(t * 25)).integers(0, 256, (th // 4, tw // 4), dtype=np.uint8)
        tv = cv2.cvtColor(cv2.resize(snow, (tw, th), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR).astype(np.float32) * 0.8
        e = ease((p - 0.3) / 0.25)
        if e > 0:
            m = np.random.default_rng(5).random((th // 10, tw // 10)) < 0.01
            m = cv2.resize(m.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST).astype(bool)
            tv *= 1 - 0.75 * e
            tv[m] = tv[m] * (1 - e) + np.array([60, 175, 255], np.float32) * e
            glow = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 6)[..., None] * np.array([40, 120, 255], np.float32) * 1.5 * e
            tv = tv + glow
        f[y0:y0 + th, x0:x0 + tw] = np.clip(tv, 0, 255).astype(np.uint8)
        cv2.rectangle(f, (x0 - 14, y0 - 14), (x0 + tw + 14, y0 + th + 14), (70, 70, 70), 10, cv2.LINE_AA)
        op = ease((p - 0.5) / 0.15)
        draw_text(f, "ABOUT 1% OF THE STATIC", 64, (0.5, 0.85), op=op, color=(255, 190, 110))
        draw_text(f, "WAS THE ECHO OF THE BIG BANG", 40, (0.5, 0.92), op=op, color=(235, 235, 235))
        return f
    if name == "horizon":  # opposite sides of the sky never touched, yet read the same temperature
        cx, cy, R = W / 2, H * 0.47, 400
        cv2.circle(f, (int(cx), int(cy)), R, (120, 110, 90), 2, cv2.LINE_AA)
        add_glow(f, cx, cy, 14, (140, 200, 255), 1.0)
        draw_text(f, "EARTH", 30, (0.5, (cy + 40) / H), color=(200, 220, 255), font="Montserrat")
        for sx in (-1, 1):
            px = cx + sx * R
            add_glow(f, px, cy, 60, (255, 170, 90), ease(p / 0.15))
            rr = int(30 + R * 0.55 * ease((p - 0.15) / 0.5))  # as far as anything from there could have reached
            cv2.circle(f, (int(px), int(cy)), rr, (90, 170, 255), 2, cv2.LINE_AA)
            draw_text(f, "-270 °C", 48, (px / W, (cy - 110) / H), op=ease((p - 0.25) / 0.15), color=(255, 200, 130), align="center")
        op = ease((p - 0.6) / 0.15)
        draw_text(f, "NEVER IN CONTACT", 64, (0.5, 0.85), op=op)
        draw_text(f, "YET EXACTLY THE SAME", 40, (0.5, 0.92), op=op, color=(255, 190, 110))
        return f
    if name == "inflate":  # the observable universe: smaller than a proton -> a large orange
        cx, cy = W / 2, H * 0.44
        g = ease((p - 0.3) / 0.35)
        r = 3 * (150 / 3) ** g
        add_glow(f, cx, cy, max(30, r * 3), (255, 160, 70), 0.6 * (1 - g) + 0.15)
        col = tuple(int(a + (b - a) * g) for a, b in zip((220, 245, 255), (40, 140, 255)))  # BGR white-hot -> orange
        cv2.circle(f, (int(cx), int(cy)), max(2, int(r)), col, -1, cv2.LINE_AA)
        if g > 0.6:
            add_glow(f, cx - r * 0.35, cy - r * 0.35, r * 0.5, (255, 225, 180), 0.45 * ease((g - 0.6) / 0.4))
        draw_text(f, "SMALLER THAN A PROTON", 60, (0.5, 0.8), op=ease(p / 0.12) * (1 - ease((p - 0.3) / 0.1)), color=(235, 235, 235))
        op = ease((p - 0.68) / 0.12)
        draw_text(f, "THE SIZE OF A LARGE ORANGE", 60, (0.5, 0.8), op=op, color=(255, 175, 80))
        draw_text(f, "IN LESS THAN A BLINK", 38, (0.5, 0.87), op=op, color=(220, 220, 220))
        return f
    if name == "south_pole":  # Hawking's example: nothing lies south of the South Pole
        cx, cy, R, ph0, lam0 = W / 2, H * 0.44, 330, math.radians(-40), t * 0.15

        def proj(ph, la):
            ph, la = np.asarray(ph, float), np.asarray(la, float)
            c = math.sin(ph0) * np.sin(ph) + math.cos(ph0) * np.cos(ph) * np.cos(la - lam0)
            x = cx + R * np.cos(ph) * np.sin(la - lam0)
            y = cy - R * (math.cos(ph0) * np.sin(ph) - math.sin(ph0) * np.cos(ph) * np.cos(la - lam0))
            return x, y, c > 0

        def curve(ph, la, col):
            x, y, vis = proj(ph, la)
            pts, run = np.stack([x, y], 1).astype(np.int32), []
            for i, v in enumerate(list(vis) + [False]):
                if v:
                    run.append(i)
                elif len(run) > 1:
                    cv2.polylines(f, [pts[run[0]:run[-1] + 1]], False, col, 1, cv2.LINE_AA)
                    run = []
                else:
                    run = []
        cv2.circle(f, (int(cx), int(cy)), R, (55, 40, 25), -1, cv2.LINE_AA)
        for k in range(18):
            curve(np.linspace(-np.pi / 2, np.pi / 2, 80), np.full(80, k * np.pi / 9), (170, 140, 100))
        for lat in (-60, -30, 0, 30, 60):
            curve(np.full(160, math.radians(lat)), np.linspace(0, 2 * np.pi, 160), (120, 100, 75))
        cv2.circle(f, (int(cx), int(cy)), R, (200, 170, 120), 2, cv2.LINE_AA)
        e = ease(p / 0.55)
        for back in np.linspace(0, 0.12, 7):  # the traveller and a short trail
            ph = math.radians(25 - 115 * max(0.0, e - back))
            x, y, _ = proj(ph, lam0)
            add_glow(f, float(x), float(y), 16 if back == 0 else 8, (255, 200, 110), 1.0 if back == 0 else 0.35)
        px, py, _ = proj(-np.pi / 2, lam0)
        if p > 0.55:
            q = (p - 0.55) / 0.45
            cv2.circle(f, (int(px), int(py)), int(10 + 60 * (q * 3 % 1)), (90, 180, 255), 2, cv2.LINE_AA)
            draw_text(f, "SOUTH POLE", 34, (0.5, (float(py) + 60) / H), op=ease(q / 0.2), color=(255, 200, 120), font="Montserrat")
        draw_text(f, "WHAT LIES SOUTH OF THE SOUTH POLE?", 54, (0.5, 0.09), op=ease(p / 0.1))
        draw_text(f, "NOTHING. IT IS THE END POINT", 50, (0.5, 0.88), op=ease((p - 0.7) / 0.12), color=(255, 190, 110))
        return f
    if name == "bounce":  # a universe shrinks, bounces and expands again
        rng = np.random.default_rng(11)
        d = rng.normal(size=(500, 3))
        d *= (rng.uniform(0.05, 1.0, 500) ** 0.5 / np.linalg.norm(d, axis=1))[:, None]
        s = 1 - 0.96 * ease(p / 0.5) if p < 0.5 else 0.04 + 1.25 * ease((p - 0.5) / 0.5)
        cx, cy, R, a = W / 2, H * 0.47, 420, t * 0.3
        x = d[:, 0] * math.cos(a) + d[:, 2] * math.sin(a)
        heat = max(0.0, 1 - s * 2.5)
        col = tuple(int(c0 + (c1 - c0) * heat) for c0, c1 in zip((255, 220, 190), (80, 170, 255)))
        for xx, yy in zip(cx + x * R * s, cy + d[:, 1] * R * s * 0.9):
            cv2.circle(f, (int(xx), int(yy)), 2, col, -1, cv2.LINE_AA)
        add_glow(f, cx, cy, 80 + 260 * (1 - s), (255, 190, 120), 0.25 + 0.5 * heat)
        add_glow(f, cx, cy, 320, (255, 235, 200), max(0.0, 1 - abs(p - 0.5) / 0.07) * 0.9, 1.3)
        for txt, a0, a1 in (("IT SHRINKS", 0.05, 0.42), ("IT BOUNCES", 0.47, 0.62), ("AND EXPANDS AGAIN", 0.66, 1.1)):
            draw_text(f, txt, 58, (0.5, 0.86), op=ease((p - a0) / 0.06) * (1 - ease((p - a1) / 0.05)), color=(255, 190, 110))
        return f
    if name == "bubbles":  # eternal inflation: bubble universes form in a sea that keeps expanding
        f = starfield(t, dim=0.35)
        cx, cy = W / 2, H * 0.47
        add_glow(f, cx, cy, 900, (120, 80, 200), 0.3, 1.2)
        rng = np.random.default_rng(21)
        nb = 18
        t0s = np.sort(rng.uniform(0.12, 0.85, nb))
        t0s[0] = 0.04
        pos = rng.uniform([-0.42, -0.34], [0.42, 0.34], (nb, 2))
        pos[0] = (-0.16, -0.06)
        grow = rng.uniform(0.6, 1.0, nb)
        stretch = 1 + 0.3 * p  # the space between them keeps stretching
        for i in range(nb):
            age = p - t0s[i]
            if age <= 0:
                continue
            r = 12 + 300 * age * grow[i]
            x, y = cx + pos[i, 0] * W * stretch, cy + pos[i, 1] * H * stretch
            add_glow(f, x, y, r * 0.8, (255, 190, 120), 0.22)
            cv2.circle(f, (int(x), int(y)), int(r), (110, 190, 255) if i == 0 else (200, 170, 140), 2, cv2.LINE_AA)
            if i == 0:
                draw_text(f, "A UNIVERSE", 34, (x / W, (y + r + 34) / H), op=ease(age / 0.1), color=(255, 200, 120),
                          font="Montserrat", align="center")
        draw_text(f, "LIKE BUBBLES IN BOILING WATER", 54, (0.5, 0.9), op=ease((p - 0.55) / 0.12))
        return f
    if name == "three_answers":  # the ending: three answers, none chosen yet
        cy = H * 0.45
        for k, (x, lab, st) in enumerate(zip((W * 0.2, W * 0.5, W * 0.8), ("TIME BEGAN", "ENDLESS CYCLES", "ONE BUBBLE OF MANY"),
                                             (0.02, 0.28, 0.52))):
            e = ease((p - st) / 0.1)
            if e <= 0:
                continue
            q = t - st * D
            if k == 0:  # a point that flashes and spreads
                add_glow(f, x, cy, 34 + 8 * math.sin(q * 3), (255, 230, 190), e)
                for j in range(3):
                    rr = (q * 60 + j * 50) % 150 + 10
                    cv2.circle(f, (int(x), int(cy)), int(rr), tuple(int(c * e * (1 - rr / 165)) for c in (120, 190, 255)), 2, cv2.LINE_AA)
            elif k == 1:  # a loop that keeps turning
                a0 = (q * 90) % 360
                col = tuple(int(c * e) for c in (120, 190, 255))
                cv2.ellipse(f, (int(x), int(cy)), (110, 110), 0, a0, a0 + 300, col, 4, cv2.LINE_AA)
                ah = math.radians(a0 + 300)
                hx, hy = x + 110 * math.cos(ah), cy + 110 * math.sin(ah)
                tip = (hx - 22 * math.sin(ah), hy + 22 * math.cos(ah))
                cv2.fillPoly(f, [np.array([(hx + 16 * math.cos(ah), hy + 16 * math.sin(ah)), (hx - 16 * math.cos(ah), hy - 16 * math.sin(ah)),
                                           tip], np.int32)], col, cv2.LINE_AA)
            else:  # bubbles, one of them gold
                for j, (dx, dy, r) in enumerate([(-60, -40, 38), (40, -62, 30), (72, 18, 44), (-22, 44, 34), (-84, 52, 24), (8, -4, 22)]):
                    gold = j == 5
                    cv2.circle(f, (int(x + dx), int(cy + dy)), r, tuple(int(c * e) for c in ((90, 190, 255) if gold else (190, 160, 130))),
                               -1 if gold else 2, cv2.LINE_AA)
            draw_text(f, lab, 46, (x / W, (cy + 175) / H), op=e, color=(235, 235, 235), align="center")
        op = ease((p - 0.78) / 0.1)
        draw_text(f, "?", 200, (0.5, 0.17), op=op, color=(255, 190, 90))
        draw_text(f, "SCIENCE HAS NOT DECIDED YET", 46, (0.5, 0.86), op=op, color=(255, 190, 110))
        return f
    raise SystemExit(f"unknown gfx {name}")


def make_web():
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(21)
    w, h = 1200, 675
    centers = rng.uniform(0, 1, (45, 2)) * (w, h)
    pts = np.concatenate([centers + rng.normal(0, 70, (45, 2)) * rng.uniform(0.3, 1.5, (45, 1)) for _ in range(5)])
    yy, xx = np.mgrid[0:h, 0:w]
    d, _ = cKDTree(pts).query(np.stack([xx.ravel(), yy.ravel()], 1), k=2)
    edge = np.exp(-((d[:, 1] - d[:, 0]) ** 2) / (2 * 1.6 ** 2)).reshape(h, w)
    big = cv2.resize(cv2.GaussianBlur(rng.random((h // 25, w // 25)).astype(np.float32), (0, 0), 1.5), (w, h))
    big = np.clip((big - big.min()) / (big.max() - big.min()), 0, 1) ** 1.6
    fine = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), 1.0)
    dens = cv2.GaussianBlur(np.exp(-d[:, 0].reshape(h, w) / 40), (0, 0), 8)
    inten = np.clip(edge * big * (0.5 + fine) * 1.4 + dens * big * 0.35, 0, 1)
    nodes = np.zeros((h, w), np.float32)
    for x, y in centers:
        cv2.circle(nodes, (int(x), int(y)), 2, 1.0, -1)
    nodes = cv2.GaussianBlur(nodes, (0, 0), 3) * 6
    inten = np.clip(inten + nodes * big, 0, 1)
    glow = cv2.GaussianBlur(inten, (0, 0), 7)
    img = np.zeros((h, w, 3), np.float32)
    img[..., 0] = 255 * np.clip(inten * 0.95 + glow * 0.8, 0, 1)
    img[..., 1] = 255 * np.clip(inten * 0.7 + glow * 0.25, 0, 1)
    img[..., 2] = 255 * np.clip(inten * 0.8 + glow * 0.55, 0, 1)
    img = (img * 0.9).astype(np.uint8)
    return cv2.resize(img, (2400, 1350), interpolation=cv2.INTER_CUBIC)


def card_frame(sh, t, D):
    f = starfield(t, speed=20, dim=0.7)
    if sh["kind"] == "title":
        op = min(1, t / 0.4)
        draw_text(f, sh["text"], int(118 + 10 * t / D), "center", op)
    else:
        num, title = sh["text"]
        op = min(1, t / 0.35)
        draw_text(f, num, 64, (0.5, 0.40), op, color=(200, 160, 255), font="Montserrat")
        draw_text(f, title, 104, (0.5, 0.53), op)
    return f


# ---------------------------------------------------------------- rendering
def init_worker(assets, fonts):
    cv2.setNumThreads(1)  # 1 thread per worker process: avoids heavy oversubscription
    G.update(assets=assets, fonts=fonts, imgs={}, stars=starfield_canvas())
    rng = np.random.default_rng(9)
    rock = cv2.GaussianBlur(rng.random((H // 4, W // 4)).astype(np.float32), (0, 0), 2)
    G["rock"] = (cv2.resize(rock, (W, H))[..., None] * np.array([18, 22, 26])).astype(np.uint8)


def render_shot(args):
    i, sh, out_dir, total_frames = args
    path = os.path.join(out_dir, f"seg_{i:03d}.mp4")
    n = sh["f1"] - sh["f0"]
    if os.path.exists(path) or n <= 0:
        return path
    D = n / FPS
    if sh["kind"] == "gfx" and sh.get("gfx") == "lz_flash":
        sh["flash_t"] = D * 0.45
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-g", "60", path + ".tmp.mp4"], stdin=subprocess.PIPE)
    for k in range(n):
        t = k / FPS
        if sh["kind"] in ("title", "card"):
            fr = card_frame(sh, t, D)
        elif sh["kind"] == "img":
            fr = ken_burns(load_img(sh["img"], sh.get("crop")), t / D, sh.get("motion", "in"), sh.get("fit", "cover"))
            if "overlay" in sh:
                overlay(fr, sh["overlay"], t / D)
            if "dim" in sh:
                fr = (fr * sh["dim"]).astype(np.uint8)
        else:
            fr = gfx(sh["gfx"], t, D, sh)
        if sh["kind"] not in ("title", "card"):
            draw_labels(fr, sh, t)
        g = sh["f0"] + k  # global fades
        if g < 30:
            fr = (fr * (g / 30)).astype(np.uint8)
        elif g > total_frames - 75:
            fr = (fr * max(0, (total_frames - g) / 75)).astype(np.uint8)
        ff.stdin.write(np.ascontiguousarray(fr).tobytes())
    ff.stdin.close()
    ff.wait()
    os.replace(path + ".tmp.mp4", path)
    return path


# ---------------------------------------------------------------- audio
def synth_audio(narr_path, sfx, total, off, cold_end):
    import soundfile as sf
    v, sr = sf.read(narr_path)
    v = v.mean(1) if v.ndim > 1 else v
    n = int(total * SR)
    mix = np.zeros((n, 2))
    o = int(off * SR)
    mix[o:o + len(v)] += v[:n - o, None]
    vr = np.sqrt(np.mean(v[np.abs(v) > 0.02] ** 2))
    t = np.arange(n) / SR
    rng = np.random.default_rng(1)

    def db(x):
        return 10 ** (x / 20)

    # sub-bass space drone (whole film), ~31 dB under the voice
    lfo = 0.7 + 0.3 * np.sin(2 * np.pi * 0.025 * t)
    dr = sum(a * np.sin(2 * np.pi * f * t + ph) for f, a, ph in ((55, 1, 0), (82.4, .5, 1), (110, .35, 2), (164.8, .12, 3)))
    noise = np.convolve(rng.normal(0, 1, n), np.ones(400) / 400, "same")
    dr = (dr * lfo + noise * 2.0)
    dr *= vr * db(-31) / np.sqrt(np.mean(dr ** 2))
    env = np.clip(t / 3, 0, 1) * np.clip((total - t) / 3, 0, 1)
    mix += (dr * env)[:, None] * [1.0, 0.92]
    # cold-open pad (Am - F - C - G), ~17 dB under voice, fades out over the title card
    pad = np.zeros(n)
    chords = [[110, 130.8, 164.8, 220], [87.3, 110, 130.8, 174.6], [130.8, 164.8, 196, 261.6], [98, 123.5, 146.8, 196]]
    end_pad = cold_end + 2.6
    seg = 7.5
    for ci in range(int(end_pad // seg) + 1):
        a, b = ci * seg, min((ci + 1) * seg + 1.5, end_pad + 1)
        idx = slice(int(a * SR), int(b * SR))
        tt = t[idx] - a
        e = np.clip(tt / 2.0, 0, 1) * np.clip((b - a - tt) / 1.5, 0, 1)
        for f in chords[ci % 4]:
            for det in (-0.6, 0.6):
                pad[idx] += e * np.sin(2 * np.pi * (f + det) * tt) * 0.5
            pad[idx] += e * 0.15 * np.sin(2 * np.pi * f * 2 * tt)
    m = t < end_pad
    pad *= vr * db(-17) / np.sqrt(np.mean(pad[m & (t > 1)] ** 2))
    pad *= np.clip((end_pad - t) / 2.5, 0, 1) * np.clip(t / 1.5, 0, 1)
    mix += pad[:, None] * [0.95, 1.0]
    vpk = np.abs(v).max()

    def place(sig, at, gain_db):
        i = int(at * SR)
        if i >= n:
            return
        sig = sig[:n - i] * vpk * db(gain_db) / np.abs(sig).max()
        mix[i:i + len(sig)] += sig[:, None]

    tp = np.arange(int(0.09 * SR)) / SR
    pop = (np.sin(2 * np.pi * 1150 * tp) + 0.4 * np.sin(2 * np.pi * 2300 * tp)) * np.exp(-tp * 55)
    tw = np.arange(int(1.0 * SR)) / SR
    wn = rng.normal(0, 1, len(tw))
    k = np.ones(60) / 60
    whoosh = (wn - np.convolve(wn, k, "same")) * np.sin(np.pi * tw / tw[-1]) ** 2
    whoosh = np.convolve(whoosh, np.ones(8) / 8, "same")
    tb = np.arange(int(2.6 * SR)) / SR
    boom = np.sin(2 * np.pi * (48 - 14 * tb) * tb) * np.exp(-tb * 1.8) + np.convolve(rng.normal(0, 1, len(tb)), np.ones(300) / 300, "same") * np.exp(-tb * 6) * 3
    for kind, at in sfx:
        place({"pop": pop, "whoosh": whoosh, "boom": boom}[kind], at, {"pop": -26, "whoosh": -16, "boom": -6}[kind])
    return mix


def main():
    ap = argparse.ArgumentParser()
    for a in ("shots", "timeline", "narration", "assets", "fonts", "out"):
        ap.add_argument(a)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated shot indices to render (preview)")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    shots, sfx, total, off = load_plan(a.shots, a.timeline)
    total_frames = round(total * FPS)
    shots[-1]["f1"] = total_frames
    print(f"{len(shots)} shots, {len(sfx)} sfx, {total:.1f}s")
    if a.check:
        for i, s in enumerate(shots):
            print(f"{i:3d} {s['t0']:7.2f}-{s['t1']:7.2f} {s['kind']:5s} {s.get('img') or s.get('gfx') or s.get('text')}")
        return
    work = os.path.splitext(a.out)[0] + "_work"
    os.makedirs(work, exist_ok=True)
    only = {int(x) for x in a.only.split(",") if x}
    jobs = [(i, s, work, total_frames) for i, s in enumerate(shots) if not only or i in only]
    with Pool(a.workers, initializer=init_worker, initargs=(a.assets, a.fonts)) as pool:
        for k, pth in enumerate(pool.imap_unordered(render_shot, sorted(jobs, key=lambda j: -(j[1]["f1"] - j[1]["f0"])))):
            print(f"  [{k + 1}/{len(jobs)}] {os.path.basename(pth)}", flush=True)
    if only:
        return
    import soundfile as sf
    cold_end = next(s["t0"] for s in shots if s["kind"] == "title")
    mix = synth_audio(a.narration, sfx, total, off, cold_end)
    wav = os.path.join(work, "mix.wav")
    sf.write(wav, np.clip(mix, -1, 1).astype(np.float32), SR)
    lst = os.path.join(work, "segs.txt")
    open(lst, "w").write("".join(f"file 'seg_{i:03d}.mp4'\n" for i in range(len(shots))))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.0:LRA=9",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", a.out], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
