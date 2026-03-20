// post_processor.js
// Full video post-production pipeline:
// 1. Enhance transcript with intro/outro voice scripts
// 2. Generate TTS from the full enhanced script
// 3. FFmpeg: Concat AXIOM intro → main video (cropped, branded) → outro card
//    with the full TTS audio playing underneath continuously

const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const { generateTTS } = require('./tts_generator');
const { enhanceTranscript } = require('../scripts/transcript_enhancer');

const ASSETS_DIR = path.join(__dirname, '../assets');
const INTRO_VIDEO = path.join(ASSETS_DIR, 'axiom_intro.mp4');     // Pre-rendered Remotion intro (7s)
const LOGO_PATH = path.join(ASSETS_DIR, 'axiom_logo.png');
const SUBSCRIBE_PATH = path.join(ASSETS_DIR, 'subscribe_button.png');

/**
 * Full Post-Processing Pipeline:
 *
 * VISUAL TIMELINE:
 * |── AXIOM Intro (7s) ──|── Main NotebookLM Video ──|── Outro Card (black+logo) ──|
 *
 * AUDIO TIMELINE (one continuous TTS track):
 * |── Intro voice ──|── Main transcript voice ──|── Outro voice (subscribe etc) ──|
 *
 * The TTS audio is generated from the full enhanced script (intro + body + outro).
 * The pre-rendered intro video plays during the intro voice segment.
 * The main NotebookLM video plays during the body voice segment.
 * A simple branded card plays during the outro voice segment.
 * AXIOM watermark (top-left) and subscribe button (bottom-right) overlay everything.
 *
 * @param {string} rawVideoPath - Path to the raw NotebookLM MP4
 * @param {string} rawTranscript - The raw transcript text from NotebookLM
 * @param {string} topicName - Topic being covered
 * @param {string} subjectName - Subject name
 * @returns {Promise<string>} - Path to the final branded video
 */
