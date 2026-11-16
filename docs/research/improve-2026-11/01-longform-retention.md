# Long-form retention and pacing (11-13 min Hindi space documentaries), 2026-11-16

Scope: what keeps viewers watching (average view duration, the Intro metric, mid-video dips, the ending),
measured against video 08 (11:02): its `cutlist.json` (205 items, 45 overlays, 104 SFX), script and edit files,
plus web research. Most retention advice online comes from vendors and creators, not studies. Only YouTube's
own docs and the peer-reviewed study are solid; test the rest on our own retention graphs (P1-1).

## 1. Where video 08 and the pipeline fall short

| # | Gap | Evidence in the repo |
|---|---|---|
| a | **Nothing reads YouTube retention data.** The OAuth scopes are upload and force-ssl only. | `upload_youtube.py:29`. 05 has been public since 1 Nov, so its data exists. |
| b | **The title's promise comes late.** "Scariest places" is first said at **25.8 s** (style-guide target: under 1 s). The opening teases only chapter 1, never chapters 2-9. | `edit.spec:19`; `docs/style-guide.md:29,34` ("2-3 teaser numbers… from later facts") |
| c | **The hook slows after 4 s.** Six flash cuts, then 3.8-6.4 s scenes (a 6.4 s Hubble shot at 0:19). | cutlist items 0-11; `render_v3.py:33-35` (one target for all sections) |
| d | **Text thins out.** Overlays/min 4-7 in min 0-6, then 2, 3, 4, 1. No text, card or graphic for 30 s+ at **5:41, 6:58, 9:19**. | `cutlist.json` |
| e | **Below our own targets:** 1 key line (30-40), 11 headlines (12-25), 9 SFX/min (18-25). The check prints them but never fails. | `science-edit-plan/SKILL.md:130-140`; `assign_shots.py:167-176` |
| f | **All 17 number cards are `hero`**, though `mograph.py:401-727` has eight other templates. | `cutlist.json` |
| g | **Five slow drone beds in a row** (Long Note Three … Four) cover 5:07-11:02, where retention sags. | `edit.base.json:65-83` |
| h | **Concrete scares first, abstraction after.** Magnetar (2:00) and TON 618 (4:20), then 5:07-9:50 is voids and flows, with chapter 8 ending "the flow may never have existed". | `script.txt:7-27` |
| i | **ch5 and ch7 open on context** ("Earth Suraj ke chakkar lagati hai…", 380,000 years). | `script.txt:17,23` |
| j | **Uniform rhythm:** 94 sentences, mean 19.9 words, only 8 of ≤8 words; **36 runs** of three within ±5 words, against §3b "never three of the same length". Unchecked. | `science-script-v2/SKILL.md:129-130` |
| k | **No room for an end screen:** the video ends 3 s after the last word. | `render_v3.py:158` |
| l | **No real people:** no archive clips, recordings or portraits, against the 10-20 clips rule. | `productions/README.md`; `"pin": {}` |

## 2. Prioritized improvements

### P1: highest expected impact, automatable

