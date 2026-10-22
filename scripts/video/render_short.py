"""YouTube Shorts (1080x1920) cut from a finished v3 video: the hook line first, then the story, then an end card.

  python render_short.py <shorts.spec> <cutlist.json> <master_work_dir> <sources.json> <clips_dir> <music_dir>
                         <fonts_dir> <assets_dir> <out_dir> [--only <id>] [--workers 4]

shorts.spec, one block per Short. Lines are found by the start of their English C caption in the cut list:
  == <id> | <YouTube title>
  hook: <caption start>                        the line that opens the Short (best: one with a number card)
  body: <caption start> .. <caption start>     a run of lines in story order (the hook line is left out of it)
  body: ...                                    further runs are joined in order

A Short re-uses the long video's reviewed plan - its cuts, shots, camera moves, headlines, number cards and sound
design - re-timed onto the Short's own clock. Each shot is fetched again from its 4K source and framed 9:16 around
its brightest subject. Audio: the master's voice stem, a fresh bed of the section's music track, the plan's sounds.
It ends on FULL VIDEO BELOW, written on screen only: the narration never addresses the viewer (channel rule).
The full video is linked with YouTube Studio's "Related video" field (links in a Short's description don't click).
Writes <out_dir>/<id>.mp4, <id>.en.srt and <id>.plan.json; 4K shot crops are cached in <out_dir>/vclips/.
"""
import argparse, copy, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
import numpy as np, cv2

sys.path.insert(0, os.path.dirname(__file__))
import render_video as rv  # noqa: E402
import render_v2  # noqa: E402
import render_v3 as r3  # noqa: E402
import mograph as mg  # noqa: E402
import grade as grade_mod  # noqa: E402
import sfx as fx  # noqa: E402

SW, SH, FPS, SR = 1080, 1920, r3.FPS, r3.SR
END = 2.6           # end card length (s)
SLIVER = 0.4        # a shot piece shorter than this at a join is given to its neighbour
GEOMETRY = ("callout", "route", "hud")  # overlays pinned to positions in the 16:9 frame: left out of Shorts


def parse_spec(path):
    shorts, cur = [], None
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("=="):
            sid, _, title = ln[2:].partition("|")
            cur = {"id": sid.strip(), "title": title.strip(), "hook": None, "body": []}
            shorts.append(cur)
        elif ln.startswith("hook:"):
            cur["hook"] = ln[5:].strip()
        elif ln.startswith("body:"):
            a, _, b = ln[5:].partition("..")
            cur["body"].append((a.strip(), (b or a).strip()))
    return shorts


class Lines:
    """Spoken sentences of the master (non-big C captions) with cut points snapped into the pause before each."""

    def __init__(self, P, voice):
        self.caps = sorted([c for c in P["caps"] if not c.get("big")], key=lambda c: c["t"])
        self.cards = sorted(it["t0"] for it in P["items"] if it["kind"] in ("card", "title"))
        self.items = P["items"]
        k = int(0.02 * SR)
        self.env = np.convolve(np.abs(voice), np.ones(k) / k, "same")

    def find(self, prefix):
        hits = [i for i, c in enumerate(self.caps) if c["text"].strip('"').lower().startswith(prefix.lower())]
        if len(hits) != 1:
            raise SystemExit(f"caption start {prefix!r} matches {len(hits)} lines: make it longer")
        return hits[0]

    def snap(self, t):
        """Quietest 20 ms just before a sentence starts: the cut lands in the pause."""
        i0, i1 = int((t - 0.35) * SR), int((t - 0.02) * SR)
        return t if i1 <= i0 else (i0 + int(np.argmin(self.env[i0:i1]))) / SR

    def span(self, i):
        c = self.caps[i]
        a = self.snap(c["t"])
        for it in self.items:  # never start inside a chapter/title card
            if it["kind"] in ("card", "title") and it["t0"] <= a < it["t1"]:
                a = it["t1"]
        nxt_card = next((t for t in self.cards if t > c["t"]), 1e9)
        b = min(c.get("end", 1e9) + 0.45, nxt_card)
        if i + 1 < len(self.caps) and self.caps[i + 1]["t"] < b:
            b = self.snap(self.caps[i + 1]["t"])
        return a, b


