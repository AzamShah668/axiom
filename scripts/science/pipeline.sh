#!/usr/bin/env bash
# Science channel (Hindi documentary) pipeline: runs the scripted stages for one production.
#
#   scripts/science/pipeline.sh <production_dir> <stage> [stage ...]
#
# Stages, in order (see .claude/skills/science-video/SKILL.md for the whole workflow):
#   setup      fonts, music, graphic stills -> $MEDIA            (once per machine)
#   narration  ElevenLabs render of tts/narration.hi.md -> $WORK/voice (narration.wav, timeline.json)
#   edit       edit.spec + edit.base.json -> edit.json, then check every trigger against the narration
#   footage    4K search -> CLIP pick -> 1080p proxies -> shots + QC   (shared library $LIB, grows over time)
#   topup      more 4K candidates for items that matched weakly (score < 0.37) -> fetch -> shots
#   assign     one unique shot per footage item -> $WORK/cutlist.json + review sheets $WORK/review_assign
#              (re-runs keep reviewed shots: previous cutlist is kept as $WORK/cutlist_prev.json)
#   render     master video -> $WORK/out/<name>.mp4
#   review     contact sheets of the master -> $WORK/review_render
#   preview    720p parts under 30 MB -> $WORK/out/preview
#   credits    description credits from the final cut -> <production_dir>/credits.txt
#   all        everything from narration to credits
#
# Environment: PY (python with scripts/requirements-science.txt), WORK (default work/<production>),
#              LIB (default work/library), MEDIA (default work/media), JOBS (default 3), WORKERS (default 4),
#              FRESH=1 (assign from scratch instead of keeping the previously reviewed shots),
#              PRESET (x264 preset for proxies, default veryfast: ~1/3 smaller than ultrafast at the same CRF),
#              CAP_MULTI (seconds kept from multi-shot videos, default 40), LIMIT (max new videos, default 330)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
P=$(cd "$1" && pwd); shift
NAME=$(basename "$P")
PY=${PY:-python3}
WORK=${WORK:-$ROOT/work/$NAME}
LIB=${LIB:-$ROOT/work/library}
MEDIA=${MEDIA:-$ROOT/work/media}
JOBS=${JOBS:-3}
WORKERS=${WORKERS:-4}
PRESET=${PRESET:-veryfast}
CAP_MULTI=${CAP_MULTI:-40}
LIMIT=${LIMIT:-330}
mkdir -p "$WORK" "$LIB" "$MEDIA"
TL=$WORK/voice/timeline.json
MASTER=$WORK/out/$NAME.mp4

stage() {
  echo "=== $1 ($NAME)"
  case $1 in
    setup)
      bash "$ROOT/scripts/setup/fetch_media.sh" "$MEDIA" ;;
    narration)
      "$PY" "$ROOT/scripts/elevenlabs/render_narration.py" "$P/tts/narration.hi.md" "$WORK/voice" --open-gap 3.5 --gap 2.0 ;;
    edit)
      "$PY" "$ROOT/scripts/video/make_edit.py" "$P/edit.spec" "$P/edit.base.json" "$P/edit.json"
      "$PY" "$ROOT/scripts/footage/assign_shots.py" "$P/edit.json" "$TL" "$LIB" "$WORK/cutlist.json" --plan-only ;;
    footage)
      "$PY" "$ROOT/scripts/footage/search_sources.py" "$P/footage/terms.txt" "$LIB/candidates.json"
      "$PY" "$ROOT/scripts/footage/select_candidates.py" "$LIB/candidates.json" "$P/edit.json" "$TL" "$LIB" "$WORK/picks.json" \
        --max "$LIMIT"
      "$PY" "$ROOT/scripts/footage/fetch_proxies.py" "$WORK/picks.json" "$LIB" --jobs "$JOBS" \
        --limit "$LIMIT" --cap-single 12 --cap-multi "$CAP_MULTI" --preset "$PRESET" --from-end
      "$PY" "$ROOT/scripts/footage/build_shots.py" "$LIB" --workers "$WORKERS" ;;
    topup)
      "$PY" "$ROOT/scripts/footage/select_candidates.py" "$LIB/candidates.json" "$P/edit.json" "$TL" "$LIB" "$WORK/picks_topup.json" \
        --weak "$WORK/cutlist.json" --below 0.37 --per-item 3 --max 160 --skip "$WORK/picks.json"
      "$PY" "$ROOT/scripts/footage/fetch_proxies.py" "$WORK/picks_topup.json" "$LIB" --jobs "$JOBS" \
        --cap-single 12 --cap-multi "$CAP_MULTI" --preset "$PRESET" --from-end
      "$PY" "$ROOT/scripts/footage/build_shots.py" "$LIB" --workers "$WORKERS" ;;
    assign)
      keep=()
      if [ -f "$WORK/cutlist.json" ] && [ "${FRESH:-0}" != 1 ]; then
        cp "$WORK/cutlist.json" "$WORK/cutlist_prev.json"
        keep=(--keep "$WORK/cutlist_prev.json" --changed "$WORK/cutlist_prev.json")
      fi
      "$PY" "$ROOT/scripts/footage/assign_shots.py" "$P/edit.json" "$TL" "$LIB" "$WORK/cutlist.json" \
        --review "$WORK/review_assign" --avoid "$ROOT/productions" ${keep[@]+"${keep[@]}"} ;;
    render)
      mkdir -p "$WORK/out"
      "$PY" "$ROOT/scripts/video/render_v2.py" "$WORK/cutlist.json" "$WORK/voice/narration.wav" "$P/edit.json" "$TL" \
        "$MEDIA/music" "$MEDIA/fonts" "$MEDIA/assets" "$MASTER" --workers "$WORKERS"
      cp "$WORK/cutlist.json" "$P/cutlist.json" ;;
    review)
      "$PY" "$ROOT/scripts/video/review_sheet.py" "$MASTER" "$WORK/review_render" ;;
    preview)
      bash "$ROOT/scripts/video/preview_parts.sh" "$MASTER" "$WORK/out/preview" 3 ;;
    credits)
      "$PY" "$ROOT/scripts/footage/credits.py" "$WORK/cutlist.json" "$LIB" "$P/edit.json" --assets "$MEDIA/assets/credits.json" \
        --full "$P/credits_full.txt" | tee "$P/credits.txt" ;;
    all)
      for s in narration edit footage assign render review preview credits; do stage "$s"; done ;;
    *)
      echo "unknown stage: $1"; exit 2 ;;
  esac
}

for s in "$@"; do stage "$s"; done
