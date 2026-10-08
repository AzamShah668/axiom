#!/usr/bin/env bash
# Documentary voice finish for ElevenLabs renders.
# Usage: voice_post.sh <in> <out.wav> [semitones_down=0] [formant=preserved|shifted]
#   0    -> clean documentary finish only (warmth, de-ess, compression, -16 LUFS)
#   1.5  -> slightly deeper (formants preserved)
#   2.5  -> deeper "bigger chest" sound (use formant=shifted)
set -euo pipefail
IN="$1"; OUT="$2"; ST="${3:-0}"; FORMANT="${4:-preserved}"
PITCH=$(python3 -c "print(round(2**(-float('$ST')/12), 4))")
SHIFT=""
[ "$ST" != "0" ] && SHIFT="rubberband=pitch=${PITCH}:formant=${FORMANT}:pitchq=quality,"
ffmpeg -v error -y -i "$IN" -af "highpass=f=60,${SHIFT}\
equalizer=f=160:t=q:w=1:g=2.5,equalizer=f=380:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.5:g=1.5,\
deesser=i=0.4,acompressor=threshold=-22dB:ratio=3:attack=8:release=180:makeup=4,\
loudnorm=I=-16:TP=-1.5:LRA=7" -ar 44100 -ac 1 "$OUT"
echo "wrote $OUT (pitch x$PITCH)"
