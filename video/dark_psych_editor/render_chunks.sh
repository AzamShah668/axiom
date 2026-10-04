#!/bin/bash
# Render the Milgram edit in 4 resumable chunks (a finished chunk is skipped on rerun).
P=$(cd "$(dirname "$0")" && pwd)
R=$P/remotion
# optional: BROWSER_EXECUTABLE=/path/to/chrome-headless-shell
BX_FLAG=${BROWSER_EXECUTABLE:+--browser-executable=$BROWSER_EXECUTABLE}
TOTAL=$(python3 -c "import json; print(json.load(open('$R/src/edit.json'))['durationInFrames'])")
N=4
SIZE=$(( (TOTAL + N - 1) / N ))
cd "$R" || exit 1
for i in $(seq 0 $((N - 1))); do
	a=$(( i * SIZE )); b=$(( (i + 1) * SIZE - 1 )); [ $b -ge $TOTAL ] && b=$((TOTAL - 1))
	out=out/part_$i.mp4
	want=$(( b - a + 1 ))
	have=$(ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 "$out" 2>/dev/null)
	if [ "$have" = "$want" ]; then echo "part $i ok ($have frames), skipping"; continue; fi
	echo "$(date +%T) part $i: frames $a-$b"
	./node_modules/.bin/remotion render build Milgram "$out" --frames=$a-$b --concurrency=4 --codec=h264 --crf=16 --muted \
		--timeout=120000 --offthreadvideo-cache-size-in-bytes=1500000000 $BX_FLAG --log=error 2>&1 \
		| tr '\r' '\n' | grep -vE '^(Rendered|Encoded|Stitched|Getting)' | grep -v '^\s*$' | tail -20
	have=$(ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 "$out" 2>/dev/null)
	echo "$(date +%T) part $i done: $have/$want frames"
	[ "$have" = "$want" ] || { echo "PART $i FAILED"; exit 1; }
done
echo ALL_PARTS_OK
