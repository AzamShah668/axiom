"""YouTube Shorts (1080x1920) cut from a finished v3 video: a spoken hook, then the story, then an end card.

  python render_short.py <shorts.spec> <cutlist.json> <master_work_dir> <sources.json> <clips_dir> <music_dir>
                         <fonts_dir> <assets_dir> <out_dir> [--only <id>] [--workers 4] [--speed 1.1]

shorts.spec, one block per Short. Master lines are found by the start of their English C caption in the cut list:
  == <id> | <YouTube title>
  top: <TITLE BAR TEXT, *GOLD* words>           written in the black bar above the picture for the whole Short
  hook: <caption start>                         the master line whose shots and number card the hook uses
  say: <Devanagari hook line>                   new spoken hook (ElevenLabs, locked preset), e.g. "क्या आपको पता है…"
  say_en: <English of the hook line>            its caption
  land: <word in the say line>                  the hook's number lands on this word
  body: <caption start> .. <caption start>      a run of master lines in story order (the hook line is left out)
  body: ...                                     further runs are joined in order
Without say:, the hook is the master line itself.

Layout: the picture is a 1080x1080 square in the middle of the frame, black above and below; the title sits in the
top bar; the bottom bar stays clear for the Shorts title and buttons. The Short plays --speed times faster than
the master (voice time-stretched, pitch kept). It re-uses the master's reviewed plan - cuts, shots, camera moves,
headlines, number cards, sounds - re-timed, with each shot fetched again from its 4K source and framed around its
brightest subject. It ends on FULL VIDEO BELOW (written, never spoken); the full video is linked with YouTube
Studio's "Related video" field. Writes <out_dir>/<id>.mp4, <id>.en.srt, <id>.plan.json; shot crops are cached in
<out_dir>/vclips/, spoken hooks in <out_dir>/tts/ (re-renders cost no credits).
"""
import argparse, base64, copy, hashlib, json, os, re, subprocess, sys, time
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

FPS, SR = r3.FPS, r3.SR
SW, SH = 1080, 1080          # the picture (stage): every shot and overlay is drawn at this size
CW, CH = 1080, 1920          # the Short
BAND_Y = (CH - SH) // 2      # top of the picture; the title bar is above it
END = 2.6                    # end card length (s)
SLIVER = 0.4                 # a shot piece shorter than this at a join is given to its neighbour
GEOMETRY = ("callout", "route", "hud")  # overlays pinned to positions in the 16:9 frame: left out of Shorts


def parse_spec(path):
    shorts, cur = [], None
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("=="):
            sid, _, title = ln[2:].partition("|")
            cur = {"id": sid.strip(), "title": title.strip(), "body": []}
            shorts.append(cur)
            continue
        key, _, val = ln.partition(":")
        if key == "body":
            a, _, b = val.partition("..")
            cur["body"].append((a.strip(), (b or a).strip()))
        elif key in ("top", "hook", "say", "say_en", "land"):
            cur[key] = val.strip()
    return shorts


class Lines:
    """Spoken sentences of the master (non-big C captions) with cut points snapped into the pause before each."""

    def __init__(self, P, voice):
        self.caps = sorted([c for c in P["caps"] if not c.get("big")], key=lambda c: c["t"])
        self.cards = sorted(it["t0"] for it in P["items"] if it["kind"] in ("card", "title"))
        self.items = P["items"]
        k = int(0.02 * SR)
        self.env = np.convolve(np.abs(voice), np.ones(k) / k, "same")
        self.quiet = 10 ** (-45 / 20)  # 20 ms level under -45 dBFS = no speech

    def find(self, prefix):
        hits = [i for i, c in enumerate(self.caps) if c["text"].strip('"').lower().startswith(prefix.lower())]
        if len(hits) != 1:
            raise SystemExit(f"caption start {prefix!r} matches {len(hits)} lines: make it longer")
        return hits[0]

    def snap(self, t, floor=0.0):
        """Cut point for a sentence whose caption starts at t: just inside the silence before its first sound.
        A section's first line is spoken under the chapter card, before its caption shows, so walk back through
        the speech to the last 0.15 s of silence (at most 2 s, never before `floor`)."""
        i = int(t * SR)
        if self.env[i - int(0.05 * SR):i].max() < self.quiet:  # the caption starts on the first sound
            return t - 0.035
        lo = int(max(floor, t - 2.0) * SR)
        run, need = 0, int(0.15 * SR)
        step = int(0.005 * SR)
        while i > lo:
            run = run + step if self.env[i - step:i].max() < self.quiet else 0
            if run >= need:
                return (i + need - int(0.04 * SR)) / SR
            i -= step
        i0, i1 = int((t - 0.35) * SR), int((t - 0.02) * SR)  # no clear pause: the quietest 20 ms before t
        return t if i1 <= i0 else (i0 + int(np.argmin(self.env[i0:i1]))) / SR

    def span(self, i):
        c = self.caps[i]
        a = self.snap(c["t"], self.caps[i - 1]["t"] + 0.3 if i else 0.0)
        nxt_card = next((t for t in self.cards if t > c["t"]), 1e9)
        b = min(c.get("end", 1e9) + 0.45, nxt_card)
        if i + 1 < len(self.caps) and self.caps[i + 1]["t"] < b:
            b = self.snap(self.caps[i + 1]["t"], c["t"] + 0.3)
        return a, b


