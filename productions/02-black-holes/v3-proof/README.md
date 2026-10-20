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

## Measured
See the table in the commit message and the session report. It is filled in below after the render.
