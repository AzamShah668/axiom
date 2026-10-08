# Breakdown #1 — "How Big is The Universe?" (Science Time)

| | |
|---|---|
| Video | https://www.youtube.com/watch?v=pSHVbLPWA28 |
| Uploaded | 2024-02-03 |
| Performance | 15.16M views · 167K likes · 13.5K comments (Oct 2026) |
| Length | 11:09 · 30 fps · 16:9 |
| Channel | @ScienceTime24 · 1.16M subscribers · 263 videos |

How this was measured: the video was downloaded via Apify (480p), shots were detected with PySceneDetect, frames were sampled every 2 s, voice and music were split with Demucs, and loudness was measured with EBU R128. Every number below comes from the actual file, not from guesswork.

---

## TL;DR — the formula

1. **One continuous "zoom-out ladder".** It starts on the ground on Earth and climbs 14 rungs: Moon → Sun → Mars → Neptune → Voyager 1 → Oort Cloud → Alpha Centauri → Milky Way → Local Group → Virgo → Laniakea → Observable Universe → beyond. Each rung gets about 30–60 s.
2. **Every rung follows the same 5 beats:** a transition line, the name and distance, a relatable comparison (car, jet, light, Voyager), one "wow" fact, then a humbling reflection.
3. **Every number spoken appears on screen within about 1 s** as plain white text, usually km on one line and mi below.
4. **The visuals are about 90% free material:** NASA/ESO/Wikimedia stills and animations, plus space-simulator flythroughs, plus simple self-made scale infographics (a line, an icon and a label).
5. **Slow, calm edit.** About 6 cuts per minute (median shot 7 s, some shots last 30–48 s). The picture never sits still, because stills always get a slow zoom.
6. **Almost no music.** There is a cinematic bed only for the 36 s cold open. After that the narration runs over a near-inaudible deep space drone, with a soft "pop" sound on every label and a whoosh or boom at each jump in scale.
7. **No intro, no sponsor, no subscribe ask, no outro.** Narration starts at 0:04 and ends at 11:05.

---

## 1. Packaging

**Title:** a 4-word question, *How Big is The Universe?*, with no clickbait words and no numbers.

