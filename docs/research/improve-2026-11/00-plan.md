# 00 · Improvement plan (2026-11-17)

Built from reports 01-05 in this folder, checked against `productions/README.md` (the owner's rules, which
override the research) and the code. Branch `claude/improve-2026-11`; the owner decides later whether to merge.

## 1. Where we are lacking, ranked by expected effect on views

Views = impressions x CTR x retention, plus the Shorts funnel.

| # | Gap | Factor it hits |
|---|---|---|
| 1 | **Packaging.** Videos go public with no thumbnail (05 did), one search-label title and no A/B test. | CTR, the largest multiplier |
| 2 | **The first 30 s.** 08 opens on a hedged 24-word sentence, says the title's promise at 25.8 s, teases only chapter 1, and slows to 4-6 s scenes after 4 s. | Intro retention, the steepest part of the curve |
| 3 | **No measurement.** Nothing reads retention, CTR or Shorts numbers. | Makes every other item testable |
| 4 | **Shorts funnel.** A 4.6 s end card (11% dead tail), the hook number at 2.5-5 s, captions under the buttons, 3 Shorts for 10 chapters, a CTA that lands at 0:00. | Shorts reach and hand-off |
| 5 | **The middle sags.** No on-screen text for 30 s at 5:41, 6:58 and 9:19; all 17 number cards are `hero`; five drone beds from 5:07; flat sentence rhythm (mean 19.9 words). | Mid-video retention |
| 6 | **Finish.** 5 Hz judder (25 fps sources forced to 30), the upload encoded twice, grain that moves with the camera, a voice too bass-heavy for phones. | Perceived quality: small, cheap |
| 7 | **No room for an end screen.** The video ends 3 s after the last word. | Session time |

Gaps 1 and 2 need the owner (thumbnails, script). The code below makes them cheap to act on.

## 2. Conflicts between the reports, resolved

| Topic | Decision |
|---|---|
| End tail: 12 s (01) or 18 s with empty boxes (03) | One key `end_tail`, default 0, recommended 12. No boxes, no text: a shorter tail costs less retention, and 04 wants abrupt endings. |
| Rhythm thresholds: 01 or 04 | 04's (they are more exact), as advice only. The owner asked for flowing sentences, so the check asks to add short lines, never to shorten long ones. |
| SFX target: 18-25/min (style guide) or 10-15 (01); fail the edit on few key lines (01) | Lint band 8-15/min; the owner calls dense SFX over-editing. Everything warns; only a 30 s gap can fail, and only with `--strict`. |
| Analytics: `retention.py` (01) or `upload_youtube.py stats` (03) | One new `analytics.py` and one new scope, requested only with `auth-url --analytics`. Existing tokens keep working. |
| Shorts length: 30-35 s (02) or 35-60 s (README) | The owner's rule stands. A lint reports words and predicted length. |
| Shorts speed default 1.2 → 1.1 (02) | Yes, in `render_short_v2.py` only. All three 08 `short.json` already say 1.1, so no render changes. |
| Shorts at 25 fps (05) | Not now: wait for the long-form trial. |
| `SR = 48000` (05) | Skip: `render_short_v2.py` shares `r3.mix` at 44.1 kHz and the mux already resamples. Only the AAC bitrate rises. |
| Music: energy tags (01) or swells (05) | Both. Tags and a warning at the edit stage (WP2), swells in the mix (WP3). `BED_LU` stays 16. |
| Titles and thumbnails (03) against two owner rules | Tools only; see §4. |

## 3. Work packages

Six packages with no file in common. Rules for all:
- **Opt-in.** A production without the new keys renders exactly as today. `make_edit.py` already copies unknown
  `edit.base.json` keys into `edit.json`.
- **Tests write to the scratchpad only**, never into `work/` (shared) or `productions/`. They read voice, cutlists
  and clips from `work/`. Free disk is about 9 GB, so keep ranges short.
