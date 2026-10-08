# Science Time (@ScienceTime24): reverse-engineering notes

Goal: produce Hindi science videos in the same editing style, at a much higher upload frequency.

## Breakdowns
| # | Video | Views | Key takeaway |
|---|---|---|---|
| 01 | [How Big is The Universe?](01-how-big-is-the-universe.md) | 15.2M | A 14-rung zoom-out ladder. Visuals are mostly free NASA/ESO/Wikimedia material plus space-sim flights plus simple scale infographics. Almost no music: just a sub-bass drone and SFX accents. |

## Analyzing the next video
Video downloads go through Apify, because YouTube blocks direct downloads from cloud IPs.

```bash
APIFY_TOKEN=... scripts/reference_analysis/fetch_video.sh <videoId> work/<videoId> 480
PY=/path/to/venv/python scripts/reference_analysis/analyze_video.sh work/<videoId>/video.mp4 work/<videoId>/an
/path/to/venv/python scripts/reference_analysis/audio_stats.py work/<videoId>/an/audio
```

Python deps: `scenedetect opencv-python-headless demucs librosa soundfile` (with CPU torch).

Outputs:
- shot lists: `an/scenes/*.csv`
- a 2-second frame timeline as contact sheets: `an/sheets/`
- voice/music stems: `an/audio/demucs/`
- loudness: `an/audio/loudness.txt`
- voice/music/SFX stats: `an/audio/audio_stats.json`

Free-plan cost note: the downloader actor caps each run at $0.20. At 480p that is enough for videos up to about 13 minutes; use 360p for longer ones.
