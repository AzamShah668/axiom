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
        
        const body = {};
        const res = await fetch(`${API_BASE}/databases/${dbId}/query`, { method: "POST", headers, body: JSON.stringify(body) });
        const data = await res.json();
        
        if (data.error) {
            console.error("NOTION API ERROR:", data);
            return;
        }
        
        console.log("---- ALL TOPICS ----");
        data.results.forEach(page => {
            const topic = page.properties.Topic.title[0]?.plain_text || "Unknown";
            const subject = page.properties.Subject.select?.name || "Unknown";
            const chapter = page.properties.Chapter.select?.name || "Unknown";
            const status = page.properties.Status.select?.name || "No Status";
            
            if (topic.includes("Merge Sort") || topic.includes("Divide and Conquer")) {
                 console.log(`\n==== FOUND MATCH ====`);
                 console.log(`ID: ${page.id} | ${subject} -> ${chapter} -> ${topic} | Status: ${status}`);
                 console.log(`=====================\n`);
            }
        });
    } catch (e) {
        console.error(e);
    }
}
fetchIds();
