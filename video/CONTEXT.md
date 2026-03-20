# Video Module (Remotion + FFmpeg)

## Purpose
Dual-mode video engine: Remotion for programmatic video generation, FFmpeg for post-processing NotebookLM outputs.

## Key Files
| File | Purpose |
|---|---|
| `src/` | Remotion React components (TSX) |
| `post_processor.js` | FFmpeg pipeline — assembles intro + video + outro + overlays |
| `tts_generator.js` | TTS integration — sends transcript to Colab Gradio API |
| `colab_manager.js` | Auto-manages Colab Gradio URL lifecycle |
| `colab_url.json` | Cached Gradio URL (auto-updated) |
| `remotion.config.ts` | Remotion build config |
| `engines/` | Placeholder for Engine 1 & 2 scripts (NOT YET BUILT) |

## FFmpeg Post-Processing Steps (post_processor.js)
Runs AFTER Engine 2 produces the synced video. Takes Engine 2 output → YouTube-ready branded MP4.

1. **Probe** input + intro durations for fade timing
2. **Scale** AXIOM intro to 1920x1080 @ 30fps, add fade-out at end
3. **Crop** bottom 60px of main video (removes NotebookLM watermark), scale to 1080p, fade-in + fade-out
4. **Generate** black outro card (8s) with centered AXIOM logo (colorkey'd for transparency)
5. **Normalize** all audio to 44100Hz stereo (intro, main TTS, silence for outro)
6. **Concatenate** intro → main → outro (video + audio)
7. **Overlay** AXIOM logo watermark (top-left, 60% opacity, colorkey'd background)
8. **Overlay** Subscribe button (bottom-right, FFmpeg-drawn red box + text)
9. Output → `<input_name>_branded.mp4`

### CLI Usage
```
node video/post_processor.js <SyncedVideoPath> [OutputPath]
```

## Pending Work
- **Engine 1** (`engines/engine_1_transcribe.py`): Whisper word-level timestamps for original + new audio
- **Engine 2** (`engines/engine_2_sync.py`): FFmpeg visual slicing to match new voice pacing

## Commands
| Action | Command |
|---|---|
| Open Remotion Studio | `cd video && npm run dev` |
| Build Remotion bundle | `cd video && npm run build` |
| Run post-processor | `node video/post_processor.js <VideoPath> <TranscriptFile> <TopicName> <SubjectName>` |

## Note
This module has its **own `package.json`** (Remotion + React). Do NOT merge with root.
