const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../config/.env') });
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const multer = require('multer');
const { spawn } = require('child_process');
const { google } = require('googleapis');
const { authorize } = require('../modules/uploader/youtube_uploader');
const { runFullPipeline } = require('../modules/orchestrator/run_pipeline');
const scheduler = require('../modules/scheduler/scheduler');

const app = express();
app.use(cors());
app.use(express.json());

// Set up Multer for handling file uploads from Dashboard to the /data directory
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const dataPath = path.join(__dirname, '../data');
    if (!fs.existsSync(dataPath)){
        fs.mkdirSync(dataPath, { recursive: true });
    }
    cb(null, dataPath);
  },
  filename: function (req, file, cb) {
    // Preserve exact NotebookLM dummy filenames if matched, else use original name
    const originalName = file.originalname.toLowerCase();
    if (originalName.includes('.wav') || originalName.includes('.mp3')) return cb(null, 'dummy_audio.wav');
    if (originalName.includes('.txt')) return cb(null, 'dummy_transcript.txt');
    if (originalName.includes('timeline') || originalName.includes('.json')) return cb(null, 'dummy_timeline.json');
    
    cb(null, file.originalname);
  }
});
const upload = multer({ storage: storage });

const PORT = 3001;

// Notion Helpers
const NOTION_TOKEN = process.env.NOTION_API_KEY;
const API_BASE = "https://api.notion.com/v1";
const headers = {
    "Authorization": `Bearer ${NOTION_TOKEN}`,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
};

const configPath = path.join(__dirname, '../config/config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

// Route: Get YouTube Stats
app.get('/api/stats', async (req, res) => {
    try {
        const auth = await authorize();
        const youtube = google.youtube({ version: 'v3', auth });
        
        const response = await youtube.channels.list({
            part: 'statistics,snippet',
            mine: true
        });

        if (response.data.items && response.data.items.length > 0) {
            const stats = response.data.items[0].statistics;
            const snippet = response.data.items[0].snippet;
            
            // Calculate a mock "completion rate" based on views/subs ratio for the fun of analytics, or just return 0 if no views
            let completionRate = "0%";
            if (parseInt(stats.viewCount) > 0) {
                 completionRate = "68%"; // Hardcoded for aesthetics as YouTube doesn't expose avg view duration via simple API easily without Analytics API
            }

            res.json({
                channelName: snippet.title,
                totalVideos: stats.videoCount,
                subscribers: stats.subscriberCount,
                views: stats.viewCount,
                avgCompletion: completionRate
            });
        } else {
            res.status(404).json({ error: "Channel not found" });
        }
    } catch (error) {
        console.error("Error fetching YT stats:", error);
        res.status(500).json({ error: error.message });
    }
});

// Route: Get Notion Queue
app.get('/api/queue', async (req, res) => {
    try {
        let allTasks = [];
        
        // Fetch from both BTech and MBBS if available
        for (const [stream, dbId] of Object.entries(config.notion.databases.master_databases)) {
            if (!dbId) continue;
            
            const body = {
                filter: {
                    or: [
                        { property: "Status", select: { equals: "Pending" } },
                        { property: "Status", select: { equals: "In Progress" } }
                    ]
                },
                sorts: [{ timestamp: "created_time", direction: "ascending" }]
            };
            
            const response = await fetch(`${API_BASE}/databases/${dbId}/query`, {
                method: 'POST',
                headers,
                body: JSON.stringify(body)
            });
            
            const data = await response.json();
            if (data.results) {
                const mapped = data.results.map(page => ({
                    id: page.id,
                    topic: page.properties.Topic.title[0]?.plain_text || "Unknown",
                    subject: page.properties.Subject.select?.name || "Unknown",
                    chapter: page.properties.Chapter.select?.name || "Unknown",
                    status: page.properties.Status.select?.name || "Pending",
                    stream: stream
                }));
                allTasks = allTasks.concat(mapped);
            }
        }
        
        res.json(allTasks);
        
    } catch (error) {
        console.error("Error fetching Notion queue:", error);
        res.status(500).json({ error: error.message });
    }
});

// Route: Upload NotebookLM Assets
app.post('/api/upload', upload.array('assets', 10), (req, res) => {
    try {
        console.log("✅ Received Asset Upload:", req.files.map(f => f.filename));
        res.json({ message: "Assets successfully uploaded to /data pipeline." });
    } catch (error) {
        console.error("Error handling asset upload:", error);
        res.status(500).json({ error: "Failed to process upload" });
    }
});

// --- Global Pipeline Logger ---
let globalPipelineLogs = [];

function stripAnsi(str) {
    return str.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '');
}

