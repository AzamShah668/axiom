# Breakdown #1 — "What If We Land On Sun?" (Curious Space)

| | |
|---|---|
| Video | https://www.youtube.com/watch?v=93x3d1E013Q |
| Uploaded | 2026-10-08 |
| Performance | 555K views · 1.7K likes · 108 comments after 12 days (2026-10-20) |
| Length | 11:10 · 29.97 fps · 16:9 |
| Channel | @curiousstudiosofficial · 2.9K subscribers · 9 videos since July 2026; "What If" Ep. 1 (*Agar Sun Gayab Ho Jaye Toh?*) has 604K, every other upload 2K-44K |

How this was measured: downloaded through Apify at 480p (the free plan's $0.20 run cap doesn't pay for
720p at 11 minutes), then `scripts/reference_analysis/analyze_video.sh`:
- PySceneDetect plus our own transition classifier on every cut, with optical flow per shot for camera moves
- EasyOCR every second, refined at 10 fps for text entry and exit
- Demucs 4-stem separation, BS.1770 loudness per stem, music segmentation, and SFX onset detection calibrated
  against the picture (see section 6)
- faster-whisper word timings on the voice stem

Every number below comes from the file. Descriptions of type, layout and animation come from 10 fps frame
strips and full-resolution key frames, which are listed with timestamps.

---

## Summary

