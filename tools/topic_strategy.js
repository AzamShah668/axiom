/**
 * topic_strategy.js  (replaces the URL-extraction role of youtube_scraper.js)
 *
 * NEW ROLE: YouTube is queried ONLY to decide strategy, NOT to get URLs.
 *
 * Pipeline:
 *  1. Search YouTube for the topic
 *  2. Analyse top results to decide:
 *        strategy = 'single'  → one self-contained video
 *        strategy = 'branch'  → multi-part series (expand into sibling Notion rows)
 *  3. If 'branch', build the branch titles and create sibling Notion rows
 *  4. Return { strategy, branches, contextPrompt } — NO YouTube URLs
 *  5. The orchestrator passes this to notebooklm_controller.js as plain text
 */

require('dotenv').config({ path: '../.env' });
const { google }  = require('googleapis');
const fs          = require('fs');
const path        = require('path');

const config  = JSON.parse(fs.readFileSync(path.join(__dirname, '../config/config.json'), 'utf8'));
const youtube = google.youtube({
    version: 'v3',
    auth: config.youtube?.api_key || process.env.YOUTUBE_API_KEY || process.env.YOUTUBE_DATA_API_KEY
});

const NOTION_API_KEY = process.env.NOTION_API_KEY;
const API_BASE       = 'https://api.notion.com/v1';
const NOTION_HEADERS = {
    'Authorization': `Bearer ${NOTION_API_KEY}`,
    'Content-Type':  'application/json',
    'Notion-Version': '2022-06-28'
};

// ── Helpers ──────────────────────────────────────────────────────────────────

async function fetchWithRetry(url, options, retries = 3) {
    for (let i = 0; i < retries; i++) {
        const res = await fetch(url, options);
        if (res.status === 429) { await new Promise(r => setTimeout(r, 2000)); continue; }
        return await res.json();
    }
    return null;
}

/**
 * Complexity score: how "broad" is a topic?
 * Returns 'branch' if the YouTube landscape shows a clearly multi-part topic,
 * 'single' otherwise.
 */
function decideStrategy(items) {
    if (!items || items.length === 0) return { decision: 'single', reason: 'No results' };

    const topItem   = items[0];
    const topTitle  = topItem.snippet.title.toLowerCase();
    const topKind   = topItem.id.kind;

    // Explicit signals for BRANCH strategy
    if (topKind === 'youtube#playlist') {
        return { decision: 'branch', reason: 'Top result is a playlist', isPlaylist: true, playlistId: topItem.id.playlistId };
    }
    if (topTitle.includes('part 1') || topTitle.includes('ep 1') || topTitle.includes('episode 1')) {
        return { decision: 'branch', reason: 'Top result is Part 1 of a series' };
    }
    // Count how many of top 5 results mention "part" or series indicators
    const seriesCount = items.filter(i =>
        i.snippet.title.toLowerCase().match(/part \d|ep\.?\s*\d|episode|series|complete guide|full course/)
    ).length;
    if (seriesCount >= 3) {
        return { decision: 'branch', reason: `${seriesCount}/5 results suggest a multi-part topic` };
    }

    return { decision: 'single', reason: 'Topic is self-contained' };
}

/**
 * Build branch titles from a playlist's video titles, or generate generic part labels.
 */
function buildBranchTitles(topicName, source) {
    if (source && source.length > 0) return source.slice(0, 10); // Cap at 10 videos
    return [`${topicName} - Part 1`, `${topicName} - Part 2`, `${topicName} - Part 3`];
}

/**
 * Create sibling Notion rows for each branch.
 * The first branch renames the current page; remaining ones are new rows.
 */
async function createNotionBranches(notionDbId, originalPageId, subject, chapter, branches) {
    if (!branches || branches.length === 0) return;

    console.log(`\n✂️  Branching "${chapter}" into ${branches.length} videos in Notion...`);

    // Rename the current Notion page to the first branch title
    await fetchWithRetry(`${API_BASE}/pages/${originalPageId}`, {
        method: 'PATCH', headers: NOTION_HEADERS,
        body: JSON.stringify({ properties: { Topic: { title: [{ text: { content: branches[0] } }] } } })
    });
    console.log(`   ✅ Renamed active row → "${branches[0]}"`);

    // Create new Notion rows for remaining branches
    for (let i = 1; i < branches.length; i++) {
        const title = branches[i]?.trim() || `${chapter} - Lesson ${i + 1}`;
        await fetchWithRetry(`${API_BASE}/pages`, {
            method: 'POST', headers: NOTION_HEADERS,
            body: JSON.stringify({
                parent: { database_id: notionDbId },
                properties: {
                    Topic:   { title: [{ text: { content: title } }] },
                    Subject: { select: { name: subject } },
                    Chapter: { select: { name: chapter } },
                    Status:  { select: { name: 'Pending' } }
                }
            })
        });
        console.log(`   ➕ Created new row → "${title}"`);
    }
    console.log('');
}

