"""Fast-cut documentary editor (v2): constant 4K-sourced footage, a scene every ~2.3 s,
a caption for every sentence, transitions between topics, music bed + SFX.

  python render_v2.py <edit.json> <timeline.json> <narration.wav> <clips_dir> <catalog.json>
                      <music_dir> <fonts_dir> <assets_dir> <out.mp4> [--check] [--only sec1,sec2] [--workers 4]

edit.json per section:
  "v": visual beats   [{"at": trigger|null, "pool": name} | {"at": ..., "gfx": name, "bg": pool}]
  "c": captions       [{"at": trigger|null, "text": "...", "big": true?}]
  "sfx": extra sounds [{"type": "boom", "at": trigger}]
Top level: "pools" {name: [clip, ...]}, "music" [{"from": section, "track": file}], "cards", "title_card",
"crops" {clip: [x0, y0, x1, y1]} (manual crop, overrides the one clip_qc.py chose),
"exclude" {clip: [[from_s, to_s], ...]} (manual cuts: insets, flashes, overlays the text scan can't see).
Each visual beat is split into scenes of ~SCENE_LEN seconds, each scene a fresh clean-range segment
of the next clip in the pool (clean = no burned-in text / black, from clip_qc.py).
"""
import argparse, json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np, cv2

sys.path.insert(0, os.path.dirname(__file__))
import render_video as rv  # noqa: E402  (text, glow and graphics helpers)

W, H, FPS, SR = rv.W, rv.H, rv.FPS, rv.SR
SCENE_LEN = 2.3
G = rv.G
TRANS = ["zoom", "flash", "whip", "blur"]


# ------------------------------------------------------------------ planning
def plan(edit, tl):
    off = edit.get("lead_in", 2.0)
    secs = {s["id"]: s for s in tl["sections"]}
    order = [s["id"] for s in tl["sections"]]
    total = tl["total"] + off + 3.0

    def t_of(sid, trig):
        if trig is None:
            return None
        s = secs[sid]
        text = "".join(s["chars"])
        i = text.find(trig)
        if i < 0:
            raise SystemExit(f"[{sid}] trigger not found: {trig!r}")
        return s["char_start"][i] + off

    items, caps, sfx = [], [], []
    trans_i = 0
    for k, sid in enumerate(order):
        s = secs[sid]
        start, end = s["start"] + off, s["end"] + off
        sec_end = end if k + 1 < len(order) else total
        first = 0.0 if k == 0 else start
        if sid in edit["cards"]:
            prev_end = secs[order[k - 1]]["end"] + off
            c0 = prev_end
            if k == 1:
                items.append({"kind": "title", "sec": sid, "t0": prev_end, "t1": prev_end + 2.6, "text": edit["title_card"], "pool": "space"})
                sfx += [("boom", prev_end + 0.05), ("whoosh_big", prev_end)]
                c0 = prev_end + 2.6
            items.append({"kind": "card", "sec": sid, "t0": c0, "t1": start + 0.9, "text": edit["cards"][sid], "pool": "space"})
            sfx.append(("whoosh_big", c0))
            first = start + 0.9
        spec = edit["sections"][sid]
        vb = spec["v"]
        t0s = [first] + [max(first, t_of(sid, b["at"])) for b in vb[1:]]
        for j, b in enumerate(vb):
            b0, b1 = t0s[j], (t0s[j + 1] if j + 1 < len(vb) else sec_end)
            if b1 - b0 < 0.4:
                continue
            tr = "cut" if j == 0 else TRANS[trans_i % len(TRANS)]
            if j:
                trans_i += 1
                sfx.append(("whoosh", b0))
            if "gfx" in b:
                items.append({"kind": "gfx", "sec": sid, "t0": b0, "t1": b1, "gfx": b["gfx"], "pool": b.get("bg", "space"), "trans": tr})
                continue
            n = max(1, round((b1 - b0) / SCENE_LEN))
            for q in range(n):
                items.append({"kind": "clip", "sec": sid, "t0": b0 + (b1 - b0) * q / n, "t1": b0 + (b1 - b0) * (q + 1) / n,
                              "pool": b["pool"], "trans": tr if q == 0 else "xfade", "zoom": "in" if len(items) % 2 else "out"})
        for c in spec.get("c", []):
            t = first if c["at"] is None else max(first, t_of(sid, c["at"]))
            caps.append({"sec": sid, "t": t, "end": end, "text": c["text"], "big": c.get("big", False)})
            if c.get("big"):
                sfx.append(("pop", t))
        for fx in spec.get("sfx", []):
            sfx.append((fx["type"], t_of(sid, fx["at"])))
    caps.sort(key=lambda c: c["t"])
    for i, c in enumerate(caps):  # each caption lasts until the next one (max 10 s, never past its section)
        nxt = caps[i + 1]["t"] if i + 1 < len(caps) else total
        c["t1"] = min(nxt, c["t"] + 10.0, c["end"] + 0.3)
    for it in items:
        it["f0"], it["f1"] = round(it["t0"] * FPS), round(it["t1"] * FPS)
    items[-1]["f1"] = round(total * FPS)
    return items, caps, sfx, total, off


