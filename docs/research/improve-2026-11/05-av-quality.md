# 05: Audio and visual production quality of the long-form render

Method: I measured video 08's master (`work/08-scariest-places/out/`): its stems, its proxies, the frame rates of its 4K sources and x264 encode times on this 4-core container, then read the code. Numbers below come from those measurements unless a URL is given.

## 1. Where the render falls short

| # | Problem | Where | Evidence |
|---|---|---|---|
| 1 | **5 Hz judder under every shot.** The ESO and ESA sources are 25 fps, but the proxies are forced to 30 fps, so every 6th frame is a duplicate. | `fetch_proxies.py:53` `fps=30` | 8/8 probed ESO/ESA 4K files: `25/1`. 183 of 08's 205 shots come from ESO/ESA. Proxy frame diffs: a near-duplicate every 6 frames. |
| 2 | **The upload copy is encoded twice.** Chunks are x264 `veryfast` CRF 18 with `-g 60` (10 Mbps). The 1440p copy is then made from that master (CRF 16, medium), so it upscales the veryfast artefacts and costs about 30 min of CPU. | `render_v3.py:636-637` | ffprobe of both files |
| 3 | **Grain and vignette move with the picture.** `item_frame()` grades before `camera()`, so the grain is zoomed and rotated with the image, and the vignette drifts on push and roll. The grain is 4 frames cycled (a 7.5 Hz pattern) at half resolution with nearest-neighbour upscaling, which gives 2×2 blocks: the coarse grain that compresses worst. `cv2.add` clips the negative grain in black, so it only lifts black. | `render_v3.py:546-548`, `grade.py:43-57` | [coarse grain breaks on YouTube](https://www.premiumbeat.com/blog/grain-overlays-affecting-youtube-upload/) |
| 4 | **Every shot is resampled twice and softened.** The corner-label crop is resized (`INTER_LINEAR`), then `warpAffine` upsamples by z=1.02-1.2 (`INTER_LINEAR`). | `render_v2.py:110`, `render_v3.py:504-522` | |
| 5 | **The voice is too bass-heavy for phone speakers.** Rudra's 80-250 Hz band is +12.5 dB over 1-4 kHz, and `voice_post.sh` still adds +2.5 dB at 160 Hz (a setting tuned for Neel). The 60 Hz 2-pole high-pass leaves the 20-60 Hz band at only -9.6 dB. | `voice_post.sh` | 87% of Indian YouTube time is on mobile ([bestmediainfo](https://bestmediainfo.com/insights/socials-new-prime-time-is-tv-youtube-ctv-time-up-219-in-india-10445366)) |
| 6 | **The pause lift never happens.** `PAUSE_LIFT` is 3 dB, but pauses are capped at 0.4 s and smoothed over 0.35 s. Measured, the music is only about 1.5 dB louder in pauses. The bed's LRA is 3.0 LU, so the music has no arc. | `render_v3.py:39, 748-749, 699` | stems |
| 7 | **Audio delivery is below spec.** AAC is 192 kbps; YouTube asks for 384 kbps stereo at 48 kHz. | `render_v3.py:860` | [YouTube encoding settings](https://support.google.com/youtube/answer/1722171) |
| 8 | **Star fields step in whole pixels.** `starfield()` moves `int(t*12)` px, i.e. 0.4 px a frame, so the stars visibly tick. | `render_video.py:222-227` | |

**Already fine, leave alone:** the master is -14.0 LUFS, -1.4 dBTP, LRA 1.9. The music is 15.7 LU under the voice and more than 20 dB under it in every band, 23 dB in the 1-4 kHz band, so no sidechain ducking is needed. Sibilance is low (0.9% of active frames). The raw ElevenLabs LRA is already 2.3 LU, so the dynamic `loudnorm` is not what makes the voice flat.

## 2. Improvements

Times assume about 15 min of frame rendering for an 11-min video on 4 cores.

### P1-a: Render long-form at 25 fps (fixes #1)
- `render_video.py:20`: set `FPS = 25`. Scale the frame-count constants so their durations stay the same:
  - `render_v3.py:37`: `TD = {k: round(v * FPS / 30) for k, v in {...}.items()}`
  - in `render_chunk`: `fi, fo = round(12*FPS/30), round(75*FPS/30)` and the logo's `/60` becomes `/(2*FPS)`
- `fetch_proxies.py:53`: use `fps=25` for 25 fps sources. For 30/60 fps sources (NASA SVS, 11%), use `framerate=fps=25` (it blends frames, so no stutter).
- One-off fix for the existing library (shots are stored in seconds, so nothing else changes): for each ESO/ESA proxy run
  `ffmpeg -i clip.mp4 -vf decimate=cycle=6 -r 25 -c:v libx264 -preset veryfast -crf 18 -g 25 out.mp4`
  (about 1 s per 12 s clip, about 15 min for the library).
- YouTube: "encode and upload at the frame rate it was recorded" ([source](https://support.google.com/youtube/answer/1722171)).
- **Impact:** every footage shot plays smoothly, which is the biggest visible gain. **Cost:** about 17% less render time (fewer frames). Shorts (`render_short_v2.py:35`) should follow.

### P1-b: Encode the 1440p upload once, inside the chunks (fixes #2)
In `render_chunk`:
```
-vf scale=2560:1440:flags=lanczos -c:v libx264 -preset veryfast -crf 16
-x264-params aq-mode=3:bframes=2 -g {FPS//2} -pix_fmt yuv420p
```
- `aq-mode=3` is x264's "auto-variance AQ with bias to dark scenes", which protects shadows from banding ([x264-devel](https://mailman.videolan.org/pipermail/x264-devel/2014-December/010949.html)).
- A closed GOP of half the frame rate is YouTube's own spec.
- Make the 1080p review/preview copy *from* this file. Drop the separate 1440p transcode.
- Benchmark (10 s, 1080p source):

  | Encode | CPU | Bitrate | SSIM vs source |
  |---|---|---|---|
  | today: 1080p veryfast CRF 18 | 24 cpu-s | 9.5 Mbps | 0.9898 |
  | 1440p veryfast CRF 16 aq3 | 46 cpu-s | 28 Mbps | 0.9913 |
  | 1440p medium CRF 16 | 121 cpu-s | | |

- **Cost:** about 6 min on the render, minus the about 30 min CPU transcode it replaces.
- **Impact:** one generation fewer. A 1440p upload is reported to get VP9 even at 1080p playback ([forum reports](https://forum.videohelp.com/showthread.php?p=2703646); not documented by YouTube).

### P1-c: Split the grade into colour and finish, and use fine grain that changes every frame (fixes #3)
`grade.py`:
- `Grade.color(fr)` = LUT + saturation, applied before the camera move.
- `Grade.finish(fr, f)` = vignette + grain, applied after `camera()`, in `item_frame` for `kind == "clip"` only.
- Grain: build one full-resolution `float32` normal plate of `(H+64, W+64)`. Each frame takes a random 64-px offset into it, so the grain is fresh every frame at about 1 ms.
- Weight it by luma: `w = clip(Y/24,0,1)*clip((255-Y)/80,0,1)`, so there is no grain on pure black (black stays black and costs no bits) and less in highlights.
- Add it as int16 and clip both ways. `grain` default 3 → 2.0 (fine, full resolution).
- **Cost:** about +5 ms/frame (+0.5 min).
- **Impact:** the grain reads as film rather than a dirty lens. With aq-mode 3 it dithers the 8-bit LUT's skipped codes (mid slope 1.5), so nebula gradients stop banding. Fine grain survives web compression better than coarse grain ([PremiumBeat](https://www.premiumbeat.com/blog/grain-overlays-affecting-youtube-upload/)).

### P1-d: A voice chain for phone speakers (fixes #5)
`voice_post.sh`, replacing the `-af` chain:
```
highpass=f=70:poles=2,highpass=f=70:poles=2,equalizer=f=280:t=q:w=1.0:g=-3,
acompressor=threshold=-24dB:ratio=2.5:attack=10:release=250:knee=6:makeup=3,
equalizer=f=3000:t=q:w=0.8:g=2.5,equalizer=f=10000:t=h:w=0.7:g=2,deesser=i=0.35,
loudnorm=I=-16:TP=-1.5:LRA=7
```
- The 4th-order 70 Hz high-pass clears rumble but keeps the voice's F0 (median 103 Hz, p10 76 Hz).
- The de-esser sits after the presence and air boosts, so it catches what they add.
- Tested on 08's `narration_raw.wav`:

  | Band, relative to 1-4 kHz | Today | New chain |
  |---|---|---|
  | 80-250 Hz | +12.5 dB | +9.5 dB |
  | 20-60 Hz | -9.6 dB | -17.5 dB |
  | Sibilant frames | 0.89% | 0.36% |

- Starting points follow common VO practice: high-pass 80-100 Hz, 1.5-5 kHz presence +1-2 dB, de-ess 5-8 kHz ([violetrecording](https://violetrecording.com/how-to-eq-vocals/), [soundbridge](https://www.soundbridge.io/how-to-mix-vocals-practical-techniques-that-work)). Poor audio lowers the perceived credibility of a speaker ([Newman & Schwartz, summarised](https://www.throughlinegroup.com/2021/06/22/study-your-bad-audio-makes-you-sound-dumber/)).
- **Cost:** 15 s. It needs no ElevenLabs call: re-run it on `narration_raw.wav`, re-mix the bites, then mix and mux (the video chunks stay cached).
- **Check:** the owner A/Bs 30 s on a phone speaker.

### P1-e: Scientist portraits without Wikimedia
Download tests from the container (2026-11-16):

| Source | Licence | Container |
|---|---|---|
| NASA Image Library (`images-api.nasa.gov`, NASA staff portraits) | PD | search and download 200 |
| Library of Congress (`loc.gov/photos/?q=…&fo=json`, keep items whose `rights_advisory` says "No known restrictions") | PD | 200, `tile.loc.gov` 200 |
| ESO image archive (astronomers at ESO sites) | CC BY 4.0 | 200 |
| Internet Archive (licence field PD/CC) | varies | 200 |
| Smithsonian Open Access API (`usage.access == "CC0"`) | CC0 | needs a free api.data.gov key; DEMO_KEY hits its limit |
| Nationaal Archief / Anefo (Dutch astronomers, e.g. Maarten Schmidt) | CC0 per image | [terms](https://nationaalarchief.nl/en/node/44203); the website search returned 404 to a direct query, check by hand |
| Openverse (`api.openverse.org`, `license=cc0,by,by-sa,pdm`) | per item | API 200; files on Flickr return **429**, so use only `source=nasa` items or other hosts that answer, never Wikimedia/Flickr |

- Add `fetch_assets.py portrait <name>`. It queries these sources in order and writes the licence and credit into `credits.json`.
- **Impact:** the owner's "photos of every person named" rule. **Cost:** minutes.

### P2
- **P2-a: Resample once (#4).** Fold the crop into the camera matrix: compose `M` with `scale=1/(x1-x0)` and `translate=-x0*W` in `camera()`, and drop the resize in `ClipReader.read`. Use `cv2.INTER_CUBIC`.
  - Benchmark: 48 ms vs 17 ms linear, about +2 min total (Lanczos4 takes 175 ms, too slow).
  - Impact: visibly crisper stars and edges.
- **P2-b: Audio delivery (#7).** `-b:a 384k`; `SR = 48000` in `render_video.py`/`sfx.py` (resample the narration once at load). Cost: none.
- **P2-c: A music arc instead of the dead pause lift (#6).**
  - In `plan()`, add a `swell` music event (+4 dB, 0.3 s up, 1.2 s down) at each section start (the 0.8 s gaps) and at each `typing` moment.
  - Raise `_level(keep=0.25 → 0.4)`. Set `PAUSE_LIFT = 0`.
  - Keep `BED_LU = 16`. The Curious Space reference sits at 13-15 LU and documentary practice ducks 12-20 dB ([BorisFX](https://borisfx.com/blog/what-is-audio-ducking-and-how-is-it-used/)).
  - Cost: none.
- **P2-d: Fades in float.** `transition("dip")`, the fade-in and the fade-out truncate to `uint8`, which darkens and bands. Use `cv2.convertScaleAbs(fr, alpha=k)` instead, which rounds. Cost: none.

### P3
- **P3-a: Sub-pixel star drift (#8).** `cv2.getRectSubPix` on the star canvas. About 3 ms.
- **P3-b: 1440p proxies** from the 4K sources (`fetch_proxies.py` scale `2560:1440`, `flags=lanczos`) and render at 1440p natively. This gives real detail rather than upscaled detail.
  - Costs about 1.8x the render time (about 35 min) and the library would have to be fetched again.
  - Worth it only once P1-a to P1-c are in and the channel grows.
- **P3-c: 2.5D parallax for photos (`G photo:`)** with Depth Anything V2 depth plus a displacement warp ([DepthFlow](https://github.com/BrokenSource/DepthFlow)). It costs a few CPU seconds per photo, cached.
- **P3-d: A linear `loudnorm`** (two-pass, with `measured_*`) in `voice_post.sh`, for predictability. Cosmetic.

## 3. Do not do
- **60 fps.** The sources are 25 fps, so it doubles render time and bitrate needs and adds judder.
- **A 4K master from 1080p proxies.** It costs 4x the render and adds no detail.
- **Coarse or heavy grain,** or grain baked in before the camera move.
- **Sharpening (`unsharp`) on star fields.** It makes halos and twinkling noise after YouTube's encode.
- **A stronger teal-orange.** It reads as artificial in documentaries ([Beverly Boy](https://beverlyboy.com/film-technology/stylized-palettes-teal-orange-done-tastefully-by-constraint/)). Keep the presets subtle and true black.
- **Pumping sidechain ducking or dynamic `loudnorm` on the master.** The bed is already 20 dB or more under the voice.
- **Reverb or a "space" effect on the narration.** It lowers intelligibility on phones.
- **Generated likenesses of real scientists.**
- **Getting around Wikimedia's or Flickr's 429s,** or taking images from Openverse that are hosted there.
- **Press-kit, Nobel (© Nobel Prize Outreach) or AIP photos.** They are editorial-only or paid, not CC/PD.
- **Judging encode quality from a paused frame.** Check motion on the live YouTube stream.
