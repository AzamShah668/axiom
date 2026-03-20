# TTS Module

## Purpose
Voice cloning using Qwen3 TTS running on **Google Colab** (T4 GPU). Replaces NotebookLM's default AI voice with a cloned reference voice.

## Engine
- **Model**: Qwen3 TTS (via Gradio API on Colab)
- **Device**: Google Colab T4 GPU (16GB VRAM)
- **Colab Notebook**: [Qwen_TTS_Server](https://colab.research.google.com/drive/1uV6ZIqg3M9mwi-9Leplkmntn94rKEh9S)
- **Local Python venv**: `C:\Users\AZAM RIZWAN\qwen-tts-gpu\` (used for `gradio_client`)

## Reference Voice
- **Primary audio sample**: `d:\notebook lm\voice\Recording (14).m4a` (~15s)
- **Reference transcript**: `"Hey everyone, welcome back! Have you ever wondered how artificial intelligence is changing the way we learn? Today, we are going to explore some incredible new concepts together. It's truly fascinating, and I know you're going to love it."`
- **Backup sample**: `d:\notebook lm\voice\Recording (9).m4a` (~26s)
- **Voice notes**: `d:\notebook lm\voice\voice.md`

## Flow
1. `video/colab_manager.js` checks if the Colab Gradio server is alive (pings cached URL)
2. If dead → prompts user to restart Colab and paste new `gradio.live` URL
3. `video/tts_generator.js` sends transcript + reference audio to Colab via Gradio API
4. Colab GPU generates cloned voice WAV in a single pass
5. WAV is saved locally for FFmpeg post-processing

## Key Files
| File | Purpose |
|---|---|
| `video/tts_generator.js` | Sends text to Colab, receives WAV |
| `video/colab_manager.js` | Auto-manages Colab URL lifecycle |
| `video/colab_url.json` | Cached Gradio URL (auto-updated) |

## Error Handling
| Error | Action |
|---|---|
| GPU OOM on Colab | Use smart chunking (50-80 word blocks) with identical ref_audio per chunk |
| Colab session expired | `colab_manager.js` detects and prompts for restart |
| Gradio server unresponsive | Health-check ping fails → auto-trigger relaunch flow |
| Slow/robotic output | Adjust speaking rate params, re-run |
