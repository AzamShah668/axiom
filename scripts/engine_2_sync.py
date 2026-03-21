"""
Engine 2 v2: Per-Slide Segment Sync
Replaces the old proportional speed adjustment with precise per-slide alignment.

For each slide detected by scene_detector:
1. Find the corresponding TTS word timestamps
2. Calculate per-slide speed factor
3. Use FFmpeg setpts to stretch/compress that video segment
4. Concatenate all adjusted segments + overlay main TTS audio

Usage:
    python engine_2_sync.py <video_path> <main_tts_audio> <slide_map_json> <tts_timestamps_json> <output_path>

Inputs:
    video_path         - NotebookLM video (already trimmed or raw)
    main_tts_audio     - Main section TTS WAV (from tts_segmenter)
    slide_map_json     - Slide-to-word mapping (from slide_word_mapper)
    tts_timestamps_json - Whisper timestamps of the full TTS audio
    output_path        - Final synced video output

The slide_map tells us which words belong to which slide.
The tts_timestamps tell us when OUR voice says each word.
By comparing slide video duration vs TTS word duration, we stretch/compress each slide independently.
"""

import json
import subprocess
import sys
import os
import time
import tempfile
from pathlib import Path


TRIM_SECONDS = 3  # NotebookLM branding at end


def get_duration(filepath):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", filepath],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def trim_branding(video_path):
    """Trim last 3s of NotebookLM branding."""
    duration = get_duration(video_path)
    trimmed_duration = max(0, duration - TRIM_SECONDS)

    base = Path(video_path)
    trimmed_path = str(base.parent / f"{base.stem}_trimmed{base.suffix}")

    cmd = ["ffmpeg", "-y", "-i", video_path, "-t", str(trimmed_duration), "-c", "copy", trimmed_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Trim failed, using original: {result.stderr[-200:]}")
        return video_path

    print(f"  Trimmed: {duration:.1f}s -> {trimmed_duration:.1f}s")
    return trimmed_path


def extract_slide_segment(video_path, start, end, output_path):
    """Extract a video segment without re-encoding."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", f"{start:.3f}",
        "-t", f"{end - start:.3f}",
        "-c", "copy",
        "-an",  # Strip audio — we'll add TTS later
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def speed_adjust_segment(input_path, speed_factor, output_path):
    """Adjust video speed using setpts filter."""
    # setpts: PTS / speed_factor speeds up, PTS * (1/speed_factor) slows down
    # We want: if speed_factor > 1, video plays faster (compress); if < 1, slower (stretch)
    pts_factor = 1.0 / speed_factor if speed_factor > 0 else 1.0

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", f"[0:v]setpts={pts_factor:.6f}*PTS[v]",
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-an",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def run_engine_2(video_path, main_tts_audio, slide_map_path, tts_timestamps_path, output_path):
    """Per-slide sync engine."""
    print("=" * 60)
    print("ENGINE 2 v2: Per-Slide Segment Sync")
    print("=" * 60)

    # Load data
    with open(slide_map_path, "r", encoding="utf-8") as f:
        slide_map = json.load(f)

    with open(tts_timestamps_path, "r", encoding="utf-8") as f:
        tts_data = json.load(f)

    tts_words = tts_data["words"]
    segments = slide_map["segments"]

    # We need to map the slide_map word indices to the MAIN section of the TTS.
    # The tts_timestamps cover the full script (intro+main+outro).
    # The slide_map word indices are relative to the ORIGINAL transcript.
    # But the main_tts_audio is already segmented — its word indices start at 0.
    # So we need to find the offset: intro words are not in the main audio.
    #
    # HOWEVER: the tts_timestamps passed here should be from the MAIN audio segment only
    # (run Whisper on main_audio.wav, not full_tts.wav).
    # If that's the case, word indices align directly with slide_map.

    print(f"\n  Slides: {len(segments)}")
    print(f"  TTS words: {len(tts_words)}")

    # Trim branding
    trimmed = trim_branding(video_path)

    # Create temp directory for slide segments
    tmp_dir = tempfile.mkdtemp(prefix="engine2_")
    segment_files = []

    print(f"\n  Processing {len(segments)} slides...")

    for seg in segments:
        slide_idx = seg["slide_index"]
        v_start = seg["video_start"]
        v_end = seg["video_end"]
        v_duration = v_end - v_start

        word_start = seg["word_start_index"]
        word_end = seg["word_end_index"]

        # Find TTS timing for these words
        # Clamp indices to available words
        ws = min(word_start, len(tts_words) - 1)
        we = min(word_end, len(tts_words) - 1)

        if ws < len(tts_words) and we < len(tts_words):
            tts_start = tts_words[ws]["start"]
            tts_end = tts_words[we]["end"]
            tts_duration = tts_end - tts_start
        else:
            # Fallback: proportional
            tts_duration = v_duration

        # Avoid division by zero
        if tts_duration < 0.1:
            tts_duration = v_duration

        speed_factor = v_duration / tts_duration

        # Clamp speed factor to reasonable range (0.5x to 2.0x)
        speed_factor = max(0.5, min(2.0, speed_factor))

        print(f"    Slide {slide_idx}: video {v_start:.1f}-{v_end:.1f}s ({v_duration:.1f}s) -> "
              f"TTS {tts_duration:.1f}s | speed: {speed_factor:.2f}x")

        # Extract video segment
        raw_segment = os.path.join(tmp_dir, f"slide_{slide_idx:03d}_raw.mp4")
        if not extract_slide_segment(trimmed, v_start, v_end, raw_segment):
            print(f"      Failed to extract slide {slide_idx}, using proportional fallback")
            continue

        # Speed-adjust if needed (skip if close to 1.0x)
        if abs(speed_factor - 1.0) < 0.05:
            segment_files.append(raw_segment)
        else:
            adjusted = os.path.join(tmp_dir, f"slide_{slide_idx:03d}_adj.mp4")
            if speed_adjust_segment(raw_segment, speed_factor, adjusted):
                segment_files.append(adjusted)
            else:
                print(f"      Speed adjustment failed for slide {slide_idx}, using raw")
                segment_files.append(raw_segment)

    if not segment_files:
        print("\n  No segments processed! Falling back to simple speed adjustment.")
        return fallback_sync(trimmed, main_tts_audio, output_path)

    # Concatenate all adjusted segments
    print(f"\n  Concatenating {len(segment_files)} adjusted segments...")
    concat_list = os.path.join(tmp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for sf in segment_files:
            f.write(f"file '{sf}'\n")

    concat_video = os.path.join(tmp_dir, "concat_video.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-an",
        concat_video
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Concat failed: {result.stderr[-500:]}")
        return fallback_sync(trimmed, main_tts_audio, output_path)

    # Overlay TTS audio onto concatenated video
    print("  Overlaying TTS audio...")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", concat_video,
        "-i", main_tts_audio,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Audio overlay failed: {result.stderr[-500:]}")
        return False

    final_dur = get_duration(output_path)
    final_size = Path(output_path).stat().st_size / (1024 * 1024)

    print(f"\n  {'=' * 50}")
    print(f"  ENGINE 2 v2 COMPLETE")
    print(f"  Output: {output_path}")
    print(f"  Duration: {final_dur:.1f}s | Size: {final_size:.1f} MB")
    print(f"  {'=' * 50}")

    # Cleanup temp files
    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except:
        pass

    # Cleanup trimmed file
    if trimmed != video_path and os.path.exists(trimmed):
        try:
            os.remove(trimmed)
        except:
            pass

    return True


def fallback_sync(video_path, tts_audio_path, output_path):
    """Simple proportional sync as fallback if per-slide fails."""
    print("\n  Using fallback: proportional speed adjustment...")

    v_dur = get_duration(video_path)
    a_dur = get_duration(tts_audio_path)
    speed = v_dur / a_dur
    pts = 1.0 / speed

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", tts_audio_path,
        "-filter_complex", f"[0:v]setpts={pts:.6f}*PTS[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python engine_2_sync.py <video> <main_tts_wav> <slide_map_json> <tts_timestamps_json> <output>")
        sys.exit(1)

    success = run_engine_2(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    sys.exit(0 if success else 1)
