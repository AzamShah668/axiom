#!/usr/bin/env bash
# Split a master into 720p preview parts that each fit a 30 MiB chat upload (2-pass).
#   preview_parts.sh <master.mp4> <out_dir> [parts]
# Each part targets 28 MiB: the video bitrate is computed from the part length. Without [parts], long
# masters get as many parts (at least 3) as it takes to keep the video bitrate at ~700 kb/s or more.
set -euo pipefail
in=$1; out=$2
mkdir -p "$out"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
budget=$(python3 -c "print(28 * 1048576 * 8 / 1000 * 0.95)")   # kbit per part, 5% container margin
parts=${3:-$(python3 -c "import math; print(max(3, math.ceil($dur * (700 + 96) / $budget)))")}
len=$(python3 -c "print($dur / $parts)")
vb=$(python3 -c "print(int($budget / $len - 96))")
base=$(basename "${in%.*}")
rm -f "$out"/"${base}"-part*.mp4
enc() {
  n=$1; ss=$(python3 -c "print(($n-1)*$len)")
  ( cd "$out" && ffmpeg -v error -y -ss "$ss" -t "$len" -i "$in" -vf scale=1280:720 -c:v libx264 -preset medium -b:v "${vb}k" \
      -maxrate "$((vb * 3 / 2))k" -bufsize "$((vb * 3))k" -pass 1 -passlogfile "p$n" -an -f null - &&
    ffmpeg -v error -y -ss "$ss" -t "$len" -i "$in" -vf scale=1280:720 -c:v libx264 -preset medium -b:v "${vb}k" \
      -maxrate "$((vb * 3 / 2))k" -bufsize "$((vb * 3))k" -pass 2 -passlogfile "p$n" -c:a aac -b:a 96k -movflags +faststart "${base}-part$n.mp4" &&
    rm -f "p$n"*.log* )
}
echo "$parts parts of $(python3 -c "print(round($len))") s at ${vb}k"
for n in $(seq 1 "$parts"); do enc "$n" & done
wait
ls -la "$out"/"${base}"-part*.mp4