| | Curious Space, "What If We Land On Sun?" |
|---|---|
| Format | First-person hypothetical ride: "our spacecraft Agniyaan" flies from Earth through every layer of the Sun to the core |
| Hook | 0:00-1:08: six "impossible" facts as a montage, each with an animated number card; the topic is named in the first second |
| Title | 1:08 "WHAT IF / WE LAND ON SUN" (2.5 s), then 1:14 "PRESENTED BY CURIOUS STUDIOS" (3 s), over a 6.7 s pause in the voice |
| Shots | 203; median 3.0 s, mean 3.3 s, p10 1.4 s, p90 5.3 s, longest 13.8 s |
| Cuts per minute | 18.1 overall; 22 in the hook, 12-13 while landing (7:08-8:55), 23 in the core section (9:40-10:30) |
| Transitions | 96 hard cuts, 30 dips to black, 27 dissolves (mostly fades through black), 21 warm flare flashes, 8 white flashes, 6 whip/zoom/slide |
| Pictures | by eye: about 70% AI-generated cinematic shots (spacecraft, astronaut, cockpit, people, Indian landscapes) and about 15% real NASA SDO solar imagery; measured: 29% of the runtime carries big kinetic type or data graphics |
| Camera on every shot | push-in on 109 of 203 shots (median 3 %/s), pans and tilts, slight roll on 44, shake on 42 |
| Text | 4.4 big animated numbers per minute (49), 15+ count-up counters, thermometers, gauges, progress bars, charts; subtitles only on typographic cards |
| Voice | 134 words/min over the narration (179 while speaking), median pause 0.58 s, only 5 pauses over 1.5 s; bright, energetic young male voice (median pitch 165 Hz, ±5.8 semitones) |
| Music | continuous bed 15 LU under the voice while speaking, 13 LU in pauses (ducking 2.7 dB, i.e. none); about 6 cues that change at act boundaries |
| SFX | about 257 audible effects (23 per minute): 26% of cuts and 37% of text entries carry one; risers into impacts fill the five long pauses |
| Loudness | -19.9 LUFS integrated, true peak about -2.5 dBFS (not normalised to YouTube's -14) |
| Grade | one colour world: orange-gold, very saturated (median HSV saturation 193/255), warm highlights (Lab b* +35), heavy vignette |
| Viewer address | constant: "hum", "aap", questions to the viewer, India-specific comparisons, a recurring on-screen subscribe pill, end screen asking for comments |

---

## TL;DR — the formula

1. **Promise the impossible in the first minute.** 0:00-1:08 is a montage of six facts, each stated as a
   paradox and stamped with an animated number. The Sun is named in the first second. The title only comes
   after the hook.
2. **Turn the topic into a ride with a goal.** "Our spacecraft Agniyaan" (one recurring AI-made design, more
   than 30 shots) has a dashboard for distance and temperature and a special camera. The question is "where
   would we put our feet?", and every section is the next layer down. A footer shows the stage
   ("THE SUN · CHROMOSPHERE … 05 / 07"), and a progress bar says "1%" after the first 15 lakh km.
3. **Every number is a moment.** 49 big number cards in 11 minutes. Numbers count up with an ease-out over
   about 1.3 s and land on the spoken number. They sit beside a thermometer, a speedometer arc, a progress bar,
   a scale or a chart, never as plain text.
4. **Cinematic pictures, one colour.** By eye, about 85% of the shots are AI-generated cinematic images and clips
   plus NASA SDO footage of the Sun, all graded orange-gold. Every shot moves (push-in, pan, roll, shake).
5. **Rhythm from the words.** A cut every 3.0 s (median). 54% of cuts fall in a pause between phrases and 64%
   within 0.2 s of a word start. Kinetic headlines reveal word by word, on the spoken word.
6. **A flat music bed, and sound design in five breaths.** The music never ducks; it sits 15 LU under the
   voice. The long pauses (0:09.6, 0:23.9, 1:06.9, 1:15.0, 9:33.9) get risers, impacts and swells of +11 to
   +15 dB.
7. **Talk to the viewer.** "Agar hum Sun par land karna chahein…", "aapka vajan…", "Delhi se Mumbai", Aditya-L1,
   a subscribe pill that pops up 15+ times, and an end screen asking for comments. Our channel doesn't copy
   this part (see section 8).

---

## 1. Packaging

**Title:** *What If We Land On Sun ? || What If Ep. 2 || Curious Space*. A hypothetical question with the
series name, plus the episode number to create a binge path to Ep. 1.

**Thumbnail** (1280×720, `thumb.jpg` on Drive):
- an AI image of an astronaut riding a burning spacecraft wreck across the Sun's surface, waving
- two lines of huge white heavy sans text, top-left: `क्या SUN पर` / `LANDING POSSIBLE है ?`
- `SUN` in yellow, so the text mixes Devanagari and Latin
- no face close-up, no arrows, very high warm contrast

**Description:**
- a link to Ep. 1 at the very top
- a one-paragraph promise ("an imaginary journey to the star")
- a fact sheet (temperatures, core, distance, Parker Solar Probe)
- like/subscribe/bell lines, a long legal disclaimer ("visuals … for illustration … may not represent actual
  scale"), and 5 hashtags (`#whatif #sun #CuriousSpace #astronomy #space`)
- no credits and no chapters

**Captions:** auto-generated only (Hindi, English, Bengali).

---

## 2. Script

### Numbers
- 1,487 words (Whisper) over 0:00.1-11:05: **134 words per minute**, or 179 counting only the time the voice
  is speaking. It speeds up through the video: 105 · 115 · 137 · 132 · 130 · 132 · 138 · 150 · 145 · 139 · 152.
- The voice is on 75% of the runtime. There are 238 pauses of 0.3 s or more (median 0.58 s, p90 0.85 s). Only
  14 pauses reach 1 s and 5 reach 1.5 s, and those five are placed: 0:09.6 (2.9 s), 0:23.9 (5.2 s), 1:06.9
  (6.7 s, the title), 1:15.0 (2.6 s, the logo) and 9:33.9 (2.3 s, entering the core).

### Section map (the ride)
| # | Time | Stage | Key numbers on screen | Device |
|---|---|---|---|---|
| 1 | 0:00-1:08 | **Hook**: "it looks calm, a smooth golden ball… where would we put our feet?" | 5,500°C, 2,000,000°, 350×, 28× gravity, 60 kg → 1,680 kg ≈ 1.7 tonnes, "8 minutes old" | six paradoxes, one card each |
| 2 | 1:08-1:18 | Title + "Presented by Curious Studios" | — | 6.7 s voice pause, music sting |
| 3 | 1:18-1:41 | The vehicle: Agniyaan with a heat shield, a dashboard ("distance and temperature every second") and a multi-wavelength camera | — | the protagonist |
| 4 | 1:41-2:25 | Departure: 15 crore km; "Delhi to Mumbai 1 lakh times", "200 years by train"; Aditya-L1 at L1 = "1% of the journey" | 14,89,65,215 → 15,00,00,000 KM; ×20; 11 / 200 SAAL; 0.2% → 1% | distance counter, progress bar |
| 5 | 2:25-3:00 | Solar wind: 3 lakh tonnes/s, 16 lakh km/h, aurora | Delhi-Mumbai map line | |
| 6 | 3:00-3:46 | The temperature paradox; Parker Solar Probe passes (6,87,000 km/h; 2021 first touch; 29th pass Sep 2026) | 5,560 → 2,000,000°C thermometer; 6,31,247 → 6,87,000 KM/H arc gauge | the "something passes us" beat |
| 7 | 3:46-4:28 | Corona = "the Sun's crown": 48°C Delhi summer ×100 = surface, ×350 = corona | 40 → 48°C thermometer, ×100 grid of thermometers, ×350 | everyday-heat ladder |
| 8 | 4:28-5:58 | Change camera wavelength (19.3 nm) → coronal rain → sunspot "the whole Earth fits" → solar flare = billions of H-bombs → magnetic reconnection → Feb 2026 X8.1 flare | 19.3 NANOMETRES; 200 MT vs 60,00,000 MT; 61,21,31,786 → 2,01,22,12,31,115; X8.1; "1 → 4 X-CLASS FLARES" chart | camera "mode switch" |
| 9 | 5:58-7:02 | CME → GPS; May 2024 storm (G5, flights rerouted, aurora over Ladakh); 1859 telegraph fires | CME card, phone GPS, X-ray flux chart with 5 "X" peaks, G5 gauge, 1859 | stakes for the viewer's phone |
| 10 | 7:02-7:08 | "We didn't come to watch the weather. We came to land." | — | +7.6 dB music hit |
| 11 | 7:08-7:50 | Chromosphere: "fire grass", spicules 100 km/s, 1 crore at once, 1,000× Everest | 98 → 100 km/s; Delhi-Agra 0.43 → 2.00 s; 1 → 1,00,00,000; 9,303 → 10,000 km | |
| 12 | 7:50-8:55 | "Landing gear down… nothing touched": the photosphere is not a surface; granules the size of Rajasthan; sunlight's 8 min 20 s | 5,075 → 5,500°C; 0 min 00 s → 8 min 20 s; 13,90,000 km | the twist |
| 13 | 8:55-9:40 | Convection zone ("a giant boiling pot") → magnetic field → radiative zone (light takes about 1,70,000 years) | 2,00,000 km; 84,084 °C; 57,734 → 1,70,000 SAAL | |
| 14 | 9:40-10:30 | Core: 15 million °C; a spoonful is about 750 g, 8× gold; fusion of 40 lakh tonnes every second; 4.6 + 5 billion years | 13,511,812 → 15,000,000 °C; 676 → 750 g; ×8; 39,88,653 → 40,00,000 TON; 3.5 → 4.6 BILLION YEARS; +5.0 | answers "solid ground?": no |
| 15 | 10:30-11:10 | Close: "the Sun isn't calm, we are just far away"; a hook to Ep. 1 ("what if it vanished?"); CTA "comment the next What If"; outro card | 1,25,27,511 km | loop to the opening line |

### Hook (0:00-1:08), beat by beat
| Time | Voice (summary) | Picture |
|---|---|---|
| 0:00 | "Every morning the Sun looks so calm…" | Earth limb with the Sun rising (push-in 7 %/s, slight shake) |
| 0:02.7 | "…a smooth golden ball." | **kinetic card**: `EK / SMOOTH, / GOLDEN / BALL.` word by word next to a glowing sphere |
| 0:05.1 | "But when NASA's cameras look closely…" | desaturated clean-room photo of a spacecraft in a camera viewfinder (`● REC`, `ZOOM 2.5× → 87×`); headline `LEKIN JAB / NASA KE / CAMERAS / ise close se dekhte hain…` |
| 0:08.6 | "…this is what it looks like." | fade through black → 0.4-1 s flash cuts: astronaut visor, burning surface, cockpit |
| 0:09.6 | (2.9 s pause) | riser → impact, +11 dB |
| 0:12 | "If we wanted to land on the Sun, where would we put our feet?" | the spacecraft lands on the Sun; landing struts in plasma |
| 0:19.4 | "…what is the smooth surface we see at sunrise?" | sunrise over Indian rooftops and a temple, a small craft crossing |
| 0:23.9 | (5.2 s pause) | hit + rumble, +12 to +15 dB; cockpit, landing struts |
| 0:31 | "The surface is 5,500°C…" | `5,500°C / SURFACE` sliding in over red SDO footage |
| 0:37 | "…the atmosphere above it, 2 million degrees: move away from the fire and it gets 350× hotter. How is that possible?" | dot-and-line diagram (`5,500°` → `20,937°` → `480,383°`, "YOU"); `AAG SE DOOR JAO…`; `350×` filled with Sun texture; `YEH KAISE POSSIBLE HAI?` |
| 0:45 | "It rains on the Sun: burning plasma…" | coronal loops raining, the craft passing under them |
| 0:50 | "…gravity 28× Earth's: 60 kg weighs like an SUV." | Earth vs Sun `SURFACE GRAVITY 1× → 26× → 28×` slider; `YOUR MASS 60 kg × 28 = 1,680 kg`; man = SUV `≈ 1.7 TONNES` |
| 1:02 | "And the sunlight on your face this morning isn't just 8 minutes old." | woman with tea at sunrise on a rooftop |
| 1:06.9 | (6.7 s pause) | sun disc; `WHAT IF / WE LAND ON SUN`; then `PRESENTED BY / CURIOUS STUDIOS` |

### Style notes
- **Paradox engine:** each fact is phrased as a contradiction of common sense ("move away from the fire and it
  gets hotter", "landing gear down… nothing touched").
- **Everyday rulers:** body weight, an SUV, a Delhi summer, a train, Delhi-Mumbai, a spoon, gold. Most are
  India-specific.
- **Open loops:** "the sunlight… isn't just 8 minutes old" is only answered at 8:44; "where would we put our
  feet?" at 8:01 and 10:05.
- **Mistakes on screen:** `FEBURURY 2026`, a mix of Indian and Western digit grouping (`15,00,00,000` beside
  `2,000,000`). The 1:45 count-up overshoots its own label.

---

## 3. Visuals — what is on screen and where it comes from

| Kind | Share (by eye from the 2 s contact sheets, except where measured) | Notes |
|---|---|---|
| AI-generated cinematic shots and clips | about 70% of the runtime | one consistent spacecraft design (rusty white hull, dish heat shield, blue thrusters) in more than 30 shots, an astronaut in the cockpit and visor reflections, people (a woman with tea, a man next to an SUV, a telegraph operator in 1859), Indian rooftops, temples, India Gate, Ladakh, aircraft in aurora. The same renders come back (spacecraft side view at 0:14, 1:18, 2:26, 7:52) |
| NASA SDO and similar solar imagery | about 15% | red 304 Å and gold 171 Å surfaces and limb (0:30, 0:43, 4:10, 8:42), sunspot close-ups. Real data, re-graded |
| Typographic and data cards | measured: 29% of the runtime carries big text (54 of 203 shots) | see section 4 |
| Photos | a few | desaturated clean-room photo in a viewfinder (0:05), real satellite photos (Aditya-L1, 1:56 and 6:38) |

Classifier output for reference: footage/animation 66.7%, graphics 17.7%, stills with a camera move 13.6%,
2.5D parallax 2%. "Graphics" here means only flat or black backgrounds; most of their cards have a Sun texture
behind them.

**Camera move per shot:**
- push-in on 109 of 203 shots (median 3 %/s; up to 15-20 %/s on energy beats, 0:19 and 0:24)
- pull-out on 37, pans on 56, tilts on 37
- a slow roll (0.3-1 °/s) on 44
- shake on 42, all on action or impact beats
- 2.5D parallax on 31 shots: layered AI stills moved like a dolly

**Grade:**
- one colour world per episode: orange to gold with black space, plus teal for the cockpit screens and the
  19.3 nm "camera mode"
- median HSV saturation 193/255, contrast p95-p5 159, warm highlights (Lab b* +35) and shadows (b* +7)
- a heavy vignette (corners about 1.4 stops darker on average; partly the centred Sun), no letterbox
- the grain is the encode's

**Overlays:**
- the logo bug `CURIOUS SPACE` top right, all the time (white box with black "CURIOUS", then white "SPACE")
- a like / dislike / Subscribe / bell pill pops in bottom centre about 15 times, each for 1-2 s (seen in the
  2 s contact sheets at 0:24, 1:28, 2:34, 3:46, 4:34, 4:38, 6:30, 6:34, 6:36, 7:30, 7:36, 8:46, 8:50, 10:00,
  10:02)
- warm flare sweeps on energy cuts (5:27)
- in the closing minutes, a journey footer bottom-left (`THE SUN · EARTH · SUNRISE`,
  `THE SUN · CHROMOSPHERE`) with a stage counter bottom-right (`03 / 08`, `05 / 07`)

---

## 4. Motion graphics — templates (specified so they can be rebuilt)

Sizes are at 1080p and measured on 480p frames scaled up. Fonts are identified by eye; the closest free
matches are given.

| # | Template | Example | Type | Layout | Animation |
|---|---|---|---|---|---|
| T1 | **Kinetic stacked headline** | 0:02.7 `EK / SMOOTH, / GOLDEN / BALL.`; 0:05.6 `LEKIN JAB / NASA KE / CAMERAS` | condensed heavy sans (Anton / Bebas Neue Bold class), white fading to light grey top to bottom; the key word in a gold gradient (#FFD25A → #E8761C); a small letter-spaced orange kicker (`LEKIN JAB`, Montserrat SemiBold, tracking 0.35 em); a white bold sub-line with mixed weights | left column at x ≈ 8%, 3-4 lines of ≈ 230-310 px, tight leading (0.95) | each line rises out of a mask (bottom clip) in 0.15 s, with a 0.1-0.5 s stagger **timed to the spoken word**; the whole card cuts out on the next shot; a 1.5 px tick SFX per line |
| T2 | **Hero number** | `15,00,00,000 KM` 1:46; `6,87,000 KM/H` 3:36; `40,00,000 TON` 10:16; `350×` 0:42 | the same condensed sans at 230-330 px; vertical gradient fill (peach #FFE1B0 top → orange #F07A1E bottom), an outer orange glow (radius ≈ 25 px, about 60%); unit in white letter-spaced caps below (`K M`, `K M / H`) | centred, or left of an object (Sun, Earth) | **count-up with ease-out over about 1.3 s**, landing on the spoken value; the unit fades in halfway; a footnote fades in after it lands (`15 CRORE KM · LIGHT TAKES ~8 MIN 20 S`); texture-filled variant: the digits are a mask over Sun footage (`350×`) |
| T3 | **Thermometer + temperature** | 3:06 `5,560 → 2,000,000°C`, `LEKIN USKE UPAR KA ATMOSPHERE?`; 4:02 `40 → 48°C` over India Gate; 8:16 `5,075 → 5,500°C` | T2 number with a smaller orange `°C`; a sub-line in letter-spaced caps; a second line `2 MILLION DEGREE!` in the gold gradient | a vertical glass thermometer at the far left (x ≈ 5%, 70% tall) with a `5,500°C` reference tick | the mercury rises with the count, ease-out; the background cuts from grey (desaturated) to full colour as the value passes the reference |
| T4 | **Arc gauge** | 3:34 `6,31,247 → 6,87,000 KM/H`; 6:22 G-scale `G5` | T2 number inside a thin glowing arc (≈ 300° of a circle), a moving bright dot on the arc | centred, star streaks behind | dot and number move together; a green → yellow → red segmented arc for the G-scale |
| T5 | **Dot-on-a-line diagram** | 0:38 `5,500°` → `480,383°` with `YOU`; 1:46 Sun ↔ Earth | a thin dashed line, a glowing white dot, small letter-spaced labels (`SUN`, `EARTH`, `YOU`) | horizontal across the frame at mid-height, objects at both ends | the dot travels with the counter; values count above it |
| T6 | **Progress bar** | 2:20 `0.2%` → 2:22 `1%` | thin grey segmented bar with a cyan fill, big light-grey % above, a bracket line to the Earth icon | top third | the fill grows as the voice says "1% of the journey" |
| T7 | **Elegant data panel** | 0:52 `SURFACE GRAVITY 1× → 28×`; 0:58 `YOUR MASS 60 kg × SUN'S GRAVITY 28 = 1,680 kg / EARTH-WEIGHT EQUIVALENT`; 7:24 `100 km/s`; 7:38 `9,303 → 10,000 km` with a vertical ruler | thin geometric sans (Inter / Montserrat Light, 120-180 px numbers), tracked small-caps labels (letter-spacing 0.4 em, 22 px), the result in pale gold, a 1 px divider | two columns over a dark, blurred Sun | count-ups; the slider dot moves; the divider draws left to right |
| T8 | **Serif fact card** | 1:00 `≈ 1.7 TONNES / EARTH-WEIGHT EQUIVALENT`; 5:48 `X8.1`; 5:44 `FEBRUARY 2026`; 1:14 `PRESENTED BY / CURIOUS STUDIOS` | Cinzel / Cormorant-like serif in pale gold, tracked small caps below, thin rules on both sides | centred, or top-left beside a subject | fade + blur in (0.4 s); the logo card is gold serif on a Sun texture, 3 s |
| T9 | **Title card** | 1:08 `WHAT IF / WE LAND ON SUN` | `WHAT IF` heavy sans at 60 px, tracking 0.6 em, white; `WE LAND ON SUN` heavy rounded sans (Montserrat ExtraBold) at 110 px with a white → grey gradient; a thin gold rule underneath | centred on a dimmed Sun disc | `WHAT IF` blur-fades in over 0.6 s; the second line slides in from the left with a motion blur over 0.6 s; held 2 s |
| T10 | **Camera / HUD overlay** | 0:05 viewfinder (`● REC`, `ZOOM 2.5× → 87×`, corner brackets); 4:28 `19.3 nm / 19.3 NANOMETRES` wavelength scale; 5:12 targeting circle in a visor; 5:06 `200 MEGATON TNT` box | thin white UI lines, tiny tracked mono labels, teal accent | frame corners and centre | zoom number counts; brackets scale in; the target ring rotates |
| T11 | **Chart** | 5:56 `1 → 4 X-CLASS FLARES` flux line; 6:20 X-ray flux 2024 with 5 red `X` spikes | one glowing orange line, faint grid, tiny axis labels, red markers with glow | lower-left or full frame | the line draws left to right (about 2 s); markers pop on each peak with a hit |
| T12 | **Comparison / scale** | 2:44 `×20`, `11 SAAL → 200 SAAL` timelines; 4:06 `×100` thermometer grid; 10:00 balance `CORE ×8 GOLD`; 10:20 `3.5 → 4.6 BILLION YEARS` heartbeat line | T2 numbers plus simple 3D props (a spoon, gold bars, a scale) or icon grids | | icons multiply in a grid; the balance tips; a heartbeat line runs with the count |
| T13 | **Map line** | 2:54 `DELHI → MUMBAI`; 7:26 `DELHI → AGRA 0.43 → 2.00 s` | a glowing orange line on a dark or satellite map, small labels, a timer box | | the line draws while the timer counts |
| T14 | **Subtitle line** | under every T1-T3 card | white sans (Inter Medium, ≈ 40 px) on a faint dark rounded box, Hinglish | bottom centre at y ≈ 90% | cut in and out with the card; **only on typographic cards, never on footage** |
| T15 | **Journey footer** | 7:38 `THE SUN · CHROMOSPHERE … 05 / 07`; 8:44 `THE SUN · EARTH · SUNRISE … 03 / 08` | tiny tracked caps, 40% white | bottom-left and bottom-right, y ≈ 96% | fades in with the stage |
| T16 | **End screen** | 10:54 channel page mock-up, 10:56 `WATCH NOW` + Ep. 1 thumbnail, 11:00 a fake comment box `WHAT IF … ?`, 11:04 `CURIOUS SPACE / STAY CURIOUS`, 11:08 `THANKS FOR WATCHING` | | | |

Counters measured by OCR (at least 15, a lower bound at 1 sample per second): 0:39 `→ 350`, 0:52 `1× → 28×`,
1:50 `11 → 200 SAAL`, 2:17 `2,03,000 → 75,00,000`, 3:06 thermometer, 5:15 `2,23,63,822 → 2,01,22,12,31,115`,
7:21 `25 → 100`, 7:26 `0.43 → 2.00`, 7:37 `857 → 10,000`, 8:15 `2,912 → 5,500`, 8:44 timer, 9:45
`10,910 → 1,70,000`, 9:51 `→ 15,000,000`, 10:14 `39,88,653 → 40,00,000`.

---

## 5. Editing

### Cut rhythm
- **203 shots in 670 s: median 3.0 s, mean 3.3 s.** Distribution:

  | 0-1 s | 1-2 s | 2-3 s | 3-4 s | 4-6 s | 6-8 s | 8-12 s | 12-20 s |
  |---|---|---|---|---|---|---|---|
  | 12 | 38 | 54 | 41 | 48 | 4 | 4 | 2 |

- Cuts per minute, minute by minute: 22 · 18 · 20 · 19 · 15 · 22 · 18 · 14 · 11 · 20 · 22.
- Per section:
  - the hook runs at 22 cuts/min with a 2.7 s median
  - the title breathes (2 shots in 10 s)
  - the landing sequence slows to 12.9 cuts/min (7:08-8:55: long, immersive surface shots)
  - the core section speeds up to 22.8 cuts/min (2.3 s median) for the finale
- **Sync with the voice:** 54% of cuts fall in a pause between phrases and 64% within 0.2 s of a word start.
  Kinetic text reveals word by word on the spoken words.

### Transitions
| Transition | Count | Where / how |
|---|---|---|
| Hard cut | 96 | the default, on a word or in a pause |
| Fade through black | 30 dips + most of the 27 "dissolves" (checked by eye on the strips) | 0.3 s fade-out to black then a hard cut in, or a cut to black and a 0.4 s fade-up; between ideas (0:08.6, 0:37.8, 0:50.3, 1:07.3, 1:55) |
| Warm flare flash | 21 | an orange-white light sweep of about 0.3 s over a cut on energy beats (0:09.8-0:11 flash montage, 0:24, 3:19, 5:05, 5:27) |
| White flash | 8 | explosions and the X-flare (5:06, 5:18, 9:47) |
| Hyperspace streaks | 3 | star streaks as a travel transition (2:44, 5:20 red warp) |
| Whip / zoom / slide | 6 | rare |

Strips: `sequences/transition_*.jpg` on Drive.

---

## 6. Audio

### Measured levels
| Layer | Level | Notes |
|---|---|---|
| Final mix | **-19.9 LUFS** integrated, true peak ≈ -2.5 dBFS | not normalised to -14: YouTube plays it about 5 dB quieter than a -14 master |
| Voice | -20.1 LUFS; momentary -20.1 LUFS while speaking | consistent, close, lightly compressed |
| Music + SFX stem | -28.8 LUFS integrated | |
| Music under speech | momentary median -35.1 LUFS = **15.0 LU under the voice** | |
| Music in pauses | -33.3 LUFS = 13.2 LU under the voice | **ducking 2.7 dB**: the bed does not move with the voice |
| Pause moments | +10.7 dB (0:09.6), +12.3 / +15.5 dB peak (0:23.9), +3.9 / +6.4 dB (1:06.9 title), +7.6 dB (6:56.6), +4.1 / +5.4 dB (9:33.9) | music level in the pause vs the speech around it: the swells are designed into the long pauses only |

### Music
About six cues that change at act boundaries, read from the spectrogram (`audio/music_map.jpg`) and the
automatic segmentation, which over-splits the textures into 10:
- 0:00-1:17 hook: a cinematic pulse at about 117 BPM with plucked or bell arpeggios (0:02-0:09), percussive
  under the montage
- 1:17-3:22: ambient pads, no steady beat
- 3:22-4:16: a low drone that's 10 dB louder (minutes 3-4: music at -25 LUFS under speech instead of -35),
  under the temperature paradox
- 5:17-7:35: a melodic arpeggiated cue (dense tonal lines) under the flare and storm stakes
- 7:35-10:52: a sustained pad with a slow pulse (about 129 BPM) for the landing and the core
- 10:52-11:10: an outro sting that fades over 6.5 s

There are no deliberate full silences. The only near-silence is the last 0.3 s.

### SFX
Of 1,637 candidates the detector found in the music stem, 257 are audible effects. Those louder than -38 dBFS
land on a cut or a text entry twice as often as chance; fainter ones are details inside the music. That makes
about 23 effects per minute.

| Trigger | Share |
|---|---|
| on a cut (±0.2 s) | 26% of cuts carry an effect: whooshes into fades, hits on hard cuts, risers ending on the cut |
| on a text entry | 37% of text entries carry one: ticks or pops on each kinetic word, a hit on each hero number landing |
| no visual trigger | sounds for on-screen action: thrusters, flares, explosions, a rumble under the landing |
| long pauses | riser → impact at 0:09.6 and 0:23.9, swell + sting under the title, impact at 6:56 |

The automatic SFX list, with time, type, level and trigger, is in `report.md` on Drive. Its "pop/click" class
also catches some notes of the 0:02-0:09 arpeggio.

### Voice
- male, young, bright and energetic: median pitch 165 Hz, ±5.8 semitones, so far more animated than a
  documentary read
- 134 words/min (179 while speaking), short regular pauses
- signposting: no ordinals or numbers; it drives with "lekin" (17), "to" (13), "hum" (18), "aap" (11),
  questions (7 sentences end in "?"), "agar" (6) and "ab" (5)

---

## 7. Key frames (on Drive in `keyframes/`)
| Time | Frame | What to take from it |
|---|---|---|
| 0:03.5 | `EK SMOOTH, GOLDEN` + glowing sphere on black, subtitle | T1: word-synced headline; gold gradient on the key word |
| 0:06.5 | desaturated clean-room photo in a REC viewfinder, `LEKIN JAB / NASA KE / CAMERAS` | T1 + T10: a camera "looking closer" device |
| 0:32.5 | `5,500°C / SURFACE` over red SDO limb | T2 on real solar data |
| 0:41.5 | `GARMI BADH JAAYE / 350×` filled with Sun texture | texture-filled number |
| 0:53.0 | Earth ↔ Sun, `SURFACE GRAVITY 8×` slider | T7 comparison slider |
| 0:58.5 | `YOUR MASS 60 kg × 28 = 1,680 kg` | T7 equation |
| 1:12.0 | `WHAT IF / WE LAND ON SUN` on the Sun disc | T9 title |
| 1:15.0 | `PRESENTED BY CURIOUS STUDIOS` gold serif on SDO texture | T8 logo card |
| 1:46.0 | `15,00,00,000 KM`, Sun - dot - Earth line | T2 + T5 |
| 2:21.0 | `1%` progress bar | T6 journey progress |
| 3:09.5 | thermometer + `2,000,000°C / 2 MILLION DEGREE!` | T3 |
| 3:35.5 | `6,87,000 KM/H` arc gauge over star streaks | T4 |
| 4:28.0 | teal `19.3 nm` sphere, wavelength scale | T10 camera mode switch (palette change) |
| 6:20.0 | X-ray flux chart with five red X peaks | T11 |
| 7:38.0 | `HEIGHT OF ONE SPICULE 9,303 km` + ruler, footer `THE SUN · CHROMOSPHERE … 05 / 07` | T7 + T15 |
| 8:44.0 | sunrise, `0 min 00 s` timer, `YOU` | open loop closed: sunlight's age |
| 10:16.0 | `40,00,000 TON` in a dial with floating cubes | T2 + T4 hybrid |
| 10:56.0 | `WATCH NOW` + Ep. 1 thumbnail | T16 binge path |

---

## 8. What to take, and what our channel rules forbid

Take (format-neutral, all buildable in our renderer):
1. a hook of four to six "impossible numbers" before the title, with the topic named in the first sentence
2. a journey frame: a goal ("land"), stages with a footer counter, progress and open loops answered later
3. every number as an animated card (count-up, thermometer, gauge, dot-on-line, chart) landing on the spoken
   value
4. kinetic headlines revealed word by word on the narration timeline; captions only where they add meaning
5. cuts placed in pauses and on words; hard cuts by default, fades through black between ideas, flares on
   energy
6. one colour world per video, push-ins and slow roll on everything, shake only on impacts
7. a flat music bed about 15 LU under the voice; the sound design in a few placed pauses (riser → impact,
   swell, sting); ticks on text and hits on number landings

Don't take (channel rules):
- viewer address ("hum", "aap", questions to the viewer), CTAs and the subscribe pill
- India-specific rulers
- Devanagari on the thumbnail
- AI-invented pictures presented as space imagery: our footage is real 4K archive material, credited

Also don't copy: their music, footage, renders or graphics.
