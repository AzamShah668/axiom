// gemini_prosody_director.js
// STEP 4F.5: Uses Gemini AI to generate per-chunk speaking instructions
// for CosyVoice 2's instruct mode. Analyzes transcript content and produces
// a JSON instruction map that controls tone, pacing, and emotion per chunk.
//
// DOES NOT CHANGE ANY WORDS — only produces speaking directions.

require('dotenv').config({ path: `${__dirname}/../config/.env` });

const { GoogleGenerativeAI } = require('@google/generative-ai');
const fs = require('fs');
const path = require('path');

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const SYSTEM_PROMPT = `You are a professional voice director for educational YouTube videos aimed at engineering students.

Your job: Given a transcript split into numbered chunks, produce a JSON array of per-chunk speaking instructions. These instructions will be fed to a text-to-speech model that supports natural-language style directions.

Rules:
1. The transcript words will NOT be changed — you are only controlling HOW they are spoken.
2. Each instruction should be 1-2 sentences describing the tone, energy, pacing, and emotion for that chunk.
3. Vary the instructions meaningfully across chunks — avoid giving every chunk the same direction.
4. Think like a real voice director coaching a teacher:
   - Introductions and greetings: warm, enthusiastic, welcoming energy
   - Definitions and foundational concepts: clear, patient, slightly slower pace
   - Step-by-step explanations: steady, methodical, building understanding
   - Key insights or "aha moments": build anticipation, then emphasize the revelation
   - Examples and analogies: conversational, relatable, slightly lighter tone
   - Important warnings or common mistakes: serious, slower, emphasizing caution
   - Conclusions and wrap-ups: warm, encouraging, motivational
5. Set speed between 0.85 and 1.1 (1.0 = normal, <1.0 = slower, >1.0 = faster).
   - Slow down for complex concepts, formulas, and key definitions
   - Speed up slightly for transitions and lighter content
6. Return ONLY valid JSON — no markdown, no explanation, no code fences.

Output format (JSON array):
[
  { "index": 0, "instruct": "...", "speed": 1.0 },
  { "index": 1, "instruct": "...", "speed": 0.95 },
  ...
]`;

/**
 * Splits text at sentence boundaries into chunks of roughly chunkWordLimit words.
 * Mirrors the chunking logic in tts_full_generate.py.
 */
function splitIntoChunks(text, chunkWordLimit = 100) {
    const sentences = text.match(/[^.!?]+[.!?]+[\s]*/g) || [text];
    const chunks = [];
    let current = '';
    let currentWords = 0;

    for (const sentence of sentences) {
        const words = sentence.trim().split(/\s+/).length;
        if (currentWords + words > chunkWordLimit && current.trim()) {
            chunks.push(current.trim());
            current = '';
            currentWords = 0;
        }
        current += sentence;
        currentWords += words;
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
}

/**
 * Generates per-chunk speaking instructions using Gemini AI.
 *
 * @param {string} transcriptText — the full enhanced transcript
 * @param {number} [chunkWordLimit=100] — words per chunk (must match TTS chunking)
 * @returns {Promise<Array<{index: number, instruct: string, speed: number}>>}
 */
async function generateProsodyMap(transcriptText, chunkWordLimit = 100) {
    if (!GEMINI_API_KEY) {
        console.warn('⚠️  GEMINI_API_KEY not set — using default prosody instructions.');
        return generateDefaultMap(transcriptText, chunkWordLimit);
    }

    const chunks = splitIntoChunks(transcriptText, chunkWordLimit);
    console.log(`🎬  Prosody Director: analyzing ${chunks.length} chunks with Gemini...`);

    // Build the user prompt with numbered chunks
    const numberedChunks = chunks.map((c, i) => {
        const wordCount = c.split(/\s+/).length;
        return `--- CHUNK ${i} (${wordCount} words) ---\n${c}`;
    }).join('\n\n');

    const userPrompt = `Here is the transcript split into ${chunks.length} chunks. Generate speaking instructions for each chunk.\n\n${numberedChunks}`;

    try {
        const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
        const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });

        const result = await model.generateContent({
            contents: [{ role: 'user', parts: [{ text: userPrompt }] }],
            systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
            generationConfig: {
                temperature: 0.7,
                maxOutputTokens: 4096,
                responseMimeType: 'application/json',
            },
        });

        const responseText = result.response.text().trim();
        let instructions = JSON.parse(responseText);

        // Validate and normalize
        if (!Array.isArray(instructions)) {
            throw new Error('Gemini returned non-array response');
        }

        // Ensure we have an instruction for every chunk
        instructions = chunks.map((_, i) => {
            const found = instructions.find(item => item.index === i);
            if (found) {
                return {
                    index: i,
                    instruct: String(found.instruct || 'Speak clearly and engagingly like a teacher'),
                    speed: Math.max(0.85, Math.min(1.1, Number(found.speed) || 1.0)),
                };
            }
            return { index: i, instruct: 'Speak clearly and engagingly like a teacher explaining to students', speed: 1.0 };
        });

        console.log(`✅  Prosody map: ${instructions.length} chunk instructions generated.`);
        return instructions;

    } catch (err) {
        console.warn(`⚠️  Gemini prosody generation failed: ${err.message}`);
        console.warn('    Falling back to default prosody instructions.');
        return generateDefaultMap(transcriptText, chunkWordLimit);
    }
}

/**
 * Fallback: generates sensible default instructions based on chunk position.
 */
function generateDefaultMap(transcriptText, chunkWordLimit = 100) {
    const chunks = splitIntoChunks(transcriptText, chunkWordLimit);
    const total = chunks.length;

    return chunks.map((_, i) => {
        const position = i / Math.max(total - 1, 1); // 0.0 to 1.0

        if (position < 0.1) {
            return { index: i, instruct: 'Speak with warm excitement, greeting your audience enthusiastically', speed: 1.0 };
        } else if (position < 0.3) {
            return { index: i, instruct: 'Clear and patient tone, introducing the foundational concept step by step', speed: 0.95 };
        } else if (position < 0.7) {
            return { index: i, instruct: 'Engaged teaching voice, explaining with clarity and building understanding', speed: 0.95 };
        } else if (position < 0.9) {
            return { index: i, instruct: 'Emphasize key takeaways, speaking with conviction and authority', speed: 0.9 };
        } else {
            return { index: i, instruct: 'Warm and encouraging wrap-up, motivating the audience to keep learning', speed: 1.0 };
        }
    });
}

/**
 * Generates prosody map and saves it to a JSON file.
 *
 * @param {string} transcriptText — full transcript text
 * @param {string} outputPath — where to save the JSON map
 * @param {number} [chunkWordLimit=100]
 * @returns {Promise<Array>} the prosody map
 */
async function generateAndSave(transcriptText, outputPath, chunkWordLimit = 100) {
    const map = await generateProsodyMap(transcriptText, chunkWordLimit);
    fs.writeFileSync(outputPath, JSON.stringify(map, null, 2), 'utf8');
    console.log(`💾  Prosody map saved: ${outputPath}`);
    return map;
}

// CLI usage: node gemini_prosody_director.js <transcript_file> [output_json]
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.log('Usage: node gemini_prosody_director.js <transcript_file> [output_json]');
        process.exit(0);
    }

    const text = fs.readFileSync(args[0], 'utf8');
    const output = args[1] || args[0].replace(/\.[^.]+$/, '_prosody.json');

    generateAndSave(text, output).catch(err => {
        console.error('Fatal:', err.message);
        process.exit(1);
    });
}

module.exports = { generateProsodyMap, generateAndSave, splitIntoChunks };
