# 03 Packaging and discovery (research, 2026-11-16)

Evidence quality is flagged: **[official]** = YouTube/Google docs, **[data]** = large
observational study, **[weak]** = blogs/anecdote.

## 1. Where we are lacking

1. **Videos launch with no thumbnail.** Video 05 went public on 1 Nov with "No thumbnail yet (the owner adds it)"
   (`productions/05-voyager/youtube.md`): its first 24-48 h of Home/Suggested impressions, the window YouTube says to
   judge CTR in, showed an auto-frame.
2. **One title, one thumbnail, no testing.** YouTube now A/B tests up to 3 titles and/or thumbnails natively and
   picks by watch-time share, not CTR. We use none of it.
3. **Titles are search labels, not hooks.** `<Topic> | Hindi Documentary` (science-publish) has no curiosity gap or
   number. The title is chosen at stage 1 and only "packaged" at stage 6. Top creators package *first*.
4. **The description wastes its first line** by repeating the title. That line is the search snippet. There is no
   Hindi/Hinglish keyword line either.
5. **Two "pinned" comments.** The poll and `credits_full.txt` are both meant to be pinned, but a video has only one
   pin. Also the API token got 403 on comments (05).
6. **No end screen.** Video 08 ends ~5 s after the last line (cutlist total 662.5 s). End-screen elements need the
   last 5-20 s and would sit on narration.
7. **Upload time is ad hoc** (05: 12:00 IST), never checked against our audience.
8. **No feedback loop.** We never record our own impressions, CTR or view duration, so we can't learn which packaging
   works for *our* audience.

## 2. Prioritized improvements

