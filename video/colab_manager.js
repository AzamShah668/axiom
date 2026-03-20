// colab_manager.js
// Fully automated Colab session manager.
//
// What it does:
//   1. Reads the last saved Gradio URL from colab_url.json.
//   2. Pings the URL — if live, returns it immediately.
//   3. If dead/expired: launches your default browser to the Colab notebook,
//      prompts you to click "Run All", then polls for the new gradio.live URL
//      by asking you to paste it. Saves it and returns it.
//
// WHY NOT FULLY HEADLESS: Chrome profile lock prevents Playwright from using
// your logged-in Google session while Chrome is running. This approach is
// simpler and 100% reliable.

const fs      = require('fs');
const path    = require('path');
const https   = require('https');
const http    = require('http');
const readline = require('readline');

// ─────────────────────────────────────────────
// CONFIGURATION
// ─────────────────────────────────────────────

// Your permanent Colab notebook link (never changes)
const COLAB_NOTEBOOK_URL =
    'https://colab.research.google.com/drive/1uV6ZIqg3M9mwi-9Leplkmntn94rKEh9S#scrollTo=code-cell-2';

// Local file where the latest live Gradio URL is persisted
const URL_CACHE_FILE = path.join(__dirname, 'colab_url.json');

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function readCachedUrl() {
    try {
        if (fs.existsSync(URL_CACHE_FILE)) {
            const data = JSON.parse(fs.readFileSync(URL_CACHE_FILE, 'utf8'));
            return data.gradioUrl || null;
        }
    } catch (_) {}
    return null;
}

function saveCachedUrl(url) {
    fs.writeFileSync(URL_CACHE_FILE, JSON.stringify({
        gradioUrl: url,
        savedAt: new Date().toISOString()
    }, null, 2));
    console.log(`💾  Saved new Gradio URL to ${URL_CACHE_FILE}`);
}

/**
 * Pings the Gradio URL to check if the server is alive.
 * Returns true if HTTP response is received within 10 seconds (not 5xx).
 */
function pingUrl(url) {
    return new Promise((resolve) => {
        try {
            const parsed = new URL(url);
            const lib    = parsed.protocol === 'https:' ? https : http;
            const req    = lib.get(url, { timeout: 10000 }, (res) => {
                // Gradio returns 200 when alive; dead servers return 502/503
                resolve(res.statusCode < 500);
            });
            req.on('error', () => resolve(false));
            req.on('timeout', () => { req.destroy(); resolve(false); });
        } catch (_) {
            resolve(false);
        }
    });
}

/**
 * Opens the Colab notebook in the user's default browser and prompts
 * for the new gradio.live URL via the terminal.
 */
async function relaunchColab() {
    console.log('\n══════════════════════════════════════════════════════');
    console.log('🤖  Colab TTS server is DOWN — need a fresh URL.');
    console.log('══════════════════════════════════════════════════════');
    console.log('');
    console.log('Opening your Colab notebook in the browser now...');
    console.log('');

    // Open the Colab notebook in the default browser
    const { exec } = require('child_process');
    exec(`start "" "${COLAB_NOTEBOOK_URL}"`);

    console.log('📋  Please do the following:');
    console.log('   1. In the Colab tab, click Runtime → Run all');
    console.log('   2. Wait for the model to load (~3-4 minutes)');
    console.log('   3. Copy the gradio.live URL from the output');
    console.log('   4. Paste it below and press Enter');
    console.log('');

    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    return new Promise((resolve, reject) => {
        const askForUrl = () => {
            rl.question('🔗  Paste the new gradio.live URL here: ', async (input) => {
                const url = input.trim().replace(/\/$/, ''); // strip trailing slash

                if (!url.includes('gradio.live')) {
                    console.log('❌  That doesn\'t look like a gradio.live URL. Try again.\n');
                    askForUrl();
                    return;
                }

                // Verify it's actually alive
                process.stdout.write('🔍  Verifying URL is live... ');
                const alive = await pingUrl(url);

                if (!alive) {
                    console.log('❌  Server not responding yet. Wait a bit and try again.\n');
                    askForUrl();
                    return;
                }

                console.log('✅  Server is live!');
                saveCachedUrl(url);
                rl.close();
                resolve(url);
            });
        };
        askForUrl();
    });
}

// ─────────────────────────────────────────────
// MAIN EXPORT
// ─────────────────────────────────────────────

/**
 * Returns a guaranteed-live Gradio URL.
 * If the cached URL is healthy, returns it instantly.
 * If dead/missing, opens the Colab notebook and prompts for the new URL.
 *
 * @returns {Promise<string>} A live gradio.live URL
 */
async function getLiveColabUrl() {
    const cached = readCachedUrl();

    if (cached) {
        process.stdout.write(`🔗  Checking cached Colab URL... `);
        const alive = await pingUrl(cached);
        if (alive) {
            console.log('✅  Server is live!');
            return cached;
        }
        console.log('❌  Server is down.');
    } else {
        console.log('📋  No cached URL found.');
    }

    return relaunchColab();
}

module.exports = { getLiveColabUrl };
