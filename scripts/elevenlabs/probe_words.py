"""Hear every new name and English term before the real recording (owner, 2026-10-27: a script must be right
the first time). Costs a few characters per term instead of a re-recorded section.

  python scripts/elevenlabs/probe_words.py productions/NN-slug/tts/narration.hi.md [--accept]

The terms tts_check.py lists as never heard are read in one request, each with up to three words either side
from its own sentence, then transcribed (faster-whisper, English) and compared with the spelling: "ok" or
"LISTEN". The audio goes to work/<NN-slug>/voice_probe/probe.mp3 (send it to the owner) with probe.txt (the
order). A term that comes out wrong gets a new spelling in narration.hi.md (Devanagari, the way it is said) and an
entry in productions/tts-lexicon.json "replace"; probe again. --accept adds the "ok" terms to "verified"."""
import difflib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import tts_check  # noqa: E402
from render_narration import ROOT, render  # noqa: E402


def snippet(term, sentence, n=3):
    words = sentence.split()
    tw = term.split()
    for i in range(len(words)):
        if [re.sub(r"[^\w']", "", w) for w in words[i:i + len(tw)]] == tw:
            return " ".join(words[max(0, i - n):i + len(tw) + n]).strip(" ,।")
    return term


def main():
    path = sys.argv[1]
    _, terms, ctx = tts_check.check(path, allow_pauses=True)
    if not terms:
        sys.exit("nothing new to probe")
    slug = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(path))))
    out = os.path.join(ROOT, "work", slug, "voice_probe")
    os.makedirs(out, exist_ok=True)
    order = list(terms)
    pieces = [snippet(t, ctx[t]) for t in order]
    text = "। ".join(pieces) + "।"
    for f in ("probe.mp3", "probe.align.json"):
        if os.path.exists(os.path.join(out, f)):
            os.remove(os.path.join(out, f))
    print(f"probing {len(order)} terms, {len(text)} characters")
    render({"id": "probe", "text": text}, "", "", out)
    al = json.load(open(os.path.join(out, "probe.align.json")))
    joined, cs, ce = "".join(al["characters"]), al["character_start_times_seconds"], al["character_end_times_seconds"]
    import numpy as np
    from faster_whisper import WhisperModel
    m = WhisperModel("medium", device="cpu", compute_type="int8")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(out, "probe.mp3"), "-ac", "1", "-ar", "16000",
                          "-f", "f32le", "-"], capture_output=True).stdout
    audio = np.frombuffer(raw, np.float32)
    lines, ok, pos = [], [], 0
    for t, p in zip(order, pieces):
        i = joined.find(p, pos)
        pos = i + len(p)
        a, b = cs[i], ce[i + len(p) - 1]
        seg = audio[int(max(0, a - 0.1) * 16000):int((b + 0.2) * 16000)]
        heard = " ".join(s.text for s in m.transcribe(seg, language="en")[0]).strip()
        norm = lambda x: re.sub(r"[^a-z]", "", x.lower())
        best = max((difflib.SequenceMatcher(None, norm(t), norm(w)).ratio()
                    for k in range(1, 4) for w in (" ".join(heard.split()[j:j + k]) for j in range(len(heard.split())))),
                   default=0.0)
        verdict = "ok" if best >= 0.75 else "LISTEN"
        if verdict == "ok":
            ok.append(t)
        lines.append(f"{a:6.1f}s  {verdict:6s} {t:30s} heard: {heard}")
    open(os.path.join(out, "probe.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"audio: {os.path.join(out, 'probe.mp3')}")
    if "--accept" in sys.argv and ok:
        lp = os.path.join(ROOT, "productions", "tts-lexicon.json")
        lex = json.load(open(lp, encoding="utf-8"))
        lex["verified"] = sorted(set(lex["verified"]) | {w for t in ok for w in t.split()}, key=str.lower)
        open(lp, "w", encoding="utf-8").write(json.dumps(lex, ensure_ascii=False, indent=1) + "\n")
        print(f"{len(ok)} terms added to verified")


if __name__ == "__main__":
    main()