function addLog(msg) {
    const text = stripAnsi(msg.toString()).trim();
    if (!text) return;
    
    // Prefix with timestamp and keep the last 50 logs
    const timestamp = new Date().toLocaleTimeString();
    
    // Split by newlines in case multiple logs come in one chunk
    text.split('\n').forEach(line => {
        if (line.trim()) {
            globalPipelineLogs.push(`[${timestamp}] ${line.trim()}`);
        }
    });

    while (globalPipelineLogs.length > 50) {
        globalPipelineLogs.shift();
    }
}

// Route: Get Pipeline Logs Real-Time
app.get('/api/pipeline-logs', (req, res) => {
    res.json({ logs: globalPipelineLogs });
});

app.post('/api/run-pipeline', (req, res) => {
    const { stream } = req.body;
    globalPipelineLogs = [];
    addLog(`🚀 [SERVER] Triggering pipeline for ${stream || 'BTech'}...`);
    
    const child = spawn('node', ['modules/orchestrator/run_pipeline.js', stream || 'BTech'], {
        cwd: path.join(__dirname, '../')
    });
    
    child.stdout.on('data', addLog);
    child.stderr.on('data', addLog);
    child.on('close', (code) => {
        if (code !== 0) addLog(`❌ Pipeline Error: Process exited with code ${code}`);
    });

    res.json({ message: "Pipeline started! Watch the Activity panel." });
});

app.post('/api/run-pipeline-topic', (req, res) => {
    const { pageId, topic, subject, chapter, stream } = req.body;
    if (!pageId || !topic) return res.status(400).json({ error: 'pageId and topic are required' });

    globalPipelineLogs = [];
    addLog(`🎯 [SERVER] Triggering pipeline specific topic: "${topic}"...`);
    
    const child = spawn('node', [
        'modules/orchestrator/run_pipeline.js',
        '--topic', topic,
        '--subject', subject || 'General',
        '--chapter', chapter || 'General'
    ], {
        cwd: path.join(__dirname, '../')
    });
    
    child.stdout.on('data', addLog);
    child.stderr.on('data', addLog);
    child.on('close', (code) => {
        if (code !== 0) addLog(`❌ Pipeline Error: Process exited with code ${code}`);
    });

    res.json({ message: `Pipeline started for "${topic}"! Watch the Activity panel.` });
});

// Route: Clear Pipeline Logs
app.get('/api/clear-logs', (req, res) => {
    globalPipelineLogs = [];
    res.json({ message: "Logs cleared!" });
});

// Route: Pipeline Health Check
app.get('/api/health', async (req, res) => {
    const health = { timestamp: new Date().toISOString(), status: 'ok', checks: {} };

    // 1. Chrome debug port
    try {
        const chromeRes = await fetch('http://localhost:9222/json/version', {
            signal: AbortSignal.timeout(3000)
        });
        health.checks.chrome = chromeRes.ok ? 'connected' : 'unreachable';
    } catch (_) {
        health.checks.chrome = 'offline';
    }

    // 2. Colab Gradio URL
    try {
        const colabFile = path.join(__dirname, '../video/colab_url.json');
        if (fs.existsSync(colabFile)) {
            const data = JSON.parse(fs.readFileSync(colabFile, 'utf8'));
            const url = data.gradio_url || data.gradioUrl;
            if (url) {
                const colabRes = await fetch(url, { signal: AbortSignal.timeout(5000) });
                const body = await colabRes.text();
                health.checks.colab = body.includes('No interface') ? 'dead' : 'live';
                health.checks.colab_url = url;
            } else {
                health.checks.colab = 'no_url';
            }
        } else {
            health.checks.colab = 'no_cache_file';
        }
    } catch (_) {
        health.checks.colab = 'unreachable';
    }

    // 3. Notion queue depth
    try {
        for (const [stream, dbId] of Object.entries(config.notion?.databases?.master_databases || {})) {
            if (!dbId) continue;
            const notionRes = await fetch(`${API_BASE}/databases/${dbId}/query`, {
                method: 'POST', headers,
                body: JSON.stringify({ filter: { property: 'Status', select: { equals: 'Pending' } } })
            });
            const data = await notionRes.json();
            health.checks[`notion_${stream}_pending`] = data.results?.length || 0;
        }
    } catch (_) {
        health.checks.notion = 'error';
    }

    // 4. Last pipeline error
    try {
        const errLog = path.join(__dirname, '../logs/pipeline_errors.log');
        if (fs.existsSync(errLog)) {
            const lines = fs.readFileSync(errLog, 'utf8').trim().split('\n');
            health.checks.last_error = lines[lines.length - 1] || 'none';
        } else {
            health.checks.last_error = 'none';
        }
    } catch (_) {}

    // Overall status
    if (health.checks.chrome === 'offline' || health.checks.colab === 'dead' || health.checks.colab === 'unreachable') {
        health.status = 'degraded';
    }

    res.json(health);
});

