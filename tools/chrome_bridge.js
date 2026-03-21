/**
 * chrome_bridge.js
 *
 * Launches a SEPARATE automation Chrome instance using .automation_profile/
 * so we never kill the user's regular Chrome. Chrome requires a non-default
 * user-data-dir for --remote-debugging-port to work.
 *
 * Flow:
 *  1. Try to connect to existing automation Chrome on port 9222
 *  2. If not running, launch Chrome with .automation_profile/ + debug port
 *  3. Return a Puppeteer browser/page ready to use
 *
 * This file exposes: getPage(), getBrowser(), relaunchChromeWithDebugPort()
 */

const puppeteer = require('puppeteer');
const path      = require('path');
const { execSync, spawn } = require('child_process');

const CHROME_EXE       = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
// Use dedicated automation profile dir — Chrome blocks debug port on the default dir
const AUTO_USER_DATA   = path.resolve(__dirname, '..', '.automation_profile');
const AUTO_PROFILE     = 'Default';
const DEBUG_PORT       = 9222;

// ── Connect to existing automation Chrome ────────────────────────────────────

async function connectToChrome() {
    console.log(`🔌 Connecting to Chrome on port ${DEBUG_PORT}...`);
    try {
        const res = await fetch(`http://localhost:${DEBUG_PORT}/json/version`, {
            signal: AbortSignal.timeout(3000)
        });
        if (!res.ok) throw new Error('Not reachable');
        const info = await res.json();
        console.log(`✅ Found Chrome: ${info.Browser}`);

        const browser = await puppeteer.connect({
            browserURL: `http://localhost:${DEBUG_PORT}`,
            defaultViewport: null
        });
        return browser;
    } catch (err) {
        console.log(`ℹ️  Chrome not running with debug port: ${err.message}`);
        return null;
    }
}

// ── Main export: getBrowser() ────────────────────────────────────────────────

let cachedBrowser = null;

async function getBrowser() {
    // Health check: verify cached browser is still alive
    if (cachedBrowser) {
        try {
            if (cachedBrowser.connected) {
                await cachedBrowser.pages(); // Throws if truly dead
                console.log('✅ Reusing cached browser instance');
                return cachedBrowser;
            }
        } catch (_) {
            console.log('⚠️  Cached browser is dead, reconnecting...');
            cachedBrowser = null;
        }
    }

    // Try connecting to already-running automation Chrome
    const connected = await connectToChrome();
    if (connected) {
        console.log('✅ Connected to running automation Chrome');
        cachedBrowser = connected;
        return connected;
    }

    // Auto-launch a new automation Chrome
    console.log('🔄 Automation Chrome not running. Launching...');
    const launched = await relaunchChromeWithDebugPort();
    if (!launched) {
        throw new Error('Failed to launch automation Chrome. Check that Chrome is installed and .automation_profile/ exists.');
    }

    const retryConnected = await connectToChrome();
    if (!retryConnected) {
        throw new Error('Automation Chrome launched but could not connect via debug port.');
    }
    console.log('✅ Connected to freshly launched automation Chrome');
    cachedBrowser = retryConnected;
    return cachedBrowser;
}

// ── getPage(): Get a Puppeteer page for NotebookLM ──────────────────────────

