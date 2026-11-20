"""09 Short "crunch" v2 (owner 2026-11-20: "the motion graphics are awful... use every capability of motion graphics,
smooth and engaging"). Built on space3d.py: a 3D camera through a field of procedural spiral galaxies whose cosmic
scale factor follows the words, a glossy rubber band, a Big Crunch with shockwave/flare/aberration, squeezed light.

  python short_crunch.py <timeline.json> <voice.wav> <captions.txt> <music.mp3> <fonts_dir> <out.mp4>
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import space3d as X        # noqa: E402
import short_motion as SM  # noqa: E402  (words, timing, audio helpers)
import sfx as fx           # noqa: E402

W, H, FPS = X.W, X.H, 30
AMBER = (66, 194, 245)
cl, ss, eo, ei, eio, back = X.cl, X.ss, X.eo, X.ei, X.eio, X.back
G = {}


def timing(wd):
    SM.PLAN = SM.PLANS["crunch"]
    return SM.build_timing(wd)


def scale_factor(t, st, ev):
    """The universe's scale factor a(t) for the galaxy world, following the words."""
    if t < st[1]:                                              # "poora universe shrink hone lage"
        return 1.0 - 0.38 * ei(cl((t - ev["shrink"] + 0.9) / 2.2))
    if t < st[4]:                                              # expansion slowing to a stop on "band"
        return 0.78 + 0.22 * eo(cl((t - st[3]) / max(0.5, ev["band"] - st[3])))
    if t < st[5]:                                              # coming back together
        return 1.0 - 0.3 * ei(cl((t - st[4]) / (st[5] - st[4])))
    if t < ev["bc"]:                                           # the crunch
        return 0.7 * (1 - ei(cl((t - st[5]) / (ev["bc"] - st[5])))) + 0.004
    return 0.004


def camera(t, shake=0.0):
    rng = np.random.default_rng(int(t * 30))
    sx, sy = (rng.normal(0, 1, 2) * shake * 18) if shake > 0 else (0, 0)
    return X.Cam(pos=(2.2 * math.sin(t * 0.17), 1.6 * math.cos(t * 0.13), 62 - 0.55 * t), yaw=0.05 * math.sin(t * 0.11),
                 pitch=0.04 * math.sin(t * 0.09), roll=0.06 * math.sin(t * 0.07), focal=1150, cx=W / 2 + sx, cy=H * 0.47 + sy)


def space_bg(t, cam, neb=1.0):
    f = np.zeros((H, W, 3), np.float32)
    nb = X.nebula(3, ((70, 25, 50), (150, 70, 40), (200, 140, 90)))
    off = int((t * 14) % W)
    f += nb[:, off:off + W] * 0.55 * neb
    X.draw_stars(f, cam, t)
    return f


# ------------------------------------------------------------------ shots
def world(t, st, ev, heat=0.0, amt=1.0, shake=0.0):
    cam = camera(t, shake)
    f = space_bg(t, cam)
    a, a0 = scale_factor(t, st, ev), scale_factor(t - 1.6 / FPS, st, ev)
    X.draw_galaxies(f, cam, a, t, amt, center=(0, 0, 0), heat=heat, blur_from=a0 if abs(a - a0) > 0.002 else None)
    if t < st[1]:                                              # the hero galaxy of the first shot, shrinking with space
        X.put(f, X.galaxy_sprite(4, 420), W / 2, H * 0.47, 1.9 * a ** 1.5, 25 + t * 8, amt, True, 0.62)
    return f, cam


