---
name: science-edit-plan
description: Write the edit plan (edit.spec) for a science-channel video in the v3 style - a visual query for every sentence, kinetic headlines, key lines and animated number cards timed to the spoken words, designed moments, chapter cards, music and the English CC captions - and compile it to edit.json. Use for stage 3 of science-video or when changing what appears on screen.
---

# Edit plan (stage 3)

Read `docs/style-guide.md` first: it defines the v3 look, the sound, the pacing and the target numbers.
This skill covers how to write the plan.

Files in `productions/NN-slug/`:
- `edit.spec`: the human-editable plan, and the source of truth
- `edit.base.json`: style, lead-in, title, chapter cards, music map, grade, card/background queries, pins and bans
- `edit.json`: compiled; never edit it by hand

Build and check:
```bash
scripts/science/pipeline.sh productions/NN-slug edit
# make_edit.py spec+base -> edit.json, then assign_shots.py --plan-only: every trigger must exist in the
# narration; prints items, overlays, breaths, cuts/min, SFX/min and scene lengths
```

## edit.spec syntax
Each section starts with `== <section_id>`: `hook`, `cold_open`, `fact10` … `fact1`, the `##` ids of
`tts/narration.hi.md`. A trigger is the **first** occurrence of that exact text in the section's Devanagari
narration; `-` means the section start. Copy triggers from the narration; nukta letters (ज़, ड़) must match
exactly.

```
V <trigger|-> @ <visual query> [| <alternative> ...] [{hold|flash|4s}]   footage beat
G <trigger|-> @ <graphic>                                               explanatory diagram over dark footage
K <trigger|-> @ LINE / *GOLD LINE* [trigger] / LINE [trigger] [| kicker=..] [| sub=..] [| sub_at=<trigger>] [| pos=left|center]
N <trigger|-> @ <hero|scale|thermo|gauge|line|equation|fact|progress|chart|callout|route|hud> | value=.. [| from=..] [| unit=..] [| kicker=..]
              [| foot=..] [| land=<trigger>] [| log] [| over] [| q=<query>; <alt>] [| count=1.3] [| dur=4]
M <trigger> [| breath=1.6] [| riser=1.8] [| impact=impact|hit|none] [| trans=flare|flash|dip|cut] [| drop] [| swell=7]
L <trigger> @ <NAME> [| <role · years>]   lower third for a person
T <trigger> | <cut|dip|dissolve|flare|flash|whip|zoom>
C <trigger|-> | <English sentence> [| big]
S <trigger> | <sound> [| gain=-3]        (tick pop roll hit impact sub_drop riser whoosh whoosh_big flare sting)
B <trigger>                              boom
F <footer text>                          (default: the chapter card title)
V #<name> @ bite:<name>                  a real recording's own picture, uncut and in sync with its sound
```
From video 05 (owner, 2026-10-27; `productions/README.md`):
- **No `M` lines** (the voice never waits) and no `"intro"` in edit.base.json; `"channel"` plays after the hook.
- **Real archive footage:** a `V` line on the sentence that names the moment, its shot pinned in edit.base.json
  (`"pin": {"ch4/8": "svs_14715-launch#2"}`: section/item number as `scripts/footage/plan_items.py` prints
  it), and an `L` card that says what and when (`L ख़ास satellite @ COBE | NASA satellite · launched 18 November
  1989 · archive footage`). Give launches and interviews `{hold}`; keep a speaker's line one scene so the name
  card lands on their face.
- **Real recordings:** `V #<name> @ bite:<name>` right after the narration marker; its clip `bite_<name>` is
  pinned automatically. The subtitle and the CC line come from bites.json, no `C` line needed. Without a `V`
  line the recording plays over whatever is on screen (a photo of the speaker works for audio-only).

## Writing it, section by section
1. **V beats: one per sentence or clause.** Each `V` query describes what a 4K space-archive shot should
   look like, in plain English, the way you'd describe a frame.
   - Good: "zooming into a galaxy cluster", "the Hubble Space Telescope in orbit", "observatory dome under a
     starry sky timelapse".
   - Not: abstract ideas, people's names, or text.
   - Add 1-2 alternatives with `|`.
   - Use `{hold}` for awe shots and section openings. Use `{flash}` only for a 2-4 s impact montage, since
     every scene needs its own shot.
   - The planner snaps the cuts to the pauses and the word starts.
2. **C lines: every sentence, in English.** They become the CC track (`captions.en.srt`), not on-screen
   text. Split long sentences into two ("..."). Mark `big` only for names, years and one-word reveals; those
   become key lines on screen. Trigger a big line on the word itself when the sentence starts earlier
   (`C dark stars | DARK STARS | big`).
