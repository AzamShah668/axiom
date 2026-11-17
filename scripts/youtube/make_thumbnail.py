"""Three thumbnail drafts (1280x720) for a science-channel video, from the footage the video actually shows.

Only when the owner asks (his rule: no thumbnail unless asked). No pipeline stage calls this.

  python scripts/youtube/make_thumbnail.py productions/NN-slug [--out work/NN-slug/thumbs] [--thumbs thumbs.json]
         [--package productions/NN-slug/youtube.md] [--hires]

thumbs.json (default <production>/thumbs.json), one entry per variant; the variants differ in idea, not colour:
  [{"id": "A", "query": "magnetar flare blasting out", "lines": ["IT HIT EARTH", "*FROM 50,000 LY*"],
    "title": "The Scariest Places in the Universe | Hindi Documentary",
    "shot": null, "t": null, "focus": 0.68, "zoom": 1.12, "pos": "bottom", "ring": null, "void": null}, ...]
  lines   1-2 lines, 2-6 words, ALL CAPS, English/Roman only; *line* = the yellow keyword line
  title   the title it is paired with (default: the package's **Titles (A/B)** in order, else its **Title**)
  shot/t  pin a shot id (and a clip time in seconds); otherwise CLIP picks from the cutlist's shots
  focus   horizontal position of the subject in the source frame (0-1); it is moved to the right third
  zoom    punch-in, 1.0-1.5 (1.5 = 1:1 pixels from a 1080p proxy, so no blur at 1280x720)
  pos     text block at the "bottom" (default), "top" or "middle" of the left 62 %
  ring    [x, y, r] glow ring on the output (fractions of the frame, or pixels if > 1)
  void    [x, y, r] radial dark mask (an "empty region" illustration), same units

Frame pick: cutlist shots only (the thumbnail shows what the video shows), minus shots flagged in text_gate.json,
dup_of, or luma < 8; ranked by CLIP (query vs shots_emb.npz), 5 frames from the shown segment of each of the top 8,
frame score 0.5 CLIP + 0.2 sharpness + 0.2 colourfulness + 0.1 centre-weighted saliency. A shot used by an earlier
variant is skipped. --hires re-grabs the chosen frame from the 4K source URL (network; off by default).

Look: grade (contrast 1.18, saturation 1.35), vignette 0.35, +12 % exposure around the subject, a left shade (then
a soft dark halo behind the letters) that deepens until the text passes the contrast lint. Anton, white 110-130 px and yellow #FFD400 160-200 px (shrunk to
fit the left 62 %), 6 px black stroke and a blurred shadow, clear of the timestamp and hover-icon corners.

Lints (exit 1 if any variant fails): 1280x720; smallest cap height >= 9 % of the height; WCAG contrast >= 4.5:1
against the local background; text inside the left 62 % and outside the corners; 2-6 words, <= 2 lines, no
Devanagari; < 50 % of the text's words in any title; JPEG <= 2 MB (quality is lowered until it fits).

Output in --out: thumb_{A,B,C}.jpg, candidates_{A,B,C}.jpg (4x3 contact sheet: pin a frame with shot/t),
preview_grid.jpg (mock mobile feed: 360x202 cards with titles, and the 168x94 list size), thumbs.out.json (shot,
clip, time, source, credit line for the description).
"""
import argparse, json, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "footage"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
W, H = 1280, 720
TEXT_W = int(W * 0.62)                 # text lives in the left 62 %
MARGIN = 56
ZONES = [(W - 230, H - 90, W, H), (W - 120, 0, W, 120)]   # timestamp, hover icons
YELLOW, WHITE = (255, 212, 0), (255, 255, 255)
STOP = set("a an the of in on at to for and or is are was it its by from with as into this that".split())
CREDIT = {"eso": "ESO (CC BY 4.0)", "esahubble": "ESA/Hubble (CC BY 4.0)", "esawebb": "ESA/Webb (CC BY 4.0)",
          "svs": "NASA's Goddard Space Flight Center", "nasa": "NASA", "pexels": "Pexels"}