def segments(spec, L):
    """[(a, b), ...] on the master's clock: the hook line, then each body run with the hook line taken out."""
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


# ------------------------------------------------------------------ spoken hook (ElevenLabs, cached)
def tts_line(text, cache_dir):
    """The hook line in the locked voice with the master's voice finish -> (mono at SR, char starts, char ends)."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "elevenlabs"))
    from el import API, ROOT, _h  # loads config/.env; the key is never printed
    preset = json.load(open(os.path.join(ROOT, "productions", "voice-preset.json")))
    body = {"text": text, "model_id": preset["model_id"], "voice_settings": preset["voice_settings"]}
    key = hashlib.sha1(json.dumps([body, preset["voice_id"]], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    os.makedirs(cache_dir, exist_ok=True)
    mp3, wav, al_p = (os.path.join(cache_dir, key + x) for x in (".mp3", ".wav", ".align.json"))
    if not os.path.exists(wav):
        import requests
        url = f"{API}/text-to-speech/{preset['voice_id']}/with-timestamps?output_format=mp3_44100_192"
        for attempt in range(4):
            r = requests.post(url, headers={**_h(), "Content-Type": "application/json"}, data=json.dumps(body), timeout=300)
            if r.status_code == 200:
                break
            if r.status_code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(5 * 2 ** attempt)
                continue
            raise SystemExit(f"hook TTS: HTTP {r.status_code} {r.text[:200]}")
        d = r.json()
        open(mp3, "wb").write(base64.b64decode(d["audio_base64"]))
        json.dump(d["alignment"], open(al_p, "w"), ensure_ascii=False)
        subprocess.run(["bash", os.path.join(ROOT, "scripts", "elevenlabs", "voice_post.sh"), mp3, wav, "0"], check=True,
                       capture_output=True)
        print(f"  hook TTS: {len(text)} characters")
    al = json.load(open(al_p))
    return r3._load(wav, 1), al["character_start_times_seconds"], al["character_end_times_seconds"]


def spoken_hook(spec, out_dir):
    """(voice, duration, land_t): trimmed to start on the first syllable, 0.3 s of air after the last."""
    text = spec["say"]
    v, cs, ce = tts_line(text, os.path.join(out_dir, "tts"))
    first = next(i for i, ch in enumerate(text) if not ch.isspace())
    a = max(0.0, cs[first] - 0.04)
    b = min(len(v) / SR, ce[-1] + 0.3)
    land = text.find(spec.get("land", "")) if spec.get("land") else -1
    land_t = (cs[land] if land >= 0 else ce[-1]) - a
    return cut(v, a, b), b - a, land_t


# ------------------------------------------------------------------ plan
def shift_ovl(o, d, a, b):
    o = copy.deepcopy(o)
    for key in ("t0", "t1", "t_last", "kicker_t", "sub_t"):
        if key in o:
            o[key] = (min(o[key], b) if key == "t1" else max(o[key], a) if key == "t0" else o[key]) + d
    for ln in o.get("lines", []):
        ln["t"] += d
    return o


def hook_count(num, land_t):
    """A number that opens a Short counts from its first frame and lands on the spoken word."""
    return dict(num, land_t=land_t, count_s=max(0.3, land_t - 0.1))


def pieces(P, a, b):
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
    if pcs:  # the picture covers the whole voice segment (a chapter card under the first words is skipped)
        pcs[0][1], pcs[-1][2] = min(pcs[0][1], a), max(pcs[-1][2], b)
        for k in range(1, len(pcs)):
            pcs[k - 1][2] = pcs[k][1]
    return pcs


def new_item(it, x0, t0, t1, trans=None):
    new = {k_: v for k_, v in it.items() if k_ not in ("f0", "f1", "_rd")}
    new.update(t0=t0, t1=t1, src_off=max(0.0, it.get("ss", 0.0) + (x0 - it["t0"])))
    if trans:
        new["trans"] = trans
    if it["kind"] == "num" and x0 > it["t0"]:
        new["num"] = dict(it["num"], land_t=it["num"].get("land_t", 1.3) - (x0 - it["t0"]))
    return new


def build(spec, P, L, hook=None):
    """Plan on the Short's clock at master speed (scale_plan() speeds it up). hook = (duration, land_t) of a
    spoken hook laid over the master hook line's shots, or None to use the master line itself."""
    segs = segments(spec, L)
    items, ovl, sfx, mus, caps = [], [], [], [], []
    a, b = segs[0]
    if hook:  # the spoken hook: the master line's shots stretched to the new line, its number landing on `land`
        Dh, land_t = hook
        w = Dh / (b - a)
        for n, (it, x0, x1) in enumerate(pieces(P, a, b)):
            items.append(new_item(it, x0, (x0 - a) * w, (x1 - a) * w, "cut" if n == 0 else None))
            if items[-1]["kind"] == "num":
                items[-1]["num"] = hook_count(items[-1]["num"], land_t - items[-1]["t0"])
        for o in P["ovl"]:
            if o["kind"] == "num" and a - 0.4 <= o["t0"] < b - 0.3 and o["num"].get("template") not in GEOMETRY:
                o = copy.deepcopy(o)
                o.update(t0=0.0, t1=Dh, num=dict(hook_count(o["num"], land_t), dur=Dh))
                ovl.append(o)
                sfx += [list(e) for e in r3.card_sfx(o["num"], 0.0)]
        caps.append({"t": 0.0, "t1": Dh, "text": spec.get("say_en", ""), "big": False})
        T, body = Dh, segs[1:]
    else:
        T, body = 0.0, segs
    for si, (a, b) in enumerate(body):
        d = T - a
        opening = not hook and si == 0
        for n, (it, x0, x1) in enumerate(pieces(P, a, b)):
            trans = ("cut" if opening else "flare" if si == (0 if hook else 1) else "cut") if n == 0 else None
            items.append(new_item(it, x0, x0 + d, x1 + d, trans))
            if opening and n == 0 and it["kind"] == "num":
                items[-1]["num"] = hook_count(items[-1]["num"], items[-1]["num"].get("land_t", 1.3))
        for o in P["ovl"]:
            if o["kind"] == "footer" or not (a - 0.4 <= o["t0"] < b - 0.3):  # a line's first word can lead the cut
                continue
            if o["kind"] == "num" and o["num"].get("template") in GEOMETRY:
                print(f"  {spec['id']}: left out {o['num']['template']} overlay at {o['t0']:.1f}s (16:9 geometry)")
                continue
            o = shift_ovl(o, d, a, b)
            if o["kind"] == "headline":
                o["pos"] = "center"
            if opening and o["kind"] == "num" and o["t0"] - T < 0.8:  # the hook's number is up and moving on frame 0
                lead = o["t0"] - T
                o["t0"] = T
                o["num"] = dict(hook_count(o["num"], o["num"].get("land_t", 1.3) + lead),
                                **({"dur": float(o["num"]["dur"]) + lead} if "dur" in o["num"] else {}))
            ovl.append(o)
        sfx += [[e[0], e[1] + d] + list(e[2:]) for e in P["sfx"] if a - 0.02 <= e[1] < b - 0.05]
        mus += [dict(e, t0=e["t0"] + d, t1=min(e["t1"], b) + d, **({"peak": e["peak"] + d} if "peak" in e else {}))
                for e in P["mus"] if a <= e["t0"] < b]
        caps += [dict(c, t=c["t"] + d, t1=min(c["t1"], b) + d) for c in P["caps"] if a <= c["t"] < b]
        if si == (0 if hook else 1):
            sfx.append(["whoosh", T - 0.25, 0])
        T += b - a
    a_body = body[0][0]
    track = [c for c in P["music"] if c["t"] <= a_body][-1]
    sfx.append(["hit", 0.0, -4])
    return segs, {"style": "v3", "items": items, "ovl": ovl, "caps": caps, "sfx": sfx, "mus": mus,
                  "music": [{"t": 0.0, "track": track["track"], "gain": track.get("gain", 0.0)}],
                  "breaths": [], "total": T, "off": 0.0, "grade": P.get("grade", {})}


