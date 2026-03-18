// scraper/youtube_scraper.js
// Scrapes YouTube for top educational videos on a topic and extracts transcripts.
// Usage: node youtube_scraper.js "Topic Name" "Subject" "Class"

const fs = require('fs');
const path = require('path');
const { google } = require('googleapis');

const configPath = path.join(__dirname, '../config.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

const API_KEY = config.youtube.api_key;
const youtube = google.youtube({
  version: 'v3',
  auth: API_KEY
});

// We will load youtube-transcript dynamically in the fetchTranscript function


async function searchYouTube(query, maxResults = 3) {
  try {
    const res = await youtube.search.list({
      part: 'snippet',
      q: query,
      type: 'video',
      maxResults: maxResults,
      regionCode: config.youtube.region_code || 'IN',
      relevanceLanguage: config.youtube.relevance_language || 'en'
    });
    
    return res.data.items.map(item => ({
      videoId: item.id.videoId,
      title: item.snippet.title,
      description: item.snippet.description,
      channelTitle: item.snippet.channelTitle
    }));
  } catch (error) {
    console.error('YouTube Search API Error:', error.message);
    return [];
  }
}

async function fetchTranscript(videoId) {
  try {
    const ytTr = await import('youtube-transcript');
    const YoutubeTranscript = ytTr.YoutubeTranscript;
    const transcript = await YoutubeTranscript.fetchTranscript(videoId);
    // Combine text
    return transcript.map(t => t.text).join(' ');
  } catch (error) {
    console.log(`No transcript found for video ${videoId} (or it is disabled).`);
    return null;
  }
}

async function scrapeTopic(topic, subject, studentClass) {
  console.log(`🔍 Scraping YouTube for: ${topic} (${subject}, Class ${studentClass})`);
  const query = `${topic} CBSE Class ${studentClass} ${subject} explanation in english`;
  
  const videos = await searchYouTube(query, config.youtube.max_results_per_topic || 5);
  console.log(`Found ${videos.length} videos matching query.`);

  const scrapedData = [];
  
  for (const video of videos) {
    // Attempt to get transcript
    const transcriptText = await fetchTranscript(video.videoId);
    if (transcriptText) {
      scrapedData.push({
        ...video,
        transcript: transcriptText
      });
      console.log(`✅ Extracted transcript for: ${video.title}`);
    } else {
        // Fallback to purely description if no transcript
        scrapedData.push({
            ...video,
            transcript: "Transcript unavailable. Description: " + video.description
        });
    }
  }

  // Save to file
  const slug = topic.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  const outDir = path.join(__dirname, '../data');
  if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir);
  }
  
  const filePath = path.join(outDir, `${subject.toLowerCase()}_${slug}.json`);
  fs.writeFileSync(filePath, JSON.stringify(scrapedData, null, 2));
  
  console.log(`💾 Scraped data saved to ${filePath}`);
  return filePath;
}

// CLI execution
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length < 3) {
    console.log("Usage: node youtube_scraper.js \"Topic Name\" \"Subject\" \"Class\"");
    process.exit(1);
  }
  
  scrapeTopic(args[0], args[1], args[2]).then(() => process.exit(0));
}

module.exports = { scrapeTopic, searchYouTube, fetchTranscript };
