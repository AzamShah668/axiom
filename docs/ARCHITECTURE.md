# AXIOM — System Architecture

## Overview

AXIOM is a fully automated educational video pipeline orchestrated around **Notion as the source of truth**. The system continuously picks topics from Notion, researches them, generates scripts via NotebookLM, produces voiceovers via TTS, post-processes with FFmpeg, and publishes to YouTube—all without manual intervention.

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AXIOM PIPELINE v3                            │
└─────────────────────────────────────────────────────────────────┘

1. PICK TOPIC
   Notion Master DB (MBBS / BTech) → Select next "Pending" topic
   ↓
2. STRATEGY
   tools/topic_strategy.js → YouTube trend analysis
   Decision: Single video OR multi-branch series?
   ↓
3. COLAB LAUNCH
   tools/colab_launcher.js → Auto-open Chrome Profile 4
   Click "Run All" → Extract Gradio URL → Save to colab_url.json
   (Skipped if URL still alive from previous run)
   ↓
4. NOTEBOOKLM GENERATION
   tools/notebooklm_controller.js → Create notebook
   Paste topic brief (text, not URLs)
   Trigger Video Overview generation
   Download MP4 → Save to output/notebooklm_raw/
   ↓
5. TTS GENERATION
   video/tts_generator.js → Call Colab Gradio API
   Input: Transcript + reference voice sample
   Output: WAV audio file with voice clone
   ↓
6. POST-PROCESSING
   video/post_processor.js → FFmpeg branding pipeline
   - Crop NotebookLM watermark (bottom 60px)
   - Replace audio (mute original, sync TTS)
   - Prepend AXIOM intro video
   - Overlay AXIOM logo (top-left, 60% opacity)
   - Overlay subscribe button (bottom-right, 80% opacity)
   Output: <topic>_branded.mp4
   ↓
7. THUMBNAIL GENERATION
   modules/thumbnails/scripts/render_thumbnail.js
   - AI background via Gemini
   - Headshot compositing with bg removal
   Output: 1280x720 PNG
   ↓
8. SEO OPTIMIZATION
   scripts/seo_generator.js → 12 viral title formulas
   - Algorithm-optimized description with timestamps
   - 29+ competitive long-tail keywords
   ↓
9. PUBLISH TO YOUTUBE
   modules/uploader/youtube_uploader.js → YouTube Data API v3
   - Authenticate via OAuth2
   - Upload MP4 + thumbnail
   - Create/add to Subject + Chapter playlists
   - Return published URL
   ↓
10. UPDATE NOTION
    Mark topic "Completed" → Log video URL
    Advance to next topic in queue
```

## Component Architecture

### 1. Core API Server (`core/server.js`)

**Role**: HTTP entrypoint for dashboard and CLI

**Exposed Endpoints**:
- `GET /api/stats` — Channel statistics (subscribers, views, video count)
- `GET /api/queue` — Pending topics from Notion
- `POST /api/run-pipeline` — Trigger pipeline (stream parameter)
- `POST /api/run-pipeline-topic` — Trigger for specific topic
- `POST /api/upload` — File upload handler (NotebookLM assets)

**Dependencies**: Express, googleapis, multer, dotenv

---

### 2. Orchestrator Module (`modules/orchestrator/run_pipeline.js`)

**Role**: Master pipeline coordinator

**Key Functions**:
- `runFullPipeline(stream)` — Main entry point
- Picks next "Pending" topic from Notion
- Validates topic is not in Video Tracker
- Calls each downstream component in sequence
- Handles errors and retry logic

**Flow**:
```
runFullPipeline("BTech")
  ├─ Notion: SELECT * WHERE status = "Pending"
  ├─ topic_strategy.js: Analyze YouTube trends
  ├─ colab_launcher.js: Launch TTS Colab (if needed)
  ├─ notebooklm_controller.js: Generate audio overview
  ├─ post_processor.js: FFmpeg branding
  ├─ render_thumbnail.js: AI thumbnail
  ├─ seo_generator.js: Viral metadata
  ├─ youtube_uploader.js: Publish
  └─ Notion: UPDATE topic status = "Completed", log URL
