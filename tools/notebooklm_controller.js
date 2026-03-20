/**
 * notebooklm_controller.js
 * Full browser automation for NotebookLM:
 *  1. Opens notebooklm.google.com with your Chrome Profile 4 session
 *  2. Creates a new notebook
 *  3. Adds a structured Topic Brief as a TEXT source (NO YouTube URLs)
 *  4. Triggers "Generate Audio Overview"
 *  5. Waits for generation to complete
 *  6. Downloads the audio/video to d:\notebook lm\output\notebooklm_raw\
 */

const puppeteer = require('puppeteer');
const fs   = require('fs');
const path = require('path');
const { getPage } = require('./chrome_bridge');

const CHROME_USER_DATA  = 'C:\\Users\\AZAM RIZWAN\\AppData\\Local\\Google\\Chrome\\User Data';
const CHROME_PROFILE    = 'Profile 4';
const NOTEBOOKLM_URL    = 'https://notebooklm.google.com';
const DOWNLOAD_DIR      = 'D:\\notebook lm\\output\\notebooklm_raw';
const MAX_GEN_WAIT_MS   = 15 * 60 * 1000;  // 15 minutes for generation
const POLL_MS           = 10000;

/**
 * Build a rich Topic Brief from topic data — this is what we paste into
 * NotebookLM instead of a YouTube URL.
 */
function buildTopicBrief({ topic, subject, chapter, strategy, branches, researchNotes }) {
    const branchSection = branches && branches.length > 0
        ? `\n## Video Series Plan\n${branches.map((b, i) => `${i + 1}. ${b}`).join('\n')}\n\nFOR THIS VIDEO: Focus ONLY on "${branches[0]}"`
        : '';

    return `# Deep Research Brief: ${topic}
Subject: ${subject}
Chapter: ${chapter}
Video Strategy: ${strategy === 'branch' ? 'SERIES (Part 1 of ' + (branches?.length || 'N') + ')' : 'SINGLE VIDEO'}
${branchSection}

## Topic Overview
${topic} is a key concept in ${subject}, specifically within the ${chapter} chapter.
Provide a comprehensive, exam-focused explanation covering:
1. Core definition and intuition
2. Step-by-step breakdown with worked examples
3. Common misconceptions and how to avoid them
4. Real-world applications and analogies
5. Key formulas, diagrams, or pseudocode (as applicable)
6. Practice questions (2–3 examples with solutions)

## Target Audience
Engineering / BTech students preparing for semester exams and interviews.
Level: Intermediate. Tone: Clear, engaging, slightly conversational.

## Research Notes
${researchNotes || 'Conduct deep research from first principles. Use authoritative academic sources.'}

## Output Format
Generate a video script with:
- A punchy intro hook (15 seconds)
- Concept explanation with examples
- A "Key Takeaways" summary
- A call-to-action outro
`.trim();
}