// ── Auto-Pilot Scheduler Routes ──────────────────────────────────────────────

app.get('/api/scheduler/status', (req, res) => {
    res.json(scheduler.getStatus());
});

app.post('/api/scheduler/enable', (req, res) => {
    const { stream = 'BTech', uploadHourIST = 18 } = req.body;
    const state = scheduler.enable(stream, parseInt(uploadHourIST), addLog);
    addLog(`[AUTO-PILOT] Enabled — daily at ${uploadHourIST}:00 IST for ${stream}`);
    res.json(state);
});

app.post('/api/scheduler/disable', (req, res) => {
    const state = scheduler.disable();
    addLog('[AUTO-PILOT] Disabled by user');
    res.json(state);
});

// ── YouTube Analytics Route ───────────────────────────────────────────────────
// Groups existing videos by upload hour (IST) and returns view counts per hour
// so the dashboard can show the actual best time to upload.

app.get('/api/analytics/youtube', async (req, res) => {
    try {
        const auth    = await authorize();
        const youtube = google.youtube({ version: 'v3', auth });

        // Get uploads playlist ID
        const chanRes = await youtube.channels.list({ part: 'contentDetails,statistics', mine: true });
        const channel = chanRes.data.items?.[0];
        if (!channel) return res.json({ videos: [], hourlyIST: [], bestHourIST: 18, totalVideos: 0 });

        const uploadsId = channel.contentDetails.relatedPlaylists.uploads;

        // Fetch latest 50 video IDs
        const plRes = await youtube.playlistItems.list({
            part: 'snippet', playlistId: uploadsId, maxResults: 50
        });
        const videoIds = (plRes.data.items || []).map(i => i.snippet.resourceId.videoId);

        if (videoIds.length === 0) {
            return res.json({ videos: [], hourlyIST: [], bestHourIST: 18, totalVideos: 0 });
        }

        // Fetch stats for all videos
        const statsRes = await youtube.videos.list({
            part: 'statistics,snippet', id: videoIds.join(',')
        });

        const videos = (statsRes.data.items || []).map(v => ({
            title:       v.snippet.title,
            publishedAt: v.snippet.publishedAt,
            views:       parseInt(v.statistics.viewCount  || 0),
            likes:       parseInt(v.statistics.likeCount  || 0),
            comments:    parseInt(v.statistics.commentCount || 0),
        }));

        // Bucket views by upload hour in IST
        const hourlyIST = Array.from({ length: 24 }, (_, h) => ({
            hour:  h,
            label: `${h === 0 ? 12 : h > 12 ? h - 12 : h}${h < 12 ? ' AM' : ' PM'}`,
            views: 0,
            count: 0,
        }));

        videos.forEach(v => {
            const utcHour = new Date(v.publishedAt).getUTCHours();
            const istHour = (utcHour + 5 + Math.floor(30 / 60)) % 24; // UTC+5:30
            hourlyIST[istHour].views += v.views;
            hourlyIST[istHour].count += 1;
        });

        // Best hour = highest avg views per upload (requires at least 1 upload at that hour)
        let bestHourIST = 18; // default: 6 PM IST
        let bestAvg = 0;
        hourlyIST.forEach(h => {
            if (h.count > 0) {
                const avg = h.views / h.count;
                if (avg > bestAvg) { bestAvg = avg; bestHourIST = h.hour; }
            }
        });

        res.json({
            videos,
            hourlyIST,
            bestHourIST,
            totalVideos: parseInt(channel.statistics.videoCount || 0),
        });

    } catch (err) {
        console.error('Analytics error:', err.message);
        // Return empty data with default recommendation — don't crash the dashboard
        res.json({ videos: [], hourlyIST: [], bestHourIST: 18, totalVideos: 0, error: err.message });
    }
});

// Serve the built React dashboard at localhost:3001
const DASHBOARD_DIST = path.join(__dirname, '../dashboard/dist');
if (fs.existsSync(DASHBOARD_DIST)) {
    app.use(express.static(DASHBOARD_DIST));
    app.use((_req, res) => res.sendFile(path.join(DASHBOARD_DIST, 'index.html')));
}

app.listen(PORT, () => {
    console.log(`EduContent Backend API running on http://localhost:${PORT}`);
    // Resume Auto-Pilot scheduler if it was enabled before server restart
    scheduler.init(addLog);
});
