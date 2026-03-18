---
name: educontent-pipeline-agent
description: End-to-end automated pipeline — Notion syllabus → Smart YouTube scrape → NotebookLM research → native video creation → TTS voice clone → YouTube publish
version: 2.0.0
author: Azam Rizwan
streams: [MBBS, BTech]
---

# EduContent Pipeline Agent v2

> **Purpose**: Automate the creation of educational YouTube videos for MBBS and BTech students.
> **Strategy**: One topic per stream per day, round-robin across subjects. The Smart Scraper dynamically splits broad topics into focused, targeted videos.

---

## 🔧 Project Structure

```
d:\notebook lm\
├── config.json                    ← API keys, Notion DB IDs, pipeline settings
├── agent.md                       ← THIS FILE (reusable agent instructions)
├── client_secret_...json          ← YouTube OAuth credentials
├── scripts\
│   ├── run_pipeline.js            ← 🚀 MASTER ORCHESTRATOR (start here)
│   ├── setup-notion-dbs.js        ← One-time Notion DB setup
│   ├── clean-notion.js            ← Reset Notion workspace
│   ├── youtube_scraper.js         ← Smart scrape + dynamic topic splitting
│   └── generate_full_syllabus.js  ← Syllabus JSON generator
├── uploader\
│   └── youtube_uploader.js        ← YouTube upload + playlist management
├── video\
│   ├── tts_generator.js           ← Qwen TTS voice clone wrapper
│   └── post_processor.js          ← FFmpeg audio-swap, watermark crop, trim
├── voice\
│   ├── Recording (9).m4a          ← Reference voice sample
│   └── voice.md                   ← Reference text for voice cloning
├── data\                          ← Scraped data, transcripts, temp files
└── output\                        ← Final rendered videos
```

---

## 🗃️ Notion Database IDs (Live)

| Database | ID | Purpose |
|---|---|---|
| **MBBS Master Syllabus** | `32629d9d-9c6e-8115-b8ac-e1cf8f6a4b6c` | All MBBS topics (Subject → Chapter → Topic) |
| **BTech Master Syllabus** | `32629d9d-9c6e-8176-835e-db51610aab76` | All BTech topics (Subject → Chapter → Topic) |
| **Global Video Tracker** | `32629d9d-9c6e-812f-b271-d4c45c556fdc` | Published video logs |
| **Pipeline Queue** | `32629d9d-9c6e-81bd-957e-cce67271f3e5` | Orchestration state |

**Parent Page**: `32629d9d-9c6e-8045-b22d-fc81f673800a`

---

## 🔑 Credentials

| Credential | Location | Status |
|---|---|---|
| YouTube Data API Key | `config.json → youtube.api_key` | ✅ |
| Notion Integration Token | Hardcoded in scripts | ✅ |
| NotebookLM MCP | Antigravity built-in | ✅ |
| YouTube Upload OAuth | `client_secret_...json` → token via first run | ✅ Provided |
| Qwen TTS GPU Engine | `C:\Users\AZAM RIZWAN\qwen-tts-gpu\` | ✅ Installed |

---

## 🚀 How to Run

### Full Pipeline (Automated)
```powershell
# Run for BTech stream:
node "d:\notebook lm\scripts\run_pipeline.js" BTech

