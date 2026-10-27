"""Render a sectioned Hindi narration with the locked voice preset.

  python render_narration.py <narration.hi.md> <out_dir> [--only cold_open,fact10] [--gap 1.2] [--open-gap 1.6]
                             [--title-after cold_open] [--gap-after hook=1.0,...] [--max-pause 0.3]

For every "## <id>" section: calls ElevenLabs /with-timestamps (with neighbour text as context so
prosody flows across joins), saves <id>.mp3 + <id>.align.json. Then joins all sections with gaps
(chapter-card breathing room), applies the documentary finish and writes:
  narration.wav / narration.mp3   final voice track
  timeline.json                   section start/end + character timings on the final timeline
Re-running skips sections that already exist (delete a section's mp3 to re-render it).
--max-pause cuts every pause inside a section down to that length (and its tail to 0.25 s), from the section's
character timings: a Short with its own script never waits (owner's rule). The timeline follows the cut audio.

Real recordings (owner, 2026-10-27: "Einstein said it like this" - and then Einstein says it): a marker
[bite:<name>] in the narration text is not spoken; the voice stops there, the recording plays, the voice goes on.
productions/NN/bites.json defines each one: {"<name>": {"file": <audio/video path from the repo root>, "ss": s,
"d": s, "who": "John Mather", "when": "1989", "said": "<English words>", "hi": "<Hinglish subtitle>" or "subs":
[[from_s, to_s, "<Hinglish line>"], ...] (one line per sentence, seconds from the start of the recording),
"credit": "...", "licence": "public domain (NASA)", "url": "...", "video": true, "gain": 0}}. The recording is levelled
to the voice before it (+ gain dB) and mixed in after the voice finish; timeline.json "bites" lists where each one plays, and a pseudo-word
"#<name>" in the section's characters marks its start (edit.spec trigger "#<name>", e.g. V #mather @ bite:mather).
"""
import argparse, base64, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

sys.path.insert(0, os.path.dirname(__file__))
from el import API, ROOT, _h  # noqa: E402  (loads config/.env)

PRESET = json.load(open(os.path.join(ROOT, "productions", "voice-preset.json")))


BITE = re.compile(r"\s*\[bite:([\w-]+)\]\s*")
BITE_PAD = 0.3  # silence either side of a recording


def strip_bites(text):
    """Text without its [bite:x] markers + [(character index where each recording plays, name)]."""
    out, bites, last = "", [], 0
    for m in BITE.finditer(text):
        out += text[last:m.start()]
        if out and m.end() < len(text):
            out += " "
        bites.append((len(out), m[1]))
        last = m.end()
    return out + text[last:], bites


def parse(path):
    secs, cur = [], None
    for line in open(path, encoding="utf-8"):
        if line.startswith("## "):
            cur = {"id": line[3:].strip(), "text": ""}
            secs.append(cur)
        elif cur is not None and not line.startswith("#"):
            cur["text"] += line
    for s in secs:
        s["text"], s["bites"] = strip_bites(s["text"].strip())
    return secs


def loudness(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])


def insert_bites(wav, al, bites, spec):
    """Open a gap at each marker (BITE_PAD + d + BITE_PAD); returns the shifted alignment and
    [(name, start of the recording in section time)]. Later markers first, so earlier times stay put."""
    import numpy as np
    import soundfile as sf
    v, sr = sf.read(wav)
    ch, cs, ce = list(al["characters"]), list(al["character_start_times_seconds"]), list(al["character_end_times_seconds"])
    vis = [i for i, c in enumerate(ch) if c.strip()]
    out = []
    for pos, name in sorted(bites, reverse=True):
        if name not in spec:
            sys.exit(f"[bite:{name}] is not in bites.json")
        d = float(spec[name]["d"])
        before = [i for i in vis if i < pos]
        after = [i for i in vis if i >= pos]
        t = (ce[before[-1]] + cs[after[0]]) / 2 if before and after else (ce[before[-1]] + 0.15 if before else 0.0)
        gap = 2 * BITE_PAD + d
        k = int(t * sr)
        v = np.concatenate([v[:k], np.zeros((int(gap * sr),) + v.shape[1:]), v[k:]])
        cs = [x + gap if x >= t else x for x in cs]
        ce = [x + gap if x >= t else x for x in ce]
        tag = f"#{name} "
        ch[pos:pos] = list(tag)
        cs[pos:pos] = [t + BITE_PAD] * len(tag)
        ce[pos:pos] = [t + BITE_PAD + d] * len(tag)
        vis = [i if i < pos else i + len(tag) for i in vis]
        out = [(n_, x + gap) for n_, x in out]
        out.append((name, t + BITE_PAD))
    sf.write(wav, v, sr)
    return dict(al, characters=ch, character_start_times_seconds=cs, character_end_times_seconds=ce), out