**Thumbnail** (1280×720):
- The left ~55% is pure black. On it sits a 3-line title in a huge, heavy, rounded white display font: `HOW BIG` / `— is the —` (small, between two thin dashes) / `UNIVERSE?`.
- The right ~45% is a curved slice of a log-scale "whole universe" illustration (in the style of Pablo Carlos Budassi's famous image): the cosmic web glowing orange, galaxies, and a red edge.
- No face, no arrows, no red circles. Only two elements and very high contrast.

**Description:** about 200 words in five short paragraphs that retell the journey and name every keyword (Moon, Sun, Mars, Neptune, Voyager 1, Oort Cloud, Alpha Centauri, Milky Way, Local Group, Virgo Supercluster, Laniakea, Great Attractor, observable universe). That is followed by one subscribe link and 3 hashtags (`#universe #sciencetime #space`). There are no chapters, no footage credits and no music credits.

**Captions:** the creator uploaded an English caption track (marked "user_generated"). It looks auto-transcribed, with lowercase text and misspelled names such as "lanaka" and "ort Cloud".

---

## 2. Script

### Numbers
- **1,599 words in 11:05 of narration, about 144 words per minute**, steady from start to end.
- The narrator talks for 83% of the runtime. The median pause is 0.5 s and 90% of pauses are 0.8 s or shorter. Only **2 pauses in the whole video are longer than 1.5 s**, so there are no dramatic silences; it is one continuous documentary read.

### Section map (the ladder)

| # | Time | Rung | Numbers spoken | Relatable comparison | On-screen text |
|---|---|---|---|---|---|
| 1 | 0:00–0:36 | **Hook — Earth** | — | "everyone you ever knew, every human who ever lived" (a Carl Sagan callback) | `EARTH`; title card `HOW BIG IS THE UNIVERSE?` at 0:36 |
| 2 | 0:36–1:13 | Moon | 384,000 km | car at 100 km/h → 160 days | `384,399 km / 238,854 mi`, `100km/h`, `160 days`, `Apollo 11 Mission Image A.K.A Earth Rise` |
| 3 | 1:13–2:03 | Sun | 1 AU = 150M km; light takes 8 min 20 s | jet at 900 km/h → 19 years | `The Sun`, `The Earth`, `1 AU`, `149,000,000 km`, `300,000 km/sec`, `19 years`, `Earth to Scale` |
| 4 | 2:03–2:50 | Mars | 54.6M–401M km | jet → 50 years | `opposition`, `closest approach`, `401 million km`, `50 years For Max Distance` |
| 5 | 2:50–3:18 | Neptune | 4.5B km; light takes 4 h 15 min | — | `Neptune`, `4.5 Billion km` |
| 6 | 3:18–4:16 | Voyager 1 + Pale Blue Dot | 1977; 22B km; photo taken from 6B km | — | `Voyager-1`, `"Pale Blue Dot"`, `6 Billion km` |
| 7 | 4:16–5:08 | Oort Cloud + heliopause | 100,000 AU (they say "1.9 ly", but it is really about 1.6 ly) | — | `Oort Cloud`, log-scale AU axis, `Heliosphere / Interstellar Space` |
| 8 | 5:08–6:11 | Alpha Centauri | 41.3 trillion km = 276,000 AU = 4.4 ly | Voyager at 17 km/s → 70,000 years | `41.3 Trillion km`, `276,000 AU`, `17 km/s`, `70,000 years` |
| 9 | 6:11–7:08 | Milky Way + radio bubble | 100,000 ly; 100 ly bubble | "our entire recorded history is but a whisper in the cosmic wind" | `The Milky Way`, `100,000 light-years in diameter` |
| 10 | 7:08–8:07 | Local Group | 50+ galaxies, 10M ly | light takes 10M years to cross it | `10 Million Years` (sic, should be light-years) |
| 11 | 8:07–8:42 | Virgo Supercluster | 110M ly / 33 Mpc | — | `110 Million Light Years / 33 Megaparsecs` |
| 12 | 8:42–9:53 | Laniakea + Great Attractor | 500M ly; mass of 10¹⁷ Suns | "Laniakea = immense heaven in Hawaiian" | `LANIAKEA`, `500 Million Light Years`, `LOCAL SUPERCLUSTERS` |
| 13 | 9:53–10:26 | Observable Universe | 93B ly vs 13.8B years old | sets up a paradox, then answers it with cosmic expansion | `OBSERVABLE UNIVERSE`, `93 Billion Light Years` |
| 14 | 10:26–11:09 | Beyond | regions receding faster than light; possibly infinite | humbling close | `Observable Universe ≠ Entire Universe` |

### The 5-beat rung formula (copy this exactly)
1. **Transition line.** These are reused with small variations: "As we continue our outward journey…", "Venturing beyond…", "As we journey to the outermost reaches…", "Our journey now takes us to…", "As we leave the Milky Way…", "As we extend our cosmic gaze…", "As we reach the boundaries of…"
2. **Name + distance.** Give the distance in the unit that fits the scale. The script switches units on purpose as the numbers grow (km → AU → light-years → megaparsecs) and **says why it is switching** ("the AU… begins to lose its practicality, hence astronomers use the light-year").
3. **Relatable conversion.** Car → jet → speed of light → Voyager. The "vehicle" gets faster as the distances grow, so the travel times stay absurd.
4. **One wow fact or famous image:** Earthrise, Pale Blue Dot, the radio bubble, the meaning of "Laniakea", the Great Attractor.
5. **Humbling reflection.** Fixed vocabulary: *vast, immense, staggering, humbling, cosmic ocean, tiny speck, fragile, profound, a stark reminder*.

### Hook (0:00–0:36)
- The camera rises from farmland to orbit while the narrator paraphrases Sagan: "Earth, our home planet, a tiny blue dot floating in the immense cosmic ocean. Here resides everyone you ever knew…"
- It then states the promise: "…we embark on an epic quest — a quest to grasp **the true scale of our universe**."
- The title card appears only **after** the promise, at 0:36.

### Ending
It ends on an unresolved mystery plus humility: "there might always be regions of space… that we will never witness as they retreat endlessly into the depths of the ever-expanding universe." Then there is a 3 s fade and the video stops. There is no CTA.

### Style notes
- The text reads like LLM-written documentary prose (stock adjectives, symmetrical sentences), which shows the script itself is not the moat.
- There are small factual slips: the Oort Cloud distance in light-years, and "10 Million Years" used as a distance label. **Our version must fact-check every number.**

---

## 3. Visuals — what is on screen and where it comes from

The source is identified from what is visible in the frames. Confidence is high where a known asset is recognisable, and marked "likely" otherwise.

| Time | What is on screen | Source (identified / likely) | Free equivalent for us |
|---|---|---|---|
| 0:00–0:24 | Continuous rise from farmland → clouds → orbit, with `EARTH` label | **Google Earth Studio** (photogrammetry look) | Google Earth Studio (free; requires an on-screen Google attribution) |
| 0:24–0:36 | Earth shrinks, the camera flies through stars, warp streaks, title | Space-simulator flight (SpaceEngine-type) plus stock hyperspace | SpaceEngine / Celestia (free) recording |
| 0:38–0:48 | Moon and Earth 3D renders; Moon "emerges" from behind Earth for the size comparison | 3D renders (likely SpaceEngine or NASA CGI Moon Kit) | NASA SVS CGI Moon Kit + Blender, or SpaceEngine |
| 0:48–0:58 | **To-scale infographic:** black background, Earth and Moon dots, a thin white line, a car icon moving along it, labels | **Custom-made** (After Effects/Keynote-level) | Generate in code (node-canvas / Remotion) |
| 0:58–1:12 | Earth over the lunar horizon → Apollo 11 "Earthrise" photo with labels | Render + **NASA photo** | NASA (public domain) |
| 1:12–1:50 | Sun vs Earth size, `1 AU` line, eclipse render with light-speed label, jet icon | Custom infographic + space render | Code + SpaceEngine |
| 1:50–1:56 | Lit 3D solar system | Stock or space simulator | SpaceEngine / Pixabay |
| 1:56–2:04 | Solar prominence with tiny "Earth to scale"; sun disk with sunspot | **NASA SDO** | NASA SDO / SVS (PD) |
| 2:06–2:24 | 2D orbit diagram: Earth/Mars orbits, opposition, closest approach | Custom 2D diagram | Code |
| 2:38–2:50 | Mars 2020 cruise stage, Mars surface, entry heat-shield | **NASA/JPL animations** | NASA/JPL (PD, credit) |
| 2:52–3:02 | Neptune vs Earth, then a distance line | Custom | Code + planet renders |
| 3:04–3:18 | Neptune light curve (green graph), orbit animation | **NASA Kepler/K2 animation**, NASA orbit visual | NASA |
| 3:20–3:30 | 1977 Voyager launch, grainy, split-screen, pillar-boxed | **NASA archival film** | NASA (PD) |
| 3:32–3:44 | Voyager-1 trajectory leaving the heliosphere grid | **NASA Eyes on the Solar System**-style visual | NASA Eyes (free web app) |
| 3:46–3:52 | Rotating Voyager model | NASA 3D model render | NASA 3D Resources + Blender |
| 3:54–4:14 | **Pale Blue Dot** with a slow push-in and labels | **NASA/JPL-Caltech** (2020 reprocessed) | NASA (PD) |
| 4:16–4:36 | Glitch into `Oort Cloud`, then a pan along a log-scale AU axis (Heliopause, Voyager 1, α-Centauri) | **NASA/JPL-Caltech** Oort-cloud scale graphic | NASA |
| 4:38–4:54 | Heliosphere, termination shock, heliopause with "Jun 21, 2008" date stamps | **NASA Goddard SVS** | NASA SVS (PD) |
| 4:56–5:04 | Solar-system poster; colourful Oort-cloud illustration | Stock / artist illustration | Make our own or use NASA |
| 5:06–5:50 | Constellation lines → Alpha Centauri marked with arrows; fly-in; Proxima b transit; zoom from the Milky Way into α Cen | **ESO animations** (ESO/M. Kornmesser, ESO/DSS2 zoom) | ESO (CC BY 4.0, credit required) |
| 5:52–6:02 | Voyager next to the triple star with speed and time labels | Custom composite | Code |
| 6:10–6:22 | Annotated Milky Way map shrinking, `100,000 light-years` scale bar | **NASA/JPL-Caltech/R. Hurt** Milky Way illustration | NASA/JPL (credit) |
| 6:26–6:34 | Milky Way with zoom-inset boxes down to the "human radio bubble" | Adam Grossman / Planetary Society radio-bubble graphic (*not* free) | Make our own inset zoom on the NASA Milky Way map |
| 6:36–7:20 | **47 s continuous flight** out of the Milky Way → galaxy disk → Andromeda | **Space simulator** (SpaceEngine-type) | SpaceEngine recording |
| 7:22–7:50 | 3D Local Group map with blue rings, labels, scale bar | **Andrew Z. Colvin maps (Wikimedia Commons)** | Wikimedia (CC BY-SA, credit) |
| 7:52–8:12 | Dense galaxy field | Space simulator | SpaceEngine |
| 8:14–8:58 | Virgo Supercluster map → Laniakea "cylinder" map zooming out, vertical `LANIAKEA` label | **Andrew Z. Colvin maps** | Wikimedia (CC BY-SA) |
| 9:00–9:22 | Hyperspace star streaks | Stock / space simulator | SpaceEngine / Pixabay |
| 9:24–10:10 | Local superclusters → observable-universe maps, `93 Billion Light Years` | **Andrew Z. Colvin maps** | Wikimedia (CC BY-SA) |
| 10:13–10:20 | Pink/white flash → Big Bang / galaxy formation | Light-leak overlay + NASA/ESA visualisation | Free light-leak + NASA |
| 10:22–10:50 | Zoom out from Earth through orbits to an "observable universe" sphere, with the `≠` text | Space simulator / Universe Sandbox-type | SpaceEngine |
| 10:52–11:09 | Fast closing montage: Earth+Sun, Saturn, Pillars of Creation fly-through, galaxy collision sim, deep field | Space sim + **NASA/ESA/Hubble/Webb** | NASA / ESA (CC BY) |

**Approximate mix of the runtime:**
- about 45% space-simulator flights and renders
- about 30% NASA/ESO/ESA/Wikimedia stills and animations
- about 20% self-made scale infographics
- about 5% archival film

> **Key insight for us:** the rungs repeat from video to video. Earth, Moon, Sun, planets, Milky Way, galaxies and superclusters show up in almost every space video this channel makes. Build the library **once** (record SpaceEngine flights, download the NASA/ESO/Colvin assets) and every later video mostly re-uses it. That is how we out-publish a channel that uploads a few times a year.

---

## 4. Editing

### Cut rhythm
- **67 shots in 669 s** (70 counting a few soft cuts): **median 7.0 s, mean 10 s**. The longest shots are 48 s (the opening zoom-out), 47 s (the flight out of the Milky Way) and 38 s (the Laniakea zoom-out).
- Cuts per minute, minute by minute: 3 · 6 · 5 · 9 · 10 · 6 · 5 · 3 · 4 · 7 · 8.
  - The busiest stretch is Voyager/Oort, where there are many short NASA clips.
  - The calmest is intergalactic space, where long continuous zooms carry the sense of scale.
- **The picture is almost never static.** Only 13 frozen stretches of 1.5 s or more appear in 11 minutes. Every still (photos, maps, posters) gets a slow push-in or pull-out, and every map ends with a **zoom-out that "reveals" the next scale**.

### Transitions
About 90% are **hard cuts**. Special transitions only appear at scale boundaries:

| Transition | Where | How to reproduce |
|---|---|---|
| Hyperspace / star-streak flight | 0:30, 6:36, 9:00 | SpaceEngine high-speed flight or a stock warp clip |
| Whip slide with motion blur | 1:28 (Sun infographic → eclipse) | FFmpeg `xfade=transition=slideleft` + `gblur`/`tmix` |
| Digital glitch | 4:16 (Pale Blue Dot → Oort Cloud) | Glitch overlay clip, or FFmpeg `xfade` + `noise`/`rgbashift` |
| White-pink flash + boom | 10:13 (into the Big Bang) | Light-leak overlay plus an impact SFX |
| Object emerges from behind another | Moon from behind Earth (0:48), Sun behind Earth (1:12) | Layered PNG animation |
| Label scales down to nothing before the cut | 2:24 | Animate text scale 1 → 0 over about 0.3 s |

### On-screen text
- **Font:** a condensed bold sans (Oswald/Anton family), white, with a soft drop shadow. There are **no boxes, no backgrounds and no colours**.
- **Placement:** next to the object being described, or centred. Distances are always 2 lines: `384,399 km` over `238,854 mi`.
- **Scale bars:** a thin white line that grows from the centre, with a label underneath (`100,000 light-years in diameter`, `500 Million Light Years`).
- **Infographics:** pure black background, objects to relative scale, a 1–2 px white line, a tiny white vehicle icon (car or airplane) that moves along the line, and a time label.
- **Labels on maps** (Oort Cloud, LANIAKEA, LOCAL SUPERCLUSTERS, OBSERVABLE UNIVERSE) are set in a lighter, wider sans, sometimes vertical along the edge of the map.
- **Animation:** fade or scale in. Some labels use a quick character-scramble reveal (2:30).
- **Not used:** burned-in subtitles, face cam, channel logo watermark, intro sting, lower thirds, end card, and progress bar.

---

## 5. Audio

### Measured levels
| Layer | Level | Notes |
|---|---|---|
| Final mix | **−16.7 LUFS** integrated, LRA 3.7 LU, peak +0.1 dBFS | Very consistent, heavily compressed, and slightly hot (no true-peak limiter) |
| Voice | −16.8 LUFS, LRA 3.6 LU | The voice is the whole mix |
| Music in cold open (0:00–0:36) | about **17 dB under the voice** | Cinematic bed. Fades in from silence over about 1.5 s and drops out when the title card hits |
| Background in the body (0:40–11:05) | about **33 dB under the voice** (−52 dBFS RMS in narration gaps) | A **deep sub-bass drone**: energy sits in 20–250 Hz, almost nothing above 1 kHz, very tonal. You feel it more than hear it, and on phone speakers it is effectively silent |
| Label "pop" SFX | about −35 dBFS peak, the **same level every time**, ~25 hits | Fires on almost every text label (0:43, 0:50, 0:54, 1:06, 1:08, 1:16, 1:24, 1:34, 1:44, 1:48, 2:16, 2:22, 2:30, 2:56, 3:00, 3:58, 4:00, 5:18, 5:23, 5:55, 5:58, 6:14, 6:16, 7:44, 8:24, 8:55, 10:01) |
| Scale-change whooshes / impacts | −25 to −30 dBFS peak | 0:20, 0:37 (title), 1:29 (whip), 2:50 (heat-shield), 3:20 (rocket rumble), 6:24, 6:35–6:42 (warp rumble), 8:14, 9:23, 9:51, 10:51 |
| **Big Bang boom** | **−9 dBFS** peak, 32–86 Hz | The single loudest non-voice moment (10:13) |
| Ending | Ambience fades out over about 3 s after the last word | Then hard stop |

**So the emotion is carried by the voice plus the visuals plus small sound-effect accents, not by music.** That makes it cheap to copy and safe from Content ID.

### Voice
- Deep male voice: median pitch **94 Hz**, pitch movement ±4.4 semitones (calm but not robotic).
- 144 words per minute, short regular pauses (median 0.5 s), clean, close-mic'd, no room sound, compressed hard.
- Calm, awe-filled documentary read, with no hype and no shouting.

---

## 6. Recipe for our Hindi version

### Script
- Use the same 14-rung ladder and 5-beat formula, with about 11 minutes of narration. Time it from the TTS output, not from word count, because Hindi runs longer than English for the same content.
- **Numbers, spoken the Indian way:**
  - 3 लाख 84 हज़ार किमी
  - 15 करोड़ किमी
  - साढ़े चार अरब किमी
  - 41 लाख करोड़ किमी
  - Then switch to प्रकाश-वर्ष (light-year) and say why, exactly like the original does.
- **Localised comparisons** (this is an edge the English channel cannot copy):
  - Chandrayaan-3: launched 14 Jul 2023, landed 23 Aug 2023
  - Mangalyaan: about 10.5 months to Mars
  - Aditya-L1: about 4 months to L1
  - A car on the expressway at 100 km/h, a jet at 900 km/h
  - "Delhi–Mumbai × N"
- Hook: a Hindi paraphrase of Pale Blue Dot, then the promise ("ब्रह्मांड का असली आकार…"), then the title card at about 0:30–0:40.
- Fact-check every number; the original has slips.

### On-screen text (Hindi)
- Labels: **Teko SemiBold/Bold** (Google Fonts). It is a condensed font with both Devanagari and Latin, which makes it the closest match to their Oswald look. Use white with a soft shadow, and **km only** (no miles).
- Thumbnail: **Baloo 2 ExtraBold** (heavy and rounded, with Devanagari), for example `ब्रह्मांड` / `— कितना —` / `बड़ा है?` on black. Put one dramatic space image on the right half.

### Visual sources (all free)
| Source | Use for | Licence |
|---|---|---|
| NASA (images.nasa.gov, svs.gsfc.nasa.gov, JPL Photojournal, NASA 3D Resources, NASA Eyes) | Planets, Sun, Voyager, heliosphere, archival launches | Generally public domain; no NASA endorsement implied |
| ESO (eso.org), ESA/Hubble, ESA/Webb | Alpha Centauri / Proxima animations, nebula fly-throughs, galaxy zooms | **CC BY 4.0**: credit in the description |
| Wikimedia Commons, Andrew Z. Colvin maps | Local Group, Virgo, Laniakea, observable universe | **CC BY-SA 3.0**: credit + share-alike |
| Google Earth Studio | Ground-to-orbit opening | Free; keep the Google attribution on screen |
| SpaceEngine (paid, Steam) or Celestia (free, open source) | All the flythroughs and warp shots | Check SpaceEngine's current terms for monetised use before publishing |
| Pixabay / Pexels | Hyperspace, light leaks, glitch overlays | Free licence |

Unlike the original, **put a credits block in the description**. It costs nothing and protects us.

### Infographics (automatable)
The to-scale scenes are simple enough to generate in code:
- black background
- two planet PNGs at relative scale
- a growing white line
- a moving vehicle icon
- a Teko label

The repo already depends on `canvas` (node-canvas), so frames can be drawn there and encoded with FFmpeg. Remotion is an option if we want React-based templates. One template, `distanceScene({from, to, km, vehicle, speedKmh, label})`, covers about 20% of the runtime.

### Audio (copy it exactly)
- **Voice:** the existing voice-clone TTS in Hindi, calm and deep. Compress and normalise to about −16 LUFS for the voice stem.
- **Cold-open music:** one cinematic/ambient track for the first 30–40 s, about 17 dB under the voice, faded out on the title card. Use the YouTube Audio Library or Pixabay Music (free), or Epidemic/Artlist (paid, safest).
- **Body drone:** we can **synthesise it ourselves**, which is Content-ID-proof. Mix a low sine/saw pad (around 55–110 Hz) with low-passed noise, keep it about 30 dB under the voice, and give it a slow volume swell.
- **SFX:**
  - a soft UI "pop" on every label at a fixed level, about 15 dB under the voice peaks
  - a whoosh on every scale jump
  - a rumble during warp flights
  - one big boom at the climax
  - Sources: Pixabay / Freesound (CC0).
- **Master:** −14 LUFS integrated, −1 dBTP. The original runs hot at +0.1 dBFS peak; don't copy that.

### Edit spec (FFmpeg-friendly)
- 1080p30, median shot length 6–8 s, never static (`zoompan` slow push on every still).
- Hard cuts inside a rung; a special transition (warp, whip, glitch or flash) only between rungs.
- Every spoken number gets a label within about 1 s. Drive this from the TTS word timestamps (we already have `scripts/whisper_extract.py`).
- No intro, no outro card, no subscribe ask in the narration. Use YouTube's end-screen overlay on the closing montage.

---

## 7. Channel-level notes (from this first pass)
- **Their best format is "true scale" / journey-of-scale videos:**
  - *The True Scale Of Modern Nuclear Weapons*: 27M views
  - *How Big is The Universe?*: 15M
  - *80 Years Since Hiroshima*: 12.6M
  - Their many Brian Cox / Neil deGrasse Tyson interview-clip videos mostly sit between 20K and 1M views.
- **Upload pace has collapsed.** Dates confirmed so far are Mar 2024, May 2024, Jun 2024 (×2), Dec 2024 and Aug 2025, plus only two more uploads since. A Hindi channel publishing this format weekly would face no competition on pace.