async function getPage() {
    const browser = await getBrowser();
    const pages   = await browser.pages();

    // 1. Try to find an existing NotebookLM tab
    let page = pages.find(p => p.url().includes('notebooklm.google.com'));

    if (page) {
        console.log('✅ Reusing existing NotebookLM tab');
        await page.bringToFront();
    } else {
        // Reuse first blank page if available to avoid extra tabs
        if (pages.length > 0 && pages[0].url() === 'about:blank') {
            page = pages[0];
        } else {
            console.log('🆕 Opening new NotebookLM tab');
            page = await browser.newPage();
        }

        await page.setDefaultNavigationTimeout(90000);

        // Pre-emptive "Restore" dismissal (Aggressive)
        console.log('🧹 Brushing away startup bubbles...');
        await new Promise(r => setTimeout(r, 5000)); // Let bubbles appear
        try { await page.evaluate(() => {
            const allElements = Array.from(document.querySelectorAll('button, div, span'));
            const restore = allElements.find(el => el.innerText && el.innerText.includes('Restore'));
            const close = allElements.find(el => el.getAttribute('aria-label')?.includes('Close') || el.innerText === '✕');
            if (restore) { restore.click(); console.log('Killed Restore bubble'); }
            if (close) { close.click(); }
        }).catch(() => {}); } catch(_) {}

        // Navigation with Retry for "Site can't be reached"
        let success = false;
        for (let i = 0; i < 3; i++) {
            try {
                await page.goto('https://notebooklm.google.com', { waitUntil: 'domcontentloaded', timeout: 90000 });
                // Second pass dismissal
                await page.evaluate(() => {
                    const all = Array.from(document.querySelectorAll('button, div, span'));
                    const r = all.find(el => el.innerText && el.innerText.includes('Restore'));
                    if (r) r.click();
                }).catch(() => {});
                success = true;
                break;
            } catch (e) {
                console.warn(`⚠️  Navigation attempt ${i+1} failed: ${e.message}. Retrying...`);
                await new Promise(r => setTimeout(r, 8000));
            }
        }
        if (!success) throw new Error('Could not reach NotebookLM after 3 attempts.');
    }

    // Set download behaviour via CDP
    try {
        const client = await page.createCDPSession();
        await client.send('Page.setDownloadBehavior', {
            behavior:     'allow',
            downloadPath: 'D:\\notebook lm\\output\\notebooklm_raw'
        });
    } catch (_) {}

    page.setDefaultNavigationTimeout(90000);
    return { page, browser };
}

// ── Launch automation Chrome with debug port ─────────────────────────────────
// Uses .automation_profile/ (non-default dir) so Chrome allows remote debugging.
// Does NOT kill the user's regular Chrome — runs as a separate instance.

async function relaunchChromeWithDebugPort() {
    console.log('\n🔄 Launching automation Chrome with remote debugging...');
    console.log(`   Profile: ${AUTO_USER_DATA}`);

    // Only kill automation Chrome instances on port 9222, not the user's browser.
    // We do this by checking if port 9222 is in use and killing that specific process.
    try {
        const netstat = execSync('netstat -ano | findstr :9222 | findstr LISTENING', { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] });
        const pidMatch = netstat.match(/\s(\d+)\s*$/m);
        if (pidMatch) {
            console.log(`   Killing stale automation Chrome (PID ${pidMatch[1]})...`);
            try { execSync(`taskkill /F /PID ${pidMatch[1]}`, { stdio: 'ignore' }); } catch (_) {}
            await new Promise(r => setTimeout(r, 2000));
        }
    } catch (_) {
        // No process on port 9222 — good
    }

    const chromeArgs = [
        `--remote-debugging-port=${DEBUG_PORT}`,
        `--user-data-dir=${AUTO_USER_DATA}`,
        `--profile-directory=${AUTO_PROFILE}`,
        '--no-first-run',
        '--no-default-browser-check'
    ];

    const proc = spawn(CHROME_EXE, chromeArgs, {
        detached: true, stdio: 'ignore', shell: false, windowsHide: false
    });
    proc.on('error', e => console.error('Chrome spawn error:', e.message));
    proc.unref();

    // Wait for Chrome to boot up
    console.log('⏳ Waiting for automation Chrome to start...');
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 1000));
        try {
            const res = await fetch(`http://localhost:${DEBUG_PORT}/json/version`, {
                signal: AbortSignal.timeout(2000)
            });
            if (res.ok) {
                console.log('✅ Automation Chrome debug port is ready!');
                return true;
            }
        } catch (_) {}
    }
    console.error('❌ Automation Chrome did not start in time');
    return false;
}

module.exports = { getPage, getBrowser, relaunchChromeWithDebugPort };
