# Using Google Flow at its best for our videos (research + plan, 2026-11-21, owner to approve)

Research basis: Google Flow help (edit and scene pages), a hands-on Omni 1.2 Flash review (18 Nov 2026), Omni 1.2 API docs, and several Flow guides (sources at the end). Flow runs on **Omni 1.2 Flash** since 5 Nov 2026. Items marked *(test)* are not documented well enough; we confirm them with a small test batch before relying on them.

## 1. What Flow can do that our own engine and stock footage cannot

| Flow ability | What it gives us |
|---|---|
| **Camera moves inside the clip, written in the prompt** (dolly-in, pull-back, orbit, fly-through). Omni 1.2 is noted for holding scale on "fly-throughs, pull-backs and orbits" with less drift. | Real cinematic zoom in / zoom out and orbits, instead of our fake zooms on still galaxy images. |
| **Start frame / end frame** (save any frame of a clip, use it as the start or end of the next) | Shots that continue each other: a cut looks like one continuous camera flight (Earth -> Solar System -> galaxy). |
| **Extend** (Pro: add 3-10 s per step, up to 30 s total; the model sees the last 10 s) | One long unbroken camera journey for a big idea (a scale zoom, a collapse). Note: an extended clip can no longer get insert/remove/camera edits. |
| **Ingredients** (up to 3 reference images per generation/extension) | The same "hero" object in every clip: our planet, the DESI telescope, the black hole look stays consistent across a video. |
| **Edit an existing clip by prompt** (insert, remove, camera, relight, restyle; one change per turn, up to 3 follow-up turns; upload up to 30 s, edit window up to 15 s on Pro) | Fix a near-miss clip instead of regenerating; adjust lighting/mood to the video's palette. The **camera** edit mode could add a move to a clip *(test)*. |
| **360p drafts at 1 credit/s, 720p final, 1080p upscale on download (5 credits)** | Check composition and motion cheaply before paying for the final. |
| **Aspect ratio** (16:9 or 9:16) | Shorts generated vertically, not cropped from wide clips. |
| Native sound (ambience, music, voices) | Not used (see 5). |

## 2. The editing style we would build with it

- **Flow carries the "cinema" moments, our pipeline carries the story.** Flow clips for the visual that explains each key claim; real NOIRLab/ESO/NASA footage for real observations; photos (with animated names) for people; our graphs/labels on top; voice, captions, music and SFX from our pipeline.
- **Where the budget goes first:** the opening 90 s (where we lose 35-43% of viewers) and each chapter's turn ("lekin…"). The strongest clips go where retention is decided (no clip limit; owner 2026-11-21).
- **Camera language, one per video** (part of the locked style block): slow, smooth, one move per clip - dolly-in to reveal, pull-back to show scale, slow orbit for a 3D object, fly-through for a journey. No handheld shake, no whip pans.
- **Zoom in / zoom out happens inside Flow,** never faked in the edit on a Flow clip (clips play once, forward).
- **Continuous sequences:** 2-4 clips chained by end-frame -> start-frame for big moments (the Big Crunch, a scale journey), so the cuts feel like one shot. Everything else: hard cuts on the spoken word, as now.
- **Text never in the clip:** labels, numbers and graphs go on in our edit (Flow garbles text).
- **Scene builder in Flow** only to preview a chained sequence; the real edit stays in our pipeline (Hindi voice sync, captions, music, SFX, credits).

## 3. Changes needed in the Flow rulebook (owner and Muse to approve)

The current template locks the camera ("the camera stays completely locked with no zoom or pan", "static background ... completely still"). That prevents every cinematic move above. Proposal:
1. **Each clip has exactly one motion: either one camera move or one subject action, never both** (keeps clips stable and still literal to the line).
2. A **camera-move clip** uses this template (subject steady, one move):
   `A <length>-second <style> clip, <LOCKED STYLE>, <subject> stays steady while the camera <one move: slowly dollies in toward / slowly pulls back from / slowly orbits around / glides forward through> <target>, the move is smooth and continuous with no cuts, with no spoken dialogue and no background music, motion is smooth and simple with no glitching, no warping, no morphing, no flickering, no extra limbs, no duplicate characters, and no on-screen text, subtitles, watermarks or logos.`