def band_scene(t, st, ev, morph=None):
    """A glossy red rubber band between two pegs, two pearl-white spheres; stretch, release, wobble."""
    f = np.zeros((H, W, 3), np.float32)
    yy, xx = np.ogrid[:H, :W]
    if "spot" not in G:
        G["spot"] = (np.exp(-(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - H * 0.47) / (H * 0.30)) ** 2))[..., None]
                     * np.array([70, 40, 28], np.float32)).astype(np.float32)
    f += G["spot"] + 8
    rng = np.random.default_rng(3)                             # floating dust motes, slow parallax
    for i in range(70):
        x = (rng.uniform(0, W) + t * rng.uniform(4, 18)) % W
        y = (rng.uniform(0, H) - t * rng.uniform(2, 8)) % H
        X.glow(f, x, y, rng.uniform(1, 3), (200, 210, 230), rng.uniform(0.2, 0.6))
    cy = H * 0.50
    d0, d1 = 130, 320
    if ev["stretch"] <= t < ev["chhodo"]:
        d = d0 + (d1 - d0) * eio((t - ev["stretch"]) / max(0.5, ev["door"] - ev["stretch"] + 0.3))
        wob = 0.0
    elif t >= ev["chhodo"]:
        k = t - ev["chhodo"]
        d = d0 + (d1 - d0) * math.exp(-k * 3.0) * math.cos(k * 8)
        wob = 26 * math.exp(-k * 2.4)
    else:
        d = d0
        wob = 0.0
    zoom = 1.3 + 0.08 * (t - st[1]) / 7
    pegL, pegR = W / 2 - d * zoom, W / 2 + d * zoom   # the band ends ARE the two dots
    xs = np.linspace(pegL, pegR, 80)
    sag = (14 if d < 300 else 4) * zoom
    ys = cy + sag * np.sin(np.linspace(0, math.pi, 80)) + wob * np.sin(np.linspace(0, 3 * math.pi, 80) + t * 30) * np.sin(np.linspace(0, math.pi, 80))
    thick = max(6, int(30 * zoom * (d0 / d) ** 0.7))
    pts = np.stack([xs, ys], 1).astype(np.int32)
    lay = np.zeros((H, W, 3), np.float32)
    cv2.polylines(lay, [pts], False, (20, 25, 120), thick + 6, cv2.LINE_AA)           # dark edge
    cv2.polylines(lay, [pts], False, (40, 55, 215), thick, cv2.LINE_AA)               # rubber
    cv2.polylines(lay, [pts - np.array([0, thick // 4])], False, (140, 160, 255), max(2, thick // 5), cv2.LINE_AA)  # gloss
    msk = (lay.sum(-1, keepdims=True) > 0).astype(np.float32)
    f = f * (1 - msk) + lay
    f += cv2.GaussianBlur(lay, (0, 0), 14) * 0.25
    for sgn in (-1, 1):
        x = W / 2 + sgn * d * zoom
        y = cy + 40
        if morph is not None and t > morph - 0.15:
            p = eo((t - morph + 0.15) / 0.6)
            X.put(f, X.sphere_sprite((235, 240, 250), 200), x, y - 40, 0.45 * zoom * (1 - p), 0, 1 - p, add=False)
            X.put(f, X.galaxy_sprite(2 if sgn < 0 else 5), x, y - 40, 1.2 * p * zoom, 30 * sgn + t * 20, p, True, 0.75)
            X.glow(f, x, y - 40, 70, (220, 230, 255), 2.5 * math.exp(-(t - morph) * 5) if t > morph else 0)
        else:
            X.glow(f, x, y - 40, 60, (210, 220, 255), 0.35)
            X.put(f, X.sphere_sprite((235, 240, 250), 200), x, y - 40, 0.45 * zoom, 0, 1.0, add=False)
    return f


def crunch_shot(t, st, ev):
    bc = ev["bc"]
    shake = math.exp(-(t - bc) * 3) if t > bc else 0.0
    if t < bc:
        heat = ei(cl((t - st[5]) / (bc - st[5])))
        f, cam = world(t, st, ev, heat=heat)
        x, y, _, _ = cam.project(np.zeros((1, 3), np.float32))
        X.glow(f, x[0], y[0], 30 + 220 * heat, (190, 225, 255), 0.4 + 2.2 * heat)
        X.flare(f, x[0], y[0], heat * 0.6)
    else:
        cam = camera(t, shake)
        f = space_bg(t, cam, neb=0.5)
        u = t - bc
        x, y = W / 2, H * 0.47
        f += 255 * 1.6 * math.exp(-u * 5)
        X.shockwave(f, x, y, 80 + u * 1700, 18 + u * 30, math.exp(-u * 1.4))
        X.shockwave(f, x, y, 40 + u * 1100, 8, 0.6 * math.exp(-u * 2.0), (200, 220, 255))
        X.flare(f, x, y, 1.2 * math.exp(-u * 1.2))
        X.glow(f, x, y, 26, (255, 255, 255), 2.0)
        X.glow(f, x, y, 140, (150, 200, 255), 0.6)
    X.ktext(f, "BIG CRUNCH", W / 2, H * 0.25, 150, (255, 255, 255), t, bc + 0.05)
    if t > bc + 0.5:
        u = cl((t - bc - 0.5) / max(0.4, ev["crore"] - bc - 0.5))
        n = int(round(20 * eio(u)))
        X.ktext(f, f"{n} BILLION YEARS", W / 2, H * 0.66, 112, AMBER, t, bc + 0.5)
        X.ktext(f, "( 2,000 CRORE SAAL )", W / 2, H * 0.715, 50, (235, 235, 235), t, ev["crore"], "Montserrat", "Bold", 0.3)
    return X.chroma(f, 10 * shake)


def light_scene(t, st, ev):
    """A perspective grid of space that keeps shrinking, and a glowing light wave being squeezed bluer."""
    f = np.zeros((H, W, 3), np.float32)
    cam = camera(t)
    f += X.nebula(3, ((70, 25, 50), (150, 70, 40), (200, 140, 90)))[:, :W] * 0.35
    X.draw_stars(f, cam, t, 0.7)
    k = ei(cl((t - ev["light"] + 0.8) / 2.6))
    hor, cxp = H * 0.40, W / 2
    sp = 1.0 - 0.55 * k                                            # grid spacing shrinks with space
    lay = np.zeros((H, W, 3), np.float32)
    for i in range(-14, 15):
        x1 = cxp + i * 160 * sp * 4
        cv2.line(lay, (int(cxp + i * 160 * sp * 0.35), int(hor)), (int(x1), H), (150, 90, 50), 2, cv2.LINE_AA)
    for j in range(1, 22):
        z = (j * sp + (t * 0.8 % sp)) ** 1.6
        y = hor + z * 18
        if y < H:
            cv2.line(lay, (0, int(y)), (W, int(y)), (150, 90, 50), 2, cv2.LINE_AA)
    f += lay * 0.5
    lam = 430 * (1 - 0.72 * k)
    c = np.array([50, 70, 255]) * (1 - k) + np.array([255, 230, 190]) * k
    wav = np.zeros((H, W, 3), np.float32)
    xs = np.arange(-20, W + 20, 3)
    ys = H * 0.42 + 150 * np.sin(2 * math.pi * xs / lam - t * 7) * (0.8 + 0.2 * math.sin(t * 2))
    pts = np.stack([xs, ys], 1).astype(np.int32)
    cv2.polylines(wav, [pts], False, tuple(float(v) for v in c), 10, cv2.LINE_AA)
    f += cv2.GaussianBlur(wav, (0, 0), 22) * 1.6 + cv2.GaussianBlur(wav, (0, 0), 5) * 1.2 + wav * 0.9
    for j in range(8):                                             # photons riding the wave
        xp = (t * 260 + j * W / 8) % (W + 40) - 20
        X.glow(f, xp, H * 0.42 + 150 * math.sin(2 * math.pi * xp / lam - t * 7), 10, (255, 255, 255), 1.6)
    X.ktext(f, "LIGHT", W / 2, H * 0.28, 120, tuple(float(v) for v in c), t, ev["light"])
    X.ktext(f, "?", W / 2, H * 0.64, 300, AMBER, t, ev["kya"] + 0.15, glow_amt=1.0)
    return f


def end_scene(t, st, ev):
    f, cam = world(t, st, ev, amt=0.35)
    f *= 0.4
    t0 = st[7]
    X.ktext(f, "WATCH THE", W / 2, H * 0.40, 128, (255, 255, 255), t, t0)
    X.ktext(f, "FULL VIDEO", W / 2, H * 0.48, 160, AMBER, t, t0 + 0.15, glow_amt=1.0)
    p = eo((t - t0 - 0.35) / 0.4)
    y = H * 0.58 + 34 * math.sin((t - t0) * 6)
    lay = np.zeros((H, W, 3), np.float32)
    cv2.arrowedLine(lay, (W // 2, int(y)), (W // 2, int(y + 230)), AMBER, 16, cv2.LINE_AA, tipLength=0.35)
    f += (lay + cv2.GaussianBlur(lay, (0, 0), 12) * 1.2) * p
    return f


def scene(t, st, ev):
    i = max(k for k in range(len(st)) if st[k] <= t)
    if i in (1, 2):
        f = band_scene(t, st, ev, morph=ev["gal"] if i == 2 else None)
        if i == 1 and ev["stretch"] < t < ev["chhodo"]:
            X.ktext(f, "STRETCH", W / 2, H * 0.36, 110, (255, 255, 255), t, ev["stretch"], out=ev["chhodo"] - 0.1)
        if i == 1 and t >= ev["chhodo"]:
            X.ktext(f, "RELEASE", W / 2, H * 0.36, 110, AMBER, t, ev["chhodo"])
        if i == 2:
            X.ktext(f, "GALAXIES", W / 2, H * 0.36, 110, AMBER, t, ev["gal"])
            if t > st[3] - 0.9:                                   # pull back into the galaxy world
                p = eio((t - st[3] + 0.9) / 0.9)
                w, _ = world(t, st, ev, amt=p)
                f = f * (1 - p) + w * p
        return f
    if i == 5:
        return crunch_shot(t, st, ev)
    if i == 6:
        return light_scene(t, st, ev)
    if i == 7:
        return end_scene(t, st, ev)
    f, _ = world(t, st, ev)
    if i == 3:
        X.ktext(f, "EXPANSION STOPS", W / 2, H * 0.70, 96, (255, 255, 255), t, ev["band"])
    return f


def frame(t, st, ev, total, caps):
    i = max(k for k in range(len(st)) if st[k] <= t)
    f = scene(t, st, ev)
    if i > 0 and t - st[i] < 0.3 and i not in (2, 3):            # flash-zoom transition into each new shot
        p = (t - st[i]) / 0.3
        acc = np.zeros_like(f)
        for k in range(4):
            s = 1 + (1 - eo(p)) * 0.25 * (k + 1) / 4
            acc += cv2.warpAffine(f, cv2.getRotationMatrix2D((W / 2, H * 0.47), 0, s), (W, H), borderMode=cv2.BORDER_REFLECT)
        f = acc / 4 + 90 * (1 - p) ** 2
    top = np.linspace(0.75, 0, 420, dtype=np.float32)[:, None, None]  # title gradient band
    f[:420] *= 1 - top
    X.ktext(f, "WILL THE UNIVERSE", W / 2, 118, 86, (255, 255, 255), t, 0.0, glow_amt=0.2)
    X.ktext(f, "SHRINK BACK?", W / 2, 222, 112, AMBER, t, 0.12, glow_amt=0.5)
    if t < st[7]:
        cur = [(wt, w) for (wt, w) in caps if wt <= t]
        if cur:
            wt, w = cur[-1]
            X.ktext(f, w.upper().strip(",.?"), W / 2, H * 0.835, 112, AMBER, t, wt, glow_amt=0.4)
    cv2.rectangle(f, (0, H - 12), (int(W * min(1, t / total)), H), (66 * 1.5, 194 * 1.5, 245 * 1.5), -1)
    return X.post(f, t)


def _render_range(args):
    a, b, st, ev, total, caps, fonts, out = args
    X.FONTS["dir"] = fonts
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for k in range(a, b):
        ff.stdin.write(frame(k / FPS, st, ev, total, caps).tobytes())
    ff.stdin.close()
    ff.wait()
    return out


def main():
    tlp, voice, capf, music, fonts, out = sys.argv[1:7]
    speed, tail = 1.1, 1.6
    tl = json.load(open(tlp))
    wd = SM.words(tl, speed)
    roman = open(capf).read().split()
    caps = list(zip([t for t, _ in wd], roman))
    st, ev = timing(wd)
    total = tl["total"] / speed + tail
    work = os.path.splitext(out)[0] + "_work"
    os.makedirs(work, exist_ok=True)
    X.FONTS["dir"] = fonts
    n = int(total * FPS)
    k = 4
    jobs = [(i * n // k, (i + 1) * n // k, st, ev, total, caps, fonts, os.path.join(work, f"part{i}.mp4")) for i in range(k)]
    with Pool(k) as p:
        parts = p.map(_render_range, jobs)
    with open(os.path.join(work, "parts.txt"), "w") as fl:
        fl.writelines(f"file '{os.path.abspath(x)}'\n" for x in parts)
    vid = os.path.join(work, "video.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(work, "parts.txt"), "-c", "copy", vid], check=True)
    # audio: voice at speed, Darkest Child low, sound hits
    import soundfile as sf
    vw = os.path.join(work, "voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-af", f"atempo={speed},loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-ac", "1", vw], check=True)
    v, sr = sf.read(vw)
    N = int((total + 0.5) * sr)
    mix = np.zeros((N, 2), np.float32)
    mix[:min(len(v), N)] += np.repeat(v[:N, None], 2, 1)
    mw = os.path.join(work, "music.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "32", "-i", music, "-t", str(total + 0.5), "-af",
                    f"loudnorm=I=-30:TP=-6,afade=t=out:st={total - 1.2}:d=1.2", "-ar", "44100", "-ac", "2", mw], check=True)
    m, _ = sf.read(mw)
    mix[:len(m)] += m[:N]
    hits = [("kz_thud", 0.0, 0), ("kz_whoosh", ev["shrink"] - 0.3, -3), ("kz_whoosh", st[1] - 0.2, -2), ("kz_whoosh", ev["stretch"], -5),
            ("kz_thud", ev["chhodo"] + 0.05, -4), ("kz_shot", ev["gal"], -8), ("kz_whoosh", st[3] - 0.4, -2), ("kz_thud", ev["band"], -6),
            ("kz_whoosh", st[4] - 0.2, -4), ("riser", ev["bc"] - 1.4, -4), ("kz_shot", ev["bc"], 0), ("sub_drop", ev["bc"] + 0.05, -2),
            ("kz_thud", ev["crore"], -5), ("kz_whoosh", st[6] - 0.2, -3), ("kz_thud", ev["kya"] + 0.15, -6), ("bell", st[7] + 0.2, -6)]
    for kind, t0, g in hits:
        x, pl = fx.make(kind, d=1.4) if kind == "riser" else fx.make(kind)
        x = x * 10 ** ((-16 + fx.LEVEL.get(kind, -15) + g + 3 - pl) / 20)
        i = int(max(0, t0) * sr)
        mix[i:i + len(x)] += x[:max(0, N - i)]
    aw = os.path.join(work, "mix.wav")
    sf.write(aw, np.clip(mix * 10 ** (2 / 20), -1, 1), sr)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", aw, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", "loudnorm=I=-14:TP=-1.5", "-shortest", "-movflags", "+faststart", out], check=True)
    print("wrote", out, f"{total:.1f}s")


if __name__ == "__main__":
    main()
