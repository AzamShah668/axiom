// colab_manager.js
// Fully automated Colab session manager — NO manual URL pasting required.
//
// Flow:
//   1. Reads the last saved Gradio URL from colab_url.json
//   2. Pings the URL — if live, returns it immediately
//   3. If dead/expired: auto-launches Colab via colab_launcher.js (Chrome automation)
//      and polls for the new gradio.live URL automatically
//
// ZERO HUMAN INTERACTION NEEDED

const fs      = require('fs');
const path    = require('path');
const https   = require('https');
const http    = require('http');

// ─────────────────────────────────────────────
// CONFIGURATION
// ─────────────────────────────────────────────

// Local file where the latest live Gradio URL is persisted
const URL_CACHE_FILE = path.join(__dirname, '..', 'video', 'colab_url.json');

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function readCachedUrl() {
    try {
        if (fs.existsSync(URL_CACHE_FILE)) {
            const data = JSON.parse(fs.readFileSync(URL_CACHE_FILE, 'utf8'));
            // Support both key naming conventions
            return data.gradio_url || data.gradioUrl || null;
        }
    } catch (_) {}
    return null;
}

/**
 * Pings the Gradio URL to check if the server is truly alive.
 * A dead Gradio server often returns HTTP 200 but renders "No interface is running right now".
 * Therefore we check the HTML body.
 */
function pingUrl(url) {
    return new Promise((resolve) => {
        try {
            const parsed = new URL(url);
            const lib    = parsed.protocol === 'https:' ? https : http;
            const req    = lib.get(url, { timeout: 10000 }, (res) => {
                if (res.statusCode >= 500) {
                    return resolve(false);
                }
                
                let body = '';
                res.on('data', chunk => body += chunk);
                res.on('end', () => {
                    if (body.includes("No interface is running right now")) {
                        resolve(false);
                    } else {
                        // If it doesn't have the dead message and response was <500, it's alive
                        resolve(true);
                    }
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
 * Auto-relaunches Colab using colab_launcher.js (Chrome Profile 4 automation).
 * Returns the new live Gradio URL without any manual intervention.
 */
async function autoRelaunchColab() {
    console.log('\n══════════════════════════════════════════════════════');
    console.log('🤖  Colab TTS server is DOWN — auto-relaunching...');
    console.log('══════════════════════════════════════════════════════\n');

    try {
        // Use colab_launcher.js which handles Chrome automation:
        //   Opens Colab → clicks "Run All" → polls for Gradio URL → saves to colab_url.json
        const { launchColabAndGetGradioUrl } = require('./colab_launcher');
        const newUrl = await launchColabAndGetGradioUrl();

        if (newUrl) {
            console.log(`\n✅ Colab auto-relaunched! New URL: ${newUrl}`);
            return newUrl;
        }

        throw new Error('colab_launcher returned null — Run All may have failed');
    } catch (err) {
        console.error(`\n❌ Auto-relaunch failed: ${err.message}`);
        console.log('\n╔═══════════════════════════════════════════════════════╗');
        console.log('║  MANUAL FALLBACK: Please start Colab manually         ║');
        console.log('║  1. Open: https://colab.research.google.com           ║');
        console.log('║  2. Open your Qwen TTS notebook                       ║');
        console.log('║  3. Click Runtime → Run All                           ║');
        console.log('║  4. Copy the gradio.live URL                          ║');
        console.log('║  5. Update video/colab_url.json with the new URL      ║');
        console.log('╚═══════════════════════════════════════════════════════╝\n');
        throw err;
    }
}

// ─────────────────────────────────────────────
// MAIN EXPORT
// ─────────────────────────────────────────────

/**
 * Returns a guaranteed-live Gradio URL.
 * If the cached URL is healthy, returns it instantly.
 * If dead/missing, auto-launches Colab via browser automation.
 *
 * @returns {Promise<string>} A live gradio.live URL
 */
async function getLiveColabUrl() {
    const cached = readCachedUrl();

    if (cached) {
        process.stdout.write(`🔗  Checking cached Colab URL (${cached})... `);
        const alive = await pingUrl(cached);
        if (alive) {
            console.log('✅  Server is live!');
            return cached;
        }
        console.log('❌  Server is down.');
    } else {
        console.log('📋  No cached Colab URL found.');
    }

    // Fully automated relaunch — no manual input needed
    return autoRelaunchColab();
}

module.exports = { getLiveColabUrl, autoRelaunchColab, pingUrl };
