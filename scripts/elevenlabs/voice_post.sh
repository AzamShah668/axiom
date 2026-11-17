#!/usr/bin/env bash
# Documentary voice finish for ElevenLabs renders.
# Usage: voice_post.sh <in> <out.wav> [semitones_down=0] [formant=preserved|shifted] [chain=legacy|phone]
#   0    -> clean documentary finish only (warmth, de-ess, compression, -16 LUFS)
#   1.5  -> slightly deeper (formants preserved)
#   2.5  -> deeper "bigger chest" sound (use formant=shifted)
# chain: legacy (default, as before; tuned for Neel) | phone (on trial, research 05 P1-d: less bass for phone
#   speakers - 4th-order 70 Hz high-pass, -3 dB at 280 Hz, gentle compression, presence and air, de-ess last)
set -euo pipefail
IN="$1"; OUT="$2"; ST="${3:-0}"; FORMANT="${4:-preserved}"; CHAIN="${5:-legacy}"
PITCH=$(python3 -c "print(round(2**(-float('$ST')/12), 4))")
SHIFT=""
[ "$ST" != "0" ] && SHIFT="rubberband=pitch=${PITCH}:formant=${FORMANT}:pitchq=quality,"
case "$CHAIN" in
  legacy) AF="highpass=f=60,${SHIFT}\
equalizer=f=160:t=q:w=1:g=2.5,equalizer=f=380:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.5:g=1.5,\
deesser=i=0.4,acompressor=threshold=-22dB:ratio=3:attack=8:release=180:makeup=4,\
loudnorm=I=-16:TP=-1.5:LRA=7" ;;
  phone) AF="highpass=f=70:poles=2,highpass=f=70:poles=2,${SHIFT}equalizer=f=280:t=q:w=1.0:g=-3,\
acompressor=threshold=-24dB:ratio=2.5:attack=10:release=250:knee=6:makeup=3,\
equalizer=f=3000:t=q:w=0.8:g=2.5,equalizer=f=10000:t=h:w=0.7:g=2,deesser=i=0.35,\
loudnorm=I=-16:TP=-1.5:LRA=7" ;;
  *) echo "chain must be legacy or phone, not $CHAIN" >&2; exit 2 ;;
esac
ffmpeg -v error -y -i "$IN" -af "$AF" -ar 44100 -ac 1 "$OUT"
echo "wrote $OUT (pitch x$PITCH, $CHAIN chain)"