# ---------------------------------------------------------------- frame pick

def segments(cl):
    """shot id -> [(clip, ss, dur, crop)] of what the cutlist shows (clips and chapter-card backgrounds)."""
    seg = {}
    for it in cl["items"]:
        if it.get("kind") not in ("clip", "card") or not it.get("shot"):
            continue
        dur = (it["t1"] - it["t0"]) * it.get("speed", 1.0)
        seg.setdefault(it["shot"], []).append((it["clip"], float(it["ss"]), max(dur, 0.2), it.get("crop")))
    return seg


def eligible(seg, lib):
    shots = {s["id"]: s for s in json.load(open(os.path.join(lib, "shots.json")))}
    tg = os.path.join(lib, "text_gate.json")
    flagged = {k.split("@")[0] for k, v in (json.load(open(tg)).items() if os.path.exists(tg) else []) if v}
    out, why = [], {"not in library": 0, "text": 0, "dup": 0, "dark": 0}
    for sid in seg:
        s = shots.get(sid)
        if s is None:
            why["not in library"] += 1
        elif sid in flagged:
            why["text"] += 1
        elif s.get("dup_of"):
            why["dup"] += 1
        elif (s.get("luma") or 0) < 8:
            why["dark"] += 1
        else:
            out.append(sid)
    return out, why


def read_frame(path, t, crop=None):
    """One RGB frame at t seconds (ffmpeg input seek: much faster than an OpenCV seek on long-GOP proxies)."""
    import cv2
    cap = cv2.VideoCapture(path)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", path, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if not w or len(r.stdout) != w * h * 3:
        return None
    f = np.frombuffer(r.stdout, np.uint8).reshape(h, w, 3)
    if crop:
        h, w = f.shape[:2]
        x0, y0, x1, y1 = crop
        f = f[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    return f


def sharpness(g):
    import cv2
    return float(np.log1p(cv2.Laplacian(g, cv2.CV_32F).var()))


def colourfulness(f):
    """Hasler & Suesstrunk (2003)."""
    r, g, b = [f[..., i].astype(np.float32) for i in range(3)]
    rg, yb = r - g, 0.5 * (r + g) - b
    return float(np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean()))


def saliency(g):
    """Spectral-residual saliency (Hou & Zhang 2007), weighted toward the centre of the frame."""
    import cv2
    s = cv2.resize(g, (128, 72)).astype(np.float32)
    F = np.fft.fft2(s)
    la = np.log(np.abs(F) + 1e-6)
    sr = la - cv2.blur(la, (3, 3))
    m = np.abs(np.fft.ifft2(np.exp(sr + 1j * np.angle(F)))) ** 2
    m = cv2.GaussianBlur(m, (9, 9), 2.5)
    m /= m.max() + 1e-9
    yy, xx = np.mgrid[0:72, 0:128]
    wgt = np.exp(-(((xx - 64) / 40.0) ** 2 + ((yy - 36) / 24.0) ** 2))
    return float((m * wgt).sum() / wgt.sum())


def norm01(v):
    v = np.asarray(v, np.float32)
    return (v - v.min()) / (v.max() - v.min()) if v.max() > v.min() else np.ones_like(v)


