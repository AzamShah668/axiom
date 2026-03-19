# TTS Module

## Purpose
Voice cloning using Qwen TTS on local GPU. Replaces NotebookLM's default AI voice with a cloned reference voice.

## Engine
- **Model**: Qwen TTS (local)
- **Device**: CUDA `cuda:0`
- **Location**: `C:\Users\AZAM RIZWAN\qwen-tts-gpu\`

## Reference Voice
- **Audio sample**: `d:\notebook lm\voice\Recording (9).m4a`
- **Reference text**: `d:\notebook lm\voice\voice.md`

## Flow
1. Receives enhanced transcript text from orchestrator
2. Sends to Qwen TTS Python engine via subprocess
3. Outputs `.wav` file for FFmpeg post-processing

## Error Handling
| Error | Action |
|---|---|
| GPU OOM | Reduce batch size or split transcript into chunks |
| TTS engine unavailable | Check CUDA drivers, fallback to manual voiceover |
| Slow/robotic output | Adjust speaking rate params, re-run |
