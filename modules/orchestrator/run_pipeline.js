/**
 * run_pipeline.js  v2
 * Master Orchestration Script — fully automated end-to-end.
 *
 * What's new in v2:
 *  • topic_strategy.js  → YouTube used for strategy only (NO URL passed to NotebookLM)
 *  • colab_launcher.js  → Auto-starts Qwen TTS Colab (no manual "Run All")
 *  • notebooklm_controller.js → Auto-creates notebook, generates + DOWNLOADS audio
 *
 * Run:
 *   node modules/orchestrator/run_pipeline.js [BTech|MBBS]
 *   node modules/orchestrator/run_pipeline.js --topic "QuickSort" --subject "DSA" --chapter "Sorting"
 *   node modules/orchestrator/run_pipeline.js --resume <NotionPageId> <Subject> <Chapter> <MP4Path> <TranscriptPath>
 */

require('dotenv').config({ path: `${__dirname}/../../.env` });

const fs   = require('fs');
const path = require('path');

// ── Module imports ────────────────────────────────────────────────────────────
const { analyseTopicStrategy }   = require('../../tools/topic_strategy');
const { runNotebookLM }          = require('../../tools/notebooklm_controller');
const { launchColabAndGetGradioUrl } = require('../../tools/colab_launcher');
const { processVideo }           = require('../../video/post_processor');
const { generateSEOMetadata }    = require('../../scripts/seo_generator');

// Lazy-load uploader (may not exist yet)
let uploadToYouTube = null;
try { uploadToYouTube = require('../uploader/youtube_uploader').uploadToYouTube; } catch (_) {}

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

// ── Main Pipeline ─────────────────────────────────────────────────────────────

