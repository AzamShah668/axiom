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
    if name == "year_counter":
        year = 1933 + int(round(37 * ease(p * 1.15)))
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
        f = (starfield(t, dim=0.15) * 0 + G["rock"]).astype(np.uint8)
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
