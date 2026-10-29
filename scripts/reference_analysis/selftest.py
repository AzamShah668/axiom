"""Self-test for the reference-analysis tools: render a 48 s synthetic video whose every cut, transition, camera
move, text animation, music track, ducking move, swell, drop-out and SFX is known, run the analyzers on it and
score what they recover.

  python selftest.py <work_dir> [--keep]

The audio stems are written directly (Demucs is not part of the test). Prints a PASS/FAIL table and writes
<work_dir>/selftest.json. Run it after changing audio_stats.py, visual_stats.py or text_track.py.
"""
import json, math, os, subprocess, sys
import numpy as np, cv2, soundfile as sf
from scipy import signal
from PIL import Image, ImageDraw, ImageFont

H_ = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR, DUR = 1280, 720, 30, 44100, 48.0
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
rng = np.random.default_rng(5)

# ------------------------------------------------------------------ ground truth
SHOTS = [  # start, end, kind, motion
    (0, 5, "still", "push-in"), (5, 10, "still", "pan right"), (10, 15, "footage", "-"), (15, 20, "graphic", "static"),
    (20, 25, "parallax", "2.5D parallax"), (25, 30, "still", "static"), (30, 40, "still", "pull-out"), (40, 48, "footage", "-")]
CUTS = [(5.0, "cut"), (10.25, "dissolve"), (15.0, "flash"), (20.0, "whip"), (25.0, "dip to black"), (30.0, "glitch"), (40.0, "cut")]
TEXTS = [  # text, t_in, t_out, entry, exit, colour, position
    ("1,000,000 KM", 16.0, 19.0, "fade", "fade", "white", "middle centre"),
    ("SUN", 26.0, 29.0, "scale pop", "fade", "yellow", "middle centre"),
    ("SURFACE 5,500 C", 27.0, 29.5, "slide in from left", "cut", "white", "lower third centre"),
    ("COUNTER", 31.0, 38.0, "cut", "cut", "white", "top centre"),
    ("THE END OF THE STAR", 41.0, 46.0, "wipe/typewriter L->R", "cut", "white", "lower third centre")]
PAUSES = [(4.6, 5.6), (9.2, 10.4), (14.0, 15.6), (19.0, 20.2), (24.0, 26.0), (29.0, 30.4), (33.5, 34.5), (38.5, 41.0), (44.0, 45.0)]
SFX = [  # onset, type
    (9.85, "whoosh"), (15.0, "boom"), (16.0, "pop/click"), (18.0, "riser"), (20.0, "hit"), (26.0, "pop/click"),
    (26.85, "whoosh"), (30.0, "glitch"), (40.0, "boom"), (43.13, "pop/click"), (45.0, "sub drop")]
MUSIC = [(0.0, 20.5, 100, "A minor"), (21.0, 48.0, 75, "C major")]
DUCK_DB = 11.0
# known limitations (reported as XFAIL): the 15.0 boom is stacked on a kick drum of the music, so the kick's attack
# sets the peak and the boom's tail reads too short: it is found at the right time but typed "hit"
KNOWN = {"sfx 15.0 boom"}
SWELL = 39.5
DROPOUT = (35.0, 35.8)


