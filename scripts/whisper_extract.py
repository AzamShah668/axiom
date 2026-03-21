"""
Step 4B: Whisper Transcript Extraction
Extracts word-level transcript from a NotebookLM video's audio track.
Also trims the last 3s (NotebookLM branding) before transcription.

Usage:
    python whisper_extract.py <video_path> <output_dir> [model_size]

Outputs:
    <output_dir>/<safe_topic>_original_transcript.json  (word-level timestamps)
    <output_dir>/<safe_topic>_original_transcript.txt   (plain text for TTS)
"""

import whisper
import json
import sys
import os
import time
import subprocess
from pathlib import Path


TRIM_SECONDS = 3  # NotebookLM branding at end


def get_duration(filepath):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", filepath],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def trim_branding(video_path):
    """Trim last 3s of NotebookLM branding. Returns trimmed path."""
    duration = get_duration(video_path)
    trimmed_duration = max(0, duration - TRIM_SECONDS)

    base = Path(video_path)
    trimmed_path = str(base.parent / f"{base.stem}_trimmed{base.suffix}")

    print(f"  Trimming last {TRIM_SECONDS}s: {duration:.1f}s -> {trimmed_duration:.1f}s")

    cmd = ["ffmpeg", "-y", "-i", video_path, "-t", str(trimmed_duration), "-c", "copy", trimmed_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Trim failed, using original: {result.stderr[-200:]}")
        return video_path

    return trimmed_path


def extract_transcript(video_path, output_dir, model_size="base"):
    """Extract word-level transcript from video audio via Whisper."""
    print("=" * 60)
    print("STEP 4B: Whisper Transcript Extraction")
    print("=" * 60)

    # Trim branding first
    trimmed = trim_branding(video_path)

    print(f"\n  Loading Whisper '{model_size}' model...")
    start = time.time()
    model = whisper.load_model(model_size)
    print(f"  Model loaded in {time.time() - start:.1f}s")

    print(f"  Transcribing: {trimmed}")
    start = time.time()
    result = model.transcribe(trimmed, language="en", word_timestamps=True, verbose=False)
    elapsed = time.time() - start
    print(f"  Transcription done in {elapsed:.1f}s")

    # Build structured output
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

    full_text = result.get("text", "").strip()
    duration = segments[-1]["end"] if segments else 0

    output = {
        "source_video": os.path.basename(video_path),
        "duration": round(duration, 3),
        "total_words": len(words),
        "total_segments": len(segments),
        "full_text": full_text,
        "segments": segments,
        "words": words
    }

    # Save JSON (word-level timestamps)
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "original_transcript.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Save plain text (for TTS input)
    txt_path = os.path.join(output_dir, "original_transcript.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"\n  Results:")
    print(f"    Duration: {duration:.1f}s")
    print(f"    Words: {len(words)}")
    print(f"    Segments: {len(segments)}")
    print(f"    JSON: {json_path}")
    print(f"    Text: {txt_path}")

    # Cleanup trimmed file
    if trimmed != video_path and os.path.exists(trimmed):
        os.remove(trimmed)

    return output


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python whisper_extract.py <video_path> <output_dir> [model_size]")
        sys.exit(1)

    video = sys.argv[1]
    out_dir = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "base"

    extract_transcript(video, out_dir, model)
