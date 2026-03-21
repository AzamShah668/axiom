// tts_segmenter.js
// Step 4H: Splits the full TTS audio into intro/main/outro segments
// using word counts from transcript_enhancer and Whisper timestamps from TTS.
//
// Usage:
//   node tts_segmenter.js <tts_wav> <tts_timestamps_json> <enhanced_json> <output_dir>

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * Split a WAV file at exact timestamps using FFmpeg stream copy.
 */
function splitAudio(inputWav, startSec, endSec, outputPath) {
    const duration = endSec - startSec;
    const cmd = `ffmpeg -y -i "${inputWav.replace(/\\/g, '/')}" ` +
        `-ss ${startSec.toFixed(3)} -t ${duration.toFixed(3)} ` +
        `-c copy "${outputPath.replace(/\\/g, '/')}"`;

    execSync(cmd, { stdio: 'pipe' });
}

/**
 * Segments the full TTS audio into 3 parts based on word boundaries.
 *
 * @param {string} ttsWavPath - Path to full TTS WAV (intro+main+outro)
 * @param {string} ttsTimestampsPath - Whisper timestamps JSON from TTS audio
 * @param {string} enhancedJsonPath - Enhanced transcript JSON (has word counts)
 * @param {string} outputDir - Where to save the 3 segments
 * @returns {object} - { introAudio, mainAudio, outroAudio, splitPoints }
 */
function segmentTTSAudio(ttsWavPath, ttsTimestampsPath, enhancedJsonPath, outputDir) {
    console.log('\n✂️  TTS Audio Segmenter');
    console.log('   Splitting full TTS into intro/main/outro...\n');

    const timestamps = JSON.parse(fs.readFileSync(ttsTimestampsPath, 'utf8'));
    const enhanced = JSON.parse(fs.readFileSync(enhancedJsonPath, 'utf8'));

    const words = timestamps.words;
    const totalDuration = timestamps.duration;

    const introWordCount = enhanced.introWordCount;
    const mainWordCount = enhanced.mainWordCount;
    const outroWordCount = enhanced.outroWordCount || 50;
    const expectedTotal = introWordCount + mainWordCount + outroWordCount;

    // Whisper often detects fewer words than the actual text (contractions, missed words).
    // Scale word indices proportionally to match the actual detected word count.
    const ratio = words.length / expectedTotal;

    // Find split points by scaled word index
    const scaledIntro = Math.round(introWordCount * ratio);
    const scaledMain = Math.round(mainWordCount * ratio);
    const introEndIdx = Math.min(scaledIntro - 1, words.length - 2);
    const mainEndIdx = Math.min(introEndIdx + scaledMain, words.length - 2);

    console.log(`   Word ratio: ${words.length}/${expectedTotal} = ${ratio.toFixed(2)} (scaled indices)`);

    // Get timestamps at split points (use word end time for clean cuts)
    const introEndTime = words[introEndIdx] ? words[introEndIdx].end : 0;
    const mainEndTime = words[mainEndIdx] ? words[mainEndIdx].end : totalDuration;

    console.log(`   Total words: ${words.length} | Duration: ${totalDuration.toFixed(1)}s`);
    console.log(`   Intro: words 0-${introEndIdx} (0.000s - ${introEndTime.toFixed(3)}s)`);
    console.log(`   Main:  words ${introEndIdx + 1}-${mainEndIdx} (${introEndTime.toFixed(3)}s - ${mainEndTime.toFixed(3)}s)`);
    console.log(`   Outro: words ${mainEndIdx + 1}-${words.length - 1} (${mainEndTime.toFixed(3)}s - ${totalDuration.toFixed(3)}s)`);

    fs.mkdirSync(outputDir, { recursive: true });

    const introAudio = path.join(outputDir, 'intro_audio.wav');
    const mainAudio = path.join(outputDir, 'main_audio.wav');
    const outroAudio = path.join(outputDir, 'outro_audio.wav');

    // Split audio at word boundaries
    splitAudio(ttsWavPath, 0, introEndTime, introAudio);
    splitAudio(ttsWavPath, introEndTime, mainEndTime, mainAudio);
    splitAudio(ttsWavPath, mainEndTime, totalDuration, outroAudio);

    // Verify all segments exist and have reasonable size
    for (const [label, fp] of [['Intro', introAudio], ['Main', mainAudio], ['Outro', outroAudio]]) {
        if (!fs.existsSync(fp)) throw new Error(`${label} audio segment not created: ${fp}`);
        const size = fs.statSync(fp).size;
        console.log(`   ${label}: ${(size / 1024).toFixed(0)} KB`);
    }

    const result = {
        introAudio,
        mainAudio,
        outroAudio,
        splitPoints: {
            introEnd: introEndTime,
            mainEnd: mainEndTime,
            totalDuration
        }
    };

    // Save split metadata
    const metaPath = path.join(outputDir, 'tts_segments.json');
    fs.writeFileSync(metaPath, JSON.stringify(result, null, 2), 'utf8');
    console.log(`\n   Metadata: ${metaPath}`);

    return result;
}

// CLI
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 4) {
        console.log('Usage: node tts_segmenter.js <tts_wav> <tts_timestamps_json> <enhanced_json> <output_dir>');
        process.exit(0);
    }
    segmentTTSAudio(args[0], args[1], args[2], args[3]);
}

module.exports = { segmentTTSAudio };
