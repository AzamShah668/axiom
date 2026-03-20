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
1. **Enhance** transcript with natural intro/outro via `transcript_enhancer.js`
2. **Generate** TTS voice clone via Colab Gradio API (`tts_generator.js`)
3. **Scale** intro video to 1920x1080
4. **Crop** bottom 60px to remove NotebookLM watermark
5. **Generate** black outro card with centered AXIOM logo
6. **Concatenate** intro → main video → outro
7. **Overlay** AXIOM watermark (top-left, 60% opacity) + subscribe button (bottom-right, 80% opacity)
8. **Map** TTS audio as the sole audio track
9. Output → `final_output.mp4` (same directory as input)

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