def scale_plan(Ps, k):
    """Play the Short k times faster: every time on the plan divided by k (footage itself plays at normal speed)."""
    def num(n):
        return dict(n, **{key: float(n[key]) / k for key in ("land_t", "count_s", "dur", "draw") if key in n})
    for it in Ps["items"]:
        it["t0"], it["t1"] = it["t0"] / k, it["t1"] / k
        if "num" in it:
            it["num"] = num(it["num"])
    for o in Ps["ovl"]:
        for key in ("t0", "t1", "t_last", "kicker_t", "sub_t"):
            if key in o:
                o[key] /= k
        for ln in o.get("lines", []):
            ln["t"] /= k
        if "num" in o:
            o["num"] = num(o["num"])
    Ps["sfx"] = [[e[0], e[1] / k] + list(e[2:3]) + ([dict(e[3], **({"d": e[3]["d"] / k} if "d" in e[3] else {}))]
                                                   if len(e) > 3 else []) for e in Ps["sfx"]]
    for e in Ps["mus"]:
        for key in ("t0", "peak", "t1"):
            if key in e:
                e[key] /= k
    for c in Ps["caps"]:
        c["t"], c["t1"] = c["t"] / k, c["t1"] / k
    Ps["total"] /= k


def add_end(Ps):
    T = Ps["total"]
    Ps["items"][-1]["t1"] = T + END
    Ps["ovl"].append({"kind": "endcard", "t0": T + 0.05, "t1": T + END})
    Ps["sfx"] += [["whoosh", T - 0.2, -2], ["pop", T + 0.05, 2]]
    Ps["sfx"].sort(key=lambda e: e[1])
    Ps["total"] = T + END
    for it in Ps["items"]:
        it["f0"], it["f1"] = round(it["t0"] * FPS), round(it["t1"] * FPS)
    Ps["items"][-1]["f1"] = round(Ps["total"] * FPS)


