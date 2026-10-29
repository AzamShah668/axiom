"""Procedural sound-effects kit for the v3 style. Every sound is synthesised here from noise and sine waves, so
the SFX layer is licence-clean by construction (no samples, nothing to credit).

  make(kind, **kw) -> stereo float (n, 2), peak 1.0; the mixer sets the level from LEVEL (LU vs the voice)
  kinds: tick, pop, roll(d), hit, impact, sub_drop, riser(d), whoosh(d), whoosh_big, flare, sting
  loudness(x, sr) -> (momentary LUFS every 100 ms, integrated LUFS)  (BS.1770 K-weighting and gating)

Listen to the whole kit: python sfx.py <out.wav>
"""
import sys
import numpy as np
from scipy import signal

SR = 44100

# level of each sound's loudest 400 ms vs the voice's momentary loudness while speaking (LU)
LEVEL = {"tick": -20, "pop": -18, "roll": -24, "hit": -8, "impact": -2, "sub_drop": -8, "riser": -7,
         "whoosh": -15, "whoosh_big": -10, "flare": -12, "sting": -3, "boom": -3, "hiss": -14}


# ------------------------------------------------------------------ loudness
def k_weight(x, sr):
    """K-weighting: high shelf + high pass, coefficients as in pyloudnorm / libebur128."""
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    A, w0 = 10 ** (G / 40), 2 * np.pi * fc / sr
    al = np.sin(w0) / (2 * Q)
    b = [A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * np.cos(w0)),
         A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * al)]
    a = [(A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * np.cos(w0)),
         (A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * al]
    x = signal.lfilter(b, a, x, axis=0)
    Q, fc = 0.5003270373238773, 38.13547087602444
    w0 = 2 * np.pi * fc / sr
    al = np.sin(w0) / (2 * Q)
    b = [(1 + np.cos(w0)) / 2, -(1 + np.cos(w0)), (1 + np.cos(w0)) / 2]
    a = [1 + al, -2 * np.cos(w0), 1 - al]
    return signal.lfilter(b, a, x, axis=0)


def loudness(x, sr=SR):
    """-> (momentary LUFS every 100 ms (400 ms window, value at window centre), integrated gated LUFS)."""
    x = x if x.ndim > 1 else x[:, None]
    z = (k_weight(x, sr) ** 2).sum(1)
    hop, win = int(sr * 0.1), int(sr * 0.4)
    c = np.concatenate([[0], np.cumsum(z)])
    starts = np.arange(-win // 2, len(z) - win // 2, hop)
    a, b = np.clip(starts, 0, len(z)), np.clip(starts + win, 0, len(z))
    ms = (c[b] - c[a]) / win
    M = -0.691 + 10 * np.log10(np.maximum(ms, 1e-12))
    g = ms[M > -70]
    if not len(g):
        return M, -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = g[(-0.691 + 10 * np.log10(g)) > rel]
    return M, float(-0.691 + 10 * np.log10(g.mean()))


def peak_loudness(x, sr=SR):
    """Loudest momentary (400 ms) loudness of a short sound, LUFS."""
    pad = np.zeros((int(0.2 * sr),) + x.shape[1:])
    return float(loudness(np.concatenate([pad, x, pad]), sr)[0].max())


# ------------------------------------------------------------------ building blocks
def _t(d):
    return np.arange(int(d * SR)) / SR


def _rng(seed):
    return np.random.default_rng(seed)


def _bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, min(hi, SR / 2 - 100)], "bandpass", fs=SR, output="sos"), x, axis=0)


def _lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "lowpass", fs=SR, output="sos"), x, axis=0)


def _hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "highpass", fs=SR, output="sos"), x, axis=0)


def _sweep(x, fc, bw=0.7):
    """Time-varying band-pass: fc(t) in Hz (array, one value per STFT frame or per sample), bw in octaves."""
    f, tt, Z = signal.stft(x, SR, nperseg=1024, noverlap=768)
    fc = np.asarray(fc, float)
    if fc.ndim and len(fc) != Z.shape[1]:
        fc = np.interp(np.linspace(0, 1, Z.shape[1]), np.linspace(0, 1, len(fc)), fc)
    oc = np.log2(np.maximum(f[:, None], 1.0) / np.maximum(fc[None, :], 1.0))
    _, y = signal.istft(Z * np.exp(-0.5 * (oc / bw) ** 2), SR, nperseg=1024, noverlap=768)
    return y[:len(x)] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))


