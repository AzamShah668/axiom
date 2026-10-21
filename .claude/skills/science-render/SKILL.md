---
name: science-render
description: Assign a unique, relevant 4K shot to every scene of a science-channel edit, review the choices, render the master in the v3 style (graded footage with camera moves, kinetic type, number cards, transitions, music bed, designed moments, SFX, CC track), review the render, fix problems and make chat-size previews. Use for stage 5 of science-video or whenever a render needs fixing.
---

# Assign, render, review (stage 5)

## 1. Assign shots
```bash
scripts/science/pipeline.sh productions/NN-slug assign
```
`assign_shots.py`:
- Runs the plan (edit.json + timeline) to get every item (scenes, graphics, number cards, chapter cards).
  For `"style": "v3"` this is `render_v3.plan()`:
  - breaths are spliced in
  - cuts are snapped to the pauses and word starts of `narration.wav`
  - overlays, SFX and music events are placed

  For older productions it is `render_v2.plan()`. The whole plan is stored in `cutlist.json`.
- Scores each library shot: 0.75 x CLIP(image, query) + 0.25 x CLIP(source title, query).
- Solves one global assignment (Hungarian). Rules:
  - every item gets a different shot
  - no two chosen shots show the same image: 3 frames from each shot's used part are compared, and a match
    means CLIP > 0.95 with phash distance <= 14, or CLIP > 0.975 with distance <= 26 (this catches the same
    picture re-zoomed or re-cropped in another video)
  - **text gate:** the frames each item will actually show are OCR'd at 768 px. A shot with any text is
    dropped and only that item is re-solved. This catches small labels such as "Artist's impression" and
    subtitles that the 2-second library scan misses
  - each shot must have enough text-free, moving seconds
  - `--avoid` leaves out shots that other productions' `cutlist.json` already used

Output: `$WORK/cutlist.json` and review sheets `$WORK/review_assign/review_*.jpg`. Each tile shows the item
number, `section/n`, score and query.

**Review every sheet** (view the images). For a wrong or weak shot:
- `"ban": ["<shot id or clip name>"]` in `edit.base.json` keeps it out (shot ids are in cutlist.json; clip names in the tile titles).
- `"pin": {"fact6/3": "<shot id>"}` forces a shot you found in `$LIB/shot_thumbs/`.
- Or rewrite the beat's query in `edit.spec` (`pipeline.sh ... edit assign`).
- Scores below ~0.20 usually mean no relevant footage exists. See science-footage "Gaps".

Re-run `assign` after every change. It is fast and deterministic.
`--local-only` uses only shots whose clip is on disk, for re-cuts after `restore-render`.

Review rounds converge automatically: `pipeline.sh ... assign` keeps every previously reviewed shot unless
it is now banned (`--keep`), and the sheets show only the items that changed (`--changed`).
Use `FRESH=1` for a clean re-solve, e.g. after the footage library grew.
Typical round 1 bans:
- graphic overlays, inset boxes and collages
- split screens and in-shot wipes
- data-map globes and flat maps
- presenters and lab talking heads
- pillarboxed or letterboxed images
- washed-out white frames

Main footage also gets a penalty for near-black or washed-out frames.

## 2. Render
```bash
scripts/science/pipeline.sh productions/NN-slug render      # v3: about 20 min on 4 cores for 12 min of 1080p
# quick look at a part: render_v3.py <same args> --range 20,45   (renders only those seconds)
```
`render_v3.py` (`docs/style-guide.md` has the rules and numbers) renders 10 s chunks in parallel (one OpenCV
thread per worker), then mixes and muxes. Per frame:
- **Footage:**
  - the proxy segment with its crop, graded by `grade.py` (preset from `edit.base.json`)
  - a camera move on top: push / drift / pull / roll; slow push on `{hold}`; impact push + shake on moments
- **Number cards and diagrams:** over blurred, dimmed footage (`mograph.card`, `render_video.gfx`).
  Chapter and title cards come from `mograph.chapter` / `mograph.title`.
- **Transitions:** hard cut, dip, flare, flash, whip, zoom, soft (rules in the style guide).
- **Overlays** in video time:
  - headlines, key lines, `over` number cards, the footer
  - the logo bug on every frame
- **Audio** (`mix()`):
  - the narration with the breaths spliced in
  - the music cues levelled to 16 LU under the voice while speaking, +3 dB in pauses, plus swells and drops
    at moments and the title
  - the synthesised SFX (`sfx.py`), levelled against the voice
  - a linear gain to -14 LUFS plus a peak limiter (no dynamic loudnorm)
  - stems are written to `<out>_work/stem_*.wav` for checks
- **Captions:** `<out>.en.srt` from the C lines; `pipeline.sh` copies it to `captions.en.srt`.
- Chunks are cached in `<out>_work/v3_<f0>_<f1>.mp4`. After a change, delete the chunks it touches (or the
  whole `_work` dir if the plan changed) and render again.

v2 productions (01, 02) still render with `render_v2.py`: running captions, 2.5 s scenes, Ken Burns zoom,
xfade/zoom/flash/whip/blur transitions, a bed 22 dB under the voice.

## 3. Review the render
```bash
scripts/science/pipeline.sh productions/NN-slug review     # one frame per item -> $WORK/review_render/sheet_*.jpg
```
View every sheet: each tile is one item as rendered (`<n> <section>/<k> <kind> m:ss`), so every shot is seen.
Pull full-resolution frames (start, middle, end) of anything doubtful before deciding. Also play the opening
minute of the master (or its preview).

Look for:
- text/logos/insets/diagram lines inside footage; split screens, mosaic edges, a lighter "plate" rectangle
  behind a visualization
- shapes that read as something silly (a "face" in a simulation)
- a headline or key line running over a chapter card or a graphic (the renderer cuts headlines at cards and
  skips key lines over graphics; if a key line is skipped, give the graphic its own later trigger)
- white or black frames (the tool flags them)
- captions overlapping graphic labels; a headline or number covering the subject
- a count that doesn't land on the spoken number (fix `land=`)
- music that is too loud in one cue (`"gain": -3` on that cue)
- irrelevant shots
- anything that looks like a repeat

Fix at the source:
- `ban` the shot or `exclude` seconds of a clip
- or move graphic labels in `render_video.gfx`

Then re-assign. Chunks are cached by frame range only (`<master>_work/v3_<f0>_<f1>.mp4`), so delete every
chunk whose items or overlays changed before rendering again. Adding or removing a cut shifts the camera-move
cycle of every later shot, so that means re-rendering from there on.

## 4. Preview and delivery
```bash
scripts/science/pipeline.sh productions/NN-slug preview credits
```
- Preview: 3 x 720p parts under 30 MB each. Send them with SendUserFile.
- The full master needs a Drive/YouTube upload; ask once, or follow the owner's standing instruction.
- Commit `cutlist.json`: it records which shots this production used, so later productions avoid them.