3. **K headlines: the claim of a beat, about one per 30-60 s.**
   - 2-3 short lines in English word order. Each line's `[trigger]` is the Hindi word that carries it.
   - Gold (`*…*`) on the line to remember.
   - The kicker is small context ("for an instant", "Michell's balance").
   - Never put a key line or a number card inside a headline's 1.6 s read time.
4. **N cards: every number that matters.**
   - `land=` is the Hindi number word ("चालीस", "पाँच सौ", "छह") so the count stops on that syllable.
   - Use `log` for huge ranges (`from=1,392,000 | value=6`).
   - Use `over` when the footage itself is the subject (Sgr A* animation + "4,000,000 SUNS"); otherwise the
     card gets its own dimmed beat with `q=`.
   - Values are written with commas the way they should read (`4,000,000`, `99.7`).
5. **M moments: 3-5 per video**, at the end of the hook, at the cold-open reveal and at one or two big
   reveals in the facts.
   - The breath is spliced into the pause before the trigger.
   - `drop` makes it a designed silence.
   - A `V` beat on the same trigger makes the cut land on the reveal word.
6. **G diagrams** (`render_video.gfx`), for explanations that footage can't show:
   - `flyapart`, `year_counter`, `orbits`, `rotation_curve`
   - `mw_spiral`, `halo_expand`, `halo_full`, `spectrum`, `spacetime`
   - `collision`, `balance`, `pie`, `cosmic_web`, `cosmic_web_glow`, `galactic_orbit`, `wind`
   - `lz_tank`, `lz_flash`, `probability`, `observatory`
   - `bh_shrink`, `dark_star`, `hidden_companion`, …

   Keep each under ~10 s. Prefer an `N` card when the point is a number.
7. **L lower thirds** for every person the first time the story names them ("KARL SCHWARZSCHILD | German
   astronomer · 1873-1916"). **callout / route / hud** over footage when the shot shows the thing:
   - a ring on Sgr A*
   - a line from Earth to Cygnus X-1
   - the Webb view

   Set `x`/`y` from the review sheet frame. Charts only with published data.
8. **T** only when the rule (cut, dip in long pauses, flare on moments) is wrong for a spot, e.g. a whip for
   a jump in scale.

## edit.base.json (v3)
```json
{"style": "v3", "lead_in": 0.5,
 "title": {"kicker": "10 facts about", "main": "Black Holes"},
 "cards": {"fact10": ["FACT #10", "PREDICTED IN *1783*, BY A VILLAGE PRIEST"], ...},
 "count_total": 10,
 "music": [{"from": "hook", "track": "Interloper.mp3"}, {"from": "cold_open", "track": "Long_Note_Three.mp3"},
           {"from": "fact10", "track": "Dark_Fog.mp3"}, ...],
 "grade": {"preset": "amber_teal", "contrast": 0.25, "sat": 1.3, "vignette": 0.35, "grain": 3},
 "card_query": [...], "bg_query": [...], "pin": {}, "ban": [], "crops": {}, "exclude": {}}
```
- Music: about one cue per act (2 facts), from `$MEDIA/music` (`fetch_media.sh <dir> "<Track Name>"` adds
  Kevin MacLeod tracks). Pick a pulsing track for the hook and darker beds for the story.
- Grade preset: by the topic's colour world (style guide §7).
- **Chapter cards without a number** (videos titled as a question, e.g. 04): `"cards": {"ch1": ["", "THE UNIVERSE
  HAS A *BIRTHDAY*"]}`. A non-numeric first entry (empty, or a kicker such as "PART ONE") gives a title card with
  a progress bar instead of FACT #n; the footer shows the video title. `*gold*` may span several words.
- `G <trigger> @ zeros:<n>:<label>` writes 1 followed by n zeros (e.g. `zeros:43:pieces of one second`).
  Anton has superscript digits (10²⁶) but no superscript minus, so write 10⁻⁴³ another way.
- `*word*` in card titles turns it gold.

**Footage search terms:** `footage/terms.txt`, one archive search term per line. Cover every concrete thing
named in the script (objects, missions, telescopes, places), plus general ones: galaxy, nebula, Earth,
observatory, simulation, zoom.

## Sanity numbers (`--plan-only` prints them; 10 facts, about 12 min)
| Measure | Target |
|---|---|
| Footage scenes | about 220-250 (a different shot each) |
| Cuts per minute | 15-19 |
| Scene length | median about 3 s, p10-p90 2-5.5 s |
| SFX per minute | 18-25 |
| Breaths | 3-5 |
| Headlines | 12-25 |
| Key lines | about 30-40 |
| Number cards | at least 2 per fact that has numbers |

Production 01/02 plans are v2 (no `style`): `render_v2.py`, a running subtitle, 2.5 s scenes.
