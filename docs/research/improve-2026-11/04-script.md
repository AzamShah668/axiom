# 04: Script and storytelling for retention

Research lead: scriptwriting. Draft for the owner. Nothing in the skill, the checker or the productions has been
changed yet.

## 1. Where 08 and our method fall short

Measured on `productions/08-scariest-places/script.txt`: 1,866 words and 94 sentences. The render is 11:02, so
Rudra reads about **170 words a minute**; the checker assumes 147.

1. **The hook is a hedged claim, said twice.** It opens with "Hamari galaxy mein lagbhag 10 crore black holes ho
   sakte hain, aur unme se zyaadatar ko aaj tak kisi ne dekha bhi nahi hai" (24 words, hedged). The next 21 words
   ("Woh na chamakte hain, na koi roshni chhodte hain…") repeat it.
2. **The roadmap is abstract and uses a banned adjective.**
   - "brahmand ki sabse daravni jagahon mein se bas pehli jagah hai" is the "one of the most terrifying" pattern
     that `outline.md` faults in SciMind.
   - "…insaan usme se kitna kam dekh pata hai" promises a thought, not the magnetar, TON 618 or the void.
3. **The rhythm is flat.**
   - Sentences average 19.9 words. Only 2 of 94 have 6 words or fewer.
   - In 28 places, three sentences in a row are within 4 words of each other in length.
   - The opening has no sentence under 14 words. 05 Voyager averaged 11.5 words, with 25 short lines.
   - The owner's "continue like you are speaking" fixed the choppy draft, but overshot.
4. **The bridges follow one template.**
   - The pattern: "Black hole kam se kam chup to rehta hai, lekin agli jagah…" (ch1), "Magnetar to phir bhi…,
     lekin…" (ch2), "…kam se kam dikh to rahi thi, jabki agli jagah…" (ch4).
   - They tease a category ("khatra khud roshni hai"), not a picture.
5. **Five sections name no person:** ch1, ch2, TON 618, the Great Attractor and the ending. §2's "person, year,
   twist" rule was dropped for the list format. Ready-made characters, both to verify:
   - Kailash Sahu (STScI) led one of the 2022 rogue black hole teams.
   - Chryssa Kouveliotou used the 08 magnetar, SGR 1806-20, to prove in 1998 that magnetars exist.
6. **Bare numbers and too many hedges.** "5,000 light years", "ek quadrillion guna" and "40 se 66 billion guna"
   get no everyday picture. "lagbhag" appears 14 times.
7. **The ending runs 69 s and closes on a moral.** It hands the viewer on to nothing.
8. **Gaps in the method.**
   - §2 has no answer for list topics: it needs a spine.
   - §3b asks for rhythm and re-hooks, but nothing checks either.
   - The checker uses the wrong pace.

## 2. Prioritised improvements

### P1