def assign_clips(items, edit, catalog):
    """Give every item a clean (text-free) segment: least-used clip of its pool first, never the clip of
    the previous few items, segments of a clip consumed in order (wrapping only when it is used up)."""
    pools = edit["pools"]
    for name, cut in edit.get("exclude", {}).items():  # manual cuts on top of clip_qc.py's
        if name in catalog:
            rng = catalog[name]["clean"]
            for x0, x1 in cut:
                rng = [r for a, z in rng for r in ([a, min(z, x0)], [max(a, x1), z]) if r[1] - r[0] >= 1.5]
            catalog[name] = dict(catalog[name], clean=rng)
    cursor, used, recent = {}, {}, []
    for it in items:
        need = (it["t1"] - it["t0"]) + 0.8  # include transition overlap
        best = None
        for k, name in enumerate(pools[it["pool"]]):
            ok = [r for r in catalog.get(name, {}).get("clean", []) if r[1] - r[0] >= need]
            if not ok:
                continue
            have = sum(r[1] - r[0] for r in ok)
            score = 1 - used.get(name, 0.0) / have - (2.0 if name in recent[-3:] else 0) - 0.001 * k
            if best is None or score > best[0]:
                best = (score, name, ok)
        if best is None:
            raise SystemExit(f"pool {it['pool']} has no clip with {need:.1f}s clean footage")
        _, name, ok = best
        cur = cursor.get(name, 0.0)
        seg = next((r for r in ok if max(cur, r[0]) + need <= r[1]), None)
        if seg is None:  # used up: wrap around
            seg, cur = ok[0], ok[0][0]
        s0 = max(cur, seg[0])
        it["clip"], it["ss"] = name, round(s0, 2)
        cursor[name] = s0 + need + 0.5
        used[name] = used.get(name, 0.0) + need + 0.5
        recent.append(name)


# ------------------------------------------------------------------ frames
class ClipReader:
    def __init__(self, path, ss, crop=None):
        self.cap = cv2.VideoCapture(path)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, ss * 1000)
        self.last, self.crop = None, crop

    def read(self):
        ok, fr = self.cap.read()
        if ok:
            if self.crop:  # cut a corner label out of the frame
                x0, y0, x1, y1 = self.crop
                fr = cv2.resize(fr[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)], (W, H), interpolation=cv2.INTER_LINEAR)
            self.last = fr
        return self.last if self.last is not None else np.zeros((H, W, 3), np.uint8)


def kb(fr, p, mode):
    z = 1.0 + 0.07 * p if mode == "in" else 1.07 - 0.07 * p
    M = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)]])
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def bg_frame(it, f):
    rd = it.setdefault("_rd", None)
    if rd is None:
        it["_rd"] = rd = ClipReader(os.path.join(G["clips"], it["clip"] + ".mp4"), it["ss"], G["crops"].get(it["clip"]))
    return rd.read()


