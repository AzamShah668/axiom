# EduContent Automation Pipeline — Task Tracker

## Phase 1: Planning & Architecture
- [x] Map available tools (Notion MCP, NotebookLM MCP, Remotion skill, YouTube API)
- [x] Design the full pipeline architecture
- [x] Write `implementation_plan.md` for user review → APPROVED ✅
- [x] Write `agent.md` — the reusable agent framework
- [x] Get user approval on the plan

## Phase 2: Project Structure & Config
- [x] Create project structure (folders for scripts, temp data, outputs)
- [x] Generate initial `config.json` with YouTube API key and board preferences
- [x] Write `.env.example` file
- [x] Formulate Notion DB Schema and identify creation script requirements
- [x] Write `setup-notion-dbs.js` script (pending Notion API key to execute)
- [x] Draft `agent.md` with:
    - [x] Setup instructions
    - [x] Daily execution protocol
    - [x] Tool usage definitions (NotebookLM MCP, YouTube API)
    - [x] Error handling & retry logic
    - [x] Notion DB IDs configuration placeholders

## Phase 2: Advanced Pipeline & Syllabus Extraction
- [x] Parse PDF Syllabi using PyPDF/pdf-parse (Extract BTech & MBBS subjects)
- [x] Update Implementation Plan with advanced Remotion pipeline
- [x] Restructure `scripts/setup-notion-dbs.js` to create separate BTech and MBBS spaces & tables
- [x] Execute `setup-notion-dbs.js` with user's Notion Token
- [x] Update `agent.md` to reflect the new post-processing flow using NotebookLM sub-agents.
- [ ] Refactor `youtube_scraper.js` to return direct video URLs instead of transcripts
- [x] Implement Remotion video post-processing (Intro splicing, Watermark removal, Outro trimming)
- [ ] Build Engine 1: Transcript Timestamp Generator (Whisper-based)
- [ ] Build Engine 2: Visual Slicer & Forced Alignment Sync for custom voice lengths

## Phase 3: Notion Database Setup & Refinement
- [x] Write `scripts/setup-notion-dbs.js` setup script
- [x] Refactor Syllabus Extraction to break chapters into granular sub-topics
- [x] Update `setup-notion-dbs.js` to create Chapter -> Topic hierarchy
- [x] Get Notion API key from user (internal integration token)
- [x] Run setup script to create 6 databases
- [x] Populate with CBSE/MBBS/BTech syllabus data

## Phase 4: Integration (TTS & YouTube)
- [ ] Integrate Qwen TTS CLI trigger into post-processing workflow
- [ ] Implement `youtube_uploader.js` using provided `client_secret.json`
- [ ] Implement YouTube Playlist management (Subject and Chapter playlists) in the uploader

## Phase 5: End-to-End Test Run
- [ ] Pick a test topic (e.g., "Physical World" — Physics 11th)
- [ ] Run YouTube scrape to get top URLs
- [ ] Feed URLs into NotebookLM and generate internal Deep Research doc
- [ ] Generate NotebookLM native video
- [ ] Download and verify video quality
- [ ] Test YouTube upload

## Phase 5: Agent.md Finalization
- [x] Write comprehensive agent.md with all 8 steps
- [ ] Add Notion DB IDs to agent.md after DB creation
- [ ] User review and approval of agent.md
