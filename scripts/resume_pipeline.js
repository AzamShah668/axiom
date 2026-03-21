/**
 * resume_pipeline.js
 * One-shot runner to complete the pipeline from Step 4E onwards.
 * Fixes metadata to DNS and re-generates intro/outro + TTS, then
 * completes all remaining steps through final video render.
 *
 * Usage: node scripts/resume_pipeline.js
 */

require('dotenv').config({ path: `${__dirname}/../config/.env` });

const fs   = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// ── Module imports ──────────────────────────────────────────────────────────
const { enhanceTranscript }          = require('./transcript_enhancer');
const { enhanceWithEmotions }        = require('./emotion_enhancer');
const { segmentTTSAudio }            = require('./tts_segmenter');
const { generateIntroVideo, generateOutroVideo } = require('../video/intro_generator');
const { processVideo }               = require('../video/post_processor');
const { generateSEOMetadata }        = require('./seo_generator');

const PYTHON_EXE = 'C:\\Users\\AZAM RIZWAN\\qwen-tts-gpu\\Scripts\\python.exe';
const ROOT       = path.join(__dirname, '..');
const DATA_DIR   = path.join(ROOT, 'data');
const OUTPUT     = path.join(ROOT, 'output');

// ── Corrected metadata ──────────────────────────────────────────────────────
const TOPIC   = 'How DNS Works';
const SUBJECT = 'Computer Networks';
const CHAPTER = 'Application Layer';

// Use the existing data directory (files are already here from previous run)
const SAFE_NAME     = 'file_systems_vs_dbms'; // keep existing dir name
const topicDataDir  = path.join(DATA_DIR, SAFE_NAME);
const videosDir     = path.join(OUTPUT, 'videos');
const videoPath     = path.join(OUTPUT, 'notebooklm_raw', `notebooklm_${SAFE_NAME}.mp4`);

function runPython(scriptPath, args = []) {
    const pyExe = PYTHON_EXE.replace(/\\/g, '/');
    const script = scriptPath.replace(/\\/g, '/');
    const quotedArgs = args.map(a => `"${a.replace(/\\/g, '/')}"`).join(' ');
    const cmd = `"${pyExe}" "${script}" ${quotedArgs}`;
    console.log(`   $ python ${path.basename(script)} ...`);
    execSync(cmd, { stdio: 'inherit', maxBuffer: 1024 * 1024 * 50, timeout: 15 * 60 * 1000 });
}

