---
name: educontent-pipeline-agent
description: Automated educational video pipeline — Notion syllabus → YouTube scrape → NotebookLM → TTS voice clone → YouTube publish
version: 3.0.0
author: Azam Rizwan
streams: [MBBS, BTech]
---

# EduContent Pipeline Agent v3

> **One-liner**: Fully automated pipeline that picks a topic from Notion, scrapes YouTube, generates video via NotebookLM, clones voice with TTS, post-processes with FFmpeg, and publishes to YouTube.

---

## 📁 Project Structure (v3 — Solidified)

```
d:\notebook lm\
├── config\
│   ├── config.json          ← API keys, Notion DB IDs, pipeline settings
│   └── .env                 ← Secrets (gitignored)
├── core\
│   └── server.js            ← Express API entrypoint (port 3001)
├── modules\
│   ├── orchestrator\
│   │   ├── run_pipeline.js  ← Master pipeline orchestrator
│   │   └── CONTEXT.md       ← Module docs (load on-demand)
│   ├── tts\
│   │   └── CONTEXT.md       ← TTS engine docs
│   ├── thumbnails\          ← AI-powered thumbnail generator (Gemini)
│   │   ├── scripts\         ← Python generation scripts
│   │   ├── assets\headshots\← Drop headshot PNG here
│   │   └── CONTEXT.md       ← Thumbnail docs
│   └── uploader\
│       ├── youtube_uploader.js
│       └── CONTEXT.md       ← Upload/playlist docs
├── tools\                   ← Browser automation + Colab management
│   ├── chrome_bridge.js     ← Chrome debug port connection (Mode A only)
│   ├── colab_launcher.js    ← Colab notebook "Run All" + Gradio URL extraction
│   ├── colab_manager.js     ← Colab session health + auto-relaunch
│   ├── notebooklm_controller.js ← NotebookLM browser automation
│   ├── topic_strategy.js    ← YouTube trend analysis + branching
│   └── utils\               ← Shared utilities
│       ├── retry.js         ← Generic retry-with-backoff wrapper
│       └── paths.js         ← Centralized path constants
├── scripts\                 ← Utility scripts (Notion setup, scraper, syllabus)
│   └── CONTEXT.md           ← Script docs
├── video\                   ← FFmpeg post-processor + TTS generator
│   ├── post_processor.js    ← Branding pipeline (intro/outro/overlays)
│   ├── tts_generator.js     ← Qwen3 TTS via Colab Gradio
│   └── CONTEXT.md           ← Render docs
├── voice\                   ← Reference voice samples for TTS cloning
├── data\                    ← Scraped data, transcripts, temp inputs
├── output\videos\           ← Final rendered MP4s
├── logs\                    ← Runtime logs (auto-created)
├── dashboard\               ← Frontend UI
├── CLAUDE.md                ← GSD + Ralph Loop integration config
└── GEMINI.md                ← Project-level AI efficiency rules
```

---

## ⚡ Quick Commands

| Action | Command |
|---|---|
| Start API server | `node core/server.js` |
| Run BTech pipeline | `node modules/orchestrator/run_pipeline.js BTech` |
| Run MBBS pipeline | `node modules/orchestrator/run_pipeline.js MBBS` |
| Resume after NotebookLM | `node modules/orchestrator/run_pipeline.js --resume <args>` |
| Generate YouTube token | `node modules/uploader/youtube_uploader.js` |
| Reset Notion workspace | `node scripts/clean-notion.js` |
| Rebuild syllabus DBs | `node scripts/setup-notion-dbs.js` |
| Clean garbage | `/clean-garbage` workflow |

---

## 🧭 Context Loading Rules

> **DO NOT read this entire file plus all CONTEXT.md files on every task.**

1. Read **this file** for orientation only
2. Read **only** the `CONTEXT.md` in the module you are working on
3. If the task spans multiple modules, read only those relevant CONTEXT.md files
4. For trivial tasks (single file, one-liner), skip all context loading
