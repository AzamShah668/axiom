"""Word-timed transcript of a reference video's voice stem (faster-whisper, CPU).

  python transcribe.py <vocals.wav> <out_dir> [--model medium] [--lang hi]

Writes words.json ({"language", "words": [{"w", "start", "end", "p"}], "segments": [...]}) and transcript.txt.
Transcripts are other people's text: keep them on Drive with the rest of the reference material, never commit them.
"""
import argparse, json, os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("out")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--lang", default=None, help="language code; default: detect")
    a = ap.parse_args()
    import numpy as np, soundfile as sf
    from scipy.signal import resample_poly
    from faster_whisper import WhisperModel
    x, sr = sf.read(a.wav, dtype="float32")
    x = x.mean(1) if x.ndim > 1 else x
    x = resample_poly(x, 16000, sr).astype(np.float32)  # decoded here: faster-whisper's own loader needs a newer PyAV
    m = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    segs, info = m.transcribe(x, language=a.lang, word_timestamps=True, vad_filter=True, beam_size=5,
                              condition_on_previous_text=False)
    words, out_segs = [], []
    for s in segs:
        out_segs.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        for w in s.words or []:
            words.append({"w": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2), "p": round(w.probability, 2)})
        print(f"  {s.start:7.1f} {s.text.strip()[:80]}", flush=True)
    os.makedirs(a.out, exist_ok=True)
    json.dump({"language": info.language, "language_p": round(info.language_probability, 2), "words": words, "segments": out_segs},
              open(f"{a.out}/words.json", "w"), ensure_ascii=False, indent=0)
    open(f"{a.out}/transcript.txt", "w").write("\n".join(f"[{s['start']:7.1f}] {s['text']}" for s in out_segs))
    print(info.language, len(words), "words")


if __name__ == "__main__":
    main()
