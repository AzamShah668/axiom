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


SHOTS = [shot_orbit, shot_cluster, shot_grip, shot_dive, shot_break, shot_gauge, shot_end]
ZOOM_IN = [None, False, True, True, True, False, False]       # how each shot enters: zoom in or out of the last


def build_timing(wd):
    """Shot starts on sentence starts; local event times from the words (seconds, at speed)."""
    def at(word, after=0.0):
        for t, w in wd:
            if t >= after and word in w:
                return t
        raise SystemExit(f"word not found: {word}")
    starts = [0.0, at("Big"), at("फिर"), at("अब"), at("क्या"), at("इसके"), at("वो")]
    ev = {"free": at("छूट"), "scatter": at("बिखरने"), "grow": at("फैलाव"), "grav": at("gravity"), "lose": at("खो"),
          "atom": at("zoom"), "tod": at("तोड़"), "khas": at("ख़ास")}
    return starts, ev


def frame(t, starts, ev, total, caps, fonts):
    S.FONTS["dir"] = fonts
    i = max(k for k in range(len(starts)) if starts[k] <= t)
    def draw(j, tt):
        g = S.background(tt, push=0.0, dim=0.8 if j != 1 else 0.6, seed=1 + j)
        u = tt - starts[j]
        T = {k: v - starts[j] for k, v in ev.items()}
        SHOTS[j](u, T, g)
        return g
    f = draw(i, t)
    tr = 0.4
    if i > 0 and t - starts[i] < tr:                  # zoom transition from the previous shot
        p = eo((t - starts[i]) / tr)
        prev = draw(i - 1, t)
        zin = ZOOM_IN[i]
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
    S.text(f, "COULD SPACE", W / 2, 120, 92, "Anton", (255, 255, 255), 1.0, "mm")
    S.text(f, "TEAR AN ATOM?", W / 2, 230, 104, "Anton", AMBER, 1.0, "mm")
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
    ap.add_argument("--tail", type=float, default=1.6)
    a = ap.parse_args()
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
    hits = [("kz_thud", 0.0, 0.0), ("kz_shot", ev["free"], -6), ("kz_whoosh", starts[1] - 0.2, -2), ("kz_whoosh", ev["scatter"], -6),
            ("kz_whoosh", starts[2] - 0.2, -2), ("kz_shot", ev["lose"], -3), ("kz_whoosh", starts[3] - 0.2, -2),
            ("riser", ev["atom"] - 1.2, -8), ("kz_thud", ev["atom"], -4), ("kz_scratch", ev["tod"], -4), ("kz_whoosh", starts[5] - 0.2, -4),
            ("kz_thud", ev["khas"], -6), ("bell", starts[6] + 0.2, -6)]
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
