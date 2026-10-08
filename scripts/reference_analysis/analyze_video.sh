#!/usr/bin/env bash
# Usage: analyze_video.sh <video.mp4> <outdir>
# Produces: scene list, contact sheets (1 frame / 2s), per-shot keyframes, audio stems + loudness stats.
set -euo pipefail
V="$1"; O="$2"
PY="${PY:-python3}"  # needs: scenedetect opencv-python-headless demucs librosa soundfile
mkdir -p "$O"/{scenes,sheets,frames,audio}

ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,bit_rate -show_entries format=duration,bit_rate -of json "$V" > "$O/probe.json"

# 1) Shot detection (adaptive = robust to camera motion; content = hard cuts)
"$PY" -m scenedetect -i "$V" -o "$O/scenes" detect-adaptive list-scenes -f adaptive.csv -q >/dev/null 2>&1 || true
"$PY" -m scenedetect -i "$V" -o "$O/scenes" detect-content -t 27 list-scenes -f content.csv -q >/dev/null 2>&1 || true

# 2) Timeline contact sheets: 1 frame every 2s, 6x5 grid, timestamp burned in
ffmpeg -v error -y -i "$V" -vf "fps=1/2,scale=320:-2,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6" -q:v 4 "$O/frames/f_%04d.jpg"
ffmpeg -v error -y -pattern_type glob -i "$O/frames/f_*.jpg" -vf "tile=6x5:padding=4:margin=4" -q:v 3 "$O/sheets/sheet_%02d.jpg"

# 3) Audio: full mix + demucs voice/music separation
ffmpeg -v error -y -i "$V" -ac 2 -ar 44100 "$O/audio/mix.wav"
"$PY" -m demucs --two-stems=vocals -n htdemucs -o "$O/audio/demucs" "$O/audio/mix.wav" >/dev/null 2>&1 || echo "demucs failed"

for f in mix demucs/htdemucs/mix/vocals demucs/htdemucs/mix/no_vocals; do
  [ -f "$O/audio/$f.wav" ] || continue
  echo "== $f" >> "$O/audio/loudness.txt"
  ffmpeg -nostats -i "$O/audio/$f.wav" -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary:/,$p' >> "$O/audio/loudness.txt"
done
echo "done: $O"
