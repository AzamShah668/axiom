// setup-notion-dbs.js
// Creates Master Syllabus Databases for streams (e.g. 1 for MBBS, 1 for BTech)
// Run: node scripts/setup-notion-dbs.js

const fs = require('fs');
const path = require('path');

const NOTION_API_KEY = process.env.NOTION_API_KEY;
const PARENT_PAGE_ID = "32629d9d-9c6e-8045-b22d-fc81f673800a";
const API_BASE = "https://api.notion.com/v1";

const headers = {
  "Authorization": `Bearer ${NOTION_API_KEY}`,
  "Content-Type": "application/json",
  "Notion-Version": "2022-06-28"
};

// --- API Helpers ---

async function fetchWithRetry(url, options, retries = 3) {
  for (let i = 0; i < retries; i++) {
    const res = await fetch(url, options);
    if (res.status === 429) {
      console.log('Rate limited... waiting 3 seconds');
      await new Promise(r => setTimeout(r, 3000));
      continue;
    }
    const data = await res.json();
    if (!res.ok) {
      console.error(`Notion API Error (${res.status}):`, data.message || JSON.stringify(data));
      return null;
    }
    return data;
  }
  return null;
}

async function createMasterSyllabusDB(streamName, parentId) {
  const schema = {
    parent: { page_id: parentId, type: "page_id" },
    title: [{ text: { content: `${streamName} Master Syllabus` } }],
    icon: { emoji: "📖" },
    properties: {
      "Topic":          { title: {} },
      "Subject":        { select: {} },
      "Chapter":        { select: {} },
      "Status":         { select: { options: [{ name: "Pending", color: "default" }, { name: "In Progress", color: "yellow" }, { name: "Completed", color: "green" }, { name: "Failed", color: "red" }] } },
      "Video URL":      { url: {} },
      "Created Date":   { date: {} }
    }
  };
  const data = await fetchWithRetry(`${API_BASE}/databases`, { method: "POST", headers, body: JSON.stringify(schema) });
  if (data && data.id) {
    console.log(`🗃️ Created Master DB: ${streamName} Database (${data.id})`);
    return data.id;
  }
  return null;
}

async function addTopicToDB(dbId, subjectName, chapterName, topicName) {
  const body = {
    parent: { database_id: dbId },
    properties: {
      "Topic": { title: [{ text: { content: topicName } }] },
      "Subject": { select: { name: subjectName } },
      "Chapter": { select: { name: chapterName } },
      "Status": { select: { name: "Pending" } }
    }
  };
  const data = await fetchWithRetry(`${API_BASE}/pages`, { method: "POST", headers, body: JSON.stringify(body) });
  if (data && data.id) {
    console.log(`   - Added Topic: [${subjectName}] ${topicName}`);
    return true;
  }
  return false;
}

async function createGlobalDBs() {
    const trackerSchema = {
        parent: { page_id: PARENT_PAGE_ID, type: "page_id" },
        title: [{ text: { content: "Global Video Tracker" } }],
        icon: { emoji: "🎬" },
        properties: {
          "Title":          { title: {} },
          "Stream":         { select: { options: [{ name: "MBBS", color: "red" }, { name: "BTech", color: "blue" }] } },
          "Subject":        { rich_text: {} },
          "Topic":          { rich_text: {} },
          "YouTube URL":    { url: {} },
          "Published Date": { date: {} },
          "Status":         { select: { options: [{ name: "Uploaded", color: "green" }, { name: "Processing", color: "yellow" }, { name: "Failed", color: "red" }] } }
        }
    };
    
    const queueSchema = {
        parent: { page_id: PARENT_PAGE_ID, type: "page_id" },
        title: [{ text: { content: "Pipeline Queue" } }],
        icon: { emoji: "🚀" },
        properties: {
          "Subject":        { title: {} },
          "Next Topic":     { rich_text: {} },
          "Last Completed": { rich_text: {} },
          "Pipeline State": { select: { options: [{ name: "Idle", color: "default" }, { name: "Scraping", color: "blue" }, { name: "Researching", color: "purple" }, { name: "Creating Video", color: "yellow" }, { name: "Uploading", color: "orange" }, { name: "Done", color: "green" }] } },
          "Run Date":       { date: {} },
          "Error Log":      { rich_text: {} }
        }
    };

    console.log("Creating Global DBs...");
    const trackerData = await fetchWithRetry(`${API_BASE}/databases`, { method: "POST", headers, body: JSON.stringify(trackerSchema) });
    const queueData = await fetchWithRetry(`${API_BASE}/databases`, { method: "POST", headers, body: JSON.stringify(queueSchema) });

    return { 
      video_tracker: trackerData?.id, 
      pipeline_queue: queueData?.id 
    };
}

async function main() {
  console.log("🚀 Starting Master Notion Database Setup...\n");

  const syllabusPath = path.join(__dirname, '../data/syllabus_extraction.json');
  if (!fs.existsSync(syllabusPath)) {
      console.error("❌ Cannot find syllabus_extraction.json");
      process.exit(1);
  }

  const syllabusData = JSON.parse(fs.readFileSync(syllabusPath, 'utf8'));
  const configPath = path.join(__dirname, '../config.json');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  
  const savedDbIds = { master_databases: {} };

  // Generate Global DBs first
  const globalIds = await createGlobalDBs();
  savedDbIds.video_tracker = globalIds.video_tracker;
  savedDbIds.pipeline_queue = globalIds.pipeline_queue;

  for (const [streamName, subjectsMap] of Object.entries(syllabusData.streams)) {
      console.log(`\n📚 Creating Master DB for: ${streamName}...`);
      
      const dbId = await createMasterSyllabusDB(streamName, PARENT_PAGE_ID);
      
      if (!dbId) {
          console.error(`Failed to create master DB for ${streamName}`);
          continue;
      }
      
      savedDbIds.master_databases[streamName] = dbId;

      for (const [subjectName, topics] of Object.entries(subjectsMap)) {
          // Populate topics based on new structure: { chapter: "...", topics: ["...", "..."] }
          for (const chapterObj of topics) {
              const chapterName = chapterObj.chapter || chapterObj; 
              const subTopics = chapterObj.topics || [chapterName + " Overview"]; 
              
              for (const topic of subTopics) {
                  await addTopicToDB(dbId, subjectName, chapterName, topic);
                  // Sleep briefly to avoid slamming Notion API limits too hard
                  await new Promise(r => setTimeout(r, 400));
              }
          }
      }
  }

  config.notion.databases = savedDbIds;
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  console.log("\n🎉 Setup complete! All mappings saved to config.json.");
}

main().catch(console.error);