# ------------------------------------------------------------------ pictures
def nebula(seed, w=1600, h=900):
    """A space-like still: shared luminance structure (so the colour channels' edges line up, as in real images),
    a slowly varying tint, and white stars."""
    r = np.random.default_rng(seed)
    lum = np.zeros((h, w), np.float32)
    for k, s in enumerate((160, 60, 20, 6)):
        lum += cv2.resize(r.random((h // s + 2, w // s + 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC) * (0.6 / (k + 1))
    lum = np.clip(lum / lum.max(), 0, 1) ** 2.2
    tint = cv2.resize(r.random((4, 6, 3)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    tint = np.clip(tint, 0.1, 1) * np.array([255, 160, 220], np.float32)[r.permutation(3)]
    img = lum[..., None] * tint
    xs, ys = r.integers(0, w, 2500), r.integers(0, h, 2500)
    img[ys, xs] = 255
    return np.clip(cv2.GaussianBlur(img, (0, 0), 0.7), 0, 255).astype(np.uint8)


def view(img, z, cx, cy):
    ih, iw = img.shape[:2]
    s = max(W / iw, H / ih) * z
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def text_layer(txt, size, color=(255, 255, 255)):
    f = ImageFont.truetype(FONT, size)
    b = f.getbbox(txt)
    im = Image.new("RGBA", (b[2] - b[0] + 20, b[3] - b[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - b[0], 10 - b[1]), txt, font=f, fill=color[::-1] + (255,))
    a = np.array(im).astype(np.float32)
    return a[..., [2, 1, 0]], a[..., 3] / 255


def put(fr, layer, cx, cy, op=1.0, scale=1.0, cols=None):
    bgr, a = layer
    if scale != 1.0:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale)
        a = cv2.resize(a, None, fx=scale, fy=scale)
    if cols is not None:
        a = a.copy()
        a[:, int(a.shape[1] * cols):] = 0
    h, w = a.shape
    x, y = int(cx - w / 2), int(cy - h / 2)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x, None] * op
    reg = fr[y0:y1, x0:x1].astype(np.float32)
    fr[y0:y1, x0:x1] = (reg * (1 - aa) + bgr[y0 - y:y1 - y, x0 - x:x1 - x] * aa).astype(np.uint8)


class Footage:
    """Non-rigid motion: blobs drifting different ways over a churning background."""
    def __init__(self, seed):
        r = np.random.default_rng(seed)
        self.p = r.uniform(0, 1, (60, 2)) * [W, H]
        self.v = r.normal(0, 90, (60, 2))
        self.c = r.uniform(60, 255, (60, 3))
        self.base = [nebula(seed + k, W // 4, H // 4) for k in range(2)]

    def frame(self, t):
        a = 0.5 + 0.5 * math.sin(t * 1.3)
        bg = cv2.addWeighted(self.base[0], a, self.base[1], 1 - a, 0)
        bg = cv2.resize(bg, (W, H))
        sh = np.float32([[1, 0, 25 * math.sin(t * 2.1)], [0, 1, 18 * math.cos(t * 1.7)]])
        fr = cv2.warpAffine(bg, sh, (W, H), borderMode=cv2.BORDER_REFLECT)
        for (x, y), (vx, vy), c in zip(self.p, self.v, self.c):
            cv2.circle(fr, (int((x + vx * t) % W), int((y + vy * t + 30 * math.sin(t * 3 + x)) % H)), 22, tuple(float(v) for v in c), -1, cv2.LINE_AA)
        return fr


def render_video(path):
    st = [nebula(s) for s in (1, 2, 3, 4)]
    fg = [Footage(7), Footage(9)]
    planet = np.zeros((420, 420, 3), np.uint8)
    cv2.circle(planet, (210, 210), 200, (80, 140, 230), -1, cv2.LINE_AA)
    cv2.circle(planet, (150, 160), 60, (120, 190, 255), -1, cv2.LINE_AA)
    pmask = np.zeros((420, 420), np.float32)
    cv2.circle(pmask, (210, 210), 200, 1.0, -1, cv2.LINE_AA)
    T1, T2 = text_layer("1,000,000 KM", 70), text_layer("SUN", 150, (40, 220, 255))
    T3 = text_layer("SURFACE 5,500 C", 44)
    T5 = text_layer("THE END OF THE STAR", 48)

    def shot(i, t):
        s0 = SHOTS[i][0]
        u = t - s0
        if i == 0:
            return view(st[0], 1.0 + 0.024 * u, 800, 450)
        if i == 1:
            return view(st[1], 1.15, 600 + 40 / 0.8 * u * 0.8, 450)
        if i == 2:
            return fg[0].frame(u)
        if i == 3:
            fr = np.zeros((H, W, 3), np.uint8)
            cv2.circle(fr, (W // 2, H // 2 - 40), 160, (255, 255, 255), 3, cv2.LINE_AA)
            cv2.line(fr, (W // 2 - 400, H // 2 + 200), (W // 2 + 400, H // 2 + 200), (255, 255, 255), 3, cv2.LINE_AA)
            cv2.circle(fr, (int(W / 2 + 160 * math.cos(u)), int(H / 2 - 40 + 160 * math.sin(u))), 14, (0, 200, 255), -1, cv2.LINE_AA)
            return fr
        if i == 4:
            fr = view(st[2], 1.1, 800 - 20 * u, 450)
            sz = int(420 * (0.8 + 0.04 * u))
            pl, pm = cv2.resize(planet, (sz, sz)), cv2.resize(pmask, (sz, sz))
            x, y = int(W / 2 - sz / 2 + 60 * u - 150), int(H / 2 - sz / 2)
            put(fr, (pl.astype(np.float32), pm), x + sz / 2, y + sz / 2)
            return fr
        if i == 5:
            return view(st[3], 1.05, 800, 450)
        if i == 6:
            return view(st[0], 1.15 - 0.015 * u, 700, 400)
        return fg[1].frame(u)

    def at(t):
        i = max(k for k, s in enumerate(SHOTS) if s[0] <= t + 1e-9)
        return i

    def base(t):
        i = at(t)
        fr = shot(i, t)
        # transitions into shot i
        if i == 2 and 10.0 <= t < 10.5:
            p = (t - 10.0) / 0.5
            fr = cv2.addWeighted(shot(1, t), 1 - p, fr, p, 0)
        if i == 3 and t < 15.3:
            p = (t - 15.0) / 0.3
            fr = cv2.addWeighted(fr, 1, np.full_like(fr, 255), 0.85 * math.cos(math.pi / 2 * p), 0)
        if i == 2 and 14.7 <= t:
            p = (t - 14.7) / 0.3
            fr = cv2.addWeighted(fr, 1, np.full_like(fr, 255), 0.85 * math.sin(math.pi * p / 2), 0)
        if i == 3 and t >= 19.85:
            p = (t - 19.85) / 0.3
            dx = int(W * p * 0.5)
            fr = np.roll(fr, -dx, 1)
            fr = cv2.blur(fr, (int(1 + 70 * math.sin(math.pi * min(p, 1))), 1))
        if i == 4 and t < 20.15:
            p = 0.5 + (t - 20.0) / 0.3
            dx = int(W * (p - 0.5) * 0.5)
            fr = np.roll(fr, W // 4 - dx, 1)
            fr = cv2.blur(fr, (int(1 + 70 * math.sin(math.pi * min(p, 1))), 1))
        if i == 4 and t >= 24.7:
            fr = (fr * max(0, (25.0 - t) / 0.3)).astype(np.uint8)
        if i == 5 and t < 25.3:
            fr = (fr * min(1, (t - 25.0) / 0.3)).astype(np.uint8)
        if 29.93 <= t < 30.1:
            b, g, r = cv2.split(fr)
            fr = cv2.merge([np.roll(b, -12, 1), g, np.roll(r, 12, 1)])
            for y in range(0, H, 60):
                if rng.random() < 0.4:
                    fr[y:y + 30] = np.roll(fr[y:y + 30], int(rng.integers(-80, 80)), 1)
        # text
        if 16.0 <= t < 19.4:
            op = min(1, (t - 16.0) / 0.4) * min(1, max(0, (19.4 - t) / 0.4))
            put(fr, T1, W / 2, H / 2 + 100, op)
        if 26.0 <= t < 29.4:
            u = t - 26.0
            sc = 0.6 + 0.5 * min(1, u / 0.2) if u < 0.2 else (1.1 - 0.1 * min(1, (u - 0.2) / 0.15))
            put(fr, T2, W / 2, H / 2 - 20, min(1, u / 0.1) * min(1, max(0, (29.4 - t) / 0.4)), sc)
        if 27.0 <= t < 29.5:
            u = min(1, (t - 27.0) / 0.4)
            x = -300 + (W / 2 + 300) * (1 - (1 - u) ** 3)
            cv2.rectangle(fr, (int(x - 260), H - 140), (int(x + 260), H - 80), (30, 30, 30), -1)
            put(fr, T3, x, H - 110)
        if 31.0 <= t < 38.0:
            v = int(150_000_000 * min(1, (t - 31.0) / 3.0))
            put(fr, text_layer(f"{v:,} KM", 54), W / 2, 90)
        if 41.0 <= t < 46.0:
            put(fr, T5, W / 2, H - 110, 1.0, 1.0, cols=min(1, (t - 41.0) / 1.0))
        if t > DUR - 0.5:
            fr = (fr * max(0, (DUR - t) / 0.5)).astype(np.uint8)
        return fr

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for f in range(int(DUR * FPS)):
        ff.stdin.write(np.ascontiguousarray(base(f / FPS)).tobytes())
    ff.stdin.close()
    ff.wait()


# ------------------------------------------------------------------ sound
def voice():
    n = int(DUR * SR)
    v = np.zeros(n)
    t = 1.0
    speech = np.zeros(n, bool)
    while t < DUR - 1.2:
        if any(a <= t < b for a, b in PAUSES):
            t = next(b for a, b in PAUSES if a <= t < b)
            continue
        d = rng.uniform(0.14, 0.24)
        nxt = min([a for a, b in PAUSES if a > t] + [DUR - 1.0])
        d = min(d, nxt - t)
        if d < 0.06:
            t = nxt
            continue
        i0, i1 = int(t * SR), int((t + d) * SR)
        tt = np.arange(i1 - i0) / SR
        f0 = rng.uniform(105, 140) * (1 + 0.04 * np.sin(2 * np.pi * 3 * tt))
        ph = 2 * np.pi * np.cumsum(f0) / SR
        s = sum(np.sin(k * ph) / k for k in range(1, 12))
        env = np.sin(np.pi * tt / d) ** 0.6
        v[i0:i1] = s * env
        speech[i0:i1] = True
        t += d + 0.04
    for lo, hi in ((300, 900), (1100, 2600)):
        b, a = signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], "band")
        v = v + 0.8 * signal.lfilter(b, a, v)
    v = v / np.abs(v).max() * 0.5
    return v, speech


def tone(f, dur, decay=0.0):
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * f * t) * (np.exp(-t * decay) if decay else 1)


def music():
    n = int(DUR * SR)
    other, drums, bass = np.zeros(n), np.zeros(n), np.zeros(n)
    t = np.arange(n) / SR
    a, b = int(0 * SR), int(20.5 * SR)
    pad = sum(np.sin(2 * np.pi * f * t[a:b]) for f in (220.0, 261.63, 329.63, 440.0)) / 4
    pad *= np.clip(t[a:b] / 1.5, 0, 1) * np.clip((20.5 - t[a:b]) / 1.0, 0, 1)
    other[a:b] += 0.5 * pad
    bass[a:b] += 0.3 * np.sin(2 * np.pi * 55 * t[a:b]) * np.clip(t[a:b] / 1.5, 0, 1) * np.clip((20.5 - t[a:b]) / 1.0, 0, 1)
    for k in np.arange(0.6, 20.0, 60 / 100):
        i = int(k * SR)
        kick = np.sin(2 * np.pi * (60 + 80 * np.exp(-np.arange(int(0.25 * SR)) / SR * 30)) * np.arange(int(0.25 * SR)) / SR) * np.exp(-np.arange(int(0.25 * SR)) / SR * 14)
        drums[i:i + len(kick)] += 0.5 * kick
    notes = [261.63, 329.63, 392.0, 523.25]
    for j, k in enumerate(np.arange(21.0, 47.5, 60 / 75 / 2)):
        i = int(k * SR)
        nt = tone(notes[j % 4], 0.5, 6) * 0.4
        other[i:i + len(nt)] += nt[:n - i] * min(1, (k - 21) / 1.0 + 0.1)
        hh = rng.normal(0, 1, int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 90) * 0.15
        drums[i:i + len(hh)] += hh[:n - i]
    return other, drums, bass


def sfx():
    n = int(DUR * SR)
    out = np.zeros(n)

    def add(t0, sig, g):
        i = int(t0 * SR)
        out[i:i + len(sig)] += g * sig[:n - i] / (np.abs(sig).max() + 1e-9)

    def noise(d):
        return rng.normal(0, 1, int(d * SR))

    def whoosh(d):
        x = noise(d)
        tt = np.arange(len(x)) / SR
        x = x - np.convolve(x, np.ones(30) / 30, "same")
        return np.convolve(x * np.sin(np.pi * tt / d) ** 2, np.ones(6) / 6, "same")

    def boom(d=2.0):
        tt = np.arange(int(d * SR)) / SR
        return np.sin(2 * np.pi * (50 - 15 * tt) * tt) * np.exp(-tt * 2) + np.convolve(noise(d), np.ones(200) / 200, "same") * np.exp(-tt * 8) * 4

    def pop():
        tt = np.arange(int(0.07 * SR)) / SR
        return (np.sin(2 * np.pi * 1800 * tt) + 0.4 * np.sin(2 * np.pi * 3600 * tt)) * np.exp(-tt * 70)

    def riser(d):
        tt = np.arange(int(d * SR)) / SR
        x = noise(d)
        b, a = signal.butter(2, 3000 / (SR / 2), "high")
        x = signal.lfilter(b, a, x)
        return x * (tt / d) ** 2.5 + 0.3 * np.sin(2 * np.pi * (2000 + 3000 * tt / d) * tt) * (tt / d) ** 2

    def hit():
        tt = np.arange(int(0.35 * SR)) / SR
        return np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 18) + noise(0.35) * np.exp(-tt * 40) * 0.5

    def glitch():
        x = np.zeros(int(0.35 * SR))
        for k in range(5):
            i = int(k * 0.07 * SR)
            x[i:i + int(0.03 * SR)] = noise(0.03)
        return x

    def subdrop(d=1.2):
        tt = np.arange(int(d * SR)) / SR
        f = 90 * np.exp(-tt * 1.2)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.0)

    add(9.85, whoosh(0.8), 0.35)
    add(15.0, boom(), 0.8)
    add(16.0, pop(), 0.15)
    add(18.0, riser(2.0), 0.3)
    add(20.0, hit(), 0.5)
    add(26.0, pop(), 0.15)
    add(26.85, whoosh(0.5), 0.3)
    add(30.0, glitch(), 0.25)
    add(40.0, boom(), 0.8)
    add(43.13, pop(), 0.15)
    add(45.0, subdrop(), 0.6)
    return out


def render_audio(adir):
    v, speech = voice()
    other, drums, bass = music()
    n = len(v)
    # ducking: -20 dB under speech, -9 dB in pauses (attack 0.15 s, release 0.4 s), a swell and a drop-out
    act = np.convolve(speech.astype(float), np.ones(int(0.25 * SR)), "same") > 0  # bridge syllable gaps
    tgt = np.where(act, -20.0, -9.0)
    g = np.zeros(n)
    cur = -9.0
    a_c, r_c = math.exp(-1 / (0.05 * SR)), math.exp(-1 / (0.13 * SR))
    for i in range(0, n, 64):
        c = a_c if tgt[i] < cur else r_c
        cur = tgt[i] + (cur - tgt[i]) * c ** 64
        g[i:i + 64] = cur
    t = np.arange(n) / SR
    g += 6 * np.exp(-((t - SWELL) / 1.0) ** 2)
    gl = 10 ** (g / 20)
    gl[(t >= DROPOUT[0]) & (t < DROPOUT[1])] = 0
    other, drums, bass = other * gl, drums * gl, bass * gl
    fx = sfx() * 0.5
    other = other + fx
    st = lambda x: np.stack([x, x], 1)
    D = f"{adir}/demucs/htdemucs/mix"
    os.makedirs(D, exist_ok=True)
    for name, x in (("vocals", v), ("other", other), ("drums", drums), ("bass", bass), ("no_vocals", other + drums + bass)):
        sf.write(f"{D}/{name}.wav", st(x).astype(np.float32), SR)
    sf.write(f"{adir}/mix.wav", st(np.clip(v + other + drums + bass, -1, 1)).astype(np.float32), SR)
    segs, on = [], None
    for i in range(0, n, int(0.01 * SR)):
        a_ = bool(act[i])
        if a_ and on is None:
            on = i / SR
        if not a_ and on is not None:
            segs.append((on, i / SR))
            on = None
    return segs


# ------------------------------------------------------------------ scoring
def main():
    work = os.path.abspath(sys.argv[1])
    an = f"{work}/an"
    os.makedirs(f"{an}/scenes", exist_ok=True)
    py = sys.executable
    vid = f"{work}/video.mp4"
    if not os.path.exists(vid):
        print("rendering synthetic video...")
        render_video(vid)
    render_audio(f"{an}/audio")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", f"{an}/audio/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", f"{work}/video_av.mp4"], check=True)
    for det, name, extra in (("detect-adaptive", "adaptive.csv", []), ("detect-content", "content.csv", ["-t", "27"])):
        subprocess.run([py, "-m", "scenedetect", "-i", vid, "-o", f"{an}/scenes", det, *extra, "list-scenes", "-f", name, "-q"],
                       capture_output=True)
    run = lambda *a: subprocess.run([py, *a], check=True, capture_output="--verbose" not in sys.argv)
    run(f"{H_}/audio_stats.py", f"{an}/audio")
    run(f"{H_}/visual_stats.py", vid, an)
    if "--no-text" not in sys.argv:
        run(f"{H_}/text_track.py", vid, an, "--langs", "en")
    run(f"{H_}/report.py", an, "--video", vid, "--no-strips")
    A = json.load(open(f"{an}/audio/audio_stats.json"))
    V = json.load(open(f"{an}/visual.json"))
    T = json.load(open(f"{an}/text_events.json")) if os.path.exists(f"{an}/text_events.json") else {"events": []}
    R = []

    def check(name, ok, detail):
        R.append({"check": name, "ok": bool(ok), "detail": detail})

    # cuts + transitions
    found = V["cuts"]
    for t, kind in CUTS:
        m = min(found, key=lambda c: abs(c["t"] - t), default=None)
        hit_ = m is not None and abs(m["t"] - t) <= 0.4
        check(f"cut {t} {kind}", hit_ and m["type"].startswith(kind), f"found {m['t'] if m else None} {m['type'] if m else ''}")
    check("no extra cuts", len(found) <= len(CUTS) + 1, f"{len(found)} cuts found for {len(CUTS)}: {[(c['t'], c['type']) for c in found]}")
    # shots
    for s0, s1, kind, motion in SHOTS:
        mid = (s0 + s1) / 2
        s = next((x for x in V["shots"] if x["start"] <= mid < x["end"]), None)
        want = {"still": "still", "footage": "footage", "graphic": "graphic", "parallax": "2.5D"}[kind]
        ok = s is not None and want in s["content"] and (motion == "-" or motion.split(" ")[0] in s["motion"] or
                                                          (motion == "static" and s["motion"] == "static"))
        check(f"shot {s0}-{s1} {kind}/{motion}", ok, f"{s['content'] if s else None} / {s['motion'] if s else None}")
    # text
    ev = T["events"]
    for txt, t_in, t_out, entry, exit_, col, pos in TEXTS:
        if txt == "COUNTER":
            m = next((e for e in ev if e.get("counter")), None)
            check("text counter", m is not None and abs(m["t_first"] - t_in) <= 0.6 and len([e for e in ev if e.get("counter")]) == 1,
                  f"{[(e['t_first'], e['counter']) for e in ev if e.get('counter')]}")
            continue
        m = min(ev, key=lambda e: abs(e.get("entry", {}).get("t_visible", e["t_first"]) - t_in) + (0 if txt.split()[0] in e["text"] else 5), default=None)
        if m is None:
            check(f"text {txt}", False, "not found")
            continue
        tvis = m.get("entry", {}).get("t_visible", m["t_first"])
        check(f"text '{txt}' timing", abs(tvis - t_in) <= 0.25, f"visible {tvis} (truth {t_in}), text '{m['text']}'")
        check(f"text '{txt}' entry {entry}", m.get("entry", {}).get("kind", "").startswith(entry), m.get("entry", {}).get("kind"))
        check(f"text '{txt}' colour/position", m.get("colour") == col and m["position"] == pos, f"{m.get('colour')} {m['position']}")
    # audio
    pz = [(a, b) for (a0, a), (b, b1) in zip(A["speech_segments"], A["speech_segments"][1:]) if b - a >= 0.3]
    hits = sum(1 for a, b in PAUSES if any(abs(a - x) <= 0.2 and abs(b - y) <= 0.2 for x, y in pz))
    check("pauses found", hits >= len(PAUSES) - 1, f"{hits}/{len(PAUSES)} pauses, {len(pz)} detected")
    ms = [m for m in A["music_segments"] if m["music"]]
    check("music tracks", A["music_distinct_tracks"] == 2, f"{A['music_distinct_tracks']} tracks; segments {[(m['start'], m['end'], m.get('track')) for m in A['music_segments']]}")
    for s0, s1, bpm, key in MUSIC:
        m = max(ms, key=lambda x: min(x["end"], s1) - max(x["start"], s0), default=None)
        ok_t = m is not None and m["tempo_bpm"] and min(abs(m["tempo_bpm"] / bpm - r) for r in (0.5, 1, 2)) < 0.06
        check(f"music {s0}-{s1} tempo {bpm}", ok_t, f"{m['tempo_bpm'] if m else None} ({m['pulse_clarity'] if m else None})")
        check(f"music {s0}-{s1} key {key}", m is not None and m["key"] == key, m["key"] if m else None)
    b = [m["start"] for m in A["music_segments"]][1:]
    check("music boundary ~20.5-21", any(19 <= x <= 22.5 for x in b), f"boundaries {b}")
    dk = A["ducking"].get("depth_db")
    check("ducking depth ~11 dB", dk is not None and abs(dk - DUCK_DB) <= 3, f"{dk} dB, release {A['ducking'].get('release_s_to_90pct')}, attack {A['ducking'].get('attack_s_to_90pct')}")
    check("swell at 39.5", any(abs(s["peak"] - SWELL) <= 0.8 for s in A["swells"]), [s["peak"] for s in A["swells"]])
    check("music drop-out 35.0", any(abs(d["start"] - DROPOUT[0]) <= 0.3 for d in A["silences"]["music_dropouts"]), A["silences"]["music_dropouts"])
    ok_n = 0
    for t, kind in SFX:
        key = "peak_t" if kind == "riser" else "t"  # a riser is heard from well after its (silent) start: check its end
        t = t + 2.0 if kind == "riser" else t
        # an edit sound exactly on a music beat is kept with the beat transients; report.py brings it back
        # when it coincides with a cut (the 15.0 boom sits on a kick and on the flash)
        pool = A["sfx_events"] + [e for e in A.get("music_beat_transients", []) if any(abs(e["t"] - c["t"]) <= 0.3 for c in V["cuts"])]
        same = [e for e in pool if e["type"] == kind and abs(e[key] - t) <= 0.2]
        m = same[0] if same else min(A["sfx_events"], key=lambda e: abs(e[key] - t), default=None)
        good = bool(same)
        ok_n += good
        check(f"sfx {t} {kind}", good, f"{m['t'] if m else None} {m['type'] if m else None} (dur {m['dur'] if m else None}, attack {m.get('attack') if m else None}, "
                                       f"low {m.get('low_share') if m else None}, bw {m.get('bandwidth') if m else None}, noise {m.get('noisiness') if m else None})")
    check("no extra sfx", len(A["sfx_events"]) <= len(SFX) + 3, f"{len(A['sfx_events'])} events: {[(e['t'], e['type']) for e in A['sfx_events']]}")
    ff = subprocess.run(["ffmpeg", "-nostats", "-i", f"{an}/audio/mix.wav", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I_ff = float(ff.split("Integrated loudness:")[1].split("I:")[1].split("LUFS")[0])
    check("integrated LUFS vs ffmpeg", abs(I_ff - A["lufs_integrated"]["mix"]) <= 0.5, f"ours {A['lufs_integrated']['mix']} ffmpeg {I_ff}")
    json.dump(R, open(f"{work}/selftest.json", "w"), indent=1)
    w = max(len(r["check"]) for r in R)
    for r in R:
        tag = "PASS" if r["ok"] else "XFAIL" if r["check"] in KNOWN else "FAIL"
        print(f"{tag:<5} {r['check']:<{w}}  {r['detail']}")
    bad = [r for r in R if not r["ok"] and r["check"] not in KNOWN]
    print(f"{sum(r['ok'] for r in R)}/{len(R)} passed, {len(bad)} unexpected failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
