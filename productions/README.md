# Productions: channel rules (apply to every video)

## Packaging
- Title format: `<Topic> | Hindi Documentary`
- **Everything written is in English**: the title, thumbnail, on-screen text, chapter cards, description and tags.
- **Only the narration is Hindi**, voiced with ElevenLabs.
  - Scripts are written in Hinglish (Hindi in English letters) for review.
  - They are converted to Devanagari only for the TTS input, because ElevenLabs pronounces Hindi better that way. Viewers never see either version.

## Narration style
- **Pure storytelling, third person.** The narrator tells a story and never talks to the audience.
- **Never:**
  - "aap" / "aapko" / "aapke"
  - commands such as "dekhiye", "sochiye", "sochiye zara", "imagine kijiye"
  - "aaj hum jaanenge…", "kya aap jaante hain…"
  - questions aimed at the viewer
  - "number 10…"-style list announcements
  - subscribe or like requests
- Questions only appear inside the story, belonging to the people in it ("Zwicky ke saamne sawaal tha…", "sabse bada sawaal wahin khada hai…").
- **Subjects are the characters of the story:** scientists, Earth, the galaxy, insaan / insaaniyat. Avoid "hum/hamara" as a way of addressing the viewer.
- The narration runs as one continuous story with a cold open. List and countdown structure lives **only on screen** (chapter cards); the voice flows from one fact into the next.
- Calm, awe-filled documentary tone with steady pacing and no hype.

## Voice
- **Locked voice:** ElevenLabs library voice **Neel – Paranormal Story Narrator** (Hindi), model `eleven_multilingual_v2`, stability 0.5, similarity 0.75, style 0, speed 1.0. See `voice-preset.json`.
- Narration source for TTS: `productions/<NN-topic>/tts/narration.hi.md` (Devanagari, one `## <section>` per chapter).
  - English names and science words stay in English letters.
  - Numbers are written as Hindi words.
- Render: `python scripts/elevenlabs/render_narration.py <narration.hi.md> <out_dir>`. This produces the narration, the timeline and per-character timings.

## Edit method
The Science Time method: see `docs/research/science-time/01-how-big-is-the-universe.md`.