def segments(spec, L):
    """[(a, b), ...] on the master's clock: the hook, then each body run with the hook line taken out."""
    h = L.find(spec["hook"])
    segs = [L.span(h)]
    for a_txt, b_txt in spec["body"]:
        i, j = L.find(a_txt), L.find(b_txt)
        run = []
        for k in range(i, j + 1):
            if k == h:
                if run:
                    segs.append((run[0][0], run[-1][1]))
                run = []
                continue
            run.append(L.span(k))
        if run:
            segs.append((run[0][0], run[-1][1]))
    return segs


def shift_ovl(o, d, a, b):
    o = copy.deepcopy(o)
    for key in ("t0", "t1", "t_last", "kicker_t", "sub_t"):
        if key in o:
            o[key] = (min(o[key], b) if key == "t1" else max(o[key], a) if key == "t0" else o[key]) + d
    for ln in o.get("lines", []):
        ln["t"] += d
    return o


def build(spec, P, L):
    segs = segments(spec, L)
    items, ovl, sfx, mus, caps, T = [], [], [], [], [], 0.0
    for si, (a, b) in enumerate(segs):
        d = T - a
        pcs = [[it, max(a, it["t0"]), min(b, it["t1"])] for it in P["items"]
               if it["kind"] not in ("card", "title") and min(b, it["t1"]) - max(a, it["t0"]) > 0.01]
        k = 0
        while len(pcs) > 1 and k < len(pcs):  # no one-frame flashes at the joins
            if pcs[k][2] - pcs[k][1] < SLIVER:
                if k == 0:
                    pcs[1][1] = pcs[0][1]
                else:
                    pcs[k - 1][2] = pcs[k][2]
                pcs.pop(k)
            else:
                k += 1
        for n, (it, x0, x1) in enumerate(pcs):
            new = {k_: v for k_, v in it.items() if k_ not in ("f0", "f1", "_rd")}
            new.update(t0=x0 + d, t1=x1 + d, src_off=max(0.0, it.get("ss", 0.0) + (x0 - it["t0"])), long_t0=x0)
            if n == 0:
                new["trans"] = "flare" if si == 1 else "cut"
            if it["kind"] == "num" and x0 > it["t0"]:
                new["num"] = dict(it["num"], land_t=it["num"].get("land_t", 1.3) - (x0 - it["t0"]))
            items.append(new)
        for o in P["ovl"]:
            if o["kind"] == "footer" or not (a - 0.4 <= o["t0"] < b - 0.3):  # a line's first word can lead the cut
                continue
            if o["kind"] == "num" and o["num"].get("template") in GEOMETRY:
                print(f"  {spec['id']}: left out {o['num']['template']} overlay at {o['t0']:.1f}s (16:9 geometry)")
                continue
            o = shift_ovl(o, d, a, b)
            if o["kind"] == "headline":
                o["pos"] = "center"
            ovl.append(o)
        sfx += [[e[0], e[1] + d] + list(e[2:]) for e in P["sfx"] if a - 0.02 <= e[1] < b - 0.05]
        mus += [dict(e, t0=e["t0"] + d, t1=min(e["t1"], b) + d, **({"peak": e["peak"] + d} if "peak" in e else {}))
                for e in P["mus"] if a <= e["t0"] < b]
        caps += [dict(c, t=c["t"] + d, t1=min(c["t1"], b) + d) for c in P["caps"] if a <= c["t"] < b]
        if si == 1:
            sfx.append(["whoosh", T - 0.25, 0])
        T += b - a
    items[-1]["t1"] = T + END
    ovl.append({"kind": "endcard", "t0": T + 0.05, "t1": T + END})
    sfx += [["hit", 0.0, -4], ["whoosh", T - 0.2, -2], ["pop", T + 0.05, 2]]
    a_body = segs[1][0] if len(segs) > 1 else segs[0][0]
    track = [c for c in P["music"] if c["t"] <= a_body][-1]
    total = T + END
    for it in items:
        it["f0"], it["f1"] = round(it["t0"] * FPS), round(it["t1"] * FPS)
    items[-1]["f1"] = round(total * FPS)
    return segs, {"style": "v3", "items": items, "ovl": ovl, "caps": caps, "sfx": sorted(sfx, key=lambda e: e[1]),
                  "mus": mus, "music": [{"t": 0.0, "track": track["track"], "gain": track.get("gain", 0.0)}],
                  "breaths": [], "total": total, "off": 0.0, "grade": P.get("grade", {})}


