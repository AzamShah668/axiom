"""Shorts rendered with the web3d engine (three.js + rapier + postprocessing in headless Chromium).
Owner's Shorts style: motion graphics only, plain text, one word caption, Darkest Child low, kz sound hits, voice at 1.1x.

  python scripts/video/short_web3d.py <scene> <timeline.json> <voice.wav> <captions.txt> <music.mp3> <out.mp4> [--workers 3] [--audio-only]

Each scene has a HITS entry here: (sfx kind, word index or 'sN' for shot N start, offset s, gain dB).
"""
import json, os, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import short_motion as SM  # noqa: E402  (word times)
import sfx as fx           # noqa: E402
import beats               # noqa: E402  (music offset so beats land on cuts)

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = {"blunder": [0, 15, 24, 35, 45, 54, 73, 84]}
HITS = {"blunder": [("kz_thud", 0, 0.0, 0), ("kz_shot", 5, 0.0, -2), ("riser", 12, -1.0, -6), ("kz_whoosh", "s1", -0.2, -3),
                    ("kz_thud", 16, 0.05, -6), ("kz_whoosh", "s2", -0.2, -3), ("kz_whoosh", "s3", -0.2, -3), ("sub_drop", 39, 0.0, -3),
                    ("kz_shot", 39, 0.0, -4), ("kz_whoosh", 42, 0.0, -8), ("kz_typing", 43, 0.1, -10), ("kz_whoosh", "s4", -0.2, -2),
                    ("kz_shot", 49, 0.0, -2), ("kz_whoosh", "s5", -0.2, -3), ("kz_scratch", 61, 0.0, -4), ("kz_thud", 66, 0.0, -4),
                    ("kz_whoosh", "s6", -0.2, -3), ("kz_thud", 83, 0.1, -5), ("bell", "s7", 0.2, -6)]}


def main():
    a = sys.argv[1:]
    scene, tlp, voice, capf, music, out = a[:6]
    workers = a[a.index("--workers") + 1] if "--workers" in a else "3"
    speed, tail = 1.1, 1.6
    tl = json.load(open(tlp))
    wd = SM.words(tl, speed)
    roman = open(capf).read().split()
    assert len(roman) == len(wd), f"captions have {len(roman)} words, voice has {len(wd)}"
    words = [[round(t, 3), r] for (t, _), r in zip(wd, roman)]
    total = tl["total"] / speed + tail
    work = os.path.splitext(out)[0] + "_work"
    os.makedirs(work, exist_ok=True)
    pj = os.path.join(work, "params.json")
    json.dump({"words": words}, open(pj, "w"))
    vid = os.path.join(work, "video.mp4")
    if not ("--audio-only" in a and os.path.exists(vid)):
        subprocess.run(["node", os.path.join(HERE, "web3d", "render_web3d.js"), scene, "--dur", f"{total:.3f}", "--fps", "30",
                        "--size", "1080x1920", "--workers", workers, "--params", "@" + pj, "--out", vid], check=True)
    # audio: voice at speed, Darkest Child low (start point picked so beats land on the cuts), sound hits on the words
    import soundfile as sf
    vw = os.path.join(work, "voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-af", f"atempo={speed},loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-ac", "1", vw], check=True)
    v, sr = sf.read(vw)
    N = int((total + 0.5) * sr)
    mix = np.zeros((N, 2), np.float32)
    mix[:min(len(v), N)] += np.repeat(v[:N, None], 2, 1)
    mw = os.path.join(work, "music.wav")
    shots = SHOTS[scene]
    moff, miss = beats.best_offset(music, [wd[k][0] for k in shots])
    print(f"music from {moff:.2f}s, cuts within {miss * 1000:.0f} ms of a beat")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(moff), "-i", music, "-t", str(total + 0.5), "-af",
                    f"loudnorm=I=-30:TP=-6,afade=t=out:st={total - 1.2}:d=1.2", "-ar", "44100", "-ac", "2", mw], check=True)
    m, _ = sf.read(mw)
    mix[:len(m)] += m[:N]
    for kind, at, off, g in HITS[scene]:
        t0 = (wd[shots[int(at[1:])]][0] if isinstance(at, str) else wd[at][0]) + off
        x, pl = fx.make(kind, d=1.0) if kind == "riser" else fx.make(kind)
        x = x * 10 ** ((-16 + fx.LEVEL.get(kind, -15) + g + 3 - pl) / 20)
        if x.ndim == 1:
            x = np.repeat(x[:, None], 2, 1)
        i = int(max(0, t0) * sr)
        n = max(0, min(len(x), N - i))
        mix[i:i + n] += x[:n]
    aw = os.path.join(work, "mix.wav")
    sf.write(aw, np.clip(mix * 10 ** (2 / 20), -1, 1), sr)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", aw, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", "loudnorm=I=-14:TP=-1.5", "-shortest", "-movflags", "+faststart", out], check=True)
    print("wrote", out, f"{total:.1f}s")


if __name__ == "__main__":
    main()
