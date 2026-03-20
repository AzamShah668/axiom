// tts_generator.js
// Integrates with the Qwen3 TTS GPU server running on Google Colab.
// SINGLE-PASS: Sends the entire transcript in ONE call to keep the voice
// perfectly consistent. AUTOMATIC: The Colab URL is health-checked and
// auto-renewed via colab_manager.js — no manual link updates ever needed.

const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { getLiveColabUrl } = require('./colab_manager');

const PYTHON_EXECUTABLE = `"C:\\Users\\AZAM RIZWAN\\qwen-tts-gpu\\Scripts\\python.exe"`;
const TTS_TIMEOUT_MS = 15 * 60 * 1000; // 15 min — generous for long full-transcript runs on Colab

// Your voice clone reference — the recording you made + its exact transcript
const REF_AUDIO_PATH = "D:/notebook lm/voice/Recording (14).m4a";
const REF_TRANSCRIPT = "Hey everyone, welcome back! Have you ever wondered how artificial intelligence is changing the way we learn? Today, we are going to explore some incredible new concepts together. It's truly fascinating, and I know you're going to love it.";

/**
 * Generates a WAV audio file via the Colab Gradio API in a SINGLE PASS.
 * The full transcript is sent at once — no chunking — so the voice stays
 * 100% consistent from the first word to the last.
 *
 * @param {string} transcriptText - Full text to synthesize.
 * @param {string} outputPath     - Final .wav destination.
 * @returns {Promise<string>}
 */
async function generateTTS(transcriptText, outputPath) {
    console.log(`\n🎙️  Starting Qwen3 TTS — Single-Pass Mode (full transcript, no chunking)...`);

    // ── Auto-refresh Colab URL if expired ──
    const GRADIO_URL = await getLiveColabUrl();
    console.log(`📡  Colab server: ${GRADIO_URL}`);

    // Sanitize control characters that may cause issues in Python string literals
    const safeText = transcriptText
        .replace(/\0/g, '')
        .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/g, ' ')
        .trim();

    const wordCount = safeText.split(/\s+/).length;
    console.log(`📝  Full transcript: ${wordCount} words — sending to GPU in one shot...`);

    const tempPyScriptPath = path.join(os.tmpdir(), `qwen_tts_singlepass_${Date.now()}.py`);
    const escapedText       = JSON.stringify(safeText);
    const escapedTranscript = JSON.stringify(REF_TRANSCRIPT);
    const pyOutputPath      = outputPath.replace(/\\/g, '/');
    const refAudioForward   = REF_AUDIO_PATH.replace(/\\/g, '/');

    const pyCode = `
import sys, shutil
from gradio_client import Client, handle_file

try:
    client = Client("${GRADIO_URL}")

    print("Sending full transcript to Colab GPU...")

    # Single predict call — the entire transcript flows through the voice clone model at once
    result = client.predict(
        text=${escapedText},
        ref_audio_path=handle_file(r"${refAudioForward}"),
        ref_text=${escapedTranscript},
        language="English",
        api_name="/predict"
    )

    # result is the filepath of the generated WAV returned by gr.Audio
    audio_wav = result
    shutil.copy(audio_wav, "${pyOutputPath}")
    print("SUCCESS|" + str(audio_wav))
    sys.exit(0)

except Exception as e:
    import traceback
    print("ERROR|" + str(e))
    traceback.print_exc()
    sys.exit(1)
`;

    fs.writeFileSync(tempPyScriptPath, pyCode, 'utf8');
    const command = `${PYTHON_EXECUTABLE} "${tempPyScriptPath}"`;

    return new Promise((resolve, reject) => {
        exec(command, { maxBuffer: 1024 * 1024 * 20, timeout: TTS_TIMEOUT_MS }, (error, stdout, stderr) => {
            try { fs.unlinkSync(tempPyScriptPath); } catch (_) {}

            if (error) {
                const logMsg = `ERROR:\n${error.message}\n\nSTDOUT:\n${stdout}\n\nSTDERR:\n${stderr}`;
                fs.writeFileSync(path.join(__dirname, '..', 'logs', 'tts_error.log'), logMsg);
                return reject(new Error(`TTS generation failed: ${error.message}\nSTDOUT: ${stdout}\nSTDERR: ${stderr}`));
            }
            if (!fs.existsSync(outputPath)) {
                return reject(new Error(`TTS returned success but output WAV is missing. STDOUT: ${stdout}`));
            }

            console.log(`✅  Full audio saved to: ${outputPath}`);
            resolve(outputPath);
        });
    });
}

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.log("Usage: node tts_generator.js <\"Full Text To Speak\"> <OutputWavPath>");
    } else {
        generateTTS(args[0], args[1]).catch(err => {
            console.error(err.message);
            process.exit(1);
        });
    }
}

module.exports = { generateTTS };
