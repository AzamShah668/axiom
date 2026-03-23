/**
 * colab_launcher.js
 * Automates launching the TTS Colab notebook using the automation Chrome profile.
 * Supports both Qwen3 (legacy) and CosyVoice 2 (instruct mode) notebooks.
 * Set TTS_COLAB_URL in config/.env to switch between notebooks.
 *
 * Flow:
 *  1. Check if existing Gradio URL is still alive → skip if yes
 *  2. Open Colab notebook in automation Chrome
 *  3. Handle "Too many sessions" dialog (terminate + reload)
 *  4. Click "Run All" → wait for Gradio server to start
 *  5. Extract the gradio.live public URL from the output cell
 *  6. Write it to video/colab_url.json for the TTS pipeline to use
 */

require('dotenv').config({ path: `${__dirname}/../config/.env` });

const fs   = require('fs');
const path = require('path');
const https = require('https');
const http  = require('http');
const { getBrowser } = require('./chrome_bridge');

// Default: Qwen3 notebook. Set TTS_COLAB_URL in .env to switch to CosyVoice 2.
const COLAB_URL      = process.env.TTS_COLAB_URL || 'https://colab.research.google.com/drive/1uV6ZIqg3M9mwi-9Leplkmntn94rKEh9S';
const COLAB_URL_JSON = path.join(__dirname, '../video/colab_url.json');

// How long to wait for Colab to generate the Gradio URL (max 12 min)
const MAX_WAIT_MS   = 12 * 60 * 1000;
const POLL_START_MS = 5000;
const POLL_MAX_MS   = 15000;

/**
 * Pings a Gradio URL to check if the server is truly alive.
 */
function pingGradio(url) {
    return new Promise((resolve) => {
        try {
            const parsed = new URL(url);
            const lib    = parsed.protocol === 'https:' ? https : http;
            const req    = lib.get(url, { timeout: 10000 }, (res) => {
                if (res.statusCode >= 500) return resolve(false);
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    resolve(!body.includes("No interface is running right now"));
                });
            });
            req.on('error', () => resolve(false));
            req.on('timeout', () => { req.destroy(); resolve(false); });
        } catch (_) {
            resolve(false);
        }
    });
}

/**
 * Deep-search shadow DOM for elements matching text, then click.
 */
async function deepClickByText(page, textVariations) {
    return page.evaluate((texts) => {
        function search(root, depth) {
            if (depth > 10) return false;
            for (const el of root.querySelectorAll('*')) {
                const t = (el.textContent || '').trim();
                const tag = el.tagName.toLowerCase();
                const isClickable = tag.includes('button') || el.getAttribute('role') === 'button';
                if (isClickable && texts.some(v => t.toLowerCase().includes(v.toLowerCase()))) {
                    el.click();
                    return true;
                }
                if (el.shadowRoot && search(el.shadowRoot, depth + 1)) return true;
            }
            return false;
        }
        return search(document, 0);
    }, textVariations);
}

/**
 * Handle "Too many sessions" dialog:
 *  1. Click "Manage sessions" in the dialog
 *  2. Click "Terminate other sessions" in the session manager
 *  3. Close dialog and reload page
 */
async function handleTooManySessions(page) {
    console.log('⚠️  "Too many sessions" detected. Fixing...');

    // Click "Manage sessions" — it's an md-text-button in the mwc-dialog
    await page.evaluate(() => {
        const dialog = document.querySelector('mwc-dialog');
        if (!dialog) return;
        const buttons = dialog.querySelectorAll('md-text-button, mwc-button, button');
        for (const b of buttons) {
            if ((b.textContent || '').trim().includes('Manage sessions')) {
                b.click();
                return;
            }
        }
        // Fallback: click any leaf with that text
        for (const el of dialog.querySelectorAll('*')) {
            if (el.children.length === 0 && (el.textContent || '').trim() === 'Manage sessions') {
                el.click();
                return;
            }
        }
    });
    await new Promise(r => setTimeout(r, 4000));

    // Click "Terminate other sessions" in the session manager
    await page.evaluate(() => {
        function findAndClick(root, depth) {
            if (depth > 10) return false;
            for (const el of root.querySelectorAll('*')) {
                const text = (el.textContent || '').trim();
                if (text === 'Terminate other sessions' && el.tagName.toLowerCase().includes('button')) {
                    el.click();
                    return true;
                }
                if (el.shadowRoot && findAndClick(el.shadowRoot, depth + 1)) return true;
            }
            return false;
        }
        findAndClick(document, 0);
    });
    await new Promise(r => setTimeout(r, 3000));

    // Close any remaining dialogs
    await page.evaluate(() => {
        for (const el of document.querySelectorAll('md-text-button, mwc-button, button')) {
            const text = (el.textContent || '').trim().toLowerCase();
            if (text === 'done' || text === 'close' || text === 'cancel') {
                el.click();
                return;
            }
        }
    });
    await new Promise(r => setTimeout(r, 2000));

    // Reload page to get clean state
    console.log('   Reloading Colab page...');
    await page.reload({ waitUntil: 'networkidle2', timeout: 60000 });
    await new Promise(r => setTimeout(r, 5000));
    console.log('   Sessions terminated and page reloaded.');
}