# ------------------------------------------------------------------ footage
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
    """Fetch the shot from its 4K source and cut the stage-shaped window (falls back to the 1080p library clip)."""
    out, src, clip_path, t_lib, dur, crop, cx = job
    if os.path.exists(out):
        return out, "have"
    x0, y0, x1, y1 = crop
    rw, rh = (x1 - x0), (y1 - y0)
    win = min(1.0, rh * SW / SH * (1080 / 1920) / rw)  # window width as a fraction of the region width
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


# ------------------------------------------------------------------ render
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
    mg.LAYOUT.update(label_w=0.9)  # labels fit the 1080 px picture
    r3.G.update(fade_in=0, fade_out=0)  # the hook hits on frame 0, the end card loops into it


def title_bar(text, path):
    """The black bar above the picture with the Short's title: Anton, white with *gold* words, centred."""
    bar = np.zeros((BAND_Y, CW, 3), np.uint8)
    W0, H0 = mg.W, mg.H
    mg.W, mg.H = CW, BAND_Y
    def words(part):
        ws = [(ph.strip("*"), ph.startswith("*")) for ph in re.findall(r"\*[^*]+\*|\S+", part)]
        return [(x, g) for ph, g in ws for x in ph.split()]  # *A BILLION TONS* -> three gold words
    parts = [words(p_) for p_ in text.split(" / ")]  # " / " = a line break chosen in the spec
    for size in (104, 96, 88, 80, 72, 64):
        f = mg._font("Anton", size, None)
        sp = f.getlength(" ") * 0.9
        lines = []
        for part in parts:
            cur, wcur = [], 0
            for w_, g in part:
                ww = mg._measure(w_.upper(), f, 0)[0]
                if cur and wcur + sp + ww > CW - 100:
                    lines.append(cur)
                    cur, wcur = [], 0
                cur.append((w_, g, ww))
                wcur += (sp if len(cur) > 1 else 0) + ww
            lines.append(cur)
        if len(lines) <= len(parts) or (len(parts) == 1 and len(lines) <= 3):
            break
    lh = size * 1.02
    y = BAND_Y * 0.6 - lh * len(lines) / 2 + lh / 2  # a little low: the top of the screen has the Shorts icons
    for ln in lines:
        total = sum(w for _, _, w in ln) + sp * (len(ln) - 1)
        x = CW / 2 - total / 2
        for w_, g, ww in ln:
            lay = mg.layer(w_.upper(), "Anton", size, None, grad=mg.GOLD if g else mg.SILVER, shadow=0.4)
            pad = (lay.shape[1] - mg.text_w(lay, size)) / 2
            mg.paste(bar, lay, x - pad, y, anchor="l")
            x += ww + sp
        y += lh
    mg.W, mg.H = W0, H0
    cv2.imwrite(path, bar)


