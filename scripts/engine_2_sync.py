"""
Engine 2: Visual Slicer & Forced Alignment Sync
1. Transcribes original video audio with Whisper (word timestamps)
2. Aligns original transcript segments to TTS transcript segments
3. Time-maps video segments to match TTS pacing
4. Assembles final video with TTS audio overlay
"""

import whisper
import json
import subprocess
import sys
import os
import time
import tempfile
from pathlib import Path


def get_duration(filepath):
    """Get media duration in seconds via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", filepath],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def transcribe_original(video_path, model_size="base"):
    """Transcribe the original video's audio to get segment timestamps."""
    print("Engine 2: Transcribing original video audio...")
    model = whisper.load_model(model_size)
    result = model.transcribe(video_path, language="en", word_timestamps=True, verbose=False)

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip()
        })
    return segments


def align_segments(orig_segments, tts_timestamps_path):
    """
    Create time mapping between original video and TTS audio.
    Uses proportional alignment: maps each original segment to
    a proportional position in the TTS timeline.
    """
    with open(tts_timestamps_path, "r", encoding="utf-8") as f:
        tts_data = json.load(f)

    orig_duration = orig_segments[-1]["end"] if orig_segments else 0
    tts_duration = tts_data["duration"]
    tts_segments = tts_data["segments"]

    print(f"  Original duration: {orig_duration:.1f}s")
    print(f"  TTS duration: {tts_duration:.1f}s")
    print(f"  Original segments: {len(orig_segments)}")
    print(f"  TTS segments: {len(tts_segments)}")

    # Build alignment keypoints using proportional mapping
    # Each original segment maps to the same proportional position in TTS
    keypoints = []
    for orig_seg in orig_segments:
        proportion_start = orig_seg["start"] / orig_duration if orig_duration > 0 else 0
        proportion_end = orig_seg["end"] / orig_duration if orig_duration > 0 else 0

        tts_start = proportion_start * tts_duration
        tts_end = proportion_end * tts_duration

        keypoints.append({
            "orig_start": orig_seg["start"],
            "orig_end": orig_seg["end"],
            "tts_start": round(tts_start, 3),
            "tts_end": round(tts_end, 3),
            "speed": (orig_seg["end"] - orig_seg["start"]) / max(tts_end - tts_start, 0.01)
        })

    return keypoints, tts_duration


def build_synced_video(video_path, tts_audio_path, keypoints, tts_duration, output_path):
    """
    Build the final synced video:
    1. Adjust video speed to match TTS duration
    2. Overlay TTS audio
    """
    orig_duration = get_duration(video_path)
    speed_factor = orig_duration / tts_duration

    print(f"\nEngine 2: Building synced video...")
    print(f"  Speed factor: {speed_factor:.4f}x")
    print(f"  Target duration: {tts_duration:.1f}s")

    # Use FFmpeg to:
    # 1. Adjust video speed with setpts filter
    # 2. Replace audio with TTS
    setpts = f"PTS*{1/speed_factor:.6f}"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", tts_audio_path,
        "-filter_complex",
        f"[0:v]setpts={setpts}[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]

    print(f"  Running FFmpeg...")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        return False

    elapsed = time.time() - start
    final_size = Path(output_path).stat().st_size / (1024 * 1024)
    final_dur = get_duration(output_path)

    print(f"  FFmpeg done in {elapsed:.1f}s")
    print(f"  Output: {output_path}")
    print(f"  Size: {final_size:.1f} MB")
    print(f"  Duration: {final_dur:.1f}s")

    return True


def run_engine_2(video_path, tts_audio_path, tts_timestamps_path, output_path, model_size="base"):
    """Full Engine 2 pipeline."""
    print("=" * 60)
    print("ENGINE 2: Visual Slicer & Forced Alignment Sync")
    print("=" * 60)

    # Step 1: Transcribe original video
    orig_segments = transcribe_original(video_path, model_size)

    # Step 2: Align original segments to TTS timeline
    print("\nEngine 2: Aligning segments...")
    keypoints, tts_duration = align_segments(orig_segments, tts_timestamps_path)

    # Save alignment data
    alignment_path = tts_timestamps_path.replace("timestamps", "alignment")
    with open(alignment_path, "w", encoding="utf-8") as f:
        json.dump({
            "original_segments": len(orig_segments),
            "keypoints": keypoints,
            "tts_duration": tts_duration
        }, f, indent=2)
    print(f"  Alignment saved: {alignment_path}")

    # Step 3: Build synced video
    success = build_synced_video(video_path, tts_audio_path, keypoints, tts_duration, output_path)

    if success:
        print("\n" + "=" * 60)
        print("ENGINE 2 COMPLETE ✅")
        print(f"  Final video: {output_path}")
        print("=" * 60)
    else:
        print("\nENGINE 2 FAILED ❌")

    return success


if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else "d:/notebook lm/Demystifying_Quicksort.mp4"
    tts_audio = sys.argv[2] if len(sys.argv) > 2 else "d:/notebook lm/data/quicksort_tts.wav"
    tts_timestamps = sys.argv[3] if len(sys.argv) > 3 else "d:/notebook lm/data/quicksort_timestamps.json"
    output = sys.argv[4] if len(sys.argv) > 4 else "d:/notebook lm/output/videos/quicksort_final.mp4"

    # Ensure output directory exists
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    run_engine_2(video, tts_audio, tts_timestamps, output)