async function processVideo(rawVideoPath, rawTranscript, topicName, subjectName) {
    console.log(`\n🎬 Starting Full Video Post-Processing...`);

    if (!fs.existsSync(rawVideoPath)) {
        throw new Error(`Raw video not found at ${rawVideoPath}`);
    }
    if (!fs.existsSync(INTRO_VIDEO)) {
        throw new Error(`Pre-rendered intro not found at ${INTRO_VIDEO}. Run: cd intro && npx remotion render AxiomIntro out/intro.mp4`);
    }

    const baseDir = path.dirname(rawVideoPath);
    const audioPath = path.join(baseDir, 'generated_voice.wav');
    const finalOutputPath = path.join(baseDir, 'final_output.mp4');

    // ==========================================
    // STEP 1: Enhance transcript with intro/outro
    // ==========================================
    console.log(`\n--- Step 1: Enhancing Transcript ---`);
    const enhanced = enhanceTranscript(rawTranscript, topicName, subjectName);

    const enhancedPath = path.join(baseDir, 'enhanced_transcript.txt');
    fs.writeFileSync(enhancedPath, enhanced.fullScript, 'utf8');
    console.log(`Enhanced transcript saved to: ${enhancedPath}`);

    // ==========================================
    // STEP 2: Generate TTS from the FULL enhanced script
    // ==========================================
    console.log(`\n--- Step 2: TTS Voice Generation ---`);
    await generateTTS(enhanced.fullScript, audioPath);

    // ==========================================
    // STEP 3: FFmpeg Complex Pipeline
    // ==========================================
    console.log(`\n--- Step 3: FFmpeg Video Assembly ---`);

    const introDuration = 7; // seconds — matches the pre-rendered Remotion intro
    const outroDuration = enhanced.outroDurationSec;

    // FFmpeg Strategy:
    // 1. Scale the intro to match main video dimensions (1920x1080, just in case)
    // 2. Crop main video (remove bottom 60px watermark), then pad back to 1080
    // 3. Generate a black outro card with the AXIOM logo centered
    // 4. Concatenate: intro → main → outro
    // 5. Overlay AXIOM watermark (top-left) and subscribe button (bottom-right) across entire output
    // 6. Replace all audio with the single TTS track

    const ffmpegCommand = `ffmpeg -y ` +
        `-i "${INTRO_VIDEO}" ` +             // Input 0: Pre-rendered AXIOM intro
        `-i "${rawVideoPath}" ` +            // Input 1: Raw NotebookLM video
        `-i "${audioPath}" ` +               // Input 2: Full TTS audio
        `-i "${LOGO_PATH}" ` +               // Input 3: AXIOM logo for watermark
        `-i "${SUBSCRIBE_PATH}" ` +          // Input 4: Subscribe button
        `-filter_complex "` +
        // Prep intro: scale to 1920x1080, set SAR/timebase
        `[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30[intro]; ` +
        // Prep main: crop bottom 60px watermark, pad back to 1080p
        `[1:v]crop=in_w:in_h-60:0:0,scale=1920:1020:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30[main]; ` +
        // Generate outro card: black with logo overlay
        `color=c=black:s=1920x1080:d=${outroDuration}:r=30,setsar=1[outro_bg]; ` +
        `[3:v]scale=250:-1,format=rgba[outro_logo]; ` +
        `[outro_bg][outro_logo]overlay=(W-w)/2:(H-h)/2[outro]; ` +
        // Concatenate all three segments
        `[intro][main][outro]concat=n=3:v=1:a=0[concat_v]; ` +
        // Prepare overlays: watermark logo (small, top-left)
        `[3:v]scale=100:-1,format=rgba,colorchannelmixer=aa=0.6[wm]; ` +
        // Subscribe button (bottom-right)
        `[4:v]scale=130:-1,format=rgba,colorchannelmixer=aa=0.8[sub]; ` +
        // Apply watermark
        `[concat_v][wm]overlay=20:20[with_wm]; ` +
        // Apply subscribe button
        `[with_wm][sub]overlay=W-w-20:H-h-20[final]" ` +
        // Map final video + TTS audio
        `-map "[final]" -map 2:a:0 ` +
        `-c:v libx264 -preset fast -crf 20 -c:a aac -b:a 192k -shortest ` +
        `"${finalOutputPath}"`;

    return new Promise((resolve, reject) => {
        console.log(`🛠️ FFmpeg Complex Pipeline:`);
        console.log(`   📼 Intro: AXIOM animated reveal (${introDuration}s)`);
        console.log(`   📹 Main: NotebookLM video (cropped, cleaned)`);
        console.log(`   🎬 Outro: AXIOM logo card (${outroDuration}s)`);
        console.log(`   🔊 Audio: Full TTS (intro voice + body + outro voice)`);
        console.log(`   💧 Watermark: AXIOM logo (top-left, 60% opacity)`);
        console.log(`   🔔 Subscribe: Button (bottom-right, 80% opacity)`);

        const child = exec(ffmpegCommand, { maxBuffer: 1024 * 1024 * 100 }, (error, stdout, stderr) => {
            if (error) {
                console.error(`❌ FFmpeg Processing Failed: ${error.message}`);
                // Output last 500 chars of stderr for debugging
                console.error(`Last stderr: ${stderr.slice(-500)}`);
                return reject(error);
            }
            if (!fs.existsSync(finalOutputPath)) {
                return reject(new Error("FFmpeg returned success but final_output.mp4 does not exist."));
            }
            console.log(`\n✅ Final branded video ready: ${finalOutputPath}`);
            // Cleanup temp audio
            try { fs.unlinkSync(audioPath); } catch(e) {}

            resolve(finalOutputPath);
        });
    });
}

// CLI for testing
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 4) {
        console.log("Usage: node post_processor.js <VideoPath> <TranscriptFile> <TopicName> <SubjectName>");
    } else {
        const transcript = fs.readFileSync(args[1], 'utf8');
        processVideo(args[0], transcript, args[2], args[3]).catch(console.error);
    }
}

module.exports = { processVideo };
