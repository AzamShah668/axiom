// run_pipeline.js
// Master Orchestration Script: Coordinates the end-to-end video pipeline

require('dotenv').config({ path: '../.env' });
const fs = require('fs');
const path = require('path');
const { scrapeForTopic } = require('./youtube_scraper');
const { processVideo } = require('../video/post_processor');
const { uploadToYouTube } = require('../uploader/youtube_uploader');
const { generateSEOMetadata } = require('./seo_generator');
const { generateThumbnail } = require('./thumbnail_generator');

const NOTION_API_KEY = process.env.NOTION_API_KEY;
const API_BASE = "https://api.notion.com/v1";
const headers = {
  "Authorization": `Bearer ${NOTION_API_KEY}`,
  "Content-Type": "application/json",
  "Notion-Version": "2022-06-28"
};

async function fetchWithRetry(url, options, retries = 3) {
    for (let i = 0; i < retries; i++) {
      const res = await fetch(url, options);
      if (res.status === 429) {
        await new Promise(r => setTimeout(r, 2000));
        continue;
      }
      return await res.json();
    }
    return null;
}

// 1. Fetch next Pending topic from Notion
async function getNextPendingTopic(dbId) {
    console.log(`\n📡 Fetching next Pending topic from Notion DB Make sure to provide valid DB ID...`);
    const body = {
        filter: { property: "Status", select: { equals: "Pending" } },
        page_size: 1
    };
    const data = await fetchWithRetry(`${API_BASE}/databases/${dbId}/query`, { method: "POST", headers, body: JSON.stringify(body) });
    
    if (!data || !data.results || data.results.length === 0) {
        console.log("No pending topics found in this database.");
        return null;
    }

    const page = data.results[0];
    const topic = page.properties.Topic.title[0]?.plain_text || "Unknown Topic";
    const subject = page.properties.Subject.select?.name || "Unknown Subject";
    const chapter = page.properties.Chapter.select?.name || "Unknown Chapter";

    // Mark as In Progress immediately to avoid double processing
    await fetchWithRetry(`${API_BASE}/pages/${page.id}`, { 
        method: "PATCH", 
        headers, 
        body: JSON.stringify({ properties: { Status: { select: { name: "In Progress" } } } }) 
    });

    console.log(`📌 Selected Topic: [${subject}] ${chapter} - ${topic}`);
    return { id: page.id, topic, subject, chapter, dbId };
}

// Update Notion Status after completion
async function completeNotionTask(pageId, url) {
    console.log(`\n✅ Updating Notion status to Completed with URL: ${url}`);
    const body = {
        properties: { 
            "Status": { select: { name: "Completed" } },
            "Video URL": { url: url },
            "Created Date": { date: { start: new Date().toISOString() } }
        }
    };
    await fetchWithRetry(`${API_BASE}/pages/${pageId}`, { method: "PATCH", headers, body: JSON.stringify(body) });
}

// Update Notion to Failed
async function failNotionTask(pageId) {
    console.log(`\n❌ Updating Notion status to Failed...`);
    const body = { properties: { "Status": { select: { name: "Failed" } } } };
    await fetchWithRetry(`${API_BASE}/pages/${pageId}`, { method: "PATCH", headers, body: JSON.stringify(body) });
}

async function startPipeline(stream = "BTech") {
    console.log(`\n====== 🚀 EDU-CONTENT MASTER PIPELINE =======`);
    console.log(`Starting execution for stream: ${stream}`);

    const config = JSON.parse(fs.readFileSync(path.join(__dirname, '../config.json'), 'utf8'));
    const masterDbId = config.notion.databases.master_databases[stream];

    if (!masterDbId) {
        console.error(`Error: Could not find Master DB ID for stream ${stream}`);
        return;
    }

    try {
        // STEP 1: Get Topic
        const target = await getNextPendingTopic(masterDbId);
        if (!target) {
            console.log("Pipeline idle. Exiting.");
            return;
        }

        // STEP 2: Smart YouTube Scrape
        console.log(`\n--- STEP 2: Smart YouTube Scraping ---`);
        const scrapeData = await scrapeForTopic(target.topic, target.subject, target.chapter, target.dbId, target.id);
        
        if (!scrapeData || scrapeData.targetUrls.length === 0) {
            throw new Error("Scraping failed to find any URLs.");
        }

        console.log(`\n>>> PIPELINE PAUSED: Agent Action Required <<<`);
        console.log(`Due to NotebookLM not having a direct non-browser API, the AI Agent must now step in.`);
        console.log(`1. Target URL: ${scrapeData.targetUrls[0]}`);
        console.log(`2. Guardrail Prompt: ${scrapeData.contextPrompt}`);
        console.log(`\nPlease use the browser sub-agent to generate the Video and Transcript in NotebookLM.`);
        console.log(`Once you have the MP4 and transcript text, save them locally and run Phase 2 of this script (Post-Processing & Uploading).`);
        console.log(`To resume, run: node scripts/run_pipeline.js --resume "${target.id}" "${target.topic}" "${target.subject}" "${target.chapter}" <PathToMP4> <PathToTranscriptText>`);

    } catch (err) {
        console.error(`Pipeline Error: ${err.message}`);
    }
}

async function resumePipeline(pageId, topicName, subject, chapter, videoPath, transcriptTextPath) {
    try {
        console.log(`\n--- STEP 3: Post Processing (Intro/Outro + TTS + Branding) ---`);
        const rawTranscript = fs.readFileSync(transcriptTextPath, 'utf8');
        
        // The post-processor now handles everything: transcript enhancement, TTS, FFmpeg branding
        const finalVideoPath = await processVideo(videoPath, rawTranscript, topicName, subject);

        console.log(`\n--- STEP 4: YouTube Upload & Playlist Management ---`);
        
        // Use the SEO Generator for viral metadata
        const seoData = generateSEOMetadata(topicName, subject, chapter);
        console.log(`Generated SEO Title: ${seoData.title}`);
        
        // Generate the viral thumbnail
        const thumbnailPath = await generateThumbnail(topicName, subject);
        
        const ytInfo = { 
            title: seoData.title, 
            description: seoData.description, 
            tags: seoData.tags, 
            subject, 
            chapter, 
            stream: "Education",
            thumbnailPath: thumbnailPath
        };
        const publishedUrl = await uploadToYouTube(finalVideoPath, ytInfo);

        console.log(`\n--- STEP 5: Finalizing Notion Tracker ---`);
        await completeNotionTask(pageId, publishedUrl);
        console.log(`\n====== 🎉 PIPELINE FULLY EXECUTED =======`);

    } catch (err) {
        console.error(`Pipeline Resume Error: ${err.message}`);
        await failNotionTask(pageId);
    }
}

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length > 0 && args[0] === '--resume') {
        if (args.length < 7) {
            console.log("Usage for resume: node run_pipeline.js --resume <NotionPageId> <TopicName> <Subject> <Chapter> <VideoPath> <TranscriptTextPath>");
        } else {
            resumePipeline(args[1], args[2], args[3], args[4], args[5], args[6]);
        }
    } else {
        const stream = args[0] || "BTech";
        startPipeline(stream);
    }
}

module.exports = { startPipeline, resumePipeline };