def item_frame(it, f):
    t = (f - it["f0"]) / FPS
    D = max((it["f1"] - it["f0"]) / FPS, 0.1)
    p = min(max(t / D, 0), 1.2)
    src = bg_frame(it, f)
    if it["kind"] == "clip":
        return kb(src, p, it["zoom"])
    dark = cv2.GaussianBlur(src, (0, 0), 2.5)
    if it["kind"] in ("title", "card"):
        fr = (kb(dark, p, "in") * 0.42).astype(np.uint8)
        op = min(1, t / 0.35)
        if it["kind"] == "title":
            rv.draw_text(fr, it["text"], int(116 + 8 * min(p, 1)), "center", op)
        else:
            num, title = it["text"]
            rv.draw_text(fr, num, 64, (0.5, 0.40), op, color=(200, 160, 255), font="Montserrat")
            rv.draw_text(fr, title, fit(title, 104, 1700), (0.5, 0.53), op)
        if t < 0.2:  # flash in
            fr = cv2.addWeighted(fr, 1.0, np.full_like(fr, 255), 0.6 * (1 - t / 0.2), 0)
        return fr
    G["bgframe"] = (dark * 0.4).astype(np.uint8)
    it.setdefault("flash_t", D * 0.45)  # lz_flash: when the detector lights up
    fr = rv.gfx(it["gfx"], t, D, it)
    G["bgframe"] = None
    return fr


def fit(text, size, maxw, font="Anton"):
    while size > 30:
        _, a = rv.text_rgba(text, size, font, (255, 255, 255))
        if a.shape[1] <= maxw:
            break
        size -= 4
    return size


def transition(a, b, p, kind):
    if kind in ("xfade", "blur"):
        if kind == "blur":
            k = int(1 + 18 * math.sin(math.pi * p))
            a, b = cv2.blur(a, (k, k)), cv2.blur(b, (k, k))
        return cv2.addWeighted(a, 1 - p, b, p, 0)
    if kind == "zoom":
        za, zb = 1 + 0.35 * p, 1.2 - 0.2 * p
        A = cv2.warpAffine(a, np.float32([[za, 0, W / 2 * (1 - za)], [0, za, H / 2 * (1 - za)]]), (W, H))
        B = cv2.warpAffine(b, np.float32([[zb, 0, W / 2 * (1 - zb)], [0, zb, H / 2 * (1 - zb)]]), (W, H))
        return cv2.addWeighted(A, 1 - p, B, p, 0)
    if kind == "flash":
        m = cv2.addWeighted(a, 1 - p, b, p, 0)
        return cv2.addWeighted(m, 1.0, np.full_like(m, 255), 0.75 * math.sin(math.pi * p), 0)
    if kind == "whip":
        dx = int(W * p)
        out = np.zeros_like(a)
        out[:, :W - dx] = a[:, dx:]
        out[:, W - dx:] = b[:, :dx]
        return cv2.blur(out, (int(1 + 60 * math.sin(math.pi * p)), 1))
    return b


TDUR = {"xfade": 7, "blur": 10, "zoom": 10, "flash": 9, "whip": 9}


def draw_caps(fr, caps, f):
    t = f / FPS
    for c in caps:
        if c["t"] <= t < c["t1"]:
            dt = t - c["t"]
            op = min(1, dt / 0.25) * min(1, (c["t1"] - t) / 0.2)
            if c["big"]:
                size = fit(c["text"], 132, 1700)
                rv.draw_text(fr, c["text"], size, (0.5, 0.5 - 0.02 * (1 - min(1, dt / 0.25))), op)
            else:
                band = G["band"]
                fr[H - band.shape[0]:] = (fr[H - band.shape[0]:] * (1 - band * op)).astype(np.uint8)
                size = fit(c["text"], 62, 1700)
                rv.draw_text(fr, c["text"], size, (0.5, 0.875 + 0.02 * (1 - min(1, dt / 0.25))), op)


def init(clips, fonts, assets, crops):
    rv.init_worker(assets, fonts)
    G["clips"], G["crops"] = clips, crops
    G["bgframe"] = None
    g = np.linspace(0, 1, 280) ** 1.6 * 0.65
    G["band"] = np.repeat(g[:, None, None], W, 1).astype(np.float32)
    orig = rv.starfield
    rv.starfield = lambda t, speed=12.0, dim=1.0: (G["bgframe"] * min(1.0, dim * 1.3)).astype(np.uint8) \
        if G.get("bgframe") is not None else orig(t, speed, dim)


