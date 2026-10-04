#!/bin/bash
# Join the rendered parts, apply the VHS finish (color fringe, film grain, flicker, vignette, scanlines),
# mux the mastered audio and encode a YouTube-ready MP4.
# Usage: finish.sh <output.mp4>
set -e
P=$(cd "$(dirname "$0")" && pwd)
OUTFILE=${1:-$P/out/final.mp4}
LIST=$P/out/parts.txt
mkdir -p "$P/out"
: > "$LIST"
want=0
for f in "$P"/remotion/out/part_*.mp4; do
	# The concat demuxer mis-times a part whose time base differs from the first part's
	# (a re-encoded part came out at 1/15360 and its frames landed minutes early), so
	# rewrap any part that is not at the 1/90000 Remotion uses.
	tb=$(ffprobe -v error -select_streams v:0 -show_entries stream=time_base -of csv=p=0 "$f" | tr -d ',')
	if [ "$tb" != "1/90000" ]; then
		ffmpeg -v error -y -i "$f" -c copy -video_track_timescale 90000 "$f.tb.mp4" && mv "$f.tb.mp4" "$f"
	fi
	n=$(ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 "$f" | tr -dc '0-9')
	want=$((want + n))
	echo "file '$f'" >> "$LIST"
done
ffmpeg -v error -stats -y -f concat -safe 0 -i "$LIST" -i "$P/out/mix.wav" -i "$P/out/scanlines.png" \
	-filter_complex "[0:v]rgbashift=rh=-2:bh=2,noise=c0s=6:c0f=t+u,eq=brightness='0.010*sin(n*1.9)':eval=frame,vignette=angle=PI/4.6[v];[v][2:v]overlay=format=auto,format=yuv420p[o]" \
	-map "[o]" -map 1:a -c:v libx264 -preset fast -crf 21 -maxrate 12M -bufsize 24M -r 30 \
	-c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUTFILE"
have=$(ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 "$OUTFILE" | tr -dc '0-9')
echo "wrote $OUTFILE: $have frames (parts total $want)"
[ "$have" = "$want" ] || { echo "FRAME COUNT MISMATCH"; exit 1; }
