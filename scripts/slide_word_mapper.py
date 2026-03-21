"""
Step 4D: Slide-to-Word Mapper
Combines Whisper word timestamps (4B) with scene timestamps (4C)
to create a per-slide segment map for precise video-audio sync.

Usage:
    python slide_word_mapper.py <transcript_json> <scenes_json> <output_dir>

Output:
    <output_dir>/slide_map.json
"""

import json
import sys
import os


def find_closest_word_boundary(words, target_time):
    """Find the word index whose start time is closest to target_time."""
    if not words:
        return 0

    best_idx = 0
    best_diff = abs(words[0]["start"] - target_time)

    for i, w in enumerate(words):
        diff = abs(w["start"] - target_time)
        if diff < best_diff:
            best_diff = diff
            best_idx = i

    return best_idx


def map_slides_to_words(transcript_path, scenes_path, output_dir):
    """Map each slide/scene to its corresponding transcript words."""
    print("=" * 60)
    print("STEP 4D: Slide-to-Word Mapper")
    print("=" * 60)

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    with open(scenes_path, "r", encoding="utf-8") as f:
        scenes_data = json.load(f)

    words = transcript["words"]
    scenes = scenes_data["scenes"]

    print(f"  Words: {len(words)}")
    print(f"  Scenes: {len(scenes)}")

    segments = []

    for i, scene in enumerate(scenes):
        scene_start = scene["timestamp"]
        scene_end = scene["end"]

        # Find the word indices that fall within this scene's time range
        word_start_idx = find_closest_word_boundary(words, scene_start)

        if i < len(scenes) - 1:
            # For non-last scenes, end at the start of next scene's first word
            word_end_idx = find_closest_word_boundary(words, scene_end) - 1
        else:
            # Last scene gets all remaining words
            word_end_idx = len(words) - 1

        # Ensure valid range
        word_start_idx = max(0, min(word_start_idx, len(words) - 1))
        word_end_idx = max(word_start_idx, min(word_end_idx, len(words) - 1))

        # Extract the text for this segment
        segment_words = words[word_start_idx:word_end_idx + 1]
        segment_text = " ".join(w["word"] for w in segment_words)

        # TTS timestamps for this segment (original audio timing)
        tts_start = words[word_start_idx]["start"] if segment_words else scene_start
        tts_end = words[word_end_idx]["end"] if segment_words else scene_end

        segments.append({
            "slide_index": i,
            "video_start": round(scene_start, 3),
            "video_end": round(scene_end, 3),
            "video_duration": round(scene_end - scene_start, 3),
            "word_start_index": word_start_idx,
            "word_end_index": word_end_idx,
            "word_count": len(segment_words),
            "original_audio_start": round(tts_start, 3),
            "original_audio_end": round(tts_end, 3),
            "text": segment_text
        })

    output = {
        "total_segments": len(segments),
        "total_words": len(words),
        "segments": segments
    }

    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "slide_map.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Mapping results:")
    for seg in segments[:5]:
        print(f"    Slide {seg['slide_index']}: "
              f"video {seg['video_start']:.1f}-{seg['video_end']:.1f}s | "
              f"words [{seg['word_start_index']}-{seg['word_end_index']}] ({seg['word_count']} words)")
    if len(segments) > 5:
        print(f"    ... and {len(segments) - 5} more")
    print(f"  Output: {json_path}")

    return output


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python slide_word_mapper.py <transcript_json> <scenes_json> <output_dir>")
        sys.exit(1)

    map_slides_to_words(sys.argv[1], sys.argv[2], sys.argv[3])
