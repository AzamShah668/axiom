# AXIOM — Automated EduContent Pipeline

![Node.js](https://img.shields.io/badge/Node.js-18+-green) ![License](https://img.shields.io/badge/License-Proprietary-blue)

**AXIOM** is a fully automated educational video production pipeline that transforms Notion syllabus topics into production-ready YouTube videos. It orchestrates research via NotebookLM, generates voiceovers via TTS (Qwen3 / CosyVoice 2), renders with Remotion/FFmpeg, and publishes to YouTube—all without manual intervention.

## What It Does

```
📚 Notion Syllabus (Topics)
    ↓
🔍 YouTube Research (Trend Analysis)
    ↓
🧪 NotebookLM Generation (Audio Overview)
    ↓
🎙️ TTS Voiceover (Local Voice Clone)
    ↓
🎬 FFmpeg Post-Processing (Branding, Watermark Removal)
    ↓
🎨 AI Thumbnail Generation (Gemini)
    ↓
📤 YouTube Upload (Playlists, SEO Optimization)
    ↓
✅ Notion Update (Completion Tracking)
```

## Features

- **No Manual Intervention**: Full pipeline automation from topic selection to upload
- **Voice Cloning**: Generate voiceovers using your voice sample (CosyVoice 2 / Qwen3 TTS)
- **Intelligent Research**: Scrapes YouTube, analyzes trends, decides single-video vs. multi-branch strategies
- **NotebookLM Integration**: Auto-generates research-backed scripts and audio overviews
- **Watermark Removal**: Automatically crops NotebookLM branding, adds AXIOM intro
- **Viral SEO**: AI-generated titles, keyword-rich descriptions, 29+ competitive tags
- **Dashboard UI**: Web-based control panel for queue management, publishing, and analytics
- **Dual-Stream Support**: MBBS (Medical) and BTech (Engineering) curricula
- **Video Tracking**: Central database of all produced videos across streams and subjects

## Tech Stack

| Component | Technology |
|---|---|
| **Language** | Node.js (v18+) |
| **Automation** | Puppeteer, Playwright |
| **Video Processing** | FFmpeg, Canvas, Remotion |
| **APIs** | YouTube Data v3, Notion, Gemini, OpenRouter |
| **TTS** | CosyVoice 2 / Qwen3 (Colab-based) |
| **Database** | Notion (as source of truth) |
| **Frontend** | React (Vite), Express API |
| **Scheduling** | node-cron |

## Project Structure

```
axiom/
├── config/                     # Configuration & credentials (.env)
├── core/                       # Express API server (port 3001)
├── modules/
│   ├── orchestrator/          # Master pipeline coordinator
│   ├── thumbnails/            # AI thumbnail generation (Gemini)
│   ├── tts/                   # TTS engine management
│   ├── uploader/              # YouTube Data API v3 upload
│   └── scheduler/             # Cron job runner
├── tools/                      # Browser automation & Colab management
│   ├── chrome_bridge.js       # Chrome DevTools Protocol
│   ├── colab_launcher.js      # Colab notebook automation
│   ├── colab_manager.js       # Colab session health checks
│   ├── notebooklm_controller.js # NotebookLM browser control
│   └── topic_strategy.js      # YouTube trend analysis
├── video/                      # FFmpeg post-processor & TTS wrapper
│   ├── post_processor.js      # Branding pipeline
│   ├── tts_generator.js       # TTS API wrapper
│   └── video/CONTEXT.md       # Video rendering docs
├── scripts/                    # Utility scripts
│   ├── setup-notion-dbs.js   # Initialize Notion structure
│   └── clean-notion.js        # Reset workspace
├── dashboard/                  # React Vite frontend
├── docs/                       # Documentation
├── logs/                       # Runtime logs (auto-created)
├── data/                       # Scraped data & transcripts
└── output/videos/              # Rendered MP4s
```

## Getting Started

### Prerequisites

- **Node.js** v18+ and npm
- **Python 3.9+** (for Colab TTS bridge)
- **Google Chrome** (for automation)
- **FFmpeg** (for video processing)
- **API Keys**: YouTube, Notion, Gemini, OpenRouter
- **Google Colab Account** (for TTS notebooks: Qwen3 or CosyVoice 2)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/AzamShah668/axiom.git
cd axiom

# 2. Install dependencies
npm install

# 3. Set up environment variables
cp .env.example config/.env
# Edit config/.env with your API keys

# 4. Initialize Notion databases (one-time setup)
node scripts/setup-notion-dbs.js

# 5. Start the API server
node core/server.js

# 6. (Optional) Start the dashboard in another terminal
cd dashboard && npm run dev
```

## Configuration

All secrets and API keys go in `config/.env` (gitignored). The `.env.example` file shows all required variables:

```env
# YouTube Data API v3
YOUTUBE_API_KEY=your_youtube_api_key_here

# Notion Internal Integration Token
NOTION_TOKEN=your_notion_internal_integration_token_here

# Gemini API Key (for thumbnail generation)
GEMINI_API_KEY=your_gemini_api_key_here

# OpenRouter API Key (for LLM-powered enhancements)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: ScrapeCreators API Key
SCRAPECREATORS_API_KEY=your_scrapecreators_api_key_here

# Optional: Custom TTS Colab notebook URL
# TTS_COLAB_URL=https://colab.research.google.com/drive/YOUR_NOTEBOOK_ID
```

Additionally, `config/config.json` contains non-secret configuration (Notion database IDs, YouTube settings, pipeline parameters). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Usage

### Run the Full Pipeline

```bash
# Trigger pipeline for the next pending topic (BTech stream)
node modules/orchestrator/run_pipeline.js BTech

# Or MBBS stream
node modules/orchestrator/run_pipeline.js MBBS

# Resume a pipeline after manual NotebookLM editing
node modules/orchestrator/run_pipeline.js --resume "<NotionPageId>" "<Subject>" "<Chapter>" "<PathToMP4>" "<PathToTranscript>"
```

### Dashboard UI

Visit **http://localhost:3001** after starting the server. The dashboard provides:

- **Queue View**: Pending topics by stream and subject
- **🚀 Publish Button**: Trigger pipeline for next topic or specific topic
- **Analytics**: Subscriber count, view count, video count
- **Activity Log**: Real-time pipeline status and errors

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/stats` | Channel statistics (subs, views, videos) |
| GET | `/api/queue` | Pending topics from Notion |
| POST | `/api/run-pipeline` | Trigger pipeline for next topic (body: `stream`) |
| POST | `/api/run-pipeline-topic` | Trigger for specific topic (body: `pageId`) |
| POST | `/api/upload` | Upload NotebookLM assets (multipart) |

### CLI Utilities

```bash
# Initialize Notion databases (MBBS, BTech, Video Tracker, Pipeline Queue)
node scripts/setup-notion-dbs.js

# Reset Notion workspace (DANGEROUS — deletes all databases)
node scripts/clean-notion.js

# Generate YouTube OAuth token (interactive)
node modules/uploader/youtube_uploader.js
```

## Architecture

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for detailed system design, pipeline flow, and integration points.

## Sprints & Roadmap

- **Sprint 1**: Core pipeline (Notion → NotebookLM → FFmpeg → YouTube) ✅ DONE
- **Sprint 2**: Dashboard UI + YouTube Analytics ✅ DONE
- **Sprint 3**: Advanced SEO, competitor thumbnail scraping, voice cloning refinement (PLANNED)

See **[docs/SPRINT-LOG.md](docs/SPRINT-LOG.md)** for detailed progress.

## Development

### Key Modules

- **`modules/orchestrator/CONTEXT.md`**: Pipeline orchestration logic
- **`modules/thumbnails/CONTEXT.md`**: AI thumbnail generation
- **`modules/tts/CONTEXT.md`**: TTS engine integration
- **`modules/uploader/CONTEXT.md`**: YouTube upload & playlist management
- **`video/CONTEXT.md`**: FFmpeg post-processing pipeline

### Token Efficiency Rules

See **[CLAUDE.md](CLAUDE.md)** and **[GEMINI.md](GEMINI.md)** for AI assistant best practices.

## Troubleshooting

### Colab URL Expired
The pipeline auto-detects and relaunches the Colab notebook if the Gradio URL is stale. If manual intervention is needed, check `tools/colab_manager.js`.

### NotebookLM Generation Timeout
If NotebookLM fails to generate audio, the pipeline saves the topic brief to file and prompts for manual intervention via dashboard logs.

### YouTube Upload Fails
Verify your YouTube OAuth token is fresh. Run:
```bash
node modules/uploader/youtube_uploader.js
```

## Support

For issues, documentation, or feature requests, see [docs/](docs/) or contact the maintainer.

## License

Proprietary — All rights reserved.