- No ElevenLabs call, no YouTube call, no media, frames or transcripts committed.
- `productions/README.md` and `STATUS.md` are not edited: rule changes are the owner's (§4).

### WP1 · Script checker and script method (1 day)
**Goal:** catch a weak hook, flat rhythm and missing turns before the owner reviews a script.
**Files:** `scripts/science/script_check.py`, `.claude/skills/science-script-v2/SKILL.md`, new `productions/outline.template.md` (04 §3).
**Spec:** existing checks and their exit code stay. New checks print `~` lines and change the exit code only with
`--strict`; `--skip <names>` turns checks off.
- `--voice neel|rudra` sets the pace (147 / 170 wpm; `--wpm` wins). Print each section's start time.
- `hook`: first sentence > 12 words, a hedge in it (`ho sakte|shayad|lagbhag|andaaza`), or OPENING > 130 words.
- `rhythm`, per section: fewer than one sentence of ≤ 7 words per 120 words; more than 2 flat runs (3 sentences
  in a row, each ≥ 12 words, within ±4 words); any sentence > 24 words.
- `turns`: ≥ 120 words without `lekin|magar|par\b|jabki|phir bhi|balki|asal mein|isliye`.
- `person`: a CHAPTER with no 4-digit year, or no capitalised two-word name outside an object list (`--objects`).
- `numbers`: `billion|crore|lakh|quadrillion|\d{4,}` with no `jaise|jitna|jitni|matlab|yaani|barabar` in that or
  the next sentence. `hedges`: more than one "lagbhag" per 150 words.
- `tells`: `sabse \w+ \w* ?mein se`; a 2-word phrase shared by ≥ 3 chapter-final sentences; > 3 reaction lines.
- `rehook`: a section over 95 s.
- Skill, marked "proposed 2026-11, on trial until the owner approves": hook order (scene → stakes by 15 s → 2-3
  concrete third-person teasers → open loop), chapter order (belief → person and year → *lekin* → payoff → a
  bridge naming one picture), a spine for list topics, strong events near 3:00 and 6:00, ending ≤ 45 s, three
  title ideas at topic time.

**Test:** run on every `productions/*/script.txt`; add a tripping and a clean fixture string per check.
**Accept:** default exit codes equal `main`'s; 08 gets `hook`, `rhythm` and `person` lines; the rewritten 08
opening in 04 §4 gets no `hook` line.

### WP2 · Edit-plan lint and music energy (1 day)
**Goal:** dead zones and a thin last third are seen at the edit stage.
**Files:** new `scripts/video/pace_lint.py`, new `scripts/video/music_energy.json`, `scripts/video/make_edit.py`,
`scripts/science/pipeline.sh` (edit stage only), `.claude/skills/science-edit-plan/SKILL.md`.
**Spec:**
- `pace_lint.py <cutlist.json>` or `pace_lint.py --edit <edit.json> --timeline <timeline.json>` (calls
  `render_v3.plan()` itself). Flags: `--window 20`, `--gap 30`, `--strict`.
- A visual event is a headline, key line, number card, name card, own graphic, photo, or a whip/flash/dip/flare.
- It prints a per-minute table (cuts, overlays by kind, SFX) and warns on: a window with no event; `hero` > 50%
  of number cards; SFX/min outside 8-15; fewer than 15 key lines or 12 headlines per 11 min (scaled); the last
  third holding under 25% of the overlays. Exit 1 only with `--strict` and a gap ≥ `--gap`.
- `pipeline.sh … edit` runs it without `--strict` after the plan-only check.
- `music_energy.json`: `{"<track>.mp3": "low|mid|high"}` for each track in `$MEDIA/music`, from measured onset
  rate and loudness range. `make_edit.py` warns on 3 `low` cues in a row and on no `mid/high` cue after the midpoint.
- Skill: the claim-to-template table (ratio → `scale`, A = B → `equation`, travel → `route`/`line`, share →
  `progress`/`gauge`, a spot in the shot → `callout`) and 2 s teaser beats with an `over` card in the opening.

