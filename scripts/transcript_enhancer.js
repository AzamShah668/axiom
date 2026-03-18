// transcript_enhancer.js
// Generates smart, natural intro & outro scripts that blend seamlessly with the NotebookLM transcript.
// The intro flows INTO the topic, and the outro wraps up WITH the topic context.

const fs = require('fs');
const path = require('path');

// A pool of organic intro templates that feel authentic and topic-aware
const INTRO_TEMPLATES = [
    (topic, subject) => `Hey everyone, welcome back to Axiom! Today we're diving deep into ${topic} — this is one of those concepts in ${subject} that a lot of students struggle with, so I wanted to break it down for you in the simplest way possible. Let's get right into it.`,
    (topic, subject) => `What's up everyone, welcome to Axiom! If you've been studying ${subject} and ${topic} still confuses you, don't worry — by the end of this video, you'll have a crystal clear understanding. Let's jump in.`,
    (topic, subject) => `Hey there, welcome to Axiom! So a lot of you have been asking me to cover ${topic} in ${subject}, and I finally got around to making this video. Trust me, once you understand this, everything else in this chapter clicks. Let me explain.`,
    (topic, subject) => `What's going on everyone, welcome back to Axiom! In today's video, we're tackling ${topic} — and honestly, this is a game changer for your ${subject} preparation. Pay close attention because this will definitely come up in your exams. Here we go.`,
    (topic, subject) => `Hey everybody, welcome to Axiom! Today's topic is ${topic} from ${subject}. Now I know this sounds intimidating at first, but I promise you — it's actually really intuitive once you see it the right way. Let me walk you through it.`
];

// Outro templates that wrap up naturally and encourage engagement
const OUTRO_TEMPLATES = [
    (topic) => `And that's everything you need to know about ${topic}! If this video helped you understand the concept better, make sure to hit that like button and drop a comment below telling me which topic you want me to cover next. Don't forget to subscribe to Axiom and turn on the bell icon so you never miss a new lecture. See you in the next one!`,
    (topic) => `So that wraps up our deep dive into ${topic}. I really hope this made things clearer for you. If it did, please like this video — it honestly helps the channel a lot. Subscribe if you haven't already, and let me know in the comments what you'd like to learn next. Until next time, keep studying smart!`,
    (topic) => `Alright, that was ${topic} explained from start to finish. If you found this useful, smash that like button and share this video with a friend who's also studying for exams. Subscribe to Axiom for more lectures like this, and I'll catch you in the next video. Take care!`,
    (topic) => `And there you have it — ${topic} simplified! Remember, understanding the basics is key to cracking exams. Hit like if this helped, subscribe to Axiom for daily lectures, and comment below with any doubts. I read every single comment. See you soon!`,
    (topic) => `That's a wrap on ${topic}! I hope you now feel way more confident about this concept. If you do, show some love — like, comment, and subscribe to Axiom. Every subscription genuinely motivates me to keep making these videos for you. See you in the next one, take care!`
];

/**
 * Enhances a raw NotebookLM transcript with a natural intro and outro.
 * The intro flows INTO the transcript and the outro wraps it up organically.
 *
 * @param {string} rawTranscript - The raw transcript text from NotebookLM
 * @param {string} topicName - The specific topic being covered
 * @param {string} subjectName - The subject (e.g., "Data Structures")
 * @returns {object} - { fullScript, introText, outroText, introWordCount, outroWordCount }
 */
function enhanceTranscript(rawTranscript, topicName, subjectName) {
    // Pick a random intro and outro template
    const introIdx = Math.floor(Math.random() * INTRO_TEMPLATES.length);
    const outroIdx = Math.floor(Math.random() * OUTRO_TEMPLATES.length);

    const introText = INTRO_TEMPLATES[introIdx](topicName, subjectName);
    const outroText = OUTRO_TEMPLATES[outroIdx](topicName);

    // Stitch them together seamlessly
    // The intro ends with a forward-looking transition, the raw transcript begins, and the outro picks up naturally.
    const fullScript = `${introText}\n\n${rawTranscript.trim()}\n\n${outroText}`;

    // Calculate approximate word counts for timing calculations
    const introWordCount = introText.split(/\s+/).length;
    const outroWordCount = outroText.split(/\s+/).length;
    const totalWordCount = fullScript.split(/\s+/).length;

    // Estimate durations (avg 150 words per minute for clear narration)
    const wordsPerSecond = 2.5; // 150 WPM
    const introDurationSec = Math.ceil(introWordCount / wordsPerSecond);
    const outroDurationSec = Math.ceil(outroWordCount / wordsPerSecond);

    console.log(`📝 Transcript Enhanced!`);
    console.log(`   Intro: ~${introWordCount} words (~${introDurationSec}s)`);
    console.log(`   Main body: ~${(totalWordCount - introWordCount - outroWordCount)} words`);
    console.log(`   Outro: ~${outroWordCount} words (~${outroDurationSec}s)`);

    return {
        fullScript,
        introText,
        outroText,
        introWordCount,
        outroWordCount,
        totalWordCount,
        introDurationSec,
        outroDurationSec
    };
}

// CLI for testing
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 3) {
        console.log("Usage: node transcript_enhancer.js <transcript_file> <topic> <subject>");
    } else {
        const transcript = fs.readFileSync(args[0], 'utf8');
        const result = enhanceTranscript(transcript, args[1], args[2]);
        const outPath = path.join(__dirname, '../data/enhanced_transcript.txt');
        fs.writeFileSync(outPath, result.fullScript, 'utf8');
        console.log(`\nEnhanced transcript saved to: ${outPath}`);
    }
}

module.exports = { enhanceTranscript };
