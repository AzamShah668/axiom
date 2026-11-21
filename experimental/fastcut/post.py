"""Fast-cut post pass (separate project): background sound design, intense moments, black-and-white mood beats and
camera shake on top of a finished render. Cues are written as narration triggers in <video>/post.json.

  python experimental/fastcut/post.py <master.mp4> <timeline.json> <post.json> <out.mp4> [--lead 0.5]

post.json:
  {"ambience": {"gain_db": -30},
   "foley":   [{"kind": "crowd|boil|crackle|traffic|ticks|slow_ticks|boing|shatter|heartbeat|door|plop|wind", "sec": "ch1",
                "from": "<trigger>", "to": "<trigger>|+<seconds>", "gain_db": -24}, ...],
   "moments": [{"sec": "ch2", "at": "<trigger>", "build": 2.5, "gain_db": -6}, ...],   # riser+heartbeat -> impact+sub drop+shake
   "bw":      [{"sec": "ch2", "from": "<trigger>", "to": "<trigger>|+s"}, ...]}
Uses scripts/video/sfx.py read-only (its generators); nothing in the main pipeline is changed.
"""
import json, os, subprocess, sys, tempfile
import numpy as np
import soundfile as sf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "video"))
import sfx  # noqa: E402

SR = 44100
a = sys.argv[1:]
master, tlp, postp, out = a[:4]
lead = float(a[a.index("--lead") + 1]) if "--lead" in a else 0.5
tl = json.load(open(tlp))
P = json.load(open(postp))
S = {s["id"]: s for s in tl["sections"]}
rng = np.random.default_rng(10)


def when(sec, trg, after=None):
    s = S[sec]
    if trg == "-":
        return s["start"] + lead
    if trg.startswith("+"):
        return after + float(trg[1:])
    txt = "".join(s["chars"])
    i = txt.find(trg)
    if i < 0:
        raise SystemExit(f"post.json: '{trg}' not found in {sec}")
    return s["char_start"][i] + lead


def db(x):
    return 10 ** (x / 20)


def env(n, att=0.05, rel=0.3):
    e = np.ones(n)
    k1, k2 = min(n, int(att * SR)), min(n, int(rel * SR))
    if k1: e[:k1] = np.linspace(0, 1, k1)
    if k2: e[-k2:] = np.minimum(e[-k2:], np.linspace(1, 0, k2))
    return e


def lp(x, k):  # one-pole low-pass, k in (0,1): smaller = darker
    from scipy.signal import lfilter
    return lfilter([k], [1, -(1 - k)], x)


def noise(d):
    return rng.standard_normal(int(d * SR))


def band(x, lo_k, hi_k):  # crude band-pass: low-pass minus a darker low-pass
    return lp(x, hi_k) - lp(x, lo_k)


# ------------------------------------------------------------------ foley generators (procedural, no samples)
def g_ambience(d):
    t = np.arange(int(d * SR)) / SR
    pad = sum(amp * np.sin(2 * np.pi * f * t + 1.7 * np.sin(2 * np.pi * lfo * t))
              for f, amp, lfo in [(41.2, 1, .05), (55, .7, .031), (61.7, .4, .043), (82.4, .25, .021)])
    rumble = lp(noise(d), 0.004) * 6
    wind = band(noise(d), 0.01, 0.06) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.04 * t + 1)) * 2.5
    x = pad * 0.35 + rumble + wind
    return x / (np.abs(x).max() + 1e-9)


def g_crowd(d):
    t = np.arange(int(d * SR)) / SR
    x = band(noise(d), 0.03, 0.25) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t) ** 2)
    x[-int(min(d, 1.5) * SR):] *= np.linspace(1, 2.2, int(min(d, 1.5) * SR))  # cheer swell at the end
    return x / (np.abs(x).max() + 1e-9)


