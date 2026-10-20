#!/usr/bin/env bash
# Fetch a reference YouTube video for style analysis via Apify (YouTube blocks direct
# downloads from cloud IPs). Pulls: metadata + subtitles, the channel's recent uploads (optional), the MP4
# and the thumbnail.
#
# Usage: fetch_video.sh <videoId> <outdir> [quality]      (APIFY_TOKEN from the environment or config/.env)
#   quality: 360 | 480 | 720 | auto (default: the best quality the budget pays for)
# Env: BUDGET_USD   spend limit for the download run (default: what is left of the Apify plan's monthly credit,
#                   and at most 0.20 on the free plan, whose actor runs are capped there)
#      SUBS_LANG    subtitle language for the metadata scraper: any, en, de, es, fr, it, ja, ko, nl, pt, ru (default en;
#                   "any" for a Hindi video)
#      CHANNEL_VIDEOS=N  also list the channel's N latest videos (titles, views, dates) -> channel_videos.json
#
# Cost (epctex/youtube-video-downloader, per second of video): 360p $0.00015, 480p $0.00025,
# 720p $0.00045. On the free plan: 720p up to ~7 min, 480p up to ~13 min, 360p up to ~22 min.
set -euo pipefail
ID="$1"; OUT="$2"; Q="${3:-auto}"
ENVF="$(cd "$(dirname "$0")/../.." && pwd)/config/.env"  # gitignored; env vars win
if [ -z "${APIFY_TOKEN:-}" ] && [ -f "$ENVF" ]; then
  APIFY_TOKEN=$(sed -n 's/^APIFY_TOKEN=//p' "$ENVF" | tail -1)
fi
: "${APIFY_TOKEN:?set APIFY_TOKEN (environment or config/.env)}"
API=https://api.apify.com/v2
AUTH=(-H "Authorization: Bearer $APIFY_TOKEN")
mkdir -p "$OUT"

start_run() { # actor input-json max-usd -> run id (retries: the API sometimes answers with an empty body)
  local r i
  for i in 1 2 3 4; do
    r=$(curl -sS -X POST "${AUTH[@]}" -H "Content-Type: application/json" "$API/acts/$1/runs?maxTotalChargeUsd=${3:-0.5}" -d "$2" || true)
    if python3 -c "import sys,json;print(json.loads(sys.argv[1])['data']['id'])" "$r" 2>/dev/null; then return 0; fi
    echo "start $1 failed (try $i): $(echo "$r" | head -c 300)" >&2
    sleep $((2 ** i))
  done
  return 1
}
wait_run() { # runId -> datasetId
  local st
  while :; do
    st=$(curl -sS "${AUTH[@]}" "$API/actor-runs/$1" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['status'])")
    case $st in READY|RUNNING) sleep 10;; SUCCEEDED) break;; *) echo "run $1 ended: $st" >&2; return 1;; esac
  done
  curl -sS "${AUTH[@]}" "$API/actor-runs/$1" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['defaultDatasetId'])"
}

# 1) metadata + subtitles (needed first: the duration decides the download quality)
if [ ! -s "$OUT/meta.json" ]; then
  RUN=$(start_run streamers~youtube-scraper "{\"startUrls\":[{\"url\":\"https://www.youtube.com/watch?v=$ID\"}],\"maxResults\":1,\"transcriptionAndSubtitle\":\"ALWAYS_SUBTITLES\",\"subtitlesLanguage\":\"${SUBS_LANG:-en}\",\"subtitlesFormat\":\"srt\"}" 0.2)
  DS=$(wait_run "$RUN")
  curl -sS "${AUTH[@]}" "$API/datasets/$DS/items?clean=true" > "$OUT/meta.json"
fi
DUR=$(python3 - "$OUT" <<'EOF'
import json, sys
out = sys.argv[1]
v = json.load(open(f"{out}/meta.json"))[0]
open(f"{out}/description.txt", "w").write(v.get("text") or "")
subs = v.get("subtitles") or []
for s in subs:
    if s.get("srt"):
        open(f"{out}/subs.{s.get('language') or 'xx'}.srt", "w").write(s["srt"])
print(v.get("title"), "|", v.get("channelName"), "|", v.get("numberOfSubscribers"), "subs |", v.get("date"), "|", v.get("viewCount"),
      "views |", v.get("likes"), "likes |", v.get("duration"), "| subs:", [s.get("type") for s in subs], file=sys.stderr)
d = str(v.get("duration") or "0")
secs = 0
for p in d.split(":"):
    secs = secs * 60 + int(float(p))
print(secs)
EOF
)

# 2) the channel's latest uploads (titles, views, dates), optional
if [ -n "${CHANNEL_VIDEOS:-}" ] && [ ! -s "$OUT/channel_videos.json" ]; then
  CH=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[0].get('channelUrl',''))" "$OUT/meta.json")
  if [ -n "$CH" ]; then
    RUN=$(start_run streamers~youtube-scraper "{\"startUrls\":[{\"url\":\"$CH/videos\"}],\"maxResults\":$CHANNEL_VIDEOS}" 0.2)
    DS=$(wait_run "$RUN") && curl -sS "${AUTH[@]}" "$API/datasets/$DS/items?clean=true&fields=title,url,viewCount,date,duration,likes" > "$OUT/channel_videos.json" || true
  fi
fi

# 3) quality: the best one the budget pays for
if [ -z "${BUDGET_USD:-}" ]; then
  BUDGET_USD=$(curl -sS "${AUTH[@]}" "$API/users/me/limits" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)['data']
    left = d['limits']['maxMonthlyUsageUsd'] - d['current']['monthlyUsageUsd']
    free = d['limits']['maxMonthlyUsageUsd'] <= 5
    print(round(max(0.0, min(left, 0.20) if free else left), 3))
except Exception:
    print(0.20)")
fi
if [ "$Q" = auto ]; then
  Q=$(python3 -c "
d, b = int('$DUR'), float('$BUDGET_USD')
for q, c in ((720, 0.00045), (480, 0.00025), (360, 0.00015)):
    if d * c <= b * 0.97:
        print(q); break
else:
    print(0)")
  [ "$Q" != 0 ] || { echo "budget \$$BUDGET_USD is too small for a ${DUR}s video even at 360p" >&2; exit 1; }
fi
echo "duration ${DUR}s, budget \$$BUDGET_USD -> ${Q}p" >&2

# 4) the video
if [ ! -s "$OUT/video.mp4" ]; then
  RUN=$(start_run epctex~youtube-video-downloader "{\"videoIds\":[\"$ID\"],\"quality\":\"$Q\",\"storageType\":\"apify\"}" "$BUDGET_USD")
  DS=$(wait_run "$RUN")
  URL=$(curl -sS "${AUTH[@]}" "$API/datasets/$DS/items?clean=true" | python3 -c "
import sys,json
r=json.load(sys.stdin)
if not r or r[0].get('status')!='succeeded': sys.exit('download failed (free plan caps runs at \$0.20 - try a lower quality): '+json.dumps(r)[:300])
print(r[0]['output']['url'])")
  curl -sS -o "$OUT/video.mp4" "$URL"
fi
curl -sS -o "$OUT/thumb.jpg" "https://i.ytimg.com/vi/$ID/maxresdefault.jpg"
echo "saved: $OUT/video.mp4 (${Q}p)"
