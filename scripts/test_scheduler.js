/**
 * test_scheduler.js
 * Tests the catch-up detection logic without running the real pipeline.
 * Uses a mock startFromNotion that just logs instead of doing anything.
 *
 * Run: node scripts/test_scheduler.js
 */

const IST_OFFSET_HOURS   = 5;
const IST_OFFSET_MINUTES = 30;

// ── Helpers (copied from scheduler.js to test in isolation) ──────────────────

function istToUtc(hourIST) {
    let totalMinutes = hourIST * 60 - (IST_OFFSET_HOURS * 60 + IST_OFFSET_MINUTES);
    if (totalMinutes < 0) totalMinutes += 24 * 60;
    return { hour: Math.floor(totalMinutes / 60) % 24, minute: totalMinutes % 60 };
}

function isSameDayIST(isoA, isoB) {
    const toIST = d => new Date(new Date(d).getTime() + (5 * 60 + 30) * 60000);
    const a = toIST(isoA);
    const b = toIST(isoB);
    return a.getUTCFullYear() === b.getUTCFullYear() &&
           a.getUTCMonth()    === b.getUTCMonth()    &&
           a.getUTCDate()     === b.getUTCDate();
}

function shouldCatchup(state, now) {
    const { hour: utcHour, minute: utcMin } = istToUtc(state.uploadHourIST);
    const scheduledTodayUTC = new Date(now);
    scheduledTodayUTC.setUTCHours(utcHour, utcMin, 0, 0);
    const didRunToday     = state.lastRun && isSameDayIST(state.lastRun, now.toISOString());
    const scheduledPassed = now > scheduledTodayUTC;
    return !didRunToday && scheduledPassed;
}

// ── Unit Tests ────────────────────────────────────────────────────────────────

let passed = 0; let failed = 0;
function test(name, result, expected) {
    const ok = result === expected;
    console.log(`  ${ok ? '✅' : '❌'} ${name}: got ${result}, expected ${expected}`);
    if (ok) passed++; else failed++;
}

console.log('\n── isSameDayIST tests ──────────────────────────────');

// Same moment → same day
test('same timestamp',
    isSameDayIST('2026-03-22T10:00:00.000Z', '2026-03-22T10:00:00.000Z'), true);

// 11:59 PM UTC → 5:29 AM IST next day — crosses midnight in IST
const justBeforeMidnightUTC  = '2026-03-21T18:29:59.000Z'; // 23:59 IST on 21st
const justAfterMidnightIST   = '2026-03-21T18:30:00.000Z'; // 00:00 IST on 22nd
test('IST midnight boundary (different days)',
    isSameDayIST(justBeforeMidnightUTC, justAfterMidnightIST), false);

// Both in IST same day
test('same IST day, different UTC hours',
    isSameDayIST('2026-03-22T01:00:00.000Z', '2026-03-22T15:00:00.000Z'), true);

// Yesterday vs today
test('yesterday vs today',
    isSameDayIST('2026-03-21T12:00:00.000Z', '2026-03-22T12:00:00.000Z'), false);

console.log('\n── istToUtc conversion tests ───────────────────────');

const ist18 = istToUtc(18); // 6 PM IST = 12:30 UTC
test('18:00 IST → 12:30 UTC (hour)',   ist18.hour,   12);
test('18:00 IST → 12:30 UTC (minute)', ist18.minute, 30);

const ist0 = istToUtc(0); // 12 AM IST = 18:30 UTC previous day
test('00:00 IST → 18:30 UTC (hour)',   ist0.hour,   18);
test('00:00 IST → 18:30 UTC (minute)', ist0.minute, 30);

console.log('\n── Catch-up detection tests ────────────────────────');

// Scenario 1: Missed — enabled, never ran, schedule time passed
const nowIST10PM = new Date('2026-03-22T16:30:00.000Z'); // 22:00 IST
test('SHOULD catch-up: enabled, never ran, schedule passed (18 IST)',
    shouldCatchup({ enabled: true, uploadHourIST: 18, lastRun: null }, nowIST10PM), true);

// Scenario 2: Already ran today
test('should NOT catch-up: already ran today',
    shouldCatchup({ enabled: true, uploadHourIST: 18, lastRun: '2026-03-22T13:00:00.000Z' }, nowIST10PM), false);

// Scenario 3: Schedule hasn't passed yet (it's 11 AM IST, schedule is 6 PM IST)
const nowIST11AM = new Date('2026-03-22T05:30:00.000Z'); // 11:00 IST
test('should NOT catch-up: schedule not yet reached today',
    shouldCatchup({ enabled: true, uploadHourIST: 18, lastRun: null }, nowIST11AM), false);

// Scenario 4: Ran yesterday, schedule already passed today → catch-up
const lastRunYesterday = '2026-03-21T13:00:00.000Z'; // yesterday at 6:30 PM IST
test('SHOULD catch-up: ran yesterday, missed today',
    shouldCatchup({ enabled: true, uploadHourIST: 18, lastRun: lastRunYesterday }, nowIST10PM), true);

// ── Live Mock Test ────────────────────────────────────────────────────────────
console.log('\n── Live catch-up mock (2 second delay) ─────────────');

// Simulate: enabled, schedule at hour=0 (midnight IST = 18:30 UTC yesterday), lastRun=null
// On any machine, midnight IST has always passed by the time you run this test
const mockState = {
    enabled: true,
    stream: 'BTech',
    uploadHourIST: 0,   // midnight IST — guaranteed to have passed today
    lastRun: null,
    lastStatus: null,
};

const now = new Date();
const { hour: utcH, minute: utcM } = istToUtc(mockState.uploadHourIST);
const scheduled = new Date(now);
scheduled.setUTCHours(utcH, utcM, 0, 0);

const didRunToday     = mockState.lastRun && isSameDayIST(mockState.lastRun, now.toISOString());
const scheduledPassed = now > scheduled;

console.log(`  State: enabled=true, uploadHourIST=0, lastRun=null`);
console.log(`  Now: ${now.toISOString()}`);
console.log(`  Scheduled UTC: ${scheduled.toISOString()}`);
console.log(`  didRunToday: ${didRunToday}`);
console.log(`  scheduledPassed: ${scheduledPassed}`);

if (!didRunToday && scheduledPassed) {
    console.log('  Detected: MISSED UPLOAD — scheduling catch-up in 2 seconds (mock)...');
    setTimeout(() => {
        console.log('\n  🚀 [MOCK PIPELINE] startFromNotion("BTech") called — would upload here');
        console.log('  ✅ Catch-up fired correctly!\n');

        console.log(`── Results ──────────────────────────────────────────`);
        console.log(`   Passed: ${passed + 1}  Failed: ${failed}`);
        if (failed === 0) console.log('   ALL TESTS PASSED\n');
        else console.log(`   ${failed} TEST(S) FAILED\n`);
    }, 2000);
} else {
    console.log('  ❌ Catch-up was NOT triggered (unexpected)');
    console.log(`\n── Results ──`);
    console.log(`   Passed: ${passed}  Failed: ${failed + 1}`);
}
