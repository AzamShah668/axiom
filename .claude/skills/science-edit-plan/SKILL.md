---
name: science-edit-plan
description: Write the edit plan (edit.spec) for a science-channel video - a visual query for every sentence, an English caption per sentence, explanatory graphics, chapter cards and music - and compile it to edit.json. Use for stage 3 of science-video or when changing what appears on screen.
---

# Edit plan (stage 3)

Files in `productions/NN-slug/`:
- `edit.spec` - human-editable plan (the source of truth)
- `edit.base.json` - lead-in, title card, chapter cards, music map, card/background queries, pins/bans
- `edit.json` - compiled; never edit by hand

Build and check:
```bash
scripts/science/pipeline.sh productions/NN-slug edit
# make_edit.py spec+base -> edit.json, then assign_shots.py --plan-only: every trigger must exist in the narration
```

## edit.spec syntax
Each section starts with `== <section_id>`. Then lines:
```
V <trigger|-> @ <visual query> [| <alternative query> ...]   footage beat, cut into ~2.5 s scenes
G <trigger|-> @ <graphic>                                    explanatory graphic over dark moving footage
C <trigger|-> | <English caption> [| big]                    caption from the moment the trigger is spoken
B <trigger>                                                  boom on a big moment
```
- A trigger is the **first** occurrence of that exact text in the section's Devanagari narration. `-` means
  the section start. Copy triggers from `tts/narration.hi.md`; nukta letters (ज़, ड़) must match exactly.
- Triggers must appear in narration order. `--plan-only` fails on a missing trigger.

## Writing rules
- **Visual beat per sentence (or clause).** Each `V` query describes what a 4K space-archive shot should look
  like, in plain English, the way you'd describe a frame:
  - Good: "zooming into a galaxy cluster", "the Hubble Space Telescope in orbit", "observatory dome
    under a starry sky timelapse", "planet Earth seen from space at night".
  - Not: abstract ideas ("the truth"), people's names, or text.
  - Add 1-2 alternatives with `|` for variety.
- Every scene gets a different shot, so a long beat needs a query broad enough for several shots.
- **Graphics** (`render_video.gfx`), for explanations only (numbers, comparisons, diagrams):
  - `flyapart`, `year_counter`, `orbits`, `rotation_curve`
  - `mw_spiral`, `halo_expand`, `halo_full`, `spectrum`, `spacetime`
  - `collision`, `balance`, `pie`, `cosmic_web`, `cosmic_web_glow`, `galactic_orbit`, `wind`
  - `lz_tank`, `lz_flash`, `probability`, `observatory`

  Keep each graphic under ~10 s; follow it with footage. New graphics go into
  `scripts/video/render_video.py` `gfx()`. Keep labels above y=800 so captions never overlap them.
- **Captions:**
  - One `C` per sentence, English, short (fits 1700 px at 62 px Anton).
  - Split long sentences into two captions ("...").
  - `big` for names, places, years and key numbers ("1933", "THE COMA CLUSTER", "85% OF ALL MATTER...").
  - Big captions avoid beats whose graphic has big centre text.
- **Booms** (`B`) on 2-4 moments only (collisions, the reveal).
- **edit.base.json:**
  - `cards`: `{"fact10": ["FACT #10", "DISCOVERED IN 1933, IGNORED FOR 40 YEARS"], ...}`
  - `title_card`
  - `music`: `[{"from": section, "track": "Dark_Fog.mp3"}]`, about one track per 2 facts, from `$MEDIA/music`
  - `card_query` / `bg_query`: footage under cards and graphics
  - `pin` / `ban` (see science-render)
- **Footage search terms:** `footage/terms.txt`, one archive search term per line. Cover every concrete thing
  named in the script (objects, missions, telescopes, places), plus general ones: galaxy, nebula, Earth,
  observatory, simulation, zoom.

## Sanity numbers (10-fact, ~12 min video)
- ~250 items (~220 footage scenes, ~20 graphics, 11 cards), ~180 captions.
- Scene length median ~2.3 s, max under ~4 s.
- `--plan-only` prints these.
