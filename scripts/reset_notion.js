const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../config/.env') });

const NOTION_TOKEN = process.env.NOTION_API_KEY;
const API_BASE = "https://api.notion.com/v1";
const headers = {
    "Authorization": `Bearer ${NOTION_TOKEN}`,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
};

const config = JSON.parse(fs.readFileSync(path.join(__dirname, '../config/config.json'), 'utf8'));
const DB_MBBS = config.notion.databases.master_databases.MBBS;
const DB_BTECH = config.notion.databases.master_databases.BTech;
const DB_TRACKER = config.notion.databases.video_tracker;

async function resetDatabase(dbId, dbName) {
    if (!dbId) return;
    console.log(`\n⏳ Fetching Completed/In Progress tasks from ${dbName} Master DB...`);
    
    // Find all pages that are NOT Pending
    const queryBody = {
        filter: {
            property: "Status",
            select: {
                does_not_equal: "Pending"
            }
        }
    };

    const res = await fetch(`${API_BASE}/databases/${dbId}/query`, {
        method: 'POST',
        headers,
        body: JSON.stringify(queryBody)
    });
    
    if (!res.ok) {
        console.error(`Error querying ${dbName}:`, await res.text());
        return;
    }
    
    const data = await res.json();
    const pages = data.results;
    
    if (pages.length === 0) {
        console.log(`✅ ${dbName} is already completely fresh (all topics are Pending).`);
        return;
    }

    console.log(`Found ${pages.length} modified tasks in ${dbName}. Resetting to Pending...`);
    
    for (const page of pages) {
        const updateRes = await fetch(`${API_BASE}/pages/${page.id}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify({
                properties: {
                    Status: {
                        select: { name: "Pending" }
                    }
                }
            })
        });
        
        if (updateRes.ok) {
            const topicName = page.properties.Topic?.title?.[0]?.plain_text || "Unknown Topic";
            console.log(`  🔄 Reset: "${topicName}" -> Pending`);
        } else {
            console.error(`  ❌ Failed to reset page ${page.id}:`, await updateRes.text());
        }
    }
}

async function clearVideoTracker(dbId) {
    if (!dbId) return;
    console.log(`\n⏳ Fetching all entries from Video Tracker DB...`);
    
    const res = await fetch(`${API_BASE}/databases/${dbId}/query`, {
        method: 'POST',
        headers
    });
    
    if (!res.ok) {
        console.error(`Error querying Video Tracker:`, await res.text());
        return;
    }
    
    const data = await res.json();
    const pages = data.results;
    
    if (pages.length === 0) {
        console.log(`✅ Video Tracker is already empty.`);
        return;
    }

    console.log(`Found ${pages.length} published entries in Video Tracker. Archiving them...`);
    
    for (const page of pages) {
        // Archiving the page effectively deletes it from the DB view
        const updateRes = await fetch(`${API_BASE}/pages/${page.id}`, {
            method: 'PATCH',
            headers,
            body: JSON.stringify({
                archived: true
            })
        });
        
        if (updateRes.ok) {
            console.log(`  🗑️ Archived past video record: ${page.id}`);
        } else {
            console.error(`  ❌ Failed to archive record ${page.id}:`, await updateRes.text());
        }
    }
}

async function main() {
    console.log("🚀 Starting Notion Database Factory Reset...");
    await resetDatabase(DB_MBBS, "MBBS");
    await resetDatabase(DB_BTECH, "BTech");
    await clearVideoTracker(DB_TRACKER);
    console.log("\n🎉 Factory Reset Complete! All tasks are 'Pending' and pipeline is fresh.");
}

main().catch(console.error);
