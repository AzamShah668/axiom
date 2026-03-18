// youtube_scraper.js
// Intelligently scrapes YouTube and dynamically splits Notion topics if they are too broad

require('dotenv').config({ path: '../.env' });
const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const config = JSON.parse(fs.readFileSync(path.join(__dirname, '../config.json'), 'utf8'));

const youtube = google.youtube({
  version: 'v3',
  auth: config.youtube.api_key || process.env.YOUTUBE_DATA_API_KEY
});

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

// Interacts with Notion API to create siblings of a dynamically split topic
async function dynamicallySplitTopic(notionDbId, originalTopicId, subject, chapter, originalTopicName, videoTitlesArray) {
    if (!videoTitlesArray || videoTitlesArray.length === 0) return;

    const firstVideoTitle = videoTitlesArray[0];
    console.log(`\n✂️ Smart Split: Transforming broad topic "${originalTopicName}" into ${videoTitlesArray.length} specific videos...`);
    
    // 1. Rename the *current* row we are processing to the title of the FIRST video in the series
    const renameBody = {
        properties: { "Topic": { title: [{ text: { content: firstVideoTitle } }] } }
    };
    await fetchWithRetry(`${API_BASE}/pages/${originalTopicId}`, { method: 'PATCH', headers, body: JSON.stringify(renameBody) });
    console.log(`   - Focused active topic to: "${firstVideoTitle}"`);

    // 2. Create the remaining videos sequentially in the same DB
    for (let i = 1; i < videoTitlesArray.length; i++) {
        let newTopicName = videoTitlesArray[i];
        
        // Safety check to ensure we don't have empty titles
        if (!newTopicName || newTopicName.trim() === "") {
             newTopicName = `${originalTopicName} - Lesson ${i+1}`; 
        }

        const newBody = {
            parent: { database_id: notionDbId },
            properties: {
              "Topic": { title: [{ text: { content: newTopicName } }] },
              "Subject": { select: { name: subject } },
              "Chapter": { select: { name: chapter } },
              "Status": { select: { name: "Pending" } }
            }
        };
        await fetchWithRetry(`${API_BASE}/pages`, { method: 'POST', headers, body: JSON.stringify(newBody) });
        console.log(`   - Dynamically added new topic: "${newTopicName}"`);
    }
    console.log("Notion Database dynamically updated with specific, granular video titles!\n");
}

async function scrapeForTopic(topicName, subjectName, chapterName, notionDbId, notionPageId) {
    console.log(`\n🔍 Searching YouTube for: [${subjectName}] ${topicName}`);
    const query = `${subjectName} ${chapterName} ${topicName} in english`;

    try {
        const searchRes = await youtube.search.list({
            part: 'snippet',
            q: query,
            type: 'video,playlist',
            maxResults: 5,
            order: 'relevance'
        });

        const items = searchRes.data.items;
        if (!items || items.length === 0) {
            console.error("No results found.");
            return null;
        }

        // --- SMART SPLIT LOGIC ---
        const topItem = items[0];
        const topTitle = topItem.snippet.title.toLowerCase();
        
        let targetUrls = [];
        let boundContextPrompt = "";
        let isMultiPart = false;

        // If the top result is explicitly a playlist:
        if (topItem.id.kind === 'youtube#playlist') {
            isMultiPart = true;
            console.log("Playlist detected! Fetching internal videos to split the topic...");
            
            // Fetch all items from the playlist
            const playlistItemsRes = await youtube.playlistItems.list({
                part: 'snippet,contentDetails',
                playlistId: topItem.id.playlistId,
                maxResults: 15 // Limit to 15 videos to avoid blowing up the Notion DB
            });

            const playlistItems = playlistItemsRes.data.items;
            
            if (playlistItems && playlistItems.length > 0) {
                // Extract the specific titles of every video in the playlist
                const videoTitles = playlistItems.map(item => item.snippet.title);
                
                // Perform the Notion split using EXACT titles
                await dynamicallySplitTopic(notionDbId, notionPageId, subjectName, chapterName, topicName, videoTitles);

                // For the current run, ONLY use the FIRST video in the playlist
                const firstVideoId = playlistItems[0].contentDetails.videoId;
                const firstVideoTitle = videoTitles[0];
                targetUrls.push(`https://www.youtube.com/watch?v=${firstVideoId}`);

                // Craft a hyper-specific prompt targeted entirely on the first video's title
                boundContextPrompt = `You are an expert tutor creating a focused video. This topic is part of a larger series, but your SOLE FOCUS for this script is specifically on: "${firstVideoTitle}". Do NOT attempt to summarize the entire parent topic of ${topicName}. Stay rigorously focused on the details necessary to explain: "${firstVideoTitle}".`;
            }

        } else if (topTitle.includes('part 1')) {
            // Handling manual "Part 1" videos that aren't formal playlists
            isMultiPart = true;
            const partsToCreate = [`${topicName} - Part 1`, `${topicName} - Part 2`, `${topicName} - Part 3`]; 
            await dynamicallySplitTopic(notionDbId, notionPageId, subjectName, chapterName, topicName, partsToCreate);
            
            targetUrls.push(`https://www.youtube.com/watch?v=${topItem.id.videoId}`);
            boundContextPrompt = `You are an expert tutor. This topic is broad. YOU MUST ONLY FOCUS ON **Part 1** of ${topicName}. Do NOT mention concepts that belong in Part 2 or Part 3. Provide a highly concentrated deep dive purely on the introductory and Part 1 elements of this concept.`;
        } 
        else {
            // Standard single-video processing
            targetUrls.push(`https://www.youtube.com/watch?v=${topItem.id.videoId}`);
            boundContextPrompt = `You are an expert tutor. Provide a comprehensive summary and deep dive into the topic of ${topicName} (Subject: ${subjectName}).`;
        }

        console.log(`\n✅ Extracted Primary URL for NotebookLM: ${targetUrls[0]}`);
        console.log(`🤖 Generated Guardrail Prompt: "${boundContextPrompt}"\n`);
        
        const outputParams = {
            targetUrls: targetUrls,
            isSplit: isMultiPart,
            contextPrompt: boundContextPrompt
        };

        // Output to a temp JSON so the parent pipeline can read it easily
        const tempPath = path.join(__dirname, '../data/temp_scrape_result.json');
        fs.writeFileSync(tempPath, JSON.stringify(outputParams, null, 2));

        return outputParams;

    } catch (err) {
        console.error("YouTube API Error:", err.message);
        return null;
    }
}

// Allow Command Line execution for testing
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 5) {
        console.log("Usage: node youtube_scraper.js <Topic Name> <Subject> <Chapter> <Notion DB ID> <Notion Page ID>");
    } else {
        scrapeForTopic(args[0], args[1], args[2], args[3], args[4]);
    }
}

module.exports = { scrapeForTopic };