**P1-1. Retention feedback loop (`scripts/youtube/retention.py`).**
- **Evidence:** YouTube's Key Moments report gives Intro (share still watching at 30 s), Dips, Spikes and Top
  moments, and compares each video with "your 10 latest videos of similar length"
  ([YouTube Help](https://support.google.com/youtube/answer/9314415)). The Analytics API exposes the same curve:
  `elapsedVideoTimeRatio` × `audienceWatchRatio`, `relativeRetentionPerformance`, with a `video==ID` filter and
  the `yt-analytics.readonly` scope ([API docs](https://developers.google.com/youtube/analytics/channel_reports)).
- **Change:**
  - Add `https://www.googleapis.com/auth/yt-analytics.readonly` to `SCOPES` (`upload_youtube.py:29`). The owner signs in once more.
  - New `retention.py <video_id> productions/NN`: pulls the 100-point curve and converts each ratio into a
    timestamp. It joins each point with `cutlist.json` (`caps` = the line spoken, `items` = the shot and kind,
    `ovl` = on-screen text).
  - It writes `productions/NN/retention.md`: Intro %, the 5 steepest drops, spikes, relative band.
  - Run on 05 now, then on each video 7 and 28 days after publishing; act on patterns seen in 2+ videos
    (Galloway: don't over-react to micro dips, [summary](https://youtubesummary.com/summary/AX3dEGjBg6w)).
- **Impact:** makes every other item testable; no ElevenLabs credits.

**P1-2. The first 30 s confirms the title and previews the whole ride.**
- **Evidence:** YouTube says a high Intro means the content "matched the viewer's expectation" of the title and
  thumbnail ([Help](https://support.google.com/youtube/answer/9314415)). A "false start" that only restates the
  title, or a bland opening, makes viewers skip or leave
  ([Blackman](https://georgeblackman.substack.com/p/5-retention-killing-youtube-mistakes)). The MrBeast
  production guide calls the first minute "the most important minute"
  ([Gigazine summary](https://gigazine.net/gsc_news/en/20240917-mrbeast-youtube-production)). Galloway's test:
  the first ~30 s should work as a Short on its own.
- **Change:**
  - **Script** (`science-script-v2` §2/§3b): opening = strongest fact → a third-person line naming the
    title's words by 8 s → **2-3 one-line teasers from later chapters** (a dead star that shook Earth from
    50,000 ly; a black hole 20 Neptune orbits wide; a hole 330 million ly across) → the long open loop.
    This restores style-guide §1's teaser rule.
  - **Edit:** each teaser gets a 2 s `V` beat and an `over` number card.
  - **Renderer:** in `render_v3.plan()`, `opening` scenes get `TARGET` 2.2 s and `MAX_SCENE` 4.0 s (now 3.0 / 6.5).
- **Impact:** the largest lever on Intro %, the steepest part of every curve.

**P1-3. Dead-zone lint in the plan-only check.**
- **Evidence:** the same practitioner guides say "re-hook or change format every 60-90 s", but they disagree on
  how often the picture should change (2-30 s)
  ([OutlierKit](https://outlierkit.com/resources/youtube-hooks-and-retention/),
  [AIR](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8)).
  Mayer's signalling principle: highlighting the essential words helps; duplicating the full narration as text
  hurts ([Mayer et al. 2001](https://www.csus.edu/indiv/e/eppersonm/hist107/documents/mayer,%20heiser,%20&%20lonn%20(2001).pdf)).
  That supports our "key phrases + CC" design, but only if the key phrases are actually present.
- **Change:** a `scripts/video/pace_lint.py` run by `pipeline.sh … edit` (or in `assign_shots.py` after line
  176): every 20 s window needs ≥1 visual event (K, big C, N, G, L, photo, whip/flash/dip); print a per-minute
  histogram; exit 1 (override `--allow-gaps`) on a 30 s gap, or when key lines < 15 or headlines < 12.
- **Impact:** removes 08's dead zones and the thin last third, where curves slope fastest.

### P2

**P2-4. Use the full number-card kit.**
- **Evidence:** in a study of 306 science videos, the most-viewed ones had more "moments of change"
  (V = 0.24) and higher emotional arousal ([Frontiers 2020](https://www.frontiersin.org/articles/10.3389/fcomm.2020.581349)).
  Curious Space's breakout animates every number with a persistent frame (`docs/research/curious-space/`).
- **Change:** the edit-plan skill rule and the P1-3 lint: `hero` ≤ 50% of N cards. Map the type of claim to a template:
  - ratio → `scale` (quasar ×1,000)
  - "A = B" → `equation` (0.1 s = 100,000 years of the Sun; TON 618 = 20 Neptune orbits)
  - speed or travel → `route`/`line` (600 km/s = Earth to the Moon in 11 min)
  - "60 of thousands" → `progress`/`gauge`
  - a spot in the shot → `callout` (the cold spot on `cmb_map`, SGR 1806-20)
- **Impact:** visual novelty in minutes 5-10 at no footage cost.

**P2-5. Chapter openers in medias res, plus a midpoint re-hook.**
- **Evidence:**
  - Bland openers lose viewers (Blackman).
  - YouTube advises moving top moments earlier because "audience sizes typically decrease" (Help).
  - The MrBeast guide puts the most exciting content in minutes 3-6.
- **Change (science-script-v2 §2):** each chapter's first sentence is its strangest concrete claim, context
  second (ch5: "Milky Way is pal 600 km har second ki raftaar se kisi andekhi cheez ki taraf bhaag rahi hai").
  At about 50%, a callback to the opening's open loop. One concrete Earth/human-stakes chapter in each third;
  a debunked chapter (dark flow) never sits right before the ending.
- **Impact:** flatter middle slope.

**P2-6. Music energy curve.**
- **Evidence:** arousal was the strongest predictor of popularity (OR ≈ 3, Frontiers).
- **Change:** tag each `$MEDIA/music` track `energy` low/mid/high in a small catalogue JSON; `make_edit.py`
  warns on 3 low cues in a row and wants a mid/high cue at the midpoint and the last chapter. Keep the 16 LU bed.
- **Impact:** keeps the second half from feeling like a wind-down.

**P2-7. End-screen tail and a story bridge to the next video.**
- **Evidence:** "leave enough space and time at the end… for an end screen", which appears in the last 5-20 s
  ([YouTube Help](https://support.google.com/youtube/answer/6388789)). Recaps and "wrap-up" signals make viewers
  leave early (Blackman; [AIR](https://air.io/en/youtube-hacks/how-to-read-youtube-retention-graph)).
- **Change:** `edit.base.json` `"end_tail": 12`, which `render_v3.plan()` adds to `total` (line 158) as a
  last `{hold}` shot with a music swell: no text, no spoken CTA. `science-publish` sets the end screen to one
  video, ideally the sequel ("how the universe will end", the next pick in `old-hits-2026-11.md`); a subscribe
  element is the owner's call. The last line stays a story beat, never a recap.
- **Impact:** session time and next-video views; the closing line stays uncovered.

### P3

- **P3-8. Rhythm check in `script_check.py`.** Flag 3 sentences in a row within ±5 words, and any reveal without
  a short (≤8 words) punch line. Keep the owner's flowing sentences: add short lines, don't shorten long ones.
- **P3-9. Recalibrate the SFX target.** Change 18-25/min to 10-15/min, tied to visual events. 08 ran 9/min, the
  owner calls dense SFX over-editing, and the practitioner backlash against heavy retention editing agrees
  ([vidIQ](https://rosetta.to/u/vidiq/retention-editing-is-dead)). This makes the target honest; it doesn't add more SFX.
- **P3-10. Real people when photos fail.** If Wikimedia won't serve a portrait, use NASA/JPL portraits or NASA
  SVS interview clips (the 05 rule). Fall back to an `L` card over a `hud` of the actual telescope instead of
  generic observatory footage.
- **P3-11. Length.** Keep 11-13 min and never pad. Duration didn't separate most- from least-viewed science
  videos (Frontiers). Vendors agree that percentage retention beats raw length
  ([AIR](https://air.io/en/youtube-hacks/what-is-the-best-length-for-a-youtube-video)).

## 3. Do not do
- **Owner's rules:** no channel intro, no title card, no gap after the opening. No viewer address or questions,
  no "aaj hum jaanenge", no spoken like/subscribe. No `M` moments, "..." holds or suspense stops. Teasers stay
  third-person statements, never "aage dekhenge".
- **The ending:** no recap, "in conclusion" or "thanks for watching". No outro card before the last line.
- **Promises:** never tease something the video doesn't deliver (Type II clickbait,
  [Veritasium](https://www.veritasium.com/videos/2021/8/17/we-need-to-talk-about-clickbait)). Never present
  disputed science (dark flow, bubble collisions) as settled to raise the stakes.
- **Shorts style in long-form:** no Shorts-v2 zoom punches, glitch transitions or typing SFX on every text.
  Typing stays at 1-2 moments per video.
- **Other people's material:** no other channel's footage, music or graphics. No thumbnail unless asked.
  Uploads stay private until the owner publishes.
- **Owner sign-off:** script changes from this note apply to the **next** video's script, approved by the
  owner. Don't re-record 08 or spend ElevenLabs credits without asking. Edit-only items (P1-3, P2-4, P2-6,
  P2-7) can be re-cut into 08 without new narration if the owner wants.
- **Over-reacting:** don't rebuild the format because of one video's dip. Confirm it on 2+ videos (P1-1).
