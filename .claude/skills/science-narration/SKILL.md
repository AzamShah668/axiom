---
name: science-narration
description: Render the Hindi voice-over for a science-channel production with the locked ElevenLabs voice (Neel), producing narration.wav and a character-level timeline used to sync captions and cuts. Use for stage 2 of science-video or when narration needs re-rendering.
---

# Narration (stage 2)

```bash
scripts/science/pipeline.sh productions/NN-slug narration
# = python scripts/elevenlabs/render_narration.py productions/NN-slug/tts/narration.hi.md $WORK/voice \
#     --open-gap 6.4 --gap 0.8 --max-pause 0.4      (no pauses: owner, 2026-10-27; NARRATION_FLAGS overrides)
# real recordings: [bite:<name>] markers + productions/NN-slug/bites.json (see render_narration.py's docstring).
# The voice stops at a marker, the recording is levelled to the voice before it and mixed in, and
# timeline.json "bites" + a "#<name>" pseudo-word mark where it plays. Re-joining costs no ElevenLabs credits.
```

## How it works
- Each `## section` is rendered by ElevenLabs `/with-timestamps` (model `eleven_multilingual_v2`).
  - The voice is "Neel - Paranormal Story Narrator", fixed in `productions/voice-preset.json`.
  - Neighbouring text is sent as context so the joins flow.
  - A production can carry its own `productions/<name>/voice-preset.json`; render_narration.py and tts_check.py
    use it over the channel's (Rome: Neel Story Narrator on eleven_v3, owner 2026-10-30).
  - **eleven_v3 records long takes, never one request per section** (owner, 2026-10-30: per-scene v3 requests
    "sound like a different voice" at every join, because v3 refuses the neighbouring text). render_narration.py
    does it by itself for a v3 preset: consecutive sections go in one request of up to 4,400 characters (v3's limit
    is 5,000), then the take is cut into `<id>.mp3` + `<id>.align.json` between the sections' words.
- Sections are cached as `<id>.mp3` + `<id>.align.json`. To re-render one, delete its mp3 and run again.
- The sections are joined with gaps that leave room for the cards:
  - 1.2 s after the hook (`HOOK_GAP`)
  - 3.5 s after the cold open (title card + first chapter card; `--title-after`)
  - 2.0 s between facts

  The designed breaths of the v3 style are not rendered here. The edit's `M` lines splice them in at render
  time. Then the documentary finish is applied (`scripts/elevenlabs/voice_post.sh`: EQ, de-ess,
  compression, -16 LUFS).
- `timeline.json` = `{total, sections: [{id, start, end, chars, char_start}]}`. Caption and cut triggers are
  looked up in `chars`, so the edit stays in sync with the voice to the character.

## Requirements
- `ELEVENLABS_API_KEY` in `config/.env` (gitignored). Never print or commit it.
- A full 10-fact script is ~9,000 characters. Check the plan's quota with `python scripts/elevenlabs/el.py whoami`.
- The voice comes from the shared library. If the account doesn't have it yet, add it once:
  `/v1/voices/add/{owner}/{voice_id}`.

## QC
- **ElevenLabs always gets Devanagari** (owner, 2026-10-29). With the locked model (eleven_multilingual_v2) a
  Roman-letter Hinglish script is half-read as English ("butchering the words"); the same lines in Devanagari were
  "exactly what I want". The owner still writes and approves the script in Hinglish (`script.txt`); the narration
  file is its word-for-word Devanagari copy (English words in Latin letters, numbers as Hindi words, "Voyager
  One"). Tried and not chosen: eleven_v3 / eleven_v4 with `language_code: "hi"` read Roman Hinglish well, but the
  owner prefers the old model's sound (v3 also refuses previous/next text). tts_check.py refuses Roman narration
  for this model.
- **ElevenLabs credits are precious** (owner, 2026-10-30): before any request that costs characters, a test
  included, tell the owner what it costs and what is left, and record only once they say so. Never play with
  them; joining, cutting or re-finishing recordings that exist costs nothing.
- **Before the first character is paid for** (owner, 2026-10-27): `tts_check.py` must print 0 problems (the
  narration stage refuses to record otherwise) and `pipeline.sh … probe` must have heard every new name; see
  science-script-v2 §7. After recording, `speech_check.py` (run by the stage) flags names not heard and extra
  नहीं; every finding goes into `productions/tts-lexicon.json`.
- Listen to the start, one join, and the end. Check pronunciation of names and numbers. Fix the Devanagari
  spelling and re-render only that section.
- Total length is usually 11-13 min for 10 facts.
- Narration audio is not committed.