def _reverb(x, t60=1.6, mix=0.25, seed=3, tone=5000):
    """Stereo reverb: convolution with decorrelated exponentially decaying noise."""
    n = int(t60 * SR)
    tt = np.arange(n) / SR
    r = _rng(seed)
    ir = np.stack([r.normal(0, 1, n), r.normal(0, 1, n)], 1) * np.exp(-6.9 * tt / t60)[:, None]
    ir = _lp(ir, tone)
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]  # pre-delay feel
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    mono = x.mean(1) if x.ndim > 1 else x
    wet = np.stack([signal.fftconvolve(mono, ir[:, 0]), signal.fftconvolve(mono, ir[:, 1])], 1)
    dry = _st(x)
    dry = np.pad(dry, ((0, len(wet) - len(dry)), (0, 0)))
    return dry * (1 - mix) + wet * mix * 3.0


def _st(x, pan=0.0):
    if x.ndim > 1:
        return x
    pan = np.broadcast_to(np.asarray(pan, float), x.shape)
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1) * np.sqrt(2)


def _norm(x):
    x = _st(x)
    fade = min(len(x), int(0.01 * SR))
    x[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def _saw(f, tt, harmonics=10):
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(f, tt.shape)) / SR
    return sum(np.sin(k * ph) / k for k in range(1, harmonics + 1))


# ------------------------------------------------------------------ the kit
def tick(seed=1):
    """Crisp UI tick for each kinetic text line (25 ms)."""
    tt = _t(0.05)
    r = _rng(seed)
    x = _bp(r.normal(0, 1, len(tt)), 3000, 9000) * np.exp(-tt / 0.004)
    x += 0.5 * np.sin(2 * np.pi * 1900 * tt) * np.exp(-tt / 0.009)
    return _norm(_reverb(x, 0.35, 0.12))


def pop(seed=2):
    """Soft pop for a key phrase appearing (90 ms falling tone + click)."""
    tt = _t(0.12)
    f = 720 * np.exp(-tt * 6) + 380
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.03)
    x += 0.3 * _bp(_rng(seed).normal(0, 1, len(tt)), 2000, 8000) * np.exp(-tt / 0.003)
    return _norm(_reverb(x, 0.5, 0.15))


def roll(d=1.3, seed=4):
    """Counter roll: ticks that slow down with an ease-out count (fast at the start, stopping at d)."""
    r = _rng(seed)
    out = np.zeros(int((d + 0.08) * SR))
    t, k = 0.0, 0
    while t < d - 0.02:
        p = t / d
        rate = 34 * (1 - p) ** 2 + 5          # ticks per second follow the counter's speed
        tt = _t(0.014)
        g = (0.55 + 0.45 * (1 - p)) * (0.8 + 0.2 * r.random())
        x = _bp(r.normal(0, 1, len(tt)), 3500 + 1500 * r.random(), 9000) * np.exp(-tt / 0.0025) * g
        i = int(t * SR)
        out[i:i + len(x)] += x[:len(out) - i]
        t += 1 / rate
        k += 1
    return _norm(_reverb(out, 0.3, 0.1))


def hit(seed=5):
    """Punchy hit for a number landing or a hard cut (body 95 -> 55 Hz, transient, short room)."""
    tt = _t(0.9)
    f = 55 + 40 * np.exp(-tt / 0.05)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.18)
    mid = 0.35 * np.sin(2 * np.pi * 185 * tt) * np.exp(-tt / 0.07)
    tr = 0.6 * _lp(_rng(seed).normal(0, 1, len(tt)), 4000) * np.exp(-tt / 0.012)
    x = np.tanh(1.6 * (body + mid + tr))
    return _norm(_reverb(x, 1.1, 0.18))


def impact(seed=6):
    """Cinematic impact for the big reveals: sub sweep 58 -> 28 Hz, crunch, long tail."""
    tt = _t(3.6)
    f = 28 + 30 * np.exp(-tt / 0.45)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.9)
    r = _rng(seed)
    crunch = _lp(r.normal(0, 1, len(tt)), 1500) * np.exp(-tt / 0.14) * 0.9
    air = _bp(r.normal(0, 1, len(tt)), 2000, 9000) * np.exp(-tt / 0.35) * 0.15
    x = np.tanh(1.3 * (sub + crunch)) + air
    return _norm(_reverb(x, 3.0, 0.32, tone=3000))


def sub_drop(d=1.4):
    """Low pitch drop 90 -> 30 Hz under a dip to black."""
    tt = _t(d)
    f = 30 + 60 * np.exp(-tt / (d / 3))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, tt / 0.04) * np.exp(-tt / (d / 2.2))
    return _norm(x)


def riser(d=2.0, seed=7):
    """Tension riser that ends exactly at d (the reveal word): sweeping noise + three rising detuned saws."""
    tt = _t(d)
    p = tt / d
    r = _rng(seed)
    noise = _sweep(r.normal(0, 1, len(tt)), 300 * (6000 / 300) ** np.linspace(0, 1, 64), bw=0.9)
    f = 110 * 4 ** (p ** 1.5)
    tone = sum(_saw(f * k, tt, 6) for k in (1.0, 1.006, 0.497)) / 3
    tone = _lp(tone, 2500)
    x = (0.9 * noise + 0.5 * tone) * p ** 2.2
    st = np.stack([x * (1 - 0.3 * p) + 0.3 * p * np.roll(x, 300), x * (1 - 0.3 * p) + 0.3 * p * np.roll(x, -300)], 1)
    st[-int(0.006 * SR):] *= np.linspace(1, 0, int(0.006 * SR))[:, None]
    return _norm(st)