3. An **action clip** keeps today's locked-camera template.
4. New clip-table columns: **Motion** (camera move or action), **Chain** (start frame = end of clip N, or none), **References** (which hero images, max 3), **Aspect** (16:9 / 9:16).
5. **Hero reference images:** for each video, 1-3 clean images (no text, no UI) of the recurring objects, made once and used as ingredients.
6. Optional **360p draft pass** for hard clips (1 credit/s) before the 720p final; final downloaded with the 1080p upscale.

## 4. How it fits our workflow (order unchanged: voice first)

1. Script approved -> voice recorded and measured.
2. Edit plan: each line gets footage / photo / graph / **Flow**. Flow lines get a clip number (`10-ch2-07`).
3. `flowlist` step writes the clip table (style block, hero references, rows with quote, meaning, seconds, motion, chain, aspect, prompt; total credits) and checks the rules.
4. Muse generates (x1 output, watermark cleaned, audio stripped) and returns a public Drive folder.
5. `flow-in` step: download, match by number, strip audio again, conform to our size/fps, first/middle/last frames for my science check, report missing.
6. `rawcut` step -> Drive (private) -> owner approves -> full render with captions, names, graphs, music, SFX -> Drive.
7. Credits line "Some visuals generated with Google Flow (AI)"; YouTube "altered or synthetic content" box ticked for realistic clips.

## 5. Music and sound

- **Keep our music** (one bed per video, Kevin MacLeod / credited) and our SFX kit. Flow music would change from clip to clip, fight the voice, and its rights/credit line is less clear.
- Flow audio stays stripped (rulebook). Possible later test: Flow ambience for a single clip (e.g. a deep rumble on a collapse) if our SFX kit lacks it.

## 6. What this changes for the viewer

- Every claim has a picture that shows exactly that claim - no generic space filler, no repeated zooms on the same galaxy images.
- Real camera motion and continuous shots make it feel like a documentary, not a slideshow.
- The same hero objects across the video make it feel designed.
- The first 90 s, where we lose most viewers, get the strongest visuals.

## 7. Budget (Pro, ~1,050 credits a month)
Example, a video with 10 clips x ~6 s at 720p = ~180 credits, + a few 360p drafts (~30) + 1080p upscales (10 x 5 = 50) = **~260 credits** (about 4 such videos a month on ~1,050 credits; more clips cost proportionally more). Extends and long clips (11-15 s at 6 credits/s) cost more; the table always shows the total first.

## 8. First test (proposed, ~60-80 credits)
Three clips for video 10's opening: one pull-back (scale), one dolly-in (reveal), one chained pair (end frame -> start frame). Check: warping during camera moves, continuity across the chain, how the 720p->1080p upscale looks next to our 4K footage, and whether the camera edit mode works on an existing clip.

## Sources
- Google Flow Help, "Edit videos & build scenes in Google Flow": https://support.google.com/flow/answer/16935718?hl=en
- Incrypted, "Gemini Omni 1.2 Flash: overview and guide" (18 Nov 2026): https://incrypted.com/en/gemini-omni-1-2-flash-overview-and-guide/
- Runware, "Gemini Omni Flash 1.2 - editing video": https://runware.ai/docs/models/google-gemini-omni-flash-1-2/guides/editing-video
- Google blog, "Gemini Omni 1.1 Flash lets you build with more control": https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-omni-1-1-flash/
- Guides on Flow camera moves, frames-to-video and scene builder: https://www.artea.in/blogs/50-google-flow-camera-commands-2026/ , https://www.simpliaxis.com/resources/what-is-google-flow
