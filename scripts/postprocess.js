// scripts/postprocess.js
// Wraps the Remotion CLI to render the final video given raw inputs.
// Usage: node scripts/postprocess.js <subject> <topic_slug> <hookText> <trimEndFrames>

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const subject = process.argv[2];
const topicSlug = process.argv[3];
const hookText = process.argv[4] || "Understand this topic in five minutes!";
const trimEndFrames = parseInt(process.argv[5] || '150', 10); // 5 seconds default

if (!subject || !topicSlug) {
    console.error("Usage: node postprocess.js <subject> <topic_slug> [hookText] [trimEndFrames]");
    process.exit(1);
}

const videoDir = path.join(__dirname, '../video');
const rawVideoPath = path.join(__dirname, `../output/raw_${subject}_${topicSlug}.mp4`);
const audioPath = path.join(__dirname, `../output/audio_${subject}_${topicSlug}.wav`);
const finalVideoPath = path.join(__dirname, `../output/final_${subject}_${topicSlug}.mp4`);

if (!fs.existsSync(rawVideoPath)) {
    console.error(`❌ Raw video not found: ${rawVideoPath}`);
    process.exit(1);
}

console.log(`🎬 Starting Post-Processing for: ${topicSlug}`);

const props = JSON.stringify({
    videoSrc: `file://${rawVideoPath}`,
    audioSrc: fs.existsSync(audioPath) ? `file://${audioPath}` : '', // Allow fallbacks for testing
    hookText: hookText,
    trimEndFrames: trimEndFrames
});

try {
    // Run Remotion CLI
    const cmd = `npx remotion render src/index.ts EduContent "${finalVideoPath}" --props='${props}'`;
    console.log(`> ${cmd}`);
    
    execSync(cmd, { cwd: videoDir, stdio: 'inherit' });
    
    console.log(`✅ Final composited video saved to: ${finalVideoPath}`);
} catch (err) {
    console.error("❌ Remotion render failed", err);
    process.exit(1);
}