def candidates(entry, seg, ok_ids, lib, used, emb, qvec, per_shot=5, top=8):
    """Scored frames for one variant: [{shot, clip, t, crop, frame, clip_sim, score, ...}], best first."""
    import cv2
    clips = os.path.join(lib, "clips")
    if entry.get("shot"):
        sid = entry["shot"]
        if sid not in seg:
            raise SystemExit(f"{entry['id']}: pinned shot {sid} is not in the cutlist")
        pool = [sid]
    else:
        ids = [s for s in ok_ids if s not in used and s in emb]
        sims = np.array([emb[s] @ qvec for s in ids])
        pool = [ids[i] for i in np.argsort(-sims)[:top]]
    frames = []
    for sid in pool:
        segs = seg[sid]
        if entry.get("shot") and entry.get("t") is not None:
            clip, _, _, crop = segs[0]
            times = [(clip, float(entry["t"]), crop)]
        else:
            times = []
            for k in range(per_shot):  # spread over the shown segments, away from the cut points
                clip, ss, dur, crop = segs[k % len(segs)]
                q = (k // len(segs) + 0.5) / max(1, -(-per_shot // len(segs)))
                times.append((clip, ss + 0.1 + (dur - 0.2) * q, crop))
        for clip, t, crop in times:
            f = read_frame(os.path.join(clips, clip + ".mp4"), t, crop)
            if f is None:
                continue
            g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
            if g.mean() < 8:
                continue
            frames.append({"shot": sid, "clip": clip, "t": round(t, 2), "crop": crop, "frame": f,
                           "sharp": sharpness(g), "colour": colourfulness(f), "sal": saliency(g)})
    if not frames:
        raise SystemExit(f"{entry['id']}: no usable frame")
    import clip_model
    fe = clip_model.embed_images([Image.fromarray(fr["frame"]) for fr in frames])
    cs = fe @ qvec
    score = (0.5 * norm01(cs) + 0.2 * norm01([f["sharp"] for f in frames]) +
             0.2 * norm01([f["colour"] for f in frames]) + 0.1 * norm01([f["sal"] for f in frames]))
    for f, c, s in zip(frames, cs, score):
        f["clip_sim"], f["score"] = round(float(c), 4), round(float(s), 4)
    return sorted(frames, key=lambda f: -f["score"])


def hires(frame, entry_src, t, crop, tmp):
    """Re-grab the frame from the 4K source (network). Falls back to the proxy frame on any failure."""
    url = entry_src.get("url")
    if not url:
        return frame, "proxy"
    out = os.path.join(tmp, "hires.png")
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{entry_src.get('ss', 0) + t:.3f}", "-i", url,
                        "-frames:v", "1", out], check=True, timeout=180)
        f = np.array(Image.open(out).convert("RGB"))
        if crop:
            h, w = f.shape[:2]
            f = f[int(crop[1] * h):int(crop[3] * h), int(crop[0] * w):int(crop[2] * w)]
        return f, "4k"
    except Exception as ex:  # noqa: BLE001
        print(f"  hires grab failed ({type(ex).__name__}); using the proxy frame")
        return frame, "proxy"


# ---------------------------------------------------------------- look

def units(v, ref):
    return v * ref if v <= 1 else v


