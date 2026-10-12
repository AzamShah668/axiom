---
name: science-video
description: End-to-end workflow for the Hindi science documentary channel (Science Time method): topic -> story script -> Hindi narration (ElevenLabs Neel) -> edit plan -> unique 4K footage -> render -> review -> preview -> YouTube package. Use when asked to make, remake, continue or fix a science video ("make the next video", "10 facts about black holes | Hindi Documentary", "redo the dark matter video").
---

# Science video workflow (Hindi documentary channel)

One production = one folder `productions/NN-slug/`. Heavy files (footage library, voice, renders) live in a
work dir and are rebuilt by the pipeline; only text, plans and cut lists are committed.

Run the stages in order. Each stage has its own skill with the details and the quality bar; read it before
doing the stage. Do not skip the review gates.

| # | Stage | Skill | Output |
|---|-------|-------|--------|
| 1 | Topic, research, story script, Devanagari narration, title/thumbnail/description | `science-script` | `script.md`, `tts/narration.hi.md` |
| 2 | Hindi voice-over with the locked voice | `science-narration` | `$WORK/voice/narration.wav`, `timeline.json` |
| 3 | Edit plan: a visual query for every sentence, captions, graphics, music | `science-edit-plan` | `edit.spec`, `edit.base.json`, `edit.json` |
| 4 | 4K footage library for the topic | `science-footage` | `$LIB` shots (QC'd, embedded) |
| 5 | Shot assignment (no repeats) -> render -> review -> fixes -> preview | `science-render` | master `.mp4`, preview parts, `cutlist.json` |
| 6 | Thumbnail, description with credits, upload checklist | `science-publish` | `thumbnail.jpg`, `youtube.md`, `credits.txt` |

One command runs the scripted parts (stages 2-6 except writing):
```bash
export PY=<venv python> WORK=<work dir> LIB=<shared library dir> MEDIA=<shared media dir>   # defaults: work/...
scripts/science/pipeline.sh productions/NN-slug setup            # once per machine: fonts, music, stills
scripts/science/pipeline.sh productions/NN-slug narration edit footage assign
#   -> look at $WORK/review_assign/*.jpg, fix with pins/bans/queries, re-run assign
scripts/science/pipeline.sh productions/NN-slug render review
#   -> look at $WORK/review_render/sheet_*.jpg, fix, re-render the affected sections
scripts/science/pipeline.sh productions/NN-slug preview credits
```
Python deps: `scripts/requirements-science.txt` (torch CPU first). Secrets: `ELEVENLABS_API_KEY` in
`config/.env` (gitignored). Never commit keys, audio, video, or other people's transcripts (the repo is public).

## Non-negotiable channel rules (from the owner's reviews)
- **Packaging:** title `<Topic> | Hindi Documentary`. Everything written (title, thumbnail, captions, cards,
  description, tags) is English; only the narration is Hindi.
- **Narration:** pure third-person storytelling. Never address the viewer: no "aap", commands, questions to
  the audience, "number 10..." announcements or subscribe requests. Countdown lives only on the chapter cards.
  No India-specific comparisons. Voice: ElevenLabs "Neel - Paranormal Story Narrator" (`productions/voice-preset.json`).
- **Footage:**
  - Every footage shot comes from a **4K source** (>= 3840 px wide; `fetch_proxies.py` refuses anything less).
  - It is **continuously moving**: frozen seconds are cut by `build_shots.py`.
  - It is **relevant to the sentence being spoken**: a visual query per beat, matched with CLIP, then a human review.
  - **No shot is ever used twice in a video**, and neither is a near-identical copy of one. `assign_shots.py`
    enforces this, and `--avoid` keeps footage from earlier productions out.
  - **No text, logos or labels inside footage**: OCR-checked, corner labels auto-cropped, the rest excluded.
  - No static photos. Stills only appear inside explanatory graphics, always moving.
- **Pace and on-screen text:**
  - A new shot every ~2.5 s.
  - An English caption for every sentence; key names and numbers get big centre captions.
  - Transitions on topic changes, with a whoosh.
- **Sound:** Kevin MacLeod dark-ambient bed ducked ~22 dB under the voice and rising in pauses, a low drone,
  whooshes, and booms on big moments. Master at -14 LUFS.

## Delivery
- The master is 1080p (~500 MB) and too large for chat. Send `preview_parts.sh` output: 3 x 720p, under 30 MB each.
- Offer the full file through a connected Drive or YouTube upload.
- Commit and push the production folder: script, narration text, `edit.spec`, `edit.json`, `cutlist.json`,
  `youtube.md`, `credits.txt`.

## Lessons already learned (don't repeat them)
- Archive "lensing" folders are mostly black-hole visualisations: check the review sheets, not titles.
- Graphic stills can carry diagram lines (the ESA Milky Way has a pointer line; `render_video.remove_hlines`).
- `pkill -f <pattern>` kills your own shell when the pattern is in the command line; stop jobs by task id or PID.
- Render with one OpenCV thread per worker (`cv2.setNumThreads(1)`), or the render takes 5x longer.
