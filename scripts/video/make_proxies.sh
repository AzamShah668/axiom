#!/usr/bin/env bash
# Make 1080p30 working proxies from 4K clip URLs (reads remote files directly).
# Usage: make_proxies.sh <list.txt: "name url" per line> <out_dir> [parallel=3]
set -uo pipefail
LIST="$1"; OUT="$2"; P="${3:-3}"
mkdir -p "$OUT"
one() {
  name="$1"; url="$2"; out="$3/$name.mp4"
  [ -s "$out" ] && return 0
  ffmpeg -v error -y -i "$url" -an -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -g 30 "$out.part.mp4" && mv "$out.part.mp4" "$out" \
    && echo "ok $name" || echo "FAIL $name"
}
export -f one
grep -v '^\s*$' "$LIST" | xargs -P "$P" -L 1 bash -c 'one "$0" "$1" "'"$OUT"'"'
