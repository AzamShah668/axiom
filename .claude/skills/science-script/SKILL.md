---
name: science-script
description: Research a space/science topic and write the story script for the Hindi documentary channel - a third-person narrated countdown ("10 facts...") with cold open, fact-check table, English packaging, and the Devanagari TTS file. Use for stage 1 of science-video or when a script needs rewriting.
---

# Science script (stage 1)

Model: Science Time (@ScienceTime24). See `docs/research/science-time/` for the reverse-engineered method.
Production 01 (`productions/01-dark-matter/script.md`) is the reference example.

## Steps
1. **Topic and angle.** Use a "10 Facts You Don't Know About <Topic>" countdown or a single big question.
   Title: `<Topic hook> | Hindi Documentary`.
2. **Research.** Use current sources: NASA, ESA, ESO, papers and news. Every number and date goes into a
   fact-check table in `script.md` with its source. Prefer facts that come with a person, a place and a year,
   so the story has characters.
3. **Structure:**
   - Cold open (~45-60 s): a scene in a year, a person, a mystery, and a hook pointing to the newest result.
   - Facts #10 -> #1, each 45-110 s. Build from history to the most mind-bending or newest fact.
   - The closing lines return to the opening mystery.
4. **Write `script.md`** in Hinglish for review, with one `## <section_id>` per section (`cold_open`, `fact10` ...
   `fact1`). Also include:
   - chapter card titles (`FACT #n` + a short English line)
   - the package: title, three-line thumbnail text, description, tags
5. **Write `tts/narration.hi.md`:**
   - Same sections, in Devanagari.
   - English names and science terms stay in Latin letters (Coma Cluster, dark matter, Hubble).
   - Numbers are written as Hindi words (उन्नीस सौ तैंतीस, पचासी percent).
   - "..." marks dramatic pauses.
   - Section headers must match `script.md`; every later stage keys on them.

## Style rules (hard)
- **Third person only, a story being told:**
  - no "aap/aapko"
  - no commands (dekhiye, sochiye, imagine kijiye)
  - no questions to the viewer
  - no "aaj hum jaanenge" and no "number 10..."
  - no like/subscribe
- Questions only belong to characters ("sabse bada sawaal wahin khada hai...").
- No India-specific comparisons or examples; the channel is about the universe.
- Calm, awe-filled documentary tone. Short sentences: every sentence becomes one caption and one visual beat.
- English words a Hindi viewer knows (galaxy, gravity, telescope) stay English, which suits Neel's accent.

## Check before handing over
- Read the Devanagari aloud mentally: no Latin-script Hindi words, no digits, no symbols ElevenLabs reads oddly (×, %, ~).
- Numbers in captions and cards come from the fact-check table.
- Commit `script.md` and `tts/narration.hi.md`.
