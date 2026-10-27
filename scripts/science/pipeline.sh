#!/usr/bin/env bash
# Science channel (Hindi documentary) pipeline: runs the scripted stages for one production.
#
#   scripts/science/pipeline.sh <production_dir> <stage> [stage ...]
#
# Stages, in order (see .claude/skills/science-video/SKILL.md for the whole workflow):
#   setup      fonts, music, graphic stills -> $MEDIA            (once per machine)
#   probe      read the names/terms never heard yet alone (a few characters) -> $WORK/voice_probe/probe.mp3
#   narration  ElevenLabs render of tts/narration.hi.md -> $WORK/voice (narration.wav, timeline.json)
#              (tts_check.py first: refuses to record while a line is flagged; speech_check.py after)
#   edit       edit.spec + edit.base.json -> edit.json, then check every trigger against the narration
#   footage    4K search -> CLIP pick -> 1080p proxies -> shots + QC (text, black, frozen, people)
#              (shared library $LIB, grows over time)
#   topup      more 4K candidates for items that matched weakly (score < 0.37) -> fetch -> shots
#   assign     one unique shot per footage item -> $WORK/cutlist.json + review sheets $WORK/review_assign
#              (only clips on disk are used: --local-only)
#              (re-runs keep reviewed shots: previous cutlist is kept as $WORK/cutlist_prev.json)
#   render     master video -> $WORK/out/<name>.mp4 (+ English caption track <name>.en.srt for v3 -> captions.en.srt)
#   review     contact sheets of the master -> $WORK/review_render
#   preview    720p parts under 30 MB -> $WORK/out/preview
#   credits    description credits from the final cut -> <production_dir>/credits.txt
#   all        everything from narration to credits
#   archive    after the video is published: catalogue the footage library (descriptive clip names,
#              productions/footage-catalog.csv), copy the master + thumbnail to Drive videos/ under the real
#              title, then push $WORK -> productions/<name>, $LIB -> footage-library, $MEDIA -> media on
#              Google Drive (folder axiom-science-channel) and delete them here. Nothing heavy stays local.
#   restore    pull media, the whole footage library and this production's work dir back from Drive
#   restore-library  pull media and the library metadata only (no clips): the footage stage then pulls the
#              picked clips that the library already has and downloads the rest (the full library no longer
#              fits the container next to new footage)
#   restore-render  pull only what a re-render needs: media, library metadata, the clips in cutlist.json
#              and the work dir (voice, renders)
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
DRIVE=$ROOT/scripts/storage/drive_sync.py
MASTER=$WORK/out/$NAME.mp4

# picks that are already in the shared library (sources.json) but not on disk come back from Drive, not from
# the archive again (the library can be restored partly: restore-library pulls only what an edit can use)
library_pull() {
  "$PY" -c "import json,os,re,sys; s=json.load(open(sys.argv[2]+'/sources.json')) if os.path.exists(sys.argv[2]+'/sources.json') else {}
n=lambda k: re.sub(r'[^A-Za-z0-9_-]','_',k.replace(':','_'))
print('\n'.join(sorted(n(p['key'])+'.mp4' for p in json.load(open(sys.argv[1])) if n(p['key']) in s and not os.path.exists(sys.argv[2]+'/clips/'+n(p['key'])+'.mp4'))))" \
    "$1" "$LIB" > "$WORK/library_pull.txt"
  if [ -s "$WORK/library_pull.txt" ]; then
    echo "pulling $(wc -l < "$WORK/library_pull.txt") picked clips from the Drive library"
    "$PY" "$DRIVE" pull footage-library/clips "$LIB/clips" --only-list "$WORK/library_pull.txt"
  fi
}

