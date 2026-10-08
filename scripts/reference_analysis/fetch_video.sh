#!/usr/bin/env bash
# Fetch a reference YouTube video for style analysis via Apify (YouTube blocks direct
# downloads from cloud IPs). Pulls: metadata + creator subtitles, and the MP4.
#
# Usage: APIFY_TOKEN=... fetch_video.sh <videoId> <outdir> [quality]
#   quality: 360 | 480 (default) | 720
#
# Cost (epctex/youtube-video-downloader, per second of video): 360p $0.00015, 480p $0.00025,
# 720p $0.00045. Free-plan runs are capped at $0.20 by the actor itself, so on the free plan
# use 480p for videos up to ~13 min and 360p up to ~22 min.
set -euo pipefail
ID="$1"; OUT="$2"; Q="${3:-480}"
: "${APIFY_TOKEN:?set APIFY_TOKEN}"
API=https://api.apify.com/v2
AUTH=(-H "Authorization: Bearer $APIFY_TOKEN")
mkdir -p "$OUT"

start_run() { # actor input-json -> run json
  curl -sS -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
    "$API/acts/$1/runs?maxTotalChargeUsd=${3:-0.5}" -d "$2"
}
wait_run() { # runId -> datasetId
  local st
  while :; do
    st=$(curl -sS "${AUTH[@]}" "$API/actor-runs/$1" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['status'])")
    case $st in READY|RUNNING) sleep 10;; SUCCEEDED) break;; *) echo "run $1 ended: $st" >&2; return 1;; esac
  done
  curl -sS "${AUTH[@]}" "$API/actor-runs/$1" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['defaultDatasetId'])"
}

META=$(start_run streamers~youtube-scraper "{\"startUrls\":[{\"url\":\"https://www.youtube.com/watch?v=$ID\"}],\"maxResults\":1,\"transcriptionAndSubtitle\":\"ALWAYS_SUBTITLES\",\"subtitlesLanguage\":\"en\",\"subtitlesFormat\":\"srt\"}" 0.2 \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")
DL=$(start_run epctex~youtube-video-downloader "{\"videoIds\":[\"$ID\"],\"quality\":\"$Q\",\"storageType\":\"apify\"}" 0.3 \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")

DS=$(wait_run "$META")
curl -sS "${AUTH[@]}" "$API/datasets/$DS/items?clean=true" > "$OUT/meta.json"
python3 - "$OUT" <<'EOF'
import json, sys
out = sys.argv[1]
v = json.load(open(f"{out}/meta.json"))[0]
open(f"{out}/description.txt", "w").write(v.get("text") or "")
subs = v.get("subtitles") or []
if subs:
    open(f"{out}/subs.srt", "w").write(subs[0].get("srt") or "")
print(v["title"], "|", v.get("date"), "|", v.get("viewCount"), "views |", v.get("duration"), "| subs:", [s.get("type") for s in subs])
EOF

DS=$(wait_run "$DL")
URL=$(curl -sS "${AUTH[@]}" "$API/datasets/$DS/items?clean=true" | python3 -c "
import sys,json
r=json.load(sys.stdin)
if not r or r[0].get('status')!='succeeded': sys.exit('download failed (free plan caps runs at \$0.20 - try a lower quality): '+json.dumps(r)[:300])
print(r[0]['output']['url'])")
curl -sS -o "$OUT/video.mp4" "$URL"
curl -sS -o "$OUT/thumb.jpg" "https://i.ytimg.com/vi/$ID/maxresdefault.jpg"
echo "saved: $OUT/video.mp4"