def whoosh(d=0.6, f0=400, f1=2600, seed=8):
    """Air whoosh into a dip or a move: band sweeps up then down, pans left to right, peak at 60 %."""
    tt = _t(d)
    p = tt / d
    shape = np.where(p < 0.6, p / 0.6, 1 - (p - 0.6) / 0.4)
    fc = f0 * (f1 / f0) ** np.interp(np.linspace(0, 1, 64), p, shape)
    x = _sweep(_rng(seed).normal(0, 1, len(tt)), fc, bw=0.8) * np.sin(np.pi * np.clip(shape, 0, 1) / 2) ** 2
    return _norm(_reverb(_st(x, -0.7 + 1.4 * p), 0.8, 0.2))


def whoosh_big(seed=9):
    """Big whoosh into a chapter card, with a sub thump at its peak."""
    w = whoosh(1.1, 220, 1900, seed)
    tt = _t(len(w) / SR)
    th = np.sin(2 * np.pi * 52 * tt) * np.exp(-np.maximum(tt - 0.66, 0) / 0.25) * (tt > 0.66)
    return _norm(w + 0.6 * _st(th))


def flare(seed=10):
    """Shimmer for a warm light-flare transition: bright partials + air, long tail."""
    tt = _t(1.4)
    r = _rng(seed)
    env = np.minimum(1, tt / 0.08) * np.exp(-tt / 0.45)
    x = sum(np.sin(2 * np.pi * f * tt + r.random() * 6.28) for f in r.uniform(1800, 7000, 12)) / 12
    air = _hp(r.normal(0, 1, len(tt)), 5000) * 0.25
    return _norm(_reverb((x + air) * env, 2.2, 0.35))


def sting(seed=11):
    """Title sting: a soft impact and a minor chord swelling open (A1 A2 E3 A3 C4)."""
    tt = _t(4.5)
    chord = sum(_saw(f, tt, 8) * g for f, g in ((55, 1.0), (110, 0.8), (164.81, 0.6), (220, 0.5), (261.63, 0.35)))
    chord = _sweep(chord, 300 * (2600 / 300) ** np.concatenate([np.linspace(0, 1, 20), np.ones(30), np.linspace(1, 0.4, 14)]), bw=1.6)
    env = np.minimum(1, tt / 0.25) * np.exp(-np.maximum(tt - 0.6, 0) / 1.6)
    x = _st(chord * env) * 0.55 + impact(seed)[:len(tt)] * 0.6
    return _norm(_reverb(x, 3.5, 0.35))


def hiss(d=3.0, seed=12):
    """Radio-antenna hiss: band-limited noise with faint crackle, swelling in and fading out (video 04's 1964 antenna)."""
    tt = _t(d)
    r = _rng(seed)
    x = _bp(r.normal(0, 1, len(tt)), 900, 7000) * 0.8 + _lp(r.normal(0, 1, len(tt)), 400) * 0.3
    crack = (r.random(len(tt)) > 0.9993) * r.normal(0, 4, len(tt))
    x = x + _bp(crack, 1500, 8000)
    env = np.minimum(1, tt / (d * 0.3)) * np.minimum(1, (d - tt) / (d * 0.35))
    return _norm(_st(x * env, 0.0))


KIT = {"tick": tick, "pop": pop, "roll": roll, "hit": hit, "impact": impact, "boom": impact, "sub_drop": sub_drop,
       "riser": riser, "whoosh": whoosh, "whoosh_big": whoosh_big, "flare": flare, "sting": sting, "hiss": hiss}
_CACHE = {}


def make(kind, **kw):
    key = (kind, tuple(sorted((k, round(v, 3) if isinstance(v, float) else v) for k, v in kw.items())))
    if key not in _CACHE:
        x = KIT[kind](**kw)
        _CACHE[key] = (x, peak_loudness(x))
    return _CACHE[key]


if __name__ == "__main__":
    import soundfile as sf
    parts = []
    for k in ("tick", "pop", "roll", "hit", "impact", "sub_drop", "riser", "whoosh", "whoosh_big", "flare", "sting"):
        x, pl = make(k)
        x = x * 10 ** ((-20 + LEVEL[k] - pl) / 20)
        parts += [x, np.zeros((int(0.6 * SR), 2))]
        print(f"{k:10s} {len(x) / SR:4.2f}s  peak loudness {pl:6.1f} LUFS")
    sf.write(sys.argv[1], np.concatenate(parts).astype(np.float32), SR)
