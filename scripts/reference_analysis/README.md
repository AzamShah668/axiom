# Reference-video analysis

Measures a reference video's editing so a breakdown in `docs/research/<channel>/` rests on numbers and
timestamps, not impressions. Everything it downloads or writes is other people's material: keep it on Google
Drive (`misc/reference/<videoId>/`, `scripts/storage/drive_sync.py push`), never in the repo.

```bash
APIFY_TOKEN=... CHANNEL_VIDEOS=30 scripts/reference_analysis/fetch_video.sh <videoId> work/ref/<videoId>      # auto quality
PY=work/venv/bin/python scripts/reference_analysis/analyze_video.sh work/ref/<videoId>/video.mp4 work/ref/<videoId>/an \
   --meta work/ref/<videoId>/meta.json --topic "sun,सूरज,सूर्य" --sections 0,95,210,...
```
Venv: `scripts/requirements-science.txt` + `scripts/requirements-analysis.txt`. A 15-minute video takes
roughly 1 h on 4 CPU cores (Demucs and Whisper `medium` are most of it); every step resumes where it stopped.

| Script | Measures | Output |
|---|---|---|
| `fetch_video.sh` | metadata, subtitles, channel's latest uploads, MP4 at the best quality the Apify budget pays for | `meta.json`, `video.mp4`, `thumb.jpg` |
| `audio_stats.py` | LUFS (mix / voice / music), speech and pauses, words per minute, voice-vs-music gap in speech and pauses, ducking depth / attack / release, music tracks (tempo, pulse, key, brightness, fades), swells, silences and drop-outs, SFX events (whoosh, riser, boom, hit, sub drop, pop/click, glitch, tonal) | `audio/audio_stats.json`, `audio/music_map.jpg` |
| `transcribe.py` | word-timed transcript (faster-whisper) | `transcript/words.json` |
| `visual_stats.py` | cuts and transition types (cut, dissolve, flash, light leak, dip to black, whip/slide, zoom, glitch), camera move per shot (push-in, pull-out, pan, tilt, roll, 2.5D parallax, shake), content (footage, still + move, 2.5D still, graphic), grade, vignette, letterbox, grain | `visual.json`, `shots/shots_NN.jpg` |
| `text_track.py` | every on-screen text: exact in/out time, entry/exit animation (cut, fade, scale pop, slide, wipe/typewriter), size, position, colour, plate, outline, counters; grouped into styles | `text_events.json`, `text/style_NN.jpg` |
| `report.py` | merges it all: summary table, SFX list with triggers (cut, text pop, reveal), music table, pacing per section, cut/word sync, intro timeline; 10 fps x 2 s frame strips of every event type | `report.md`, `summary.json`, `sequences/*.jpg` |

## Trust, and what to check by eye
`python scripts/reference_analysis/selftest.py <dir>` renders a 48 s video with known cuts, transitions, camera
moves, text animations, music tracks, ducking, swell, drop-out and SFX, runs the analyzers and scores them
(51/52 pass; the one known miss is listed in the script). Run it after changing an analyzer.

The automatic labels are a first pass. Before writing a breakdown:
- view `shots/` and `sequences/` (content and motion labels, transition and text animations frame by frame);
- check `music_map.jpg`: track boundaries, swells (yellow), SFX (red);
- SFX with trigger `none` and a regular spacing are usually music notes that slipped through;
- music levels under speech are an upper bound (Demucs leaves some voice in the music stem); levels in pauses are clean.
