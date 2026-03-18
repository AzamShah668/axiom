const fs = require('fs');
const NOTION_API_KEY = process.env.NOTION_API_KEY;
const PARENT_PAGE_ID = "32629d9d-9c6e-8045-b22d-fc81f673800a";
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

async function getChildren(blockId) {
    const data = await fetchWithRetry(`${API_BASE}/blocks/${blockId}/children?page_size=100`, { headers });
    return data && data.results ? data.results : [];
}

async function archiveBlock(blockId) {
    const data = await fetchWithRetry(`${API_BASE}/blocks/${blockId}`, { 
        method: 'DELETE', 
        headers 
    });
    if (data && data.id) {
        console.log(`🗑️ Archived Block: ${blockId}`);
    }
}

async function cleanNotion() {
    console.log("Fetching children for Parent Page to clean up...");
    const children = await getChildren(PARENT_PAGE_ID);
    console.log(`Found ${children.length} items to archive.`);
    
    for (const child of children) {
        await archiveBlock(child.id);
        await new Promise(r => setTimeout(r, 400)); // Rate limiting
    }
    console.log("Cleanup complete!");
}

cleanNotion().catch(console.error);
