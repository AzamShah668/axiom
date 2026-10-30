# Where things stand (read this first in a new chat)

Last updated 2026-10-30. Update this file and commit it at the end of every chat.

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
| 05 Voyager 1 | narration recorded 2026-10-29 (12:45, Devanagari to the old model; real voices: Suzanne Dodd 2019 NASA, the JPL team's 2024 reaction), all chapters speech-checked | owner listens; then the edit plan (photos, own graphics, 10-20 archive clips: 1977 launches, JPL rooms, Golden Record, flyby images, Pale Blue Dot, DSN), render, previews; publish by 18 Nov 2026 |
| Rome history (the owner's other channel, a one-off) | the owner's 90-scene Hinglish script checked and fixed (`productions/rome-history/fixes.md`), Devanagari copy in `tts/narration.hi.md`. Voice locked: Neel Story Narrator `q4KoKwFyTWQ0Fvvsl9LW` on **eleven_v3** (`productions/rome-history/voice-preset.json`); never "Neel Ancient Storyteller" `PnaKthDVqB7PvUN6iU48`. Two takes rejected: the first on multilingual_v2 by mistake, the second on v3 one request per scene (the voice changed at every join) | after the credits reset on 2026-11-01, with the owner's OK (about 21,800 characters): `work/venv/bin/python scripts/elevenlabs/render_narration.py productions/rome-history/tts/narration.hi.md work/rome-history/voice --open-gap 0.4 --gap 0.4 --max-pause 0.4` (v3 now records 6 long takes by itself); send narration.mp3 and a per-scene start/end table from timeline.json |

## Open decisions for the owner
- Captions: upload the English CC track or not (pending since video 03).
- Missing photos for 04 (Lemaître, Penrose, Hoyle, Hartle, Wilson, Solvay 1927, Holmdel antenna, Mount Wilson,
  LiteBIRD) are covered by footage in the final; they only matter if the owner wants them added.

## On trial (in main since 2026-10-30 with everything else; the owner decides after video 05)
- Script rule "context before concept" (science-script-v2 §2c).

## Accounts and budget
- YouTube signed in again 2026-10-30 (Science Guy); it expires after 7 days (re-sign-in: `upload_youtube.py auth-url`, then `exchange`). The Google app is in
  Testing mode, so its sign-ins expire after 7 days; publishing the consent screen stops that.
- ElevenLabs: 8,746 characters left on 2026-10-30; 131,000 a period, next reset 2026-11-01.
- All work up to 2026-10-30 (Voyager, Devanagari narration, Rome, per-production presets, v3 takes) merged into
  `main` on 2026-10-30. Earlier, all work of 2026-10-20 to 10-29 was merged into `main` on 2026-10-29 (https://github.com/AzamShah668/axiom/pull/3).
