require('dotenv').config({ path: '../.env' });
const { fetchNotionData } = require('./notion_helper.js');

async function printIds() {
    try {
        const data = await fetchNotionData('BTech');
        console.log("ALL BTECH TOPICS:");
        data.forEach(t => {
            console.log(`ID: ${t.id} | Name: ${t.topicName} | Status: ${t.status}`);
        });
    } catch (e) {
        console.error(e);
    }
}
printIds();
