<!-- Source: yihui-dev/awesome-opus5-5-videos (MIT), filtered for our style by a research agent 2026-11-20. Ideas worth trying in web3d scenes; not rules. Adopted so far: deterministic render(t), review stills before full render, one amber accent, plain digits. Candidates next: velocity-match camera, zoom-out scale ladder, lensing scene, sub-frame motion blur, 1.2 s still end frame, frame-difference pop scan. -->
# Techniques from the yihui prompt collection (filtered for our Hindi space-science style)
Note: ~700 prompts, but only a handful are science and most are one-liners. Most useful content is structural (how the good prompts are built). Text/kinetic-type material skipped.

## Camera moves
- Limit a film to a tiny, named set of camera operations (pull-back, one roll, velocity-match) and give each a narrative reason; never move the camera "just because" [gdgtify-989608]
- Velocity-match: camera tracks a departing object until it looks still while the old background slides away, a good way to sell speed without shake [gdgtify-989608]
- Show acceleration through widening spacing of trailing marks along the path, not camera shake or blur on the subject [gdgtify-989608]
- One smooth camera language per film; ban reversing direction, sudden resets and camera shake [raphaelaubryy-687877, gdgtify-989608]
- Locked, front-on camera where objects rotate instead (drafting-table feel) is a valid calm alternative for diagrams [heyiamnick-119558]
- Continuous zoom-out from a ground-level spot to the whole observable universe in one three.js take, no external assets [kgonia7-746268]
- Slow push inside every scene plus faint handheld float keeps stills alive [twoclipping-041659]
- Dive through an object into the next scene (camera falls through a head until the frame is all one colour) as a hand-off [twoclipping-041659]

## Scale, numbers, data
- Zoom-out ladder (hill, Earth, Solar System, galaxy, universe) as the standard way to show scale; one continuous move beats a slideshow of sizes [kgonia7-746268]
- Compare two altitudes/distances in one animation (orbital altitude vs surface distance, e.g. Point Nemo and the spacecraft graveyard) [haribuilds-007643]
- Pull real public data first, then compare "this year vs other years" in the animation; ground the story in fetched numbers [groundcontrol-230877]
- Zoom from the overview to specific routes while slowing the moving objects when zoomed in, so the viewer can read the landscape [milos-gis-317580]
- A counter that ticks every frame up to the real-world scale makes a huge number felt (use plain digits, no glow) [notdwd-998633]
- Flat plain line vs steep lit curve as an A/B contrast for "slow way vs fast way" growth [notdwd-998633]
- Mark invented numbers as abstract: say "abstract metaphor, no invented mission data" in the brief to stop fake telemetry [gdgtify-989608]

## Shot and scene ideas for science
- Gravitational lensing lab: drag the black hole and background sky bends into arcs, closing into an Einstein ring on perfect alignment [voxyz-ai-345550]
- Procedural whole planet from maths only: oceans, mountains, night-side city lights, sun position drives day/night, sea level rises to drown land [0xsolty-735200]
- Exploded-view of a mechanism with each part sliding apart along one axis, light beams bending through glass elements (reusable for telescope optics) [aichrislee-408244]
- Cutaway of a system with flow colour-coded by direction (blue in, red out) and parts in time with one beat [aichrislee-378670]
- Single hairline ellipse as orbit with a small mark at the focus: minimal, honest orbital diagram [gdgtify-989608]
- Frame the visual as "an astronomical instrument", and list banned clichés (starfield wallpaper, lens flares, decorative telemetry) [gdgtify-989608]
- Molecular/orbital simulation made quickly as an educational sim; iterate on structures afterward [explorations-iq-921682]
- Accuracy request in one line ("scientifically accurate, one canvas, one HTML file") works for single-topic mechanism explainers like optogenetics [rashadmirza404-020971]
- Launch-profile comparison (suborbital vs orbital deployment) as a 3D render brief [vic305-885957]

## Transitions
- Make every scene out of the previous one (shape morphs into next scene) rather than crossfades; a ban list of crossfades and blur-ins forces this [heyiamnick-119558, twoclipping-496100]
- A large flood shape must overscale past the corners and take ~0.3 s, or half the screen changes in a single frame [twoclipping-496100]
- Hand-off starts on the exact last frame of the previous scene (position match) [twoclipping-041659]
- Scene change by a single scan line sweeping across the frame [heyiamnick-119558]
- Match cuts: measure element positions at runtime so the next shot starts where the last one ended [raphaelaubryy-687877]
- Avoid arbitrary full-frame crossfades and long blank gaps [groundcontrol-230877, notdwd-998633]

