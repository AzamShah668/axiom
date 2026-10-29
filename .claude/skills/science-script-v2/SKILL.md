---
name: science-script-v2
description: Write the script for a science-channel video the owner's improved way (from video 04, Oct 2026) - topic picked from real YouTube view data, one mystery told as a story with chapters and bridge lines, conversational Hinglish that flows when Neel reads it, accuracy-hedged physics, a checker for pauses/repeats/unspeakable words, and the owner's copy-paste review loop. Use when starting any new video script or rewriting one. (The older science-script skill is kept unchanged.)
---

# Science script v2 (stage 1, improved)

Everything in `science-script` still holds (research, fact-check table, Devanagari TTS file, third person, no
India-specific comparisons, simple spoken Hindi). This skill adds what the owner and two review rounds on video 04
taught us. Reference: `productions/04-before-big-bang/` (`script.txt`, `script.md`).

## 1. Pick the topic from data, not taste
Use the YouTube Data API with the channel token (`scripts/youtube/upload_youtube.py` env helpers; `search.list`
is 100 quota units, so stay under ~30 searches a day).
1. **Proven demand.** Pull the most-viewed videos of Science Time (`forHandle=ScienceTime24`), and run English
   searches on the topic family (`order=viewCount`, `videoDuration=long`).
2. **Hindi gap.** For each candidate, search the Hindi equivalent (`relevanceLanguage=hi`; Devanagari and
   Hinglish queries). A strong pick has a big English hit and no good Hindi long video. Shorts and kids' songs in
   the results don't count.
3. What has worked so far:
   - aliens / are we alone
   - the scale of the universe
   - existential questions (before the Big Bang, the end of everything)
   - "can humans do X"
   - timely news hooks (e.g. Voyager 1 reaching one light-day)
4. **Never translate or re-voice someone else's video.** That is copyright infringement and a channel strike risk.
   Only the topic and the facts are free; the script, footage, music and edit are always our own.
5. Give the owner 3-5 options with the numbers behind each, and recommend one.

## 2. Structure: one mystery, told as a story
- **One question carries the whole video** ("us se pehle kya tha?"). Open it in the first 30 s and answer it,
  or admit it is open, only at the end.