# Run for MBBS stream:
node "d:\notebook lm\scripts\run_pipeline.js" MBBS
```

The orchestrator will:
1. **PICK** the next `Pending` topic from the Notion Master DB
2. **SCRAPE** YouTube intelligently (with Dynamic Topic Splitting)
3. **PAUSE** for the AI Agent to run NotebookLM (browser sub-agent)
4. Print a `--resume` command to continue after NotebookLM is done

### Resume After NotebookLM
```powershell
node "d:\notebook lm\scripts\run_pipeline.js" --resume "<NotionPageId>" "<Subject>" "<Chapter>" "<PathToMP4>" "<PathToTranscriptText>"
```

This will:
4. **TTS** — Clone voice using Qwen TTS GPU
5. **POST-PROCESS** — FFmpeg audio-swap + watermark crop + outro trim
6. **UPLOAD** — YouTube upload + dual playlist assignment
7. **UPDATE** — Mark Notion status as Completed with video URL

---

## 🧠 Smart YouTube Scraper Logic

The scraper (`youtube_scraper.js`) doesn't just grab URLs — it thinks:

1. **Playlist Detection**: If the top YouTube result is a playlist, it fetches all videos inside.
2. **Title Extraction**: It pulls the **exact title** of each video in the playlist (e.g., "Intro to Linked Lists", "Doubly Linked Lists").
3. **Dynamic Notion Split**: It renames the current Notion topic to the first video's title, and creates new `Pending` rows for the remaining titles.
4. **Single URL Focus**: Only the first video's URL is passed to NotebookLM.
5. **Guardrail Prompt**: A hyper-specific context prompt is generated (e.g., *"Your SOLE FOCUS is: 'Intro to Linked Lists'. Do NOT summarize the full topic."*) to prevent NotebookLM from going off-scope.

---

## 🔄 Daily Pipeline Flow (10 Steps)

```
1. PICK    → Next Pending topic from Notion Master DB
2. CHECK   → Not already in Video Tracker
3. SCRAPE  → Smart YouTube search + Dynamic Split
4. FEED    → Create NotebookLM notebook with single focused URL
5. GEN     → Trigger Audio Overview, download MP4 + transcript
6. TTS     → Qwen TTS voice clone (GPU, cuda:0)
7. RENDER  → FFmpeg: audio-swap, crop watermark, trim outro
8. PUBLISH → YouTube upload + Subject & Chapter playlists
9. UPDATE  → Mark Completed in Notion, log URL
10.ADVANCE → Round-robin to next subject/stream
```

---

## 📤 YouTube Playlist Strategy

YouTube doesn't support nested playlists. Workaround:

- **Subject Playlist**: `[BTech] Data Structures Full Course`
- **Chapter Playlist**: `Linked Lists | Data Structures`
- Every uploaded video gets added to **both** playlists automatically.

---

## 🎙️ TTS Voice Cloning

**Engine**: Qwen TTS (local GPU, cuda:0)
**Reference Audio**: `d:\notebook lm\voice\Recording (9).m4a`
**Reference Text**: `d:\notebook lm\voice\voice.md`

The `tts_generator.js` module handles passing the NotebookLM transcript text to the local Python TTS engine and saving the output `.wav`.

---

## 🎬 Post-Processing (FFmpeg)

The `post_processor.js` module:
1. **Mutes** original NotebookLM audio
2. **Syncs** new Qwen TTS audio track
3. **Crops** bottom 60px to remove NotebookLM watermark
4. **Trims** video to match audio length (removing outro)
5. Outputs `final_output.mp4`

---

## 🚨 Error Handling

| Error | Action |
|---|---|
| YouTube API quota exceeded | Wait 24h, retry next day |
| NotebookLM rate limit (50/day free) | Use `re_auth` to switch account |
| NotebookLM generation fails | Retry once, then mark `Failed` in Notion |
| Notion API error | Retry 3x with 2s delay |
| YouTube upload auth expired | Re-run uploader with no args to refresh token |
| Topic has no good YouTube results | Mark `Failed`, advance to next |
| TTS engine unavailable | Check GPU/CUDA, fallback to manual voiceover |

---

## 📊 Quick Commands

| Action | Command |
|---|---|
| Run BTech pipeline | `node scripts/run_pipeline.js BTech` |
| Run MBBS pipeline | `node scripts/run_pipeline.js MBBS` |
| Resume after NotebookLM | `node scripts/run_pipeline.js --resume ...` |
| Generate YouTube token | `node uploader/youtube_uploader.js` (no args) |
| Reset Notion workspace | `node scripts/clean-notion.js` |
| Rebuild syllabus DBs | `node scripts/setup-notion-dbs.js` |

---

## 📝 API Limits

- **NotebookLM free**: 100 notebooks, 50 sources each, 50 daily queries
- **YouTube Data API**: 10,000 units/day (search = 100 units)
- **Notion API**: 3 req/sec rate limit
- **Qwen TTS**: Limited by GPU VRAM (requires cuda:0)
