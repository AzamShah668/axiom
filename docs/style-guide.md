# Editing style guide: v3 (every video from production 03 on)

Where it comes from:
- the measured breakdown of Curious Space, "What if we land on the Sun"
  (`docs/research/curious-space/01-what-if-we-land-on-sun.md`)
- the ranked gap list against our production 02 (`docs/research/curious-space/02-gap-list-production-02.md`)
- the owner's decisions of 2026-10-20:
  - key phrases on screen, with the full English text as a CC track
  - an audible music bed plus designed pauses
  - a logo bug
  - the new packaging test from video 03

Tools:
- `scripts/video/render_v3.py`: plan, render and mix
- `scripts/video/mograph.py`: graphics
- `scripts/video/sfx.py`: sound effects
- `scripts/video/grade.py`: colour grade
- the edit-plan syntax is in `scripts/video/make_edit.py`

The channel rules in `productions/README.md` still apply:
- English on screen, Hindi narration (Neel, locked preset)
- third-person storytelling
- 4K moving footage, never repeated, no text in footage
- full credits

## 1. Structure and intro
| Part | Length | What it does |
|---|---|---|
| `## hook` | 15-30 s | The **first sentence names the topic** and its paradox ("Black hole. The place nothing escapes, not even light."). It gives 2-3 teaser numbers or claims from later facts, each with a headline or number card. It ends on an open loop that leads into the story ("…but the story begins on a battlefield"). |
| `## cold_open` | 45-75 s | The story hook: a person, a place, a year. It ends on a reveal (a moment, see §6) and a second open loop. |
| title card | 2.4 s | `10 facts about` / `BLACK HOLES`, with a sting. It sits in the 3.5 s gap after the cold open. |
| chapter cards | 2-2.6 s | `FACT` / gold `#n` / title revealed word by word / countdown bar. Then the footer `FACT n / 10 · title` for the whole fact. |

Targets: topic named in under 1 s, first number on screen within 15 s, title before 1:45.
Production 02 named the topic at 0:59; the reference names it at 0:00.

## 2. Pacing
- **Scene length:**
  - about 3 s by default (median about 3 s, p10-p90 2-5.5 s)
  - `{hold}` 5.5 s for awe shots and openings
  - `{flash}` 0.6 s montages, rare: impacts only
  - `{4s}` sets an exact length
- **Cuts follow the voice.** A beat starts in the pause before its first word: the picture leads the word by a
  few frames. Inner cuts snap to pauses first, then to word starts. On a moment, the cut lands exactly on the
  reveal word.
- **No cut** while a kinetic headline is being read, or under a counting number.
- Sanity numbers (`pipeline.sh … edit` prints them):

  | Measure | Target |
  |---|---|
  | Cuts per minute | 15-19 |
  | SFX per minute | 18-25 |
  | Key lines | about 1 per 20 s |
  | Headlines | about 1 per 30-60 s |
  | Number cards | at least 2 per fact with numbers |

## 3. On-screen text (English)
There is **no running subtitle.** Every sentence still gets a `C` line, but it goes to the English caption
track `captions.en.srt`, which is uploaded to YouTube as CC. Burned-in text is only for meaning:

| Element | Spec line | Look | When |
|---|---|---|---|
| Kinetic headline | `K` | 2-3 lines of Anton, silver; the key line gold (`*…*`). An optional orange tracked kicker and a white sub-line. Left column at x 7.5%, with a dark gradient behind it. Each line rises out of a mask in 0.18 s **on its spoken word**, with a tick on each line. | The claim of a beat: "NOTHING ESCAPES / *NOT EVEN LIGHT*" |
| Key line | `C … \| big` | One centred line of Anton. Words rise in 0.07 s apart; numbers turn gold. Soft dark ellipse behind it, pop + ticks. | Years, places, one-word reveals: `DECEMBER 1915`, `1783`, `BLACK HOLE` |
| Lower third | `L` | name in Anton 76 px rising out of a mask, orange tracked role line, gold bar, left-bottom; 3.5 s | Each person, the first time they appear |
| Number card | `N` | See §4. Count-up with ease-out that **lands on the syllable that says the number**, a roll while counting, a hit on landing. | Every number that matters |
| Chapter card, title, footer | (automatic) | `mograph.chapter`, `mograph.title`, `mograph.footer` | |
| Logo bug | (automatic) | `SCIENCE` in black on a white box + `GUY`, top right, 80%, all the time | |

Rules:
- Only one big element at a time. `edit` warns and drops a key line that collides with a headline or number
  card. Trigger the key line on the word itself (`C dark stars | DARK STARS | big`).
- Text never covers the subject's centre: use `pos=left` headlines over centred objects.
- Gold is for the one thing to remember in each element.

## 4. Number-card templates (`N <trigger> @ <template> | key=value …`)
| Template | Use for | Keys |
|---|---|---|
| `hero` | one big number: masses, distances, counts | `value`, `from`, `unit`, `kicker`, `foot`, `log` (log count for huge ranges, e.g. 1,392,000 → 6) |
| `scale` | "×500", "4 million times" | `value`, `from`, `unit`, `kicker` |
| `thermo` | temperatures, a rising level against a reference | `value`, `from`, `unit` (°C), `ref`, `ref_label`, `kicker`, `foot` |
| `gauge` | percentages, fractions of the speed of light | `value`, `from`, `max`, `unit`, `kicker`, `foot` |
| `line` | journeys and timelines: a dot travels from `left` to `right` | `value`, `from`, `unit`, `left`, `right`, `foot` |
| `equation` | A → B relations ("1 Sun → 6 km") | `a`, `a_label`, `b`, `b_label`, `op`, `value`, `unit`, `foot` |
| `fact` | a serif statement card (Cinzel) for a quiet, weighty line | `value`, `sub` |
| `progress` | "1% of the journey", "a third of the way" | `value`, `from`, `max`, `unit`, `left`, `right`, `kicker` |
| `chart` | a real data series drawn left to right (light curves, flux, counts per year) | `points` ("y,y,…" or "x:y,…"), `marks` (indices that pop), `label`, `xlabel`, `ylabel`, `log`, `draw` (s) |

