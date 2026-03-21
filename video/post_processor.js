// post_processor.js
// Full video post-production pipeline — 3-Track Assembly Model.
//
// Takes 3 independently-synced tracks and assembles the final YouTube-ready video:
//
// Track 1: INTRO (dynamic video + TTS audio)
// Track 2: MAIN  (per-slide synced NotebookLM video + TTS audio)
// Track 3: OUTRO (dynamic video + TTS audio)
//
// Then applies:
// - Fade transitions between tracks (1s opacity fades)
// - NotebookLM watermark crop (bottom 60px) on main track
// - AXIOM logo overlay (top-left)
// - Subscribe button overlay (bottom-right)
// - Scale to 1920x1080 @ 30fps
// - H.264/AAC output

const { exec, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ASSETS_DIR = path.join(__dirname, '..', 'assets');
const LOGO_PATH = path.join(ASSETS_DIR, 'axiom_logo.png');
const FONT_PATH = 'C\\:/Windows/Fonts/arialbd.ttf';

const FADE_DURATION = 1;  // seconds — fade transition between segments

/**
 * Get the duration of a media file in seconds via ffprobe.
 */
function probeDuration(filePath) {
    const result = execSync(
        `ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${filePath.replace(/\\/g, '/')}"`,
        { encoding: 'utf8' }
    );
    return parseFloat(result.trim());
}

/**
 * 3-Track Assembly: Merge intro, main, and outro into final branded video.
 *
 * VISUAL TIMELINE:
 * |── Intro (dynamic) ──|─ fade ─|── Main (synced) ──|─ fade ─|── Outro (dynamic) ──|
 *
 * OVERLAYS (across main + outro only):
 * - AXIOM logo: top-left, 90% opacity
 * - Subscribe button: bottom-right (red box with text)
 *
 * @param {object} opts
 * @param {string} opts.introVideo  - Dynamic intro video (from intro_generator)
 * @param {string} opts.introAudio  - Intro TTS WAV
 * @param {string} opts.mainVideo   - Per-slide synced video (from engine_2, already has main TTS audio)
 * @param {string} opts.outroVideo  - Dynamic outro video (from intro_generator)
 * @param {string} opts.outroAudio  - Outro TTS WAV
 * @param {string} [opts.outputPath] - Final output path
 * @returns {Promise<string>} - Path to final branded video
 */
async function processVideo(opts) {
    const { introVideo, introAudio, mainVideo, outroVideo, outroAudio, outputPath } = opts;

    console.log(`\n🎬 ═══════════════════════════════════════════════════════════`);
    console.log(`   AXIOM Post-Processor — 3-Track Assembly`);
    console.log(`   ═══════════════════════════════════════════════════════════\n`);

    // Validate all inputs
    const requiredFiles = {
        'Intro video': introVideo,
        'Intro audio': introAudio,
        'Main video': mainVideo,
        'Outro video': outroVideo,
        'Outro audio': outroAudio,
    };
    for (const [label, fp] of Object.entries(requiredFiles)) {
        if (!fs.existsSync(fp)) {
            throw new Error(`${label} not found: ${fp}`);
        }
    }

    // Probe durations
    const introDuration = probeDuration(introVideo);
    const mainDuration = probeDuration(mainVideo);
    const outroDuration = probeDuration(outroVideo);

    console.log(`   Probed durations:`);
    console.log(`      Intro: ${introDuration.toFixed(1)}s`);
    console.log(`      Main:  ${mainDuration.toFixed(1)}s`);
    console.log(`      Outro: ${outroDuration.toFixed(1)}s`);
    console.log(`      Fade:  ${FADE_DURATION}s each transition\n`);

    const baseDir = path.dirname(mainVideo);
    const baseName = path.basename(mainVideo, path.extname(mainVideo));
    const finalOutputPath = outputPath || path.join(baseDir, `${baseName}_branded.mp4`);

    console.log(`   Input main: ${mainVideo}`);
    console.log(`   Output:     ${finalOutputPath}\n`);

    // Probe the audio stream duration of the main video separately —
    // Engine 2 may pad the video container beyond the actual TTS audio length.
    let mainAudioDuration = mainDuration;
    try {
        const raw = execSync(
            `ffprobe -v quiet -show_entries stream=duration -select_streams a:0 -of csv=p=0 "${mainVideo.replace(/\\/g, '/')}"`,
            { encoding: 'utf8' }
        ).trim().split('\n')[0];
        const parsed = parseFloat(raw);
        if (!isNaN(parsed) && parsed > 0) mainAudioDuration = parsed;
    } catch (_) {}

    if (mainAudioDuration < mainDuration - 0.5) {
        console.log(`   Main audio shorter than video: ${mainAudioDuration.toFixed(1)}s < ${mainDuration.toFixed(1)}s — trimming video to audio`);
    }

    const ffmpegCmd = buildFFmpegCommand({
        introVideo, introAudio, mainVideo, outroVideo, outroAudio,
        finalOutputPath, introDuration, mainDuration, outroDuration, mainAudioDuration
    });

    // Save command for debugging
    const cmdLogPath = path.join(__dirname, '..', 'logs', 'post_processor_cmd.txt');
    try {
        fs.mkdirSync(path.dirname(cmdLogPath), { recursive: true });
        fs.writeFileSync(cmdLogPath, ffmpegCmd, 'utf8');
    } catch (_) {}

    return new Promise((resolve, reject) => {
        console.log(`   Running FFmpeg 3-track assembly...\n`);

        const child = exec(ffmpegCmd, {
            maxBuffer: 1024 * 1024 * 200,
            timeout: 15 * 60 * 1000
        }, (error, stdout, stderr) => {
            if (error) {
                console.error(`\n   FFmpeg Post-Processing FAILED`);
                console.error(`   Error: ${error.message}`);
                console.error(`   Last stderr:\n${stderr.slice(-1000)}`);
                const logPath = path.join(__dirname, '..', 'logs', 'post_processor_error.log');
                try {
                    fs.writeFileSync(logPath,
                        `COMMAND:\n${ffmpegCmd}\n\nERROR:\n${error.message}\n\nSTDOUT:\n${stdout}\n\nSTDERR:\n${stderr}`
                    );
                } catch (_) {}
                return reject(error);
            }

            if (!fs.existsSync(finalOutputPath)) {
                return reject(new Error('FFmpeg succeeded but output file missing.'));
            }

            const sizeMB = (fs.statSync(finalOutputPath).size / (1024 * 1024)).toFixed(1);
            let finalDur = 0;
            try { finalDur = probeDuration(finalOutputPath); } catch (_) {}

            console.log(`\n   ═══════════════════════════════════════════════════════`);
            console.log(`      AXIOM Post-Processing COMPLETE`);
            console.log(`      Output:   ${finalOutputPath}`);
            console.log(`      Duration: ${finalDur.toFixed(1)}s`);
            console.log(`      Size:     ${sizeMB} MB`);
            console.log(`   ═══════════════════════════════════════════════════════\n`);

            resolve(finalOutputPath);
        });

        if (child.stderr) {
            child.stderr.on('data', (data) => {
                const line = data.toString().trim();
                if (line.includes('frame=') || line.includes('time=')) {
                    process.stdout.write(`\r   ${line.substring(0, 120)}`);
                }
            });
        }
    });
}

/**
 * Builds the FFmpeg filter graph for 3-track assembly.
 *
 * Inputs:
 *   0: intro video
 *   1: intro audio
 *   2: main video (already has audio from Engine 2)
 *   3: outro video
 *   4: outro audio
 *   5: AXIOM logo PNG
 */
function buildFFmpegCommand(opts) {
    const {
        introVideo, introAudio, mainVideo, outroVideo, outroAudio,
        finalOutputPath, introDuration, mainAudioDuration
    } = opts;

    const fwd = (p) => p.replace(/\\/g, '/');

    const introFadeOut = Math.max(0, introDuration - FADE_DURATION);
    // Use audio duration (not video duration) so fade-out aligns with actual speech end
    const mainFadeOut = Math.max(0, mainAudioDuration - FADE_DURATION);

    const hasLogo = fs.existsSync(LOGO_PATH);

    const filterLines = [
        // ══════════ VIDEO PREP ══════════

        // Intro: scale to 1080p, fade-out at end
        `[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,` +
            `pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,` +
            `setsar=1,fps=30,format=yuv420p,` +
            `fade=t=out:st=${introFadeOut.toFixed(3)}:d=${FADE_DURATION}[intro_v]`,

        // Main: trim to audio duration (Engine 2 may pad video beyond TTS),
        //        crop bottom 60px (NotebookLM watermark), scale to 1080p,
        //        fade-in at start, fade-out at end
        `[2:v]trim=end=${mainAudioDuration.toFixed(3)},setpts=PTS-STARTPTS,` +
        `crop=in_w:in_h-60:0:0,` +
            `scale=1920:1080:force_original_aspect_ratio=decrease,` +
            `pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,` +
            `setsar=1,fps=30,format=yuv420p,` +
            `fade=t=in:st=0:d=${FADE_DURATION},` +
            `fade=t=out:st=${mainFadeOut.toFixed(3)}:d=${FADE_DURATION}[main_v]`,

        // Outro: scale to 1080p, fade-in at start
        `[3:v]scale=1920:1080:force_original_aspect_ratio=decrease,` +
            `pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,` +
            `setsar=1,fps=30,format=yuv420p,` +
            `fade=t=in:st=0:d=${FADE_DURATION}[outro_v]`,

        // ══════════ AUDIO PREP ══════════
        // Normalize all audio to 44100 Hz stereo for clean concat

        // Intro audio (TTS) — no fade, transitions are video-only
        `[1:a]aformat=sample_rates=44100:channel_layouts=stereo[intro_a]`,

        // Main audio (from Engine 2 — already muxed in main video)
        // Trim to actual TTS duration (video may be longer due to Engine 2 padding)
        `[2:a]aformat=sample_rates=44100:channel_layouts=stereo,` +
            `atrim=end=${mainAudioDuration.toFixed(3)},asetpts=PTS-STARTPTS[main_a]`,

        // Outro audio (TTS) — no fade, transitions are video-only
        `[4:a]aformat=sample_rates=44100:channel_layouts=stereo[outro_a]`,

        // ══════════ CONCATENATE ══════════
        `[intro_v][intro_a][main_v][main_a][outro_v][outro_a]concat=n=3:v=1:a=1[concat_v][concat_a]`,
    ];

    // ══════════ OVERLAYS ══════════
    if (hasLogo) {
        filterLines.push(
            // AXIOM logo watermark — top-left, 90% opacity
            `[5:v]scale=150:-1,format=rgba,colorkey=color=0xD6D2CC:similarity=0.25:blend=0.15,` +
                `colorchannelmixer=aa=0.9[wm]`,
            `[concat_v][wm]overlay=20:20[with_wm]`,
        );

        // Subscribe button — bottom-right
        filterLines.push(
            `color=c=0xFF0000:s=240x50:d=1,format=rgba,colorchannelmixer=aa=0.9,` +
                `drawtext=fontfile='${FONT_PATH}':text='SUBSCRIBE':fontcolor=white:fontsize=26:` +
                `x=(w-text_w)/2:y=(h-text_h)/2[sub]`,
            `[with_wm][sub]overlay=W-w-30:H-h-60[final_v]`,
        );
    } else {
        // No logo — just subscribe button on concat
        filterLines.push(
            `color=c=0xFF0000:s=240x50:d=1,format=rgba,colorchannelmixer=aa=0.9,` +
                `drawtext=fontfile='${FONT_PATH}':text='SUBSCRIBE':fontcolor=white:fontsize=26:` +
                `x=(w-text_w)/2:y=(h-text_h)/2[sub]`,
            `[concat_v][sub]overlay=W-w-30:H-h-60[final_v]`,
        );
    }

    const filterComplex = filterLines.join('; ');

    // Build input list
    let inputs = '';
    inputs += `-i "${fwd(introVideo)}" `;    // 0: intro video
    inputs += `-i "${fwd(introAudio)}" `;    // 1: intro audio
    inputs += `-i "${fwd(mainVideo)}" `;     // 2: main video+audio (from Engine 2)
    inputs += `-i "${fwd(outroVideo)}" `;    // 3: outro video
    inputs += `-i "${fwd(outroAudio)}" `;    // 4: outro audio
    if (hasLogo) {
        inputs += `-i "${fwd(LOGO_PATH)}" `; // 5: AXIOM logo PNG
    }

    return `ffmpeg -y ` +
        inputs +
        `-filter_complex "${filterComplex}" ` +
        `-map "[final_v]" -map "[concat_a]" ` +
        `-c:v libx264 -preset fast -crf 20 ` +
        `-c:a aac -b:a 192k ` +
        `-movflags +faststart ` +
        `"${fwd(finalOutputPath)}"`;
}


// CLI
if (require.main === module) {
    const args = process.argv.slice(2);

    if (args.length < 5) {
        console.log(`
AXIOM Post-Processor — 3-Track Assembly Pipeline
─────────────────────────────────────────────────

Usage:
  node post_processor.js <introVideo> <introAudio> <mainVideo> <outroVideo> <outroAudio> [outputPath]

Pipeline:
  Track 1: Intro video + intro TTS audio (fade transition)
  Track 2: Main synced video + main TTS audio (watermark cropped)
  Track 3: Outro video + outro TTS audio (fade transition)
  + AXIOM logo overlay (top-left)
  + Subscribe button (bottom-right)
  + Scale to 1920x1080 @ 30fps
`);
        process.exit(0);
    }

    processVideo({
        introVideo: args[0],
        introAudio: args[1],
        mainVideo: args[2],
        outroVideo: args[3],
        outroAudio: args[4],
        outputPath: args[5]
    })
        .then((out) => console.log(`\nDone: ${out}`))
        .catch((err) => {
            console.error(`\nFATAL: ${err.message}`);
            process.exit(1);
        });
}

module.exports = { processVideo };
