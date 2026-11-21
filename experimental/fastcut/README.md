# Fast-cut edits (separate project, NOT part of the main pipeline)

Owner, 2026-11-21: "keep this as a separate project. Do not integrate it into our main video production pipeline."
A faster, curiosity-driven re-edit style, studied from a reference video (kitsuna, "Why Japan Gave Up on Love"):
a new visual on every key word (literal or metaphor), stock + archive + images + own animations in quick succession,
big punch words, black-and-white mood beats, background sound design and intense moments. Combined with our own
documentary style, Flow clips and graphics, which all stay.

- Nothing here changes scripts/ or productions/. The main tools are only *called* (make_edit, assign_shots,
  render_v3, unmodified) with this folder's plan; everything new (sound design, mood grade, shake) lives here.
- Footage only from free licences (NASA, ESA, ESO, NOIRLab, Wikimedia Commons, Pexels/Pixabay for Earth scenes) and
  our Flow clips: never film/TV/news clips (copyright strikes), even though the reference uses them.
- Per video: `<NN-slug>/edit.spec`, `edit.base.json`, `post.json` (mood grade, shake, sound design cues);
  work files in `work/fastcut/<NN-slug>/`.