def mix_bites(final, bites, spec):
    """Mix each recording into the finished voice track at the loudness of the voice just before it, 30 ms fades."""
    import numpy as np
    import soundfile as sf
    if not bites:
        return
    v, sr = sf.read(final)
    for b in bites:
        sp = spec[b["name"]]
        tmp, ref = final + f".{b['name']}.wav", final + ".ref.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(sp["ss"]), "-t", str(sp["d"]), "-i",
                        os.path.join(ROOT, sp["file"]), "-vn", "-ac", "1", "-ar", str(sr), "-af",
                        "highpass=f=70,lowpass=f=12000", tmp], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(0.0, b["t"] - 10.0)), "-t",
                        str(min(10.0, b["t"])), "-i", final, ref], check=True)
        x, _ = sf.read(tmp)
        x = x * 10 ** ((loudness(ref) + float(sp.get("gain", 0.0)) - loudness(tmp)) / 20)
        x *= min(1.0, 0.89 / max(1e-6, np.abs(x).max()))  # peaks under -1 dBFS
        os.remove(tmp)
        os.remove(ref)
        m = min(len(x) // 2, int(0.03 * sr))
        x[:m] *= np.linspace(0, 1, m)
        x[len(x) - m:] *= np.linspace(1, 0, m)
        i = int(b["t"] * sr)
        x = x[:max(0, len(v) - i)]
        if v.ndim == 2:
            v[i:i + len(x)] += x[:, None]
        else:
            v[i:i + len(x)] += x
    sf.write(final, v, sr)


def render(sec, prev_text, next_text, out_dir):
    mp3 = os.path.join(out_dir, f"{sec['id']}.mp3")
    if os.path.exists(mp3):
        return sec["id"], "cached"
    body = {"text": sec["text"], "model_id": PRESET["model_id"], "voice_settings": PRESET["voice_settings"]}
    if prev_text:
        body["previous_text"] = prev_text[-800:]
    if next_text:
        body["next_text"] = next_text[:800]
    url = f"{API}/text-to-speech/{PRESET['voice_id']}/with-timestamps?output_format=mp3_44100_192"
    for attempt in range(4):
        r = requests.post(url, headers={**_h(), "Content-Type": "application/json"}, data=json.dumps(body), timeout=900)
        if r.status_code == 200:
            break
        if r.status_code in (429, 500, 502, 503) and attempt < 3:
            time.sleep(5 * 2 ** attempt)
            continue
        raise SystemExit(f"{sec['id']}: HTTP {r.status_code} {r.text[:300]}")
    d = r.json()
    open(mp3, "wb").write(base64.b64decode(d["audio_base64"]))
    json.dump(d.get("alignment"), open(os.path.join(out_dir, f"{sec['id']}.align.json"), "w"), ensure_ascii=False)
    return sec["id"], f"{len(sec['text'])} chars"


def tighten(wav, al, cap):
    """Cut pauses longer than cap (s) between a section's words down to cap, its tail to 0.25 s.
    Rewrites wav; returns (alignment on the new clock, seconds removed)."""
    import numpy as np
    import soundfile as sf
    v, sr = sf.read(wav)
    ch, cs, ce = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    vis = [i for i, c in enumerate(ch) if c.strip() and c not in ",.?!।…-—"]
    gaps = [(ce[i] + cap / 2, cs[j] - cap / 2) for i, j in zip(vis, vis[1:]) if cs[j] - ce[i] > cap + 0.05]
    end = min(len(v) / sr, ce[vis[-1]] + 0.25)

    def at(t):
        return t - sum(min(max(t - g0, 0.0), g1 - g0) for g0, g1 in gaps)

    edges = [0.0] + [x for g in gaps for x in g] + [end]
    parts, n = [], int(0.01 * sr)
    for k, (x, y) in enumerate(zip(edges[::2], edges[1::2])):
        seg = v[int(x * sr):int(y * sr)].copy()
        m = min(n, len(seg) // 2)
        if k:  # 10 ms fades at the joins only stop clicks; the joins sit in silence
            seg[:m] *= np.linspace(0, 1, m)
        seg[len(seg) - m:] *= np.linspace(1, 0, m)
        parts.append(seg)
    sf.write(wav, np.concatenate(parts), sr)
    return (dict(al, character_start_times_seconds=[at(t) for t in cs], character_end_times_seconds=[at(t) for t in ce]),
            len(v) / sr - end + sum(g1 - g0 for g0, g1 in gaps))


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("narration")
    p.add_argument("out_dir")
    p.add_argument("--only", default="")
    p.add_argument("--gap", type=float, default=1.2, help="silence before each chapter (s)")
    p.add_argument("--open-gap", type=float, default=1.6, help="silence after the cold open (title card) (s)")
    p.add_argument("--title-after", default="cold_open",
                   help="section the open gap follows (default cold_open; the first section if there is none)")
    p.add_argument("--gap-after", default="", help="per-section gaps, e.g. hook=1.0,fact5=3.0 (silence after it)")
    p.add_argument("--max-pause", type=float, default=0.0, help="cut pauses inside sections to this (s); 0 = keep")
    p.add_argument("--settings", default="", help='JSON over the locked voice_settings, e.g. {"stability": 0.35, "style": 0.3} '
                                                 "(a test take only; the preset file stays the default)")
    a = p.parse_args()
    if a.settings:
        PRESET["voice_settings"] = {**PRESET["voice_settings"], **json.loads(a.settings)}
    os.makedirs(a.out_dir, exist_ok=True)
    secs = parse(a.narration)
    only = set(filter(None, a.only.split(",")))
    jobs = []
    with ThreadPoolExecutor(3) as ex:
        for i, s in enumerate(secs):
            if only and s["id"] not in only:
                continue
            prev_t = secs[i - 1]["text"] if i else ""
            next_t = secs[i + 1]["text"] if i + 1 < len(secs) else ""
            jobs.append(ex.submit(render, s, prev_t, next_t, a.out_dir))
        for j in jobs:
            print("rendered", *j.result())

    # join sections with gaps -> raw track + timeline
    concat, timeline, t = [], [], 0.0
    ids = [s["id"] for s in secs]
    title_i = ids.index(a.title_after) + 1 if a.title_after in ids else 1
    after = {k: float(v) for k, v in (x.split("=") for x in a.gap_after.split(",") if x)}
    bpath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(a.narration))), "bites.json")
    bspec = json.load(open(bpath, encoding="utf-8")) if os.path.exists(bpath) else {}
    bites = []
    sr = 44100
    for i, s in enumerate(secs):
        mp3 = os.path.join(a.out_dir, f"{s['id']}.mp3")
        if not os.path.exists(mp3):
            sys.exit(f"missing {mp3}")
        if i:
            g = after.get(secs[i - 1]["id"], a.open_gap if i == title_i else a.gap)
            sil = os.path.join(a.out_dir, f"_gap{i}.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
                            "-t", str(g), sil], check=True)
            concat.append(sil)
            t += g
        wav = os.path.join(a.out_dir, f"_{s['id']}.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", str(sr), "-ac", "1", wav], check=True)
        al = json.load(open(os.path.join(a.out_dir, f"{s['id']}.align.json")))
        if a.max_pause and al:
            al, cut_s = tighten(wav, al, a.max_pause)
            print(f"  {s['id']}: pauses cut by {cut_s:.2f} s")
        if s["bites"] and al:
            al, placed = insert_bites(wav, al, s["bites"], bspec)
            for name, tb in placed:
                bites.append({**{k: v for k, v in bspec[name].items() if k in ("who", "when", "said", "hi", "subs", "video")},
                              "name": name, "sec": s["id"], "t": round(t + tb, 3), "d": float(bspec[name]["d"])})
                print(f"  {s['id']}: [bite:{name}] at {t + tb:.2f} s ({bspec[name]['d']} s)")
        dur = duration(wav)
        timeline.append({"id": s["id"], "start": round(t, 3), "end": round(t + dur, 3),
                         "chars": al["characters"] if al else [],
                         "char_start": [round(t + x, 3) for x in (al["character_start_times_seconds"] if al else [])]})
        concat.append(wav)
        t += dur
    lst = os.path.join(a.out_dir, "_concat.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in concat))
    raw = os.path.join(a.out_dir, "narration_raw.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw], check=True)
    final = os.path.join(a.out_dir, "narration.wav")
    subprocess.run(["bash", os.path.join(ROOT, "scripts", "elevenlabs", "voice_post.sh"), raw, final, "0"], check=True)
    mix_bites(final, bites, bspec)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-c:a", "libmp3lame", "-b:a", "192k",
                    os.path.join(a.out_dir, "narration.mp3")], check=True)
    json.dump({"total": round(t, 3), "sections": timeline, "bites": sorted(bites, key=lambda b: b["t"])}, open(os.path.join(a.out_dir, "timeline.json"), "w"),
              ensure_ascii=False)
    for s in timeline:
        print(f"{s['id']:10s} {s['start']:7.2f} -> {s['end']:7.2f}  ({s['end'] - s['start']:5.1f}s)")
    print(f"TOTAL {int(t // 60)}:{t % 60:04.1f}")


if __name__ == "__main__":
    main()
