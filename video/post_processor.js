// post_processor.js
// Full video post-production pipeline — runs AFTER Engine 2 has produced the synced video.
//
// What this does:
// 1. Takes the Engine 2 output (synced raw video + TTS audio)
// 2. Prepends the AXIOM intro (7s brand animation)
// 3. Appends the AXIOM outro card (black + logo, ~8s)
// 4. Adds fade transitions between intro→main and main→outro (monetization-safe)
// 5. Crops the NotebookLM watermark (bottom 60px)
// 6. Overlays AXIOM logo (top-left) and subscribe button (bottom-right)
// 7. Scales everything to 1920x1080 @ 30fps
// 8. Outputs a single final MP4

const { exec, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ASSETS_DIR = path.join(__dirname, '..', 'assets');
const INTRO_VIDEO = path.join(ASSETS_DIR, 'axiom_intro.mp4');
const LOGO_PATH = path.join(ASSETS_DIR, 'axiom_logo.png');
const SUBSCRIBE_PATH = path.join(ASSETS_DIR, 'subscribe_button.png');

const OUTRO_DURATION = 8;       // seconds — branded outro card
const FADE_DURATION = 1;        // seconds — fade transition between segments
// NOTE: NotebookLM branding trim (last 3s) is handled in Engine 2 (engine_2_sync.py)
//       BEFORE audio sync, so no audio is lost.

/**
 * Get the duration of a media file in seconds via ffprobe.
 */
function probeDuration(filePath) {
    const result = execSync(
        `ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${filePath}"`,
        { encoding: 'utf8' }
    );
    return parseFloat(result.trim());
}

/**
 * Post-processes the Engine 2 synced video into the final YouTube-ready output.
 *
 * VISUAL TIMELINE:
 * |── AXIOM Intro (7s) ──|─ fade ─|── Main Video ──|─ fade ─|── Outro (8s) ──|
 *
 * OVERLAYS (across entire output):
 * - AXIOM logo: top-LEFT, 60% opacity
 * - Subscribe button: bottom-RIGHT, 80% opacity
 *
 * TRANSITIONS:
 * - Fade-out last 1s of intro + fade-in first 1s of main (dissolve via concat)
 * - Fade-out last 1s of main + fade-in first 1s of outro (dissolve via concat)
 * These are simple opacity fades — YouTube monetization safe (no flash/strobe).
 *
 * @param {string} syncedVideoPath - Path to the Engine 2 output (synced video + TTS audio)
 * @param {string} [outputPath]    - Optional custom output path
 * @returns {Promise<string>}      - Path to the final branded video
 */
async function processVideo(syncedVideoPath, outputPath) {
    console.log(`\n🎬 ═══════════════════════════════════════════════════════════`);
    console.log(`   AXIOM Post-Processor — Full Branding Pipeline`);
    console.log(`   ═══════════════════════════════════════════════════════════\n`);

    // ── Validate all inputs ──
    const requiredFiles = {
        'Synced video': syncedVideoPath,
        'Intro video': INTRO_VIDEO,
        'AXIOM logo': LOGO_PATH,
        'Subscribe button': SUBSCRIBE_PATH,
    };
    for (const [label, fp] of Object.entries(requiredFiles)) {
        if (!fs.existsSync(fp)) {
            throw new Error(`❌ ${label} not found: ${fp}`);
        }
    }

    // ── Probe durations ──
    const introDuration = probeDuration(INTRO_VIDEO);
    const mainDuration = probeDuration(syncedVideoPath);

    console.log(`   📐 Probed durations:`);
    console.log(`      Intro: ${introDuration.toFixed(1)}s`);
    console.log(`      Main:  ${mainDuration.toFixed(1)}s`);
    console.log(`      Outro: ${OUTRO_DURATION}s`);
    console.log(`      Fade:  ${FADE_DURATION}s each transition\n`);

    const baseDir = path.dirname(syncedVideoPath);
    const baseName = path.basename(syncedVideoPath, path.extname(syncedVideoPath));
    const finalOutputPath = outputPath || path.join(baseDir, `${baseName}_branded.mp4`);

    console.log(`   📥 Input:     ${syncedVideoPath}`);
    console.log(`   📤 Output:    ${finalOutputPath}\n`);

    // ── Build & run FFmpeg ──
    const ffmpegCmd = buildFFmpegCommand(
        syncedVideoPath, finalOutputPath,
        introDuration, mainDuration
    );

    // Save command for debugging
    const cmdLogPath = path.join(__dirname, '..', 'logs', 'post_processor_cmd.txt');
    try {
        fs.mkdirSync(path.dirname(cmdLogPath), { recursive: true });
        fs.writeFileSync(cmdLogPath, ffmpegCmd, 'utf8');
    } catch (_) {}

    return new Promise((resolve, reject) => {
        console.log(`   🛠️  Running FFmpeg pipeline...\n`);

        const child = exec(ffmpegCmd, {
            maxBuffer: 1024 * 1024 * 200,
            timeout: 15 * 60 * 1000   // 15 min max
        }, (error, stdout, stderr) => {
            if (error) {
                console.error(`\n❌ FFmpeg Post-Processing FAILED`);
                console.error(`   Error: ${error.message}`);
                console.error(`   Last stderr:\n${stderr.slice(-1000)}`);
                const logPath = path.join(__dirname, '..', 'logs', 'post_processor_error.log');
                try {
                    fs.writeFileSync(logPath,
                        `COMMAND:\n${ffmpegCmd}\n\nERROR:\n${error.message}\n\nSTDOUT:\n${stdout}\n\nSTDERR:\n${stderr}`
                    );
                    console.error(`   Full log: ${logPath}`);
                } catch (_) {}
                return reject(error);
            }

            if (!fs.existsSync(finalOutputPath)) {
                return reject(new Error('FFmpeg succeeded but output file missing.'));
            }

            const sizeMB = (fs.statSync(finalOutputPath).size / (1024 * 1024)).toFixed(1);
            let finalDur = 0;
            try { finalDur = probeDuration(finalOutputPath); } catch (_) {}

            console.log(`\n   ✅ ═══════════════════════════════════════════════════════`);
            console.log(`      AXIOM Post-Processing COMPLETE`);
            console.log(`      Output:   ${finalOutputPath}`);
            console.log(`      Duration: ${finalDur.toFixed(1)}s`);
            console.log(`      Size:     ${sizeMB} MB`);
            console.log(`   ═══════════════════════════════════════════════════════\n`);

            resolve(finalOutputPath);
        });

        // Stream progress
        if (child.stderr) {
            child.stderr.on('data', (data) => {
                const line = data.toString().trim();
                if (line.includes('frame=') || line.includes('time=')) {
                    process.stdout.write(`\r   ⏳ ${line.substring(0, 120)}`);
                }
            });
        }
    });
}


/**
 * Builds the full FFmpeg command.
 *
 * Audio normalization strategy:
 *   All audio streams are resampled to 44100 Hz stereo BEFORE concat,
 *   so FFmpeg concat doesn't choke on mismatched formats.
 *
 * Transition strategy:
 *   Fade-out end of segment N + fade-in start of segment N+1.
 *   Then concat. This is visually identical to a crossfade but
 *   doesn't require xfade (which needs a known offset).
 */
function buildFFmpegCommand(syncedVideoPath, finalOutputPath, introDuration, mainDuration) {
    const fwd = (p) => p.replace(/\\/g, '/');

    // Compute fade-out start times
    const introFadeOutStart = Math.max(0, introDuration - FADE_DURATION);
    const mainFadeOutStart = Math.max(0, mainDuration - FADE_DURATION);

    const filterLines = [
        // ══════════ VIDEO PREP ══════════

        // Intro: scale → 1080p, 30fps, fade-out at end
        `[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,` +
            `pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,` +
            `setsar=1,fps=30,format=yuv420p,` +
            `fade=t=out:st=${introFadeOutStart.toFixed(3)}:d=${FADE_DURATION}[intro_v]`,

        // Main: crop bottom 60px (NotebookLM watermark), scale → 1080p, 30fps,
        //        fade-in at start, fade-out at end
        // NOTE: NotebookLM branding already trimmed in Engine 2
        `[1:v]crop=in_w:in_h-60:0:0,` +
            `scale=1920:1080:force_original_aspect_ratio=decrease,` +
            `pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,` +
            `setsar=1,fps=30,format=yuv420p,` +
            `fade=t=in:st=0:d=${FADE_DURATION},` +
            `fade=t=out:st=${mainFadeOutStart.toFixed(3)}:d=${FADE_DURATION}[main_v]`,

        // Outro card: dark gradient bg + AXIOM logo on white card for contrast, fade-in
        `color=c=0x1A1A2E:s=1920x1080:d=${OUTRO_DURATION}:r=30,format=yuv420p[outro_bg]`,
        // White card behind logo for contrast (450x250 white rectangle)
        `color=c=0xF0F0F0:s=450x250:d=${OUTRO_DURATION}:r=30,format=yuv420p[logo_card]`,
        `[outro_bg][logo_card]overlay=(W-w)/2:(H-h)/2-30[outro_with_card]`,
        `[2:v]scale=380:-1,format=rgba[outro_logo]`,
        `[outro_with_card][outro_logo]overlay=(W-w)/2:(H-h)/2-30:format=auto,format=yuv420p,` +
            `fade=t=in:st=0:d=${FADE_DURATION}[outro_v]`,

        // ══════════ AUDIO PREP ══════════
        // Normalize ALL audio to 44100 Hz stereo so concat works

        // Intro audio (from the Remotion intro — has music/sfx), fade-out at end
        `[0:a]aformat=sample_rates=44100:channel_layouts=stereo,` +
            `afade=t=out:st=${introFadeOutStart.toFixed(3)}:d=${FADE_DURATION}[intro_a]`,

        // Main audio (TTS voice), fade-in at start, fade-out at end
        `[1:a]aformat=sample_rates=44100:channel_layouts=stereo,` +
            `afade=t=in:st=0:d=${FADE_DURATION},` +
            `afade=t=out:st=${mainFadeOutStart.toFixed(3)}:d=${FADE_DURATION}[main_a]`,

        // Outro audio (silence, matching format)
        `anullsrc=r=44100:cl=stereo,atrim=0:${OUTRO_DURATION}[outro_a]`,

        // ══════════ CONCATENATE ══════════
        `[intro_v][intro_a][main_v][main_a][outro_v][outro_a]concat=n=3:v=1:a=1[concat_v][concat_a]`,

        // ══════════ OVERLAYS ══════════

        // AXIOM logo watermark — top-left, 90% opacity, clearly visible
        // colorkey removes the grey/white background, then boost brightness
        `[2:v]scale=150:-1,format=rgba,colorkey=color=0xD6D2CC:similarity=0.25:blend=0.15,colorchannelmixer=aa=0.9[wm]`,
        `[concat_v][wm]overlay=20:20[with_wm]`,

        // Subscribe button — bottom-right, large and catchy
        // Solid red box with bold "SUBSCRIBE" text — fully in-frame
        `color=c=0xFF0000:s=240x50:d=1,format=rgba,colorchannelmixer=aa=0.9,` +
            `drawtext=text='SUBSCRIBE':fontcolor=white:fontsize=26:` +
            `x=(w-text_w)/2:y=(h-text_h)/2[sub]`,
        `[with_wm][sub]overlay=W-w-30:H-h-60[final_v]`,
    ];

    const filterComplex = filterLines.join('; ');

    return `ffmpeg -y ` +
        `-i "${fwd(INTRO_VIDEO)}" ` +            // 0: AXIOM intro
        `-i "${fwd(syncedVideoPath)}" ` +         // 1: Engine 2 synced video + TTS
        `-i "${fwd(LOGO_PATH)}" ` +               // 2: AXIOM logo PNG
        `-filter_complex "${filterComplex}" ` +
        `-map "[final_v]" -map "[concat_a]" ` +
        `-c:v libx264 -preset fast -crf 20 ` +
        `-c:a aac -b:a 192k ` +
        `-movflags +faststart ` +
        `"${fwd(finalOutputPath)}"`;
}


// ═══════════════════════════════════════════════════════════
// CLI
// ═══════════════════════════════════════════════════════════
if (require.main === module) {
    const args = process.argv.slice(2);

    if (args.length < 1) {
        console.log(`
AXIOM Post-Processor — Branding & Assembly Pipeline
────────────────────────────────────────────────────

Usage:
  node post_processor.js <SyncedVideoPath> [OutputPath]

Example:
  node post_processor.js "d:/notebook lm/output/videos/quicksort_final.mp4"

Pipeline:
  ✅ Prepend 7s AXIOM intro (fade transition)
  ✅ Append 8s AXIOM outro card (fade transition)
  ✅ Remove NotebookLM watermark (bottom crop)
  ✅ AXIOM logo overlay (top-left, 60% opacity)
  ✅ Subscribe button overlay (bottom-right, 80% opacity)
  ✅ Scale to 1920x1080 @ 30fps
  ✅ YouTube-ready MP4 output
`);
        process.exit(0);
    }

    processVideo(args[0], args[1])
        .then((out) => console.log(`\n🎉 Done: ${out}`))
        .catch((err) => {
            console.error(`\nFATAL: ${err.message}`);
            process.exit(1);
        });
}

module.exports = { processVideo };
