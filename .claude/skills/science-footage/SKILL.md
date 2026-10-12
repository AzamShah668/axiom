---
name: science-footage
description: Build the 4K footage library for a science-channel production - search ESO, ESA/Hubble, ESA/Webb and NASA SVS, pick candidates with CLIP against the edit's visual queries, transcode 4K sources to proxies, split into shots, and QC each shot for text, black frames, motion and duplicates. Use for stage 4 of science-video or when a video needs more or better footage.
---

# Footage library (stage 4)

```bash
scripts/science/pipeline.sh productions/NN-slug footage
```
The four steps can also be run alone (all in `scripts/footage/`):

| Step | Script | What it does |
|------|--------|--------------|
| search | `search_sources.py terms.txt $LIB/candidates.json [--sources eso,esahubble,esawebb,svs]` | archive search per term; keeps only videos with a verified 4K file (ultra_hd on ESO/ESA CDNs, >= 3840 px mp4 on NASA SVS) |
| pick | `select_candidates.py ... $WORK/picks.json [--per-item 2]` | CLIP-scores each candidate's preview frame and title against every item's queries; keeps each item's best unclaimed candidates |
| fetch | `fetch_proxies.py picks.json $LIB [--jobs 3]` | ffprobe check (>= 3840 px or skipped), streams the 4K file into a 1080p30 proxy (16 s for single shots, 90 s for multi-shot episodes) |
| shots | `build_shots.py $LIB [--workers 4]` | PySceneDetect shots; per second: OCR text (auto-crop for corner labels), black, frozen (motion < 0.6); perceptual-hash duplicates; CLIP embedding |

- `$LIB` is shared across productions and only grows; every step is incremental and resumable.
- `$LIB/shot_thumbs/` has 3 frames per shot for checking by eye.

## Sources and licences
- **ESO** (eso.org), **ESA/Hubble** (esahubble.org), **ESA/Webb** (esawebb.org): CC BY 4.0. Credit the
  archive; `credits.py` lists the video ids.
- **NASA SVS** (svs.gsfc.nasa.gov): public domain. Credit NASA's Goddard Space Flight Center.
- Not usable here: NOIRLab (blocked from the container). Most images-api.nasa.gov video is 1080p.
- Not 4K, never used: older ESO videos without ultra_hd, NASA SVS 1080p-only pages, and fulldome/VR renders
  (`-FD`, `dome`, `360`).

## Budget
- Decoding 4K costs ~2 CPU-seconds per video second; 4 cores manage ~2.5 videos a minute.
- Keep proxies short: `--cap-single 12 --cap-multi 60 --preset ultrafast --limit 400`. Each shot is used
  once for ~3 s, and only graphics backgrounds need ~10-14 s.
- `build_shots.py` saves after every clip. Run it in a loop while proxies arrive; it resumes where it stopped.
- In Claude Code cloud sessions, background commands stop at their timeout. Start long stages with
  `run_in_background` and `timeout: 7200000`. Every step is resumable, so just start it again.
- The edit needs ~250 different shots. Aim for 1.5-2x that many usable unique shots, so every item has a real choice.
- Top-up for weak matches after a first assignment:
  `select_candidates.py ... --weak $WORK/cutlist.json --below 0.22 --skip $WORK/picks.json`,
  then fetch, shots and assign again.

## Gaps
If the assignment review shows weak matches for a beat (no 4K footage of the thing exists):
1. Add search terms and re-run the footage stage (incremental).
2. Or broaden the beat's query to something the archives do have (e.g. "laboratory" -> "telescope
   instruments being assembled").
3. Or turn the beat into a graphic.

Never fall back to 1080p footage or repeat a shot.