async function runFullPipeline({ topic, subject, chapter, notionPageId, notionDbId }) {
    console.log('\n╔══════════════════════════════════╗');
    console.log('║  🚀 EDU-CONTENT PIPELINE v2      ║');
    console.log('╚══════════════════════════════════╝');
    console.log(`   Topic:   ${topic}`);
    console.log(`   Subject: ${subject}`);
    console.log(`   Chapter: ${chapter}\n`);

    try {
        // ── STEP 1: Strategy Analysis ─────────────────────────────────────────
        console.log('--- STEP 1: Topic Strategy (YouTube Trend Analysis) ---');
        const strategy = await analyseTopicStrategy(topic, subject, chapter, notionDbId, notionPageId);
        console.log(`✅ Strategy: ${strategy.strategy.toUpperCase()} | Focus: "${strategy.focusTopic}"`);

        // ── STEP 2: Ensure Colab TTS is running ───────────────────────────────
        await ensureColabIsRunning();

        // ── STEP 3: NotebookLM — Generate + Download ──────────────────────────
        console.log('\n--- STEP 3: NotebookLM (Generate + Auto-Download) ---');
        const downloaded = await runNotebookLM({
            topic:         strategy.focusTopic,
            subject,
            chapter,
            strategy:      strategy.strategy,
            branches:      strategy.branches,
            researchNotes: strategy.contextPrompt
        });

        if (!downloaded) {
            throw new Error('NotebookLM download failed — check browser for status');
        }

        // Read handoff file written by notebooklm_controller.js
        const handoffPath = path.join(OUTPUT, 'notebooklm_handoff.json');
        if (!fs.existsSync(handoffPath)) {
            throw new Error('notebooklm_handoff.json not found — download may have failed');
        }
        const handoff = JSON.parse(fs.readFileSync(handoffPath, 'utf8'));
        console.log(`\n✅ NotebookLM audio downloaded: ${handoff.local_audio}`);

        // ── STEP 4: Post-Processing (FFmpeg branding pipeline) ─────────────────
        console.log('\n--- STEP 4: Post-Processing (FFmpeg Branding Pipeline) ---');
        // processVideo takes the synced/raw video and applies:
        //   intro → fade → main (watermark-cropped) → fade → outro → overlays
        const finalVideoPath = await processVideo(handoff.local_audio);
        console.log(`✅ Final video: ${finalVideoPath}`);

        // ── STEP 5: Thumbnail ─────────────────────────────────────────────────
        console.log('\n--- STEP 5: Thumbnail Generation ---');
        const { renderThumbnail } = require('../../modules/thumbnails/scripts/render_thumbnail');
        const safeTopicName = strategy.focusTopic.replace(/[^a-zA-Z0-9]/g, '_').toUpperCase();
        const thumbnailPath = path.join(OUTPUT, `thumbnail_${safeTopicName}.png`);

        await renderThumbnail({
            templatePath: path.join(ROOT, 'tools/thumbnail_generator.html'),
            outputPath:   thumbnailPath,
            params: {
                TOP_BADGE:         subject,
                MAIN_TITLE:        strategy.focusTopic.toUpperCase().replace(' ', '<br>'),
                SUBTITLE:          chapter,
                SUB_LINE:          strategy.contextPrompt.slice(0, 60),
                MUST_WATCH_TEXT:   'MUST WATCH',
                BG_IMAGE_DISPLAY:  'block',
                TOP_BADGE_DISPLAY: 'inline-block',
                MUST_WATCH_DISPLAY:'block',
                HEADSHOT_DISPLAY:  'block',
                LOGO_DISPLAY:      'block',
                BG_IMAGE_PATH:     path.join(ROOT, 'modules/thumbnails/assets/bgs/quicksort_bg.png'),
                HEADSHOT_PATH:     path.join(ROOT, 'modules/thumbnails/assets/headshots/azam_smiling.png'),
                LOGO_PATH:         path.join(ROOT, 'modules/thumbnails/assets/axiom_logo.png'),
            }
        });
        console.log(`✅ Thumbnail: ${thumbnailPath}`);

        // ── STEP 6: Generate Viral SEO Metadata ──────────────────────────────
        console.log('\n--- STEP 6: SEO Optimization (Viral Title/Desc/Tags) ---');
        const seo = generateSEOMetadata(strategy.focusTopic, subject, chapter);
        console.log(`🔥 Title: ${seo.title}`);
        console.log(`📋 Tags: ${seo.tags.slice(0, 5).join(', ')}... (${seo.tags.length} total)`);

        // ── STEP 7: Upload to YouTube ─────────────────────────────────────────
        if (uploadToYouTube) {
            console.log('\n--- STEP 7: YouTube Upload ---');
            const uploadedUrl = await uploadToYouTube(finalVideoPath, {
                title:         seo.title,
                description:   seo.description,
                tags:          seo.tags,
                subject,
                chapter,
                stream:        'BTech',
                thumbnailPath,
                privacyStatus: 'public',
            });
            console.log(`✅ Published: ${uploadedUrl}`);

            if (notionPageId) await markComplete(notionPageId, uploadedUrl);
            console.log('\n🎉 Pipeline Complete!');
            return uploadedUrl;
        } else {
            console.log('\n⚠️  Uploader not configured — skipping YouTube upload step.');
            console.log(`   Final video ready at: ${finalVideoPath}`);
            console.log(`   Thumbnail ready at:   ${thumbnailPath}`);
            if (notionPageId) await markComplete(notionPageId, '(local only)');
        }

    } catch (err) {
        console.error(`\n❌ Pipeline Error: ${err.message}`);
        if (notionPageId) await markFailed(notionPageId);
        throw err;
    }
}

// ── Entry Points ──────────────────────────────────────────────────────────────

async function startFromNotion(stream = 'BTech') {
    const configPath = path.join(ROOT, 'config/config.json');
    if (!fs.existsSync(configPath)) {
        console.error('❌ config.json not found at project root');
        process.exit(1);
    }
    const config   = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    const masterDbId = config.notion?.databases?.master_databases?.[stream];

    if (!masterDbId) {
        console.error(`❌ No Master DB ID found for stream: ${stream}`);
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

    if (args[0] === '--resume') {
        // Legacy resume mode — for manually downloaded NoteookLM files
        const [, pageId, topic, subject, chapter, videoPath, transcriptPath] = args;
        if (!videoPath) {
            console.log('Usage: node run_pipeline.js --resume <pageId> <topic> <subject> <chapter> <videoPath> <transcriptPath>');
            process.exit(1);
        }
        const { processVideo } = require('../../video/post_processor');
        processVideo(videoPath, fs.readFileSync(transcriptPath, 'utf8'), topic, subject)
            .then(fp => { console.log('Done:', fp); })
            .catch(console.error);

    } else if (args[0] === '--topic') {
        // Direct topic mode (bypass Notion)
        const topic   = args[1];
        const subject = args[3] || 'General';
        const chapter = args[5] || 'General';
        startFromArgs({ topic, subject, chapter }).catch(console.error);

    } else {
        // Notion mode (default)
        const stream = args[0] || 'BTech';
        startFromNotion(stream).catch(console.error);
    }
}

module.exports = { runFullPipeline, startFromNotion, startFromArgs };