def _worker_init(*args):
    set_canvas()
    r3.init(*args)


def render(sid, Ps, voice_wav, a, out_dir, title_png):
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
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", title_png, "-i", wav,
                    "-filter_complex", f"[0:v]pad={CW}:{CH}:0:{BAND_Y}:color=black[p];[p][1:v]overlay=0:0[v]",
                    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-af", "alimiter=limit=0.84:attack=3:release=80:level=false", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-t", f"{Ps['total']:.3f}", "-movflags", "+faststart", mp4], check=True)
    r3.write_srt(Ps["caps"], os.path.join(out_dir, f"{sid}.en.srt"))
    return mp4, Vm


def main():
    ap = argparse.ArgumentParser()
    for x in ("spec", "cutlist", "master_work", "sources", "clips", "music", "fonts", "assets", "out"):
        ap.add_argument(x)
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--speed", type=float, default=1.1, help="Shorts play this much faster than the master")
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
    mg.set_fonts(a.fonts)
    for spec in parse_spec(a.spec):
        if a.only and spec["id"] != a.only:
            continue
        sid = spec["id"]
        work = os.path.join(a.out, f"{sid}_work")
        os.makedirs(work, exist_ok=True)
        hook = spoken_hook(spec, a.out) if spec.get("say") else None
        segs, Ps = build(spec, P, L, hook and hook[1:])
        voice_parts = ([hook[0]] if hook else []) + [cut(voice, x, y) for x, y in (segs[1:] if hook else segs)]
        raw, voice_wav = os.path.join(work, "voice_raw.wav"), os.path.join(work, "voice.wav")
        sf.write(raw, np.concatenate(voice_parts).astype(np.float32), SR)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"rubberband=tempo={a.speed}:pitchq=quality",
                        "-ar", str(SR), "-ac", "1", voice_wav], check=True)  # faster, same pitch
        scale_plan(Ps, a.speed)
        v = r3._load(voice_wav, 1)
        sf.write(voice_wav, np.concatenate([v, np.zeros(int(END * SR) + SR)]).astype(np.float32), SR)
        add_end(Ps)
        print(f"{sid}: {Ps['total']:.1f}s at x{a.speed} ({'spoken hook, ' if hook else ''}master "
              f"{', '.join(f'{x:.1f}-{y:.1f}' for x, y in segs)}); {len(Ps['items'])} shots, {len(Ps['ovl'])} overlays", flush=True)
        jobs = []
        for it in Ps["items"]:
            crop = it.get("crop") or [0.0, 0.0, 1.0, 1.0]
            clip_path = os.path.join(a.clips, it["clip"] + ".mp4")
            dur = it["t1"] - it["t0"] + 1.2  # margin: the outgoing shot keeps playing through a transition
            cx = 0.5 if it["kind"] != "clip" else subject_x(clip_path, it["src_off"], it["t1"] - it["t0"], crop)
            name = (f"{it['clip']}@{it['src_off']:.2f}+{dur:.2f}_{SW}x{SH}"
                    + (f"c{'_'.join(f'{v:g}' for v in crop)}" if it.get("crop") else ""))
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
        title_png = os.path.join(work, "title.png")
        title_bar(spec.get("top") or spec["title"].replace("#shorts", "").strip(), title_png)
        json.dump({**Ps, "id": sid, "title": spec["title"], "segments": segs}, open(os.path.join(a.out, f"{sid}.plan.json"), "w"),
                  indent=1, ensure_ascii=False)
        mp4, Vm = render(sid, Ps, voice_wav, a, a.out, title_png)
        print(f"wrote {mp4} ({Ps['total']:.1f}s, voice {Vm:.1f} LUFS)")


if __name__ == "__main__":
    main()
