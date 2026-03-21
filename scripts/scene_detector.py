"""
Step 4C: Scene Detection (Slide Changes)
Uses FFmpeg scene detection to find slide/scene transitions in NotebookLM videos.

Usage:
    python scene_detector.py <video_path> <output_dir> [threshold]

Output:
    <output_dir>/scene_changes.json
"""

import subprocess
import json
import sys
import os
import re


DEFAULT_THRESHOLD = 0.3  # Scene change sensitivity (0-1, lower = more sensitive)


def get_duration(filepath):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", filepath],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def detect_scenes(video_path, output_dir, threshold=DEFAULT_THRESHOLD):
    """Detect scene/slide changes using FFmpeg scene filter."""
    print("=" * 60)
    print("STEP 4C: Scene Detection (Slide Changes)")
    print("=" * 60)

    video_duration = get_duration(video_path)
    print(f"  Video: {video_path}")
    print(f"  Duration: {video_duration:.1f}s")
    print(f"  Threshold: {threshold}")

    # FFmpeg scene detection: outputs timestamps where scene change score > threshold
    # -vf "select='gt(scene,T)',showinfo" prints frame info for selected frames
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-"
    ]

    print(f"  Running scene detection...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse showinfo output for timestamps
    # Format: [Parsed_showinfo...] n: 0 pts: 12345 pts_time:1.234 ...
    scenes = [{"frame": 0, "timestamp": 0.0}]  # Always include start

    for line in result.stderr.split("\n"):
        match = re.search(r"pts_time:\s*([0-9.]+)", line)
        if match:
            ts = round(float(match.group(1)), 3)
            # Skip if too close to a previous scene (< 1s apart = same transition)
            if scenes and ts - scenes[-1]["timestamp"] < 1.0:
                continue
            # Skip scenes in the last 3s (NotebookLM branding)
            if ts > video_duration - 3.0:
                continue
            scenes.append({
                "frame": len(scenes),
                "timestamp": ts
            })

    # Add end timestamps to each scene
    for i in range(len(scenes)):
        if i < len(scenes) - 1:
            scenes[i]["end"] = scenes[i + 1]["timestamp"]
            scenes[i]["duration"] = round(scenes[i]["end"] - scenes[i]["timestamp"], 3)
        else:
            # Last scene ends at video duration (minus branding trim)
            effective_end = max(0, video_duration - 3.0)
            scenes[i]["end"] = round(effective_end, 3)
            scenes[i]["duration"] = round(effective_end - scenes[i]["timestamp"], 3)

    output = {
        "source_video": os.path.basename(video_path),
        "video_duration": round(video_duration, 3),
        "threshold": threshold,
        "total_scenes": len(scenes),
        "scenes": scenes
    }

    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "scene_changes.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Results:")
    print(f"    Scenes detected: {len(scenes)}")
    for s in scenes[:5]:
        print(f"      Scene {s['frame']}: {s['timestamp']:.1f}s - {s['end']:.1f}s ({s['duration']:.1f}s)")
    if len(scenes) > 5:
        print(f"      ... and {len(scenes) - 5} more")
    print(f"    Output: {json_path}")

    return output


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scene_detector.py <video_path> <output_dir> [threshold]")
        sys.exit(1)

    video = sys.argv[1]
    out_dir = sys.argv[2]
    thresh = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_THRESHOLD

    detect_scenes(video, out_dir, thresh)
