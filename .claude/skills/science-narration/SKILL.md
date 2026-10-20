---
name: science-narration
description: Render the Hindi voice-over for a science-channel production with the locked ElevenLabs voice (Neel), producing narration.wav and a character-level timeline used to sync captions and cuts. Use for stage 2 of science-video or when narration needs re-rendering.
---

# Narration (stage 2)

```bash
scripts/science/pipeline.sh productions/NN-slug narration
# = python scripts/elevenlabs/render_narration.py productions/NN-slug/tts/narration.hi.md $WORK/voice --open-gap 3.5 --gap 2.0 \
#     --gap-after hook=1.2
```

## How it works
- Each `## section` is rendered by ElevenLabs `/with-timestamps` (model `eleven_multilingual_v2`).
  - The voice is "Neel - Paranormal Story Narrator", fixed in `productions/voice-preset.json`.
  - Neighbouring text is sent as context so the joins flow.
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
- Listen to the start, one join, and the end. Check pronunciation of names and numbers. Fix the Devanagari
  spelling and re-render only that section.
- Total length is usually 11-13 min for 10 facts.
- Narration audio is not committed.
