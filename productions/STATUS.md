# Where things stand (read this first in a new chat)

Last updated 2026-10-29. Update this file and commit it at the end of every chat.

## How we work across chats
- One chat per job: a script, a recording, an edit and render, Shorts, an upload. Long chats fill up; a new chat
  costs nothing because everything that matters lives in the repo, not in the chat.
- Open a new chat with one line, for example: "Read productions/STATUS.md, then write the script for video 05."
- The rules live in: `CLAUDE.md` → `.claude/skills/science-video/SKILL.md` (and the other science-* skills),
  `productions/README.md` (channel rules, the standard from video 05), `productions/tts-lexicon.json`
  (pronunciation fixes; tts_check.py, probe_words.py and speech_check.py use it).
- Keys come from the environment's variables (`ELEVENLABS_API_KEY`, `DRIVE_REFRESH_TOKEN`, `YT_CLIENT_ID`,
  `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`) or the gitignored `config/.env`. Never print or commit them.
- Big files are on Google Drive (cnnvgvc@gmail.com): `videos/` (masters), `footage-library/` (all clips,
  including the NASA archive clips), `productions/<name>/` (work folders), `media/`. A new container gets them back
  with `scripts/science/pipeline.sh productions/<name> restore`.

## Videos
| Video | State | Next step |
|---|---|---|
| 03 Neutron Stars | on YouTube, **private** (https://youtu.be/fv9M4nmAEeM) | publish when the owner says (command in `productions/03-neutron-stars/youtube.md`) |
| 03 gold Short | done, on Drive (`videos/03 Short - One Flash From a Dead Star Made Gold.mp4`) | upload private when the owner says (`productions/03-neutron-stars/shorts/gold.md`) |
| 03 teaspoon Short | to be remade | when the owner asks |
| 04 Before the Big Bang | **final = the 04-x version** (owner accepted 2026-10-27): no pauses, real NASA footage, photos, channel intro. On Drive: `videos/04 - What Was There Before the Big Bang? (Hindi Documentary) 1080p - FINAL (real footage, no pauses).mp4` | fill the two `AUTHOR_TBD` photo credits (Alan Guth, Arno Penzias; Wikimedia was rate-limiting), then upload private when the owner says: `productions/04-before-big-bang-x/youtube.md` |
| 05 | not started | topic from YouTube view data (science-script-v2), in the standard from video 05: 10-20 real archive clips, real recordings of the people (`[bite:name]`, 2-3 sentences each), no pauses, right-first-time narration (tts_check → probe → record → speech_check) |

## Open decisions for the owner
- Captions: upload the English CC track or not (pending since video 03).
- Missing photos for 04 (Lemaître, Penrose, Hoyle, Hartle, Wilson, Solvay 1927, Holmdel antenna, Mount Wilson,
  LiteBIRD) are covered by footage in the final; they only matter if the owner wants them added.

## Accounts and budget
- ElevenLabs: about 38,300 of 131,000 characters left in the current period (2026-10-27).
- All work of 2026-10-20 to 10-29 is in pull request https://github.com/AzamShah668/axiom/pull/3 (branch
  `claude/determined-bell-frode3` → `main`). Once it is merged, every new chat sees it.
