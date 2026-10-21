---
name: science-publish
description: Package a finished science-channel video for YouTube - Science Time style thumbnail, English title/description/tags with the required footage and music credits, and the upload checklist. Use for stage 6 of science-video.
---

# Publish package (stage 6)

## English captions (v3)
`pipeline.sh … render` writes `captions.en.srt` (every `C` line, timed to the voice). Upload it with the video
(`--captions`) so the whole story is readable in English. It also helps search and accessibility.

## Thumbnail
```bash
python scripts/video/thumbnail.py <4K still or frame.jpg> $MEDIA/fonts productions/NN-slug/thumbnail.jpg "10 FACTS" "about" "DARK MATTER" [--halo]
```
- Science Time look: black left half, huge rounded Fredoka title (3 lines), one striking space image on the right.
- From video 03 (owner's OK, 2026-10-20), test the gap-list variant:
  - a full-bleed hero image with a 2-line English hook
  - one keyword in yellow ("SOME ARE *OLDER THAN GALAXIES*")
  - "Hindi Documentary" kept in the title
  ```bash
  python scripts/video/thumbnail.py <frame.jpg> $MEDIA/fonts thumbnail.jpg --fullbleed "A TEASPOON WEIGHS" "*1 BILLION TONS*" \
    --label "Neutron Stars" --focus 0.6     # focus: where the subject sits horizontally (0-1)
  ```
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
- `captions.en.srt` is uploaded (v3).
- Commit `productions/NN-slug` (text files only) and push.

## Upload (`scripts/youtube/upload_youtube.py`)
Needs `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN` in `config/.env` (gitignored, never committed).
```bash
python scripts/youtube/upload_youtube.py whoami          # must print the Science Guy channel (UC6-6ZqXKuT7BQSx-c6zbNBg)
python scripts/youtube/upload_youtube.py upload $WORK/out/NN-slug.mp4 productions/NN-slug/youtube.md \
  --thumbnail thumbnail.jpg --captions productions/NN-slug/captions.en.srt --privacy private   # check it in Studio, then:
python scripts/youtube/upload_youtube.py publish <video_id> --comment productions/NN-slug/credits_full.txt
```
- The credits comment must be pinned by hand in YouTube Studio (the API can't pin).
- `invalid_grant` means the refresh token expired. Tokens expire after 7 days while the OAuth consent screen
  is in "Testing". Fix: `auth-url`, sign in with the channel's account, `exchange "<redirect URL>"`.
- The channel About text lives in `productions/channel/description.txt` (max 1000 characters, no `<` or `>`).
  Apply it with `upload_youtube.py channel --description productions/channel/description.txt`.
  Run `channel` with no options to show the current text.