### P1-a: Never publish without a thumbnail; ship 3 variants for Test & Compare
*Evidence:* the A/B tool takes up to 3 titles/thumbnails, desktop Studio only, needs advanced features, not on
private videos, runs up to 2 weeks, winner by watch-time share [official]
(https://support.google.com/youtube/answer/16391400). Packaging is the biggest lever: "the difference between a
million views and 28 million views is how you package it"; a 30-40 % thumbnail fix took one old video to ~40x daily views
(Paddy Galloway, https://www.colinandsamir.com/resources/the-new-rules-of-youtube-from-paddy-galloway) [weak].
Design traits alone barely separate breakouts from flops: brightness, contrast, saturation and faces are all within noise across
2,960 thumbnails, but **text-free thumbnails are ~25 % more common among underperformers** and 4-6 words is the
best band (https://eden.so/blog/what-makes-a-good-youtube-thumbnail/) [data]. Faces don't help on average
(1of10, 300k videos, https://www.searchenginejournal.com/do-faces-help-youtube-thumbnails-heres-what-the-data-says/563944/)
[data], so our footage-only look is fine. **The concept matters more than the polish.** The 3 variants must differ in *idea*, not colour.

**Owner decision needed** (his rule is "no thumbnail"): the tool makes 3 drafts he can use, edit or replace; a
thumbnail is set before the video goes public.

**New script `scripts/youtube/make_thumbnail.py`** (extends `scripts/video/thumbnail.py` `fullbleed()`; reuse
`scripts/footage/clip_model.py`):
- **Input:** `productions/NN/thumbs.json`, three entries:
  `{"id":"A","query":"magnetar flare blasting out","shot":null,"t":null,"lines":["IT HIT EARTH","*FROM 50,000 LY*"],"focus":0.68,"ring":null}`.
  `*word*` = yellow keyword line. `shot`/`t` pin an exact frame. `ring:[x,y,r]` draws an optional glow ring.
- **Frame pick:** restrict to shots in `work/NN/cutlist.json`, so the thumbnail shows what the video shows (watch-time
  scoring punishes bait). Rank by CLIP similarity of `query` vs `work/library/shots_emb.npz`. Drop shots flagged in
  `text_gate.json`, `dup_of`, or with `luma` < 8. Sample 5 frames per top-8 shot. Score each frame:
  0.5·CLIP + 0.2·sharpness (Laplacian variance) + 0.2·colourfulness (Hasler-Süsstrunk) + 0.1·centre-weighted
  saliency. Write `work/NN/thumbs/candidates.jpg` (4x3 contact sheet with ids) for a human pick.
- **Resolution:** library clips are 1080p proxies. For the chosen frame, re-grab from the 4K source
  (`sources.json` `url`, `ss`+offset, `ffmpeg -ss … -frames:v 1`), falling back to the proxy. This allows a 1.5x
  punch-in without blur.
- **Look:** 1280x720. Keep the existing grade (contrast 1.18, saturation 1.35). Add a 0.35 vignette and a +12 %
  exposure lift in a radius around `focus`, so one subject pops.
- **Text:** Anton (`work/media/fonts/Anton.ttf`), ALL CAPS, 2-6 words (4-6 is the best band in the eden data), ≤ 2 lines. White line 110-130 px and
  yellow `#FFD400` keyword line 160-200 px, 6 px black stroke plus a blurred shadow.
  - **Placement:** left 62 % only. Keep out of the bottom-right 230x90 px (timestamp) and the top-right 120x120 px
    (hover icons).
  - **No Devanagari** (no font installed; big Hindi channels use English or Roman text).
- **Lint (fail = exit 1):**
  - The smallest text cap height is ≥ 9 % of the frame height, so it is readable at 168x94
    (https://creaticalc.com/blog/youtube-thumbnail-mobile-readability) [weak].
  - WCAG contrast ≥ 4.5:1 between the text and its local background.
  - The thumbnail text shares < 50 % of its words with every title variant. Google says title and thumbnail should
    "work together" (https://support.google.com/youtube/answer/12340300) [official].
  - The JPEG is ≤ 2 MB (lower the quality until it fits).
- **Output:**
  - `work/NN/thumbs/thumb_{A,B,C}.jpg`
  - `preview_grid.jpg`: each variant at 360x202 with its paired title in Roboto under it, next to a 168x94 row, as a
    mock of the mobile feed.
  - `thumbs.out.json`: shot, clip, time and source credit. Add "Thumbnail images: ESO/ESA/NASA (CC BY 4.0)" to the
    credits.
- **Upload:**
  - `upload_youtube.py upload … --thumbnail thumb_A.jpg` sets the default (needs a verified channel).
  - The owner adds B and C (and the title variants) in Studio → A/B test at publish time. There is no API for this,
    and private videos can't be tested.

### P1-b: Title rules (add to `science-publish` and `science-script-v2` §1)
- **Packaging first:** at topic time write 3 title + thumbnail concepts. If none passes a one-second glance test, drop
  the topic (MrBeast guide: work starts from title/thumbnail,
  https://www.tubefilter.com/2024/09/17/mrbeast-internal-production-guide-leaked-key-points/).
- **Front-load:** the hook sits in the first ~45 characters. Branding/language tag goes last, ≤ 60 characters total.
  Limit ALL CAPS and emoji (https://support.google.com/youtube/answer/12340300) [official].
- **Write 3 titles** for the A/B test:
  - **T1 search:** the outlier's proven keyword, verbatim.
  - **T2 browse:** a curiosity gap plus a concrete number. The number must be true, never "explained" or "one of
    the most".
  - **T3 language test:** a Hinglish (Roman) version.
- **Language:** keep English as the default title. No rigorous study compares Hindi/Hinglish/English CTR (all sources
  are vendor blogs [weak]). The biggest Hindi-audio science channels title in English: Getsetfly
  ("Indian Origin Scientist finds Biggest Alien Life Evidence on K2-18B Planet", 7M,
  https://vidiq.com/youtube-stats/channel/@getsetfly/videos/-Yjd0-ZeM2w/), Dhruv Rathee ("Black Holes Explained | They
  are not what you think they are!") and FactTechz. Indian searchers type Roman Hinglish
  (https://capsai.co/blog/ultimate-keyword-research-and-youtube-seo-secrets-for-creators) [weak]. Our own T3 test
  settles it for this channel.
- **Shorter tag:** "| Hindi Documentary" → "(Hindi)" when space is tight. YouTube already knows the audio
  (`defaultAudioLanguage: hi`).

### P1-c: Pinned comment = engagement; credits by link
Pin the poll (one pin per video, https://support.google.com/youtube/answer/6000964 [official]). Move the item-by-item
credits behind a URL in the description. CC BY 4.0 §3(a)(2) allows attribution "by providing a URI or hyperlink to a
resource that includes the required information" (https://creativecommons.org/licenses/by/4.0/legalcode.en)
[official]. Host `credits_full.txt` as a stable page (a gist, or the file in this public repo; the owner chooses).
Fix the 403 by re-authing with the `youtube.force-ssl` scope already in `SCOPES`.

### P2-a: `youtube.md` template changes
```
**Titles (A/B)**   T1 / T2 / T3, each ≤ 60 chars, hook in first 45
**Thumbnails (A/B)**  A / B / C: image idea + text, pairing with T1-T3
**Publish**  <date> 18:00 IST (upload private ≥ 24 h earlier, thumbnail set, test started at publish)
**Description**  line 1 = hook with the keyword (not the title); line 2 = one Hinglish line
                 ("Universe ki sabse darawni jagahein, Hindi mein"); chapters; credits + full-credits URL; 3 hashtags
**Tags**  ≤ 12: keyword, Hindi forms, misspellings only
**Pinned comment**  the poll
**End screen**  video to link + "best for viewer"
```
- **Tags:** "tags play a minimal role", and are useful mainly for misspellings
  (https://support.google.com/youtube/answer/146402) [official].
- **Chapter titles:** make them searchable phrases ("Magnetar: The Star That Hit Earth"). Google shows chapters as
  Key Moments only on videos that already rank (https://influencermarketinghub.com/youtube-chapters-key-moments/)
  [weak]. Keep chapters: they cost nothing.

### P2-b: End-screen tail
Add `"tail": 18` to `edit.base.json`. `render_v3.py` holds music plus slow, darkened footage for 18 s after the last
word, with two empty safe boxes (left and right thirds) for Studio elements. The owner links the best-performing
long video plus "Best for viewer". End-screen click-rate benchmarks are 2-10 % [weak], but the tail costs nothing.
The rule "no intro" is untouched.

### P2-c: Upload timing
Publish 18:00-19:00 IST, ahead of the 19:00-23:00 Indian evening peak that most guides cite
(https://www.wscubetech.com/blog/best-time-to-post-on-youtube/) [weak]. Use the existing `--publish-at` (12:30 UTC).
After 3 public videos, replace this with Studio → Audience → "When your viewers are on YouTube".

### P2-d: Measure our own packaging
Add `upload_youtube.py stats <video_id>` using the YouTube Reporting API reach report: `video_thumbnail_impressions`,
`video_thumbnail_impressions_ctr` by traffic source
(https://developers.google.com/youtube/reporting/v1/reports/full_report_list) [official]. This needs a new
`yt-analytics.readonly` scope, which means an owner re-consent. Write `productions/NN/stats.md` at 48 h, 7 d and 28 d,
including the A/B result. Feed it into topic picks.

### P2-e: Topic method (science-script-v2 §1)
- **Score:** outlier ratio (views ÷ channel *median*, the robust baseline,
  https://1of10.com/chrome-extension) × Hindi gap. Require **≥ 2 independent outliers** (two channels) or ≥ 10x.
  Weight the last 24 months.
- **Gates:**
  - The packaging-first gate (P1-b).
  - 4K footage exists in our sources for the thumbnail's hero image.

### P3
- Hindi `localizations` (Devanagari title/description) in the upload call for Hindi-UI viewers. Vendor case studies
  claim gains from translated metadata (https://air.io/en/creators-spotlight/51m-views-growth-with-ai-translated-metadata-and-subtitles)
  [weak].
- Decide on captions (pending since 03).

## 3. Video 08 "The Scariest Places in the Universe": three title + thumbnail pairs (for one A/B test)

All three come from facts in the script's fact-check table and from shots that are in the cutlist.

| | Title (≤ 60) | Thumbnail |
|---|---|---|
| **A** (search, proven keyword) | The Scariest Places in the Universe \| Hindi Documentary | Magnetar frame (glowing star, field lines), focus right. Text: `IT HIT EARTH` / yellow `FROM 50,000 LY` (SGR 1806-20, Dec 2004). |
| **B** (browse, number) | 9 Places in Space That Should Scare You (Hindi) | Deep-field frame with a radial dark mask over the centre (an illustration of the Boötes Void, our own graphic). Text: yellow `NOTHING` / `330 MILLION LY WIDE`. |
| **C** (language test) | Universe ki Sabse Darawni Jagahein \| Hindi Documentary | Black hole frame with warped starlight (the cold-open shot `eso_eso2105b#1`). Text: `100 MILLION` / yellow `HIDING IN OUR GALAXY` (an estimate, as in the script). |

Run the test as "Title and thumbnail" from publish. If it ends "Performed same", keep A (the outlier's keyword), then
re-test C's title alone with A's thumbnail, to isolate the language effect. Pinned comment: the existing poll.
Credits: by URL (P1-c).