// ── Main Export ───────────────────────────────────────────────────────────────

/**
 * analyseTopicStrategy()
 *
 * @param {string} topicName
 * @param {string} subjectName
 * @param {string} chapterName
 * @param {string} notionDbId      — Notion DB to create sibling rows in
 * @param {string} notionPageId    — The current Notion page being processed
 *
 * @returns {Promise<{
 *   strategy: 'single'|'branch',
 *   branches: string[],
 *   focusTopic: string,       — The specific topic THIS video should cover
 *   contextPrompt: string,    — Guardrail text for NotebookLM
 *   reason: string
 * }>}
 */
async function analyseTopicStrategy(topicName, subjectName, chapterName, notionDbId, notionPageId) {
    console.log(`\n🔍 Analysing topic strategy for: [${subjectName}] ${topicName}`);

    const query = `${subjectName} ${chapterName} ${topicName}`;

    let items = [];
    try {
        const res = await youtube.search.list({
            part: 'snippet',
            q: query,
            type: 'video,playlist',
            maxResults: 5,
            order: 'relevance'
        });
        items = res.data.items || [];
    } catch (err) {
        console.warn('⚠️  YouTube API error:', err.message);
    }

    // Log what YouTube returned (for transparency)
    console.log(`📊 YouTube trend signals (top ${items.length} results):`);
    items.forEach((item, i) => {
        const kind  = item.id.kind === 'youtube#playlist' ? '📋 Playlist' : '🎬 Video';
        console.log(`   ${i + 1}. ${kind}: ${item.snippet.title}`);
    });

    // Decide strategy
    const { decision, reason, isPlaylist, playlistId } = decideStrategy(items);
    console.log(`\n🧠 Strategy Decision: ${decision.toUpperCase()} — ${reason}`);

    let branches      = [];
    let focusTopic    = topicName;
    let contextPrompt = '';

    if (decision === 'branch') {
        // Get branch titles
        if (isPlaylist && playlistId) {
            try {
                const playlistRes = await youtube.playlistItems.list({
                    part: 'snippet,contentDetails',
                    playlistId,
                    maxResults: 10
                });
                const rawTitles = (playlistRes.data.items || []).map(i => i.snippet.title);
                branches = buildBranchTitles(topicName, rawTitles);
            } catch (_) {
                branches = buildBranchTitles(topicName, []);
            }
        } else {
            branches = buildBranchTitles(topicName, []);
        }

        focusTopic = branches[0];

        // Update Notion with sibling rows
        if (notionDbId && notionPageId) {
            await createNotionBranches(notionDbId, notionPageId, subjectName, chapterName, branches);
        }

        contextPrompt = `This video is Part 1 of a ${branches.length}-part series on "${topicName}".`
            + ` YOUR SOLE FOCUS is: "${focusTopic}". Do NOT discuss concepts from later parts.`;

    } else {
        // Single video
        contextPrompt = `Create a comprehensive, single-video deep dive on: "${topicName}" (${subjectName} — ${chapterName}).`;
    }

    const result = { strategy: decision, branches, focusTopic, contextPrompt, reason };

    // Save to temp file for orchestrator handoff
    const tempPath = path.join(__dirname, '../data/temp_strategy_result.json');
    fs.mkdirSync(path.dirname(tempPath), { recursive: true });
    fs.writeFileSync(tempPath, JSON.stringify(result, null, 2));

    console.log(`💾 Strategy saved → ${tempPath}`);
    console.log(`🎯 Focus Topic: "${focusTopic}"\n`);

    return result;
}

// ── CLI ───────────────────────────────────────────────────────────────────────
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 3) {
        console.log('Usage: node topic_strategy.js <Topic> <Subject> <Chapter> [NotionDbId] [NotionPageId]');
        console.log('Example: node topic_strategy.js "QuickSort" "DSA" "Sorting Algorithms"');
        process.exit(1);
    }
    analyseTopicStrategy(args[0], args[1], args[2], args[3], args[4]).catch(console.error);
}

module.exports = { analyseTopicStrategy };
