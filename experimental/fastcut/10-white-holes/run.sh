#!/usr/bin/env bash
# Fast-cut 10 (separate project): plan -> pins -> shots -> render -> post pass. Main-pipeline tools are only called.
#   bash experimental/fastcut/10-white-holes/run.sh [plan|assign|render|post|all]
set -euo pipefail
cd "$(dirname "$0")/../../.."
P=experimental/fastcut/10-white-holes; F=work/fastcut/10-white-holes; TL=work/10-white-holes/voice/timeline.json
M=work/media; OUT=$F/out/10-white-holes-fast.mp4; FINAL=$F/out/10-white-holes-fast-final.mp4
step=${1:-all}; mkdir -p $F/out
plan()   { python3 scripts/video/make_edit.py $P/edit.spec $P/edit.base.json $F/edit.json
           python3 experimental/fastcut/pins.py $F/edit.json $TL $P/edit.base.json
           python3 scripts/video/make_edit.py $P/edit.spec $P/edit.base.json $F/edit.json; }
assign() { python3 scripts/footage/assign_shots.py $F/edit.json $TL work/library $F/cutlist.json --review $F/review_assign --local-only; }
render() { python3 scripts/video/render_v3.py $F/cutlist.json work/10-white-holes/voice/narration.wav $F/edit.json $TL \
             $M/music $M/fonts $M/assets $OUT --workers 4; }
post()   { python3 experimental/fastcut/post.py $OUT $TL $P/post.json $FINAL; }
case $step in plan) plan;; assign) assign;; render) render;; post) post;; all) plan; assign; render; post;; esac
