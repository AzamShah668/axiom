/**
 * colab_launcher.js
 * Automates launching the Qwen TTS Colab notebook using the user's existing
 * Chrome profile (no credentials stored in code).
 *
 * Flow:
 *  1. Launch Chrome with Profile 4 (Axiom Academy / Google account)
 *  2. Navigate to the saved Colab notebook
 *  3. Click "Run All" → wait for Gradio server to start
 *  4. Extract the gradio.live public URL from the output cell
 *  5. Write it to video/colab_url.json for the TTS pipeline to use
 */

const fs   = require('fs');
const path = require('path');
const { getBrowser } = require('./chrome_bridge');

const COLAB_URL = 'https://colab.research.google.com/drive/1uV6ZIqg3M9mwi-9Leplkmntn94rKEh9S';
const CHROME_PROFILE   = 'Profile 4';   // Axiom Academy (fhjchvc6@gmail.com)
const COLAB_URL_JSON   = path.join(__dirname, '../video/colab_url.json');

// How long to wait for Colab to generate the Gradio URL (max 10 min)
const MAX_WAIT_MS  = 10 * 60 * 1000;
const POLL_MS      = 8000;

async function launchColabAndGetGradioUrl() {
    console.log('\n🚀 Colab Launcher — Starting...');

    const browser = await getBrowser();
    const page    = await browser.newPage();
    page.setDefaultNavigationTimeout(60000);

    // ── Step 1: Open Colab ──────────────────────────────────────────────────
    console.log(`📂 Opening Colab notebook: ${COLAB_URL}`);
    await page.goto(COLAB_URL, { waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 4000)); // Let Colab UI settle

    // ── Step 2: Click "Runtime → Run All" ──────────────────────────────────
    console.log('▶️  Triggering "Run All"...');
    try {
        // Method A: Keyboard Shortcut (Most Reliable)
        console.log('   Pressing Ctrl + F9...');
        await page.click('body').catch(() => {}); // Ensure focus
        await page.keyboard.down('Control');
        await page.keyboard.press('F9');
        await page.keyboard.up('Control');
        
        await new Promise(r => setTimeout(r, 2000));

        // Method B: DOM Traversal (Fallback)
        await page.evaluate(() => {
            const menuItems = document.querySelectorAll('colab-menu-item, .menu-item');
            for (const item of menuItems) {
                if (item.textContent && item.textContent.includes('Run all')) {
                    item.click();
                    return;
                }
            }
        });
        await new Promise(r => setTimeout(r, 2000));

        // Handle confirmation dialogs (piercing Shadow DOM)
        await page.evaluate(() => {
            function findTextAndClick(root, textVariations) {
                // Check current root
                const elements = root.querySelectorAll('*');
                for (const el of elements) {
                    // Check if it's a button-like element
                    if (el.tagName.includes('BUTTON') || el.getAttribute('role') === 'button') {
                        const txt = (el.textContent || '').trim().toLowerCase();
                        if (textVariations.some(v => txt.includes(v.toLowerCase()))) {
                            el.click();
                            return true;
                        }
                    }
                    // Traverse shadow roots
                    if (el.shadowRoot) {
                        if (findTextAndClick(el.shadowRoot, textVariations)) return true;
                    }
                }
                return false;
            }
            findTextAndClick(document, ['Run anyway', 'Disconnect and run all']);
        });

        console.log('✅ "Run All" triggered. Waiting for Gradio server to start...');
    } catch (err) {
        console.warn('⚠️  Could not auto-click Run All:', err.message);
        console.log('ℹ️  Please manually click "Runtime → Run All" in the browser window.');
    }

const https = require('https');
const http = require('http');

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

    // ── Step 3: Poll cell outputs for the gradio.live URL ──────────────────
    console.log(`⏳ Polling for Gradio URL (timeout: ${MAX_WAIT_MS / 60000} min)...`);
    const startTime = Date.now();
    let gradioUrl = null;

    while (Date.now() - startTime < MAX_WAIT_MS) {
        await new Promise(r => setTimeout(r, POLL_MS));

        let potentialUrl = null;
        try {
            for (const frame of page.frames()) {
                const url = await frame.evaluate(() => {
                    const allText = document.body ? document.body.innerText : '';
                    const match = allText.match(/https?:\/\/[a-z0-9\-]+\.gradio\.live/);
                    return match ? match[0] : null;
                }).catch(() => null); // Silent catch for cross-origin or detached frames
                
                if (url) {
                    potentialUrl = url;
                    break;
                }
            }
        } catch (pollError) {
            console.log(`   ⏱ Frame polling issue. Still waiting...`);
            continue;
        }

        if (potentialUrl) {
            // Verify it's actually alive and not Old HTML from yesterday
            const isAlive = await pingGradio(potentialUrl);
            if (isAlive) {
                gradioUrl = potentialUrl;
                console.log(`\n✅ New, LIVE Gradio URL found: ${gradioUrl}`);
                break;
            } else {
                const elapsed = Math.round((Date.now() - startTime) / 1000);
                console.log(`   ⏱ Found old URL (${potentialUrl}) but it's dead. Still waiting... (${elapsed}s elapsed)`);
            }
        } else {
            const elapsed = Math.round((Date.now() - startTime) / 1000);
            console.log(`   ⏱ Still waiting... (${elapsed}s elapsed)`);
        }
    }

    if (!gradioUrl) {
        console.error('❌ Timed out waiting for Gradio URL. Check Colab manually.');
        await browser.close();
        process.exit(1);
    }

    // ── Step 4: Save URL to colab_url.json ─────────────────────────────────
    const payload = {
        gradio_url: gradioUrl,
        updated_at: new Date().toISOString(),
        profile_used: CHROME_PROFILE,
    };
    fs.writeFileSync(COLAB_URL_JSON, JSON.stringify(payload, null, 2));
    console.log(`💾 Saved to: ${COLAB_URL_JSON}`);

    // Keep browser open — Colab session must stay alive for TTS jobs
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

module.exports = { launchColabAndGetGradioUrl };
