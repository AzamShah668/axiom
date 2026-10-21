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
- **Simple, spoken Hindi (owner's rule, 2026-10-21).** Write the way people talk, not the way a textbook reads.
  Every line is heard only once, so a viewer has to understand it on first hearing.
  - Avoid formal, Sanskritised or literary Urdu words, for example कण (particle), घनत्व (density), तत्व
    (elements), चरम (peak), नियमित (regular), सटीक (precise), शक्तिशाली (powerful), वायुमंडल (atmosphere),
    साम्राज्य (empire), माद्दा (matter), केंद्र (centre), घातक (deadly), हैरत-अंगेज़ (amazing).
  - Use the everyday word (घने, ताक़तवर, सबसे तेज़, बीच में, ख़तरनाक, कमाल का), or the English word that Hindi
    viewers already use (particle, elements, atmosphere, density).
  - Test: if a 15-year-old wouldn't get the line on first hearing, simplify it.
- **Lines must agree with each other.** For example, a fact must not say "this story began with…" when the cold
  open already began the story somewhere else.

## Voice
- **Locked voice:** ElevenLabs library voice **Neel – Paranormal Story Narrator** (Hindi), model `eleven_multilingual_v2`, stability 0.5, similarity 0.75, style 0, speed 1.0. See `voice-preset.json`.
- Narration source for TTS: `productions/<NN-topic>/tts/narration.hi.md` (Devanagari, one `## <section>` per chapter).
  - English names and science words stay in English letters.
  - Numbers are written as Hindi words.
- Render: `python scripts/elevenlabs/render_narration.py <narration.hi.md> <out_dir>`. This produces the narration, the timeline and per-character timings.

## Edit method
Since production 03: the **v3 style**, `docs/style-guide.md`. It was measured against Curious Space and
production 02 (`docs/research/curious-space/`), and its changes were approved by the owner on 2026-10-20:
- a hook before the cold open
- key phrases plus a CC track instead of a running subtitle
- an audible music bed with designed pauses
- a logo bug

Productions 01-02 used the Science Time method (`docs/research/science-time/01-how-big-is-the-universe.md`).

Rules that still hold (from the owner's reviews of v1 and v2; enforced by the pipeline):
- **4K, moving, relevant, never repeated footage.**
  - Every shot comes from a 4K source (ESO, ESA/Hubble, ESA/Webb, NASA SVS) and is continuously moving.
  - It is matched to the sentence being spoken.
  - No shot (or near-identical copy) appears twice in a video, and shots used by earlier productions are avoided.
  - No static photos. Stills only appear inside explanatory graphics, always moving.
- **Pace that follows the voice.** A visual beat per sentence, cut into scenes of about 3 s, each a different
  shot. Cuts sit in pauses or on word starts. (v2: every ~2.5 s.)
- **What is said is readable in English.**
  - v3: every sentence is in the English CC track; key phrases, names, years and numbers are on screen as
    kinetic text and number cards.
  - v2: one caption per sentence.
- **Transitions with meaning.** Hard cut by default, dip to black at idea breaks, warm flare on reveals.
- **Sound.**
  - Kevin MacLeod music (CC BY 4.0, credited), 16 LU under the voice and steady.
  - 3-5 designed moments.
  - Synthesised, licence-clean SFX.
  - Never another channel's music, footage or graphics.
- **No text in footage.** OCR finds burned-in text. Corner labels are cropped out automatically; any other part with text is never used.

## Workflow
The whole process is the `science-video` skill (`.claude/skills/science-video/SKILL.md`), with one sub-skill
per stage, and `scripts/science/pipeline.sh` for the scripted stages:
`narration -> edit -> footage -> assign -> render -> review -> preview -> credits`.
Production folder contents:
- `script.md`, `tts/narration.hi.md` (sections `hook`, `cold_open`, `fact10` … `fact1`)
- `edit.spec` + `edit.base.json` -> `edit.json`
- `footage/terms.txt`
- `cutlist.json` (the shots used), `captions.en.srt` (v3 CC track)
- `youtube.md`, `credits.txt`
