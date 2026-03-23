// audio_postprocess.js
// STEP 4G.5: Polish raw TTS audio with broadcast-quality FFmpeg filters.
// Runs between TTS generation and TTS segmentation.
// Does NOT change words or timing — pure audio quality improvement.

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * Applies broadcast-quality audio processing to raw TTS output.
 *
 * Filter chain:
 *   1. highpass=f=80       — remove low-frequency rumble/TTS artifacts
 *   2. lowpass=f=12000     — cut harsh artificial highs
 *   3. acompressor         — dynamic range compression (quiet parts louder, loud parts controlled)
 *   4. loudnorm            — broadcast-standard loudness normalization (YouTube targets ~-14 LUFS)
 *
 * @param {string} inputWav  — path to raw TTS WAV (e.g., full_tts.wav)
 * @param {string} outputWav — path to polished WAV (e.g., full_tts_polished.wav)
 * @returns {string} outputWav path
 */
function polishAudio(inputWav, outputWav) {
    if (!fs.existsSync(inputWav)) {
        throw new Error(`Audio post-process: input not found: ${inputWav}`);
    }

    const absIn = path.resolve(inputWav).replace(/\\/g, '/');
    const absOut = path.resolve(outputWav).replace(/\\/g, '/');

    const filterChain = [
        'highpass=f=80',
        'lowpass=f=12000',
        'acompressor=threshold=-18dB:ratio=3:attack=5:release=50',
        'loudnorm=I=-16:TP=-1.5:LRA=11',
    ].join(',');

    // Preserve original sample rate and encoding (TTS outputs 24kHz mono PCM)
    const cmd = `ffmpeg -y -i "${absIn}" -af "${filterChain}" -ar 24000 -ac 1 -acodec pcm_s16le "${absOut}"`;

    console.log('🎛️  Audio post-processing (EQ + compression + loudness normalization)...');
    execSync(cmd, { stdio: 'pipe', timeout: 120_000 });

    const sizeKB = (fs.statSync(outputWav).size / 1024).toFixed(0);
    console.log(`✅  Polished audio: ${outputWav} (${sizeKB} KB)`);

    return outputWav;
}

// CLI usage: node audio_postprocess.js <input.wav> [output.wav]
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.log('Usage: node audio_postprocess.js <input.wav> [output.wav]');
        process.exit(0);
    }
    const input = args[0];
    const output = args[1] || input.replace('.wav', '_polished.wav');
    polishAudio(input, output);
}

module.exports = { polishAudio };
