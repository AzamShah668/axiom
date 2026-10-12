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

Fast-cut rules (from the owner's reviews of v1 and v2; enforced by the pipeline):
- **4K, moving, relevant, never repeated footage.**
  - Every shot comes from a 4K source (ESO, ESA/Hubble, ESA/Webb, NASA SVS) and is continuously moving.
  - It is matched to the sentence being spoken.
  - No shot (or near-identical copy) appears twice in a video, and shots used by earlier productions are avoided.
  - No static photos. Stills only appear inside explanatory graphics, always moving.
- **New shot every ~2.5 s.** A visual beat per sentence, cut into ~2.5 s scenes, each scene a different shot.
- **What is said is on screen.** One English caption per sentence (lower third). Key names and numbers get a big centred caption.
- **Transitions.** Crossfade between scenes; zoom, flash, whip or blur on topic changes, each with a whoosh.
- **Sound.** Dark-ambient music bed (Kevin MacLeod, CC BY 4.0) ducked about 22 dB under the voice and rising in pauses, a low drone, whooshes, and booms on big moments.
- **No text in footage.** OCR finds burned-in text. Corner labels are cropped out automatically; any other part with text is never used.

## Workflow
The whole process is the `science-video` skill (`.claude/skills/science-video/SKILL.md`), with one sub-skill
per stage, and `scripts/science/pipeline.sh` for the scripted stages:
`narration -> edit -> footage -> assign -> render -> review -> preview -> credits`.
Production folder contents:
- `script.md`, `tts/narration.hi.md`
- `edit.spec` + `edit.base.json` -> `edit.json`
- `footage/terms.txt`
- `cutlist.json` (the shots used)
- `youtube.md`, `credits.txt`
