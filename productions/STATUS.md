# Where things stand (read this first in a new chat)

Last updated 2026-10-31. Update this file and commit it at the end of every chat.

## How we work across chats
- One chat per job: a script, a recording, an edit and render, Shorts, an upload. Long chats fill up; a new chat
  costs nothing because everything that matters lives in the repo, not in the chat.
- Open a new chat with one line, for example: "Read productions/STATUS.md, then write the script for video 05."
- The rules live in: `CLAUDE.md` → `.claude/skills/science-video/SKILL.md` (and the other science-* skills),
  `productions/README.md` (channel rules, the standard from video 05), `productions/tts-lexicon.json`
  (pronunciation fixes; tts_check.py, probe_words.py and speech_check.py use it).
- **ElevenLabs credits are precious** (owner, 2026-10-30): before any request that costs characters, tests
  included, say what it costs and what is left, and record only when the owner says so.
- Keys come from the environment's variables (`ELEVENLABS_API_KEY`, `DRIVE_REFRESH_TOKEN`, `YT_CLIENT_ID`,
  `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`) or the gitignored `config/.env`. Never print or commit them.
- Big files are on Google Drive (cnnvgvc@gmail.com): `videos/` (masters), `footage-library/` (all clips,
  including the NASA archive clips), `productions/<name>/` (work folders), `media/`. A new container gets them back
  with `scripts/science/pipeline.sh productions/<name> restore`.

## Videos
| Video | State | Next step |
|---|---|---|
| 03 Neutron Stars | on YouTube, **private** (https://youtu.be/fv9M4nmAEeM) | publish when the owner says (command in `productions/03-neutron-stars/youtube.md`) |
| 03 gold Short | on YouTube, **private** (https://youtu.be/cAm16FD1b44), uploaded 2026-10-30 | publish when the owner says |
| 03 teaspoon Short | to be remade | when the owner asks |
| 04 Before the Big Bang | **final = the 04-x version** (owner accepted 2026-10-27): no pauses, real NASA footage, photos, channel intro. On Drive: `videos/04 - What Was There Before the Big Bang? (Hindi Documentary) 1080p - FINAL (real footage, no pauses).mp4` | fill the two `AUTHOR_TBD` photo credits (Alan Guth, Arno Penzias; Wikimedia was rate-limiting), then upload private when the owner says: `productions/04-before-big-bang-x/youtube.md` |
| 05 Voyager 1 | **finished 2026-10-30**: master 12:48, 1080p30, -13.9 LUFS. Drive `videos/05 - Voyager 1 (Hindi Documentary) 1080p - master/`: `… 1080p - FINAL.mp4` (shared by link at the owner's request, 2026-10-31) and `… 1440p - FINAL for YouTube.mp4` (the upload copy). Work dir, render chunks and stems on Drive `productions/05-voyager` | **scheduled**: https://youtu.be/dhLf0_YjElc goes public 1 Nov 2026 12:00 IST. After 12:00 the owner posts and pins `credits_full.txt` (API token can't comment) and adds a thumbnail |
| 05 Shorts: fix, lightday | lightday **scheduled**: https://youtu.be/zvnLW2j18-E goes public 1 Nov 2026 13:00 IST. fix rendered (65.5 s), not uploaded. Packages `productions/05-voyager/shorts/{fix,lightday}.md` | owner sets Related video on lightday after 12:00 on 1 Nov; fix when the owner says |

## Open decisions for the owner
- Captions: upload the English CC track or not (pending since video 03).
- Missing photos for 04 (Lemaître, Penrose, Hoyle, Hartle, Wilson, Solvay 1927, Holmdel antenna, Mount Wilson,
  LiteBIRD) are covered by footage in the final; they only matter if the owner wants them added.

## On trial (in main since 2026-10-30 with everything else; the owner decides after video 05)
- Script rule "context before concept" (science-script-v2 §2c).

## Accounts and budget
- YouTube signed in again 2026-10-30 (Science Guy); it expires after 7 days (re-sign-in: `upload_youtube.py auth-url`, then `exchange`). The Google app is in
  Testing mode, so its sign-ins expire after 7 days; publishing the consent screen stops that.
- ElevenLabs: 8,376 characters left on 2026-10-31; 131,000 a period, reset 2026-11-01 (Shorts hooks need a few hundred each; ask the owner first).
- All work up to 2026-10-30 (Voyager, Devanagari narration, per-production voice presets, v3 long takes) merged into
  `main` on 2026-10-30. Earlier, all work of 2026-10-20 to 10-29 was merged into `main` on 2026-10-29 (https://github.com/AzamShah668/axiom/pull/3).
