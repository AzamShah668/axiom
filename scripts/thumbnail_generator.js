require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { createCanvas, loadImage, registerFont } = require('canvas');
const { google } = require('googleapis');

const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY;

// Catchy viral text templates
const viralTemplates = [
    "Watch this to learn\n{TOPIC} in 5 minutes",
    "The ONLY video you need\nfor {TOPIC}",
    "{TOPIC} explained\nlike never before",
    "Never fail {TOPIC}\nafter watching this",
    "Master {TOPIC}\nin one video"
];

async function getTopThumbnail(topic) {
    try {
        const youtube = google.youtube({ version: 'v3', auth: YOUTUBE_API_KEY });
        const res = await youtube.search.list({
            part: 'snippet',
            q: topic + ' study tutorial',
            maxResults: 1,
            type: 'video',
            order: 'relevance' // Gets the most algorithm-favored video
        });

        if (res.data.items && res.data.items.length > 0) {
            const snippet = res.data.items[0].snippet;
            // Get maxres if available, else high
            return snippet.thumbnails.high.url;
        }
    } catch (error) {
        console.error("Error fetching competitor thumbnail:", error);
    }
    return null;
}

function wrapText(context, text, x, y, maxWidth, lineHeight) {
    const lines = text.split('\n');
    let currentY = y;
    
    lines.forEach(line => {
        const words = line.split(' ');
        let currentLine = '';

        for (let n = 0; n < words.length; n++) {
            const testLine = currentLine + words[n] + ' ';
            const metrics = context.measureText(testLine);
            const testWidth = metrics.width;
            if (testWidth > maxWidth && n > 0) {
                context.strokeText(currentLine, x, currentY);
                context.fillText(currentLine, x, currentY);
                currentLine = words[n] + ' ';
                currentY += lineHeight;
            } else {
                currentLine = testLine;
            }
        }
        context.strokeText(currentLine, x, currentY);
        context.fillText(currentLine, x, currentY);
        currentY += lineHeight;
    });
}

async function generateThumbnail(topic, subject) {
    console.log(`\n🎨 Generating Viral Thumbnail for: ${topic}`);
    
    const width = 1280;
    const height = 720;
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');

    // 1. Fetch Top Competitor Thumbnail as Background
    const backgroundUrl = await getTopThumbnail(topic);
    
    // 2. Draw Background
    try {
        // We use a predefined gradient if API fails, otherwise we use the scraped thumbnail
        if (backgroundUrl) {
            console.log(`Scraped top competitor thumbnail: ${backgroundUrl}`);
            const image = await loadImage(backgroundUrl);
            // Draw image covering the whole canvas, blurred slightly
            ctx.drawImage(image, 0, 0, width, height);
            
            // Add a dark heavy overlay to make text pop
            ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
            ctx.fillRect(0, 0, width, height);
        } else {
            console.log(`Using fallback gradient background.`);
            const gradient = ctx.createLinearGradient(0, 0, width, height);
            gradient.addColorStop(0, '#0f172a');
            gradient.addColorStop(1, '#3b82f6');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, width, height);
        }
    } catch (err) {
        console.error("Failed to draw background image:", err);
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, width, height);
    }

    // 3. Draw Brand Accent / Glowing Elements
    const glow = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, width/2);
    glow.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
    glow.addColorStop(1, 'transparent');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);

    // 4. Select Catchy Viral Text
    const template = viralTemplates[Math.floor(Math.random() * viralTemplates.length)];
    // Truncate topic if too long
    const shortTopic = topic.length > 25 ? topic.substring(0, 25) + '...' : topic;
    const mainText = template.replace('{TOPIC}', shortTopic.toUpperCase());

    // 5. Draw Text (Bold, Center Aligned, with Stroke/Drop Shadow)
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    // Add fake "Drop shadow" via offset
    ctx.font = 'bold 85px sans-serif';
    ctx.fillStyle = 'rgba(0,0,0,0.8)';
    wrapText(ctx, mainText, (width / 2) + 5, (height / 2) - 35, 1100, 100);
    
    // Draw Subject Badge
    ctx.font = 'bold 40px sans-serif';
    ctx.fillStyle = '#3b82f6'; // Primary blue
    ctx.fillText(`${subject.toUpperCase()} MASTERCLASS`, width / 2, 120);

    // Main Text (White with Yellow Highlights ideally, but we'll do solid white with black stroke here for simplicity & impact)
    ctx.font = 'bold 85px sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 12;
    wrapText(ctx, mainText, width / 2, (height / 2) - 40, 1100, 100);

    // Draw little details like a fake progress bar or "verified" check to increase CTR
    ctx.fillStyle = '#10b981'; // Green
    ctx.fillRect(0, height - 15, width, 15);

    // 6. Save to disk
    const outDir = path.join(__dirname, '../output');
    if (!fs.existsSync(outDir)) {
        fs.mkdirSync(outDir, { recursive: true });
    }
    const thumbPath = path.join(outDir, 'thumbnail.png');
    const buffer = canvas.toBuffer('image/png');
    fs.writeFileSync(thumbPath, buffer);

    console.log(`✅ Viral Thumbnail generated at: ${thumbPath}`);
    return thumbPath;
}

module.exports = { generateThumbnail };

// If ran directly for testing
if (require.main === module) {
    generateThumbnail("Newton's Laws of Motion", "Physics");
}
