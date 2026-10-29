"""Listen to every newly recorded section before anything is built on it (owner, 2026-10-27).

  python scripts/elevenlabs/speech_check.py productions/NN-slug/tts/narration.hi.md <voice_dir>

For each section mp3 not checked yet (voice_dir/speech_check.json remembers the checked ones):
- every name and English term in the text must be heard in an English transcript (faster-whisper medium)
- the Hindi transcript must not hold more नहीं than the text (Neel's नए sounded like नहीं and flipped a line)
Prints FLAG lines (exit 1) with the section and term. Listen to each: the English transcript is a translation and
can drop a place name ("America के New Jersey में" -> "In New Jersey"). A real misread: fix the spelling
(tts-lexicon.json), re-record that section."""
import difflib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from render_narration import parse  # noqa: E402


def norm(x):
    return re.sub(r"[^a-z]", "", x.lower())


def heard(term, text):
    w = text.split()
    return max((difflib.SequenceMatcher(None, norm(term), norm(" ".join(w[j:j + k]))).ratio()
                for k in range(1, 4) for j in range(len(w))), default=0.0) >= 0.72


def main():
    narr, vdir = sys.argv[1:3]
    import numpy as np
    from faster_whisper import WhisperModel
    cache_p = os.path.join(vdir, "speech_check.json")
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}
    m, flags = None, []
    for s in parse(narr):
        mp3 = os.path.join(vdir, s["id"] + ".mp3")
        if not os.path.exists(mp3):
            continue
        stamp = f"{os.path.getsize(mp3)}:{int(os.path.getmtime(mp3))}"
        if cache.get(s["id"], {}).get("stamp") == stamp:
            flags += cache[s["id"]]["flags"]
            continue
        m = m or WhisperModel("medium", device="cpu", compute_type="int8")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             capture_output=True).stdout
        audio = np.frombuffer(raw, np.float32)
        en = " ".join(x.text for x in m.transcribe(audio, language="en")[0])
        hi = " ".join(x.text for x in m.transcribe(audio, language="hi")[0])
        f = []
        hinglish = not re.search(r"[\u0900-\u097F]", s["text"])
        terms = set()
        for mt in re.finditer(r"\b[A-Z][\w'’]+(?:\s+[A-Z][\w'’]+)*", s["text"]):
            t = mt.group(0)
            if hinglish and re.search(r"(^|[.?!।\"]\s*)$", s["text"][:mt.start()]):  # a sentence's first word
                t = " ".join(t.split()[1:])
            if t:
                terms.add(t)
        f += [f"{s['id']}: '{t}' not heard (English transcript)" for t in sorted(terms) if not heard(t, en)]
        written = s["text"].count("नहीं") + len(re.findall(r"\bnahi?n?\b", s["text"], re.I))  # Devanagari or Hinglish
        if hi.count("नहीं") > written:
            f.append(f"{s['id']}: नहीं heard {hi.count('नहीं')}x, written {written}x: a line may flip its meaning")
        cache[s["id"]] = {"stamp": stamp, "flags": f, "en": en}
        json.dump(cache, open(cache_p, "w"), ensure_ascii=False, indent=1)
        print(f"{s['id']}: {'ok' if not f else str(len(f)) + ' flags'}", flush=True)
        flags += f
    for x in flags:
        print("FLAG", x)
    sys.exit(1 if flags else 0)


if __name__ == "__main__":
    main()
