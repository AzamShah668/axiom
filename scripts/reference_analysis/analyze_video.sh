#!/usr/bin/env bash
# Measure a reference video: shots, transitions, camera moves, text, music, SFX, voice, pacing.
#
# Usage: analyze_video.sh <video.mp4> <outdir> [report.py options, e.g. --topic "sun,सूरज" --meta meta.json --sections 0,95,...]
#
# Every step is skipped when its output exists, so a stopped run resumes. Outputs in <outdir>:
#   probe.json, scenes/*.csv (PySceneDetect), sheets/ (1 frame / 2 s), audio/ (mix, Demucs stems, audio_stats.json,
#   music_map.jpg), transcript/ (words.json, transcript.txt), visual.json + shots/, text_events.json + text/,
#   report.md + summary.json + sequences/ (10 fps x 2 s strips of every event type).
# Env: PY (venv python: scripts/requirements-science.txt + requirements-analysis.txt), WHISPER_MODEL (medium),
#      LANG_CODE (whisper language, default detect), OCR_LANGS (hi,en), OCR_STEP (0.5 s).
# Never commit anything in <outdir>: it is other people's video, audio and words. Keep it on Drive.
set -euo pipefail
V="$1"; O="$2"; shift 2
PY="${PY:-python3}"
H=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$O"/{scenes,sheets,frames,audio,transcript}
todo() { if [ -s "$1" ]; then echo "--- skip $2 (done)"; return 1; fi; echo "=== $2"; }

todo "$O/probe.json" probe && ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,bit_rate \
  -show_entries format=duration,bit_rate -of json "$V" > "$O/probe.json"

# 1) shots (adaptive = robust to camera motion; content = hard cuts)
if todo "$O/scenes/content.csv" scenes; then
  "$PY" -m scenedetect -i "$V" -o "$O/scenes" detect-adaptive list-scenes -f adaptive.csv -q >/dev/null 2>&1 || true
  "$PY" -m scenedetect -i "$V" -o "$O/scenes" detect-content -t 27 list-scenes -f content.csv -q >/dev/null 2>&1 || true
fi

# 2) timeline contact sheets: 1 frame every 2 s, 6x5 grid, timestamp burned in
if todo "$O/sheets/sheet_01.jpg" sheets; then
  ffmpeg -v error -y -i "$V" -vf "fps=1/2:round=up,scale=320:-2,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6" -q:v 4 "$O/frames/f_%04d.jpg"
  ffmpeg -v error -y -pattern_type glob -i "$O/frames/f_*.jpg" -vf "tile=6x5:padding=4:margin=4" -q:v 3 "$O/sheets/sheet_%02d.jpg"
fi

# 3) audio: full mix + Demucs 4 stems (vocals, drums, bass, other) + no_vocals = drums + bass + other
D="$O/audio/demucs/htdemucs/mix"
todo "$O/audio/mix.wav" "audio mix" && ffmpeg -v error -y -i "$V" -ac 2 -ar 44100 "$O/audio/mix.wav"
if todo "$D/vocals.wav" demucs; then
  "$PY" -m demucs -n htdemucs -o "$O/audio/demucs" "$O/audio/mix.wav"
fi
todo "$D/no_vocals.wav" "no_vocals stem" && ffmpeg -v error -y -i "$D/drums.wav" -i "$D/bass.wav" -i "$D/other.wav" \
  -filter_complex "amix=inputs=3:normalize=0" "$D/no_vocals.wav"
if todo "$O/audio/loudness.txt" "EBU R128 (ffmpeg cross-check)"; then
  for f in mix demucs/htdemucs/mix/vocals demucs/htdemucs/mix/no_vocals; do
    echo "== $f" >> "$O/audio/loudness.txt"
    ffmpeg -nostats -i "$O/audio/$f.wav" -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary:/,$p' >> "$O/audio/loudness.txt"
  done
fi

# 4) words with timestamps (voice stem)
todo "$O/transcript/words.json" transcript && "$PY" "$H/transcribe.py" "$D/vocals.wav" "$O/transcript" \
  --model "${WHISPER_MODEL:-medium}" ${LANG_CODE:+--lang "$LANG_CODE"}

# 5) audio measurements
todo "$O/audio/audio_stats.json" "audio stats" && "$PY" "$H/audio_stats.py" "$O/audio" --words "$O/transcript/words.json"

# 6) visual measurements
todo "$O/visual.json" "visual stats" && "$PY" "$H/visual_stats.py" "$V" "$O"

# 7) on-screen text
todo "$O/text_events.json" "text tracking" && "$PY" "$H/text_track.py" "$V" "$O" --langs "${OCR_LANGS:-hi,en}" --step "${OCR_STEP:-0.5}"

# 8) report + frame strips (always re-run: cheap, and options may change)
echo "=== report"
"$PY" "$H/report.py" "$O" --video "$V" "$@"
echo "done: $O/report.md"
