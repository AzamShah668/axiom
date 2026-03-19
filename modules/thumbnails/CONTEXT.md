# Thumbnails Module

## Purpose
AI-powered YouTube thumbnail generator using Gemini 3 Pro Image Preview. Generates 4 professionally designed thumbnail variations per video topic, composited with a headshot.

## Origin
Integrated from [AI-Essentials/claude-thumbnails](https://github.com/AI-Essentials/claude-thumbnails) by Tyler Germain @ Friday Labs.

## Key Files
| File | Purpose |
|---|---|
| `scripts/generate_thumbnail.py` | Core generation via Gemini API |
| `scripts/search_examples.py` | Scrape high-performing competitor thumbnails |
| `scripts/combine_thumbnails.py` | Create 2×2 comparison grid |
| `assets/headshots/` | Drop your headshot PNG/JPG here |
| `SKILL.md` | Full strategy guide + prompt templates |

## Requirements
- **Python**: `google-genai`, `Pillow`, `pillow-avif-plugin`, `requests`
- **API Key**: `GEMINI_API_KEY` in `config/.env`
- **Optional**: `SCRAPECREATORS_API_KEY` for competitor thumbnail scraping

## Quick Usage
```powershell
# Generate a thumbnail
py modules/thumbnails/scripts/generate_thumbnail.py \
  --headshot "modules/thumbnails/assets/headshots/azam.png" \
  --prompt "A professional YouTube thumbnail..." \
  --output "output/videos/thumbnail_a.png"

# Search competitor thumbnails
py modules/thumbnails/scripts/search_examples.py \
  --query "Newton's Laws Physics" --top 5 --min-views 10000

# Create comparison grid
py modules/thumbnails/scripts/combine_thumbnails.py \
  --images a.png b.png c.png d.png \
  --output comparison.png --labels A B C D
```

## Workflow
1. Give a video topic → AI defines 4 desire-loop concepts
2. Fetches competitor thumbnails as style references
3. Generates 4 unique thumbnails via Gemini (parallel)
4. Creates a 2×2 comparison grid
5. User picks direction → iterate with refinements

## Note
The old Canvas-based `scripts/thumbnail_generator.js` is now superseded by this AI-powered module. It can be removed once this module is fully validated.
