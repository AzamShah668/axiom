"""Shorts, v2 style (owner, 2026-11-16: "change the editing style completely ... attractive, beats, a new picture every
2-3 s, text on screen, motion graphics; at least 100k views"). Full-screen 9:16 instead of the square between bars.

  python render_short_v2.py <short.json> <cutlist.json> <voice_dir> <captions.hinglish.md> <lib_dir> <media_dir> <out.mp4>

short.json (next to the Short's edit.spec):
  {"title": "100 MILLION BLACK HOLES / *YOU CAN'T SEE*",   top title (English, *gold*), on screen until the end card
   "music": "Darkest_Child.mp3", "music_start": 32.0, "music_gain": 4.0,
   "suspense_after": "hunter_problem", "suspense_text": "BUT...",   a designed silence (freeze, heartbeat, text)
   "cta_at": "पूरी कहानी",            the end card starts on this word of the last section ("WATCH THE FULL VIDEO", arrow)
   "stills": {"darkflow_end/0": "photos/Planck_sat.jpg"},   items shown as a moving still (media/assets/...)
   "speed": 1.2}

Picture: every item of the plan (assign_shots.py over the Short's own edit.spec) fetched again from its 4K source as a
9:16 window around the subject (render_short.vclip), with a push-in or pull-out and a zoom punch on every cut; items
longer than 2.7 s get a jump-zoom in the middle (a new frame every 2-3 s). Cuts snap to the music's beats (<= 0.12 s).
Transitions: punch on every cut, a flash every third cut, a glitch at each new section, a light leak sweep.
Grade: teal-orange curve, vignette, grain. Text: the title on top, one burned-in Hinglish caption word at a time
(gold, popping), headlines that slam in (K lines), count-up numbers (N lines), the suspense text, the end card, a
progress bar. Sound: the voice at 1.2x (rubberband, pitch kept), a beat-driven Kevin MacLeod bed that drops out for
the suspense, the owner's five SFX (bass_impact on the hook and slams, swish_big on glitches, camera_flash on flashes,
typing on the title, bell on the end card) plus whooshes on cuts and a riser into the twist.
"""
import argparse, json, math, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mograph as mg  # noqa: E402
import sfx as fx  # noqa: E402
import render_short as rs  # noqa: E402
import render_v3 as r3  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 44100
SW, SH = 1188, 2112          # fetched footage: 10% larger than the frame, room for camera moves
GAP, SUS, END_HOLD = 0.12, 1.35, 2.4


