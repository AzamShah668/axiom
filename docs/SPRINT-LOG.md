---
project: AXIOM — Automated EduContent Pipeline
type: sprint-log
last_updated: 2026-06-21
status: active
---

# Sprint Log

## Sprint 1 — Core Pipeline (DONE)

**Goal**: Build end-to-end pipeline from Notion topic selection to YouTube upload.

### Delivered

- ✅ Notion database architecture (MBBS, BTech, Video Tracker, Pipeline Queue)
- ✅ YouTube scraper (`scraper/youtube_scraper.js`) — retrieves relevant videos by topic
- ✅ NotebookLM browser automation (`tools/notebooklm_controller.js`) — creates notebooks, generates audio overviews
- ✅ Colab TTS integration (`video/tts_generator.js`) — CosyVoice 2 voice cloning via Gradio API
- ✅ FFmpeg post-processor (`video/post_processor.js`) — watermark removal, audio replacement, intro/outro editing
- ✅ YouTube uploader (`modules/uploader/youtube_uploader.js`) — OAuth2, playlist management, video publishing
- ✅ Orchestrator (`modules/orchestrator/run_pipeline.js`) — master pipeline coordinator
- ✅ Configuration layer (`config/config.json`) — centralized settings for all integrations

### Open

- **Transcript Timestamp Generator** (`video/engines/engine_1_transcribe.py`) — NOT YET BUILT
- **Visual Slicer & Forced Alignment** (`video/engines/engine_2_sync.py`) — NOT YET BUILT
  - Current limitation: Video and audio may fall slightly out of sync if TTS pacing differs from original
  - Plan: Implement Whisper-based word-level timestamps + FFmpeg time-stretch to keep visuals in perfect sync

---

## Sprint 2 — Dashboard + Analytics (DONE)

**Goal**: Build web UI for queue management, publishing control, and channel analytics.

### Delivered

- ✅ Express API server (`core/server.js`) — HTTP endpoints for all pipeline operations
- ✅ React + Vite dashboard (`dashboard/src/pages/Dashboard.jsx`)
  - ✅ Queue view — shows pending topics by stream and subject
  - ✅ **🚀 Publish** button — trigger pipeline for next topic
  - ✅ Per-topic **🚀** button — publish specific topic
  - ✅ Activity log — real-time pipeline status and errors
  - ✅ Analytics panel — subscriber count, total views, video count, completion rate
- ✅ Multer file upload handler — supports NotebookLM asset uploads
- ✅ YouTube channel stats endpoint (`GET /api/stats`)
- ✅ Notion queue endpoint (`GET /api/queue`)

### Open

- **Notion update notifications** — Dashboard doesn't auto-refresh when topics complete (manual refresh needed)
- **Video preview** — No embedded video previews in queue; links only
- **Performance analytics** — No per-video retention/engagement metrics (requires YouTube Analytics API)

---

## Sprint 3 — Advanced Features (IN PROGRESS / PLANNED)

**Goal**: Enhance SEO, add competitor analysis, refine voice cloning, and enable autonomous daily runs.

### In Progress

- **Viral Title Generation** (`scripts/seo_generator.js`)
  - 12 attention-grabbing title formulas
  - Algorithm-optimized descriptions with timestamps
  - 29+ competitive long-tail keyword tags
  - Status: ✅ COMPLETE (committed to main)

- **AI Thumbnail Generation** (`modules/thumbnails/scripts/render_thumbnail.js`)
  - Gemini-powered background generation
  - Headshot compositing with background removal (u2net)
  - 1280x720 PNG export
  - Status: ✅ COMPLETE (committed to main)

- **Topic Strategy & Branching** (`tools/topic_strategy.js`)
  - YouTube trend analysis (view velocity, relevance)
  - Single-video vs. multi-branch decision
  - Auto-creation of sibling Notion rows for branches
  - Status: ✅ COMPLETE (committed to main)

- **Colab Auto-Launch** (`tools/colab_launcher.js`)
  - Removes manual URL paste requirement
  - Auto-detects Colab notebook, clicks "Run All"
  - Extracts Gradio endpoint automatically
  - Status: ✅ COMPLETE (committed to main)

- **Colab Session Manager** (`tools/colab_manager.js`)
  - Monitors Colab URL health
  - Auto-relaunches if endpoint is stale
  - No manual intervention required
  - Status: ✅ COMPLETE (committed to main)

### Planned

- **Transcript Timestamp Alignment** (Engine 1 & 2)
  - Implement Whisper-based word-level timestamps
  - Use FFmpeg time-stretch to sync video with new TTS audio
  - Ensures visuals perfectly match voice pacing

- **Voice Quality Refinement**
  - A/B test CosyVoice 2 settings (exaggeration, CFG scale)
  - Support additional voice cloning models
  - Build voice library for different tones (dramatic, calm, energetic)

- **Competitor Thumbnail Scraping**
  - Integrate ScrapeCreators API
  - Analyze top competitor thumbnails for AXIOM subject
  - Auto-generate similar thumbnails with AXIOM branding

- **Autonomous Daily Scheduler**
  - Enable `modules/scheduler/scheduler.js` (node-cron)
  - Daily round-robin across MBBS/BTech subjects
  - Configurable publish time
  - Auto-failure recovery

- **YouTube Analytics Integration**
  - Per-video retention metrics (watch time, audience retention %)
  - Engagement tracking (likes, comments, shares)
  - Use analytics to inform future topic selection

- **Batch Processing**
  - Process multiple topics per day
  - Queue parallelization (e.g., generate 3 videos while 1 uploads)
  - Configurable batch size

---

## Blockers & Known Issues

| Issue | Severity | Status | Notes |
|---|---|---|---|
| Colab notebook timeout | MEDIUM | WORKAROUND | Manual URL paste required; auto-launch mitigates |
| NotebookLM API unavailable | HIGH | N/A | No official API; browser automation is only option |
| YouTube upload rate limits | MEDIUM | N/A | 1 video per day quota recommended |
| Notion API token expiry | LOW | MANUAL | Re-auth needed if token > 6 months old |
| Audio/video sync drift | MEDIUM | PLANNED (Sprint 4) | Requires Whisper + FFmpeg time-stretch |

---

## Key Metrics

| Metric | Current | Target |
|---|---|---|
| Pipeline success rate | ~85% (TBD) | 95%+ |
| Avg time per video | 20-50 min | 15-30 min |
| Daily capacity | 1 topic/day | 3+ topics/day |
| Video quality score | 7.5/10 (initial feedback) | 9/10 |
| Channel subscriber growth | TBD | 1000+ subs/month |

---

## Next Steps

1. **Verify current sprint 3 completions** — run full pipeline end-to-end on test topic
2. **Implement audio/video sync** (Engine 1 & 2) — critical for production quality
3. **A/B test voice engines** — compare CosyVoice 2 vs. Qwen3 output quality
4. **Enable autonomous scheduling** — let AXIOM run daily without human input
5. **Integrate YouTube Analytics** — use viewer data to improve topic selection
6. **Scale to batch processing** — process 3+ topics per day

---

## Session Notes

- All logs in `logs/` (auto-created)
- All renders in `output/videos/` (auto-created)
- Notion is source of truth for all topics and tracking
- Chrome Profile 4 auto-maintains login state (no credential storage)
- Configuration in `config/config.json` (gitignored `.env` for secrets)
