---
name: flow-clip-director
description: Direct Google Flow (Veo) video clips for the science channel - write the clip list (one row per narration slice, exact Hindi quote, meaning, needed length, full one-paragraph Flow prompt with the locked style block) from the measured voiceover. Use whenever a video or Short needs visuals that real footage or photos cannot give, or when the owner asks for Flow prompts. Claude is the director and only writes the list; the owner's executor (Muse) generates in Flow, cleans and assembles. Read before writing any clip prompt.
---

# Directing Google Flow clips (owner's rulebook, corrected 2026-11-21 from a live check of the account)

Claude writes the clip list. The owner's executor (Muse) generates the clips in Flow, cleans them and returns them (a public Drive folder). Claude never touches Flow.

## The one fact: clip length depends on the model (live check 21 Nov 2026; the Flow screen wins if it differs)
- **Omni 1.2 Flash (default):** Length slider 3-15 s in 1 s steps (default 8). Any whole-second length in that range is generated directly.
- **Omni 1.1 Flash** (leaves Flow 5 Dec 2026): 4, 6, 8 or 10 s only.
- **Veo 3.1 Lite / Fast / Quality:** fixed 8 s, 720p, no length control (Fast and Quality leave 5 Dec 2026).
- The Flow agent composer ("Describe your goal") has no duration control: Muse turns the agent off and uses the manual create bar.
- Nothing under 3 s can be generated: a 2 s insert is cut from a 3 s (or longer) generation. Never brief a 1-2 s generation.
- A slice up to 15 s is one Omni 1.2 Flash clip; longer than 15 s -> two clips split at a clause break, never mid-sentence.
- Every brief carries the exact narration quote and the needed length in seconds. Never absolute timestamps: timing comes from the real voiceover audio.
- Veo Extend was retired 5 Nov 2026: get the length right in the brief; do not plan on extending later.

## How Flow is reached (limits and cost)
- No API or connector: flow.google.com in a browser, signed in to the owner's Flow account (Pro tier). Never ask Muse to change accounts.
- About 4.5 min per render; Muse queues and collects later.
- Cost per clip at 720p (the screen shows the total for 2 outputs):
  - Omni 1.2 Flash: 3 credits/s up to 10 s (3 s = 9, 4 s = 12, 5 s = 15, 6 s = 18, 7 s = 21, 8 s = 24, 9 s = 27, 10 s = 30), then 6 credits/s for 11-15 s (11 s = 36, 12 s = 42, 13 s = 48, 14 s = 54, 15 s = 60). 360p: 1 credit/s.
  - Omni 1.1 Flash: 4 s = 7, 6 s = 10, 8 s = 12, 10 s = 15.
  - Veo 3.1 Lite 10, Fast 20, Quality 100 credits per 8 s clip.
- Balance 21 Nov 2026: 1,050 credits, resets 3 Dec. Muse reports the running total with each video. Prefer lengths of 10 s or less (cheaper rate) when the slice allows.
- **At most 10 Flow clips per video**; more needs the owner's explicit approval.
- "Confirm before generating" stays on **Always**; never set it to Never. Muse approves each generation's stated cost one at a time, nothing else. If a price differs from the above, stop and report.
- Include the total credit cost of the clip list at the bottom of the table.

## What the clip must show
- One visual per narration slice, showing exactly what the narrator says at that moment (a star collapsing, not generic space). One clear action per clip; the movement itself shows the narration.
- Real named people get free-licensed PHOTOS (PD, CC0, CC BY, CC BY-SA), never Flow clips; no free photo -> a typed name card, never a generated face.
- Flow clips are for things with no specific person: phenomena, events, planets, stars, black holes, experiments, machines, processes, maps, diagrams in motion, landscapes, objects.
- Use real footage (NOIRLab, ESO, ESA, NASA) where it exactly shows the line; Flow fills the gaps. No repeated static galaxy zooms.

## Locked style block
Before the first clip, write one style block for the video (look - realistic cinematic OR flat cartoon, never mixed; lighting; palette; realism; camera behaviour) and paste it word for word into every prompt. It never changes mid-video. If the owner corrects it, say the correction back in short plain sentences, confirm, then continue.
Channel default (owner may change): `realistic cinematic space visuals, deep blacks, warm starlight with a soft amber accent, physically plausible motion, no cartoon styling`

