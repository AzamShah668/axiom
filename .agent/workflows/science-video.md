---
description: Make a Hindi science documentary (Science Time method) end to end - script, ElevenLabs narration, edit plan, unique 4K footage, render, review, preview, YouTube package.
---

Follow `.claude/skills/science-video/SKILL.md` and its stage skills in `.claude/skills/science-*/SKILL.md`.
Channel rules: `productions/README.md`. Scripted stages:

```bash
scripts/science/pipeline.sh productions/NN-slug setup
scripts/science/pipeline.sh productions/NN-slug narration edit footage assign   # then review $WORK/review_assign
scripts/science/pipeline.sh productions/NN-slug render review                   # then review $WORK/review_render
scripts/science/pipeline.sh productions/NN-slug preview credits
```