**P1.1 The hook: a scene, then stakes, then specific teasers.**
- **Evidence:**
  - The first 30 s should be a real example that proves the title, then why it matters, then a roadmap
    ([Outlierkit](https://outlierkit.com/resources/youtube-hooks-and-retention/)).
  - YouTube reports retention at 30 s as "Intro" ([YouTube Help](https://support.google.com/youtube/answer/9314415)).
  - In 1,239 top videos (Ames Create, Oct 2026), compared with each creator's usual results: bold-claim openings
    did 10% worse, question openings 14% worse, relatable openings 19% better, and visual spectacle 33% better
    ([Net Influencer](https://www.netinfluencer.com/curiosity-gap-openings-dominate-top-creator-videos-but-visual-spectacle-runs-furthest-data-shows/)).
- **SKILL.md §3b:**
  - The first sentence has 12 words or fewer, no hedge, and names something the footage can show.
  - Stakes for Earth or insaan come by 15 s.
  - The roadmap names 2-3 specific later moments, never a theme.
  - The opening is 130 words or fewer (about 45 s).
- **Check `hook`:** flag a first sentence over 12 words, a hedge in it (`ho sakte|shayad|lagbhag|andaaza`), or an
  OPENING over 130 words. Message: `! [OPENING] first sentence 24 words (max 12), hedged: open on a concrete scene`.

**P1.2 Vary sentence length; don't shorten everything.**
- **Evidence:**
  - Use "short sentences so the meaning is clear immediately"; read the script aloud and make sure each sentence
    fits in one breath ([Media Helping Media](https://mediahelpingmedia.org/how-to/how-to-write-a-radio-news-script/)).
  - Voice-over guides cap sentences at 15-20 words and fix rushed reads with shorter sentences and firmer
    punctuation ([Artlist](https://artlist.io/blog/elevenlabs-text-to-voice-tips/)).
- **SKILL.md §3:**
  - Keep the flowing lines, and add a 3-7 word punch line at a turn every 4-6 sentences.
  - Average 11-16 words; no sentence over 24.
- **Check `rhythm`:** per section, flag any of these:
  - fewer than one sentence of 7 words or fewer per 120 words
  - more than 2 "flat runs" (3 sentences in a row, each 12 words or more, within ±4 words of each other)
  - any sentence over 24 words
  - 08 fails in every section.

**P1.3 Every turn is "but" or "therefore"; every chapter is setup, tension, payoff.**
- **Evidence:**
  - Parker and Stone's rule: "but/therefore", never "and then"
    ([Cheatsheet](https://www.cheatsheet.com/entertainment/south-park-trey-parker-and-matt-stone-1-rule.html/)).
  - Blackman: each segment "needs all the components of a full video"
    ([RR#5](https://georgeblackman.substack.com/p/retention-review-5-why-should-i-care)); reverse the belief early,
    "and this, *but* that" ([RR#6](https://georgeblackman.substack.com/p/retention-review-6-and-this-but-that)).
  - Muller's research behind Veritasium: plain explanations made students *more* confident in wrong ideas, and
    starting from the misconception worked better
    ([THE Journal](https://thejournal.com/articles/2015/05/05/watching-videos-does-not-necessarily-lead-to-learning.aspx)).
- **SKILL.md §2:** each chapter runs in this order: what people believed → a person and a year → the *lekin* →
  the payoff → a bridge that names one concrete next picture.
- **Check `turns`:** flag 120 words or more with no turn word
  (`lekin|magar|par\b|jabki|phir bhi|balki|asal mein|isliye`). Message: `! [CH5] 140 words without a turn`.

**P1.4 A person in every chapter, and the real pace.**
- **Evidence:** one named person moves people more than statistics, and adding statistics to the story weakened it
  ([Small, Loewenstein & Slovic](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Sympathy_and_callousness.pdf)).
- **Check `person`:** warn when a CHAPTER has no 4-digit year, or no capitalised two-word name outside an object
  list (`Milky Way|Big Bang|Cold Spot|Dark Flow|…`). Message: `~ [CH1] no person named: who found it?`
- **Pace:** `--wpm` comes from the voice preset (Rudra about 170).

### P2

**P2.1 A spine for list topics.** A numbered list can make viewers feel they already got the answer
([Social Media Examiner](https://www.socialmediaexaminer.com/youtube-retention)). Escalate along one axis and say
it in every chapter.
- For 08, sort by distance: 5,000 ly → 50,000 → ~250 M → ~700 M → 2.4 B → ~3 B → ~10 B → the edge (to verify).
- **SKILL.md §2:** "list topics: choose the spine (distance, size, time, danger) in the outline."

**P2.2 Re-engagement at fixed times.**
- **Evidence:**
  - The MrBeast memo marks minutes 3 and 6 as "re-engagement" points
    ([memo](https://www.alexanderjarvis.com/memo-how-to-succeed-in-mrbeast-production/)).
  - YouTube: if top moments appear late, "move that compelling content earlier"
    ([YouTube Help](https://support.google.com/youtube/answer/9314415)).
- **SKILL.md:** the outline puts the strongest real event at about 2:30-3:30 and about 6:00.
- **Check `rehook`:** print each section's start time, and flag any section over 95 s.

**P2.3 Tangible numbers, and fewer hedges.**
- **Evidence:** say "nearly two thousand", not "1,988" ([Media Helping Media](https://mediahelpingmedia.org/how-to/how-to-write-a-radio-news-script/)).
- **Check `numbers`:** warn on a sentence with `billion|crore|lakh|quadrillion|\d{4,}` when neither it nor the next
  sentence has a comparison (`jaise|jitna|jitni|matlab|yaani|barabar`).
- **Check `hedges`:** warn on more than one "lagbhag" per 150 words.

**P2.4 AI tells.**
- **Check `tells`:** flag `sabse \w+ \w* ?mein se`, a 2-word phrase shared by 3 or more chapter-final sentences
  (this catches "kam se kam"), and more than 3 reaction lines (`Achhi khabar|Buri khabar|Sach kahein`) per script.

### P3: trial, then judge by retention

- **P3.1 Shorter ending.** The final payoff, then a callback, all in 45 s or less.
  - The memo: "endings must always be abrupt to protect retention"; Blackman found viewers drop off during repeated
    reflections ([RR#2](https://georgeblackman.substack.com/p/retention-review-2-payoff-outro-core)).
  - The last line hands over to the end-screen video in the third person ("Lekin is andhere ki shuruaat ek roshni
    se hui thi…" → video 04). This is the owner's call.
- **P3.2 Open loop before each point**, as Hindi creators teach: "create a question related to the next point…
  before you start" ([transcript](https://sozai.app/transcript/write-youtube-script-get-2x-watch-time/)). Dhruv
  Rathee is described as working hook → background → present
  ([summary](https://recapio.com/digest/how-to-research-like-dhruvrathee-script-like-dhruv-rathee-by-tube-sensei)).
  The Hindi-channel evidence is thin and second-hand; our own retention graphs should decide.
- **P3.3 TTS punctuation.**
  - Commas are breath points.
  - A turn line ends with a full stop, so the voice resets.
  - Never "…" or dashes: ElevenLabs says ellipses "add pauses and weight" and dashes are "less consistent"
    ([docs](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices)).

## 3. Outline template (`productions/NN-slug/outline.md`)

```
TITLE PROMISE: <one line>
SPINE: <one question>, or for a list: <escalating axis: distance / size / time / danger>
HOOK (<=130 words, ~45 s)
  0-10 s  present-tense scene proving the title (<=12 words, no hedge)
  10-25 s stakes for Earth / insaan, made tangible
  25-40 s 2-3 specific teasers; the last one = the ending's idea
  bridge  names ch1's first picture
CHAPTER n (60-95 s), starts ~m:ss   [re-engage slot 2:30-3:30 / ~6:00?]
  belief -> person + year + moment -> LEKIN -> payoff
  number = everyday picture
  archive clip / bite id
  bridge: one concrete next picture
ENDING (<=45 s): payoff -> callback to the hook scene -> third-person hand-off
PINNED POLL: <options>
```

## 4. Rewritten opening for 08 (136 words, about 47 s; `script_check.py` clean)

> Hamari galaxy mein ek black hole akela bhatak raha hai. Na koi taara saath hai, na roshni. Scientists ko use
> pakka karne mein chhe saal lage. Aur woh akela nahi hai. Milky Way mein lagbhag 10 crore black holes ho sakte
> hain, aur zyaadatar ko kisi ne kabhi nahi dekha. Agar koi solar system ki taraf aaye, to use pehle se dekh paana
> bahut mushkil hoga. Aur yeh bas pehli jagah hai. Aage ek mara hua taara hai, jiski chamak ne 50,000 light years
> door se Earth ki upar wali hawa hila di. Ek aur black hole, jiske andar Neptune ki poori orbit bees se zyaada
> baar samaa jaaye. Aur aakhri jagah par khatra koi cheez nahi, ek andhera hai, jo dheere dheere badh raha hai.
> Shuruaat usi black hole se, jise koi dekh nahi sakta.

**What changed:**
- Sentence lengths run 10/7/9/5/19/16/6/21/16/17/10.
- It opens on a scene, not a statistic.
- The stakes arrive by 15 s.
- Three concrete teasers follow, and the last one promises the ending.
- **Owner rules kept:** English words in Latin letters; no "aap" and no questions; no "…", dashes, "goonj" or
  "naye"; no intro and no date.

**Knock-on edits to ch1:**
- Open on the 2011 star; its current first line would repeat the bridge.
- Drop its duplicate "pehle se dekh paana" line.
- Name Kailash Sahu.
