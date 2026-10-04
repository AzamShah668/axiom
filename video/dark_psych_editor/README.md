# Dark-psychology editor (Remotion + FFmpeg)

Turns a voiceover into a fast-cut, dark "psychology channel" edit, modelled on
*5 DARK PSYCHOLOGY Tricks to Secretly Control Anyone*. First used for the
Milgram voiceover (11:51, 1569 words, 377 scenes).

## The style, measured from the reference

| Element | Reference | Here |
|---|---|---|
| Pace | 201 cuts in 6:44, median shot 1.4 s | 377 scenes in 11:51, cuts snapped to word starts |
| Hook | Red kinetic words over a laser grid, glitches | `Word` with `bg: 'laser'` (slide up, pale-to-red fill, RGB split, glitch frames) |
| Chapters | Grey flash + black beat + boom, then "Trick - #N" card | `flash` + `black` + `ChapterCard` ("Level - #1", "Question - #2"); music dips to silence |
| B-roll | Literal illustration of the current words | Archival film, web images, generated noir stills, programmatic graphics |
| Captions | Centered white serif, 2-4 words, instant switch | `Caption` (Libre Baskerville); hidden over titles, moved low over graphics |
| Finish | VHS: grain, scanlines, vignette, chromatic aberration | `finish.sh` (FFmpeg) |
| Sound | Dark music bed, impacts on titles | 7 Kevin MacLeod tracks, ducked under the voice; 41 Mixkit effects |

## Pipeline

```bash
# 0. one-time: Remotion deps come from ../node_modules (cd video && npm ci)
ln -s ../../node_modules remotion/node_modules
./fetch_fonts.sh
pip install faster-whisper pillow numpy

# 1. voiceover -> word timings
python3 transcribe.py audio/vo16k.wav transcript.json       # ffmpeg -i voice.mp3 -ac 1 -ar 16000 audio/vo16k.wav

# 2. write plan.py: one beat per visual idea, timed to word starts (see the Milgram plan)
# 3. collect visuals for the plan's image beats, review them, record choices in picks.py
python3 fetch_ddg.py && python3 fetch_openverse.py && python3 review_sheets.py
python3 gen_images.py                                       # generated stills for anything without a good image
python3 shots.py assets/archive/<film>.mp4 KEY               # shot list + contact sheet for archival films

# 4. build the timeline (cuts clips, prepares stills, captions, sound-effect cues)
python3 build_edit.py

# 5. audio: voice cleanup + music bed + ducking + effects, mastered to -14 LUFS
python3 mix.py

# 6. render (resumable, 4 chunks), then finish
(cd remotion && npx remotion bundle src/index.ts --out-dir=build)
./render_chunks.sh        # BROWSER_EXECUTABLE=/path/to/chrome-headless-shell is optional
./finish.sh ../../output/videos/<name>.mp4
```

`remotion/src/edit.json` and everything under `assets/`, `audio/`, `out/`, `review/` and
`remotion/public/a/` are generated and not committed.

## Components (`remotion/src`)

- `common.tsx`: `Media` (grades: ink, red, cold, sepia, gray, color; motion: in, out, left, right, up, down, shake),
  `Word`, `Typewriter`, `Carousel`, `ChapterCard`, `Caption`, `Laser` background
- `gfx.tsx`: `ShockPanel` (30-switch generator: reveal, cascade, sweep, press3, zoomLast, label, stepUp),
  `VoltMeter`, `Counter`, `VoltSteps`, `Staircase`, `PillLabel`, `Split`, `Prediction`, `Variations`, `Puppet`

Upgrade path: the components load fonts with `FontFace` + `delayRender` and embed footage with
`OffthreadVideo`; `video/.claude/skills/remotion-best-practices` recommends `@remotion/fonts` and
`@remotion/media` (`<Video>`), which are not installed in `video/` yet.

## Rights

Borrowed footage and web images are not cleared. The Milgram lab scenes appear to come from the
1979 film *I... comme Icare* and are the most likely to get a Content ID claim. The music
(incompetech.com, CC BY 4.0) needs the credit lines from `CREDITS.txt` in the video description.
