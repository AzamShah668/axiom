// tts_generator.js
// Node.js TTS wrapper — standalone usage and backward compatibility.
// The main pipeline (run_pipeline.js) calls tts_full_generate.py directly,
// which supports both Qwen3 and CosyVoice 2 with per-chunk prosody instructions.
// This file is kept for standalone CLI usage and legacy integrations.

const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { getLiveColabUrl, autoRelaunchColab } = require('../tools/colab_manager');

const PYTHON_EXECUTABLE = `"C:\\Users\\AZAM RIZWAN\\qwen-tts-gpu\\Scripts\\python.exe"`;
const TTS_TIMEOUT_MS = 10 * 60 * 1000; // 10 min per chunk — T4 GPU processes ~3 words/sec
const MAX_RETRIES = 3;
const MIN_WAV_SIZE = 10 * 1024; // 10KB — anything smaller is corrupt/empty
const CHUNK_WORD_LIMIT = 100;   // Words per TTS chunk — keeps each call under 5 min on T4

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

    // Sanitize control characters that may cause issues in Python string literals
    const safeText = transcriptText
        .replace(/\0/g, '')
        .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/g, ' ')
        .trim();

    const wordCount = safeText.split(/\s+/).length;
    console.log(`📝  Full transcript: ${wordCount} words`);

    const backoffDelays = [5000, 15000, 45000]; // 5s, 15s, 45s

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        try {
            console.log(`\n📡  Attempt ${attempt}/${MAX_RETRIES} — fetching live Colab URL...`);
            const GRADIO_URL = await getLiveColabUrl();
            console.log(`📡  Colab server: ${GRADIO_URL}`);

            await runTTSPython(GRADIO_URL, safeText, outputPath);

            // Validate output file exists and is large enough
            if (!fs.existsSync(outputPath)) {
                throw new Error('TTS returned success but output WAV is missing.');
            }
            const fileSize = fs.statSync(outputPath).size;
            if (fileSize < MIN_WAV_SIZE) {
                throw new Error(`Output WAV too small (${fileSize} bytes) — likely corrupt or empty.`);
            }

            console.log(`✅  Full audio saved to: ${outputPath} (${(fileSize / 1024).toFixed(0)} KB)`);
            return outputPath;

        } catch (err) {
            console.error(`❌  TTS attempt ${attempt} failed: ${err.message}`);
            const logMsg = `[Attempt ${attempt}] ${new Date().toISOString()}\n${err.message}\n`;
            const logPath = path.join(__dirname, '..', 'logs', 'tts_error.log');
            try { fs.mkdirSync(path.dirname(logPath), { recursive: true }); } catch (_) {}
            try { fs.appendFileSync(logPath, logMsg + '\n'); } catch (_) {}

            if (attempt < MAX_RETRIES) {
                // Try relaunching Colab before retrying
                console.log('🔄  Attempting Colab relaunch before retry...');
                try { await autoRelaunchColab(); } catch (relaunchErr) {
                    console.warn(`⚠️  Colab relaunch failed: ${relaunchErr.message}`);
                }
                const delay = backoffDelays[attempt - 1] || 45000;
                console.log(`⏳  Waiting ${delay / 1000}s before retry...`);
                await new Promise(r => setTimeout(r, delay));
            } else {
                throw new Error(`TTS failed after ${MAX_RETRIES} attempts. Last error: ${err.message}`);
            }
        }
    }
}

/**
 * Splits text into chunks of roughly CHUNK_WORD_LIMIT words,
 * breaking at sentence boundaries to preserve natural flow.
 */
