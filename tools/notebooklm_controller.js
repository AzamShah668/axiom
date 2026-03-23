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

const fs   = require('fs');
const path = require('path');
const { getPage } = require('./chrome_bridge');

const DOWNLOAD_DIR      = 'D:\\notebook lm\\output\\notebooklm_raw';

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



    // Helper: Find button by text (Self-healing + Shadow DOM Piercing)
    const findAndClickBtn = async (page, searchText, timeout = 25000, silent = false) => {
        if (!silent) console.log(`🔍 Searching for button: "${searchText}"...`);
        try {
            const result = await page.waitForFunction((text) => {
                const queryShadow = (root, selector) => {
                    let found = null;
                    const walk = (node) => {
                        if (found) return;
                        if (node.nodeType === 1 && node.matches(selector)) {
                            const content = (node.innerText || node.getAttribute('aria-label') || '').trim();
                            if (content.toLowerCase().includes(text.toLowerCase()) || 
                                (text === '→' && node.innerHTML.includes('arrow_forward'))) {
                                found = node; return;
                            }
                        }
                        if (node.shadowRoot) walk(node.shadowRoot);
                        for (let child of node.childNodes) walk(child);
                    };
                    walk(root);
                    return found;
                };

                // Periodic cleanup of "Restore" bubble that blocks clicks
                const dismissBubbles = () => {
                    const all = Array.from(document.querySelectorAll('button, div, span'));
                    const r = all.find(el => el.innerText && el.innerText.includes('Restore'));
                    if (r) r.click();
                };
                dismissBubbles();

                const target = queryShadow(document, 'button, div[role="button"], span, div[role="menuitem"], .mat-icon-button, [aria-label*="arrow"], a, .create-notebook-card, .mdc-button, .add-icon');
                
                if (target) {
                    target.scrollIntoView({ block: 'center' });
                    target.click();
                    return true;
                }
                return false;
            }, { timeout }, searchText);
            
            if (result && !silent) console.log(`✅ Success for "${searchText}"`);
            return !!result;
        } catch (e) {
            if (!silent && !e.message.includes('detached Frame')) {
                console.warn(`⚠️  Could not find/click "${searchText}": ${e.message}`);
            }
            return false;
        }
    };

    console.log('🧹 Letting the UI settle (5s) before dismissal...');
    await new Promise(r => setTimeout(r, 5000));

    // --- OVERLAY DISMISSAL ---
    console.log('🧹 Checking for system overlays (Restore/Dismiss/Welcome)...');
    await findAndClickBtn(page, 'Restore', 5000, true);
    await findAndClickBtn(page, 'Dismiss', 3000, true);
    await findAndClickBtn(page, 'Try it now', 3000, true);
    await findAndClickBtn(page, 'Get started', 3000, true);
    await findAndClickBtn(page, 'Got it', 3000, true);
    const currentUrl = page.url();
    const isHome = currentUrl === 'https://notebooklm.google.com' || currentUrl === 'https://notebooklm.google.com/' || !currentUrl.includes('/notebook/');

    if (isHome) {
        console.log('🏠 Home screen detected (URL). Attempting to click "Create new" or "+"...');
        const clicked = await findAndClickBtn(page, 'Create new', 15000);
        if (!clicked) {
            console.log('🔄 Secondary attempt: Searching for "+" icon...');
            await findAndClickBtn(page, '+', 10000);
        }
        if (!clicked) {
            console.log('🔄 Tertiary attempt: Searching for "Create notebook"...');
            await findAndClickBtn(page, 'Create notebook', 10000);
        }
        
        // --- VERIFICATION LOOP (Hardened) ---
        console.log('⏳ Waiting for navigation to a notebook (up to 60s)...');
        let navSuccess = false;
        for (let i = 0; i < 30; i++) {
            await new Promise(r => setTimeout(r, 2000));
            
            // Proof A: URL contains /notebook/
            const url = page.url();
            // Proof B: "Notebook guide" or "Add source" button exists
            const hasNotebookUI = await page.evaluate(() => {
                const body = document.body.innerText.toLowerCase();
                return body.includes('notebook guide') || body.includes('add source') || !!document.querySelector('.source-card');
            });

            if (url.includes('/notebook/') || hasNotebookUI) {
                console.log(`\n✅ Successfully reached notebook! Proof: ${url.includes('/notebook/') ? 'URL' : 'UI'}`);
                navSuccess = true;
                break;
            }
            process.stdout.write('.');
        }
        
        if (!navSuccess) {
            console.error('❌ Failed to navigate to a new notebook. Aborting to prevent invalid clicks.');
            await page.screenshot({ path: 'd:/notebook lm/output/snapshots/nav_fail.png' });
            return false;
        }
    } else {
        console.log('ℹ️  Already inside a notebook (URL detected).');
    }

    // ── Step 2: Add research brief / Import existing ────────────────────────
    console.log('📄 Checking for research results to Import...');
    try {
        const importBtn = await findAndClickBtn(page, 'Import', 15000);
        if (importBtn) {
            console.log('✅ Found "Import" — Unlocking the notebook...');
            await new Promise(r => setTimeout(r, 5000)); // Wait for unlock
        }
    } catch (_) {}

    console.log('📄 Adding Topic Brief as text source (if needed)...');
    
    try {
        // 1. Verify if we already have sources
        const sourceCountValue = await page.evaluate(() => {
            // Try specific count element
            const el = document.querySelector('.source-count, .sources-header-count, [aria-label*="source count"], [class*="source-count"]');
            if (el) {
                const text = el.innerText || '';
                const match = text.match(/\d+/);
                if (match) return parseInt(match[0], 10);
            }
            // Fallback: check Sources panel for actual source items (NOT Studio buttons)
            // Look for "Saved sources will appear here" = 0 sources
            const body = document.body.innerText;
            if (body.includes('Saved sources will appear here')) return 0;
            // Check for actual source cards in the sources panel
            const sourcePanel = document.querySelector('[class*="sources"], [aria-label*="Sources"]');
            if (sourcePanel) {
                const cards = sourcePanel.querySelectorAll('[class*="source-item"], [class*="source_card"], .source-card');
                if (cards.length > 0) return cards.length;
            }
            // Check for "N sources" text near the notebook title area
            const srcMatch = body.match(/(\d+)\s+sources?/);
            if (srcMatch) return parseInt(srcMatch[1], 10);
            return 0;
        });
        
        console.log(`🧐 Current Source Count: ${sourceCountValue}`);

        if (sourceCountValue === 0) {
            console.log('➕ No sources found. Manually adding Topic Brief...');
            const openedMenu = await findAndClickBtn(page, 'Add source', 10000);
            if (openedMenu) {
                // Latest UI uses "Copied text" instead of "Text"
                const clickedText = await findAndClickBtn(page, 'Copied text', 10000);
                if (!clickedText) await findAndClickBtn(page, 'Text', 5000); // Fallback

                const textArea = await page.waitForSelector('textarea, .source-text-input, [contenteditable="true"]', { timeout: 10000 });
                await textArea.click();
                await page.evaluate((text) => {
                    const ta = document.querySelector('textarea, .source-text-input, [contenteditable="true"]');
                    if (ta) {
                        if (ta.tagName === 'DIV' || ta.getAttribute('contenteditable')) { ta.innerText = text; }
                        else { ta.value = text; }
                        ta.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }, topicBrief);

                // Click the Blue Arrow (→) to save
                await findAndClickBtn(page, '→', 5000);
                console.log('⏳ Saving source...');
                await new Promise(r => setTimeout(r, 8000)); // Wait for save
            }
        } else {
            console.log(`✅ Sources already present (${sourceCountValue}). Skipping add step.`);
        }
    } catch (err) {
        console.log(`⚠️  Source injection issue: ${err.message}`);
    }

    // --- FINAL SOURCE VERIFICATION (with retry) ---
    console.log('🧐 Final Source Verification...');
    let finalSourceCheck = false;
    for (let i = 0; i < 5; i++) {
        finalSourceCheck = await page.evaluate(() => {
            const body = document.body.innerText;

            // Method 1: Check for source cards (old + new selectors)
            const cards = document.querySelectorAll('.source-card, mat-card.source-card, [class*="source-item"], [class*="source_card"]');
            if (cards.length > 0) return true;

            // Method 2: Check for source count text
            const el = document.querySelector('.source-count, .sources-header-count, [class*="source-count"]');
            if (el) {
                const text = el.innerText || '';
                const match = text.match(/\d+/);
                if (match && parseInt(match[0], 10) > 0) return true;
            }

            // Method 3: Check if the Sources panel has any listed items
            // NotebookLM shows source titles under the "Sources" heading
            if (body.includes('Sources') && (body.includes('Deep Research Brief') || body.includes('more sources'))) return true;

            // Method 4: Check if "Saved sources will appear here" is absent (= has sources)
            // and the page is NOT showing the empty notebook state
            if (!body.includes('Saved sources will appear here') && body.includes('Notebook guide')) return true;

            return false;
        });
        if (finalSourceCheck) break;
        console.log('   ⏳ Waiting for source to register (5x retry)...');
        await new Promise(r => setTimeout(r, 2000));
    }

    if (!finalSourceCheck) {
        console.error('❌ Aborting: Notebook has 0 sources. Overview generation will fail.');
        await page.screenshot({ path: 'd:/notebook lm/output/snapshots/zero_sources.png' });
        return false;
    }

    // ── Step 4: Check for existing overview OR trigger new generation ────────
    console.log('🎬 Checking for existing overview or triggering generation...');

    // Check if an overview is already ready (from a previous run)
    const existingOverview = await page.evaluate(() => {
        const body = document.body.innerText;
        if (body.includes('is ready')) return 'ready';
        if (body.includes('generating') || body.includes('creating your')) return 'generating';
        return null;
    });

    if (existingOverview === 'ready') {
        console.log('✅ An overview is already ready! Skipping generation.');
    } else if (existingOverview === 'generating') {
        console.log('⏳ Generation already in progress. Waiting for completion...');
    } else {
        // Check for daily Cinematics limit
        const hasLimit = await page.evaluate(() => {
            return document.body.innerText.includes('daily Cinematics limit') ||
                   document.body.innerText.includes('reached your daily');
        });

        if (hasLimit) {
            console.log('⚠️  Daily Video (Cinematics) limit reached. Using Audio Overview...');
            await findAndClickBtn(page, 'Audio Overview', 10000);
            await new Promise(r => setTimeout(r, 3000));
            // Handle any generate confirmation
            await findAndClickBtn(page, 'Generate', 8000);
        } else {
            // Try Video Overview first
            const triggeredVideo = await findAndClickBtn(page, 'Video Overview', 10000);
            if (triggeredVideo) {
                console.log('📝 Handling Video Customization popup...');
                const customPrompt = `Create an excited, high-energy educational video overview for "${topic}".
The content MUST be top-tier: professional, engaging, and exam-focused.
Cover the core intuition, worked examples, and common interview questions.
Ensure the tone is enthusiastic and keeps the audience hooked!`;

                await new Promise(r => setTimeout(r, 3000));

                // Fill the textarea
                await page.evaluate((text) => {
                    for (const el of document.querySelectorAll('textarea, [contenteditable="true"]')) {
                        if (el.offsetParent === null && !el.closest('[role="dialog"]')) continue;
                        if (el.tagName === 'DIV' || el.getAttribute('contenteditable')) { el.innerText = text; }
                        else { el.value = text; }
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        return;
                    }
                }, customPrompt);
                console.log('   ✅ Custom prompt filled');
                await new Promise(r => setTimeout(r, 1000));

                // Click Generate button in the popup
                const genClicked = await page.evaluate(() => {
                    const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
                    const gen = btns.find(b => (b.innerText || '').trim() === 'Generate' && b.offsetParent !== null);
                    if (gen) { gen.click(); return true; }
                    return false;
                });
                if (!genClicked) await findAndClickBtn(page, 'Generate', 8000);

                // Check if we hit the limit after clicking
                await new Promise(r => setTimeout(r, 3000));
                const hitLimit = await page.evaluate(() => {
                    return document.body.innerText.includes('daily Cinematics limit') ||
                           document.body.innerText.includes('reached your daily');
                });
                if (hitLimit) {
                    console.log('⚠️  Hit Cinematics limit. Falling back to Audio Overview...');
                    // Dismiss any dialog
                    await page.evaluate(() => {
                        for (const b of document.querySelectorAll('button')) {
                            if (['ok', 'close', 'cancel', 'dismiss'].includes((b.innerText || '').trim().toLowerCase())) {
                                b.click(); return;
                            }
                        }
                    });
                    await new Promise(r => setTimeout(r, 2000));
                    await findAndClickBtn(page, 'Audio Overview', 10000);
                    await new Promise(r => setTimeout(r, 3000));
                    await findAndClickBtn(page, 'Generate', 8000);
                } else {
                    console.log('✅ Video Generation triggered!');
                }
            } else {
                console.log('ℹ️  Video Overview not found, using Audio Overview...');
                await findAndClickBtn(page, 'Audio Overview', 10000);
                await new Promise(r => setTimeout(r, 3000));
                await findAndClickBtn(page, 'Generate', 8000);
            }
        }
    }

    // --- GENERATION / READINESS VERIFICATION ---
    console.log('🧪 Waiting for overview to be ready...');
    let isReady = existingOverview === 'ready';
    if (!isReady) {
        for (let i = 0; i < 120; i++) { // Up to 10 minutes
            await new Promise(r => setTimeout(r, 5000));
            const status = await page.evaluate(() => {
                const body = document.body.innerText.toLowerCase();
                if (body.includes('is ready') || body.includes('play_arrow')) return 'ready';
                if (body.includes('generating') || body.includes('creating') || body.includes('processing')) return 'generating';
                return 'unknown';
            });
            if (status === 'ready') {
                console.log('✅ Overview is ready!');
                isReady = true;
                break;
            }
            if (i % 6 === 0) {
                const elapsed = (i + 1) * 5;
                console.log(`   ⏱ ${status === 'generating' ? 'Generating' : 'Waiting'}... (${elapsed}s)`);
                try { await page.screenshot({ path: 'd:/notebook lm/output/snapshots/live_vision.png' }); } catch (_) {}
            }
        }
    }

    if (!isReady) {
        console.warn('⚠️  Generation may have timed out. Checking for download anyway...');
        await page.screenshot({ path: 'd:/notebook lm/output/snapshots/gen_timeout.png' });
    }

    // ── Step 5: Download the overview ────────────────────────────────────────
    console.log('📥 Attempting to download overview...');

    // Ensure CDP download path is set on this page
    try {
        const client = await page.createCDPSession();
        await client.send('Page.setDownloadBehavior', {
            behavior: 'allow',
            downloadPath: DOWNLOAD_DIR
        });
    } catch (_) {}

    // The download is behind the 3-dot menu (more_vert) next to the play_arrow button.
    // We find it by locating play_arrow first, then clicking the next more_vert after it.
    let downloaded = false;
    for (let attempt = 0; attempt < 3; attempt++) {
        // Find the more_vert button adjacent to the play_arrow button in DOM order
        const menuOpened = await page.evaluate(() => {
            const allButtons = Array.from(document.querySelectorAll('button'));
            let playIndex = -1;
            for (let i = 0; i < allButtons.length; i++) {
                const text = (allButtons[i].innerText || '').trim();
                const aria = allButtons[i].getAttribute('aria-label') || '';
                if (text === 'play_arrow' || aria === 'Play') {
                    playIndex = i;
                    break;
                }
            }
            if (playIndex === -1) return null;

            // Click the next more_vert button after play
            for (let j = playIndex + 1; j < Math.min(playIndex + 5, allButtons.length); j++) {
                const text = (allButtons[j].innerText || '').trim();
                const aria = allButtons[j].getAttribute('aria-label') || '';
                if (text === 'more_vert' || aria === 'More') {
                    allButtons[j].click();
                    return true;
                }
            }
            return null;
        });

        if (menuOpened) {
            await new Promise(r => setTimeout(r, 1500));
            // Click Download in the Angular Material CDK overlay menu
            const dlClicked = await page.evaluate(() => {
                const items = document.querySelectorAll('.cdk-overlay-container [role="menuitem"], .cdk-overlay-container button, [role="menu"] [role="menuitem"]');
                for (const item of items) {
                    if ((item.innerText || '').toLowerCase().includes('download') && item.offsetWidth > 0) {
                        item.click();
                        return true;
                    }
                }
                return false;
            });

            if (dlClicked) {
                console.log('✅ Download clicked from overview menu!');
                break;
            }
        }

        // Fallback: direct Download button search
        const directClick = await findAndClickBtn(page, 'Download', 5000, true);
        if (directClick) {
            console.log('✅ Download clicked directly!');
            break;
        }

        await page.keyboard.press('Escape'); // Close any open menu
        await new Promise(r => setTimeout(r, 2000));
        if (attempt < 2) console.log(`   Retry download attempt ${attempt + 2}/3...`);
    }

    // Wait for download to complete
    console.log('⏳ Waiting for download to finish...');
    await new Promise(r => setTimeout(r, 5000));
    for (let w = 0; w < 24; w++) {
        await new Promise(r => setTimeout(r, 5000));
        const pending = fs.readdirSync(DOWNLOAD_DIR).filter(f => f.endsWith('.crdownload'));
        if (pending.length === 0) break;
        console.log(`   ⏳ Download in progress... (${pending.length} file(s))`);
    }

    // Final file scan — check both configured dir and Chrome's default Downloads
    const safeTopic = topic.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
    const chromeDownloads = path.join(process.env.USERPROFILE || 'C:\\Users\\AZAM RIZWAN', 'Downloads');
    const searchDirs = [DOWNLOAD_DIR, chromeDownloads];

    let foundFile = null;
    const cutoffTime = Date.now() - 120000; // Files from last 2 minutes

    for (const dir of searchDirs) {
        if (!fs.existsSync(dir)) continue;
        const files = fs.readdirSync(dir)
            .filter(f => !f.endsWith('.crdownload') && (f.endsWith('.mp4') || f.endsWith('.wav') || f.endsWith('.mp3') || f.endsWith('.webm')))
            .map(f => ({ name: f, full: path.join(dir, f), mtime: fs.statSync(path.join(dir, f)).mtimeMs }))
            .filter(f => f.mtime > cutoffTime)
            .sort((a, b) => b.mtime - a.mtime);

        if (files.length > 0) {
            foundFile = files[0];
            console.log(`   Found recent file in ${dir === DOWNLOAD_DIR ? 'configured dir' : 'Chrome Downloads'}: ${foundFile.name}`);
            break;
        }
    }

    if (foundFile) {
        const ext = path.extname(foundFile.name);
        const renamed = path.join(DOWNLOAD_DIR, `notebooklm_${safeTopic}${ext}`);
        // Move from source to our download dir if needed
        if (foundFile.full !== renamed) {
            try {
                fs.copyFileSync(foundFile.full, renamed);
                // Only delete from Chrome Downloads, not from our dir
                if (!foundFile.full.startsWith(DOWNLOAD_DIR)) {
                    fs.unlinkSync(foundFile.full);
                }
            } catch (e) {
                console.warn(`   Could not move file: ${e.message}`);
            }
        }
        console.log(`\n🎉 SUCCESS! Video Saved: ${renamed}`);

        const handoffPath = path.join(DOWNLOAD_DIR, '..', 'notebooklm_handoff.json');
        fs.writeFileSync(handoffPath, JSON.stringify({
            local_audio: renamed,
            topic, subject, chapter, strategy,
            timestamp: new Date().toISOString()
        }, null, 2));
        console.log(`📋 Handoff written: ${handoffPath}`);
        downloaded = true;
    } else {
        console.error('❌ No downloaded file found in:', searchDirs.join(' or '));
        await page.screenshot({ path: 'd:/notebook lm/output/snapshots/download_fail.png' });
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