**Test:** `pace_lint.py productions/08-scariest-places/cutlist.json`; `make_edit.py` on 08 into the scratchpad.
**Accept:** it reports the gaps at 5:41, 6:58 and 9:19, 17/17 `hero` and the drone run; exit 0; 08's `edit.json` is unchanged.

### WP3 · Long-form renderer (2.5-3 days)
**Goal:** a faster first 30 s, an end-screen tail, a cleaner picture and voice. One engineer owns every renderer file.
**Files:** `scripts/video/render_v3.py`, `grade.py`, `render_video.py`, `render_v2.py`,
`scripts/footage/fetch_proxies.py`, `scripts/elevenlabs/voice_post.sh`, `docs/style-guide.md`, `.claude/skills/science-render/SKILL.md`.
**Spec (keys in `edit.base.json`, all absent by default):**
- `"opening_pace": {"target": 2.2, "max": 4.0}`: in `plan()`, default scenes of the first section use these in
  place of `TARGET` 3.0 and `MAX_SCENE` 6.5. `{hold}`, `{flash}` and `{Ns}` beats are untouched.
- `"end_tail": 12`: added to `total`; the last scene continues as a slow push (1.5%/s) darkened to 70%, with one
  +4 dB swell and the existing 4 s fade. No text.
- `"music_arc": true`: a swell (+4 dB, 0.3 s up, 1.2 s down) at each section start and `typing` moment,
  `_level(keep=0.4)`, pause lift 0. It is read from `P`, so Shorts, which call `r3.mix`, are unaffected.
- `"grade": {"finish": "v2"}`: `Grade.color()` (LUT + saturation) before `camera()`, `Grade.finish()` (vignette +
  grain) after it, clips only. Grain: one float32 plate `(H+64, W+64)`, a random offset per frame, weight
  `clip(Y/24,0,1)*clip((255-Y)/80,0,1)`, int16 add clipped both ways, strength 2.0. `Grade.__call__` is unchanged.
- `"render": {"resample": "cubic", "fades": "round"}`: the label crop folded into the camera matrix (one
  `INTER_CUBIC` warp); `cv2.convertScaleAbs` for dips and fades.
- `"render": {"upload": "1440"}`: chunks encoded once (`scale=2560:1440:flags=lanczos`, `veryfast`, CRF 16,
  `aq-mode=3:bframes=2`, `-g FPS//2`); the 1080p copy is made from it. Always `-b:a 384k`.
- `"render": {"fps": 25}`: `main()` sets `FPS` in `render_v3` and `render_video` before the pool forks, scales
  `TD` and the fade and logo frame counts by `FPS/30`, and recomputes `f0`/`f1` from `t0`/`t1`. New
  `--clips-dir` overrides `P["clips_dir"]`. `fetch_proxies.py --fps 25` writes to `clips25/` (`fps=25`, or
  `framerate=fps=25` for 30/60 fps sources). The one-off `decimate=cycle=6` library conversion is documented, not run.
- `voice_post.sh`: 5th argument `legacy` (default) or `phone` (the 05 P1-d chain).
- Style guide: a "v3.1 options (on trial)" section.

