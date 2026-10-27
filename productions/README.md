# Productions: channel rules (apply to every video)

## Packaging
- Title format: `<Topic> | Hindi Documentary`
- **Everything written is in English**: the title, on-screen text, chapter cards, description and tags.
- **No thumbnail.** The owner makes every thumbnail; never make one unless asked (owner's rule, 2026-10-21).
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
- Render: `python scripts/elevenlabs/render_narration.py <narration.hi.md> <out_dir> --open-gap 6.4 --gap 0.8 --max-pause 0.4`
  (`pipeline.sh … narration`). This produces the narration, the timeline and per-character timings.
- **Pace: full videos at 1.0x** (owner, 2026-10-26, after a 1.0x vs 1.2x sample of video 04). Shorts at 1.2x.

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
    Exception: real archive footage (below), which is often SD or HD.
  - It is matched to the sentence being spoken.
  - No shot (or near-identical copy) appears twice in a video, and shots used by earlier productions are avoided.
  - Stills only appear inside our own graphics, always moving (photos of people and things: `G photo:<stem>`).
- **Pace that follows the voice.** A visual beat per sentence, cut into scenes of about 3 s, each a different
  shot. Cuts sit in pauses or on word starts. (v2: every ~2.5 s.)
- **What is said is readable in English.**
  - v3: every sentence is in the English CC track; key phrases, names, years and numbers are on screen as
    kinetic text and number cards.
  - v2: one caption per sentence.
- **Transitions with meaning.** Hard cut by default, dip to black at idea breaks, warm flare on reveals.
- **Sound.**
  - Kevin MacLeod music (CC BY 4.0, credited), 16 LU under the voice and steady.
  - No designed pauses or suspense breaths from video 05 on (see below).
  - Synthesised, licence-clean SFX.
  - Never another channel's music, footage or graphics.
- **No text in footage.** OCR finds burned-in text. Corner labels are cropped out automatically; any other part with text is never used.
  Pinned shots (archive footage, recordings) are a deliberate choice and skip this check.

## Standard from video 05 (owner, 2026-10-27, after the 04-x experiment: "I accept all these changes")
- **No opening animation, no pauses.** The voice starts at 0.5 s. No `M` moments and no "..." suspense pauses.
  The narration stage joins with `--open-gap 6.4 --gap 0.8 --max-pause 0.4` (pipeline default).
- **Channel intro after the opening/hook** (edit.base.json `"channel"`), then the title card. Chapter cards carry
  a short title, no number. `"lead_in": 0.5`, no `"intro"`.
- **Show what is being said.** Photos of the people and things named, our own motion graphics for every idea
  that is explained, name cards (`L`) for people, missions and instruments, kinetic text and number cards.
- **Real archive footage on many occasions: 10-20 clips a video when they exist.** Launches, the actual
  instruments, labs, control rooms, discoveries as filmed, interviews of the people named. Research them with the
  script (stage 1), write the lines so they name what the footage shows, pin each clip to its line, and add a
  name card that says what it is and when ("archive footage").
- **Real recordings of the people.** When someone in the story was recorded, the narration introduces them
  ("…John Mather ने कहा था,") and their own voice plays: `[bite:<name>]` in narration.hi.md + `bites.json`
  (see `scripts/elevenlabs/render_narration.py`). The recording's own video plays in sync when there is one; a
  Hinglish subtitle and who/when are shown, and the English words go into the CC track.
- **Licences for archive material:** only public domain (NASA, other US government) or CC BY / CC BY-SA / CC0,
  each clip and recording credited by name in the description. Never a TV channel, news agency (BBC, AP,
  Reuters, British Pathé), film studio or another YouTuber, and never "fair use": a monetised upload gets Content ID
  claims. If a moment has no free clip, use a photo or one of our own graphics.
- **Where to look:** NASA SVS (svs.gsfc.nasa.gov: "From the Archives", interviews, launches), NASA Image and Video
  Library (images.nasa.gov: video and audio, launch broadcasts with .srt to find the exact moment), NASA JPL,
  Internet Archive items whose licence field says public domain or CC, Wikimedia Commons (slow from the
  container: it rate-limits shared IPs; never route around it). ESA's site blocks automated downloads.

## Shorts (owner's plan, 2026-10-22)
- **Every video gets as many Shorts as it can carry**: roughly one per fact plus the cold open, cut from the
  finished video (`shorts.spec`, pipeline stage `shorts`).
- **Shorts get their own script** (owner's rule, 2026-10-22, first used for the 02 "marble" Short): written
  for the Short and recorded fresh, not cut from the master narration. Four beats with time targets:
  1. **Hook (0-8 s):** the fact as a statement ("Agar poori Earth ko daba kar ek Black Hole bana diya jaaye, to
     uska size bas ek kanche jitna reh jaayega"), then a bridge that opens the story ("Lekin yeh hisaab sabse
     pehle kisi lab mein nahi, ek jung ke maidan mein nikla tha"). No "Kya aapko pata hai" needed.
  2. **Conflict & Discovery (8-24 s):** when, who, what happened, with one sensory detail ("shor aur mitti").
  3. **Core Concept (24-38 s):** the science in one idea and one number ("Hamare Suraj ke liye... 6 km").
  4. **Payoff (38-48 s):** the ironic or emotional end, landing on the name or term ("...The Black Hole").
  - Conversational Hinglish: English words where people say them (officer, calculate, exact solution, size,
    gate), simple spoken Hindi otherwise; "hamara Suraj", not "the Sun".
  - **Word budget:** Neel at 1.2x speaks about 2.9 words a second (Devanagari count), so a 48 s Short holds
    about 130 words. The first one ran 166 words, 64.5 s.
  - The owner writes or approves it in Hinglish; it is recorded from Devanagari (English words in Latin
    letters, numbers in Hindi words), one section per beat, pauses capped at 0.3 s.
- **The older form** (still used by the 03 teaspoon and 02 Maggi Shorts) is hook + body: the hook is a new spoken line in the same voice that asks the viewer, e.g.
  "क्या आपको पता है, कि neutron star का सिर्फ़ एक चम्मच…" (owner's exception to the no-addressing rule,
  Shorts hooks only, 2026-10-22). It plays over the fact's strongest shot and number card, and the number lands
  on its word. Then the fact's story follows in order, in the master's narration.
- **The hook moves from frame 0** (owner's rule, 2026-10-22): fast-moving footage (animations, flows, streams;
  never a still or a slow drift), a cut every 2-3 s, chosen with `hook_shots.py`. A spoken hook never waits:
  no pause inside it longer than 0.15 s (0.3 s between sentences); the key word follows straight on.
- **Pace: every Short plays at 1.2x, hook included** (owner's rule, 2026-10-22, raised from 1.1x; pitch kept). Length 35-60 s.
- **Layout:** 1080x1920 with the picture as a 1080x1080 square in the middle, black above and below. A title in
  the top bar says what the Short is about (English, one gold phrase). The bottom bar stays clear for YouTube's
  title and buttons.
- **Burned-in captions on every Short** (owner's rule, 2026-10-22): the spoken words in Roman letters (Hinglish),
  one word at a time (owner, 2026-10-22), in gold as it is spoken. No caption while other text is on
  screen (a name card, a date, a headline or number card already says it). `captions:` file per Short (`say_roman:` for a spoken hook).
- **The end card is written, never said:** `FULL VIDEO BELOW ↓` on screen.
- **Everyday comparisons are allowed in Shorts hooks and titles** (owner's exception, 2026-10-22), e.g. "Maggi
  की तरह" for spaghettification. The science term stays, and the full videos stay universal (no India-specific
  comparisons there).
- **The full video is linked with YouTube Studio's "Related video"** on each Short (links typed into a Short's
  description don't click). The full video must be public first.
- Uploads stay private until the owner says publish; the footage and music credits go in every Short's description.

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
