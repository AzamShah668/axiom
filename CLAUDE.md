# EduContent Pipeline — Claude Code Project Config

> Automated educational video pipeline: Notion → NotebookLM → Colab TTS → FFmpeg → YouTube

## Tech Stack
Node.js, Puppeteer, FFmpeg, googleapis, Notion API, YouTube Data API, Gemini AI, Gradio (Colab)

## GSD Integration
- Follow smart phase-skipping rules from `GEMINI.md` section 5
- **Trivial** (1 file, one-liner): Skip GSD entirely
- **Small** (2-3 files): `/gsd:plan-phase` → `/gsd:execute-phase`
- **Large** (multi-module): Full `/gsd:map-codebase` → `/gsd:plan-phase` → `/gsd:execute-phase` → `/gsd:verify-work`

## Ralph Loop Integration
- Ralph Loop is a **tactical tool** used ONLY inside GSD execute-phase or debug sessions
- When a GSD executor hits an iterative implement→test→fix cycle, invoke:
  `/ralph-loop "<specific task>" --completion-promise "DONE" --max-iterations 5`
- Good for: getting tests to pass, debugging flaky automation, iterative FFmpeg filter tuning
- NOT for: planning, research, one-shot edits, or verification

## Anti-Patterns (DO NOT)
- Run full GSD AND full Ralph Loop end-to-end on every task
- Use multiple mandatory checklists per step
- Have two separate "final verification" gates on every change
- Invoke Ralph Loop at orchestrator level (only inside executors/debuggers)
- Run `/gsd:map-codebase` for tasks touching < 3 modules

## Token Efficiency
- See `GEMINI.md` for full rules (lazy loading, batch reads, concise output)
- Start with `agent.md` for orientation, read module `CONTEXT.md` only when needed
- All logs → `logs/`, all renders → `output/videos/`

## Key Paths
| Resource | Path |
|----------|------|
| Pipeline entry | `modules/orchestrator/run_pipeline.js` |
| Chrome bridge | `tools/chrome_bridge.js` |
| Colab launcher | `tools/colab_launcher.js` |
| NotebookLM controller | `tools/notebooklm_controller.js` |
| TTS generator | `video/tts_generator.js` |
| Post-processor | `video/post_processor.js` |
| YouTube uploader | `modules/uploader/youtube_uploader.js` |
| Chrome Profile 4 | `C:\Users\AZAM RIZWAN\AppData\Local\Google\Chrome\User Data\Profile 4` |
| Python venv | `C:\Users\AZAM RIZWAN\qwen-tts-gpu\` |
| Reference voice | `voice/Recording (14).m4a` |