**Test:** copy 08's `edit.json` and `cutlist.json` to the scratchpad, add keys, and run `render_v3.py …
--range 0,30` and `--range 640,675` with and without them. For 25 fps, convert only the clips of 0-30 s. Voice:
run the `phone` chain on `work/08-scariest-places/voice/narration_raw.wav` into the scratchpad.
**Accept:**
- No keys: `--range 20,30` gives the same `framemd5` as `main`.
- `opening_pace`: no opening clip scene over 4.0 s. `end_tail`: 12 s longer, no text in the tail.
- `finish v2`: the vignette is static on a `roll` shot and pure black stays 0.
- 25 fps: no duplicate every 6th frame on an ESO clip.
- `phone`: 80-250 Hz at most +10 dB over 1-4 kHz, the same length to the sample, -16 LUFS.

### WP4 · Shorts renderer (1.5 days)
**Goal:** no dead tail, the claim on frame 0, text inside the safe zone, a CTA that says where to go.
**Files:** `scripts/video/render_short_v2.py`, new `scripts/video/short_lint.py`, `.claude/skills/science-shorts/SKILL.md`.
**Spec (`short.json` keys; today's behaviour is the default unless stated):**
- `speed` default 1.2 → 1.1; fix the docstring.
- `"end_hold": 2.4` (recommended 0.7). `"loop": true` moves the bell to `cta0`.
- `"hook_number": true`: a number card in the first section counts from 0.0 and lands on its word; no caption before it lands.
- `"hook_cut": true`: when item 0 is longer than 1.8 s, a real cut to the next item's clip at ≤ 1.5 s replaces
  the same-shot jump zoom.
- `"safe_zone": true`: captions at (492, 1170) with `fit(lay, 780)`; title at y 330, x 500, `fit(box, 860)`;
  number cards and headlines x 500, `fit(…, 860)`; end-card arrow at (300, 1330).
- `"cta_sub": "DARK FLOW · CHAPTER 8"`: a silver line above `WATCH THE FULL VIDEO`.
- `"key_scale": 1.2` with `"key_words"`: those captions and numbers drawn larger, still gold and one word. Default 1.0.
- `short_lint.py <short dir> [--max-words 130]`: word count and predicted length (3.0 words/s at 1.1x); the number
  or claim in the first 8 words, no comma in the first 3, no date first; a leftover `[SUSPENSE]`; `speed` missing.
  Warnings only.
- Skill: looping endings, the chapter timestamp in the description, 6-8 Shorts per video inside 72 h of the full
  video, engaged views recorded after 7 days. Script rewrites are proposals for the owner.

**Test:** re-render `hunter` from its existing voice into the scratchpad, with the cached clips of
`work/08-shorts/out/vclips9x16` linked there so nothing is fetched: once with no new keys, once with all.
**Accept:** no keys → 43.0 s and the same layout; all keys → tail ≤ 2.2 s after `cta0`, a number on frame 0, a
new picture by 1.5 s, every text box inside x 48-888 and y 288-1248, voice still 1.1x.

### WP5 · Packaging and measurement (2 days)
**Goal:** retention and reach per video on file, and three title and thumbnail drafts when the owner asks.
**Files:** `scripts/youtube/upload_youtube.py`, new `scripts/youtube/analytics.py`, `make_thumbnail.py` and
`package_lint.py`, `.claude/skills/science-publish/SKILL.md`.
**Spec:**
- `upload_youtube.py`: `auth-url --analytics` adds `yt-analytics.readonly`. `upload --privacy` default `public` →
  `private` (the owner's rule; the one default we change). `parse_package` accepts an optional `**Titles (A/B)**` block.
- `analytics.py retention <video_id> <production dir>`: the 100-point `audienceWatchRatio` curve joined to
  `cutlist.json` → `retention.md` (Intro % at 30 s, the 5 steepest drops with the line spoken and the shot,
  spikes, `relativeRetentionPerformance`). `analytics.py summary`: views, average view duration and traffic sources →
  `stats.md`; impressions and CTR are typed in from Studio for now. `--from-json` runs offline. Credentials come
  from `upload_youtube.env()` and are never printed.
- `package_lint.py <youtube.md>`: title ≤ 60 characters, hook in the first 45; description line 1 differs from the
  title; ≤ 12 tags; credits present. Warnings only.
- `make_thumbnail.py <production dir> --out <dir>`: as in 03 P1-a (cutlist shots only, CLIP ranking, contact
  sheet, Anton text in the left 62%, lints for size, contrast, word overlap and 2 MB, a mobile preview grid). No
  pipeline stage calls it.

**Test:** `analytics.py --from-json` on a synthetic curve with 08's cutlist; `package_lint.py` on the 04, 05 and 08
packages; `make_thumbnail.py` on 08 into the scratchpad from the proxies; `auth-url` with and without the flag
using dummy values.
**Accept:** `retention.md` names the line at each planted drop; three 1280x720 JPEGs under 2 MB pass the lints;
no network call and no credential in any output.

### WP6 · Portraits of the people named (0.5-1 day)
**Goal:** the owner's "photos of every person named" rule, without Wikimedia.
**Files:** `scripts/video/fetch_assets.py`, `.claude/skills/science-footage/SKILL.md`.
**Spec:** `fetch_assets.py portrait "<name>" [--out dir] [--dry-run]` asks, in order, the NASA Image Library,
Library of Congress ("No known restrictions" only), the ESO archive and Internet Archive (licence PD or CC), and
writes licence, author and source into `credits.json`. It never requests a Wikimedia or Flickr host, and stops
on a 429 from any host.
**Test:** `--dry-run` for Kailash Sahu, Chryssa Kouveliotou and Maarten Schmidt; one download into the scratchpad.
**Accept:** every result carries a licence and credit; the request log shows no Wikimedia or Flickr host.

## 4. For the owner to decide

Until he answers, each item is off and existing productions render as before.

1. **Thumbnails.** Your rule is "no thumbnail unless asked". Should each video get three drafts for you to use,
   edit or replace before it goes public? *Meanwhile: the tool exists and is never run.*
2. **Titles.** Three per video for YouTube's A/B test (the proven keyword, one with a number, one in Hinglish),
   and "(Hindi)" in place of "| Hindi Documentary" when space is tight? *Meanwhile: one title, your format.*
3. **25 fps.** It removes a visible stutter; the library is converted once (about 15 min). Trial on one video? *Meanwhile: 30 fps.*
4. **Script rules for the next video:** a first sentence of ≤ 12 words with no "lagbhag", 2-3 specific teasers in
   the opening, a short line every 4-6 sentences, a named person per chapter, an ending under 45 s. *Meanwhile:
   the checker only advises.*
5. **Shorts length:** 30-35 s and about 100 words, not 35-60 s? *Meanwhile: your budget.*
6. **Shorts ending and layout:** a 0.7 s end card that loops, and captions moved out of the button area.
   *Meanwhile: unchanged; you get a side-by-side of `hunter`.*
7. **Shorts scripts:** the three rewritten 08 hooks (02 P1-3), darkflow answering part of its question, and 6-8
   Shorts per video. New recordings cost ElevenLabs characters; we quote first.
8. **End-screen tail:** 12 s of music and footage after the last word.
9. **Phone voice chain:** a 30 s A/B from 08's existing recording, no credits spent.
10. **Analytics sign-in:** one more Google sign-in with a read-only permission.
11. **Credits by link,** with the poll as the only pinned comment. Where should the credits page live?
12. **Targets:** SFX 8-15 a minute in the style guide, and 30 s with nothing on screen treated as an error?
13. **Upload time 18:00 IST,** and a third-person story bridge to the next video as the last line?

## 5. What we deliberately do not do

- **No intro, title card, recap, spoken CTA, suspense stop or designed pause.** The end tail is footage after the story ends.
- **No change to recorded narration and no ElevenLabs spend.** Script findings apply to the next script.
- **No re-cut or re-upload of 08, no public upload, no change to any existing package.**
- **No hard failures from the new lints by default.** A pattern must show on two videos before it blocks anything.
- **No 60 fps, 4K master, sharpening, stronger teal-orange, sidechain ducking or reverb** (05 §3).
- **No 1440p proxies, photo parallax or sub-pixel star drift yet:** low return until the rest is judged.
- **No Shorts-style punches in long-form, no trending audio, no change to the gold one-word captions or 1.1x voice.**
- **No new paid service or API key, and no vendor benchmark as a target.**
- **No route around Wikimedia or Flickr 429s; no press, Nobel or AIP photos; no generated likenesses.**
- **No Hindi `localizations` or Reporting-API job yet:** thin evidence; revisit after three public videos.
