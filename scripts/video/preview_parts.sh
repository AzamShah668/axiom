#!/usr/bin/env bash
# Split a master into 720p preview parts that each fit a 30 MB chat upload (2-pass, ~800 kb/s video).
#   preview_parts.sh <master.mp4> <out_dir> [parts=3]
set -euo pipefail
in=$1; out=$2; parts=${3:-3}
mkdir -p "$out"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
len=$(python3 -c "print($dur/$parts)")
base=$(basename "${in%.*}")
enc() {
  n=$1; ss=$(python3 -c "print(($n-1)*$len)")
  ( cd "$out" && ffmpeg -v error -y -ss "$ss" -t "$len" -i "$in" -vf scale=1280:720 -c:v libx264 -preset medium -b:v 800k \
      -maxrate 1200k -bufsize 2400k -pass 1 -passlogfile "p$n" -an -f null - &&
    ffmpeg -v error -y -ss "$ss" -t "$len" -i "$in" -vf scale=1280:720 -c:v libx264 -preset medium -b:v 800k \
      -maxrate 1200k -bufsize 2400k -pass 2 -passlogfile "p$n" -c:a aac -b:a 96k -movflags +faststart "${base}-part$n.mp4" &&
    rm -f "p$n"*.log* )
}
for n in $(seq 1 "$parts"); do enc "$n" & done
wait
ls -la "$out"/"${base}"-part*.mp4