## Pacing
- Write the storyboard as time ranges (0-3.5, 3.5-6 ...) with one purpose per range; add a reading-hold of ~0.7 s before any ornamental move [gdgtify-989608]
- End on a fully still held frame (about 1.2 s) so the final image can be absorbed [gdgtify-989608]
- Cap holds (0.5-1.5 s in fast pieces, ~1 s of frozen screen per 30 s); for a documentary raise this but still never leave dead time [notdwd-998633, heyiamnick-119558]
- Cut on the beat grid: measure tempo and drop with numpy, calibrate to real kicks; for us, align cuts to narration word timestamps instead [raphaelaubryy-687877, twoclipping-041659]
- Use faster-whisper word timestamps to hang each scene on spoken words, one short chunk at a time (good fit for "visuals show what narrator says") [twoclipping-041659]
- Ask for a storyboard with all timings approved BEFORE any code [raphaelaubryy-687877]
- "Something happens every beat" rule; moves start ~50 ms early so they land on the beat [heyiamnick-119558]

## Easing and motion
- Critically damped spring, no overshoot, as the single easing family; exponential ease for wipes/exits; ban bouncy easing [heyiamnick-119558, raphaelaubryy-687877]
- Nothing pops in: ~0.5 s eased glides with a soft start [twoclipping-041659]
- Real motion blur by rendering 3-4 sub-frames per frame and blending with ffmpeg tmix, not fake ghost copies [raphaelaubryy-687877, twoclipping-496100]
- Motion blur only on trailing geometry, never on the thing being read [gdgtify-989608]
- Slow, long-period motion on cinematic scenes; pixel/limited-fps look only if deliberately chosen [majidmanzarpour-927543]

## Lighting and post-processing
- Path-traced look checklist: soft shadows, ambient occlusion, glossy reflection, fog with light shafts, depth of field, motion blur, bloom [xanares-738984]
- One raymarching fragment shader serving as both live player and render source (WebGL2); 16 spp offline at 1080p60 [xanares-738984]
- Film finish in numpy per frame: fresh grain each frame, halation on bright edges, vignette ~0.65x at corners, 1 px chroma fringe (edge-clamped) [twoclipping-496100, notdwd-998633]
- Heat-camera ramp (black > red > orange > cream) with a razor-sharp edge and soft outer glow, driven by thickness; useful for thermal/infrared science shots [twoclipping-041659]
- Light via line/scan density instead of blur halo, a way to get "glow" without glow [heyiamnick-119558]
- Limit palette to one saturated accent on neutral base (matches our amber accent) [notdwd-998633, raphaelaubryy-687877]
- Premium restraint: faint ambient bloom and restrained vignette only [groundcontrol-230877]

## Prompt-structure patterns that worked
- Tagged sections: inputs / direction / structure / build / gotchas / start; keeps long briefs scannable [twoclipping-496100, raphaelaubryy-687877, heyiamnick-119558]
- Put a "Banned:" list in the direction block (crossfades, particles, glows, bouncy easing, templates); bans steer harder than adjectives [twoclipping-496100, heyiamnick-119558]
- Specify exact hex colours per role, and an empty-border safe margin where nothing rests [gdgtify-989608, heyiamnick-119558]
- Determinism: every style computed from time via seek(t), frame(n) = t/60, no timers/CSS transitions/runtime randomness so any frame renders reproducibly [gdgtify-989608, twoclipping-496100]
- Closed-form springs: sum one spring per target change so a value stays a pure function of time [twoclipping-496100]
- Arc-length sampling for even spacing on curves; analytic paths with blended tangent, no teleporting [gdgtify-989608]
- Quality gate: inspect frames at named timestamps (or one per beat, or contact sheets) before the full render; scan for single-frame pops via frame-difference spikes [gdgtify-989608, twoclipping-496100, xanares-738984]
- Multi-round review loop: two reviewers rank issues P0/P1/P2, a third fixes, back up and screenshot each round, roll back failures; rounds themed (materials/lighting, camera/interaction, science communication, ship decision) [voxyz-ai-345550]
- Use real archival material and real pages instead of stock/fake UI; "never placeholder cards" [notdwd-998633, raphaelaubryy-687877]
- Re-encode footage all-intra (ffmpeg -g 1) and await 'seeked' per frame for frame-accurate video in a seek renderer [twoclipping-496100]
- Place each SFX by its measured peak, loudnorm to -14 LUFS [twoclipping-496100, raphaelaubryy-687877]
- Gotcha: opacity/filter on a preserve-3d element flattens it; fade its wrapper instead [raphaelaubryy-687877]
