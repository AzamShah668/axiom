require('dotenv').config({ path: '../.env' });
const fs = require('fs');

const NOTION_API_KEY = process.env.NOTION_API_KEY;
const API_BASE = "https://api.notion.com/v1";
const headers = {
  "Authorization": `Bearer ${NOTION_API_KEY}`,
  "Content-Type": "application/json",
  "Notion-Version": "2022-06-28"
};

async function fetchIds() {
    try {
        const config = JSON.parse(fs.readFileSync('../config.json', 'utf8'));
        const dbId = config.notion.databases.master_databases['BTech'];
        
        const body = {
            filter: { property: "Status", select: { equals: "In Progress" } },
        };
        const res = await fetch(`${API_BASE}/databases/${dbId}/query`, { method: "POST", headers, body: JSON.stringify(body) });
        const data = await res.json();
        
        console.log("---- IN PROGRESS TOPICS ----");
        data.results.forEach(page => {
            const topic = page.properties.Topic.title[0]?.plain_text || "Unknown";
            const subject = page.properties.Subject.select?.name || "Unknown";
            const chapter = page.properties.Chapter.select?.name || "Unknown";
            console.log(`ID: ${page.id} | ${subject} -> ${chapter} -> ${topic}`);
        });
    } catch (e) {
        console.error(e);
    }
}
fetchIds();
