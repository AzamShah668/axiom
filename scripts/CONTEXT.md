# Scripts Module

## Purpose
Standalone utility scripts for setup, data management, and content scraping.

## Files
| Script | Purpose |
|---|---|
| `setup-notion-dbs.js` | One-time Notion database creation |
| `clean-notion.js` | Reset/wipe Notion workspace |
| `youtube_scraper.js` | Smart YouTube search + dynamic topic splitting |
| `generate_full_syllabus.js` | Generate syllabus JSON from PDFs |
| `transcript_enhancer.js` | LLM-powered transcript rewriting |
| `seo_generator.js` | YouTube SEO metadata generator |
| `thumbnail_generator.js` | Canvas-based thumbnail creator |
| `postprocess.js` | Lightweight post-processing helper |
| `temp_read_pdfs.js/.py` | PDF text extraction (temporary) |
| `get_id.js` | Quick Notion page ID lookup |

## Smart Scraper Logic
The scraper (`youtube_scraper.js`) doesn't just grab URLs — it thinks:
1. **Playlist Detection**: If top result is a playlist, fetch all videos
2. **Title Extraction**: Pull exact title of each playlist video
3. **Dynamic Notion Split**: Rename current topic → first video title, create `Pending` rows for rest
4. **Single URL Focus**: Only first video URL passes to NotebookLM
5. **Guardrail Prompt**: Hyper-specific context to prevent scope creep

## API Limits
- **YouTube Data API**: 10,000 units/day (search = 100 units)
- **Notion API**: 3 req/sec rate limit
- **NotebookLM free**: 100 notebooks, 50 sources each, 50 daily queries
