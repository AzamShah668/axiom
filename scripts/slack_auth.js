/**
 * slack_auth.js
 * One-click Slack OAuth: starts a local server, opens the auth URL,
 * captures the token automatically, and saves it to config/.env
 *
 * Run: node scripts/slack_auth.js
 */

require('dotenv').config({ path: require('path').join(__dirname, '../config/.env') });
const http = require('http');
const fs   = require('fs');
const path = require('path');

const CLIENT_ID     = '10242244537954.10753356141540';
const CLIENT_SECRET = '94b4b7e77a7339735a3b7f85ca4abf5a';
const REDIRECT_URI  = 'http://localhost:3002/slack/oauth';
const ENV_FILE      = path.join(__dirname, '../config/.env');
const SCOPES        = 'chat:write,chat:write.public,chat:scheduleMessage';

const authUrl = `https://slack.com/oauth/v2/authorize?client_id=${CLIENT_ID}&scope=${SCOPES}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`;

console.log('\n=== AXIOM Slack OAuth ===');
console.log('\nOpen this URL in your browser to authorize the Slack app:\n');
console.log(authUrl);
console.log('\nWaiting for authorization...\n');

const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost:3002');
    if (url.pathname !== '/slack/oauth') { res.end('Not found'); return; }

    const code  = url.searchParams.get('code');
    const error = url.searchParams.get('error');

    if (error) {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`<h2>❌ Authorization denied: ${error}</h2><p>You can close this tab.</p>`);
        console.error(`\n❌ Auth denied: ${error}`);
        server.close();
        return;
    }

    if (!code) {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end('<h2>❌ No code received</h2>');
        server.close();
        return;
    }

    // Exchange code for token
    console.log('Code received — exchanging for token...');
    try {
        const params = new URLSearchParams({
            client_id:     CLIENT_ID,
            client_secret: CLIENT_SECRET,
            code,
            redirect_uri:  REDIRECT_URI,
        });

        const tokenRes  = await fetch(`https://slack.com/api/oauth.v2.access`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body:    params.toString(),
        });
        const tokenData = await tokenRes.json();

        if (!tokenData.ok) {
            throw new Error(tokenData.error);
        }

        const botToken = tokenData.access_token;
        console.log(`\n✅ Bot token received: ${botToken.slice(0, 20)}...`);

        // Save to config/.env
        let envContent = fs.readFileSync(ENV_FILE, 'utf8');
        if (envContent.includes('SLACK_BOT_TOKEN=')) {
            envContent = envContent.replace(/SLACK_BOT_TOKEN=.*/, `SLACK_BOT_TOKEN=${botToken}`);
        } else {
            envContent += `\nSLACK_BOT_TOKEN=${botToken}`;
        }
        fs.writeFileSync(ENV_FILE, envContent, 'utf8');

        console.log('✅ Token saved to config/.env');
        console.log('\nYou can close the browser tab now.');

        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`
            <html><body style="font-family:sans-serif;padding:2rem;background:#0d1117;color:#e6edf3">
            <h2>✅ AXIOM Slack connected!</h2>
            <p>Bot token saved. You can close this tab.</p>
            </body></html>
        `);

        server.close(() => {
            console.log('\n--- Testing the connection ---');
            testSlack(botToken);
        });

    } catch (err) {
        console.error(`\n❌ Token exchange failed: ${err.message}`);
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`<h2>❌ Failed: ${err.message}</h2>`);
        server.close();
    }
});

async function testSlack(token) {
    const channelId = process.env.SLACK_CHANNEL_ID || 'C0AN5ASHZB6';
    const res = await fetch('https://slack.com/api/chat.postMessage', {
        method:  'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body:    JSON.stringify({
            channel: channelId,
            text:    '✅ *AXIOM Agent connected!* Slack notifications are working. You will receive upload updates and daily reminders here.',
        }),
    });
    const data = await res.json();
    if (data.ok) {
        console.log('✅ Test message sent to Slack! Check your #axiom-agent channel.');
    } else {
        console.error(`❌ Test message failed: ${data.error}`);
        if (data.error === 'not_in_channel') {
            console.log('   → Invite the bot to the channel: /invite @AXIOM Agent');
        }
    }
    process.exit(0);
}

server.listen(3002, () => {
    console.log('Local OAuth server listening on http://localhost:3002');
});
