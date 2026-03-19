# EduContent Pipeline — Project-Level AI Rules

## Token Efficiency Directives

These rules apply to ALL AI assistants working in this repository.

### 1. Lazy Context Loading
- **Always** start by reading `agent.md` (the compact router)
- **Only** read a module's `CONTEXT.md` when the task involves that module
- **Never** pre-load all CONTEXT.md files "just in case"

### 2. No Redundant Reads
- Do not re-read files already in your context unless >5 turns have passed
- If you read a file earlier in this conversation, reference your memory instead

### 3. Batch Parallel Calls
- Always combine independent file reads into a single parallel tool call
- Never read files one-by-one when they can be read simultaneously

### 4. Concise Output
- Keep responses under 200 words unless the user asks for detail
- Use tables and bullet points over paragraphs
- Skip preambles like "Sure, I'd be happy to help" — go straight to the answer

### 5. Smart Phase Skipping
- **Trivial tasks** (single file edit, one-liner fix, Q&A): Skip GSD entirely
- **Small tasks** (2-3 files, clear scope): Skip `map-codebase`, go straight to `plan-phase`
- **Full GSD** only for multi-module refactors, new features, or debugging sessions

### 6. Garbage Discipline
- All logs go to `logs/` — never dump to root
- All video renders go to `output/videos/` — never dump to root
- Run `/clean-garbage` before any major pipeline execution
