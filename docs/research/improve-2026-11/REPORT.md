# Improvement branch `claude/improve-2026-11`: what was done

Requested by the owner on 2026-11-16: research where the channel is lacking (retention, Shorts, packaging, script,
production quality), plan it with the strongest model, implement it on a separate branch, merge only if the owner
likes it.

## How it was made
1. **Research (5 Opus agents, in parallel):** `01-longform-retention.md`, `02-shorts.md`, `03-packaging.md`,
   `04-script.md`, `05-av-quality.md`. Each audited our real files (video 08, its Shorts, the renderers, the skills)
   and searched current sources (YouTube Help and Analytics docs, length/retention studies, thumbnail studies,
   top science channels).
2. **Plan (Fable 5.2):** `00-plan.md`: six work packages with no shared files, owner questions, do-not-do list.
3. **Implementation (6 Opus agents, one worktree each), merged here.** Everything is opt-in: with no new key or flag,
   existing productions render byte-identical (checked by md5/framemd5 on 08 and the hunter Short). Two defaults
   changed on purpose: Shorts speed default 1.2 -> 1.1, and `upload --privacy` default public -> private.

## What changed
| WP | Files | What it gives |
|---|---|---|
| 1 Script | `scripts/science/script_check.py`, science-script-v2 skill, `productions/outline.template.md` | Advice checks (`~`): hook, rhythm, turns, person, numbers, hedges, AI tells, re-hooks; `--voice`, `--strict`, `--selftest`. Proposed script rules marked "on trial". |
| 2 Edit lint | `scripts/video/pace_lint.py`, `music_energy.json`, `make_edit.py`, `pipeline.sh` | Dead zones (no text/graphic for 20-30 s), number-card variety, key-line and headline counts, a thin last third, music energy arc. Runs as warnings in the edit stage. |
| 3 Long-form render | `render_v3.py`, `grade.py`, `fetch_proxies.py`, `voice_post.sh`, style guide | Opt-in: `opening_pace`, `end_tail` (12 s end-screen tail), `music_arc`, `grade.finish: v2` (fixed vignette, fresh fine grain), `render.resample/fades/upload: 1440/fps: 25`, phone voice chain. |
| 4 Shorts render | `render_short_v2.py`, `short_lint.py`, science-shorts skill | Opt-in: `end_hold`+`loop` (tail 4.7 s -> 1.9 s), `hook_number` (number from frame 0), `hook_cut` (new shot by 1.2 s), `safe_zone` (text clear of the Shorts buttons), `cta_sub` (chapter on the end card), key words. |
| 5 Packaging | `scripts/youtube/{analytics,package_lint,make_thumbnail}.py`, `upload_youtube.py`, science-publish skill | Retention curve joined to the cutlist (which line/shot loses viewers), stats log, package lint, 3 thumbnail drafts for A/B, Titles (A/B) block, analytics sign-in scope (opt-in). |
| 6 Portraits | `scripts/video/fetch_assets.py portrait` | Free-licence photos of named people from NASA, Library of Congress, ESO, Internet Archive; never Wikimedia/Flickr. None found for 08's four scientists. |

## Lint findings on video 08 (examples of what the new checks catch)
- Opening: the title promise is first said at 25.8 s; 24-word hedged first sentence; "one of the most X" phrasing.
- Three 30 s+ stretches with nothing on screen (5:41, 6:58, 9:19); all 17 number cards are the same template;
  1 key line (target 15+); the last third has 19% of the overlays.
- Five slow drone tracks in a row from 5:07; no energetic cue in the second half.
- Shorts: 4.7 s end card with a silent tail; filler words on frame 0; text under the like/comment buttons.

## Owner decisions (everything stays off until answered)
See `00-plan.md` §3: thumbnails (drafts per video?), A/B titles, 25 fps trial, the new script rules, Shorts length
30-35 s, looping Shorts ending and safe-zone layout, end-screen tail, phone voice chain, analytics sign-in, credits
by link, SFX target, 18:00 IST upload time.
