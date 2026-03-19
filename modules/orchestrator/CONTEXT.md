# Orchestrator Module

## Purpose
Master pipeline coordinator. Picks topics from Notion, runs the 10-step pipeline.

## Pipeline Flow
```
1. PICK    → Next Pending topic from Notion Master DB
2. CHECK   → Not already in Video Tracker
3. SCRAPE  → Smart YouTube search + Dynamic Topic Splitting
4. FEED    → Create NotebookLM notebook with single focused URL
5. GEN     → Trigger Audio Overview, download MP4 + transcript
6. TTS     → Qwen TTS voice clone (GPU, cuda:0)
7. RENDER  → FFmpeg: audio-swap, crop watermark, trim outro
8. PUBLISH → YouTube upload + Subject & Chapter playlists
9. UPDATE  → Mark Completed in Notion, log URL
10.ADVANCE → Round-robin to next subject/stream
```

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
| Topic has no good YouTube results | Mark `Failed`, advance to next |