```

**Error Handling**:
- Notion API errors: Retry 3x with 2s delay
- Colab URL expired: Auto-relaunch via `colab_manager.js`
- NotebookLM timeout: Save brief to file, log error
- YouTube upload failure: Log and continue to next topic

---

### 3. Browser Automation Tools (`tools/`)

#### 3a. Chrome Bridge (`tools/chrome_bridge.js`)
- Opens Chrome DevTools Protocol (CDP) connection to Chrome Profile 4
- Used for Puppeteer-based automation when needed
- No credentials stored — uses existing logged-in session

#### 3b. Colab Launcher (`tools/colab_launcher.js`)
- Launches Google Colab notebook (Qwen3 TTS or CosyVoice 2)
- Auto-clicks "Run All"
- Extracts Gradio URL from page
- Saves to `video/colab_url.json` for downstream use
- Handles timeouts and retries

#### 3c. Colab Manager (`tools/colab_manager.js`)
- Monitors Colab URL health
- Auto-relaunches if URL is stale (404)
- Prevents manual URL pasting

#### 3d. NotebookLM Controller (`tools/notebooklm_controller.js`)
- Opens NotebookLM in Chrome Profile 4
- Creates new notebook
- Pastes topic brief (text source, NOT URLs)
- Triggers Video Overview generation
- Monitors progress and downloads output MP4
- Writes handoff JSON for downstream modules

#### 3e. Topic Strategy (`tools/topic_strategy.js`)
- Searches YouTube for trend signals
- Analyzes view counts, relevance
- Decides: Single video OR multi-branch series
- Returns strategy metadata for orchestrator

---

### 4. TTS Module (`modules/tts/` + `video/tts_generator.js`)

**Role**: Voice generation from transcript

**Supported Engines**:
- **CosyVoice 2** (default) — Colab-based TTS with voice cloning
- **Qwen3** — Fallback TTS engine

**Flow**:
```
tts_generator.js
  ├─ Read colab_url.json (Gradio API endpoint)
  ├─ Load reference voice sample (voice/Recording (14).m4a)
  ├─ Call Colab Gradio API with:
  │   ├─ Transcript (text)
  │   ├─ Reference voice (audio)
  │   └─ Voice clone configuration (exaggeration, CFG scale)
  ├─ Poll for completion
  └─ Download output WAV → data/tts_output.wav
