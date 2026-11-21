# Motion-repo experiments (kept separately, NOT in the pipeline)

Owner, 2026-11-21: "I didn't like the way that you integrated those things... reverse all those things and do not include them in our pipeline right now. Just keep it separately."
Do not use anything here for a video unless the owner asks. Paths inside the notes below are the old ones (scripts/video/... -> experimental/motion-repos/...).

## 3D motion-graphics engine (web3d) and the repo review (2026-11-20)
Owner: "use only those repos that you think we can integrate… if something doesn't match our style, do not add that."
- **web3d** (`scripts/video/web3d/`): three.js + postprocessing (bloom, vignette) + rapier physics, rendered frame by frame in headless Chromium. Each scene is a pure function of time (`init`, `render(t)`). About 0.4-0.5 s a frame at 1080x1920 on our CPU, so a 30 s Short is about 8 minutes. Text stays PLAIN (2D overlay), photos are drawn whole as framed prints.
  - `node scripts/video/web3d/render_web3d.js <scene> --dur S --out x.mp4 [--size 1080x1920] [--params @p.json] [--stills 1.5,8]`; `--stills` writes review stills first.
  - Shorts: `python scripts/video/short_web3d.py <scene> <timeline.json> <voice.wav> <captions.txt> <music.mp3> <out.mp4>` (word times at 1.1x, sound hits per scene in `HITS`, `--audio-only` remixes).
  - First scene: `scenes/blunder.js` (09 Short 3). Shared parts in `scenes/_lib.js` (stars, glow, bloom, plain-text overlay, easing).
  - Install once per container (outside the repo): `sh scripts/setup/fetch_motion_tools.sh`.
- **Beat sync** (`scripts/video/beats.py`, librosa): cuts stay on the words; the music start point is chosen so its beats land on the cuts (Short 3: 204 ms -> 98 ms average miss).
- **lemo-opuscar** (MIT code, CC BY-NC style docs, so it lives outside the repo): tested. `dark-documentary` fits our look but needs a GPU (7 s a frame here); keep for the Colab GPU step. `flat-space-explainer` renders fast but is cartoon, `hardcore-info` is a white product teardown (29 s a frame): not our style, not used.
- Not used: video-shotcraft (product promos), pixelfx, the Claude character base, mcp-for-blender (needs a desktop app; Blender comes later via Colab). joeseesun/opus-video-prompts has no licence: read only.