- **Opening (30-50 s): start in the middle of the action.** A person, a place, a year, a strange event (1964,
  two scientists cleaning a radio antenna, a hiss that won't go). Reveal what it was, add 1-2 big numbers as
  teasers, then ask the question. Title card after it. Don't tease a mystery in a hook and then solve it 15 s
  later in a cold open: merge the two.
- **Chapters, not a countdown, when the title is a question.** Use "10 Facts…" countdown cards only when the
  title says "10 Facts". Chapter cards carry an English title (no number); they also become YouTube chapters.
- **Every chapter ends on a bridge line** into the next ("Inflation ne bata diya, ki brahmaand phaila kaise.
  Lekin jaise hi scientists is ghadi ko aur peeche ghumate hain, poori science hi toot jaati hai."). This open
  loop is what holds viewers through the middle.
- **Every chapter has a person, a year and a twist** (Einstein: "your physics is abominable"; Hoyle named the
  theory he hated; BICEP2's discovery was dust).
- **Order:** history, then the science, then the newest clues, then the wildest ideas. End on the most
  mind-bending idea, not on dates or launch schedules.
- **Ending:** a debate line in the third person that names the competing ideas ("Hawking sahi the, ya
  Penrose? … Science abhi tak faisla nahi kar paayi."), then a callback to the opening scene.
- **Comment trigger:** the narrator never asks the viewer. The question goes in the **pinned comment** as a
  numbered poll of the ideas. The full footage list then moves to the description, which must stay under 5,000
  characters.

## 2b. Archive hunt: real footage and real voices (owner, 2026-10-27, standard from video 05)
While researching, list every real clip and recording the story could use, in `footage/archive.md`: the moment,
the source page, the licence, and the in/out seconds. Aim for **10-20 clips** a video: launches, the actual
instruments, labs and control rooms, the discovery as it was filmed, interviews of the people named.
- Only public domain (NASA, other US government) or CC BY / CC BY-SA / CC0. Never TV, news agencies, studios,
  other YouTubers or "fair use". Where to look: `productions/README.md` ("Where to look"). NASA launch broadcasts
  come with an .srt: grep it for "liftoff" to find the second.
- **Write the lines so they name what the footage shows** ("उन्नीस सौ नवासी में, NASA ने … कोबी"). A clip that
  doesn't match a line is not used; add a short line when a strong clip deserves one.
- **Real voices:** when a person in the story was recorded saying something that fits, introduce them in the
  narration and put the marker where their voice plays: `…John Mather ने कहा था, [bite:mather]` (the marker
  goes in `tts/narration.hi.md` and `script.txt`). Define it in `productions/NN/bites.json`: file, ss, d, who,
  when, the English words ("said"), a Hinglish subtitle ("hi"), credit, licence, url, "video": true when it has
  picture. Transcribe the recording first (faster-whisper, `language="en"`; NASA SVS interviews ship an .srt)
  and cut on word boundaries. **2-3 sentences, about 8-20 s** (one sentence "looked odd": owner, 2026-10-27),
  the person on camera, nobody talking over them, and nothing that is outdated today (Mather in 1989 called the
  CMB "the dominant form of energy in the whole universe": not true since dark energy). Subtitle it line by
  line: `"subs": [[0.0, 2.95, "Phir sabse bada sawaal tha: kya isme dhabbe hain?"], ...]`.
- No "..." suspense pauses and no `M` moments: the voice never waits (owner, 2026-10-27).

## 2c. Context before concept (owner, 2026-10-29)
The owner, after video 04: "you start with a concept in the middle of the thing; you don't give the context of
what is behind it." A viewer hears each line once; an idea that arrives without its "why" loses them. Every new
idea (a theory, a measurement, a puzzle, a named thing) gets, in this order:
1. **The question it answers**, in one line ("Scientists ke saamne ek sawaal tha: …").
2. **What it builds on**: a callback to something the viewer already heard ("wahi roshni, jo New Jersey ke
   antenna ne pakdi thi").
3. **The idea itself**, in plain words.
4. **An everyday comparison** (two cups of tea at the same temperature that never touched).
5. **The payoff**: how it answered the question, or why it didn't.
Video 04 broke this, and every case is a check for the next script:
- the horizon puzzle: never said why "never met, yet the same" is strange (heat needs time to even out)
- inflation: never said how it solved the puzzle (the regions were close and evened out, then were stretched
  apart)
- "the faint marks tell the universe's age": what marks, and how
- "the signal proved Hoyle wrong": why (a universe that never changes has no leftover glow from a hot start)
- gravity vs quantum physics "clash": why; Planck time arrived as a bare number
- BICEP2's "direct traces of inflation": what traces (a twist in the light), and why dust could fake them
- Hawking-Hartle's "time becomes like length" and Penrose's "marks of an earlier universe": no picture of either
**Context pass** before the owner sees the script: for every line, ask "what must the viewer already know for
this to land?" If the answer isn't earlier in the script, add it. To keep the length, cut a side fact, never the
context. Do the same for numbers: a number comes after the thing it measures, never before.

## 3. Language that flows when Neel reads it
- Conversational Hinglish. Keep English words people actually say (scientist, satellite, theory,
  calculate, inflation, Big Bounce, galaxy). Keep the emotional words Hindi (suraag, goonj, pahaili, daava).
- Avoid textbook words. Use **sateek** (not sateekta), **phailaav** (not vistaar), **Father X, ek Catholic
  padri** (not "Church Father"), and **gandagi** (not beet, which reads as crude).
- **Short sentences.** One idea and at most one number per sentence. Put the number near the end, so a
  count-up can land on the spoken word.
- **No "..." at all** (owner, 2026-10-27: no pauses, not even for suspense). Neel holds each "..." for about a
  second. Use commas; `tts_check.py` refuses "...", "…" and dashes.
- **Nothing Neel can't say smoothly.** No catalogue names like MoM-z14 or GW250114 in the narration: say what
  it is ("ab tak ki sabse door ki galaxy") and put the name on screen.
- **Repeat a key phrase at most 3 times** (opening, one middle callback, the end). Vary the rest ("sabse purani
  roshni" becomes "Big Bang ki goonj", "woh roshni").
- **Questions belong to characters,** plus the one agreed debate line at the end. Turn the rest into statements
  ("Aisa kaise?" becomes "Yahi thi pahaili.").
- **Check grammar, especially gender agreement** (waqt is masculine: "waqt bhi, lambaai chaudaai jaisa hi ban
  jaata hai").
- **Numbers should be easy to picture.** "1 ke aage 43 zero", not "10 ki power minus 43". Check the zero count
  (10⁻⁴³ s = 1 second cut into 1 followed by 43 zeros pieces). Big numbers go in Hindi words in the Devanagari
  file.
- **Every abstract idea gets an everyday comparison:**
  - an orange for the early observable universe
  - the South Pole for "no before"
  - a ball for a bounce
  - bubbles in boiling water for the multiverse

## 4. Accuracy: say only what is known
- **Hedge theories.** "scientists ke hisaab se" for inflation; "zyaadatar scientists is daave ko nahi maante"
  for disputed claims (Penrose's Hawking points).
- **Don't credit an old discovery with later results.** The 1964 hiss proved there was a beginning; the 13.8
  billion years came from Planck in 2018.
- **Precise wording physics fans check:**
  - space *itself* expanded faster than light
  - only the *observable* universe was orange-sized
  - don't describe Penrose's cycles as shrinking: that is the Big Bounce, a different idea
- Check the newest items on the web (records, launch dates). Every number goes in the fact-check table with a
  source.

## 5. Length and pace
- **Length:** Neel reads about 147 words a minute at 1.0x, so about 1,600 words is 11 minutes.
- **Record at normal pace.** Before planning the edit, send the owner a 60 s sample at 1.0x and 1.2x
  (rubberband time-stretch of the recording, no credits). Build the edit at the chosen speed, so the master
  renders only once. Video 04: the owner chose **1.0x** for full videos (2026-10-26); Shorts stay at 1.2x.
- **The recording is checked automatically** (`speech_check.py`, run by the narration stage): every name and
  English term must be heard, and no extra नहीं. Video 04: "BICEP" read as "B-sep" until written बाइसेप; "नए
  idea" sounded like "नहीं"; वक़्त came out wrong (now "time"). See §7 for how to avoid all of this up front.
- **Never write नए / naye.** Neel says it so it sounds like नहीं ("naye bhaari atom bante hain" heard as "heavy
  atoms don't form"). Use अलग, अभी अभी बने, or rephrase (video 04 ch7, the 03 gold Short, 2026-10-26).

## 6. Review loop with the owner
1. Propose the topic and an outline of the key points. Get an OK.
2. Write `productions/NN-slug/script.md`:
   - package: title, description, tags
   - the script, one `## <section id>` per section (`opening`, `ch1`…, `ending`)
   - the chapter card titles
   - the fact-check table
3. Write `script.txt`, plain text the owner can copy and paste (section labels, no markdown, no tables).
   Paste it in the chat as well.
4. The owner may run it past another AI agent. Weigh each point honestly:
   - adopt the good ones
   - correct its factual slips (e.g. its "point laga kar 43 zero" was off by one; it called Penrose's model a
     shrink-and-bounce)
   - flag anything that breaks a channel rule and leave that decision to the owner
5. Before the owner's final OK, run the checker:
   ```bash
   python scripts/science/script_check.py productions/NN-slug/script.txt
   ```
   It counts "...", flags catalogue-style names, repeated phrases and narrator questions, and estimates the
   length.
6. Only after the OK, write `tts/narration.hi.md` in Devanagari, one `##` section per script section.
   Use the same section ids and commas instead of dashes, and record.

## 7. Right the first time: no paid re-recordings (owner, 2026-10-27)
ElevenLabs bills a whole section every time it is recorded, so a script goes to ElevenLabs only once it can't
come back wrong. In this order:
1. The owner's OK on `script.txt` (§6), with `script_check.py` clean.
2. Write `tts/narration.hi.md`, then `python scripts/elevenlabs/tts_check.py productions/NN-slug/tts/narration.hi.md`
   until it prints 0 problems. It refuses every word in `productions/tts-lexicon.json` "replace" (mispronounced or
   unwanted, with the fix), "...", digits and symbols, acronyms Neel would guess at, catalogue codes, Hindi in
   Latin letters, 28+ word sentences and undefined `[bite:]` markers. The narration stage runs it too.
3. `pipeline.sh productions/NN-slug probe`: every name and English term never heard before is read alone (a few
   characters each), transcribed and marked ok / LISTEN. Send the owner `work/NN-slug/voice_probe/probe.mp3` with
   `probe.txt` if anything says LISTEN. Respell what comes out wrong (Devanagari, the way it is said: बाइसेप,
   कोबी), add it to the lexicon, probe again; then `PROBE_FLAGS=--accept` adds the good ones to "verified".
4. Only then `pipeline.sh … narration`. `speech_check.py` listens to the new sections; a FLAG means respell +
   lexicon entry + re-record that one section.
5. **Every new finding goes into `tts-lexicon.json` the same day**, so it can never be paid for twice.

## Owner's verdicts on video 04 (2026-10-26/27): do this, not that
Liked and kept:
- An opening that starts on the big fact and its numbers and ends on the one question: "तेरह point आठ अरब साल
  पहले, ब्रह्मांड की शुरुआत हुई। … Big Bang से पहले, आख़िर क्या था?", then a bridge into the story
  ("इस सवाल तक पहुँचने का रास्ता, उन्नीस सौ चौंसठ में खुला।"). When an opening changes, write the bridge so the next
  chapter continues without a jolt, and show the owner the join.
- The calm take with the locked preset (he picked it over a more expressive one: "1 easily"). Never change the
  voice settings for a whole video.
- Full videos at 1.0x; Shorts at 1.2x.
- Lines that name what is on screen: people (with photos), missions and real footage (the COBE lines were added for
  their 1989 footage).
- Simple English words where Hindi ones trip: time (not वक़्त), signal (not सरसराहट), particles (not कण).
Did not like (never again):
- Pauses anywhere: no "..." suspense, no designed silences, no long gaps between chapters.
- An odd or unpleasant image in the hook (pigeon droppings in the antenna) and showy sound words (सरसराहट).
- A Short script that wasn't the video's own story ("Is this from the video that we created? I don't like the
  script."): Shorts retell the strongest moment of the finished video.
- A weak Short hook: start with "क्या आपको पता है कि हमारे…" and make it about the viewer's world ("हमारे planet का
  सोना", not "गहनों").

## Shorts
Shorts scripts follow the owner's 4-beat format and the Shorts rules in `productions/README.md` and the
`science-shorts` skill:
- hook, conflict & discovery, core concept, payoff
- about 130 words for 48 s at 1.2x
- one-word gold captions
- FULL VIDEO BELOW written on screen, never spoken
