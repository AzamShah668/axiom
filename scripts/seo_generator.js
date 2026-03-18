// seo_generator.js
// Generates viral, highly-targeted YouTube titles, descriptions, and tags.

/**
 * Generates SEO metadata based on the subject and topic.
 * @param {string} topic - The specific topic of the video (e.g., "Newton's First Law")
 * @param {string} subject - The broader subject (e.g., "Physics")
 * @param {string} chapter - The chapter name (e.g., "Laws of Motion")
 * @returns {Object} { title, description, tags }
 */
function generateSEOMetadata(topic, subject, chapter) {
    // 1. Generate a Catchy Title
    // We want the primary keyword early, plus a hook or emotional trigger.
    const hookPhrases = [
        "Explained in 5 Minutes!",
        "The Easiest Explanation",
        "Master this in One Video",
        "Exam Prep Masterclass",
        "Everything You Need To Know",
        "Explained Simply"
    ];
    const randomHook = hookPhrases[Math.floor(Math.random() * hookPhrases.length)];
    const title = `${topic} | ${chapter} | ${subject} - ${randomHook}`;

    // 2. Generate a Viral Description
    const descriptionTemplate = `
🚀 Master ${topic} in ${subject}! 
In this video, we dive deep into ${chapter}, breaking down the core concepts of ${topic} so you can understand it easily and ace your exams.

📚 What you will learn:
- Clear, simple definitions of ${topic}
- Core concepts and theories from ${chapter}
- Real-world examples and applications

Make sure to LIKE 👍 and SUBSCRIBE 🔔 for more premium educational content on ${subject}!

#${subject.replace(/\s+/g, '')} #${chapter.replace(/\s+/g, '')} #${topic.replace(/\s+/g, '')} #Education #Studying #ExamPrep #BoardExams #NCERT
`;

    // 3. Generate Targeted Tags
    // Mix of broad, specific, and trending keywords
    const baseTags = [
        "education", "study", "lecture", "exam prep", "ncert", "cbse"
    ];
    
    // Add specific topic and subject tags, breaking them down by words too
    const specificTags = [
        subject.toLowerCase(),
        chapter.toLowerCase(),
        topic.toLowerCase(),
        `${subject} class 11`, 
        `${subject} class 12`,
        `${topic} explained`,
        `${chapter} full chapter`
    ];

    // Combine and deduplicate, ensuring we stay within YouTube limits (approx 500 chars total for tags)
    const combinedTags = [...new Set([...specificTags, ...baseTags])];
    
    // Safety check: ensure no tag is too long (YouTube limit: 30 chars per tag)
    const validTags = combinedTags.map(tag => tag.substring(0, 30));

    return {
        title: title.substring(0, 100), // YouTube limit: 100 chars
        description: descriptionTemplate.trim(), // YouTube limit: 5000 chars
        tags: validTags
    };
}

module.exports = { generateSEOMetadata };