stage() {
  echo "=== $1 ($NAME)"
  case $1 in
    setup)
      bash "$ROOT/scripts/setup/fetch_media.sh" "$MEDIA" ;;
    narration)
      # no pauses (owner, 2026-10-27): 0.8 s before a chapter card, pauses inside a chapter cut to 0.4 s; the
      # open gap holds the channel intro + title card after the opening (productions 01-04 used --open-gap 3.5 --gap 2.0)
      # right the first time (owner, 2026-10-27): the text is checked before a character is paid for, and every new
      # recording is listened to (speech_check) before anything is built on it
      "$PY" "$ROOT/scripts/elevenlabs/tts_check.py" "$P/tts/narration.hi.md" ${TTS_CHECK_FLAGS:-} \
        || { echo "fix the flagged lines (new names: pipeline.sh $P probe) before recording"; exit 1; }
      # shellcheck disable=SC2086
      "$PY" "$ROOT/scripts/elevenlabs/render_narration.py" "$P/tts/narration.hi.md" "$WORK/voice" \
        ${NARRATION_FLAGS:---open-gap 6.4 --gap 0.8 --max-pause 0.4}
      "$PY" "$ROOT/scripts/elevenlabs/speech_check.py" "$P/tts/narration.hi.md" "$WORK/voice" ;;
    probe)  # new names and English terms read alone first: a few characters instead of a re-recorded section
      "$PY" "$ROOT/scripts/elevenlabs/probe_words.py" "$P/tts/narration.hi.md" ${PROBE_FLAGS:-} ;;
    edit)
      "$PY" "$ROOT/scripts/video/make_edit.py" "$P/edit.spec" "$P/edit.base.json" "$P/edit.json"
      "$PY" "$ROOT/scripts/footage/assign_shots.py" "$P/edit.json" "$TL" "$LIB" "$WORK/cutlist.json" --plan-only ;;
    footage)
      "$PY" "$ROOT/scripts/footage/search_sources.py" "$P/footage/terms.txt" "$LIB/candidates.json"
      "$PY" "$ROOT/scripts/footage/select_candidates.py" "$LIB/candidates.json" "$P/edit.json" "$TL" "$LIB" "$WORK/picks.json" \
        --max "$LIMIT" --avoid "$ROOT/productions" --lib "$LIB"
      library_pull "$WORK/picks.json"
      "$PY" "$ROOT/scripts/footage/fetch_proxies.py" "$WORK/picks.json" "$LIB" --jobs "$JOBS" \
        --limit "$LIMIT" --cap-single 12 --cap-multi "$CAP_MULTI" --preset "$PRESET" --from-end
      "$PY" "$ROOT/scripts/footage/build_shots.py" "$LIB" --workers "$WORKERS"
      "$PY" "$ROOT/scripts/footage/people_scan.py" "$LIB" ;;
    topup)
      "$PY" "$ROOT/scripts/footage/select_candidates.py" "$LIB/candidates.json" "$P/edit.json" "$TL" "$LIB" "$WORK/picks_topup.json" \
        --weak "$WORK/cutlist.json" --below 0.37 --per-item 3 --max 160 --skip "$WORK/picks.json" --avoid "$ROOT/productions" --lib "$LIB"
      library_pull "$WORK/picks_topup.json"
      "$PY" "$ROOT/scripts/footage/fetch_proxies.py" "$WORK/picks_topup.json" "$LIB" --jobs "$JOBS" \
        --cap-single 12 --cap-multi "$CAP_MULTI" --preset "$PRESET" --from-end
      "$PY" "$ROOT/scripts/footage/build_shots.py" "$LIB" --workers "$WORKERS"
      "$PY" "$ROOT/scripts/footage/people_scan.py" "$LIB" ;;
    assign)
      keep=()
      if [ -f "$WORK/cutlist.json" ] && [ "${FRESH:-0}" != 1 ]; then
        cp "$WORK/cutlist.json" "$WORK/cutlist_prev.json"
        keep=(--keep "$WORK/cutlist_prev.json" --changed "$WORK/cutlist_prev.json")
      fi
      "$PY" "$ROOT/scripts/footage/assign_shots.py" "$P/edit.json" "$TL" "$LIB" "$WORK/cutlist.json" \
        --review "$WORK/review_assign" --avoid "$ROOT/productions" --local-only ${keep[@]+"${keep[@]}"} ;;
    render)  # edit.json "style": "v3" -> render_v3.py (docs/style-guide.md), else the v2 renderer
      mkdir -p "$WORK/out"
      style=$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('style', 'v2'))" "$P/edit.json")
      "$PY" "$ROOT/scripts/video/render_${style}.py" "$WORK/cutlist.json" "$WORK/voice/narration.wav" "$P/edit.json" "$TL" \
        "$MEDIA/music" "$MEDIA/fonts" "$MEDIA/assets" "$MASTER" --workers "$WORKERS"
      cp "$WORK/cutlist.json" "$P/cutlist.json"
      [ -f "${MASTER%.mp4}.en.srt" ] && cp "${MASTER%.mp4}.en.srt" "$P/captions.en.srt" || true ;;
    review)
      "$PY" "$ROOT/scripts/video/review_sheet.py" "$MASTER" "$WORK/review_render" --cutlist "$WORK/cutlist.json" ;;
    shorts)  # 9:16 Shorts from the finished master (productions/NN/shorts.spec); ONLY=<id> renders one
      "$PY" "$ROOT/scripts/video/render_short.py" "$P/shorts.spec" "$WORK/cutlist.json" "${MASTER%.mp4}_work" \
        "$LIB/sources.json" "$LIB/clips" "$MEDIA/music" "$MEDIA/fonts" "$MEDIA/assets" "$WORK/out/shorts" \
        ${ONLY:+--only "$ONLY"} --workers "$WORKERS" ;;
    preview)
      bash "$ROOT/scripts/video/preview_parts.sh" "$MASTER" "$WORK/out/preview" ;;
    credits)
      "$PY" "$ROOT/scripts/footage/credits.py" "$WORK/cutlist.json" "$LIB" "$P/edit.json" --assets "$MEDIA/assets/credits.json" \
        --full "$P/credits_full.txt" | tee "$P/credits.txt" ;;
    all)
      for s in narration edit footage assign render review preview credits; do stage "$s"; done ;;
    archive)
      "$PY" "$ROOT/scripts/footage/catalog.py" "$LIB" --csv "$ROOT/productions/footage-catalog.csv"
      if [ -f "$MASTER" ]; then  # the finished video under its real title, easy to find on Drive
        title=$("$PY" -c "import re,sys; m=re.search(r'\*\*Title\*\*\s*\n(.+)', open(sys.argv[1]).read()); print(m.group(1).strip().replace(' | ', ' (').replace('/', '-') + ')' if m else '')" "$P/youtube.md" 2>/dev/null || true)
        n=${NAME%%-*}
        "$PY" "$DRIVE" put "$MASTER" videos --as "$n - ${title:-$NAME} 1080p.mp4"
        for th in "$WORK/thumbnail.jpg" "$WORK/thumb/thumbnail.jpg"; do
          if [ -f "$th" ]; then "$PY" "$DRIVE" put "$th" videos --as "$n - ${title:-$NAME} thumbnail.jpg"; break; fi
        done
      fi
      "$PY" "$DRIVE" push "$WORK" "productions/$NAME" --delete
      "$PY" "$DRIVE" put "$ROOT/productions/footage-catalog.csv" footage-library --as catalog.csv
      "$PY" "$DRIVE" push "$LIB" footage-library --pack thumbs,shot_thumbs --names "$LIB/drive_names.json" --delete
      "$PY" "$DRIVE" push "$MEDIA" media --delete ;;
    restore)
      "$PY" "$DRIVE" pull media "$MEDIA"
      "$PY" "$DRIVE" pull footage-library "$LIB"
      "$PY" "$DRIVE" pull "productions/$NAME" "$WORK" || echo "(no work dir on Drive yet for $NAME)" ;;
    restore-library)
      "$PY" "$DRIVE" pull media "$MEDIA"
      "$PY" "$DRIVE" pull footage-library "$LIB" --exclude clips
      "$PY" "$DRIVE" pull "productions/$NAME" "$WORK" || echo "(no work dir on Drive yet for $NAME)" ;;
    restore-render)
      "$PY" "$DRIVE" pull media "$MEDIA"
      "$PY" "$DRIVE" pull footage-library "$LIB" --exclude clips
      "$PY" -c "import json,sys; print('\\n'.join(sorted({i['clip'] + '.mp4' for i in json.load(open(sys.argv[1]))['items'] if i.get('clip')})))" \
        "$P/cutlist.json" > "$WORK/clips_needed.txt"
      "$PY" "$DRIVE" pull footage-library/clips "$LIB/clips" --only-list "$WORK/clips_needed.txt"
      "$PY" "$DRIVE" pull "productions/$NAME" "$WORK" ;;
    *)
      echo "unknown stage: $1"; exit 2 ;;
  esac
}

for s in "$@"; do stage "$s"; done