def subject_x(clip_path, t0, dur, crop):
    """Horizontal centre (0-1 of the crop region) of the brightest subject over the shot."""
    cap = cv2.VideoCapture(clip_path)
    xs = []
    for q in (0.15, 0.5, 0.85):
        cap.set(cv2.CAP_PROP_POS_MSEC, (t0 + dur * q) * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        x0, y0, x1, y1 = crop
        g = cv2.cvtColor(f[int(y0 * 1080):int(y1 * 1080), int(x0 * 1920):int(x1 * 1920)], cv2.COLOR_BGR2GRAY)
        g = cv2.GaussianBlur(cv2.resize(g, (192, 108)), (0, 0), 4).astype(np.float32) / 255
        w = g ** 3
        if w.sum() > 1e-3:
            xs.append(float((w.sum(0) * np.arange(w.shape[1])).sum() / w.sum() / (w.shape[1] - 1)))
    cap.release()
    return float(np.median(xs)) if xs else 0.5


def vclip(job):
    """Fetch the shot from its 4K source and cut the 9:16 window (falls back to the 1080p library clip)."""
    out, src, clip_path, t_lib, dur, crop, cx = job
    if os.path.exists(out):
        return out, "have"
    x0, y0, x1, y1 = crop
    rw, rh = (x1 - x0), (y1 - y0)
    win = min(1.0, rh * 9 / 16 * (1080 / 1920) / rw)  # window width as a fraction of the region width
    wx = min(max(cx - win / 2, 0.0), 1.0 - win)

    def vf(Wf, Hf):
        ew = lambda v: int(v) // 2 * 2  # noqa: E731
        return (f"scale={Wf}:{Hf}:force_original_aspect_ratio=increase:flags=bicubic,crop={Wf}:{Hf},"
                f"crop={ew(rw * Wf)}:{ew(rh * Hf)}:{ew(x0 * Wf)}:{ew(y0 * Hf)},"
                f"crop={ew(win * rw * Wf)}:{ew(rh * Hf)}:{ew(wx * rw * Wf)}:0,scale={SW}:{SH}:flags=lanczos,fps={FPS}")
    enc = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-g", "30", out + ".part.mp4"]
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src['ss'] + t_lib:.3f}", "-t", f"{dur:.3f}", "-i", src["url"],
                        "-vf", vf(3840, 2160)] + enc, capture_output=True, text=True)
    how = "4k"
    if r.returncode or not os.path.exists(out + ".part.mp4") or os.path.getsize(out + ".part.mp4") < 5000:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t_lib:.3f}", "-t", f"{dur:.3f}", "-i", clip_path,
                        "-vf", vf(1920, 1080)] + enc, check=True)
        how = "1080p fallback: " + r.stderr.strip()[:80]
    os.replace(out + ".part.mp4", out)
    return out, how


def cut(v, x, y):
    """Voice from x to y (s) with 10 ms fades: joins sit in pauses, the fades only stop clicks."""
    s = v[int(x * SR):int(y * SR)].copy()
    n = min(int(0.01 * SR), len(s) // 2)
    s[:n] *= np.linspace(0, 1, n)
    s[len(s) - n:] *= np.linspace(1, 0, n)
    return s


def set_canvas():
    for m in (rv, render_v2, r3, mg, grade_mod):
        m.W, m.H = SW, SH
    mg.LAYOUT.update(name_y=0.62, logo="left", logo_y=120, label_w=0.9)  # clear of the Shorts buttons and title
    r3.G.update(fade_in=0, fade_out=0)


def _worker_init(*args):
    set_canvas()
    r3.init(*args)


def render(sid, Ps, voice_wav, a, out_dir):
    work = os.path.join(out_dir, f"{sid}_work")
    total_f = round(Ps["total"] * FPS)
    step = 10 * FPS
    jobs = [(c, min(c + step, total_f), Ps["items"], Ps["ovl"], total_f, os.path.join(work, f"s_{c:06d}_{min(c + step, total_f):06d}.mp4"))
            for c in range(0, total_f, step)]
    for j in jobs:  # the plan may have changed since the last run
        if os.path.exists(j[5]):
            os.remove(j[5])
    # fresh worker processes: forking after OpenCV has run in this one can deadlock its thread pool
    with mp.get_context("spawn").Pool(a.workers, initializer=_worker_init,
                                      initargs=(Ps["clips_dir"], a.fonts, a.assets, Ps["grade"])) as pool:
        for k, pth in enumerate(pool.imap(r3.render_chunk, jobs)):
            print(f"  [{k + 1}/{len(jobs)}] {os.path.basename(pth)}", flush=True)
    import soundfile as sf
    out, _, Vm = r3.mix(voice_wav, Ps, a.music)
    _, I = fx.loudness(out)
    out *= 10 ** ((-14.0 - I) / 20)
    wav = os.path.join(work, "mix.wav")
    sf.write(wav, out.astype(np.float32), SR, subtype="FLOAT")
    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.basename(j[5])}'\n" for j in jobs))
    mp4 = os.path.join(out_dir, f"{sid}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "alimiter=limit=0.84:attack=3:release=80:level=false", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-t", f"{Ps['total']:.3f}", "-movflags", "+faststart", mp4], check=True)
    r3.write_srt(Ps["caps"], os.path.join(out_dir, f"{sid}.en.srt"))
    return mp4, Vm


