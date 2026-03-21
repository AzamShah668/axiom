/**
 * scheduler.js
 * Auto-Pilot: runs the pipeline once per day at the optimal upload time.
 *
 * Optimal time logic:
 *   - Default: 6 PM IST (18:00) — research-backed best time for Indian edu content
 *   - As channel grows, override via the dashboard to match real audience activity
 *
 * State is persisted to config/scheduler_state.json so it survives server restarts.
 */

const cron = require('node-cron');
const path = require('path');
const fs   = require('fs');

const { startFromNotion } = require('../orchestrator/run_pipeline');

const STATE_FILE = path.join(__dirname, '../../config/scheduler_state.json');

// IST = UTC+5:30
const IST_OFFSET_HOURS   = 5;
const IST_OFFSET_MINUTES = 30;

function istToUtc(hourIST) {
    let totalMinutes = hourIST * 60 - (IST_OFFSET_HOURS * 60 + IST_OFFSET_MINUTES);
    if (totalMinutes < 0) totalMinutes += 24 * 60;
    return { hour: Math.floor(totalMinutes / 60) % 24, minute: totalMinutes % 60 };
}

function getNextRunISO(hourIST) {
    const { hour, minute } = istToUtc(hourIST);
    const now  = new Date();
    const next = new Date(now);
    next.setUTCHours(hour, minute, 0, 0);
    if (next <= now) next.setUTCDate(next.getUTCDate() + 1);
    return next.toISOString();
}

function formatIST(isoString) {
    if (!isoString) return null;
    const d = new Date(isoString);
    const ist = new Date(d.getTime() + (5 * 60 + 30) * 60000);
    return ist.toISOString().replace('T', ' ').slice(0, 16) + ' IST';
}

function loadState() {
    try {
        if (fs.existsSync(STATE_FILE))
            return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    } catch (_) {}
    return {
        enabled:        false,
        stream:         'BTech',
        uploadHourIST:  18,       // 6 PM IST default
        lastRun:        null,
        lastStatus:     null,
        nextRun:        null,
    };
}

function saveState(state) {
    try {
        fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
        fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf8');
    } catch (_) {}
}

let cronJob  = null;
let logFn    = null;

function log(msg) {
    if (logFn) logFn(`[AUTO-PILOT] ${msg}`);
    else console.log(`[AUTO-PILOT] ${msg}`);
}

function startCron(stream, uploadHourIST) {
    if (cronJob) { cronJob.stop(); cronJob = null; }

    const { hour, minute } = istToUtc(uploadHourIST);
    const expr = `${minute} ${hour} * * *`;  // once per day at UTC equivalent

    cronJob = cron.schedule(expr, async () => {
        const state = loadState();
        state.lastRun    = new Date().toISOString();
        state.lastStatus = 'running';
        state.nextRun    = getNextRunISO(uploadHourIST);
        saveState(state);

        log(`Running daily pipeline — stream: ${stream}`);

        try {
            await startFromNotion(stream);
            state.lastStatus = 'success';
            log('Pipeline completed successfully');
        } catch (err) {
            state.lastStatus = `failed: ${err.message}`;
            log(`Pipeline failed: ${err.message}`);
        }

        saveState(state);
    }, { timezone: 'UTC' });

    log(`Scheduled — daily at ${uploadHourIST}:00 IST (${hour}:${String(minute).padStart(2,'0')} UTC)`);
}

// ── Public API ────────────────────────────────────────────────────────────────

function enable(stream, uploadHourIST, onLog) {
    logFn = onLog || null;
    const state = {
        enabled:       true,
        stream,
        uploadHourIST,
        lastRun:       loadState().lastRun,
        lastStatus:    loadState().lastStatus,
        nextRun:       getNextRunISO(uploadHourIST),
    };
    saveState(state);
    startCron(stream, uploadHourIST);
    return getStatus();
}

function disable() {
    if (cronJob) { cronJob.stop(); cronJob = null; }
    const state = { ...loadState(), enabled: false, nextRun: null };
    saveState(state);
    log('Auto-Pilot disabled');
    return getStatus();
}

function getStatus() {
    const s = loadState();
    return {
        ...s,
        nextRunFormatted: formatIST(s.nextRun),
        lastRunFormatted: formatIST(s.lastRun),
    };
}

/** Returns true if two ISO timestamps fall on the same calendar day in IST (UTC+5:30). */
function isSameDayIST(isoA, isoB) {
    const toIST = d => new Date(new Date(d).getTime() + (5 * 60 + 30) * 60000);
    const a = toIST(isoA);
    const b = toIST(isoB);
    return a.getUTCFullYear() === b.getUTCFullYear() &&
           a.getUTCMonth()    === b.getUTCMonth()    &&
           a.getUTCDate()     === b.getUTCDate();
}

/** Call once on server startup to resume if Auto-Pilot was enabled. */
function init(onLog) {
    logFn = onLog || null;
    const state = loadState();
    if (!state.enabled) return;

    startCron(state.stream, state.uploadHourIST);
    log(`Resumed — next run: ${formatIST(getNextRunISO(state.uploadHourIST))}`);

    // ── Catch-up: run immediately if today's upload was missed ──────────────
    // e.g. scheduled for 4 PM IST but laptop was closed; user opens at 6 PM.
    const now = new Date();
    const { hour: utcHour, minute: utcMin } = istToUtc(state.uploadHourIST);
    const scheduledTodayUTC = new Date(now);
    scheduledTodayUTC.setUTCHours(utcHour, utcMin, 0, 0);

    const didRunToday     = state.lastRun && isSameDayIST(state.lastRun, now.toISOString());
    const scheduledPassed = now > scheduledTodayUTC;

    if (!didRunToday && scheduledPassed) {
        log('Missed upload detected — catch-up run will start in 60 seconds...');
        setTimeout(async () => {
            // Re-read state: guard against disable between startup and this callback
            const s = loadState();
            if (!s.enabled) { log('Catch-up cancelled — Auto-Pilot was disabled.'); return; }
            if (s.lastRun && isSameDayIST(s.lastRun, new Date().toISOString())) {
                log('Catch-up cancelled — already uploaded today.');
                return;
            }

            s.lastRun    = new Date().toISOString();
            s.lastStatus = 'running';
            s.nextRun    = getNextRunISO(s.uploadHourIST);
            saveState(s);
            log(`Running catch-up pipeline — stream: ${s.stream}`);

            try {
                await startFromNotion(s.stream);
                s.lastStatus = 'success';
                log('Catch-up pipeline completed successfully');
            } catch (err) {
                s.lastStatus = `failed: ${err.message}`;
                log(`Catch-up pipeline failed: ${err.message}`);
            }
            saveState(s);
        }, 60 * 1000);
    }
}

module.exports = { enable, disable, getStatus, init };