/**
 * Check if the page has a "Too many sessions" error.
 */
async function hasTooManySessionsError(page) {
    return page.evaluate(() => {
        const body = document.body.innerText;
        return body.includes('too many active sessions') || body.includes('Too many sessions');
    });
}

async function launchColabAndGetGradioUrl() {
    console.log('\n🚀 Colab Launcher — checking existing URL first...');

    // ── Pre-check: Is the existing URL still alive? ────────────────────────
    if (fs.existsSync(COLAB_URL_JSON)) {
        try {
            const existing = JSON.parse(fs.readFileSync(COLAB_URL_JSON, 'utf8'));
            if (existing.gradio_url) {
                console.log(`🔍 Pinging existing Gradio URL: ${existing.gradio_url}`);
                const isAlive = await pingGradio(existing.gradio_url);
                if (isAlive) {
                    console.log('✅ Existing URL is still LIVE. Skipping browser launch.');
                    return existing.gradio_url;
                }
                console.log('ℹ️  Existing URL is dead/stale. Proceeding to launch browser...');
            }
        } catch (e) {
            console.warn('⚠️  Could not read existing colab_url.json. Proceeding...');
        }
    }

    const browser = await getBrowser();

    // Reuse existing Colab tab or open new one
    const pages = await browser.pages();
    let page = pages.find(p => p.url().includes('colab.research.google.com'));

    if (page) {
        console.log('📂 Reusing existing Colab tab');
        await page.bringToFront();
    } else {
        // Reuse blank tab or create new
        const blank = pages.find(p => p.url() === 'about:blank' || p.url() === 'chrome://newtab/');
        page = blank || await browser.newPage();
        page.setDefaultNavigationTimeout(60000);
        console.log(`📂 Opening Colab notebook: ${COLAB_URL}`);
        await page.goto(COLAB_URL, { waitUntil: 'networkidle2' });
    }

    await new Promise(r => setTimeout(r, 4000));

    // ── Handle "Not authored by Google" trust dialog ────────────────────────
    const trustDismissed = await page.evaluate(() => {
        const dialogs = document.querySelectorAll('mwc-dialog[open]');
        for (const d of dialogs) {
            const text = d.innerText || '';
            if (text.includes('not authored by Google') || text.includes('authored by')) {
                // Click "Run anyway" button
                for (const btn of d.querySelectorAll('mwc-button, md-text-button, button')) {
                    const btnText = (btn.textContent || '').trim().toLowerCase();
                    if (btnText.includes('run anyway')) {
                        btn.click();
                        return 'dismissed';
                    }
                }
            }
        }
        return 'none';
    });
    if (trustDismissed === 'dismissed') {
        console.log('🔓 Dismissed "not authored by Google" trust dialog');
        await new Promise(r => setTimeout(r, 3000));
    }

    // ── Handle "Too many sessions" ─────────────────────────────────────────
    if (await hasTooManySessionsError(page)) {
        await handleTooManySessions(page);

        // If still on Colab, check again
        if (await hasTooManySessionsError(page)) {
            console.warn('⚠️  Session error persists. Will try to connect anyway...');
        }
    }

    // ── Connect to runtime if needed ──────────────────────────────────────
    console.log('🔌 Connecting to runtime...');
    await page.evaluate(() => {
        const wrapper = document.querySelector('colab-connect-button');
        if (!wrapper) return;
        // The real button is inside shadow DOM
        if (wrapper.shadowRoot) {
            const btn = wrapper.shadowRoot.querySelector('#connect');
            if (btn) { btn.click(); return; }
        }
        wrapper.click();
    });
    await new Promise(r => setTimeout(r, 10000));

    // ── Check for GPU quota exhaustion ──────────────────────────────────
    const gpuBlocked = await page.evaluate(() => {
        const body = document.body.innerText;
        return body.includes('Cannot connect to GPU') ||
               body.includes('usage limits in Colab') ||
               body.includes('cannot currently connect to a GPU');
    });
    if (gpuBlocked) {
        console.error('❌ GPU QUOTA EXHAUSTED — Colab cannot allocate a GPU right now.');
        console.log('   Options: wait for quota reset, or use Colab Pro.');
        // Dismiss the dialog so the page isn't stuck
        await page.evaluate(() => {
            for (const btn of document.querySelectorAll('button, md-text-button, mwc-button')) {
                if ((btn.textContent || '').trim() === 'Close') { btn.click(); return; }
            }
        });
        throw new Error('GPU quota exhausted — Colab cannot allocate a GPU. Wait for quota reset or use Colab Pro.');
    }

    // ── Wait for runtime to be connected ─────────────────────────────────
    console.log('⏳ Waiting for runtime to be allocated...');
    const runtimeStart = Date.now();
    while (Date.now() - runtimeStart < 60000) {
        const btnText = await page.evaluate(() => {
            const wrapper = document.querySelector('colab-connect-button');
            if (!wrapper || !wrapper.shadowRoot) return '';
            const btn = wrapper.shadowRoot.querySelector('#connect');
            return btn ? btn.innerText : '';
        });
        if (btnText.includes('RAM') || btnText.includes('Disk') || btnText.includes('Connected')) {
            console.log('✅ Runtime connected!');
            break;
        }
        await new Promise(r => setTimeout(r, 3000));
    }

    // ── Snapshot pre-existing Gradio URLs before Run All ──────────────────
    let preExistingUrls = new Set();
    try {
        for (const frame of page.frames()) {
            const urls = await frame.evaluate(() => {
                const matches = document.body.innerText.match(/https?:\/\/[a-z0-9\-]+\.gradio\.live/g);
                return matches ? [...new Set(matches)] : [];
            }).catch(() => []);
            urls.forEach(u => preExistingUrls.add(u));
        }
        if (preExistingUrls.size > 0) {
            console.log(`📸 Snapshotted ${preExistingUrls.size} pre-existing URL(s) to skip`);
        }
    } catch (_) {}

    // ── Click "Run All" ──────────────────────────────────────────────────
    console.log('▶️  Triggering "Run All"...');
    try {
        await page.click('body').catch(() => {});
        await page.keyboard.down('Control');
        await page.keyboard.press('F9');
        await page.keyboard.up('Control');
        await new Promise(r => setTimeout(r, 3000));

        // Handle "Run anyway" / "Disconnect and run all" dialogs
        await deepClickByText(page, ['Run anyway', 'Disconnect and run all', 'Yes', 'Ok']);
        await new Promise(r => setTimeout(r, 3000));

        // Check if GPU quota dialog appeared after Run All
        const gpuBlockedAfterRun = await page.evaluate(() => {
            const body = document.body.innerText;
            return body.includes('Cannot connect to GPU') ||
                   body.includes('usage limits in Colab') ||
                   body.includes('cannot currently connect to a GPU');
        });
        if (gpuBlockedAfterRun) {
            throw new Error('GPU quota exhausted — Colab cannot allocate a GPU. Wait for quota reset or use Colab Pro.');
        }

        // Handle another "Too many sessions" that appears after Run All
        if (await hasTooManySessionsError(page)) {
            await handleTooManySessions(page);

            // After reload, runtime is disconnected — reconnect it
            console.log('🔌 Re-connecting runtime after session fix...');
            await page.evaluate(() => {
                const wrapper = document.querySelector('colab-connect-button');
                if (!wrapper) return;
                if (wrapper.shadowRoot) {
                    const btn = wrapper.shadowRoot.querySelector('#connect');
                    if (btn) { btn.click(); return; }
                }
                wrapper.click();
            });
            await new Promise(r => setTimeout(r, 15000));

            // Re-snapshot URLs after reload (old output may be cleared)
            preExistingUrls = new Set();
            try {
                for (const frame of page.frames()) {
                    const urls = await frame.evaluate(() => {
                        const matches = document.body.innerText.match(/https?:\/\/[a-z0-9\-]+\.gradio\.live/g);
                        return matches ? [...new Set(matches)] : [];
                    }).catch(() => []);
                    urls.forEach(u => preExistingUrls.add(u));
                }
            } catch (_) {}

            // Retry Run All after session fix + reconnect
            await page.keyboard.down('Control');
            await page.keyboard.press('F9');
            await page.keyboard.up('Control');
            await new Promise(r => setTimeout(r, 3000));
            await deepClickByText(page, ['Run anyway', 'Disconnect and run all', 'Yes', 'Ok']);
        }

        console.log('✅ "Run All" triggered. Waiting for Gradio server to start...');
    } catch (err) {
        console.warn('⚠️  Could not auto-click Run All:', err.message);
        console.log('ℹ️  Please manually click "Runtime → Run All" in the browser window.');
    }

    // ── Poll for Gradio URL ─────────────────────────────────────────────
    console.log(`⏳ Polling for Gradio URL (timeout: ${MAX_WAIT_MS / 60000} min)...`);
    const startTime = Date.now();
    let gradioUrl = null;
    let pollInterval = POLL_START_MS;
    // Track ALL dead URLs so we don't re-ping them every cycle
    const deadUrls = new Set(preExistingUrls);

    while (Date.now() - startTime < MAX_WAIT_MS) {
        await new Promise(r => setTimeout(r, pollInterval));
        pollInterval = Math.min(pollInterval * 1.3, POLL_MAX_MS);

        let potentialUrls = [];
        try {
            // Check all frames for gradio.live URLs
            for (const frame of page.frames()) {
                const urls = await frame.evaluate(() => {
                    const matches = document.body.innerText.match(/https?:\/\/[a-z0-9\-]+\.gradio\.live/g);
                    return matches ? [...new Set(matches)] : [];
                }).catch(() => []);
                potentialUrls.push(...urls);
            }

            // Deduplicate
            potentialUrls = [...new Set(potentialUrls)];
        } catch (pollError) {
            console.log(`   ⏱ Polling issue: ${pollError.message}`);
            continue;
        }

        // Only ping NEW URLs we haven't already confirmed dead
        const newUrls = potentialUrls.filter(u => !deadUrls.has(u));

        for (const url of newUrls) {
            const isAlive = await pingGradio(url);
            if (isAlive) {
                gradioUrl = url;
                console.log(`\n✅ LIVE Gradio URL found: ${gradioUrl}`);
                break;
            } else {
                deadUrls.add(url);
            }
        }

        if (gradioUrl) break;

        const elapsed = Math.round((Date.now() - startTime) / 1000);
        const totalFound = potentialUrls.length;
        const newCount = newUrls.length;
        if (totalFound > 0) {
            console.log(`   ⏱ ${totalFound} URL(s) found, ${newCount} new — none alive yet. (${elapsed}s elapsed)`);
        } else {
            console.log(`   ⏱ Still waiting... (${elapsed}s elapsed)`);
        }
    }

    if (!gradioUrl) {
        console.error('❌ Timed out waiting for Gradio URL. Check Colab manually.');
        throw new Error('Timed out waiting for Gradio URL after ' + (MAX_WAIT_MS / 60000) + ' minutes.');
    }

    // ── Save URL ─────────────────────────────────────────────────────────
    const payload = {
        gradio_url: gradioUrl,
        updated_at: new Date().toISOString(),
        profile_used: 'automation',
    };
    fs.writeFileSync(COLAB_URL_JSON, JSON.stringify(payload, null, 2));
    console.log(`💾 Saved to: ${COLAB_URL_JSON}`);

    console.log('\n🟢 Colab session is live. Browser will remain open.');
    console.log('   Do NOT close this window while TTS is running.\n');

    return gradioUrl;
}

// Standalone execution
if (require.main === module) {
    launchColabAndGetGradioUrl().catch(err => {
        console.error('Fatal error:', err.message);
        process.exit(1);
    });
}

module.exports = { launchColabAndGetGradioUrl, pingGradio };