def compose_bg(frame, entry):
    """Crop/punch-in, grade, subject lift, vignette, void. Returns float32 HxWx3 in 0-1 and the subject point."""
    zoom = float(np.clip(entry.get("zoom", 1.12), 1.0, 2.0))
    focus = float(entry.get("focus", 0.68))
    fh, fw = frame.shape[:2]
    cw = min(fw, fh * W / H) / zoom
    ch = cw * H / W
    x0 = float(np.clip(focus * fw - 0.70 * cw, 0, fw - cw))   # the subject goes to the right third
    y0 = (fh - ch) / 2
    im = Image.fromarray(frame).crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
    sx = (focus * fw - x0) / cw * W
    a = np.array(im, np.float32) / 255
    a = np.clip((a - 0.5) * 1.18 + 0.5, 0, 1) ** 0.95
    g = a.mean(2, keepdims=True)
    a = np.clip(g + (a - g) * 1.35, 0, 1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    lift = np.exp(-((xx - sx) ** 2 + (yy - H / 2) ** 2) / (2 * (0.22 * W) ** 2))
    a = np.clip(a * (1 + 0.12 * lift)[..., None], 0, 1)
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / np.sqrt(2)
    a *= (1 - 0.35 * r ** 2)[..., None]
    if entry.get("void"):
        vx, vy, vr = entry["void"]
        vx, vy, vr = units(vx, W), units(vy, H), units(vr, W)
        d = np.hypot(xx - vx, yy - vy) / vr
        a *= (1 - 0.92 * np.clip(1.15 - d, 0, 1) ** 1.2 / 1.15 ** 1.2)[..., None]
    return a, sx


def shade(a, strength, pos):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    s = np.clip(1 - xx / (W * 0.78), 0, 1) ** 1.2 * strength
    band = {"bottom": np.clip((yy - H * 0.30) / (H * 0.70), 0, 1), "top": np.clip(1 - yy / (H * 0.70), 0, 1),
            "middle": 1 - np.clip(np.abs(yy - H / 2) / (H * 0.5), 0, 1)}[pos]
    s = s * (0.55 + 0.45 * band)
    return a * (1 - np.clip(s, 0, 0.92))[..., None]


def anton(fonts, size):
    return ImageFont.truetype(os.path.join(fonts, "Anton.ttf"), size)


def layout(fonts, lines, pos):
    """[(text, colour, font, x, baseline, cap_h)] for 1-2 lines in the left 62 %."""
    spec = []
    for ln in lines:
        key = ln.startswith("*") and ln.endswith("*")
        txt = ln.strip("*").upper()
        size = 190 if key else 124
        while size > 40 and anton(fonts, size).getbbox(txt, stroke_width=6)[2] > TEXT_W - MARGIN - 10:
            size -= 2
        f = anton(fonts, size)
        b = f.getbbox("H")
        spec.append([txt, YELLOW if key else WHITE, f, b[3] - b[1], b[3]])
    gaps = [int(0.16 * s[3]) for s in spec]
    block = sum(s[3] for s in spec) + sum(gaps[1:])
    top = {"bottom": H - 64 - block, "top": 52, "middle": (H - block) // 2}[pos]
    out, y = [], top
    for k, (txt, col, f, cap, base_off) in enumerate(spec):
        if k:
            y += gaps[k]
        y += cap
        out.append((txt, col, f, MARGIN, y, cap))    # y = baseline
    return out


def text_masks(lay, stroke=6):
    glyph, outer = Image.new("L", (W, H), 0), Image.new("L", (W, H), 0)
    per = []
    for txt, col, f, x, base, cap in lay:
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).text((x, base), txt, font=f, fill=255, anchor="ls")
        per.append(np.array(m) > 127)
        glyph.paste(255, (0, 0), m)
        ImageDraw.Draw(outer).text((x, base), txt, font=f, fill=255, anchor="ls", stroke_width=stroke)
    return np.array(glyph) > 127, np.array(outer) > 0, per


def rel_lum(rgb):
    c = rgb / 255.0 if rgb.max() > 1 else rgb
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def contrast_per_line(bg, lay, outer, per):
    """WCAG ratio of each line's colour against the mean luminance of the background around its glyphs."""
    import cv2
    out = []
    L = rel_lum(bg)
    for (txt, col, f, x, base, cap), m in zip(lay, per):
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = max(0, xs.min() - 14), min(W, xs.max() + 14), max(0, ys.min() - 14), min(H, ys.max() + 14)
        region = np.zeros((H, W), bool)
        region[y0:y1, x0:x1] = True
        ring = region & ~cv2.dilate(outer.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        lb = float(L[ring].mean()) if ring.any() else float(L[region].mean())
        lt = float(rel_lum(np.array(col, np.float32)[None, None])[0, 0])
        out.append((max(lt, lb) + 0.05) / (min(lt, lb) + 0.05))
    return out


def backing(a, outer, k):
    """Darken a soft halo around the text (only when the left shade alone is not enough for the contrast lint)."""
    if k <= 0:
        return a
    m = Image.fromarray(outer.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(22))
    return a * (1 - k * np.array(m, np.float32)[..., None] / 255)


def draw_text(canvas, lay, stroke=6):
    sh = Image.new("L", (W, H), 0)
    ds = ImageDraw.Draw(sh)
    for txt, col, f, x, base, cap in lay:
        ds.text((x + 6, base + 8), txt, font=f, fill=210, anchor="ls", stroke_width=stroke)
    canvas.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(canvas)
    for txt, col, f, x, base, cap in lay:
        d.text((x, base), txt, font=f, fill=col, anchor="ls", stroke_width=stroke, stroke_fill=(0, 0, 0))


def draw_ring(canvas, ring):
    x, y, r = units(ring[0], W), units(ring[1], H), units(ring[2], W)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse((x - r, y - r, x + r, y + r), outline=YELLOW, width=14)
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    canvas.paste(Image.fromarray(np.clip(np.array(canvas, np.int16) + np.array(glow, np.int16), 0, 255).astype(np.uint8)))
    ImageDraw.Draw(canvas).ellipse((x - r, y - r, x + r, y + r), outline=YELLOW, width=6)


# ---------------------------------------------------------------- lints

def words(s):
    return [w for w in re.sub(r"[^a-z0-9 ]+", " ", s.lower().replace(",", "")).split() if w not in STOP]


def lint(entry, lay, outer, ratios, titles):
    fails, notes = [], []
    text = " ".join(t for t, *_ in lay)
    n = len(text.split())
    if not 2 <= n <= 6:
        fails.append(f"{n} words (2-6)")
    if len(lay) > 2:
        fails.append(f"{len(lay)} lines (<= 2)")
    if re.search(r"[ऀ-ॿ]", " ".join(entry.get("lines", []))):
        fails.append("Devanagari text (no font; use English or Roman)")
    cap = min(c for *_, c in lay)
    (notes if cap >= 0.09 * H else fails).append(f"cap height {cap} px ({cap / H * 100:.1f} % of the height, min 9 %)")
    for (t, *_), r in zip(lay, ratios):
        (notes if r >= 4.5 else fails).append(f"contrast {r:.1f}:1 for '{t}' (min 4.5)")
    ys, xs = np.nonzero(outer)
    if xs.max() > TEXT_W:
        fails.append(f"text reaches x={xs.max()} (left 62 % ends at {TEXT_W})")
    for zx0, zy0, zx1, zy1 in ZONES:
        if outer[zy0:zy1, zx0:zx1].any():
            fails.append(f"text in a reserved corner {zx0},{zy0}-{zx1},{zy1}")
    tw = set(words(text))
    for t in titles:
        ov = len(tw & set(words(t))) / max(1, len(tw))
        (notes if ov < 0.5 else fails).append(f"{ov * 100:.0f} % of the text's words in title '{t}' (< 50 %)")
    return fails, notes


def save_jpeg(canvas, path, limit=2 * 1024 * 1024):
    q = 92
    while True:
        canvas.save(path, quality=q, optimize=True)
        if os.path.getsize(path) <= limit or q <= 40:
            return q, os.path.getsize(path)
        q -= 4


# ---------------------------------------------------------------- sheets

def label_font(size, bold=True):
    for p in ("/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf",
              "/usr/share/fonts/truetype/roboto/Roboto-Medium.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def contact_sheet(vid, frames, path, cols=4, rows=3, tw=400):
    th = tw * 9 // 16
    sheet = Image.new("RGB", (cols * tw, rows * (th + 34)), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    f = label_font(15)
    for k, fr in enumerate(frames[:cols * rows]):
        x, y = (k % cols) * tw, (k // cols) * (th + 34)
        sheet.paste(Image.fromarray(fr["frame"]).resize((tw - 4, th - 4)), (x + 2, y + 2))
        d.text((x + 6, y + th + 2), f"{vid}{k + 1}  {fr['score']:.2f}  clip {fr['clip_sim']:.3f}", font=f, fill=(255, 212, 0))
        d.text((x + 6, y + th + 17), f"{fr['shot']} t={fr['t']}", font=f, fill=(220, 220, 220))
    sheet.save(path, quality=88)


def wrap(d, text, font, width, max_lines=2):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    if len(out) > max_lines:
        out = out[:max_lines]
        out[-1] = out[-1].rstrip() + "..."
    return out


def preview_grid(results, path):
    """Mock mobile feed: 360x202 cards with their titles, then the 168x94 list size with the title beside it."""
    pad, cw, chh = 24, 360, 202
    n = len(results)
    gw = pad + n * (cw + pad)
    gh = pad + chh + 60 + pad + 94 * n + pad * n + 30
    g = Image.new("RGB", (gw, gh), (15, 15, 15))
    d = ImageDraw.Draw(g)
    ft, fs = label_font(17), label_font(13, bold=False)
    for k, r in enumerate(results):
        im = Image.open(r["path"])
        x = pad + k * (cw + pad)
        g.paste(im.resize((cw, chh), Image.LANCZOS), (x, pad))
        for j, ln in enumerate(wrap(d, r["title"], ft, cw)):
            d.text((x, pad + chh + 8 + j * 22), ln, font=ft, fill=(241, 241, 241))
    y = pad + chh + 60 + pad
    d.text((pad, y - 22), "168x94 (search and suggested list)", font=fs, fill=(170, 170, 170))
    for k, r in enumerate(results):
        im = Image.open(r["path"])
        g.paste(im.resize((168, 94), Image.LANCZOS), (pad, y))
        for j, ln in enumerate(wrap(d, r["title"], ft, gw - 168 - 3 * pad)):
            d.text((pad + 168 + pad, y + 4 + j * 22), ln, font=ft, fill=(241, 241, 241))
        d.text((pad + 168 + pad, y + 54), f"{r['id']}: {' / '.join(r['lines'])}", font=fs, fill=(170, 170, 170))
        y += 94 + pad
    g.save(path, quality=90)


# ---------------------------------------------------------------- main

def package_titles(path):
    if not path or not os.path.exists(path):
        return []
    from upload_youtube import parse_titles
    s = open(path, encoding="utf-8").read()
    m = re.search(r"\*\*Title\*\*\s*\n(.+)", s)
    ab = parse_titles(s)
    return ab or ([m.group(1).strip()] if m else [])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prod", help="productions/NN-slug")
    ap.add_argument("--out", default="", help="default work/NN-slug/thumbs")
    ap.add_argument("--thumbs", default="", help="default <prod>/thumbs.json")
    ap.add_argument("--package", default="", help="default <prod>/youtube.md (titles for pairing and the overlap lint)")
    ap.add_argument("--cutlist", default="", help="default <prod>/cutlist.json, else work/NN-slug/cutlist.json")
    ap.add_argument("--lib", default=os.path.join(ROOT, "work", "library"))
    ap.add_argument("--fonts", default=os.environ.get("MEDIA", os.path.join(ROOT, "work", "media")) + "/fonts")
    ap.add_argument("--top", type=int, default=8, help="shots sampled per variant")
    ap.add_argument("--per-shot", type=int, default=5, help="frames sampled per shot")
    ap.add_argument("--hires", action="store_true", help="re-grab the chosen frames from the 4K source URLs (network)")
    a = ap.parse_args()
    prod = os.path.normpath(a.prod)
    slug = os.path.basename(prod)
    out = a.out or os.path.join(ROOT, "work", slug, "thumbs")
    os.makedirs(out, exist_ok=True)
    tj = a.thumbs or os.path.join(prod, "thumbs.json")
    if not os.path.exists(tj):
        raise SystemExit(f"no {tj}: write three entries first (see this script's docstring)")
    entries = json.load(open(tj, encoding="utf-8"))
    cpath = a.cutlist or next((p for p in (os.path.join(prod, "cutlist.json"), os.path.join(ROOT, "work", slug, "cutlist.json"))
                               if os.path.exists(p)), None)
    if not cpath:
        raise SystemExit("no cutlist.json")
    cl = json.load(open(cpath))
    titles = package_titles(a.package or os.path.join(prod, "youtube.md"))
    for k, e in enumerate(entries):
        e.setdefault("id", "ABC"[k] if k < 3 else str(k + 1))
        e.setdefault("title", titles[k] if k < len(titles) else (titles[0] if titles else ""))
    all_titles = sorted({e["title"] for e in entries if e["title"]} | set(titles))

    seg = segments(cl)
    ok_ids, why = eligible(seg, a.lib)
    print(f"{len(seg)} cutlist shots, {len(ok_ids)} eligible (dropped: " +
          ", ".join(f"{v} {k}" for k, v in why.items() if v) + ")")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")   # the CLIP weights are cached: no network call
    import clip_model
    E = np.load(os.path.join(a.lib, "shots_emb.npz"))
    emb = {str(i): v for i, v in zip(E["ids"], E["emb"]) if str(i) in seg}
    qv = clip_model.embed_texts([e.get("query") or " ".join(e["lines"]) for e in entries])
    sources = json.load(open(os.path.join(a.lib, "sources.json")))

    used, results, failed = set(), [], False
    for e, q in zip(entries, qv):
        vid = e["id"]
        frames = candidates(e, seg, ok_ids, a.lib, used, emb, q, a.per_shot, a.top)
        shown, per = [], {}
        for fr in frames:  # at most 3 frames per shot on the sheet, so more shots are on offer
            per[fr["shot"]] = per.get(fr["shot"], 0) + 1
            if per[fr["shot"]] <= 3:
                shown.append(fr)
        contact_sheet(vid, shown, os.path.join(out, f"candidates_{vid}.jpg"))
        best = frames[0]
        used.add(best["shot"])
        src = sources.get(best["clip"], {})
        frame, res = (hires(best["frame"], src, best["t"], best["crop"], out) if a.hires else (best["frame"], "proxy"))
        base, sx = compose_bg(frame, e)
        pos = e.get("pos", "bottom")
        lay = layout(a.fonts, e["lines"], pos)
        glyph, outer, per = text_masks(lay)
        for strength, halo in ((0.55, 0), (0.65, 0), (0.75, 0.25), (0.85, 0.45), (0.92, 0.65), (0.92, 0.85)):
            bg = backing(shade(base, strength, pos), outer, halo)   # deepen the shade until the text reads
            ratios = contrast_per_line(bg * 255, lay, outer, per)
            if min(ratios) >= 4.5:
                break
        canvas = Image.fromarray((bg * 255).astype(np.uint8))
        if e.get("ring"):
            draw_ring(canvas, e["ring"])
        draw_text(canvas, lay)
        fails, notes = lint(e, lay, outer, ratios, all_titles)
        path = os.path.join(out, f"thumb_{vid}.jpg")
        qual, size = save_jpeg(canvas, path)
        chk = Image.open(path)
        if chk.size != (W, H):
            fails.append(f"size {chk.size}")
        (notes if size <= 2 * 1024 * 1024 else fails).append(f"{size / 1024:.0f} KB at quality {qual} (<= 2 MB)")
        failed |= bool(fails)
        print(f"{vid}: {best['shot']} t={best['t']} score {best['score']:.2f} -> {path}  "
              f"{'FAIL ' + '; '.join(fails) if fails else 'lints pass'}")
        for n_ in notes:
            print("   ok  ", n_)
        results.append({"id": vid, "path": path, "title": e["title"], "lines": e["lines"], "query": e.get("query", ""),
                        "shot": best["shot"], "clip": best["clip"], "t": best["t"], "frame_from": res,
                        "score": best["score"], "clip_sim": best["clip_sim"], "shade": strength, "halo": halo,
                        "source": {k: src.get(k) for k in ("source", "page", "title")},
                        "credit": CREDIT.get(src.get("source"), src.get("source", "")),
                        "jpeg_kb": round(size / 1024), "quality": qual, "fails": fails, "checks": notes})
    preview_grid(results, os.path.join(out, "preview_grid.jpg"))
    cc = sorted({r["credit"] for r in results if r["credit"]})
    meta = {"production": slug, "cutlist": os.path.relpath(cpath, ROOT), "variants": results,
            "credit_line": "Thumbnail images: " + "; ".join(cc) if cc else ""}
    for r in results:
        r["path"] = os.path.basename(r["path"])
    json.dump(meta, open(os.path.join(out, "thumbs.out.json"), "w"), indent=1, ensure_ascii=False)
    print("wrote", os.path.join(out, "preview_grid.jpg"), "and thumbs.out.json;", meta["credit_line"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
