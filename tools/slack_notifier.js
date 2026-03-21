/**
 * slack_notifier.js
 * Sends Slack messages for the AXIOM pipeline.
 *
 * Required env vars (add to config/.env):
 *   SLACK_BOT_TOKEN=xoxb-...
 *   SLACK_CHANNEL_ID=C0XXXXXXXXX
 *
 * All functions are silent no-ops if the token is missing —
 * so the pipeline never breaks if Slack isn't configured.
 */

const fs   = require('fs');
const path = require('path');

const STATE_FILE = path.join(__dirname, '../config/scheduler_state.json');

function getConfig() {
    return {
        token:   process.env.SLACK_BOT_TOKEN   || null,
        channel: process.env.SLACK_CHANNEL_ID  || null,
    };
}

function loadState() {
    try {
        if (fs.existsSync(STATE_FILE))
            return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    } catch (_) {}
    return {};
}

function saveState(patch) {
    const current = loadState();
    const next    = { ...current, ...patch };
    try {
        fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
        fs.writeFileSync(STATE_FILE, JSON.stringify(next, null, 2), 'utf8');
    } catch (_) {}
}

async function slackPost(endpoint, body, token) {
    const res = await fetch(`https://slack.com/api/${endpoint}`, {
        method:  'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type':  'application/json',
        },
        body: JSON.stringify(body),
    });
    return res.json();
}

/**
 * Send an immediate Slack message to the configured channel.
 * Silent no-op if SLACK_BOT_TOKEN / SLACK_CHANNEL_ID not set.
 */
async function notify(text) {
    const { token, channel } = getConfig();
    if (!token || !channel) {
        console.log('[Slack] Not configured — skipping notification.');
        return;
    }
    try {
        const result = await slackPost('chat.postMessage', { channel, text }, token);
        if (!result.ok) console.warn(`[Slack] postMessage failed: ${result.error}`);
    } catch (err) {
        console.warn(`[Slack] notify error: ${err.message}`);
    }
}

/**
 * Pre-schedule a "open your laptop" reminder for today's upload time.
 * Only schedules if the time is still in the future.
 * Saves scheduled_message_id to scheduler_state.json so it can be cancelled later.
 */
async function scheduleReminder(uploadHourIST) {
    const { token, channel } = getConfig();
    if (!token || !channel) return;

    try {
        // Calculate Unix timestamp for today at uploadHourIST in IST (UTC+5:30)
        const now = new Date();
        const istOffsetMs = (5 * 60 + 30) * 60 * 1000;
        const nowIST = new Date(now.getTime() + istOffsetMs);

        // Build today's upload time in IST as UTC
        const targetIST = new Date(nowIST);
        targetIST.setUTCHours(uploadHourIST, 0, 0, 0);
        const targetUTC = new Date(targetIST.getTime() - istOffsetMs);

        // Only schedule if the time is still at least 60 seconds away
        if (targetUTC.getTime() - now.getTime() < 60 * 1000) {
            console.log('[Slack] Reminder time already passed — skipping schedule.');
            return;
        }

        const post_at = Math.floor(targetUTC.getTime() / 1000);
        const text = `⚠️ *AXIOM Agent reminder:* Today's video hasn't been uploaded yet.\nYour laptop may be offline. Please open it so the pipeline can run!`;

        const result = await slackPost('chat.scheduleMessage', { channel, text, post_at }, token);

        if (result.ok) {
            saveState({
                scheduledMsgId:      result.scheduled_message_id,
                scheduledMsgChannel: channel,
            });
            const timeIST = `${uploadHourIST}:00 IST`;
            console.log(`[Slack] Reminder scheduled for ${timeIST} (id: ${result.scheduled_message_id})`);
        } else {
            console.warn(`[Slack] scheduleMessage failed: ${result.error}`);
        }
    } catch (err) {
        console.warn(`[Slack] scheduleReminder error: ${err.message}`);
    }
}

/**
 * Cancel the pre-scheduled reminder (call this when upload starts).
 * Reads the scheduled_message_id from scheduler_state.json.
 * Silent no-op if no reminder is scheduled or token missing.
 */
async function cancelReminder() {
    const { token } = getConfig();
    if (!token) return;

    const state = loadState();
    const { scheduledMsgId, scheduledMsgChannel } = state;
    if (!scheduledMsgId || !scheduledMsgChannel) return;

    try {
        const result = await slackPost('chat.deleteScheduledMessage', {
            channel:               scheduledMsgChannel,
            scheduled_message_id:  scheduledMsgId,
        }, token);

        if (result.ok) {
            console.log(`[Slack] Reminder cancelled (id: ${scheduledMsgId})`);
            saveState({ scheduledMsgId: null, scheduledMsgChannel: null });
        } else {
            // 'invalid_scheduled_message_id' just means it already fired — not an error
            if (result.error !== 'invalid_scheduled_message_id') {
                console.warn(`[Slack] cancelReminder failed: ${result.error}`);
            }
            saveState({ scheduledMsgId: null, scheduledMsgChannel: null });
        }
    } catch (err) {
        console.warn(`[Slack] cancelReminder error: ${err.message}`);
    }
}

module.exports = { notify, scheduleReminder, cancelReminder };
