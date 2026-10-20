# v3 style proof (production 02 re-cut)

The cold open and fact #10 of "10 Facts You Don't Know About Black Holes", re-cut in the v3 style
(`docs/style-guide.md`). It gets a new 28 s hook, so the topic is named in the first second.
- cold open and fact 10: the published narration is reused
- hook: new, rendered with the locked Neel preset

## Inputs
| File | What it is |
|---|---|
| `tts/narration.hi.md` | `hook` (new) + `cold_open` + `fact10` (unchanged text) |
| `edit.spec` | the v3 plan: beats, headlines `K`, number cards `N`, callout, lower thirds `L`, moments `M`, CC lines `C` |
| `edit.base.json` | style v3, grade `amber_teal`, music (Interloper → Long Note Three → Dark Fog), pins for the Webb and Sgr A* shots |
| `cutlist.json` | the full v3 plan with the assigned shots |
| `captions.en.srt` | the English CC track |

## Build
```bash
PY=work/venv/bin/python; D=productions/02-black-holes/v3-proof; W=work/02v3
bash scripts/science/pipeline.sh productions/02-black-holes restore-render     # media + production 02's clips
mkdir -p $W/voice && cp work/02-black-holes/voice/{cold_open,fact10}.{mp3,align.json} $W/voice/
$PY scripts/elevenlabs/render_narration.py $D/tts/narration.hi.md $W/voice --open-gap 3.5 --gap 2.0 --gap-after hook=1.2
$PY scripts/video/make_edit.py $D/edit.spec $D/edit.base.json $D/edit.json
$PY scripts/footage/assign_shots.py $D/edit.json $W/voice/timeline.json work/library $W/cutlist.json --local-only --review $W/review_assign
$PY scripts/video/render_v3.py $W/cutlist.json $W/voice/narration.wav $D/edit.json $W/voice/timeline.json \
    work/media/music work/media/fonts work/media/assets $W/out/02v3-proof.mp4
```
- `--local-only` uses only clips that `restore-render` pulled, i.e. production 02's own footage.
- `--avoid` is left out on purpose: this is a re-cut of the same video.
- Renders and voice are on Drive under `productions/02-black-holes/v3-proof/`.

## Measured (same section: before = published v2 cut 0:00-2:12.6, after = this re-cut 0:00-2:46.6)
| | Before (v2) | After (v3) | Curious Space reference |
|---|---|---|---|
| Topic named | 0:58.8 | **0:00.5** (headline at 0:00.2) | 0:00.1 |
| First number on screen | 0:42 | **0:10** (count-up landing on "चालीस लाख") | 0:38 |
| Title card | 1:13 | 1:43 (after the new 28 s hook) | 1:08 |
| Cuts per minute | 20.9 (whole video) | 15.8 | 18.1 |
| Cuts inside a pause | 24% | **84%** | 54% |
| Scene length p10-p90 | 1.8-4.2 s | 2.0-5.6 s | 1.4-5.3 s |
| Transitions | rotation of zoom / flash / whip / blur | 28 cuts, 13 dips, 2 flares, 2 soft (by rule) | 96 cuts, 30 dips, 27 dissolves, 21 flares |
| On-screen text | subtitle on 96% of the runtime | key text / cards on 35% (5 headlines, 6 key lines, 2 lower thirds, 5 cards); every sentence in the CC track | big text on 29% |
| Number cards | none animated | 4 (1.4/min; story-heavy section) | 4.4/min |
| Music under the voice (speaking / pauses) | 25.7 / 18.5 LU | **16.1 / 14.3 LU** | 15.0 / 13.2 LU |
| SFX | identical whoosh per beat | 66 (24/min), 9 kinds, synthesised | 23/min |
| Designed moments | 1 boom | 3 (flare + impact, flare + impact, silence + dip + hit) | 5 in 11 min |
| Saturation (median HSV S) | 44 | **121** | 193 |
| Loudness | -14.0 LUFS | -14.0 LUFS, TP -1.1 dBFS (linear, no pumping) | -19.9 LUFS |

Measured from `cutlist.json`, the render stems (BS.1770, mono voice counted as dual-mono) and the masters
(ffmpeg ebur128, frames at 2 fps). The levels are measured, not listened to: a listen on headphones is the
check still to do.
