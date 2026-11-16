# 02 · Shorts: what holds us back from 100k (research, 2026-11-16)

Scope: the v2 Shorts (`scripts/video/render_short_v2.py`) and the three 08 Shorts (hunter, attractor, darkflow).
Evidence quality: YouTube publishes no swipe or retention thresholds. Where a number below comes from a vendor
blog it is marked *(vendor)*. Only the official sources and the large-sample studies should carry weight.

## 1. Where our Shorts fall short (measured on the 2026-11-16 renders in `work/08-shorts/out/`)

| # | Problem | Where |
|---|---|---|
| A | **A dead tail.** Each Short ends on 4.6-4.7 s of end card (11% of the runtime), and the last ~2.6 s of it is silent. This is the moment viewers swipe, and it breaks the loop. | `END_HOLD = 2.4` (L37, added at L115); `cta0` (L483). hunter 43.0 s, card from 38.3 s; attractor 41.7/37.1; darkflow 43.0/38.4 |
| B | **Too long for a teaser.** The Shorts run 41.7-43.0 s on 119-135 words. In the largest length dataset, median views fall from 542 (21-30 s) to 347 (31-45 s). | `captions.hinglish.md` word counts |
| C | **The hook comes late.** The centre of frame 0 shows a filler caption ("HAMARI", "ABHI", "2008"). hunter's number lands about 2.5 s in. attractor pauses 0.29 s at 0.37 s ("Abhi,"). darkflow opens on a date and gives its claim at about 5 s. | `script.txt` HOOK lines; number cards start on their word (L201) |
| D | **The first cut in hunter is a fake.** The 1.4 s "jump" zooms into the same shot (L190-191), so the first new picture appears at 3.51 s. The owner's rule is a cut within 1.5-2 s. | `build()` L190-192 |
| E | **Captions sit under the action buttons.** Caption centre y = 1325 (`H*0.69`) with a width of up to 990 px (`W-90`, L463-465). That is below the conservative safe bottom (y ≤ 1248) and inside the right 192 px button column. | L465 |
| F | **The title is wider than the top safe area.** Its centre is y = 285 and its width is up to 1000 px (L380, L400). The right end can sit under the search and menu icons. | L380, L400 |
| G | **darkflow withholds everything, and its answer is 8:51 into the full video.** Its last line is "Usne kya dekha? … poori video dekhiye". The Related-video tap lands at 0:00 of an 11-minute video. | `darkflow/script.txt`, `youtube.md` chapters |
| H | **The default speed is still 1.2x.** `cfg.get("speed", 1.2)` (L98) and the docstring (L12, L20) say 1.2. A `short.json` without `"speed"` would break the owner's 1.1x rule. | L98 |
| J | **Too few Shorts.** We have 3 Shorts for a 10-chapter video, so the algorithm gets 3 tries per video. | `productions/08-scariest-places/shorts/` |

## 2. Improvements, in priority order

### P1 (do before the 08 uploads)