## Prompt template (follow exactly)
One flowing paragraph, plain prose, no headers, bullets, labels or line breaks. Style block verbatim. The length in seconds comes from the clip list. Say what stays still. One simple continuous action. End with the negative run.

`A <length>-second <style> clip, <LOCKED STYLE, verbatim>, <one simple continuous action>, against <static background> which is completely still with no moving elements and no camera movement, with no spoken dialogue and no background music, the camera stays completely locked with no zoom or pan, motion is smooth and simple with no glitching, no warping, no morphing, no flickering, no extra limbs, no duplicate characters, and no on-screen text, subtitles, watermarks or logos.`

- Silent always (voice and music are added later). No on-screen text ever (labels go on in the edit with channel fonts).
- Hindi narration, English prompt: translate the meaning into what is seen, not the words.
- Prompts are text only. Never pass a screenshot as a reference image (UI, captions, player bars, watermarks become the first frame); a reference image must be a clean crop.

Worked example. Narration: "Phir taara apne hi wazan se andar ki taraf girne lagta hai." Needed: 4 s.
`A four-second realistic cinematic space clip, deep blacks with warm starlight and physically plausible motion, a massive glowing star slowly collapsing inward toward its own centre, against a still field of distant stars which is completely still with no moving elements and no camera movement, with no spoken dialogue and no background music, the camera stays completely locked with no zoom or pan, motion is smooth and simple with no glitching, no warping, no morphing, no flickering, no extra limbs, no duplicate characters, and no on-screen text, subtitles, watermarks or logos.`
Muse generates exactly 4 s on Omni 1.2 Flash (12 credits) and trims it to the slice.

## The handoff: one table per video (nothing is generated before it exists)
Locked style block at the top, then:

| Clip | Narration quote (Hindi, exact words) | What it means (English) | Needed length (s) | Full Flow prompt |
|---|---|---|---|---|

- One row per clip, one clip per narration slice; never reuse a clip in another scene.
- Needed length: any whole number of seconds from 3 to 15; a slice over 15 s gets two rows, split at a clause break. At most 10 rows unless the owner approves more.
- No absolute timestamps: quote + needed length is the timing. Measure needed length from the recorded voice (word times in `voice/timeline.json`, at the final speed).
- Number clips `<prod>-<chapter>-<nn>` (e.g. `10-ch2-07`) and ask for the returned files to carry that number, so the pipeline places them automatically.

## How a clip plays and is checked
- Plays once, forward only, then cut to the next visual. No boomerang, last-frame hold or slow-zoom stretch.
- Check first, middle and last frame of every clip: reject for watermark, stray text, player bar, wrong style, or movement that does not show the line. Remake once as a genuinely different shot.
- Fails twice -> a detailed still for that slice (setting and emotion, slow zoom), more detailed than a video, never a placeholder.
- Every Flow clip has a visible Gemini sparkle (bottom right): cleaned before the edit. The invisible SynthID mark is never stripped; clips are never presented as filmed footage, and AI use is disclosed (YouTube "altered or synthetic content" where realistic).
- Report every batch honestly: done, missing, fallback. A missing clip is never counted as done.

## Order of work (never change it)
1. Approved script; narration fixed, one slice per scene.
2. Voiceover, then measure it (timing from the real audio).
3. Claude's clip list (the table), built from the measured voiceover.
4. Generate in Flow, clean, check; raw cut: clips trimmed to their voice windows, full voice underneath, no captions, grade or polish.
5. Stop for the owner's approval of the raw cut; fix only the scenes he names.
6. Finish after approval: captions, grade, polish; finished video to Drive. Nothing public without the owner's explicit order for that file.

## Never
- Change the narration, voice or scene timings to fit a clip limit.
- Use a clip from one scene in another.
- Brief a single generation shorter than 3 s or longer than 15 s, or a Veo 3.1 clip at any length but 8 s.
- Ask for text, dialogue, music or a real person's face in a Flow clip.
- Present a still, fallback or missing clip as the real clip.
- Make anything public or share a Drive link as public without the owner's explicit order for that file.

**Short version:** Flow's default model is Omni 1.2 Flash: silent clips of 3 to 15 s, 3 credits a second at 720p (8 s = 24 credits); Veo 3.1 is fixed at 8 s. At most 10 clips per video. One visual per slice, showing exactly what is said. Real people get free photos. One locked style block in every prompt. No text, dialogue or music in any clip. Audio first, measure, clip list, generate, raw cut, owner approves.
