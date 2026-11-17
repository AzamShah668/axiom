---
name: science-publish
description: Package a finished science-channel video for YouTube - English title/description/tags with the required footage and music credits, and the upload checklist. Use for stage 6 of science-video.
---

# Publish package (stage 6)

## English captions (v3)
`pipeline.sh … render` writes `captions.en.srt` (every `C` line, timed to the voice). Upload it with the video
(`--captions`) so the whole story is readable in English. It also helps search and accessibility.

## Thumbnail: the owner makes it
Do not make a thumbnail unless the owner asks (owner's rule, 2026-10-21). The owner designs and sets it in YouTube
Studio. Upload without `--thumbnail`. When he asks for drafts, `scripts/youtube/make_thumbnail.py` makes three
(no pipeline stage runs it):
```bash
python scripts/youtube/make_thumbnail.py productions/NN-slug --out $WORK/thumbs   # reads productions/NN-slug/thumbs.json
```
- `thumbs.json`: three entries `{"id","query","lines":["IT HIT EARTH","*FROM 50,000 LY*"],"title","shot","t","focus",
  "zoom","pos","ring","void"}` (docstring). Each differs in idea, not colour; 2-6 words, English/Roman only,
  `*line*` = yellow. Frames come only from the cutlist's shots (CLIP-ranked); pin a frame from
  `candidates_X.jpg` with `shot`/`t`.
- It writes `thumb_{A,B,C}.jpg` (1280x720, <= 2 MB), `preview_grid.jpg` (mobile-feed mock) and `thumbs.out.json`
  (shot, source and the credit line to add to the description). It exits 1 if a lint fails (cap height, contrast,
  corners, word overlap with the titles, size).
- The owner sets A as the default and adds B and C in Studio > Test & Compare at publish (no API; not on private
  videos).

## youtube.md
- **Title:** `<Topic hook> | Hindi Documentary`, <= 60 characters with the hook in the first 45.
- **Titles (A/B)** (optional, only if the owner wants an A/B test): a block of up to three lines under that heading,
  `T1: ...` (search keyword), `T2: ...` (a true number), `T3: ...` (Hinglish). With no **Title** line the uploader
  uses T1; the others are added in Studio.
- **Description:**
  - two short English paragraphs (hook + what the story covers, no spoilers of the last fact)
  - then the credits block from `pipeline.sh ... credits` (`credits.txt`)
  - then 3-5 hashtags
- The credits are required:
  - ESO / ESA/Hubble / ESA/Webb footage is CC BY 4.0 (credit + licence)
  - Kevin MacLeod music is CC BY 4.0 with exact titles
  - NASA footage is credited to NASA's Goddard Space Flight Center
  - archive footage and recordings are named one by one ("Archive footage and recordings: …" from
    `credits.py`); add audio-only recordings from bites.json by hand (credit + licence)
- **Length:** YouTube refuses a description over 5,000 characters (video 05's itemised credits made 7,082). Keep the
  footage, CC BY and music credits in the description; put the item-by-item archive, recording and photo lists in
  `credits_full.txt` (the pinned comment, up to 10,000 characters) and say so in one line.
- **Tags:** topic in English and Hindi-search forms ("dark matter hindi", "hindi documentary", "space
  documentary hindi"), plus key names from the script.
- **Chapters:** list `0:00 Intro` plus each card's start time (the cutlist's card items, `t0`) as YouTube chapters.

## Package lint
`python scripts/youtube/package_lint.py productions/NN-slug/youtube.md` warns (never fails) on: title > 60 chars or
hook > 45, description line 1 repeating the title, > 12 tags, missing footage/licence/music credits, > 5,000 bytes.

## Upload checklist
- The master plays end to end and is 1080p30 at -14 LUFS (`ffmpeg -i master.mp4 -af ebur128 -f null -`).
- Title, description, credits, tags and chapters are all in English.
- `captions.en.srt` is uploaded (v3).
- Commit `productions/NN-slug` (text files only) and push.

## Upload (`scripts/youtube/upload_youtube.py`)
Needs `YT_CLIENT_ID`, `YT_CLIENT_SECRET` and `YT_REFRESH_TOKEN` in `config/.env` (gitignored, never committed).
```bash
python scripts/youtube/upload_youtube.py whoami          # must print the Science Guy channel (UC6-6ZqXKuT7BQSx-c6zbNBg)
python scripts/youtube/upload_youtube.py upload $WORK/out/NN-slug.mp4 productions/NN-slug/youtube.md \
  --captions productions/NN-slug/captions.en.srt   # private is the default; check it in Studio, then:
python scripts/youtube/upload_youtube.py publish <video_id> --comment productions/NN-slug/credits_full.txt
```
- The credits comment must be pinned by hand in YouTube Studio (the API can't pin).
- `invalid_grant` means the refresh token expired. Tokens expire after 7 days while the OAuth consent screen
  is in "Testing". Fix: `auth-url`, sign in with the channel's account, `exchange "<redirect URL>"`.
- The channel About text lives in `productions/channel/description.txt` (max 1000 characters, no `<` or `>`).
  Apply it with `upload_youtube.py channel --description productions/channel/description.txt`.
  Run `channel` with no options to show the current text.

## Measurement (`scripts/youtube/analytics.py`)
Needs the read-only Analytics scope once: `upload_youtube.py auth-url --analytics`, sign in with the channel's
account, `exchange "<redirect URL>"` (the new token keeps the upload scopes; old tokens still upload).
```bash
python scripts/youtube/analytics.py retention <video_id> productions/NN-slug --label 7d   # -> retention.md
python scripts/youtube/analytics.py summary <video_id> productions/NN-slug --label 48h \
  --impressions <Studio> --ctr <Studio %>                                                  # appends to stats.md
```
- `retention.md`: Intro % at 0:30, the 5 steepest drops after 0:30 with the line spoken, the shot and the
  on-screen text (from `cutlist.json`), spikes, loss per chapter, relative retention.
- Run at 48 h, 7 d and 28 d. Impressions and CTR are not in the API: type them from Studio > Reach.
- `--save-json raw.json` keeps the API response; `--from-json raw.json` re-makes the report offline.
- Act on a pattern seen in 2+ videos, never on one dip.
