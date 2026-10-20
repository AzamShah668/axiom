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
| 3 | Edit plan (v3 style, `docs/style-guide.md`): a visual query for every sentence, headlines, number cards, moments, CC captions, music | `science-edit-plan` | `edit.spec`, `edit.base.json`, `edit.json` |
| 4 | 4K footage library for the topic | `science-footage` | `$LIB` shots (QC'd, embedded) |
| 5 | Shot assignment (no repeats) -> render -> review -> fixes -> preview | `science-render` | master `.mp4`, `captions.en.srt`, preview parts, `cutlist.json` |
| 6 | Thumbnail, description with credits, upload checklist | `science-publish` | `thumbnail.jpg`, `youtube.md`, `credits.txt` |

One command runs the scripted parts (stages 2-6 except writing):
```bash
export PY=<venv python> WORK=<work dir> LIB=<shared library dir> MEDIA=<shared media dir>   # defaults: work/...
scripts/science/pipeline.sh productions/NN-slug restore          # fresh container: library + media back from Drive
scripts/science/pipeline.sh productions/NN-slug setup            # once per machine: fonts, music, stills
scripts/science/pipeline.sh productions/NN-slug narration edit footage assign
scripts/science/pipeline.sh productions/NN-slug topup assign     # more 4K footage for weakly matched scenes
#   -> look at $WORK/review_assign/*.jpg, ban/pin/requery in edit.base.json / edit.spec, then
#      `pipeline.sh ... edit assign` again (reviewed shots are kept; sheets show only what changed)
scripts/science/pipeline.sh productions/NN-slug render review
#   -> look at $WORK/review_render/sheet_*.jpg, fix, re-render the affected sections
scripts/science/pipeline.sh productions/NN-slug preview credits
#   -> publish (science-publish), commit the production folder, then:
scripts/science/pipeline.sh productions/NN-slug archive          # everything heavy -> Google Drive, deleted here
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
- **Editing style v3** (`docs/style-guide.md`, the owner's decisions of 2026-10-20). Every video from 03 on.
  - **Intro:** a 15-30 s hook that names the topic in its first sentence, then the story cold open, then the
    title card.
  - **Pace:** cuts follow the voice (pauses, word starts), about 3 s scenes, holds for awe, 15-19 cuts/min.
  - **On-screen text:** key phrases only:
    - kinetic headlines and key lines on the spoken words
    - every number as an animated card that lands on the spoken number
    - the full English text as a CC track (`captions.en.srt`), not burned in
    - a `SCIENCE GUY` logo bug top right
  - **Look:** one colour grade per video, camera moves by energy, transitions by meaning (hard cut default,
    dips at idea breaks, flares on reveals).
  - **Sound:**
    - a Kevin MacLeod bed you can hear (16 LU under the voice, flat)
    - 3-5 designed moments (breath, riser, impact, swell or silence)
    - synthesised SFX by rule
    - master at -14 LUFS

## Storage: Google Drive, not the container (owner's rule)
Drive folder `axiom-science-channel` (README.txt there explains it):
| Drive folder | Contents |
|---|---|
| `videos/` | finished masters + thumbnails named `NN - <YouTube title> 1080p.mp4` |
| `productions/NN-slug/` | the work dir: voice/, out/ (master, previews), cutlists, review sheets |
| `footage-library/` | the shared library; `clips/` named `<category>__<archive-title>__<id>.mp4`, plus catalog.csv and the shot metadata |
| `media/` | fonts, music, graphic stills |
| `misc/` | session scratch |

- After every video, `pipeline.sh ... archive`:
  - catalogues the library (`scripts/footage/catalog.py`): CLIP category and tags, usable seconds, used-in.
    It writes `productions/footage-catalog.csv` (committed, searchable without downloading anything) and the
    descriptive Drive names.
  - copies the master and thumbnail into `videos/`.
  - pushes `$WORK`, `$LIB` and `$MEDIA`, then deletes them locally. Each file's MD5 is checked on Drive before its
    local copy is removed. Nothing heavy stays in the cloud container.
- Fresh container:
  - `restore`: the full library, for footage/assign of a new video.
  - `restore-render`: only the clips in `cutlist.json`, for re-rendering a finished one.
  - Downloads turn `<...>__<id>.mp4` back into `<id>.mp4`, so cutlists, bans and pins keep working.
- Picking footage by hand: `grep -i "accretion" productions/footage-catalog.csv` gives clip ids for `pin` / `ban`.
  The `used_in` column shows footage earlier videos already showed.
- Tool: `scripts/storage/drive_sync.py` (`quota`, `ls`, `push`, `pull`, `put`, `copy`, `rename`).
  - Credentials: `DRIVE_REFRESH_TOKEN` plus the YouTube OAuth client in `config/.env`.
  - Scope `drive.file`: it only sees the files it created.
  - If the token stops working: run `drive_sync.py auth-url`, have the owner sign in, then `exchange "<redirect URL>"`.
- The Python venv is not archived; rebuild it from `scripts/requirements-science.txt`.

## Delivery
- The master is 1080p (~500 MB) and too large for chat. Send `preview_parts.sh` output: 3 x 720p, under 30 MB each.
- The full master goes to YouTube (`scripts/youtube/upload_youtube.py`, see science-publish) and to Drive with `archive`.
- Commit and push the production folder: script, narration text, `edit.spec`, `edit.json`, `cutlist.json`,
  `youtube.md`, `credits.txt`.

## Lessons already learned (don't repeat them)
- `assign_shots.py` writes the shot's source title into each item's `title` key. Plan items must not use `title`
  for their own text (v3 uses `ttl` / `ctitle`).
- Many ESO zoom videos open on the same all-sky Milky Way panorama. Cut long videos from their end
  (`--from-end`), or "different" shots will look repeated.
- Review sheets catch what QC can't: graphic overlays, inset boxes, split screens, wipes, data-map globes,
  presenters, pillarboxed 4:3 images. Ban those clips in `edit.base.json` (production 01 has a long list to learn from).
- Archive "lensing" folders are mostly black-hole visualisations: check the review sheets, not titles.
- Graphic stills can carry diagram lines (the ESA Milky Way has a pointer line; `render_video.remove_hlines`).
- `pkill -f <pattern>` kills your own shell when the pattern is in the command line; stop jobs by task id or PID.
- Render with one OpenCV thread per worker (`cv2.setNumThreads(1)`), or the render takes 5x longer.
- The 4K archives overlap a lot between topics: production 02's first 330 picks were 252 clips already in the
  library. `--avoid` removes every shot an earlier production used *and* its look-alikes, so plan on a `topup`.
- Drive downloads can arrive gzip-encoded; `drive_sync.py` decodes and MD5-checks every download.