# ------------------------------------------------------------------ helpers
def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def ease_back(p, s=1.7):
    p = min(max(p, 0.0), 1.0) - 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def stroke_layer(text, size, font="Montserrat", weight="ExtraBold", grad=mg.GOLD, stroke=0.09, glow=None):
    """Text with a black outline (Shorts captions), uint8 BGRA, anchor = centre."""
    f = mg._font(font, size, weight)
    sw = max(2, int(size * stroke))
    b = f.getbbox(text, stroke_width=sw)
    pad = sw + int(size * 0.25)
    tw, th = b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad
    fill, outl = Image.new("L", (tw, th), 0), Image.new("L", (tw, th), 0)
    xy = (pad - b[0], pad - b[1])
    ImageDraw.Draw(outl).text(xy, text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    ImageDraw.Draw(fill).text(xy, text, font=f, fill=255)
    m, o = np.array(fill, np.float32) / 255, np.array(outl, np.float32) / 255
    rows = np.where(m.max(1) > 0)[0]
    y0, y1 = (rows[0], rows[-1]) if len(rows) else (0, th - 1)
    k = np.clip((np.arange(th) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    top, bot = np.array(grad[0], np.float32)[::-1], np.array(grad[1], np.float32)[::-1]
    col = (top + (bot - top) * k) * m[..., None]
    a = np.clip(o, 0, 1)
    sh = cv2.GaussianBlur(np.roll(a, (int(size * 0.05), int(size * 0.03)), (0, 1)), (0, 0), size * 0.04) * 0.6
    if glow:
        g = cv2.GaussianBlur(m, (0, 0), size * 0.18) * glow[1]
        col = col + np.array(glow[0], np.float32)[::-1] * (g * (1 - a))[..., None]
        a = np.clip(a + g, 0, 1)
    a = np.clip(a + sh * (1 - a), 0, 1)
    return np.dstack([np.clip(col / np.maximum(a[..., None], 1e-4), 0, 255), a * 255]).astype(np.uint8)


def fit(lay, maxw):
    return min(1.0, maxw / max(1, lay.shape[1]))


def words_of(text):
    """'NO SOUND' or '*GOLD WORDS*' -> (text, gold)."""
    gold = text.startswith("*")
    return text.strip("*").strip(), gold


def fmt_value(v, spec):
    if "." in spec:
        return f"{v:.1f}"
    return f"{int(round(v)):,}" if "," in spec else str(int(round(v)))


# ------------------------------------------------------------------ timing
class Clock:
    """Narration time (1.0x, per section) -> Short time (speed x, sections joined with short gaps)."""
    def __init__(self, tl, cfg, voice_wav, work):
        self.k = cfg.get("speed", 1.2)
        self.secs = tl["sections"]
        v = r3._load(voice_wav, 1)
        parts, self.out0, self.out1, cur = [], {}, {}, 0.0
        for i, s in enumerate(self.secs):
            seg = v[int(s["start"] * SR):int(s["end"] * SR)]
            raw, st = os.path.join(work, f"v_{i}.wav"), os.path.join(work, f"v_{i}_st.wav")
            import soundfile as sf
            sf.write(raw, seg.astype(np.float32), SR)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"rubberband=tempo={self.k}:pitchq=quality",
                            "-ar", str(SR), "-ac", "1", st], check=True)
            y, _ = sf.read(st)
            self.out0[s["id"]] = cur
            self.out1[s["id"]] = cur + len(y) / SR
            parts.append((cur, y))
            cur += len(y) / SR
            last = i == len(self.secs) - 1
            cur += END_HOLD if last else (SUS if s["id"] == cfg.get("suspense_after") else GAP)
        self.total = cur
        self.voice = np.zeros(int(cur * SR) + SR)
        for t, y in parts:
            i = int(t * SR)
            self.voice[i:i + len(y)] += y

    def sec_of(self, t):
        for s, nxt in zip(self.secs, self.secs[1:] + [None]):
            if nxt is None or t < nxt["start"] - 1e-6:
                return s
        return self.secs[-1]

    def __call__(self, t, sec=None):
        s = next(x for x in self.secs if x["id"] == sec) if sec else self.sec_of(t)
        return min(self.out0[s["id"]] + max(0.0, t - s["start"]) / self.k, self.out1[s["id"]] + (0.0 if sec else 0.4))


def caption_words(path, tl, clock):
    secs, cur = {}, None
    for ln in open(path, encoding="utf-8"):
        if ln.startswith("## "):
            cur = secs.setdefault(ln[3:].strip(), [])
        elif cur is not None and not ln.startswith("#"):
            cur += rs.roman_tokens(ln)
    out = []
    for s in tl["sections"]:
        if s["id"] in secs:
            for t, x, brk in rs.match_words(s["id"], rs.spoken_words(s["chars"], s["char_start"]), secs[s["id"]]):
                out.append((clock(t, s["id"]), x, brk, s["id"]))
    return out


def word_time(tl, clock, sec_id, word):
    s = next(x for x in tl["sections"] if x["id"] == sec_id)
    for t, w in rs.spoken_words(s["chars"], s["char_start"]):
        if w.strip("।,?!.") == word or w.startswith(word):
            return clock(t, sec_id)
    raise SystemExit(f"cta_at: '{word}' not spoken in {sec_id}")


def beats(music, start, total):
    import librosa
    y, sr = librosa.load(music, sr=22050, offset=start, duration=total + 1)
    _, b = librosa.beat.beat_track(y=y, sr=sr)
    return librosa.frames_to_time(b, sr=sr)


# ------------------------------------------------------------------ plan
def build(P, tl, clock, cfg, beat_t, cap_words, cta0):
    items = [dict(it) for it in P["items"]]
    starts = []
    for i, it in enumerate(items):
        first_of_sec = i == 0 or items[i - 1]["sec"] != it["sec"]
        a = 0.0 if i == 0 else (clock.out0[it["sec"]] if first_of_sec else clock(it["t0"], it["sec"]))
        if i and not first_of_sec and len(beat_t):  # a cut inside a section snaps to the nearest beat
            b = beat_t[np.argmin(np.abs(beat_t - a))]
            if abs(b - a) <= 0.12:
                a = float(b)
        starts.append(a)
    sus = None
    if cfg.get("suspense_after"):
        sid = cfg["suspense_after"]
        sus = (clock.out1[sid], clock.out1[sid] + SUS)
    for i, it in enumerate(items):
        it["a"] = starts[i]
        nxt = starts[i + 1] if i + 1 < len(items) else clock.total
        if sus and it["sec"] == cfg["suspense_after"] and (i + 1 == len(items) or items[i + 1]["sec"] != it["sec"]):
            nxt = sus[0]
        it["b"] = nxt
        it["first_of_sec"] = i == 0 or items[i - 1]["sec"] != it["sec"]
        it["move"] = "in" if i % 2 == 0 else "out"
        it["drift"] = (-1) ** (i // 2) * 22
        d = it["b"] - it["a"]
        it["jumps"] = [it["a"] + d / 2] if d > 2.7 else []
        if i == 0 and d > 1.8:  # the opening changes picture within 1.5 s (owner's first-2-seconds rule)
            it["jumps"] = [min(1.4, d / 2)] + ([it["a"] + d * 0.75] if d > 3.6 else [])
        it["trans"] = "none" if i == 0 else "glitch" if it["first_of_sec"] else "flash" if i % 3 == 2 else "punch"
    # overlays on the Short's clock
    heads, nums = [], []
    for o in P["ovl"]:
        if o["kind"] == "headline":
            ls = [(clock(x["t"]),) + words_of(x["text"]) for x in o["lines"]]
            heads.append({"lines": ls, "t0": ls[0][0], "t1": min(clock(o["t1"]), ls[-1][0] + 1.8)})
        elif o["kind"] == "num":
            n = o["num"]
            t0, land = clock(o["t0"]), clock(n["land_t"])
            nums.append({"t0": t0, "land": max(land, t0 + 0.5), "t1": max(land, t0 + 0.5) + 1.3, "value": n["value"],
                         "unit": n.get("unit", ""), "kicker": n.get("kicker", "")})
    return items, heads, nums, sus


# ------------------------------------------------------------------ footage
def fetch(items, lib, out_dir, cfg, media):
    sources = json.load(open(os.path.join(lib, "sources.json")))
    rs.SW, rs.SH, rs.FPS = SW, SH, FPS
    os.makedirs(out_dir, exist_ok=True)
    jobs = []
    for it in items:
        if it.get("ref") in cfg.get("stills", {}):
            it["still"] = os.path.join(media, "assets", cfg["stills"][it["ref"]])
            continue
        need = it["b"] - it["a"] + 0.3
        clip_path = os.path.join(lib, "clips", it["clip"] + ".mp4")
        cap = cv2.VideoCapture(clip_path)
        avail = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(1, cap.get(cv2.CAP_PROP_FPS)) - it["ss"] - 0.05
        cap.release()
        dur = max(0.5, min(need, avail))
        it["rate"] = min(1.0, dur / need)
        crop = tuple(it["crop"]) if it.get("crop") else (0.0, 0.0, 1.0, 1.0)
        cx = rs.subject_x(clip_path, it["ss"], dur, crop)
        key = f"{it['shot'].replace('#', '_')}_{it['ss']:.2f}_{dur:.2f}_{cx:.2f}"
        it["vclip"] = os.path.join(out_dir, key + ".mp4")
        jobs.append((it["vclip"], sources[it["clip"]], clip_path, it["ss"], dur, crop, cx))
    with ThreadPoolExecutor(3) as ex:
        for out, how in ex.map(rs.vclip, jobs):
            if how != "have":
                print(f"  {os.path.basename(out)}: {how}", flush=True)


class Reader:
    def __init__(self, it):
        self.it, self.cap, self.idx, self.last = it, None, -1, None
        if it.get("still"):
            im = cv2.imread(it["still"])
            if im is None:
                raise SystemExit(f"still not found: {it['still']}")
            s = max(SW / im.shape[1], SH / im.shape[0])
            im = cv2.resize(im, (int(im.shape[1] * s + 0.5), int(im.shape[0] * s + 0.5)), interpolation=cv2.INTER_AREA)
            y0, x0 = (im.shape[0] - SH) // 2, (im.shape[1] - SW) // 2
            self.last = im[y0:y0 + SH, x0:x0 + SW].copy()
        else:
            self.cap = cv2.VideoCapture(it["vclip"])

    def frame(self, u):
        if self.cap is None:
            return self.last
        want = int(u * self.it.get("rate", 1.0) * FPS)
        while self.idx < want:
            ok, f = self.cap.read()
            if not ok:
                break
            self.idx += 1
            self.last = f
        return self.last


# ------------------------------------------------------------------ look
def make_look():
    x = np.arange(256, dtype=np.float32) / 255
    s = x + 0.22 * (x - 0.5) * (1 - np.abs(2 * x - 1))  # S-curve
    lut_b = np.clip((s + 0.05 * (1 - x) ** 2) * 255, 0, 255).astype(np.uint8)   # teal shadows
    lut_g = np.clip((s + 0.015 * (1 - x) ** 2) * 255, 0, 255).astype(np.uint8)
    lut_r = np.clip((s + 0.06 * x ** 2 - 0.02 * (1 - x) ** 2) * 255, 0, 255).astype(np.uint8)  # warm highlights
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.62)) ** 2)
    vig = np.clip(1 - 0.42 * np.clip(r - 0.35, 0, 1) ** 1.6, 0, 1)[..., None].astype(np.float32)
    rng = np.random.default_rng(7)
    grain = [rng.normal(0, 4.0, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
    grain = [cv2.resize(g, (W, H))[..., None] for g in grain]
    leak = np.zeros((H, W * 2, 3), np.float32)
    for cx, cy, rad, col in ((W * 0.6, H * 0.35, W * 0.55, (40, 140, 255)), (W * 1.3, H * 0.65, W * 0.5, (255, 190, 90))):
        g = np.exp(-(((np.mgrid[0:H, 0:W * 2][1] - cx) ** 2 + (np.mgrid[0:H, 0:W * 2][0] - cy) ** 2) / (2 * rad ** 2)))
        leak += g[..., None] * np.array(col, np.float32)
    return {"lut": (lut_b, lut_g, lut_r), "vig": vig, "grain": grain, "leak": leak}


def grade(fr, look, fi, sat=1.12):
    b, g, r = cv2.split(fr)
    fr = cv2.merge([cv2.LUT(b, look["lut"][0]), cv2.LUT(g, look["lut"][1]), cv2.LUT(r, look["lut"][2])])
    f = fr.astype(np.float32)
    gray = f.mean(2, keepdims=True)
    f = gray + (f - gray) * sat
    f = f * look["vig"] + look["grain"][fi % 6]
    return f


def camera(src, z, dx, dy, blur=0.0):
    sc = (W / SW) * z
    M = np.array([[sc, 0, W / 2 - sc * SW / 2 + dx], [0, sc, H / 2 - sc * SH / 2 + dy]], np.float32)
    out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if blur > 0.5:
        k = int(blur) * 2 + 1
        out = cv2.blur(out, (1, k))
    return out


def glitch(f, amt, seed):
    rng = np.random.default_rng(seed)
    out = f.copy()
    sh = int(26 * amt)
    out[..., 2] = np.roll(f[..., 2], sh, 1)
    out[..., 0] = np.roll(f[..., 0], -sh, 1)
    for _ in range(int(7 * amt) + 1):
        y0 = int(rng.integers(0, H - 80))
        h = int(rng.integers(20, 120))
        out[y0:y0 + h] = np.roll(out[y0:y0 + h], int(rng.integers(-90, 90) * amt), 1)
    return out


def paste(f, lay, cx, cy, op=1.0, scale=1.0):
    """Alpha-blend a BGRA layer onto a float frame."""
    if op <= 0.01 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        lay = cv2.resize(lay, (max(1, int(lay.shape[1] * scale)), max(1, int(lay.shape[0] * scale))), interpolation=cv2.INTER_LINEAR)
    h, w = lay.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    L = lay[ya - y0:yb - y0, xa - x0:xb - x0].astype(np.float32)
    a = L[..., 3:4] / 255 * op
    f[ya:yb, xa:xb] = f[ya:yb, xa:xb] * (1 - a) + L[..., :3] * a


# ------------------------------------------------------------------ text
class Text:
    def __init__(self, cfg, cap_words, heads, nums):
        self.cache = {}
        self.cfg = cfg
        self.title = self.title_layer(cfg["title"])
        self.caps = cap_words
        self.heads, self.nums = heads, nums
        self.arrow = self.arrow_layer()
        self.band = (1 - 0.55 * np.clip(1 - np.arange(520) / 520, 0, 1) ** 1.5)[:, None, None].astype(np.float32)

    def get(self, key, fn):
        if key not in self.cache:
            self.cache[key] = fn()
        return self.cache[key]

    def title_layer(self, text):
        lines = [[words_of(w) for w in re.findall(r"\*[^*]+\*|[^*\s][^*]*?(?=\s*\*|$)", ln.strip())] for ln in text.split(" / ")]
        lays = []
        for ln in lines:
            parts = [stroke_layer(t, 84, "Anton", None, mg.GOLD if g else mg.SILVER, 0.07) for t, g in ln if t]
            hh = max(p.shape[0] for p in parts)
            row = np.zeros((hh, sum(p.shape[1] for p in parts) - 30 * (len(parts) - 1), 4), np.uint8)
            x = 0
            for p in parts:
                y = (hh - p.shape[0]) // 2
                sub = row[y:y + p.shape[0], x:x + p.shape[1]]
                a = p[..., 3:4].astype(np.float32) / 255
                sub[..., :3] = (sub[..., :3] * (1 - a) + p[..., :3] * a).astype(np.uint8)
                sub[..., 3] = np.maximum(sub[..., 3], p[..., 3])
                x += p.shape[1] - 30
            lays.append(row)
        wmax = max(l_.shape[1] for l_ in lays)
        hsum = sum(l_.shape[0] for l_ in lays) - 40 * (len(lays) - 1)
        box = np.zeros((hsum + 30, wmax + 40, 4), np.uint8)
        y = 15
        for l_ in lays:
            x = (box.shape[1] - l_.shape[1]) // 2
            sub = box[y:y + l_.shape[0], x:x + l_.shape[1]]
            a = l_[..., 3:4].astype(np.float32) / 255
            sub[..., :3] = (sub[..., :3] * (1 - a) + l_[..., :3] * a).astype(np.uint8)
            sub[..., 3] = np.maximum(sub[..., 3], l_[..., 3])
            y += l_.shape[0] - 40
        s = fit(box, W - 80)
        return cv2.resize(box, (int(box.shape[1] * s), int(box.shape[0] * s)), interpolation=cv2.INTER_AREA) if s < 1 else box

    def arrow_layer(self):
        a = np.zeros((170, 140), np.uint8)
        pts = np.array([[70, 160], [10, 90], [45, 90], [45, 10], [95, 10], [95, 90], [130, 90]], np.int32)
        cv2.fillPoly(a, [pts], 255, cv2.LINE_AA)
        col = np.zeros((170, 140, 3), np.uint8)
        col[:] = (40, 190, 255)
        return np.dstack([col, a])

    def draw(self, f, t, total, cta0, sus, busy_cap):
        # progress bar
        f[0:10, :] *= 0.35
        f[0:10, :int(W * min(1, t / total))] = np.array((40, 190, 255), np.float32)
        hidden = t >= cta0
        # title on top (the Shorts icons sit above ~200 px)
        if not hidden:
            f[:520] *= self.band
            p = ease_back(t / 0.28)
            paste(f, self.title, W / 2, 285, op=min(1, t / 0.1 + 0.4), scale=0.85 + 0.15 * p)
        # number cards
        shown = False
        for n in self.nums:
            if n["t0"] <= t < n["t1"] + 0.15:
                shown = True
                p = min(1, (t - n["t0"]) / max(0.05, n["land"] - n["t0"]))
                val = mg.parse_num(n["value"]) * ease_out(p)
                txt = fmt_value(val, n["value"])
                op = min(1, (t - n["t0"]) / 0.12) * (1 - max(0, (t - n["t1"]) / 0.15))
                f *= 1 - 0.38 * op
                bounce = 1 + 0.22 * max(0, 1 - (t - n["land"]) / 0.18) if t >= n["land"] else 1.0
                lay = self.get(("num", txt), lambda: stroke_layer(txt, 250, "Anton", None, mg.GOLD, 0.05, ((255, 140, 40), 0.55)))
                paste(f, lay, W / 2, H * 0.44, op, fit(lay, W - 70) * bounce)
                if n["kicker"]:
                    k = self.get(("k", n["kicker"]), lambda: stroke_layer(n["kicker"].upper(), 50, "Montserrat", "Bold", mg.SILVER, 0.08))
                    paste(f, k, W / 2, H * 0.44 - 185, op, fit(k, W - 80))
                if n["unit"]:
                    u = self.get(("u", n["unit"]), lambda: stroke_layer(n["unit"].upper(), 64, "Montserrat", "ExtraBold", mg.SILVER, 0.08))
                    paste(f, u, W / 2, H * 0.44 + 175, op, fit(u, W - 80))
        # headline slams
        for hd in self.heads:
            if hd["t0"] <= t < hd["t1"] + 0.15 and not shown:
                shown = True
                out = max(0, (t - hd["t1"]) / 0.15)
                f *= 1 - 0.3 * (1 - out)
                n = len(hd["lines"])
                for j, (tl_, txt, gold) in enumerate(hd["lines"]):
                    if t < tl_:
                        continue
                    p = (t - tl_) / 0.16
                    lay = self.get(("h", txt, gold), lambda: stroke_layer(
                        txt, 150 if gold else 120, "Anton", None, mg.GOLD if gold else mg.SILVER, 0.06,
                        ((255, 140, 40), 0.5) if gold else None))
                    sc = fit(lay, W - 80) * (2.1 - 1.1 * ease_out(p))
                    paste(f, lay, W / 2, H * 0.42 + (j - (n - 1) / 2) * 165, min(1, p * 1.6) * (1 - out), sc)
        # suspense text
        if sus and sus[0] + 0.12 <= t < sus[1]:
            shown = True
            p = (t - sus[0] - 0.12) / 0.2
            lay = self.get(("s",), lambda: stroke_layer(self.cfg.get("suspense_text", "?"), 170, "Anton", None, mg.GOLD, 0.06,
                                                      ((255, 140, 40), 0.6)))
            paste(f, lay, W / 2, H * 0.45, min(1, p * 2), fit(lay, W - 80) * (1.6 - 0.6 * ease_out(p)) * (1 + 0.03 * (t - sus[0])))
        # end card
        if t >= cta0:
            shown = True
            p = t - cta0
            f *= 1 - 0.5 * min(1, p / 0.2)
            a = self.get(("c1",), lambda: stroke_layer("WATCH THE", 120, "Anton", None, mg.SILVER, 0.06))
            b = self.get(("c2",), lambda: stroke_layer("FULL VIDEO", 190, "Anton", None, mg.GOLD, 0.05, ((255, 140, 40), 0.6)))
            paste(f, a, W / 2, H * 0.36, min(1, p / 0.15), fit(a, W - 80) * (1.8 - 0.8 * ease_out(p / 0.18)))
            q = p - 0.18
            if q > 0:
                paste(f, b, W / 2, H * 0.36 + 175, min(1, q / 0.12), fit(b, W - 70) * (2.0 - 1.0 * ease_out(q / 0.18)))
            r = p - 0.45
            if r > 0:
                bob = 26 * abs(math.sin(r * 5.0))
                paste(f, self.arrow, W / 2, H * 0.62 + bob, min(1, r / 0.15))
        # captions: one word at a time, gold, popping (hidden while other text is up)
        if not shown and not busy_cap:
            for i, (tw, txt, brk, sid) in enumerate(self.caps):
                nxt = self.caps[i + 1][0] if i + 1 < len(self.caps) else tw + 0.8
                if tw - 0.03 <= t < min(nxt - 0.03, tw + 0.9):
                    lay = self.get(("w", txt), lambda: stroke_layer(txt.upper(), 112, "Montserrat", "Black", mg.GOLD, 0.1))
                    p = (t - tw + 0.03) / 0.1
                    paste(f, lay, W / 2, H * 0.69, 1.0, fit(lay, W - 90) * (1.3 - 0.3 * ease_back(p)))
                    break


# ------------------------------------------------------------------ render
def render(a):
    cfg = json.load(open(a.short))
    P = json.load(open(a.cutlist))
    tl = json.load(open(os.path.join(a.voice, "timeline.json")))
    out_dir = os.path.splitext(a.out)[0] + "_work"
    os.makedirs(out_dir, exist_ok=True)
    mg.set_fonts(os.path.join(a.media, "fonts"))
    clock = Clock(tl, cfg, os.path.join(a.voice, "narration.wav"), out_dir)
    total = clock.total
    music = os.path.join(a.media, "music", cfg["music"])
    beat_t = beats(music, cfg.get("music_start", 0.0), total)
    cap_words = caption_words(a.captions, tl, clock)
    last = tl["sections"][-1]["id"]
    cta0 = word_time(tl, clock, last, cfg["cta_at"]) - 0.05
    items, heads, nums, sus = build(P, tl, clock, cfg, beat_t, cap_words, cta0)
    print(f"{len(items)} items, {len(heads)} headlines, {len(nums)} numbers, {total:.1f}s, cuts/min "
          f"{60 * sum(1 + len(i['jumps']) for i in items) / total:.0f}", flush=True)
    fetch(items, a.lib, os.path.join(os.path.dirname(a.out), "vclips9x16"), cfg, a.media)
    look = make_look()
    text = Text(cfg, cap_words, heads, nums)
    # impacts (camera shake) and sound events
    impacts, ev = [0.0], [["bass_impact", 0.0, 0], ["typing", 0.02, 0, {"d": 0.45}]]
    for i, it in enumerate(items[1:], 1):
        ev.append({"glitch": ["swish_big", it["a"] - 0.12, -2], "flash": ["camera_flash", it["a"] - 0.02, -2]}.get(
            it["trans"], ["whoosh", it["a"] - 0.18, -3, {"d": 0.4}]))
        for j in it["jumps"]:
            ev.append(["whoosh", j - 0.12, -6, {"d": 0.3}])
    for hd in heads:
        for tl_, txt, gold in hd["lines"]:
            ev.append(["bass_impact" if gold else "hit", tl_, -1 if gold else 0])
            impacts.append(tl_)
    for n in nums:
        ev.append(["roll", n["t0"], -2, {"d": max(0.4, n["land"] - n["t0"])}])
        ev.append(["bass_impact", n["land"], 0])
        impacts.append(n["land"])
    mus = []
    if sus:
        ev += [["sub_drop", sus[0], 0], ["riser", sus[1] - 1.0, 0, {"d": 1.0}], ["impact", sus[1], 0]]
        impacts += [sus[0] + 0.05, sus[0] + 0.55, sus[1]]
        mus.append({"kind": "drop", "t0": sus[0], "t1": sus[1]})
    ev += [["bell", cta0 + 0.2, 0], ["bass_impact", cta0, -2]]
    impacts.append(cta0)
    for it in items:
        if it["first_of_sec"] and it["a"] > 0:
            impacts.append(it["a"])
    # frames
    vid = os.path.join(out_dir, "video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", vid],
                          stdin=subprocess.PIPE)
    readers, frozen = {}, None
    nF = int(round(total * FPS))
    rng = np.random.default_rng(3)
    for fi in range(nF):
        t = fi / FPS
        in_sus = sus and sus[0] <= t < sus[1]
        k = max(i for i, it in enumerate(items) if it["a"] <= t + 1e-6) if not in_sus else None
        if in_sus:
            src = frozen
            u = t - sus[0]
            z = 1.0 + 0.12 * ease_out(u / SUS) + 0.05 * sum(math.exp(-((t - x) / 0.06) ** 2) for x in (sus[0] + 0.05, sus[0] + 0.55))
            fr = camera(src, z * 1.1, 0, 0)
            fr = grade(fr, look, fi, sat=0.25) * 0.5
        else:
            it = items[k]
            if k not in readers:
                readers = {k: Reader(it)}
            u = t - it["a"]
            src = readers[k].frame(u)
            frozen = src
            D = max(0.1, it["b"] - it["a"])
            z = 1.0 + 0.08 * (u / D) if it["move"] == "in" else 1.08 - 0.08 * (u / D)
            dx = it["drift"] * (u / D - 0.5)
            punch = 0.0 if it["trans"] == "none" and k == 0 and u > 0.3 else 0.16 * (1 - ease_out(u / 0.24))
            if k == 0:
                punch = 0.12 * (1 - ease_out(u / 0.35))
            for j in it["jumps"]:
                if t >= j:
                    z *= 1.18
                    punch = 0.12 * (1 - ease_out((t - j) / 0.2))
            z *= 1 + punch
            blur = 18 * max(0, 1 - u / 0.1) if it["trans"] in ("punch", "glitch") and k else 0.0
            fr = grade(camera(src, z, dx, 0, blur), look, fi)
        # shake
        amp = sum(18 * math.exp(-(t - x) / 0.11) for x in impacts if 0 <= t - x < 0.45)
        if amp > 0.5:
            M = np.float32([[1, 0, rng.normal(0, amp)], [0, 1, rng.normal(0, amp)]])
            fr = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        # transitions
        if not in_sus:
            it = items[k]
            u = t - it["a"]
            if it["trans"] == "flash" and u < 0.14:
                fr = fr + (255 - fr) * (0.85 * (1 - u / 0.14))
            if it["trans"] == "glitch" and u < 0.22:
                fr = glitch(fr, 1 - u / 0.22, fi)
            nxt = items[k + 1] if k + 1 < len(items) else None
            if nxt and nxt["trans"] == "glitch" and nxt["a"] - t < 0.07:
                fr = glitch(fr, 0.6, fi)
            if it["first_of_sec"] and it["a"] > 0 and u < 0.6:  # light leak sweep
                q = u / 0.6
                x0 = int((1 - q) * W)
                lk = look["leak"][:, x0:x0 + W] * (0.55 * math.sin(math.pi * q))
                fr = fr + lk
        else:
            if any(0 <= t - x < 0.1 for x in (sus[0] + 0.05, sus[0] + 0.55)):
                fr = glitch(fr, 0.5, fi)
        text.draw(fr, t, total, cta0, sus, False)
        ff.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if fi % 150 == 0:
            print(f"  frame {fi}/{nF}", flush=True)
    ff.stdin.close()
    ff.wait()
    # sound
    import soundfile as sf
    vw = os.path.join(out_dir, "voice.wav")
    sf.write(vw, clock.voice[:int(total * SR)].astype(np.float32), SR)
    Pm = {"total": total, "off": 0.0, "breaths": [], "sfx": ev, "mus": mus,
          "music": [{"t": 0.0, "track": cfg["music"], "start": cfg.get("music_start", 0.0), "gain": cfg.get("music_gain", 4.0)}]}
    mix, _, _ = r3.mix(vw, Pm, os.path.join(a.media, "music"))
    _, I = fx.loudness(mix)
    mix *= 10 ** ((-13.0 - I) / 20)
    wav = os.path.join(out_dir, "mix.wav")
    sf.write(wav, mix.astype(np.float32), SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "alimiter=limit=0.89:attack=3:release=80:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{total:.3f}", "-movflags", "+faststart", a.out], check=True)
    json.dump({"items": [{k_: v for k_, v in it.items() if k_ in ("ref", "shot", "clip", "a", "b", "trans", "still")} for it in items],
               "total": total, "cta0": cta0, "sus": sus}, open(os.path.splitext(a.out)[0] + ".plan.json", "w"), indent=1)
    print(f"wrote {a.out} ({total:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    for x in ("short", "cutlist", "voice", "captions", "lib", "media", "out"):
        ap.add_argument(x)
    render(ap.parse_args())


if __name__ == "__main__":
    main()
