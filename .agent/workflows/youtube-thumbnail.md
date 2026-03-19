---
description: Generate AI-powered YouTube thumbnails using Gemini. Creates 4 variations with headshot compositing and competitor analysis.
---

Generate professional YouTube thumbnails using Gemini 3 Pro. Produces 4 different thumbnail concepts, composited with your headshot.

## Prerequisites
- A headshot photo in `modules/thumbnails/assets/headshots/`
- `GEMINI_API_KEY` set in `config/.env`

## Steps

1. Ask the user for the **video topic/title** and whether any specific logos or visual assets should appear.

2. Search for competitor thumbnails as style inspiration (optional, requires `SCRAPECREATORS_API_KEY`):
```powershell
py modules/thumbnails/scripts/search_examples.py --query "{topic}" --top 5 --min-views 10000
```

3. Define 4 desire-loop concepts (end state, process, before/after, pain point). Describe each briefly to the user.

4. Generate all 4 thumbnails (run in parallel):
// turbo-all
```powershell
py modules/thumbnails/scripts/generate_thumbnail.py --headshot "modules/thumbnails/assets/headshots/{headshot}" --prompt "{concept A}" --output "output/videos/thumbnails/{slug}/a.png"
```
```powershell
py modules/thumbnails/scripts/generate_thumbnail.py --headshot "modules/thumbnails/assets/headshots/{headshot}" --prompt "{concept B}" --output "output/videos/thumbnails/{slug}/b.png"
```
```powershell
py modules/thumbnails/scripts/generate_thumbnail.py --headshot "modules/thumbnails/assets/headshots/{headshot}" --prompt "{concept C}" --output "output/videos/thumbnails/{slug}/c.png"
```
```powershell
py modules/thumbnails/scripts/generate_thumbnail.py --headshot "modules/thumbnails/assets/headshots/{headshot}" --prompt "{concept D}" --output "output/videos/thumbnails/{slug}/d.png"
```

5. Create a 2×2 comparison grid:
```powershell
py modules/thumbnails/scripts/combine_thumbnails.py --images "output/videos/thumbnails/{slug}/a.png" "output/videos/thumbnails/{slug}/b.png" "output/videos/thumbnails/{slug}/c.png" "output/videos/thumbnails/{slug}/d.png" --output "output/videos/thumbnails/{slug}/comparison.png" --labels A B C D
```

6. Present the comparison grid to the user. Ask which direction they prefer.

7. Iterate based on user feedback by passing the chosen thumbnail as `--reference`.
