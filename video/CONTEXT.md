# Video Module (Remotion + FFmpeg)

## Purpose
Dual-mode video engine: Remotion for programmatic video generation, FFmpeg for post-processing NotebookLM outputs.

## Key Files
- `src/` — Remotion React components (TSX)
- `post_processor.js` — FFmpeg pipeline
- `tts_generator.js` — TTS integration wrapper
- `remotion.config.ts` — Remotion build config

## FFmpeg Post-Processing Steps
1. **Mute** original NotebookLM audio
2. **Sync** new Qwen TTS audio track
3. **Crop** bottom 60px to remove NotebookLM watermark
4. **Trim** video to match audio length (removing outro)
5. Output → `output/videos/final_output.mp4`

## Commands
| Action | Command |
|---|---|
| Open Remotion Studio | `cd video && npm run dev` |
| Build Remotion bundle | `cd video && npm run build` |
| Lint | `cd video && npm run lint` |

## Note
This module has its **own `package.json`** (Remotion + React). Do NOT merge with root.
