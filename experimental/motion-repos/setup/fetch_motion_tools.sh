#!/bin/sh
# Fetch the motion-graphics engines used as extra editing styles, OUTSIDE the repo.
# lemo-opuscar: code is MIT, its style docs are CC BY-NC, so it never goes into this public repo.
# Films we render with it are ours. Needs Node 20+ and ffmpeg 7+ (a static build is fetched).
#   sh scripts/setup/fetch_motion_tools.sh            -> $TOOLS (default /home/user/tools)
set -e
TOOLS=${TOOLS:-/home/user/tools}
mkdir -p "$TOOLS"
[ -d "$TOOLS/lemo-opuscar/.git" ] || git clone --depth 1 https://github.com/lemomo-ai/lemo-opuscar "$TOOLS/lemo-opuscar"
(cd "$TOOLS/lemo-opuscar" && sh plugin/skills/lemo-opuscar/scripts/setup.sh deps)
if ! "$TOOLS/ffmpeg7/ffmpeg" -version >/dev/null 2>&1; then
  mkdir -p "$TOOLS/ffmpeg7" && cd "$TOOLS/ffmpeg7"
  curl -fsSL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar xJ --strip-components=1
fi
pip install -q fonttools brotli   # fill_fonts.py: stand-in fonts when google/github font hosts are blocked
echo "LIB=$TOOLS/lemo-opuscar  PATH=$TOOLS/ffmpeg7:\$PATH"
