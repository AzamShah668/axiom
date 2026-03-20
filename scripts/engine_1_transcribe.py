"""
Engine 1: Transcript Timestamp Generator
Uses OpenAI Whisper to generate word-level timestamps from the TTS audio.
Output: JSON file with word timestamps for Engine 2 sync.
"""

import whisper
import json
import sys
import os
import time

def run_engine_1(audio_path, output_path, model_size="base"):
    """
    Transcribe audio with word-level timestamps using Whisper.
    
    Args:
        audio_path: Path to the TTS-generated WAV file
        output_path: Path to save the timestamps JSON
        model_size: Whisper model size (tiny/base/small/medium)
    """
    print(f"Engine 1: Loading Whisper '{model_size}' model...")
    start = time.time()
    model = whisper.load_model(model_size)
    print(f"  Model loaded in {time.time() - start:.1f}s")

    print(f"Engine 1: Transcribing {audio_path}...")
    start = time.time()
    result = model.transcribe(
        audio_path,
        language="en",
        word_timestamps=True,
        verbose=False
    )
    elapsed = time.time() - start
    print(f"  Transcription done in {elapsed:.1f}s")

    # Extract word-level timestamps
    words = []
    segments = []

    for seg in result.get("segments", []):
        seg_data = {
            "id": seg["id"],
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip(),
            "words": []
        }

        for w in seg.get("words", []):
            word_data = {
                "word": w["word"].strip(),
                "start": round(w["start"], 3),
                "end": round(w["end"], 3)
            }
            seg_data["words"].append(word_data)
            words.append(word_data)

        segments.append(seg_data)

    # Build output
    output = {
        "audio_file": os.path.basename(audio_path),
        "duration": round(result.get("segments", [{}])[-1].get("end", 0), 3) if result.get("segments") else 0,
        "total_words": len(words),
        "total_segments": len(segments),
        "full_text": result.get("text", "").strip(),
        "segments": segments,
        "words": words
    }

    # Save
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nEngine 1 Complete:")
    print(f"  Duration: {output['duration']:.1f}s")
    print(f"  Words: {output['total_words']}")
    print(f"  Segments: {output['total_segments']}")
    print(f"  Output: {output_path}")

    return output


if __name__ == "__main__":
    audio = sys.argv[1] if len(sys.argv) > 1 else "d:/notebook lm/data/quicksort_tts.wav"
    out = sys.argv[2] if len(sys.argv) > 2 else "d:/notebook lm/data/quicksort_timestamps.json"
    model = sys.argv[3] if len(sys.argv) > 3 else "base"

    run_engine_1(audio, out, model)
