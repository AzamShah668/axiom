# Science Time (@ScienceTime24): reverse-engineering notes

Goal: produce Hindi science videos in the same editing style, at a much higher upload frequency.

## Breakdowns
| # | Video | Views | Key takeaway |
|---|---|---|---|
| 01 | [How Big is The Universe?](01-how-big-is-the-universe.md) | 15.2M | A 14-rung zoom-out ladder. Visuals are mostly free NASA/ESO/Wikimedia material plus space-sim flights plus simple scale infographics. Almost no music: just a sub-bass drone and SFX accents. |

## Analyzing the next video
See `scripts/reference_analysis/README.md`: download through Apify (YouTube blocks direct downloads from cloud
IPs), then `analyze_video.sh` measures cuts, transitions, camera moves, text styles and animations, music tracks,
ducking, SFX events, voice and pacing, and `report.py` writes the tables and frame strips for the breakdown.

Free-plan cost note: the downloader actor caps each run at $0.20. That pays for 720p up to about 7 minutes,
480p up to about 13 minutes and 360p up to about 22 minutes; `fetch_video.sh` picks the best one that fits.
