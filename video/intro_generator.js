// intro_generator.js
// Step 4J: Dynamically generates intro and outro videos via FFmpeg.
// Videos are duration-matched to their corresponding TTS audio segments.
//
// Intro: Dark gradient bg + AXIOM logo + topic title + subject subtitle
// Outro: Dark gradient bg + "Like & Subscribe" + AXIOM logo + channel name

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ASSETS_DIR = path.join(__dirname, '..', 'assets');
const LOGO_PATH = path.join(ASSETS_DIR, 'axiom_logo.png');
const FONT_PATH = 'C\\:/Windows/Fonts/arialbd.ttf';
const FONT_PATH_REGULAR = 'C\\:/Windows/Fonts/arial.ttf';

/**
 * Get audio duration via ffprobe.
 */
function getDuration(filePath) {
    const result = execSync(
        `ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${filePath.replace(/\\/g, '/')}"`,
        { encoding: 'utf8' }
    );
    return parseFloat(result.trim());
}

/**
 * Escapes text for FFmpeg drawtext filter.
 * Must escape: colon, backslash, single quote, semicolon
 */
function escapeDrawtext(text) {
    return text
        .replace(/\\/g, '\\\\')
        .replace(/:/g, '\\:')
        .replace(/'/g, "\\'")
        .replace(/;/g, '\\;')
        .replace(/\n/g, '');
}

/**
 * Generate intro video matching TTS audio duration.
 *
 * Visual layout:
 *   - Dark gradient background (#1A1A2E → #16213E)
 *   - AXIOM logo centered, 60% opacity
 *   - Topic title: large bold white, below center
 *   - Subject | Chapter: smaller subtitle
 *   - Fade-in from black over 1s
 *
 * @param {object} opts
 * @param {string} opts.introAudioPath - Intro TTS audio WAV
 * @param {string} opts.outputPath - Output MP4 path
 * @param {string} opts.topic - Topic name
 * @param {string} opts.subject - Subject name
 * @param {string} opts.chapter - Chapter name
 */
function generateIntroVideo({ introAudioPath, outputPath, topic, subject, chapter }) {
    console.log('\n🎬 Generating dynamic intro video...');

    const duration = getDuration(introAudioPath);
    console.log(`   Duration: ${duration.toFixed(1)}s (matching TTS audio)`);

    const fwd = (p) => p.replace(/\\/g, '/');
    const safeTopic = escapeDrawtext(topic.toUpperCase());
    const safeSubtitle = escapeDrawtext(`${subject} | ${chapter}`);

    // Build FFmpeg filter
    const hasLogo = fs.existsSync(LOGO_PATH);

    let filterParts = [
        // Dark gradient background
        `color=c=0x1A1A2E:s=1920x1080:d=${duration}:r=30,format=yuv420p[bg]`,
    ];

    if (hasLogo) {
        filterParts.push(
            // Logo: center, slightly above middle, with transparency
            `[1:v]scale=300:-1,format=rgba,colorchannelmixer=aa=0.6[logo]`,
            `[bg][logo]overlay=(W-w)/2:(H-h)/2-80[with_logo]`,
        );
    }

    const baseLabel = hasLogo ? 'with_logo' : 'bg';

    filterParts.push(
        // Topic title: large, bold, centered below logo
        `[${baseLabel}]drawtext=fontfile='${FONT_PATH}':` +
            `text='${safeTopic}':fontcolor=white:fontsize=64:` +
            `x=(w-text_w)/2:y=(h/2)+60[with_title]`,

        // Subtitle: smaller, below title
        `[with_title]drawtext=fontfile='${FONT_PATH_REGULAR}':` +
            `text='${safeSubtitle}':fontcolor=0xAAAAAA:fontsize=32:` +
            `x=(w-text_w)/2:y=(h/2)+140[with_sub]`,

        // Fade in from black
        `[with_sub]fade=t=in:st=0:d=1[intro_v]`,
    );

    const filterComplex = filterParts.join('; ');

    const inputs = [`-f lavfi -i "color=c=black:s=1:d=0"`]; // dummy to start filter
    // Actually, let's use proper inputs
    const cmd = `ffmpeg -y ` +
        `-f lavfi -i "color=c=0x1A1A2E:s=1920x1080:d=${duration}:r=30" ` +
        (hasLogo ? `-i "${fwd(LOGO_PATH)}" ` : '') +
        `-filter_complex "${filterParts.slice(hasLogo ? 1 : 0).join('; ')}" ` +
        `-map "[intro_v]" ` +
        `-c:v libx264 -preset fast -crf 20 ` +
        `-t ${duration} ` +
        `-an ` +
        `"${fwd(outputPath)}"`;

    // Simpler approach: single filter graph with color source
    const simpleFilter = buildIntroFilter(duration, safeTopic, safeSubtitle, hasLogo);

    const simpleCmd = `ffmpeg -y ` +
        (hasLogo ? `-i "${fwd(LOGO_PATH)}" ` : '') +
        `-filter_complex "${simpleFilter}" ` +
        `-map "[out]" ` +
        `-c:v libx264 -preset fast -crf 20 ` +
        `-t ${duration} -an ` +
        `"${fwd(outputPath)}"`;

    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    execSync(simpleCmd, { stdio: 'pipe', maxBuffer: 1024 * 1024 * 50 });

    const size = (fs.statSync(outputPath).size / 1024).toFixed(0);
    console.log(`   Intro video: ${outputPath} (${size} KB)`);
}

function buildIntroFilter(duration, safeTopic, safeSubtitle, hasLogo) {
    const parts = [];

    // Background
    parts.push(`color=c=0x1A1A2E:s=1920x1080:d=${duration}:r=30,format=yuv420p[bg]`);

    let current = 'bg';

    if (hasLogo) {
        parts.push(`[0:v]scale=300:-1,format=rgba,colorchannelmixer=aa=0.6[logo]`);
        parts.push(`[${current}][logo]overlay=(W-w)/2:(H-h)/2-80[wl]`);
        current = 'wl';
    }

    // Topic title
    parts.push(
        `[${current}]drawtext=fontfile='${FONT_PATH}':` +
        `text='${safeTopic}':fontcolor=white:fontsize=64:` +
        `x=(w-text_w)/2:y=(h/2)+60[wt]`
    );
    current = 'wt';

    // Subtitle
    parts.push(
        `[${current}]drawtext=fontfile='${FONT_PATH_REGULAR}':` +
        `text='${safeSubtitle}':fontcolor=0xAAAAAA:fontsize=32:` +
        `x=(w-text_w)/2:y=(h/2)+140[ws]`
    );
    current = 'ws';

    // Fade in
    parts.push(`[${current}]fade=t=in:st=0:d=1[out]`);

    return parts.join('; ');
}

/**
 * Generate outro video matching TTS audio duration.
 *
 * Visual layout:
 *   - Dark gradient background
 *   - "Thanks for watching!" text
 *   - "LIKE & SUBSCRIBE" large text
 *   - AXIOM logo
 *   - Fade-in from black
 */
function generateOutroVideo({ outroAudioPath, outputPath, topic }) {
    console.log('\n🎬 Generating dynamic outro video...');

    const duration = getDuration(outroAudioPath);
    console.log(`   Duration: ${duration.toFixed(1)}s (matching TTS audio)`);

    const fwd = (p) => p.replace(/\\/g, '/');
    const safeTopic = escapeDrawtext(topic);
    const hasLogo = fs.existsSync(LOGO_PATH);

    const parts = [];

    // Background
    parts.push(`color=c=0x1A1A2E:s=1920x1080:d=${duration}:r=30,format=yuv420p[bg]`);

    let current = 'bg';

    if (hasLogo) {
        parts.push(`[0:v]scale=250:-1,format=rgba,colorchannelmixer=aa=0.5[logo]`);
        parts.push(`[${current}][logo]overlay=(W-w)/2:100[wl]`);
        current = 'wl';
    }

    // "Thanks for watching!"
    parts.push(
        `[${current}]drawtext=fontfile='${FONT_PATH_REGULAR}':` +
        `text='Thanks for watching!':fontcolor=0xCCCCCC:fontsize=36:` +
        `x=(w-text_w)/2:y=(h/2)-40[wt1]`
    );
    current = 'wt1';

    // "LIKE & SUBSCRIBE"
    parts.push(
        `[${current}]drawtext=fontfile='${FONT_PATH}':` +
        `text='LIKE \\& SUBSCRIBE':fontcolor=0xFF4444:fontsize=72:` +
        `x=(w-text_w)/2:y=(h/2)+40[wt2]`
    );
    current = 'wt2';

    // Channel name
    parts.push(
        `[${current}]drawtext=fontfile='${FONT_PATH_REGULAR}':` +
        `text='@AxiomAcademy':fontcolor=0x888888:fontsize=28:` +
        `x=(w-text_w)/2:y=(h/2)+130[wt3]`
    );
    current = 'wt3';

    // Fade in
    parts.push(`[${current}]fade=t=in:st=0:d=1[out]`);

    const filterComplex = parts.join('; ');

    const cmd = `ffmpeg -y ` +
        (hasLogo ? `-i "${fwd(LOGO_PATH)}" ` : '') +
        `-filter_complex "${filterComplex}" ` +
        `-map "[out]" ` +
        `-c:v libx264 -preset fast -crf 20 ` +
        `-t ${duration} -an ` +
        `"${fwd(outputPath)}"`;

    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    execSync(cmd, { stdio: 'pipe', maxBuffer: 1024 * 1024 * 50 });

    const size = (fs.statSync(outputPath).size / 1024).toFixed(0);
    console.log(`   Outro video: ${outputPath} (${size} KB)`);
}

// CLI
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.log('Usage:');
        console.log('  node intro_generator.js intro <audio_wav> <output_mp4> <topic> <subject> <chapter>');
        console.log('  node intro_generator.js outro <audio_wav> <output_mp4> <topic>');
        process.exit(0);
    }

    if (args[0] === 'intro') {
        generateIntroVideo({
            introAudioPath: args[1],
            outputPath: args[2],
            topic: args[3] || 'Topic',
            subject: args[4] || 'Subject',
            chapter: args[5] || 'Chapter'
        });
    } else if (args[0] === 'outro') {
        generateOutroVideo({
            outroAudioPath: args[1],
            outputPath: args[2],
            topic: args[3] || 'Topic'
        });
    }
}

module.exports = { generateIntroVideo, generateOutroVideo };
