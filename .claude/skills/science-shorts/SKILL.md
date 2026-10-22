---
name: science-shorts
description: Cut YouTube Shorts (1080x1920, 35-60 s) from a finished science-channel video - one per fact plus the cold open, each opening on a spoken "क्या आपको पता है…" hook over its strongest shot and number card, then the fact's story at 1.1x, a square picture between black bars with a title on top, and a written FULL VIDEO BELOW card - reviewed, previewed and uploaded private. Use for stage 7 of science-video or when asked for Shorts from a video.
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
top: ONE TEASPOON OF A NEUTRON STAR / WEIGHS *A BILLION TONS*
hook: According to NASA, one teaspoon
say: क्या आपको पता है, कि neutron star का सिर्फ़ एक चम्मच, Earth पर लगभग एक अरब टन का होता है?
say_en: Did you know that just one teaspoon of neutron star weighs about a billion tons on Earth?
land: अरब
body: The strangest thing about neutron stars .. So scientists calculate
```
- **top:** the title bar above the picture, in English. ` / ` sets the line break; `*gold*` marks the payoff phrase.
- **hook:** the master line whose shots and number card the spoken hook plays over. Pick a number or a reveal.
- **say:** the new spoken hook. It asks the viewer ("क्या आपको पता है, कि…"; the owner's exception for Shorts
  hooks only) and ends on the number. Simple spoken Hindi; numbers in Hindi words; English terms in Latin
  letters. It is rendered with the locked voice and cached in `$WORK/out/shorts/tts/` (about 90 credits each).
- **say_en:** its English line (the Short's caption file).
- **land:** the word in `say` where the count stops. The number is up and counting from frame 0.
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
- each shot fetched again from its 4K source (`sources.json`) and cropped square around its brightest subject
  (cached in `$WORK/out/shorts/vclips/`)
- audio: the master's voice stem (`<master>_work/stem_voice.wav`), a fresh bed of the section's music track,
  the plan's sounds, a whoosh at the hook -> story join
- layout: a 1080x1080 square picture in the middle, black bars of 420 px above and below. The `top` title is
  in the top bar; the bottom bar is left for YouTube's title and buttons. Headlines are centred.
- pace: `--speed 1.1` by default. The voice is time-stretched with rubberband (pitch kept) and every time on
  the plan is scaled to match; footage plays at normal speed.
- cut points come from the voice track: a section's first line starts under its chapter card, before its
  caption does, so the cut walks back to the silence before the first word
- no fade-in (the hook hits on frame 0) and no fade-out (the end card loops into the hook)

Output: `$WORK/out/shorts/<id>.mp4`, `<id>.en.srt` and `<id>.plan.json`.

## 3. Review
- `python scripts/video/review_sheet.py $WORK/out/shorts/<id>.mp4 <dir> --cutlist $WORK/out/shorts/<id>.plan.json`
  gives one frame per shot.
- Check the spoken hook and every join with speech recognition (faster-whisper medium): no clipped first word.
- Look for:
  - a subject cut off by the square window
  - text running off the 1080 px width
  - anything under the right-side buttons or the bottom title area
  - a flash frame at a join
  - the end card readable for its full 2.6 s
- Callout, route and HUD overlays are pinned to 16:9 positions and are left out (the log says so).
- Send the Short to the owner with SendUserFile (one file, under 30 MB; re-encode at 720x1280 if bigger).

## 4. Upload (private) and link
Package file per Short: `productions/NN-slug/shorts/<id>.md` (same **Title** / **Description** / **Tags**
format as `youtube.md`; credits list every archive video ID the Short uses, no pinned comment needed).
```bash
python scripts/youtube/upload_youtube.py upload $WORK/out/shorts/<id>.mp4 productions/NN-slug/shorts/<id>.md --privacy private
```
`--privacy private` is required: the uploader's default is public.
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