**P1-1. Cut the dead tail and make the end loop.** Set `END_HOLD = 0.7` (L37). The end card already starts on the spoken
cue (`cta_at`), so it stays fully readable for about 2.1 s (the spoken "Poori kahani, poori video mein" plus the hold). Move the bell to `cta0` (L510) so it does not land on the loop seam.
In the scripts, make the last spoken line run straight into the first line. For hunter, the last line is "…chhe saal kyun lage?" and the first is
"Das crore black holes…". End on a question the first line restarts.
- *Evidence:* creators' average view percentage roughly doubled once they looped (96.8% → 187.1%), and YouTube's own Shorts
  report advises an ending that flows back to the start ([vidIQ](https://vidiq.com/blog/post/double-youtube-watch-time-looping-shorts)).
  Completion and re-watch are distribution signals ([Quso, 108k Shorts](https://quso.ai/research/youtube-shorts-length)).
  YouTube ranks on both average view duration and average % viewed ([YouTube Help](https://support.google.com/youtube/answer/11914225)).
- *Expected impact:* about +8-12 points of average % viewed from the tail alone, plus replays.

**P1-2. Target 30-35 s.** Set the word budget to **≤ 100 words** (Rudra at 1.1x speaks about 3.0 Roman words/s: 122 words in
40.4 s on hunter). Cut THE PROBLEM first: drop the setup sentences ("Scientists bhi saalon tak yahi sochte rahe";
attractor's list "hamara Suraj, hamari Milky Way…"). Never cut the twist. Add to the science-shorts skill: "35 s max for curiosity Shorts".
- *Evidence:* median views by length were 21-30 s 542, 31-45 s 347, 46-60 s 188
  ([Quso](https://quso.ai/research/youtube-shorts-length)). A 253M-view Short ran 31 s and was watched about 1.4 times on average
  ([breakdown](https://danielrusnok.substack.com/p/how-a-faceless-channel-engineered)).
- *Expected impact:* a higher completion rate and more loops. These are the main levers after the swipe decision.

**P1-3. Front-load the hook: the claim and the number in the first 1.5 s.**
- *Scripts:* start on the number or the claim, with no opening comma or date.
  - hunter: "Das crore black holes, sirf hamari galaxy mein…"
  - attractor: "Aap abhi 600 kilometre har second ki speed se…"
  - darkflow: "Hamare universe ke bahar se koi cheez galaxies ko kheench rahi hai. Ye daava 2008 mein…"
- *Renderer:* for a number in the first section, start the count at 0.0 (`t0 = 0` in L201, land on its word). This restores the old
  skill's "number up and counting from frame 0". Show no caption before the number lands, so frame 0 carries the number and the title, not "HAMARI".
- *Renderer:* the first item gets a real cut at ≤ 1.5 s. In `build()`, split item 0 into two shots when `d > 1.8`, instead of the same-shot jump
  (L190-191). Or plan it in edit.spec: give the first `V` line a second shot on the 3rd-4th word.
- *Evidence:* YouTube's Shorts guide (Apr 2025) says "Capture attention in the first few seconds to prevent viewers from
  scrolling" ([PPC Land](https://ppc.land/insider-tips-for-creating-viral-youtube-shorts-revealed/)). "Viewed vs swiped away"
  is the official measure of this decision ([YouTube Help](https://support.google.com/youtube/answer/9314355)). In 1,467
  million-view Shorts hooks, the median length was 11 words and 37% addressed "you"
  ([Overseer](https://www.overseeros.com/blog/million-view-youtube-hooks-study)). The 1.5-2 s swipe window is a practitioner
  convention *(vendor)*.
- *Expected impact:* the largest single lever on Viewed vs swiped away. Aim for ≥ 70% *(vendor heuristic)* and compare against our own Shorts.

**P1-4. Move the text into the Shorts safe zone.** The clear area is x 48-888 and y 288-1248 (conservative); the bottom 672 px and the right 192 px are UI
([Socialync](https://www.socialync.io/tools/safe-zones/youtube-shorts), [Reap](https://reap.video/blog/short-form-video-safe-zones)).
- Captions (L465): centre `x = 492`, `y = 1170` (61%), `fit(lay, 780)`.
- Title (L400 and L380): `y = 330`, `fit(box, 860)`, centre `x = 500`.
- Number cards and headlines (L413, L435): `fit(…, 860)`, `x = 500`.
- End-card arrow (L457): move it to `x ≈ 300`, `y ≈ 1330`, pointing at the Related-video pill, which sits bottom-left under the channel name.
  **Check the exact pill position on a phone with the private upload.**
- *Expected impact:* fewer unreadable words; the one-word style only works if every word is legible.

**P1-5. Point the CTA at the exact place in the full video.** A Related-video tap opens at 0:00. Name the chapter on the
end card's first line, e.g. `DARK FLOW · CHAPTER 8` over `WATCH THE FULL VIDEO`, and add a `"cta_sub"` key to `short.json`. Put
"Full video (Dark Flow at 8:51): https://youtu.be/<id>?t=531" as the description's first line.
- *Evidence:* YouTube's editor says "The very first few seconds of your long video should confirm they made the right
  choice" ([Social Media Today, Jul 2026](https://www.socialmediatoday.com/news/youtube-offers-tips-on-working-with-shorts-videos/)).
  Shorts whose theme matches the linked video convert best ([Spotter](https://spottercommunity.beehiiv.com/p/increase-views-from-related-shorts)).
- *Expected impact:* fewer viewers who tap and then bounce, which protects the long video's retention.

**P1-6. Fix the speed default.** L98: `cfg.get("speed", 1.1)`, and update the docstring at L12 and L20. Delete the `[SUSPENSE]` markers from the three `script.txt` files.

### P2 (next video)

**P2-1. Pay off the Short's own question and withhold the bigger one.** hunter already works this way: the twist answers "what passed in front" and
holds back "why six years". darkflow and attractor withhold their only question. For the owner: have the Planck line answer
partly ("Planck ko utna bada flow nahi dikha…"), then end on the open question. Test it on one Short against a full withhold, and compare
average % viewed and engaged views.
- *Evidence:* no controlled study exists. Million-view practice is "ending where curiosity ends"
  ([breakdown](https://danielrusnok.substack.com/p/how-a-faceless-channel-engineered)). YouTube measures satisfaction with
  surveys and "not interested" ([YouTube Help](https://support.google.com/youtube/answer/11914225)).

**P2-2. Release the Shorts inside the first 72 h after the full video goes public, then one a day.** Shorts posted within 3 days of the long video
drove more long-form views ([Spotter](https://spottercommunity.beehiiv.com/p/increase-views-from-related-shorts)). Analysts
see Shorts reach fade after about 28-30 days (unconfirmed by YouTube; [SEJ](https://www.searchenginejournal.com/youtube-shorts-algorithm-may-now-favor-fresh-over-evergreen/562661/)).
Suggested order for 08: hunter (chapter at 0:39) on day 0, attractor on day 1, darkflow on day 2.

**P2-3. More Shorts per video.** 08 has 7 more chapters with a hook: magnetar, quasars, TON 618, Great Nothing, Cold Spot,
edge, and the 270-day star. Aim for 6-8 Shorts per video. YouTube tests each Short on a seed audience ("find a set of people
that may enjoy your video", [Sherman](https://www.youtube.com/watch?v=n3jsYK_-aRU&t=388s)), and channel totals come from a few hits (one space
channel: 4.6M views, median Short 432; [Revid](https://www.revid.ai/case-studies/mysteries-of-the-universe) *(vendor)*).

**P2-4. Measure engaged views, not views.** Since 31 Mar 2025 every replay counts as a view; use engaged views
(Advanced mode) ([emarketer](https://emarketer.com/content/youtube-shorts-changes-view-count-rules-match-tiktok--instagram)).
Record per Short after 7 days, in `productions/NN/shorts/<id>.md`:
- Viewed vs swiped away
- average % viewed
- engaged views
- subscribers gained
- the full video's views from the "Shorts" traffic source

The Related video lifts long-form views by about 10% on average for channels it works for, and is "modest"
([Spotter](https://spottercommunity.beehiiv.com/p/related-shorts)). Judge success first by the Short's own reach.

### P3 (worth testing)
- **Bigger key words:** scale captions 1.2x for numbers and the science term (still gold, still one word). Caption-style
  gains are vendor claims only ([BlitzCut](https://blitzcutai.com/blog/word-by-word-captions-vs-full-sentence-captions)).
- **Titles under about 50 characters,** so the overlay does not truncate them. Hashtags are not required (Sherman) and classification is by
  aspect ratio and length ([YouTube Help](https://support.google.com/youtube/answer/15424877)). Keep `#shorts` plus 2 tags.
- **Trending audio:** YouTube says trending audio widens reach
  ([PPC Land](https://ppc.land/insider-tips-for-creating-viral-youtube-shorts-revealed/)). It can only be added in the app, so it clashes with our mixed bed and credits. Test it on one Short only.

## 3. Do not do
- **No suspense stop or silent freeze** (owner: "it kills the rhythm"). Leave `suspense_after` unset. P1-1 removes silence; it adds none.
- **Do not change the caption style.** Captions stay one word at a time, in gold (P1-4 moves them; P3 scales key words only).
- **Do not change the voice speed for these.** Voice stays at 1.1x; shorten by cutting words, never by speeding up.
- **No public uploads.** Uploads go `--privacy private`; the owner publishes. Related video is set only after the full video is public.
- **No script changes without the owner.** Every script change above (hooks, length, payoff) goes to the owner first, in Hinglish.
- **No links in descriptions or comments as the CTA.** They do not click in Shorts (since Aug 2023, [Tubefilter](https://tubefilter.com/2023/08/10/youtube-shorts-comments-spam/)); the Related video is the only link.
- **Do not delete and re-upload a weak Short.** This "may be seen as spam" ([Sherman](https://www.youtube.com/watch?v=n3jsYK_-aRU&t=443s)).
- **No re-used clips across a video's Shorts** (existing ban rule). YouTube is cutting the reach of unoriginal re-uploads
  ([YouTube, Oct 2026](https://support.google.com/youtube/blog/470890423/prioritizing-original-content-on-shorts?hl=en)).
- **Do not trust vendor benchmarks** ("70% viewed", "+34% captions"). Compare each Short against our own earlier Shorts of the same length.
