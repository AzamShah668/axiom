---
name: science-shorts
description: Cut YouTube Shorts (1080x1920, 35-60 s) from a finished science-channel video - one per fact plus the cold open, each opening on its strongest line, telling the fact's story and ending on a written FULL VIDEO BELOW card - re-framed from the 4K sources, reviewed, previewed and uploaded private. Use for stage 7 of science-video or when asked for Shorts from a video.
---

# Shorts (stage 7)

Owner's plan (2026-10-22): every video gets as many Shorts as it can carry, cut from the finished video.
The rules are in `productions/README.md` ("Shorts"):
- Each Short is a **hook + body**.
- The **end card is written, never spoken**.
- The full video is linked through **Related video** in Studio.

## 1. shorts.spec (the owner approves it, like a script)
`productions/NN-slug/shorts.spec`, one block per Short. Lines are named by the start of their English `C` caption:
```
== teaspoon | A Teaspoon of This Star Weighs a Billion Tons #shorts
hook: According to NASA, one teaspoon
body: The strangest thing about neutron stars .. So scientists calculate
```
- **hook:** the line that wins the first second. Pick a line with a number card or a reveal: the count starts on
  frame 0, so the number is the hook.
- **body:** one or more runs of lines, `first .. last`, in story order. The hook line is left out of the run
  automatically, so the run can cover the whole fact.
- **Length:** aim for 35-60 s. Trim setup lines rather than the payoff.
- **Coverage:** one Short per fact, plus the cold open. Two facts may share a Short only when they tell one story.
- **Title:** `<English hook> #shorts`, under 100 characters. Never Hindi in titles or on screen.

## 2. Render
```bash
ONLY=teaspoon scripts/science/pipeline.sh productions/NN-slug shorts   # one; without ONLY: every Short in the spec
```
`scripts/video/render_short.py` re-uses the master's reviewed plan, re-timed onto the Short's clock:
- the cuts, shots, camera moves, headlines, key lines, number cards and sound design
- each shot fetched again from its 4K source (`sources.json`) and framed 9:16 around its brightest subject
  (cached in `$WORK/out/shorts/vclips/`)
- audio: the master's voice stem (`<master>_work/stem_voice.wav`), a fresh bed of the section's music track,
  the plan's sounds, a whoosh at the hook -> story join
- layout: headlines centred, number cards in the middle, the name tag at 62% height, the logo top-left, so
  nothing sits under the Shorts buttons (right side) or the title (bottom fifth)
- no fade-in (the hook hits on frame 0) and no fade-out (the end card loops into the hook)

Output: `$WORK/out/shorts/<id>.mp4`, `<id>.en.srt` and `<id>.plan.json`.

## 3. Review
- `python scripts/video/review_sheet.py $WORK/out/shorts/<id>.mp4 <dir> --cutlist $WORK/out/shorts/<id>.plan.json`
  gives one frame per shot.
- Look for:
  - a subject cut off by the 9:16 window
  - text running off the 1080 px width
  - anything under the right-side buttons or the bottom title area
  - a flash frame at a join
  - the end card readable for its full 2.6 s
- Callout, route and HUD overlays are pinned to 16:9 positions and are left out (the log says so).
- Send the Short to the owner with SendUserFile (one file, under 30 MB; re-encode at 720x1280 if bigger).

## 4. Upload (private) and link
- Upload each Short **private** with `scripts/youtube/upload_youtube.py`. The description carries:
  - 2 lines on the fact
  - "Full video: <link>"
  - the footage and music credits (`credits.txt`; every Short needs them)
  - #shorts plus 2-3 tags
- The full video must be **public** before a Short can link to it.
- The owner sets **Related video** in YouTube Studio on each Short; it is not in the public API. Give them a
  checklist: Short title, video ID, the full video to link.
- Release about one Short a day after the full video goes public; never publish without the owner's word.
- After about 10 Shorts, compare in Analytics:
  - viewed vs swiped away
  - average view duration
  - related-video clicks
  - subscribers gained

  Then adjust the hook choice and length.