Templates drawn **over the footage** (use `over`):

| Template | Use for | Keys |
|---|---|---|
| `callout` | pointing at an object in the shot: a ring, a leader line and a label | `x`, `y` (frame fractions), `r` (px), `label`, `sub`, `dur` |
| `route` | a map line between two places, with a distance counter | `x0`, `y0`, `x1`, `y1`, `left`, `right`, `value`, `unit` |
| `hud` | a telescope or camera view: brackets, REC, a target ring, a zoom counter | `label`, `sub`, `x`, `y`, `value`, `unit` (×) |
| `name` (`L` line) | lower third for a person: `L <trigger> @ JOHN MICHELL \| village priest of Thornhill · 1724-1793` | `value`, `sub`, `dur` (3.5 s) |

Use a chart only with **published data** (cite it in `script.md`'s fact-check table). An invented curve labelled
as data is never allowed.

Common keys:
- `land=<trigger>`: the word the count lands on. Default: 1.3 s after the card starts.
- `count=<s>`: count duration. Default 1.3 s.
- `over`: draw on top of the running footage. Without it, the card is its own beat over dimmed footage, and
  `q=` gives that footage's query (`;` separates alternatives).
- `dur=<s>`: how long an `over` card stays.

## 5. Transitions (by rule; `T <trigger> | <kind>` overrides)
| Kind | When | Sound |
|---|---|---|
| hard cut | default | none |
| dip to black (0.4 s) | a cut in a pause of 0.5 s or more (an idea break) | whoosh |
| warm flare (0.33 s) | on moments (reveals, energy) | shimmer |
| white flash | explosions, flares; only via `T` or `M … \| trans=flash` | hit |
| whip, zoom | travel or a jump in scale only | fast whoosh |
| soft dissolve | out of title and chapter cards | none |

## 6. Moments (`M`): 3-5 per video, at act breaks and big reveals
`M <trigger> | breath=1.6 | riser=1.8 | impact=impact|hit|none | trans=flare | drop | swell=7`
- A **silence (breath)** is spliced into the narration in the pause before the trigger. The timeline shifts by
  itself, so no re-render of the voice is needed.
- A riser ends exactly on the trigger word, then the impact and the transition. The camera does a fast
  push-in with a small shake.
- Music:
  - default: it swells +7 dB through the breath
  - `drop`: it falls silent for the breath and comes back with the impact (the designed silence)
- The reference has 5 such pauses in 11 minutes. More than one per minute wears it out.

## 7. Camera and grade
- Every footage scene moves on top of its own motion. Moves cycle push (3.2%/s) → drift → pull → push → roll
  (±1.1°). `{hold}` scenes push slowly (1.5%/s). Scenes that start on a moment get the impact move.
- One colour world per video (`edit.base.json` `"grade"`):
  - presets: `amber_teal` (black holes, stars), `gold` (Sun, fire), `ice` (planets, moons), `neutral`
  - `contrast` 0.25, `sat` 1.3, `vignette` 0.35, `grain` 3, `lift` 0.01
  - true black stays black
  - the grade applies to footage only, so graphics keep their colours
  - measured on our footage: median saturation 34-122 → 58-172

## 8. Sound
| Layer | Rule |
|---|---|
| Voice | -16 LUFS after `voice_post.sh`. Nothing is louder than the voice except impacts. |
| Music bed | Kevin MacLeod (CC BY 4.0, credited by `credits.py`), one cue per act (about 2 facts) with 2.5 s crossfades. Each cue is levelled (only 25% of its own swing is kept) and sits **16 LU under the voice while speaking, +3 dB in pauses**: a flat bed that never pumps. The reference has 15 / 13 LU; production 02 had 26 LU (inaudible). |
| Title | sting + swell +4 dB |
| SFX | All synthesised in `scripts/video/sfx.py`: no samples, so licence-clean by construction and never the reference's sounds. Levels are set by each sound's loudest 400 ms against the voice (`sfx.LEVEL`). |
| Master | measured linear gain to -14 LUFS, then a peak limiter at -1.5 dBFS (no dynamic loudnorm, so the mix never pumps) |

SFX placement (automatic):

| Trigger | Sound |
|---|---|
| headline line, key-line word | tick (key-line first word: pop) |
| number count, landing | roll, hit |
| number card as its own beat | whoosh |
| chapter card | big whoosh + hit + a tick per title word |
| dip | whoosh |
| flare | shimmer |
| flash | hit |
| moment | riser into the reveal word + impact |
| `B` / `S` lines | boom / any kit sound |

## 9. Workflow changes
- `tts/narration.hi.md` starts with `## hook`. `pipeline.sh … narration` puts 1.2 s after the hook (`HOOK_GAP`)
  and 3.5 s after the cold open.
- `edit.base.json`:
  - `"style": "v3"`
  - `"lead_in": 0.5` (the voice starts at once)
  - `"title": {"kicker": "10 facts about", "main": "Black Holes"}`
  - `"count_total": 10`
  - `"grade": {…}`
- `pipeline.sh … render` picks `render_v3.py` by the style and copies `captions.en.srt` into the production
  folder. Upload it with the video (science-publish).
- Quick look at one part: `render_v3.py … --range 20,45` renders only those seconds.

## 10. Proof
`productions/02-black-holes/v3-proof/` re-cuts production 02's cold open and fact 10 in this style, with a new
hook. Its README shows how it was built and what it measured.