def main():
    ap = argparse.ArgumentParser()
    for x in ("spec", "cutlist", "master_work", "sources", "clips", "music", "fonts", "assets", "out"):
        ap.add_argument(x)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    import soundfile as sf
    P = json.load(open(a.cutlist))
    sources = json.load(open(a.sources))
    voice, sr = sf.read(os.path.join(a.master_work, "stem_voice.wav"), always_2d=True)
    voice = voice.mean(1)
    assert sr == SR, f"voice stem at {sr} Hz"
    L = Lines(P, voice)
    vdir = os.path.join(a.out, "vclips")
    os.makedirs(vdir, exist_ok=True)
    set_canvas()
    for spec in parse_spec(a.spec):
        if a.only and spec["id"] != a.only:
            continue
        sid = spec["id"]
        segs, Ps = build(spec, P, L)
        os.makedirs(os.path.join(a.out, f"{sid}_work"), exist_ok=True)
        print(f"{sid}: {Ps['total']:.1f}s from {', '.join(f'{x:.1f}-{y:.1f}' for x, y in segs)} (master s); "
              f"{len(Ps['items'])} shots, {len(Ps['ovl'])} overlays")
        jobs = []
        for n, it in enumerate(Ps["items"]):
            crop = it.get("crop") or [0.0, 0.0, 1.0, 1.0]
            clip_path = os.path.join(a.clips, it["clip"] + ".mp4")
            dur = it["t1"] - it["t0"] + 1.2  # margin: the outgoing shot keeps playing through a transition
            cx = 0.5 if it["kind"] != "clip" else subject_x(clip_path, it["src_off"], it["t1"] - it["t0"], crop)
            name = f"{it['clip']}@{it['src_off']:.2f}+{dur:.2f}" + (f"c{'_'.join(f'{v:g}' for v in crop)}" if it.get("crop") else "")
            jobs.append((os.path.join(vdir, re.sub(r"[^\w@.+-]", "_", name) + ".mp4"), sources[it["clip"]], clip_path,
                         it["src_off"], dur, crop, cx))
            it["vclip"] = os.path.splitext(os.path.basename(jobs[-1][0]))[0]
        with ThreadPoolExecutor(4) as ex:
            for out, how in ex.map(vclip, jobs):
                if how not in ("have", "4k"):
                    print(f"  {os.path.basename(out)}: {how}")
        for it in Ps["items"]:
            it.update(clip=it["vclip"], ss=0.0, crop=None)
        Ps["clips_dir"] = os.path.abspath(vdir)
        voice_wav = os.path.join(a.out, f"{sid}_work", "voice.wav")
        v = np.concatenate([cut(voice, x, y) for x, y in segs] + [np.zeros(int(END * SR))])
        sf.write(voice_wav, v.astype(np.float32), SR)
        json.dump({**Ps, "id": sid, "title": spec["title"], "segments": segs}, open(os.path.join(a.out, f"{sid}.plan.json"), "w"),
                  indent=1, ensure_ascii=False)
        mp4, Vm = render(sid, Ps, voice_wav, a, a.out)
        print(f"wrote {mp4} ({Ps['total']:.1f}s, voice {Vm:.1f} LUFS)")


if __name__ == "__main__":
    main()
