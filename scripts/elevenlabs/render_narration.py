"""Render a sectioned Hindi narration with the locked voice preset.

  python render_narration.py <narration.hi.md> <out_dir> [--only cold_open,fact10] [--gap 1.2] [--open-gap 1.6]

For every "## <id>" section: calls ElevenLabs /with-timestamps (with neighbour text as context so
prosody flows across joins), saves <id>.mp3 + <id>.align.json. Then joins all sections with gaps
(chapter-card breathing room), applies the documentary finish and writes:
  narration.wav / narration.mp3   final voice track
  timeline.json                   section start/end + character timings on the final timeline
Re-running skips sections that already exist (delete a section's mp3 to re-render it).
"""
import argparse, base64, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

sys.path.insert(0, os.path.dirname(__file__))
from el import API, ROOT, _h  # noqa: E402  (loads config/.env)

PRESET = json.load(open(os.path.join(ROOT, "productions", "voice-preset.json")))


def parse(path):
    secs, cur = [], None
    for line in open(path, encoding="utf-8"):
        if line.startswith("## "):
            cur = {"id": line[3:].strip(), "text": ""}
            secs.append(cur)
        elif cur is not None and not line.startswith("#"):
            cur["text"] += line
    for s in secs:
        s["text"] = s["text"].strip()
    return secs


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
    a = p.parse_args()
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
    sr = 44100
    for i, s in enumerate(secs):
        mp3 = os.path.join(a.out_dir, f"{s['id']}.mp3")
        if not os.path.exists(mp3):
            sys.exit(f"missing {mp3}")
        if i:
            g = a.open_gap if i == 1 else a.gap
            sil = os.path.join(a.out_dir, f"_gap{i}.wav")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
                            "-t", str(g), sil], check=True)
            concat.append(sil)
            t += g
        wav = os.path.join(a.out_dir, f"_{s['id']}.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", str(sr), "-ac", "1", wav], check=True)
        dur = duration(wav)
        al = json.load(open(os.path.join(a.out_dir, f"{s['id']}.align.json")))
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
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-c:a", "libmp3lame", "-b:a", "192k",
                    os.path.join(a.out_dir, "narration.mp3")], check=True)
    json.dump({"total": round(t, 3), "sections": timeline}, open(os.path.join(a.out_dir, "timeline.json"), "w"),
              ensure_ascii=False)
    for s in timeline:
        print(f"{s['id']:10s} {s['start']:7.2f} -> {s['end']:7.2f}  ({s['end'] - s['start']:5.1f}s)")
    print(f"TOTAL {int(t // 60)}:{t % 60:04.1f}")


if __name__ == "__main__":
    main()
