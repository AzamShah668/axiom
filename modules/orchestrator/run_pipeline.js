/**
 * run_pipeline.js  v3
 * Master Orchestration Script — 3-Track Sync Pipeline.
 *
 * What's new in v3:
 *  • Whisper extracts transcript from NotebookLM video (video is source of truth)
 *  • FFmpeg scene detection finds slide changes
 *  • Per-slide sync: each slide stretched/compressed to match TTS pacing
 *  • Dynamic intro/outro videos generated via FFmpeg (duration-matched to TTS)
 *  • Gemini AI adds emotion markers for natural TTS
 *  • 3-track assembly: [Intro] | [Main synced] | [Outro]
 *
 * Run:
 *   node modules/orchestrator/run_pipeline.js [BTech|MBBS]
 *   node modules/orchestrator/run_pipeline.js --topic "QuickSort" --subject "DSA" --chapter "Sorting"
 */

require('dotenv').config({ path: `${__dirname}/../../config/.env` });

const fs   = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// ── Module imports ────────────────────────────────────────────────────────────
const { analyseTopicStrategy }       = require('../../tools/topic_strategy');
const { runNotebookLM }              = require('../../tools/notebooklm_controller');
const { launchColabAndGetGradioUrl } = require('../../tools/colab_launcher');
const { processVideo }               = require('../../video/post_processor');
const { generateSEOMetadata }        = require('../../scripts/seo_generator');
const { enhanceTranscript }          = require('../../scripts/transcript_enhancer');
const { enhanceWithEmotions }        = require('../../scripts/emotion_enhancer');
const { segmentTTSAudio }           = require('../../scripts/tts_segmenter');
const { generateIntroVideo, generateOutroVideo } = require('../../video/intro_generator');

// Lazy-load uploader (may not exist yet)
let uploadToYouTube = null;
try { uploadToYouTube = require('../uploader/youtube_uploader').uploadToYouTube; } catch (_) {}

const PYTHON_EXE = 'C:\\Users\\AZAM RIZWAN\\qwen-tts-gpu\\Scripts\\python.exe';

const ROOT      = path.join(__dirname, '../..');
const DATA_DIR  = path.join(ROOT, 'data');
const OUTPUT    = path.join(ROOT, 'output');

// ── Notion helpers ────────────────────────────────────────────────────────────

const NOTION_API_KEY = process.env.NOTION_API_KEY;
const API_BASE       = 'https://api.notion.com/v1';
const N_HEADERS      = {
    'Authorization':  `Bearer ${NOTION_API_KEY}`,
    'Content-Type':   'application/json',
    'Notion-Version': '2022-06-28'
};

async function nFetch(url, options = {}, retries = 3) {
    for (let i = 0; i < retries; i++) {
        const res = await fetch(url, options);
        if (res.status === 429) { await new Promise(r => setTimeout(r, 2000)); continue; }
        return res.json();
    }
    return null;
}

async function getNextPendingTopic(dbId) {
    console.log('\n📡 Fetching next Pending topic from Notion...');
    const data = await nFetch(`${API_BASE}/databases/${dbId}/query`, {
        method: 'POST', headers: N_HEADERS,
        body: JSON.stringify({ filter: { property: 'Status', select: { equals: 'Pending' } }, page_size: 1 })
    });
    if (!data?.results?.length) { console.log('No pending topics.'); return null; }

    const page     = data.results[0];
    const topic    = page.properties.Topic.title[0]?.plain_text    || 'Unknown Topic';
    const subject  = page.properties.Subject?.select?.name         || 'Unknown Subject';
    const chapter  = page.properties.Chapter?.select?.name         || 'Unknown Chapter';

    // Mark as In Progress immediately
    await nFetch(`${API_BASE}/pages/${page.id}`, {
        method: 'PATCH', headers: N_HEADERS,
        body: JSON.stringify({ properties: { Status: { select: { name: 'In Progress' } } } })
    });
    console.log(`📌 Topic: [${subject}] ${chapter} → ${topic}`);
    return { id: page.id, topic, subject, chapter, dbId };
}

