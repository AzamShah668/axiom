---
name: science-publish
description: Package a finished science-channel video for YouTube - Science Time style thumbnail, English title/description/tags with the required footage and music credits, and the upload checklist. Use for stage 6 of science-video.
---

# Publish package (stage 6)

## Thumbnail
```bash
python scripts/video/thumbnail.py <4K still or frame.jpg> $MEDIA/fonts productions/NN-slug/thumbnail.jpg "10 FACTS" "about" "DARK MATTER" [--halo]
```
- Science Time look: black left half, huge rounded Fredoka title (3 lines), one striking space image on the right.
- 1280x720.
- Use a frame from a shot in the cut (`ffmpeg -ss <t> -i master.mp4 -frames:v 1`) or an archive still with
  a CC BY / public-domain licence.
- English only. Never put Hindi on the thumbnail.

## youtube.md
- **Title:** `<Topic hook> | Hindi Documentary`.
- **Description:**
  - two short English paragraphs (hook + what the story covers, no spoilers of the last fact)
  - then the credits block from `pipeline.sh ... credits` (`credits.txt`)
  - then 3-5 hashtags
- The credits are required:
  - ESO / ESA/Hubble / ESA/Webb footage is CC BY 4.0 (credit + licence)
  - Kevin MacLeod music is CC BY 4.0 with exact titles
  - NASA footage is credited to NASA's Goddard Space Flight Center
- **Tags:** topic in English and Hindi-search forms ("dark matter hindi", "hindi documentary", "space
  documentary hindi"), plus key names from the script.
- **Chapters:** list `0:00 Intro` plus each card's start time (the cutlist's card items, `t0`) as YouTube chapters.

## Upload checklist
- The master plays end to end and is 1080p30 at -14 LUFS (`ffmpeg -i master.mp4 -af ebur128 -f null -`).
- Title, thumbnail, description, credits, tags and chapters are all in English.
- Uploading itself is a manual step, or goes through `modules/uploader/youtube_uploader.js` once it is set
  up for this channel.
- Commit `productions/NN-slug` (text files only) and push.
