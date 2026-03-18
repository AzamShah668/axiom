// tts_generator.js
// Integrates with the local Qwen TTS GPU Engine using the Gradio API.
// KEY FIX: Chunks large text into ~60-word pieces to prevent the server from hanging/OOMing,
// then stitches all WAV chunks together using FFmpeg.

const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const PYTHON_EXECUTABLE = `"C:\\Users\\AZAM RIZWAN\\qwen-tts-gpu\\Scripts\\python.exe"`;
const MAX_WORDS_PER_CHUNK = 60;
const TTS_TIMEOUT_MS = 3 * 60 * 1000; // 3 min per chunk

/**
 * Splits text into sentence-aware chunks of approximately MAX_WORDS_PER_CHUNK words.
 */
function chunkText(text) {
    // Split on sentence boundaries
    const sentences = text.match(/[^.!?]+[.!?]+[\s]*/g) || [text];
    const chunks = [];
    let current = '';
    let wordCount = 0;

    for (const sentence of sentences) {
        const words = sentence.trim().split(/\s+/).length;
        if (wordCount + words > MAX_WORDS_PER_CHUNK && current.trim()) {
            chunks.push(current.trim());
            current = sentence;
            wordCount = words;
        } else {
            current += ' ' + sentence;
            wordCount += words;
        }
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks.filter(c => c.length > 2);
}

/**
 * Generates a single WAV chunk from text using the local Qwen TTS Gradio server.
 * @param {string} text - Text for this chunk.
 * @param {string} outputPath - Path where the .wav should be saved.
 * @returns {Promise<string>}
 */
function synthesizeChunk(text, outputPath) {
    const tempPyScriptPath = path.join(os.tmpdir(), `gradio_chunk_${Date.now()}.py`);
    const escapedText = JSON.stringify(text);
    // Use forward slashes in the Python script to avoid Windows backslash issues
    const pyOutputPath = outputPath.replace(/\\/g, '/');

    const pyCode = `
import sys, shutil
from gradio_client import Client

try:
    client = Client("http://127.0.0.1:8000/")
    
    result = client.predict(
        text=${escapedText},
        lang_disp="English",
        spk_disp="Dylan",
        instruct="narrate in a natural, engaging way. speak clearly and at a steady pace.",
        api_name="/run_instruct"
    )
    
    audio_wav = result[0]
    shutil.copy(audio_wav, "${pyOutputPath}")
    print("SUCCESS|" + audio_wav)
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
        const child = exec(command, { maxBuffer: 1024 * 1024 * 10, timeout: TTS_TIMEOUT_MS }, (error, stdout, stderr) => {
            // Keep temp script on error for debugging, cleanup on success
            if (error) {
                const logMsg = `ERROR:\n${error.message}\n\nSTDOUT:\n${stdout}\n\nSTDERR:\n${stderr}\n\nSCRIPT:\n${tempPyScriptPath}`;
                fs.writeFileSync(path.join(__dirname, '..', 'js_python_error.log'), logMsg);
                try { fs.unlinkSync(tempPyScriptPath); } catch (_) {}
                return reject(new Error(`TTS chunk failed: ${error.message}\nSTDOUT: ${stdout}\nSTDERR: ${stderr}`));
            }
            if (!fs.existsSync(outputPath)) {
                return reject(new Error(`TTS chunk returned success but output missing. STDOUT: ${stdout}`));
            }
            resolve(outputPath);
        });
    });
}

/**
 * Stitches multiple WAV files into one using FFmpeg concat demuxer.
 * @param {string[]} wavPaths - List of .wav file paths to concatenate.
 * @param {string} outputPath - Final output .wav path.
 * @returns {Promise<string>}
 */
function stitchWavFiles(wavPaths, outputPath) {
    const listFile = path.join(os.tmpdir(), `ffmpeg_concat_${Date.now()}.txt`);
    const content = wavPaths.map(p => `file '${p.replace(/\\/g, '/')}'`).join('\n');
    fs.writeFileSync(listFile, content, 'utf8');

    const command = `ffmpeg -y -f concat -safe 0 -i "${listFile}" -c copy "${outputPath}"`;

    return new Promise((resolve, reject) => {
        exec(command, { timeout: 60000 }, (error, stdout, stderr) => {
            try { fs.unlinkSync(listFile); } catch (_) {}
            if (error) {
                return reject(new Error(`FFmpeg stitch failed: ${error.message}\n${stderr}`));
            }
            resolve(outputPath);
        });
    });
}

/**
 * Main entry point: Chunks text, synthesizes each chunk, stitches output.
 * @param {string} transcriptText - Full text to synthesize.
 * @param {string} outputPath - Final .wav destination.
 * @returns {Promise<string>}
 */
async function generateTTS(transcriptText, outputPath) {
    console.log(`\n🎙️ Starting Qwen TTS with chunked synthesis...`);

    // Sanitize
    const safeText = transcriptText
        .replace(/\0/g, '')
        .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/g, ' ');

    const chunks = chunkText(safeText);
    console.log(`📦 Split into ${chunks.length} chunks (max ${MAX_WORDS_PER_CHUNK} words/chunk)`);

    const tempDir = path.join(os.tmpdir(), `tts_chunks_${Date.now()}`);
    fs.mkdirSync(tempDir, { recursive: true });

    const chunkPaths = [];
    for (let i = 0; i < chunks.length; i++) {
        const chunkPath = path.join(tempDir, `chunk_${String(i).padStart(3, '0')}.wav`);
        const wordCount = chunks[i].split(/\s+/).length;
        console.log(`  🔊 Chunk ${i + 1}/${chunks.length} (~${wordCount} words)...`);
        await synthesizeChunk(chunks[i], chunkPath);
        chunkPaths.push(chunkPath);
        console.log(`  ✅ Chunk ${i + 1} done.`);
    }

    if (chunkPaths.length === 1) {
        fs.copyFileSync(chunkPaths[0], outputPath);
    } else {
        console.log(`🎵 Stitching ${chunkPaths.length} audio chunks...`);
        await stitchWavFiles(chunkPaths, outputPath);
    }

    // Cleanup temp chunks
    try { chunkPaths.forEach(p => fs.unlinkSync(p)); } catch (_) {}
    try { fs.rmdirSync(tempDir); } catch (_) {}

    console.log(`✅ Full TTS audio saved to: ${outputPath}`);
    return outputPath;
}

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.log("Usage: node tts_generator.js <\"Text To Speak\"> <OutputWavPath>");
    } else {
        generateTTS(args[0], args[1]).catch(err => {
            console.error(err.message);
            process.exit(1);
        });
    }
}

module.exports = { generateTTS };