function splitIntoChunks(text) {
    const sentences = text.match(/[^.!?]+[.!?]+[\s]*/g) || [text];
    const chunks = [];
    let current = '';
    let currentWords = 0;

    for (const sentence of sentences) {
        const sentenceWords = sentence.trim().split(/\s+/).length;
        if (currentWords + sentenceWords > CHUNK_WORD_LIMIT && current.trim()) {
            chunks.push(current.trim());
            current = '';
            currentWords = 0;
        }
        current += sentence;
        currentWords += sentenceWords;
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
}

/**
 * Runs the Python TTS subprocess for a single chunk.
 */
function runTTSChunk(gradioUrl, chunkText, outputPath) {
    const tempPyScriptPath = path.join(os.tmpdir(), `qwen_tts_chunk_${Date.now()}.py`);
    const escapedText       = JSON.stringify(chunkText);
    const escapedTranscript = JSON.stringify(REF_TRANSCRIPT);
    const pyOutputPath      = outputPath.replace(/\\/g, '/');
    const refAudioForward   = REF_AUDIO_PATH.replace(/\\/g, '/');

    const pyCode = `
import sys, shutil
from gradio_client import Client, handle_file
import httpx

try:
    client = Client("${gradioUrl}", httpx_kwargs={"timeout": httpx.Timeout(300.0)})
    result = client.predict(
        text=${escapedText},
        ref_audio_path=handle_file(r"${refAudioForward}"),
        ref_text=${escapedTranscript},
        language="English",
        api_name="/predict"
    )
    shutil.copy(result, "${pyOutputPath}")
    print("SUCCESS|" + str(result))
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
                return reject(new Error(`TTS chunk failed: ${error.message}\nSTDOUT: ${stdout}\nSTDERR: ${stderr}`));
            }
            resolve(stdout);
        });
    });
}

/**
 * Concatenates multiple WAV files into one using ffmpeg.
 */
function concatWavFiles(wavPaths, outputPath) {
    const { execSync } = require('child_process');
    const listFile = path.join(os.tmpdir(), `tts_concat_${Date.now()}.txt`);
    // Use absolute paths and forward slashes for ffmpeg concat compatibility
    const listContent = wavPaths.map(p => `file '${path.resolve(p).replace(/\\/g, '/')}'`).join('\n');
    fs.writeFileSync(listFile, listContent, 'utf8');

    const absOutput = path.resolve(outputPath).replace(/\\/g, '/');
    const cmd = `ffmpeg -y -f concat -safe 0 -i "${listFile.replace(/\\/g, '/')}" -c copy "${absOutput}"`;
    execSync(cmd, { stdio: 'pipe', timeout: 60000 });
    try { fs.unlinkSync(listFile); } catch (_) {}
}

/**
 * Runs chunked TTS: splits text into ~200-word chunks, generates each separately,
 * then concatenates with ffmpeg. This prevents Gradio tunnel timeouts on long texts.
 */
async function runTTSPython(gradioUrl, safeText, outputPath) {
    const chunks = splitIntoChunks(safeText);

    if (chunks.length === 1) {
        console.log(`   Single chunk (${safeText.split(/\s+/).length} words) — direct call`);
        return runTTSChunk(gradioUrl, chunks[0], outputPath);
    }

    console.log(`   Splitting into ${chunks.length} chunks (~${CHUNK_WORD_LIMIT} words each) to avoid tunnel timeout`);
    const chunkWavs = [];

    for (let i = 0; i < chunks.length; i++) {
        const words = chunks[i].split(/\s+/).length;
        const chunkPath = outputPath.replace('.wav', `_chunk${i}.wav`);
        console.log(`   Chunk ${i + 1}/${chunks.length} (${words} words)...`);
        await runTTSChunk(gradioUrl, chunks[i], chunkPath);

        if (!fs.existsSync(chunkPath) || fs.statSync(chunkPath).size < MIN_WAV_SIZE) {
            throw new Error(`Chunk ${i + 1} produced invalid output`);
        }
        chunkWavs.push(chunkPath);

        // Small delay between chunks to let the Gradio server recover
        if (i < chunks.length - 1) {
            await new Promise(r => setTimeout(r, 3000));
        }
    }

    console.log(`   Concatenating ${chunkWavs.length} chunks with ffmpeg...`);
    concatWavFiles(chunkWavs, outputPath);

    // Clean up chunk files
    for (const p of chunkWavs) {
        try { fs.unlinkSync(p); } catch (_) {}
    }
}

/**
 * Generates TTS audio AND runs Whisper to get word-level timestamps.
 * Used by the 3-track sync pipeline to know exactly when each word is spoken.
 *
 * @param {string} transcriptText - Full text to synthesize
 * @param {string} outputWavPath  - Final .wav destination
 * @param {string} timestampsOutputPath - Where to save Whisper timestamps JSON
 * @returns {Promise<{audioPath: string, timestampsPath: string}>}
 */
async function generateTTSWithTimestamps(transcriptText, outputWavPath, timestampsOutputPath) {
    // Step 1: Generate TTS audio
    await generateTTS(transcriptText, outputWavPath);

    // Step 2: Run Whisper on our TTS output to get word-level timestamps
    console.log('\n🔍 Running Whisper on TTS output for word-level timestamps...');
    const whisperResult = await runWhisperOnAudio(outputWavPath, timestampsOutputPath);
    console.log(`✅ TTS timestamps: ${whisperResult.total_words} words, ${whisperResult.duration.toFixed(1)}s`);

    return { audioPath: outputWavPath, timestampsPath: timestampsOutputPath };
}

/**
 * Runs Whisper on a WAV file to extract word-level timestamps.
 * Uses the same Python venv that has whisper installed.
 */
function runWhisperOnAudio(audioPath, outputJsonPath) {
    const pyAudioPath = audioPath.replace(/\\/g, '/');
    const pyOutputPath = outputJsonPath.replace(/\\/g, '/');

    const pyCode = `
import whisper, json, sys

model = whisper.load_model("base")
result = model.transcribe(r"${pyAudioPath}", language="en", word_timestamps=True, verbose=False)

words = []
segments = []
for seg in result.get("segments", []):
    seg_data = {"id": seg["id"], "start": round(seg["start"], 3), "end": round(seg["end"], 3), "text": seg["text"].strip(), "words": []}
    for w in seg.get("words", []):
        wd = {"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)}
        seg_data["words"].append(wd)
        words.append(wd)
    segments.append(seg_data)

output = {
    "duration": round(segments[-1]["end"], 3) if segments else 0,
    "total_words": len(words),
    "total_segments": len(segments),
    "full_text": result.get("text", "").strip(),
    "segments": segments,
    "words": words
}

with open(r"${pyOutputPath}", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(json.dumps({"duration": output["duration"], "total_words": output["total_words"]}))
`;

    const tempScript = path.join(os.tmpdir(), `whisper_tts_${Date.now()}.py`);
    fs.writeFileSync(tempScript, pyCode, 'utf8');

    return new Promise((resolve, reject) => {
        exec(`${PYTHON_EXECUTABLE} "${tempScript}"`, {
            maxBuffer: 1024 * 1024 * 20,
            timeout: 5 * 60 * 1000  // 5 min for Whisper
        }, (error, stdout, stderr) => {
            try { fs.unlinkSync(tempScript); } catch (_) {}

            if (error) {
                return reject(new Error(`Whisper failed: ${error.message}\n${stderr}`));
            }

            try {
                const result = JSON.parse(stdout.trim().split('\n').pop());
                resolve(result);
            } catch (_) {
                // If JSON parse fails, read from file
                try {
                    const data = JSON.parse(fs.readFileSync(outputJsonPath, 'utf8'));
                    resolve({ duration: data.duration, total_words: data.total_words });
                } catch (e) {
                    reject(new Error('Whisper ran but output is unreadable.'));
                }
            }
        });
    });
}

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.log("Usage: node tts_generator.js <\"Full Text To Speak\"> <OutputWavPath> [TimestampsJsonPath]");
    } else if (args[2]) {
        generateTTSWithTimestamps(args[0], args[1], args[2]).catch(err => {
            console.error(err.message);
            process.exit(1);
        });
    } else {
        generateTTS(args[0], args[1]).catch(err => {
            console.error(err.message);
            process.exit(1);
        });
    }
}

module.exports = { generateTTS, generateTTSWithTimestamps };
