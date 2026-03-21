# Orchestrator Module

## Purpose
Master pipeline coordinator. Picks topics from Notion, runs the full automated pipeline.

## Updated Pipeline Flow (v3)

```
1. PICK       → Next Pending topic from Notion Master DB
2. CHECK      → Not already in Video Tracker
3. STRATEGY   → tools/topic_strategy.js
                  • Searches YouTube for trend signals ONLY
                  • Decides: single video OR multi-branch series
                  • If branch: creates sibling Notion rows automatically
                  • Returns { strategy, branches, focusTopic, contextPrompt }
                  • ⚠️ NO YouTube URLs are passed downstream
4. COLAB      → tools/colab_launcher.js (FULLY AUTOMATED)
                  • Auto-opens Chrome (Profile 4: Axiom Academy)
                  • Clicks "Run All" in the Qwen TTS Colab notebook
                  • Extracts gradio.live URL → saves to video/colab_url.json
                  • (Skipped if Colab URL is still alive from a previous run)
                  • colab_manager.js auto-relaunches if URL is dead (NO manual paste)
5. NOTEBOOK   → tools/notebooklm_controller.js
                  • Opens notebooklm.google.com (same Chrome Profile 4)
                  • Creates new notebook
                  • Pastes Topic Brief as TEXT source (no URLs ever)
                  • Triggers VIDEO Overview generation (falls back to Audio if unavailable)
                  • Downloads output to output/notebooklm_raw/
                  • Writes handoff to output/notebooklm_handoff.json
6. RENDER     → video/post_processor.js (FFmpeg branding pipeline)
                  • Prepend intro → fade → main (watermark-cropped) → fade → outro
                  • AXIOM logo overlay + Subscribe button overlay
                  • Output: <input>_branded.mp4
7. THUMBNAIL  → modules/thumbnails/scripts/render_thumbnail.js
                  • AI background via Gemini
                  • Headshot compositing (canvas bg removal)
                  • Full 1280x720 PNG ready for YouTube
8. SEO        → scripts/seo_generator.js (VIRAL OPTIMIZATION)
                  • 12 attention-grabbing title formulas
                  • Algorithm-optimized description with timestamps
                  • 29+ competitive long-tail keyword tags
9. PUBLISH    → modules/uploader: YouTube API upload (PUBLIC by default)
                  • Attaches thumbnail, viral title, SEO description, tags
                  • Adds to Subject + Chapter playlists
10. UPDATE    → Mark Completed in Notion, log URL, ADVANCE to next topic
```

## What Changed in v3

| Old (v2) | New (v3) |
|---|---|
| processVideo(audio, text, topic, subject) | processVideo(videoPath) — fixed signature |
| Static SEO hook phrases | 12 viral title formulas + keyword-rich descriptions |
| YouTube uploads as "unlisted" | YouTube uploads as "public" (configurable) |
| colab_manager asks for manual URL paste | colab_manager auto-relaunches via colab_launcher.js |
| Dashboard "Run Master Pipeline" button | Dashboard "🚀 Publish" with stream selector + per-topic publish |

## Dashboard Trigger

The Dashboard (`dashboard/src/pages/Dashboard.jsx`) now has:
- **"🚀 Publish" button** with BTech/MBBS stream selector
- **Per-topic 🚀 button** on each queue item to publish a specific topic
- **Pipeline Activity Log** showing real-time status

## API Endpoints (core/server.js)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/stats` | YouTube channel statistics |
| GET | `/api/queue` | Notion pending topics queue |
| POST | `/api/run-pipeline` | Trigger pipeline for next pending topic by stream |
| POST | `/api/run-pipeline-topic` | Trigger pipeline for a specific topic by pageId |
| POST | `/api/upload` | Upload NotebookLM assets |

## Chrome Profile Used

- **Profile**: `Profile 4`
- **Account**: `fhjchvc6@gmail.com` (Axiom Academy)
- **Path**: `C:\Users\AZAM RIZWAN\AppData\Local\Google\Chrome\User Data\Profile 4`
- **No credentials stored in code** — uses your existing logged-in session

## Resume Command
```powershell
node modules/orchestrator/run_pipeline.js --resume "<NotionPageId>" "<Subject>" "<Chapter>" "<PathToMP4>" "<PathToTranscriptText>"
```

## Notion DB IDs
| Database | ID |
|---|---|
| MBBS Master | `32629d9d-9c6e-8115-b8ac-e1cf8f6a4b6c` |
| BTech Master | `32629d9d-9c6e-8176-835e-db51610aab76` |
| Video Tracker | `32629d9d-9c6e-812f-b271-d4c45c556fdc` |
| Pipeline Queue | `32629d9d-9c6e-81bd-957e-cce67271f3e5` |

## Error Handling
| Error | Action |
|---|---|
| Notion API error | Retry 3x with 2s delay |
| Topic has no YouTube results | Log warning, proceed with topic name only |
| Colab URL expired | colab_manager auto-relaunches via colab_launcher.js |
| NotebookLM generation timeout | Save brief to file, prompt manual intervention |