async function markComplete(pageId, videoUrl) {
    await nFetch(`${API_BASE}/pages/${pageId}`, {
        method: 'PATCH', headers: N_HEADERS,
        body: JSON.stringify({ properties: {
            Status:       { select: { name: 'Completed' } },
            'Video URL':  { url: videoUrl },
            'Created Date': { date: { start: new Date().toISOString() } }
        }})
    });
}
async function markFailed(pageId) {
    await nFetch(`${API_BASE}/pages/${pageId}`, {
        method: 'PATCH', headers: N_HEADERS,
        body: JSON.stringify({ properties: { Status: { select: { name: 'Failed' } } } })
    });
}

// ── Colab health check ────────────────────────────────────────────────────────

async function ensureColabIsRunning() {
    console.log('\n--- STEP: Colab TTS Server ---');
    const colabUrlFile = path.join(ROOT, 'video/colab_url.json');

    let isAlive = false;

    if (fs.existsSync(colabUrlFile)) {
        const saved    = JSON.parse(fs.readFileSync(colabUrlFile, 'utf8'));
        const gradioUrl = saved.gradio_url || saved.url;
        const updatedAt = new Date(saved.updated_at || saved.updated);
        const ageMinutes = (Date.now() - updatedAt.getTime()) / 60000;

        if (gradioUrl && ageMinutes < 60) {
            // Quick ping to see if it's still alive
            try {
                const res = await fetch(gradioUrl, { signal: AbortSignal.timeout(5000) });
                if (res.ok) {
                    console.log(`✅ Colab alive (${Math.round(ageMinutes)}min old): ${gradioUrl}`);
                    isAlive = true;
                }
            } catch (_) {}
        }
    }

    if (!isAlive) {
        console.log('🔄 Colab is not running — launching now...');
        await launchColabAndGetGradioUrl();
    }
}

// ── Helper: Run Python script ─────────────────────────────────────────────────

function runPython(scriptPath, args = []) {
    const pyExe = PYTHON_EXE.replace(/\\/g, '/');
    const script = scriptPath.replace(/\\/g, '/');
    const quotedArgs = args.map(a => `"${a.replace(/\\/g, '/')}"`).join(' ');
    const cmd = `"${pyExe}" "${script}" ${quotedArgs}`;
    console.log(`   $ python ${path.basename(script)} ...`);
    execSync(cmd, { stdio: 'inherit', maxBuffer: 1024 * 1024 * 50, timeout: 10 * 60 * 1000 });
}

// ── Main Pipeline ─────────────────────────────────────────────────────────────

