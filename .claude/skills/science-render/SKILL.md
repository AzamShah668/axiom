---
name: science-render
description: Assign a unique, relevant 4K shot to every scene of a science-channel edit, review the choices, render the master (footage, captions, graphics, transitions, music, SFX), review the render, fix problems and make chat-size previews. Use for stage 5 of science-video or whenever a render needs fixing.
---

# Assign, render, review (stage 5)

## 1. Assign shots
```bash
scripts/science/pipeline.sh productions/NN-slug assign
```
`assign_shots.py`:
- Runs `render_v2.plan()` (edit.json + timeline) to get every item (scenes, graphics, cards).
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
scripts/science/pipeline.sh productions/NN-slug render      # ~15-20 min on 4 cores for 12 min of 1080p
```
`render_v2.py` renders one chunk per section in parallel, then mixes the audio and concatenates. Per item:
- **Footage:** a Ken Burns zoom (1.0-1.07) on the proxy segment, with the crop applied.
- **Graphics:** drawn over the item's footage, blurred and dimmed to 40%.
- **Cards:** text over dimmed footage, with a flash-in.
- **Transitions:** xfade inside a beat; zoom / flash / whip / blur between beats.
- **Captions:** lower-third band (62 px Anton) or big centre caption.
- **Audio:**
  - narration
  - music bed per `edit.music`, 3 s crossfades, ducked -22 dB under speech / -13 dB in pauses
  - drone at -32 dB
  - SFX: whoosh -24, whoosh_big -15, pop -30 on big captions, boom -7
  - loudnorm -14 LUFS
- Sections are cached in `<out>_work/v2_<section>.mp4`. To re-render one section, delete its file and run
  render again (`--only <ids>` renders only those chunks without the final mux).

## 3. Review the render
```bash
scripts/science/pipeline.sh productions/NN-slug review     # one frame / 6 s -> $WORK/review_render/sheet_*.jpg
```
View every sheet. Look for:
- text/logos/insets/diagram lines inside footage
- white or black frames (the tool flags them)
- captions overlapping graphic labels
- irrelevant shots
- anything that looks like a repeat

Fix at the source:
- `ban` the shot or `exclude` seconds of a clip
- or move graphic labels in `render_video.gfx`

Then re-assign. Re-render only the affected sections if the assignment didn't change elsewhere; otherwise
re-render all.

## 4. Preview and delivery
```bash
scripts/science/pipeline.sh productions/NN-slug preview credits
```
- Preview: 3 x 720p parts under 30 MB each. Send them with SendUserFile.
- The full master needs a Drive/YouTube upload; ask once, or follow the owner's standing instruction.
- Commit `cutlist.json`: it records which shots this production used, so later productions avoid them.