async function runNotebookLM({ topic, subject, chapter, strategy, branches, researchNotes }) {
    console.log('🚀 [VERSION 2.1] - Resilient NotebookLM Controller Active');
    const topicBrief = buildTopicBrief({ topic, subject, chapter, strategy, branches, researchNotes });

    // Ensure download directory exists
    if (!fs.existsSync(DOWNLOAD_DIR)) {
        fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });
    }

    console.log(`\n📓 NotebookLM Controller — Topic: ${topic}`);

    const { page, browser } = await getPage();



    // Helper: Find button by text (Self-healing)
    const findAndClickBtn = async (page, searchText, timeout = 25000) => {
        console.log(`🔍 Searching for button: "${searchText}"...`);
        try {
            await page.waitForFunction((text) => {
                const elements = Array.from(document.querySelectorAll('button, div[role="button"], span, div[role="menuitem"], .mat-icon-button, [aria-label*="arrow"]'));
                const target = elements.find(el => {
                    const content = (el.innerText || el.getAttribute('aria-label') || '').trim();
                    if (content.length > 0 && content.length < 50) { 
                        // Intentionally log matched content for debug when text is short
                    }
                    return content.toLowerCase().includes(text.toLowerCase()) || 
                           (text === '→' && el.innerHTML.includes('arrow_forward'));
                });
                if (target) { 
                    target.scrollIntoView();
                    target.click(); 
                    return true; 
                }
                return false;
            }, { timeout }, searchText);
            console.log(`✅ Clicked "${searchText}"`);
        } catch (e) {
            console.warn(`⚠️  Could not find/click "${searchText}": ${e.message}`);
            return false;
        }
        return true;
    };

    const fastFind = (txt) => findAndClickBtn(page, txt, 5000);

    // ── Step 1: Ensure we are INSIDE a notebook ─────────────────────────────
    console.log('🔍 Checking if we are on the Home screen or inside a notebook...');
    try {
        const createBtn = await fastFind('Create notebook');
        if (createBtn) {
            console.log('🏠 Found Home screen — Clicking "+ Create notebook" to start fresh!');
            // After clicking "Create", the page will navigate to a new notebook URL
            await new Promise(r => setTimeout(r, 5000)); // Navigation buffer
        }
    } catch (_) {
        console.log('ℹ️  Already inside a notebook or create button not found.');
    }

    // ── Step 2: Add research brief / Import existing ────────────────────────
    console.log('📄 Checking for research results to Import...');
    try {
        const importBtn = await fastFind('Import');
        if (importBtn) {
            console.log('✅ Found "Import" — Unlocking the notebook...');
            await new Promise(r => setTimeout(r, 5000)); // Wait for unlock
        }
    } catch (_) {}

    console.log('📄 Adding Topic Brief as text source (if needed)...');
    
    try {
        // 0. Handle "Fast Research" popup first
        const importedResult = await fastFind('Import');
        if (importedResult) {
            console.log('✅ Fast Research result imported first');
            await new Promise(r => setTimeout(r, 1000));
        }

        // 1. Add Source
        const openedMenu = await fastFind('Add source');
        if (openedMenu) {
            await fastFind('Text');
            const textArea = await page.waitForSelector('textarea, .source-text-input, [contenteditable="true"]', { timeout: 5000 });
            await textArea.click();
            await page.evaluate((text) => {
                const ta = document.querySelector('textarea, .source-text-input, [contenteditable="true"]');
                if (ta) {
                    if (ta.tagName === 'DIV') { ta.innerText = text; }
                    else { ta.value = text; }
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }, topicBrief);

            // Priority 1: The Blue Arrow Arrow from your screenshot
            try {
                const clickedArrow = await fastFind('→');
                if (clickedArrow) {
                    console.log('✅ Blue Arrow clicked — waiting for guide to open...');
                    await new Promise(r => setTimeout(r, 3000));
                }
            } catch (_) {}
            
            // Handle the new "+ Import" popup if it appears
            try { await fastFind('Import'); } catch (_) {}
        }
    } catch (err) {
        console.log('ℹ️  Research sources already present. Skipping add step.');
    }

    // ── Step 4: Trigger High-Level Generation ─────────────────────────────────
    console.log('🎬 Attempting to trigger Video Overview...');
    try {
        await fastFind('Notebook guide');
        await fastFind('Generate');
    } catch (_) {}
    
    // Priority: Video Overview (New Google Feature)
    const triggeredVideo = await fastFind('Video Overview');
    if (triggeredVideo) {
        console.log('📝 Handling Video Customization popup...');
        const customPrompt = `Create an excited, high-energy educational video overview for "${topic}". 
The content MUST be top-tier: professional, engaging, and exam-focused. 
Cover the core intuition, worked examples, and common interview questions. 
Ensure the tone is enthusiastic and keeps the audience hooked!`;

        try {
            // Target ONLY the prompt box inside the popup/modal
            const promptBox = await page.waitForSelector('.mat-mdc-dialog-container textarea, .mat-dialog-container textarea, role["dialog"] textarea, .customization-prompt-field', { timeout: 8000 })
                .catch(() => page.waitForSelector('textarea[placeholder*="customize"], textarea[aria-label*="custom"]', { timeout: 5000 }));
            
            await promptBox.click();
            await page.evaluate((el, text) => {
                if (el.tagName === 'DIV' || el.getAttribute('contenteditable')) { el.innerText = text; }
                else { el.value = text; }
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }, promptBox, customPrompt);
            
            // Click the Blue "Generate" specifically inside that popup
            await page.evaluate(() => {
                const modal = document.querySelector('.mat-mdc-dialog-container, .mat-dialog-container, [role="dialog"]');
                if (modal) {
                    const btns = Array.from(modal.querySelectorAll('button'));
                    const genBtn = btns.find(b => b.innerText.includes('Generate'));
                    if (genBtn) genBtn.click();
                }
            });
            console.log('✅ Final Video Customization submitted!');
        } catch (e) {
            console.log('ℹ️  Customization box not found (falling back to generic click)...');
            await fastFind('Generate');
        }
    } else {
        console.log('ℹ️  Video Overview not found, falling back to Audio Overview...');
        await fastFind('Audio Overview');
    }
    
    console.log('⏳ Generation started. Polling for download...');

    // ── Step 5: Poll for Download Button (Resilient) ───────────────────────
    const startTime = Date.now();
    let downloaded = false;

    while (Date.now() - startTime < 1800000) { // 30 Minute Timeout
        await new Promise(r => setTimeout(r, 5000));
        const elapsed = Math.round((Date.now() - startTime) / 1000);

        // Vision Snapshot
        try {
            await page.screenshot({ path: 'd:/notebook lm/output/snapshots/live_vision.png' });
        } catch (_) {}

        try {
            const clicked = await fastFind('Download', 5000);
            if (clicked) {
                console.log('✅ Download clicked!');
                await new Promise(r => setTimeout(r, 10000)); // Buffer
                
                // Final file scan
                const safeTopic = topic.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
                const files = fs.readdirSync(DOWNLOAD_DIR).filter(f => !f.endsWith('.crdownload'));
                const newest = files.sort((a,b) => fs.statSync(path.join(DOWNLOAD_DIR,b)).mtimeMs - fs.statSync(path.join(DOWNLOAD_DIR,a)).mtimeMs)[0];
                
                if (newest) {
                    const ext = path.extname(newest);
                    const renamed = path.join(DOWNLOAD_DIR, `notebooklm_${safeTopic}${ext}`);
                    fs.renameSync(path.join(DOWNLOAD_DIR, newest), renamed);
                    console.log(`\n🎉 SUCCESS! Video Saved: ${renamed}`);
                    downloaded = true;
                    break;
                }
            }
            if (elapsed % 30 < 6) {
                console.log(`   ⏱ Polling... (${elapsed}s elapsed) — Check snapshots/live_vision.png`);
            }
        } catch (err) {
            // Silence noise
        }
    }
    
    await browser.disconnect();
    return downloaded;
}

// CLI usage
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 3) {
        console.log('Usage: node notebooklm_controller.js <topic> <subject> <chapter>');
        console.log('Example: node notebooklm_controller.js "QuickSort" "DSA" "Sorting"');
        process.exit(1);
    }
    runNotebookLM({ topic: args[0], subject: args[1], chapter: args[2], strategy: 'single' }).catch(console.error);
}

module.exports = { runNotebookLM, buildTopicBrief };