def g_boil(d):
    x = np.zeros(int(d * SR))
    for _ in range(int(d * 45)):
        i = rng.integers(0, len(x) - 2000); n = rng.integers(300, 1600)
        f = rng.uniform(200, 900); tt = np.arange(n) / SR
        x[i:i + n] += np.sin(2 * np.pi * f * tt * (1 + 3 * tt)) * np.exp(-tt * 40) * rng.uniform(.3, 1)
    x += band(noise(d), 0.05, 0.4) * 0.08  # gas burner hiss
    return x / (np.abs(x).max() + 1e-9)


def g_crackle(d):
    x = band(noise(d), 0.1, 0.6) * 0.15
    for _ in range(int(d * 120)):
        i = rng.integers(0, len(x) - 400)
        x[i:i + 200] += rng.standard_normal(200) * np.exp(-np.arange(200) / 30) * rng.uniform(.4, 1.2)
    return x / (np.abs(x).max() + 1e-9)


def g_traffic(d):
    t = np.arange(int(d * SR)) / SR
    x = lp(noise(d), 0.01) * 3 + band(noise(d), 0.02, 0.1) * 0.6   # engines
    for _ in range(max(2, int(d * 1.6))):  # horns
        i = rng.integers(0, max(1, len(x) - int(.6 * SR))); n = int(rng.uniform(.25, .6) * SR); tt = np.arange(n) / SR
        f = rng.choice([370, 415, 466, 523])
        h = np.sign(np.sin(2 * np.pi * f * tt)) * 0.5 + np.sin(2 * np.pi * f * 1.26 * tt) * 0.5
        x[i:i + n] += lp(h, 0.2) * env(n, .01, .05) * 0.9
    return x / (np.abs(x).max() + 1e-9)


def g_ticks(d, every=1.0):
    x = np.zeros(int(d * SR))
    tk, _ = sfx.make("tick")
    for b in np.arange(0.05, d - 0.1, every):
        i = int(b * SR); n = min(len(tk), len(x) - i); x[i:i + n] += tk[:n]
    return x / (np.abs(x).max() + 1e-9)


def g_boing(d):
    n = int(min(d, 1.2) * SR); tt = np.arange(n) / SR
    f = 180 + 420 * np.exp(-tt * 6)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.5) * (1 + 0.3 * np.sin(2 * np.pi * 9 * tt))
    out = np.zeros(int(d * SR)); out[:n] = x
    return out


def g_shatter(d):
    n = int(min(d, 1.4) * SR); tt = np.arange(n) / SR
    x = band(rng.standard_normal(n), 0.15, 0.9) * np.exp(-tt * 4)
    for _ in range(60):
        i = rng.integers(0, n - 3000); f = rng.uniform(2500, 7000); m = 2500
        x[i:i + m] += np.sin(2 * np.pi * f * np.arange(m) / SR) * np.exp(-np.arange(m) / 400) * 0.3
    out = np.zeros(int(d * SR)); out[:n] = x
    return out / (np.abs(out).max() + 1e-9)


def g_heartbeat(d, bpm=72):
    x = np.zeros(int(d * SR)); per = 60 / bpm
    for b in np.arange(0.0, d - 0.3, per):
        for off, amp in ((0, 1.0), (0.22, 0.7)):
            i = int((b + off) * SR); n = min(int(.18 * SR), len(x) - i); tt = np.arange(n) / SR
            x[i:i + n] += np.sin(2 * np.pi * (55 - 30 * tt) * tt) * np.exp(-tt * 22) * amp
    return x / (np.abs(x).max() + 1e-9)


def g_door(d):
    x, _ = sfx.make("kz_thud"); out = np.zeros(int(d * SR)); n = min(len(x), len(out)); out[:n] = x[:n]
    return out


def g_plop(d):
    n = int(.35 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * np.cumsum(900 * np.exp(-tt * 18) + 300) / SR) * np.exp(-tt * 14)
    out = np.zeros(int(d * SR)); out[:min(n, len(out))] = x[:len(out)]
    return out


