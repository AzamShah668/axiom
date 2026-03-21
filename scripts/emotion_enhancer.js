// emotion_enhancer.js
// Step 4F: Rule-based emotion marker enhancement (no external API needed).
// Adds natural punctuation (!, ?, ..., commas) and emphasis to make TTS sound human.
// CONSTRAINT: Does NOT change any words — only adds/modifies punctuation.

const fs = require('fs');
const path = require('path');

// ── Patterns that trigger rhetorical question marks ───────────────────────────

const QUESTION_STARTERS = [
    /\b(why|how|what|when|where|which|who)\b.{10,60}[.]/gi,
    /\b(but why|so why|so how|and why|then why|then what)\b.{5,50}[.]/gi,
    /\b(you might wonder|you may ask|you might ask)\b.{5,60}[.]/gi,
];

// ── Words/phrases that get trailing ! ─────────────────────────────────────────

const EXCLAIM_AFTER = [
    /\b(that's it|simple as that|easy right|makes sense right|and that's how|and that's why|remember that|key insight|the answer is|turns out)\b([^.!?]*)[.]/gi,
    /\b(brilliant|amazing|perfect|exactly|correct|absolutely)\b([^.!?]*)[.]/gi,
];

// ── Phrases that get ... before them (suspense / reveal) ─────────────────────

const SUSPENSE_BEFORE = [
    /([,.])\s+(the answer is|the result is|and the output|which means|which gives us|so the final)/gi,
    /([,.])\s+(but here's the thing|but wait|but there's more|now here's where)/gi,
    /([,.])\s+(this is where it gets|this is the key|this is what makes)/gi,
];

// ── Phrases that get a comma after for breathing room ────────────────────────

const COMMA_AFTER = [
    // "Now" / "So" / "Well" at sentence start
    /^(Now|So|Well|Right|Okay|Alright|Look|See|Think about it|Remember|Notice)\s/gm,
    // Conjunctions that benefit from a pause
    /\b(however|therefore|furthermore|moreover|in other words|in fact|actually|basically)\b\s/gi,
];

// ── Sentence endings to upgrade to ! ─────────────────────────────────────────

const EXCITING_ENDINGS = [
    /\b(it works|it runs|it sorts|it completes|we're done|we got it|nailed it|that's correct|that's right)\b([^.!?]*)\./gi,
];

// ── Key educational terms to CAPITALIZE for emphasis ─────────────────────────

const EMPHASIS_WORDS = [
    'pivot', 'recursion', 'base case', 'time complexity', 'space complexity',
    'worst case', 'best case', 'average case', 'key', 'important', 'critical',
    'remember', 'never forget', 'always', 'never', 'the trick is', 'note that',
];

/**
 * Pure rule-based emotion enhancement.
 * Modifies punctuation and capitalization only — no words added or removed.
 *
 * @param {string} text
 * @returns {Promise<string>}
 */
async function enhanceWithEmotions(text) {
    console.log('🎭 Humanizing transcript with rule-based emotion markers...');

    let out = text;

    // 1. Add suspense ... before reveal phrases
    for (const [pattern, replacement] of SUSPENSE_BEFORE.map(p => [p, null])) {
        out = out.replace(SUSPENSE_BEFORE[SUSPENSE_BEFORE.indexOf(pattern)], (match, punct, phrase) => {
            return `${punct} ...${phrase}`;
        });
    }
    // Reapply cleanly
    out = text;
    out = out.replace(/([,.]) (the answer is|the result is|and the output|which means|which gives us|so the final)/gi,
        (_, punct, phrase) => `${punct} ...${phrase}`);
    out = out.replace(/([,.]) (but here's the thing|but wait|but there's more|now here's where)/gi,
        (_, punct, phrase) => `${punct} ...${phrase}`);
    out = out.replace(/([,.]) (this is where it gets|this is the key|this is what makes)/gi,
        (_, punct, phrase) => `${punct} ...${phrase}`);

    // 2. Upgrade select sentence endings to !
    out = out.replace(/\b(it works|it runs|it sorts|it completes|we're done|we got it|nailed it|that's correct|that's right)([^.!?]*)\.(?!\s*\.)/gi,
        (match, phrase, rest) => `${phrase}${rest}!`);
    out = out.replace(/\b(simple as that|easy right|makes sense right|and that's how|and that's why|the answer is)([^.!?]*)\.(?!\s*\.)/gi,
        (match, phrase, rest) => `${phrase}${rest}!`);

    // 3. Convert obvious rhetorical questions from . to ?
    out = out.replace(/\b(why does|why do|how does|how do|what happens|what is|what are|can you see|do you see|makes sense)\b([^.!?]{5,60})\./gi,
        (match, starter, rest) => `${starter}${rest}?`);

    // 4. Add comma after sentence-opening connectors
    out = out.replace(/^(Now|So|Well|Right|Okay|Alright|Look|See|Remember|Notice) ([A-Z])/gm,
        (_, word, next) => `${word}, ${next}`);
    out = out.replace(/\b(however|therefore|furthermore|moreover|in other words|in fact|actually|basically) ([a-z])/gi,
        (_, connector, next) => `${connector}, ${next}`);

    // 5. Add em-dash pauses before dramatic reveals
    out = out.replace(/\b(and the answer is|and the result is|and it turns out|and here's the thing) /gi,
        (match, phrase) => `${phrase} — `);

    // 6. Light capitalization on emphasis words (only when standalone in sentence)
    const emphasisTargets = ['key', 'important', 'critical', 'remember', 'always', 'never'];
    for (const word of emphasisTargets) {
        const re = new RegExp(`\\b(${word})\\b`, 'g');
        out = out.replace(re, word.toUpperCase());
    }

    // Validate: word count must not change
    const origWords = text.trim().split(/\s+/).length;
    const newWords  = out.trim().split(/\s+/).length;
    const drift = Math.abs(origWords - newWords) / origWords;

    if (drift > 0.03) {
        console.warn(`   Word count drifted (${origWords} → ${newWords}) — using original.`);
        return text;
    }

    const changes = countChanges(text, out);
    console.log(`   Done: ${changes} punctuation/emphasis changes applied.`);
    return out;
}

function countChanges(original, enhanced) {
    let count = 0;
    for (let i = 0; i < Math.min(original.length, enhanced.length); i++) {
        if (original[i] !== enhanced[i]) count++;
    }
    count += Math.abs(original.length - enhanced.length);
    return count;
}

// CLI
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.log('Usage: node emotion_enhancer.js <transcript_file> [output_file]');
        process.exit(0);
    }

    const inputText = fs.readFileSync(args[0], 'utf8');
    const outputFile = args[1] || args[0].replace('.txt', '_emotional.txt');

    enhanceWithEmotions(inputText).then(enhanced => {
        fs.writeFileSync(outputFile, enhanced, 'utf8');
        console.log(`Saved to: ${outputFile}`);
    }).catch(err => {
        console.error('Fatal:', err.message);
        process.exit(1);
    });
}

module.exports = { enhanceWithEmotions };