def render_chunk(args):
    sid, items, caps, out_dir, total_f = args
    path = os.path.join(out_dir, f"v2_{sid}.mp4")
    if os.path.exists(path):
        return path
    f0, f1 = items[0]["f0"], items[-1]["f1"]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-g", "60",
                           path + ".part.mp4"], stdin=subprocess.PIPE)
    k = 0
    for f in range(f0, f1):
        while k + 1 < len(items) and f >= items[k + 1]["f0"]:
            k += 1
            if k >= 2 and items[k - 2].get("_rd"):  # free decoders that are no longer needed
                items[k - 2]["_rd"].cap.release()
                items[k - 2]["_rd"] = None
        it = items[k]
        fr = item_frame(it, f)
        tr = it.get("trans", "cut")
        if k > 0 and tr in TDUR and f - it["f0"] < TDUR[tr]:
            prev = items[k - 1]
            fr = transition(item_frame(prev, f), fr, (f - it["f0"] + 1) / (TDUR[tr] + 1), tr)
        draw_caps(fr, caps, f)
        if f < 30:
            fr = (fr * (f / 30)).astype(np.uint8)
        elif f > total_f - 75:
            fr = (fr * max(0, (total_f - f) / 75)).astype(np.uint8)
        ff.stdin.write(np.ascontiguousarray(fr).tobytes())
    ff.stdin.close()
    ff.wait()
    os.replace(path + ".part.mp4", path)
    return path


# ------------------------------------------------------------------ audio
def mix(narr, sfx, total, off, edit, tl, music_dir):
    import soundfile as sf
    v, sr = sf.read(narr)
    v = v.mean(1) if v.ndim > 1 else v
    n = int(total * SR)
    out = np.zeros((n, 2))
    o = int(off * SR)
    out[o:o + len(v)] += v[:n - o, None]
    vr = np.sqrt(np.mean(v[np.abs(v) > 0.02] ** 2))
    vpk = np.abs(v).max()
    db = lambda x: 10 ** (x / 20)
    # speech envelope -> music ducking (music sits ~22 dB under speech, ~13 dB under in pauses)
    env = np.zeros(n)
    env[o:o + len(v)] = np.abs(v[:n - o])
    win = int(0.5 * SR)
    sm = np.convolve(env, np.ones(win) / win, "same")
    speaking = np.clip(sm / (vr * 0.35), 0, 1)
    duck = db(-22) + (db(-13) - db(-22)) * (1 - speaking)
    # music: one track per section group, crossfaded
    starts = {s["id"]: s["start"] + off for s in tl["sections"]}
    marks = [(0.0 if i == 0 else starts[m["from"]] - 1.5, m["track"]) for i, m in enumerate(edit["music"])] + [(total, None)]
    music = np.zeros((n, 2))
    xf = int(3 * SR)
    for (a, trk), (b, _) in zip(marks, marks[1:]):
        y, msr = sf.read(os.path.join(music_dir, trk))
        y = y if y.ndim > 1 else np.stack([y, y], 1)
        if msr != SR:
            idx = np.arange(0, len(y), msr / SR).astype(int)
            y = y[idx[idx < len(y)]]
        ia, ib = int(a * SR), min(n, int(b * SR) + xf)
        L = ib - ia
        reps = int(np.ceil(L / len(y)))
        seg = np.tile(y, (reps, 1))[:L]
        g = np.ones(L)
        g[:xf] = np.linspace(0, 1, min(xf, L))
        g[-xf:] = np.minimum(g[-xf:], np.linspace(1, 0, min(xf, L)))
        seg = seg / (np.sqrt(np.mean(seg ** 2)) + 1e-9)
        music[ia:ib] += seg * g[:, None]
    music *= vr * duck[:, None]
    tail = np.clip((total - np.arange(n) / SR) / 4, 0, 1)
    out += music * tail[:, None]
    # sub-bass drone
    t = np.arange(n) / SR
    dr = sum(a * np.sin(2 * np.pi * f * t + ph) for f, a, ph in ((55, 1, 0), (82.4, .5, 1), (110, .3, 2)))
    dr *= vr * db(-32) / np.sqrt(np.mean(dr ** 2))
    out += (dr * np.clip(t / 3, 0, 1) * tail)[:, None]
    rng = np.random.default_rng(1)
    tp = np.arange(int(0.08 * SR)) / SR
    pop = (np.sin(2 * np.pi * 1300 * tp) + 0.3 * np.sin(2 * np.pi * 2600 * tp)) * np.exp(-tp * 60)

    def whoosh(d):
        tw = np.arange(int(d * SR)) / SR
        wn = rng.normal(0, 1, len(tw))
        wn = wn - np.convolve(wn, np.ones(40) / 40, "same")
        return np.convolve(wn * np.sin(np.pi * tw / tw[-1]) ** 2, np.ones(10) / 10, "same")
    tb = np.arange(int(2.6 * SR)) / SR
    boom = np.sin(2 * np.pi * (48 - 14 * tb) * tb) * np.exp(-tb * 1.8) + \
        np.convolve(rng.normal(0, 1, len(tb)), np.ones(300) / 300, "same") * np.exp(-tb * 6) * 3
    lib = {"pop": (pop, -30), "whoosh": (whoosh(0.55), -24), "whoosh_big": (whoosh(1.0), -15), "boom": (boom, -7)}
    for kind, at in sfx:
        sig, gdb = lib[kind]
        i = int(at * SR)
        if i >= n:
            continue
        s_ = sig[:n - i] * vpk * db(gdb) / np.abs(sig).max()
        out[i:i + len(s_)] += s_[:, None]
    return out