def g_wind(d):
    t = np.arange(int(d * SR)) / SR
    x = band(noise(d), 0.006, 0.05) * (0.4 + 0.6 * np.sin(2 * np.pi * 0.25 * t) ** 2)
    return x / (np.abs(x).max() + 1e-9)


GEN = {"crowd": g_crowd, "boil": g_boil, "crackle": g_crackle, "traffic": g_traffic, "ticks": g_ticks,
       "slow_ticks": lambda d: g_ticks(d, 2.2), "fast_ticks": lambda d: g_ticks(d, 0.25), "boing": g_boing, "shatter": g_shatter, "heartbeat": g_heartbeat,
       "door": g_door, "plop": g_plop, "wind": g_wind}

# ------------------------------------------------------------------ build the layer
tmp = tempfile.mkdtemp(prefix="fastcut-post-")
base_wav = os.path.join(tmp, "base.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vn", "-ac", "2", "-ar", str(SR), base_wav], check=True)
base, _ = sf.read(base_wav)
N = len(base)
layer = np.zeros(N)


def add(x, t0, g):
    i = int(t0 * SR)
    if i >= N: return
    n = min(len(x), N - i)
    layer[i:i + n] += x[:n] * g


D = N / SR
amb = P.get("ambience", {})
if amb:
    add(g_ambience(D) * env(N, 2.0, 2.0), 0.0, db(amb.get("gain_db", -30)))
for f in P.get("foley", []):
    t0 = when(f["sec"], f["from"]); t1 = when(f["sec"], f["to"], t0)
    d = max(0.3, t1 - t0)
    x = GEN[f["kind"]](d)
    add(x * env(len(x), 0.08, 0.25), t0, db(f.get("gain_db", -24)))
shake = []
for m in P.get("moments", []):
    t = when(m["sec"], m["at"]); b = m.get("build", 2.5); g = db(m.get("gain_db", -6))
    r, _ = sfx.make("riser", d=b); add(r / (np.abs(r).max() + 1e-9), t - b, g * 0.55)
    add(g_heartbeat(b, 84) * np.linspace(0.3, 1, int(b * SR)), t - b, g * 0.5)
    for k, gg in (("bass_impact", 1.0), ("impact", 0.7), ("sub_drop", 0.9)):
        x, _ = sfx.make(k); add(x / (np.abs(x).max() + 1e-9), t, g * gg)
    shake.append((t, t + m.get("shake", 0.6)))
mix = base + np.repeat(layer[:, None], 2, 1)
mix_wav = os.path.join(tmp, "mix.wav")
sf.write(mix_wav, np.clip(mix, -1, 1), SR)

# ------------------------------------------------------------------ video: black-and-white beats and shake
vf = []
bw = [(when(b["sec"], b["from"]), None, b) for b in P.get("bw", [])]
bw = [(t0, when(b["sec"], b["to"], t0)) for t0, _, b in bw]
if bw:
    cond = "+".join(f"between(t,{x:.2f},{y:.2f})" for x, y in bw)
    vf.append(f"hue=s=0:enable='{cond}'")
if shake:
    dx = "+".join(f"if(between(t,{x:.2f},{y:.2f}),26*sin(91*t)*exp(-7*(t-{x:.2f})),0)" for x, y in shake)
    dy = "+".join(f"if(between(t,{x:.2f},{y:.2f}),20*sin(67*t+1)*exp(-7*(t-{x:.2f})),0)" for x, y in shake)
    vf.append(f"scale=2016:1134,crop=1920:1080:x='48+({dx})':y='27+({dy})'")
cmd = ["ffmpeg", "-v", "error", "-y", "-i", master, "-i", mix_wav, "-map", "0:v", "-map", "1:a"]
cmd += (["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"] if vf else ["-c:v", "copy"])
cmd += ["-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True)
print("wrote", out, f"{len(P.get('foley', []))} foley, {len(shake)} moments, {len(bw)} b&w beats")