async function runFullPipeline({ topic, subject, chapter, notionPageId, notionDbId }) {
    console.log('\n╔══════════════════════════════════════════╗');
    console.log('║  🚀 EDU-CONTENT PIPELINE v3 (3-Track)    ║');
    console.log('╚══════════════════════════════════════════╝');
    console.log(`   Topic:   ${topic}`);
    console.log(`   Subject: ${subject}`);
    console.log(`   Chapter: ${chapter}\n`);

    // Create per-topic data directory for intermediate files
    const safeName = topic.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
    const topicDataDir = path.join(DATA_DIR, safeName);
    const videosDir = path.join(OUTPUT, 'videos');
    fs.mkdirSync(topicDataDir, { recursive: true });
    fs.mkdirSync(videosDir, { recursive: true });

    try {
        // ══════════════════════════════════════════════════════════════════════
        // STEP 1: Strategy Analysis (YouTube Trend Analysis)
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 1: Topic Strategy ---');
        const strategy = await analyseTopicStrategy(topic, subject, chapter, notionDbId, notionPageId);
        const focusTopic = strategy.focusTopic;
        console.log(`   Strategy: ${strategy.strategy.toUpperCase()} | Focus: "${focusTopic}"`);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 2: Ensure Colab TTS is running
        // ══════════════════════════════════════════════════════════════════════
        await ensureColabIsRunning();

        // ══════════════════════════════════════════════════════════════════════
        // STEP 3 (4A): NotebookLM — Generate VIDEO + Download
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 3: NotebookLM (Generate + Download Video) ---');
        let downloaded = false;
        for (let attempt = 1; attempt <= 2; attempt++) {
            console.log(`   Attempt ${attempt}/2...`);
            downloaded = await runNotebookLM({
                topic: focusTopic, subject, chapter,
                strategy: strategy.strategy,
                branches: strategy.branches,
                researchNotes: strategy.contextPrompt
            });
            if (downloaded) break;
            if (attempt < 2) {
                console.log('   NotebookLM attempt failed. Retrying in 10s...');
                await new Promise(r => setTimeout(r, 10000));
            }
        }
        if (!downloaded) {
            throw new Error('NotebookLM download failed after 2 attempts');
        }

        const handoffPath = path.join(OUTPUT, 'notebooklm_handoff.json');
        if (!fs.existsSync(handoffPath)) {
            throw new Error('notebooklm_handoff.json not found');
        }
        const handoff = JSON.parse(fs.readFileSync(handoffPath, 'utf8'));
        const videoPath = handoff.local_audio;  // Despite the name, this is the video MP4
        console.log(`   NotebookLM video: ${videoPath}`);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4B + 4C: Whisper Transcript + Scene Detection (parallel)
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4B: Whisper Transcript Extraction ---');
        const whisperScript = path.join(ROOT, 'scripts', 'whisper_extract.py');
        runPython(whisperScript, [videoPath, topicDataDir, 'base']);

        console.log('\n--- STEP 4C: Scene Detection (Slide Changes) ---');
        const sceneScript = path.join(ROOT, 'scripts', 'scene_detector.py');
        runPython(sceneScript, [videoPath, topicDataDir, '0.3']);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4D: Map Slides to Words
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4D: Slide-to-Word Mapping ---');
        const transcriptJson = path.join(topicDataDir, 'original_transcript.json');
        const scenesJson = path.join(topicDataDir, 'scene_changes.json');
        const mapperScript = path.join(ROOT, 'scripts', 'slide_word_mapper.py');
        runPython(mapperScript, [transcriptJson, scenesJson, topicDataDir]);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4E: Generate Intro/Outro Scripts
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4E: Generate Intro/Outro Scripts ---');
        const originalText = fs.readFileSync(path.join(topicDataDir, 'original_transcript.txt'), 'utf8');
        const enhanced = enhanceTranscript(originalText, focusTopic, subject);

        // Save for downstream steps
        const enhancedJsonPath = path.join(topicDataDir, 'enhanced_transcript.json');
        fs.writeFileSync(enhancedJsonPath, JSON.stringify(enhanced, null, 2), 'utf8');
        fs.writeFileSync(path.join(topicDataDir, 'enhanced_transcript.txt'), enhanced.fullScript, 'utf8');

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4F: Emotion Enhancement (Gemini AI)
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4F: Emotion Enhancement (Gemini AI) ---');
        const emotionalScript = await enhanceWithEmotions(enhanced.fullScript);
        const emotionalScriptPath = path.join(topicDataDir, 'emotional_transcript.txt');
        fs.writeFileSync(emotionalScriptPath, emotionalScript, 'utf8');

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4G: TTS Generation + Whisper Timestamps
        // Uses Python-native script (tts_full_generate.py) to avoid Node exec() failures.
        // 45-min timeout: ~7 chunks × 3-5 min each on Colab T4 GPU.
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4G: TTS Voice Clone (Qwen3) ---');
        const fullTtsWav = path.join(topicDataDir, 'full_tts.wav');
        const fullTtsTimestamps = path.join(topicDataDir, 'full_tts_timestamps.json');
        {
            const colabData = JSON.parse(fs.readFileSync(path.join(ROOT, 'video/colab_url.json'), 'utf8'));
            const gradioUrl = colabData.gradio_url;
            const ttsScript = path.join(ROOT, 'scripts', 'tts_full_generate.py');
            const pyExe = PYTHON_EXE.replace(/\\/g, '/');
            const cmd = `"${pyExe}" "${ttsScript.replace(/\\/g, '/')}" `
                + `"${emotionalScriptPath.replace(/\\/g, '/')}" `
                + `"${fullTtsWav.replace(/\\/g, '/')}" `
                + `"${fullTtsTimestamps.replace(/\\/g, '/')}" `
                + `"${gradioUrl}"`;
            console.log(`   $ python tts_full_generate.py ...`);
            execSync(cmd, { stdio: 'inherit', maxBuffer: 1024 * 1024 * 50, timeout: 45 * 60 * 1000 });
        }

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4H: Segment TTS Audio (Intro / Main / Outro)
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4H: TTS Audio Segmentation ---');
        const segments = segmentTTSAudio(fullTtsWav, fullTtsTimestamps, enhancedJsonPath, topicDataDir);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4I: Per-Slide Video Sync (Main Track)
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4I: Per-Slide Video Sync (Engine 2 v2) ---');
        // Run Whisper on the main audio segment to get word timestamps for alignment
        const mainTtsTimestamps = path.join(topicDataDir, 'main_tts_timestamps.json');
        const whisperMainScript = path.join(ROOT, 'scripts', 'engine_1_transcribe.py');
        runPython(whisperMainScript, [segments.mainAudio, mainTtsTimestamps, 'base']);

        const slideMapJson = path.join(topicDataDir, 'slide_map.json');
        const syncedMainVideo = path.join(videosDir, `${safeName}_synced_main.mp4`);
        const engine2Script = path.join(ROOT, 'scripts', 'engine_2_sync.py');
        runPython(engine2Script, [videoPath, segments.mainAudio, slideMapJson, mainTtsTimestamps, syncedMainVideo]);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4J: Generate Intro/Outro Videos (parallel with 4I conceptually)
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4J: Generate Dynamic Intro/Outro Videos ---');
        const introVideoPath = path.join(videosDir, `${safeName}_intro.mp4`);
        const outroVideoPath = path.join(videosDir, `${safeName}_outro.mp4`);

        generateIntroVideo({
            introAudioPath: segments.introAudio,
            outputPath: introVideoPath,
            topic: focusTopic, subject, chapter
        });

        generateOutroVideo({
            outroAudioPath: segments.outroAudio,
            outputPath: outroVideoPath,
            topic: focusTopic
        });

        // ══════════════════════════════════════════════════════════════════════
        // STEP 4K: 3-Track Assembly (Post-Processing)
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 4K: 3-Track Assembly (Final Post-Processing) ---');
        const finalVideoPath = await processVideo({
            introVideo: introVideoPath,
            introAudio: segments.introAudio,
            mainVideo: syncedMainVideo,
            outroVideo: outroVideoPath,
            outroAudio: segments.outroAudio,
            outputPath: path.join(videosDir, `${safeName}_final.mp4`)
        });
        console.log(`   Final video: ${finalVideoPath}`);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 5: Thumbnail
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 5: Thumbnail Generation ---');
        let thumbnailPath = path.join(OUTPUT, `thumbnail_${safeName.toUpperCase()}.png`);
        try {
            const { renderThumbnail } = require('../../modules/thumbnails/scripts/render_thumbnail');
            await renderThumbnail({
                templatePath: path.join(ROOT, 'tools/thumbnail_generator.html'),
                outputPath: thumbnailPath,
                params: {
                    TOP_BADGE: subject,
                    MAIN_TITLE: focusTopic.toUpperCase().replace(' ', '<br>'),
                    SUBTITLE: chapter,
                    SUB_LINE: strategy.contextPrompt.slice(0, 60),
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
            console.log(`   Thumbnail: ${thumbnailPath}`);
        } catch (thumbErr) {
            console.warn(`   Thumbnail generation failed: ${thumbErr.message} — skipping`);
            thumbnailPath = null;
        }

        // ══════════════════════════════════════════════════════════════════════
        // STEP 6: SEO Metadata
        // ══════════════════════════════════════════════════════════════════════
        console.log('\n--- STEP 6: SEO Optimization ---');
        const seo = generateSEOMetadata(focusTopic, subject, chapter);
        console.log(`   Title: ${seo.title}`);
        console.log(`   Tags: ${seo.tags.slice(0, 5).join(', ')}...`);

        // ══════════════════════════════════════════════════════════════════════
        // STEP 7: YouTube Upload
        // ══════════════════════════════════════════════════════════════════════
        if (uploadToYouTube) {
            console.log('\n--- STEP 7: YouTube Upload ---');
            const uploadedUrl = await uploadToYouTube(finalVideoPath, {
                title: seo.title,
                description: seo.description,
                tags: seo.tags,
                subject, chapter, stream: 'BTech',
                thumbnailPath,
                privacyStatus: 'public',
            });
            console.log(`   Published: ${uploadedUrl}`);
            if (notionPageId) await markComplete(notionPageId, uploadedUrl);
            console.log('\n🎉 Pipeline Complete!');
            return uploadedUrl;
        } else {
            console.log('\n   Uploader not configured — skipping YouTube upload.');
            console.log(`   Final video: ${finalVideoPath}`);
            if (notionPageId) await markComplete(notionPageId, '(local only)');
        }

    } catch (err) {
        const msg = err.message || '';
        let category = 'UNKNOWN';
        if (msg.includes('Gradio') || msg.includes('Colab') || msg.includes('colab'))
            category = 'COLAB_DEAD';
        else if (msg.includes('NotebookLM') || msg.includes('notebooklm'))
            category = 'NOTEBOOKLM_TIMEOUT';
        else if (msg.includes('FFmpeg') || msg.includes('ffmpeg'))
            category = 'FFMPEG_FAIL';
        else if (msg.includes('TTS') || msg.includes('WAV') || msg.includes('tts'))
            category = 'TTS_FAIL';
        else if (msg.includes('Whisper') || msg.includes('whisper'))
            category = 'WHISPER_FAIL';
        else if (msg.includes('Notion') || msg.includes('429'))
            category = 'NOTION_API';
        else if (msg.includes('YouTube') || msg.includes('upload'))
            category = 'UPLOAD_FAIL';

        console.error(`\n   Pipeline Error [${category}]: ${msg}`);

        const logPath = path.join(ROOT, 'logs', 'pipeline_errors.log');
        try {
            fs.mkdirSync(path.dirname(logPath), { recursive: true });
            fs.appendFileSync(logPath,
                `[${new Date().toISOString()}] [${category}] ${topic || 'unknown'}: ${msg}\n`
            );
        } catch (_) {}

        if (notionPageId) await markFailed(notionPageId);
        throw err;
    }
}

// ── Entry Points ──────────────────────────────────────────────────────────────

async function startFromNotion(stream = 'BTech') {
    const configPath = path.join(ROOT, 'config/config.json');
    if (!fs.existsSync(configPath)) {
        console.error('config.json not found at project root');
        process.exit(1);
    }
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    const masterDbId = config.notion?.databases?.master_databases?.[stream];

    if (!masterDbId) {
        console.error(`No Master DB ID found for stream: ${stream}`);
        process.exit(1);
    }

    const target = await getNextPendingTopic(masterDbId);
    if (!target) { console.log('Nothing to process — all done!'); return; }

    await runFullPipeline({ ...target });
}

async function startFromArgs({ topic, subject, chapter }) {
    await runFullPipeline({ topic, subject, chapter, notionPageId: null, notionDbId: null });
}

// ── CLI ───────────────────────────────────────────────────────────────────────
if (require.main === module) {
    const args = process.argv.slice(2);

    if (args[0] === '--topic') {
        const topic   = args[1];
        const subject = args[3] || 'General';
        const chapter = args[5] || 'General';
        startFromArgs({ topic, subject, chapter }).catch(console.error);
    } else {
        const stream = args[0] || 'BTech';
        startFromNotion(stream).catch(console.error);
    }
}

module.exports = { runFullPipeline, startFromNotion, startFromArgs };
