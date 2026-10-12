#!/usr/bin/env bash
# Shared media for every science-channel render: fonts, music bed tracks, stills used by the graphics.
#   fetch_media.sh <media_dir> [track names...]    (default: the dark-ambient set used by production 01)
# Music: Kevin MacLeod (incompetech.com), CC BY 4.0 - credits.py writes the attribution line.
set -euo pipefail
dir=$1; shift || true
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$dir/fonts" "$dir/music" "$dir/assets"
gf=https://raw.githubusercontent.com/google/fonts/main/ofl
get() { [ -s "$2" ] || curl -sfL --retry 3 -o "$2" "$1" || { echo "failed: $1"; rm -f "$2"; }; }
get "$gf/anton/Anton-Regular.ttf" "$dir/fonts/Anton.ttf"
get "$gf/montserrat/Montserrat%5Bwght%5D.ttf" "$dir/fonts/Montserrat.ttf"
get "$gf/fredoka/Fredoka%5Bwdth,wght%5D.ttf" "$dir/fonts/Fredoka.ttf"
tracks=("$@")
[ ${#tracks[@]} -gt 0 ] || tracks=("Lightless Dawn" "Dark Fog" "Long Note Two" "Phantasm" "Long Note Four" "Ossuary 5 - Rest")
for t in "${tracks[@]}"; do
  f="$dir/music/${t// /_}.mp3"
  get "https://incompetech.com/music/royalty-free/mp3-royaltyfree/$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$t").mp3" "$f"
done
python3 "$here/../video/fetch_assets.py" "$here/gfx_assets.json" "$dir/assets"
ls "$dir"/fonts "$dir"/music "$dir"/assets
