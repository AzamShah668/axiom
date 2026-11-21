---
name: youtube-shorts-scriptwriter
description: Write, rewrite, humanize and fact-check YouTube Shorts ("shots") scripts for the Hindi science channel in natural spoken Hinglish, then make the Devanagari voice text for ElevenLabs after the owner approves. Use whenever the owner asks to create, write, improve, fix or review a Short script, or gives feedback on one. A living skill - every fixed mistake is added to the Lessons log so it never happens again.
---

# YouTube Shorts scriptwriter (living skill)

The owner writes or approves every Short script. This skill drafts, fixes and checks; it never records voice without the owner's OK on the exact character cost.
**After every Short session, add each new mistake or preference to the Lessons log below and commit it.**

## 1. Shape (25-45 s at 1.1x, about 80-120 words)
- **Hook (first 1.5 s):** the boldest, strangest concrete claim or number. No hedge word ("shayad"), no date, no filler, no comma in the first 3 words. "Socho, ..." openings also work (owner's 09 Shorts).
- **Setup:** who found what, with only the details the viewer needs now. Cut technical clutter (observatory peak names, fibre counts, catalogue codes) before the viewer is hooked.
- **Twist:** flow straight into the turn, no suspense pause.
- **Open end + CTA in one spoken line:** leave the biggest question open and tie it to the full video, e.g. "Phir uske baad kya hoga, poori kahani niche linked video mein hai." The open question must be answered in the full video.

## 2. Sound human
- Science words in English (universe, galaxy, dark energy, data, model, equations); story, emotion and connectors in everyday spoken Hindi.
- Connect sentences with spoken connectors (ki, jiske, matlab, lekin, aur) so it is one continuous thought; zero flow cuts.
- Every sentence under 25 words (best 12-20). If a connector such as "ki" pushes a sentence past 25, split the clause before it.
- No colons, ellipses, dashes or brackets in narration: AI voices read them as robotic pauses.

## 3. Bold but true (accuracy guard)
- A bold hook is allowed only if the next lines attribute it ("Unke hisaab se...", "Ek model mein..."). Never state a hint or one team's model as settled fact without that attribution inside the Short.
- Check every number against the latest source before giving the script (counts, ages, dates). Prefer a rounded true number ("ek crore se zyada") over a vague wrong one ("lakhon").
- Hints stay hints in the body ("ek ishaara mila"): the hook carries the punch, the body carries the honesty.

## 4. Output format
1. If rewriting a draft: a short list of what changed and why (facts, flow, grammar).
2. The clean Hinglish script, one sentence per line, plain text.
3. Word count, estimated length at 1.1x, an English title under 100 characters ending in `#shorts`.
4. Wait for approval.

## 5. Devanagari voice text (only after approval)
- Hindi words and Indian/foreign names in Devanagari (हेनरी टाय, एरिज़ोना); English science words in English letters.
- Numbers as Hindi words (तैंतीस, तेरह पॉइंट आठ); acronyms phonetically (डेज़ी, नासा); "3D" as "three D".
- Only commas and the full stop "।". Save to `work/<prod>/shorts_test/<name>/tts/narration.hi.md` and report the exact character count, then wait for the owner's OK before any ElevenLabs request.
- Voice: Rudra (`vIdhHAZdn1bGjKe1dFw8`), `eleven_multilingual_v2`, stability 0.35, style 0.45 (`productions/voice-preset.json`); played at 1.1x in the Short.

## 6. After the voice
Render with `scripts/video/short_web3d.py` (one web3d scene per Short, `--stills` check first): motion graphics only, PLAIN text, photos whole and never under text, one word caption, Darkest Child low, kz hits. Package in `productions/<prod>/shorts/<name>.md`. Upload private; the owner posts.

## Lessons log (do not repeat)
- 2026-11-21 (halfway, with Gemini): "shayad" in the hook made it weak; cut it.
- 2026-11-21: "Kitt Peak" and "paanch hazaar optical fibres" slowed the opening; keep just DESI and the 3D map.
- 2026-11-21: colon before the reveal ("ishaara mila: ...") broke the flow; "ek ishaara mila ki ..." sounds human. Keep that sentence under 25 words by ending the previous one at "banaya".
- 2026-11-21: clipped CTA "Poori kahani, poori video mein." sounds robotic; use one natural sentence pointing to the linked video.
- 2026-11-21: "lakhon galaxies" undersold DESI (more than 14 million galaxies and quasars, DR2 2025): say "ek crore se zyada".
- 2026-11-21: a bold hook ("Universe apni aadhi zindagi jee chuka hai") must be attributed in the body ("Unke hisaab se ...") because it is one model on a hint.
- Voice traps: avoid "waqt" (say "time"), "naye/nayi" (Rudra reads it like "nahi"), heavy textbook Hindi.