async function main() {
    console.log('\n╔══════════════════════════════════════════════════════╗');
    console.log('║  🔄 RESUME PIPELINE — Fix to DNS + Complete Render  ║');
    console.log('╚══════════════════════════════════════════════════════╝');
    console.log(`   Topic:   ${TOPIC}`);
    console.log(`   Subject: ${SUBJECT}`);
    console.log(`   Chapter: ${CHAPTER}`);
    console.log(`   Data:    ${topicDataDir}\n`);

    fs.mkdirSync(videosDir, { recursive: true });

    const enhancedJsonPath = path.join(topicDataDir, 'enhanced_transcript.json');
    const emotionalScriptPath = path.join(topicDataDir, 'emotional_transcript.txt');

    // ══════════════════════════════════════════════════════════════════════
    // STEP 1: Re-generate Enhanced Transcript with DNS metadata
    // ══════════════════════════════════════════════════════════════════════
    if (fs.existsSync(enhancedJsonPath)) {
        const existing = JSON.parse(fs.readFileSync(enhancedJsonPath, 'utf8'));
        if (existing.introText && existing.introText.includes('How DNS Works')) {
            console.log('\n--- STEP 1: Enhanced Transcript (DNS) --- SKIPPED (already done)');
        } else {
            console.log('\n--- STEP 1: Re-generate Enhanced Transcript (DNS) ---');
            const originalText = fs.readFileSync(path.join(topicDataDir, 'original_transcript.txt'), 'utf8');
            const enhanced = enhanceTranscript(originalText, TOPIC, SUBJECT);
            fs.writeFileSync(enhancedJsonPath, JSON.stringify(enhanced, null, 2), 'utf8');
            fs.writeFileSync(path.join(topicDataDir, 'enhanced_transcript.txt'), enhanced.fullScript, 'utf8');
            console.log('   ✅ Enhanced transcript saved');
        }
    } else {
        console.log('\n--- STEP 1: Re-generate Enhanced Transcript (DNS) ---');
        const originalText = fs.readFileSync(path.join(topicDataDir, 'original_transcript.txt'), 'utf8');
        const enhanced = enhanceTranscript(originalText, TOPIC, SUBJECT);
        fs.writeFileSync(enhancedJsonPath, JSON.stringify(enhanced, null, 2), 'utf8');
        fs.writeFileSync(path.join(topicDataDir, 'enhanced_transcript.txt'), enhanced.fullScript, 'utf8');
        console.log('   ✅ Enhanced transcript saved');
    }

    // ══════════════════════════════════════════════════════════════════════
    // STEP 2: Re-generate Emotional Transcript
    // ══════════════════════════════════════════════════════════════════════
    if (fs.existsSync(emotionalScriptPath) && fs.statSync(emotionalScriptPath).size > 1000) {
        // Check if it already has DNS content
        const existing = fs.readFileSync(emotionalScriptPath, 'utf8');
        if (existing.includes('How DNS Works') || existing.includes('DNS')) {
            console.log('\n--- STEP 2: Emotion Enhancement --- SKIPPED (already done)');
        } else {
            console.log('\n--- STEP 2: Emotion Enhancement ---');
            const fullScript = fs.readFileSync(path.join(topicDataDir, 'enhanced_transcript.txt'), 'utf8');
            const emotionalScript = await enhanceWithEmotions(fullScript);
            fs.writeFileSync(emotionalScriptPath, emotionalScript, 'utf8');
            console.log('   ✅ Emotional transcript saved');
        }
    } else {
        console.log('\n--- STEP 2: Emotion Enhancement ---');
        const fullScript = fs.readFileSync(path.join(topicDataDir, 'enhanced_transcript.txt'), 'utf8');
        const emotionalScript = await enhanceWithEmotions(fullScript);
        fs.writeFileSync(emotionalScriptPath, emotionalScript, 'utf8');
        console.log('   ✅ Emotional transcript saved');
    }

    // ══════════════════════════════════════════════════════════════════════
    // STEP 3: Re-generate TTS + Timestamps
    // ══════════════════════════════════════════════════════════════════════
    const fullTtsWav = path.join(topicDataDir, 'full_tts.wav');
    const fullTtsTimestamps = path.join(topicDataDir, 'full_tts_timestamps.json');

    if (fs.existsSync(fullTtsTimestamps) && fs.statSync(fullTtsTimestamps).size > 1000) {
        console.log('\n--- STEP 3: TTS + Timestamps --- SKIPPED (already done)');
    } else {
        console.log('\n--- STEP 3: TTS Voice Clone + Whisper Timestamps ---');
        const colabData = JSON.parse(fs.readFileSync(path.join(ROOT, 'video/colab_url.json'), 'utf8'));
        const gradioUrl = colabData.gradio_url;
        console.log(`   Gradio URL: ${gradioUrl}`);

        const ttsScript = path.join(ROOT, 'scripts', 'tts_full_generate.py');
        runPython(ttsScript, [emotionalScriptPath, fullTtsWav, fullTtsTimestamps, gradioUrl]);
        console.log('   ✅ TTS + timestamps generated');
    }

    // ══════════════════════════════════════════════════════════════════════
    // STEP 4H: Segment TTS Audio
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n--- STEP 4H: TTS Audio Segmentation ---');
    const segments = segmentTTSAudio(fullTtsWav, fullTtsTimestamps, enhancedJsonPath, topicDataDir);
    console.log('   ✅ Audio segmented into intro/main/outro');

    // ══════════════════════════════════════════════════════════════════════
    // STEP 4I: Per-Slide Video Sync (Engine 2)
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n--- STEP 4I: Per-Slide Video Sync (Engine 2) ---');

    // First: Whisper on main audio segment
    const mainTtsTimestamps = path.join(topicDataDir, 'main_tts_timestamps.json');
    const engine1Script = path.join(ROOT, 'scripts', 'engine_1_transcribe.py');
    runPython(engine1Script, [segments.mainAudio, mainTtsTimestamps, 'base']);

    // Then: Engine 2 sync
    const slideMapJson = path.join(topicDataDir, 'slide_map.json');
    const syncedMainVideo = path.join(videosDir, `${SAFE_NAME}_synced_main.mp4`);
    const engine2Script = path.join(ROOT, 'scripts', 'engine_2_sync.py');
    runPython(engine2Script, [videoPath, segments.mainAudio, slideMapJson, mainTtsTimestamps, syncedMainVideo]);
    console.log('   ✅ Main video synced to TTS');

    // ══════════════════════════════════════════════════════════════════════
    // STEP 4J: Generate Intro/Outro Videos
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n--- STEP 4J: Generate Dynamic Intro/Outro Videos ---');
    const introVideoPath = path.join(videosDir, `${SAFE_NAME}_intro.mp4`);
    const outroVideoPath = path.join(videosDir, `${SAFE_NAME}_outro.mp4`);

    generateIntroVideo({
        introAudioPath: segments.introAudio,
        outputPath: introVideoPath,
        topic: TOPIC, subject: SUBJECT, chapter: CHAPTER
    });

    generateOutroVideo({
        outroAudioPath: segments.outroAudio,
        outputPath: outroVideoPath,
        topic: TOPIC
    });
    console.log('   ✅ Intro/outro videos generated');

    // ══════════════════════════════════════════════════════════════════════
    // STEP 4K: 3-Track Assembly
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n--- STEP 4K: 3-Track Assembly (Final Post-Processing) ---');
    const finalVideoPath = await processVideo({
        introVideo: introVideoPath,
        introAudio: segments.introAudio,
        mainVideo: syncedMainVideo,
        outroVideo: outroVideoPath,
        outroAudio: segments.outroAudio,
        outputPath: path.join(videosDir, `${SAFE_NAME}_final.mp4`)
    });
    console.log(`   ✅ Final video: ${finalVideoPath}`);

    // ══════════════════════════════════════════════════════════════════════
    // STEP 5: Thumbnail
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n--- STEP 5: Thumbnail Generation ---');
    let thumbnailPath = path.join(OUTPUT, `thumbnail_HOW_DNS_WORKS.png`);
    try {
        const { renderThumbnail } = require('../modules/thumbnails/scripts/render_thumbnail');
        await renderThumbnail({
            templatePath: path.join(ROOT, 'tools/thumbnail_generator.html'),
            outputPath: thumbnailPath,
            params: {
                TOP_BADGE: SUBJECT,
                MAIN_TITLE: TOPIC.toUpperCase().replace(/ /g, '<br>'),
                SUBTITLE: CHAPTER,
                SUB_LINE: 'The Internet\'s Phone Book Explained',
                MUST_WATCH_TEXT: 'MUST WATCH',
                BG_IMAGE_DISPLAY: 'block',
                TOP_BADGE_DISPLAY: 'inline-block',
                MUST_WATCH_DISPLAY: 'block',
                HEADSHOT_DISPLAY: 'block',
                LOGO_DISPLAY: 'block',
                BG_IMAGE_PATH: path.join(ROOT, 'modules/thumbnails/assets/bgs/quicksort_bg.png'),
                HEADSHOT_PATH: path.join(ROOT, 'modules/thumbnails/assets/headshots/azam_smiling.png'),
                LOGO_PATH: path.join(ROOT, 'modules/thumbnails/assets/axiom_logo.png'),
            }
        });
        console.log(`   ✅ Thumbnail: ${thumbnailPath}`);
    } catch (thumbErr) {
        console.warn(`   ⚠️  Thumbnail generation failed: ${thumbErr.message} — skipping`);
        thumbnailPath = null;
    }

    // ══════════════════════════════════════════════════════════════════════
    // STEP 6: SEO Metadata
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n--- STEP 6: SEO Optimization ---');
    const seo = generateSEOMetadata(TOPIC, SUBJECT, CHAPTER);
    console.log(`   Title: ${seo.title}`);
    console.log(`   Tags: ${seo.tags.slice(0, 8).join(', ')}...`);
    console.log(`\n   Full Description:\n${seo.description.substring(0, 300)}...\n`);

    // Save SEO data for later use
    const seoPath = path.join(topicDataDir, 'seo_metadata.json');
    fs.writeFileSync(seoPath, JSON.stringify(seo, null, 2), 'utf8');
    console.log(`   ✅ SEO metadata saved: ${seoPath}`);

    // ══════════════════════════════════════════════════════════════════════
    // STEP 7: Update Handoff JSON
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n--- STEP 7: Update Handoff ---');
    const handoffPath = path.join(OUTPUT, 'notebooklm_handoff.json');
    const handoff = {
        local_audio: videoPath,
        topic: TOPIC,
        subject: SUBJECT,
        chapter: CHAPTER,
        strategy: 'single',
        timestamp: new Date().toISOString()
    };
    fs.writeFileSync(handoffPath, JSON.stringify(handoff, null, 2), 'utf8');
    console.log('   ✅ Handoff updated');

    // ══════════════════════════════════════════════════════════════════════
    // DONE
    // ══════════════════════════════════════════════════════════════════════
    console.log('\n╔══════════════════════════════════════════════════════╗');
    console.log('║  🎉 PIPELINE COMPLETE — LOCAL RENDER ONLY           ║');
    console.log('╠══════════════════════════════════════════════════════╣');
    console.log(`║  Final Video:  ${finalVideoPath}`);
    if (thumbnailPath) console.log(`║  Thumbnail:    ${thumbnailPath}`);
    console.log(`║  SEO Title:    ${seo.title}`);
    console.log(`║  SEO Data:     ${seoPath}`);
    console.log('╚══════════════════════════════════════════════════════╝\n');
}

main().catch(err => {
    console.error('\n❌ Pipeline failed:', err.message);
    console.error(err.stack);
    process.exit(1);
});
