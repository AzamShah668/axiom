// seo_generator.js
// Generates VIRAL, attention-grabbing YouTube titles, descriptions, and tags.
// Uses multiple proven hook formulas rotated for variety.

/**
 * Generates SEO metadata optimized for virality and algorithm reach.
 * @param {string} topic   - e.g., "QuickSort"
 * @param {string} subject - e.g., "DSA"
 * @param {string} chapter - e.g., "Sorting Algorithms"
 * @param {object} [opts]  - Optional overrides
 * @returns {{ title: string, description: string, tags: string[] }}
 */
function generateSEOMetadata(topic, subject, chapter, opts = {}) {

    // ─── 1. VIRAL TITLE GENERATOR ────────────────────────────────────

    const titleFormulas = [
        `Watch This and You'll FINALLY Understand ${topic}`,
        `${topic} — The Video I WISH I Had Before My Exam`,
        `${topic} Explained So Well, You'll Never Forget It`,
        `How ${topic} ACTUALLY Works (${subject})`,
        `I Taught ${topic} to 1000 Students — Here's the BEST Way`,
        `${topic} in ${subject}: Once You See This, It Clicks`,
        `Stop Memorizing ${topic} — UNDERSTAND It Instead`,
        `${topic} | The Only Video You'll Ever Need (${chapter})`,
        `Why Most Students Get ${topic} WRONG — And How to Fix It`,
        `${topic} — From Zero to Hero in One Video`,
        `The Secret Behind ${topic} That Teachers Don't Tell You`,
        `${topic} Made RIDICULOUSLY Simple | ${subject}`,
    ];

    const titleIndex = opts.titleIndex ?? Math.floor(Math.random() * titleFormulas.length);
    const title = titleFormulas[titleIndex % titleFormulas.length].substring(0, 100);

    // ─── 2. ALGORITHM-OPTIMIZED DESCRIPTION ──────────────────────────

    // YouTube shows the first ~120 chars in search results — pack keywords here
    const description = `🚀 ${topic} in ${subject} — the COMPLETE breakdown you've been looking for!

In this video, we go deep into ${chapter}, covering ${topic} from the absolute basics to exam-level mastery. Whether you're prepping for semester exams, GATE, placements, or just want to truly understand the concept — this is the one video you need.

📌 What You'll Learn:
• Core definition & intuition behind ${topic}
• Step-by-step worked examples with dry runs
• Common mistakes & how to avoid them
• Time & space complexity analysis
• Real interview questions on ${topic}

⏱️ Timestamps:
0:00 — Intro & Why ${topic} Matters
0:30 — Core Concept Explained
2:00 — Step-by-Step Example
4:30 — Common Mistakes
6:00 — Complexity Analysis
7:30 — Interview Questions & Recap

🔥 If this helped, smash that LIKE button and SUBSCRIBE for daily ${subject} videos!

📚 Part of our ${chapter} series in ${subject}.

#${topic.replace(/\s+/g, '')} #${subject.replace(/\s+/g, '')} #${chapter.replace(/\s+/g, '')} #Education #Engineering #ExamPrep #GATE #Placements #CodingInterview #BTech #CSE #LearnWithMe
`.trim();

    // ─── 3. COMPETITIVE TAGS (long-tail + broad) ─────────────────────

    const topicLower = topic.toLowerCase();
    const subjectLower = subject.toLowerCase();
    const chapterLower = chapter.toLowerCase();

    const tags = [
        // Exact match Keywords (highest priority)
        topicLower,
        `${topicLower} explained`,
        `${topicLower} in ${subjectLower}`,
        `${topicLower} tutorial`,

        // Long-tail variations
        `${topicLower} for beginners`,
        `${topicLower} step by step`,
        `${topicLower} with example`,
        `${topicLower} interview questions`,
        `${topicLower} gate`,
        `${topicLower} placement`,

        // Chapter-level
        chapterLower,
        `${chapterLower} ${subjectLower}`,
        `${chapterLower} full chapter`,

        // Subject-level
        subjectLower,
        `${subjectLower} lecture`,
        `${subjectLower} class 11`,
        `${subjectLower} class 12`,
        `${subjectLower} btech`,
        `${subjectLower} notes`,

        // Broad education
        "education",
        "exam prep",
        "semester exam",
        "engineering",
        "ncert",
        "cbse",
        "gate preparation",
        "coding interview",
        "learn with me",
        "study tips",
    ];

    // Deduplicate + strip commas (YouTube uses commas as tag separators) + enforce 30-char limit
    const uniqueTags = [...new Set(tags)].map(t => t.replace(/,/g, '').replace(/\s{2,}/g, ' ').trim().substring(0, 30));

    // YouTube enforces a 500-character total limit on tags. Internally it counts
    // each tag as "tag" (quoted) separated by commas: "tag1","tag2",...
    // So the real cost per tag = tag.length + 3 (2 quotes + 1 comma).
    const finalTags = [];
    let totalLen = 0;
    for (const tag of uniqueTags) {
        const cost = tag.length + 3; // 2 quotes + comma
        if (totalLen + cost > 495) break;
        finalTags.push(tag);
        totalLen += cost;
    }

    return {
        title,
        description: description.substring(0, 4900), // YouTube limit: 5000 chars
        tags: finalTags,
    };
}

module.exports = { generateSEOMetadata };
