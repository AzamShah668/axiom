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

## 3. Language that flows when Neel reads it
- Conversational Hinglish. Keep English words people actually say (scientist, satellite, theory,
  calculate, inflation, Big Bounce, galaxy). Keep the emotional words Hindi (suraag, goonj, pahaili, daava).
- Avoid textbook words. Use **sateek** (not sateekta), **phailaav** (not vistaar), **Father X, ek Catholic
  padri** (not "Church Father"), and **gandagi** (not beet, which reads as crude).
- **Short sentences.** One idea and at most one number per sentence. Put the number near the end, so a
  count-up can land on the spoken word.
- **At most 5 "..." per video.** Neel holds each "..." for about a second; save them for the designed moments
  (the reveal words). Use commas everywhere else.
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
  renders only once.

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

## Shorts
Shorts scripts follow the owner's 4-beat format and the Shorts rules in `productions/README.md` and the
`science-shorts` skill:
- hook, conflict & discovery, core concept, payoff
- about 130 words for 48 s at 1.2x
- one-word gold captions
- FULL VIDEO BELOW written on screen, never spoken
