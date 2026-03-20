/**
 * chrome_bridge.js
 * 
 * The Problem: Chrome locks its profile directory when running.
 * Puppeteer can't use `userDataDir` pointing to an active Chrome session.
 * 
 * The Solution (2 modes):
 * 
 * MODE A — Fresh Chrome with debug port (RECOMMENDED):
 *   Kills existing Chrome, relaunches it with --remote-debugging-port=9222
 *   Puppeteer then connects to it via CDP (Chrome DevTools Protocol)
 *   Your session/cookies/login are preserved because we still use your profile dir
 *
 * MODE B — Puppeteer launches its own Chrome with a COPY of your profile:
 *   Copies your Profile 4 to a temp dir (so Chrome doesn't fight over the lock)
 *   Puppeteer runs its own Chrome with the copied session
 *   ⚠️  Slower (copy takes time) but doesn't require killing Chrome
 *
 * This file exposes: getPage() → returns a Puppeteer page ready to use
 */

const puppeteer = require('puppeteer');
const { execSync, spawn } = require('child_process');
const fs   = require('fs');
const path = require('path');

const CHROME_EXE       = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const CHROME_USER_DATA = 'C:\\Users\\AZAM RIZWAN\\AppData\\Local\\Google\\Chrome\\User Data';
const CHROME_PROFILE   = 'Profile 4';
const DEBUG_PORT       = 9222;
const TEMP_PROFILE_DIR = path.join(require('os').tmpdir(), 'axiom_chrome_profile');

// ── Mode A: Connect to existing Chrome (after relaunch with debug port) ────────

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

// ── Mode B: Copy profile to temp, launch isolated Puppeteer Chrome ────────────

async function launchWithProfileCopy() {
    const srcProfile = path.join(CHROME_USER_DATA, CHROME_PROFILE);
    const dstProfile = path.join(TEMP_PROFILE_DIR, CHROME_PROFILE);
    const dstUserData = TEMP_PROFILE_DIR;

    // Copy only if not already recent (saves time on repeated runs)
    const lockFile = path.join(dstProfile, 'lockfile');
    const needsCopy = !fs.existsSync(dstProfile) ||
                      (Date.now() - fs.statSync(dstProfile).ctimeMs > 30 * 60 * 1000);

    if (needsCopy) {
        console.log(`📋 Copying Chrome profile to temp dir...`);
        console.log(`   From: ${srcProfile}`);
        console.log(`   To:   ${dstProfile}`);
        if (fs.existsSync(dstProfile)) {
            fs.rmSync(dstProfile, { recursive: true, force: true });
        }
        // Use robocopy on Windows for fast directory copy
        try {
            execSync(`robocopy "${srcProfile}" "${dstProfile}" /E /NFL /NDL /NJH /NJS /nc /ns /np`, 
                     { stdio: 'ignore' });
        } catch (_) {
            // robocopy returns exit code 1 on success (at least 1 file copied), ignore
        }
        // Remove the lock file so Chrome can start fresh
        if (fs.existsSync(lockFile)) fs.unlinkSync(lockFile);
        console.log(`✅ Profile copied`);
    } else {
        console.log(`✅ Using cached profile copy (< 30 min old)`);
    }

    const browser = await puppeteer.launch({
        headless: false,
        executablePath: CHROME_EXE,
        userDataDir: dstUserData,
        args: [
            `--profile-directory=${CHROME_PROFILE}`,
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--start-maximized'
        ],
        defaultViewport: null
    });

    return browser;
}

// ── Main export: getPage() ────────────────────────────────────────────────────

let cachedBrowser = null;

async function getBrowser() {
    if (cachedBrowser) {
        console.log('✅ Reusing cached browser instance');
        return cachedBrowser;
    }

    // Try Mode A first (fastest, preserves live session)
    const connected = await connectToChrome();
    if (connected) {
        console.log('✅ Mode A: Connected to your running Chrome');
        cachedBrowser = connected;
        return connected;
    }

    // Fall back to Mode B (profile copy)
    console.log('🔄 Mode B: Launching isolated Chrome with profile copy...');
    cachedBrowser = await launchWithProfileCopy();
    return cachedBrowser;
}

async function getPage() {
    const browser = await getBrowser();
    const pages   = await browser.pages();
    
    // 1. Try to find an existing NotebookLM tab
    let page = pages.find(p => p.url().includes('notebooklm.google.com'));
    
    if (page) {
        console.log('✅ Reusing existing NotebookLM tab');
        await page.bringToFront();
    } else {
        console.log('🆕 Opening new NotebookLM tab');
        page = await browser.newPage();
        await page.goto('https://notebooklm.google.com', { waitUntil: 'domcontentloaded', timeout: 30000 });
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

// ── Helper: Relaunch Chrome with debug port ───────────────────────────────────
// Run this ONCE before the pipeline starts — it opens a regular Chrome window
// with remote debugging enabled so Puppeteer can control it.

async function relaunchChromeWithDebugPort() {
    console.log('\n🔄 Relaunching Chrome with remote debugging enabled...');
    
    // Kill all existing Chrome instances
    try { execSync('taskkill /F /IM chrome.exe', { stdio: 'ignore' }); } catch (_) {}
    await new Promise(r => setTimeout(r, 2000));

    // Relaunch with the debug port + your profile
    const chromeArgs = [
        `--remote-debugging-port=${DEBUG_PORT}`,
        `--user-data-dir=${CHROME_USER_DATA}`,
        `--profile-directory=${CHROME_PROFILE}`,
        '--no-first-run',
        '--no-default-browser-check'
    ];
    spawn(CHROME_EXE, chromeArgs, { detached: true, stdio: 'ignore' }).unref();
    
    // Wait for Chrome to boot up
    console.log('⏳ Waiting for Chrome to start...');
    for (let i = 0; i < 15; i++) {
        await new Promise(r => setTimeout(r, 1000));
        try {
            const res = await fetch(`http://localhost:${DEBUG_PORT}/json/version`, {
                signal: AbortSignal.timeout(2000)
            });
            if (res.ok) {
                console.log('✅ Chrome debug port is ready!');
                return true;
            }
        } catch (_) {}
    }
    console.error('❌ Chrome did not start in time');
    return false;
}

module.exports = { getPage, getBrowser, relaunchChromeWithDebugPort };