```

**Configuration** (`config/config.json`):
```json
{
  "postprocessing": {
    "tts_engine": "CosyVoice 2",
    "use_custom_voice_clone": true
  }
}
```

---

### 5. Video Post-Processor (`video/post_processor.js`)

**Role**: FFmpeg-based video editing pipeline

**Steps**:
1. **Watermark Crop**: Remove bottom 60px (NotebookLM branding)
2. **Audio Replacement**: Mute original, sync new TTS audio
3. **Intro Splice**: Prepend AXIOM intro video
4. **Logo Overlay**: Add AXIOM watermark (top-left, 60% opacity)
5. **Subscribe Button**: Add overlay (bottom-right, 80% opacity)
6. **Final Render**: Export as MP4

**Configuration**:
```json
{
  "postprocessing": {
    "crop_watermark": true,
    "trim_outro": true,
    "insert_hooks": true
  }
}
```

**Dependencies**: FFmpeg, canvas

---

### 6. Thumbnail Generator (`modules/thumbnails/`)

**Role**: AI-powered YouTube thumbnail creation

**Process**:
- **Background**: AI-generated via Gemini API (context-aware)
- **Foreground**: Headshot image with background removal (u2net segmentation)
- **Output**: 1280x720 PNG ready for YouTube

**API**: Google Gemini v1.5

---

### 7. YouTube Uploader (`modules/uploader/youtube_uploader.js`)

**Role**: Publish videos to YouTube with metadata

**Process**:
1. OAuth2 authentication (generates refresh token on first run)
2. Create or fetch Subject playlist
3. Create or fetch Chapter playlist
4. Upload MP4 + thumbnail
5. Set title, description, tags
6. Add to both playlists
7. Publish as "Public" (configurable)
8. Return video URL

**API**: YouTube Data v3

**Dependencies**: googleapis

---

### 8. Notion Integration

**Role**: Central database for all topics, playlists, and video tracking

**Databases**:

| Database | ID | Purpose |
|---|---|---|
| MBBS Master | `32629d9d-9c6e-8115-b8ac-e1cf8f6a4b6c` | Medical stream topics |
| BTech Master | `32629d9d-9c6e-8176-835e-db51610aab76` | Engineering stream topics |
| Video Tracker | `32629d9d-9c6e-812f-b271-d4c45c556fdc` | All published videos |
| Pipeline Queue | `32629d9d-9c6e-81bd-957e-cce67271f3e5` | Processing queue |

**Schema per Syllabus DB**:
```
Topic (Title)
├─ Chapter (Select)
├─ Status (Select: Pending / In Progress / Completed / Failed)
├─ Video URL (URL)
└─ Created Date (Date)
```

**Notion Token**: Stored in `config/.env` as `NOTION_TOKEN`

---

### 9. Dashboard UI (`dashboard/`)

**Role**: Web-based control panel

**Features**:
- View pending topics queue
- **🚀 Publish** button to trigger pipeline
- Real-time activity log
- Channel analytics (subs, views, videos)

**Tech**: React + Vite

**API Integration**: Calls `core/server.js` endpoints

---

### 10. Scheduler (`modules/scheduler/scheduler.js`)

**Role**: Autonomous cron-based execution (optional)

**Features**:
- Daily topic selection and processing
- Round-robin across MBBS/BTech streams
- Configurable schedule

---

## Data Storage

| Data | Location | Storage | Notes |
|---|---|---|---|
| API Keys | `config/.env` | Gitignored | Never commit |
| Configuration | `config/config.json` | Committed | Non-secret settings |
| Logs | `logs/` | Gitignored | Auto-created on run |
| Scraped Data | `data/` | Gitignored | Transcripts, metadata |
| Rendered Videos | `output/videos/` | Gitignored | Final MP4s |
| NotebookLM Output | `output/notebooklm_raw/` | Gitignored | Raw audio overviews |
| Colab URL | `video/colab_url.json` | Gitignored | Gradio endpoint |
| Voice Samples | `voice/` | Committed | Reference audio |

---

## Chrome Profile Integration

**Profile**: `Profile 4` (AXIOM Academy)

**Location**: `C:\Users\AZAM RIZWAN\AppData\Local\Google\Chrome\User Data\Profile 4`

**Auto-Logged Accounts**:
- Axiom Academy YouTube channel
- Notion workspace
- Google Colab
- NotebookLM

**Why Profile 4**: Isolation from main Chrome profile; all automation uses existing logged-in sessions (no credential storage in code).

---

## Error Handling & Retry Logic

| Error | Severity | Retry | Action |
|---|---|---|---|
| Notion API timeout | HIGH | 3x, 2s delay | Fail topic, move to next |
| YouTube scraper no results | MEDIUM | 0x | Proceed with topic name only |
| Colab URL expired | MEDIUM | Auto | colab_manager relaunches |
| NotebookLM timeout | HIGH | 0x | Save brief, log for manual review |
| FFmpeg render failure | HIGH | 1x | Log error, skip topic |
| YouTube upload fail | HIGH | 1x | Log error, save for retry |

---

## Performance Characteristics

| Operation | Typical Duration |
|---|---|
| YouTube research | 2-5 minutes |
| Colab launch | 3-5 minutes (first run); instant (cached) |
| NotebookLM generation | 5-15 minutes |
| TTS generation | 2-5 minutes |
| FFmpeg post-processing | 3-8 minutes |
| Thumbnail generation | 1-2 minutes |
| YouTube upload | 2-5 minutes |
| **Full Pipeline** | **20-50 minutes per topic** |

---

## Security Considerations

1. **No Secrets in Code**: All API keys in `config/.env` (gitignored)
2. **Chrome Profile Auth**: Uses existing logged-in sessions; no passwords stored
3. **YouTube OAuth2**: Refresh token stored locally in encrypted config
4. **Notion Token**: Bearer token in environment variable
5. **Colab Session**: Auto-managed; no credentials exposed

---

## Extensibility

### Adding a New TTS Engine
1. Create new engine in `modules/tts/`
2. Implement interface: `generate(transcript, voiceSample) → WAV`
3. Update `config/config.json` with engine name
4. Update `tts_generator.js` routing logic

### Adding a New Post-Processor
1. Create new pipeline in `video/`
2. Implement interface: `process(inputMP4, transcript) → outputMP4`
3. Update orchestrator to call new pipeline

### Adding a New Uploader
1. Create new uploader in `modules/uploader/`
2. Implement interface: `upload(videoPath, metadata) → publishedURL`
3. Update orchestrator and dashboard routing

---

## Monitoring & Logging

- All logs go to `logs/` with timestamp and stream name
- Dashboard shows real-time activity log
- Notion Video Tracker is the source of truth for completion status
- Failed topics remain "Pending" for manual review

---

## See Also

- **[SPRINT-LOG.md](SPRINT-LOG.md)** — Development progress by sprint
- **[ROADMAP.md](ROADMAP.md)** — Planned features and improvements
- **[CLAUDE.md](../CLAUDE.md)** — AI assistant integration rules
- **[GEMINI.md](../GEMINI.md)** — Token efficiency directives