def main():
    ap = argparse.ArgumentParser()
    for a in ("edit", "timeline", "narration", "clips", "catalog", "music", "fonts", "assets", "out"):
        ap.add_argument(a)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    edit, tl, catalog = json.load(open(a.edit)), json.load(open(a.timeline)), json.load(open(a.catalog))
    items, caps, sfx, total, off = plan(edit, tl)
    assign_clips(items, edit, catalog)
    total_f = round(total * FPS)
    lens = [it["t1"] - it["t0"] for it in items]
    print(f"{len(items)} items, {len(caps)} captions, {len(sfx)} sfx, {total:.1f}s, median item {np.median(lens):.2f}s")
    if a.check:
        from collections import Counter
        print("clip uses:", Counter(it.get("clip") for it in items).most_common(12))
        for it in items[:40]:
            print(f"{it['t0']:7.2f} {it['kind']:5s} {it.get('gfx') or it.get('clip')} @{it.get('ss')} {it.get('trans')}")
        return
    work = os.path.splitext(a.out)[0] + "_v2work"
    os.makedirs(work, exist_ok=True)
    only = set(filter(None, a.only.split(",")))
    order = [s["id"] for s in tl["sections"]]
    jobs = []
    for sid in order:
        if only and sid not in only:
            continue
        its = [dict(it) for it in items if it["sec"] == sid]
        jobs.append((sid, its, caps, work, total_f))
    jobs.sort(key=lambda j: -(j[1][-1]["f1"] - j[1][0]["f0"]))
    with Pool(a.workers, initializer=init, initargs=(a.clips, a.fonts, a.assets, {**{k: v.get("crop") for k, v in catalog.items()}, **edit.get("crops", {})})) as pool:
        for k, pth in enumerate(pool.imap_unordered(render_chunk, jobs)):
            print(f"  [{k + 1}/{len(jobs)}] {os.path.basename(pth)}", flush=True)
    if only:
        return
    import soundfile as sf
    wav = os.path.join(work, "mix.wav")
    sf.write(wav, np.clip(mix(a.narration, sfx, total, off, edit, tl, a.music), -1, 1).astype(np.float32), SR)
    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file 'v2_{sid}.mp4'\n" for sid in order))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", a.out], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
