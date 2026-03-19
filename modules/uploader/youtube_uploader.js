// youtube_uploader.js
// Handles YouTube OAuth, Video Upload, and precise Playlist Management for Subjects and Chapters

require('dotenv').config({ path: '../.env' });
const fs = require('fs');
const path = require('path');
const { google } = require('googleapis');
const readline = require('readline');

// The OAuth file provided by the user
const CREDENTIALS_PATH = path.join(__dirname, '../client_secret_38777465067-iaku7ck3ormsr8q72noa27ka5l9n12id.apps.googleusercontent.com.json');
const TOKEN_PATH = path.join(__dirname, 'token.json');

const SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
];

/**
 * Reads credentials and authenticates.
 */
async function authorize() {
    if (!fs.existsSync(CREDENTIALS_PATH)) {
        throw new Error(`Credentials file not found at ${CREDENTIALS_PATH}`);
    }

    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH));
    const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
    const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0] || 'urn:ietf:wg:oauth:2.0:oob');

    // Check if we have previously stored a token.
    if (fs.existsSync(TOKEN_PATH)) {
        oAuth2Client.setCredentials(JSON.parse(fs.readFileSync(TOKEN_PATH)));
        return oAuth2Client;
    } else {
        return await getNewToken(oAuth2Client);
    }
}

/**
 * Generates an auth URL, prompts user for auth code, and saves token.
 */
async function getNewToken(oAuth2Client) {
    const authUrl = oAuth2Client.generateAuthUrl({
        access_type: 'offline',
        scope: SCOPES,
    });
    console.log('Authorize this app by visiting this url:\n', authUrl);
    
    // We expect the user to manually run this script once to get the token!
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });

    return new Promise((resolve, reject) => {
        rl.question('Enter the code from that page here: ', async (code) => {
            rl.close();
            try {
                const { tokens } = await oAuth2Client.getToken(code);
                oAuth2Client.setCredentials(tokens);
                fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens));
                console.log('Token stored to', TOKEN_PATH);
                resolve(oAuth2Client);
            } catch (err) {
                reject(new Error('Error retrieving access token: ' + err));
            }
        });
    });
}

/**
 * Searches for a playlist by title. Creates it if it doesn't exist.
 * Returns the playlist ID.
 */
async function getOrCreatePlaylist(youtube, title, description) {
    // Search existing playlists
    const res = await youtube.playlists.list({
        part: 'snippet',
        mine: true,
        maxResults: 50
    });

    const playlists = res.data.items || [];
    const existing = playlists.find(p => p.snippet.title.toLowerCase() === title.toLowerCase());

    if (existing) {
        console.log(`Found existing playlist: "${title}" (${existing.id})`);
        return existing.id;
    }

    // Create new
    console.log(`Creating new playlist: "${title}"`);
    const createRes = await youtube.playlists.insert({
        part: 'snippet,status',
        resource: {
            snippet: {
                title: title,
                description: description || `Educational videos for ${title}`
            },
            status: {
                privacyStatus: 'public' // or unlisted for testing
            }
        }
    });

    return createRes.data.id;
}

/**
 * Adds a video to a specific playlist.
 */
async function addVideoToPlaylist(youtube, videoId, playlistId) {
    console.log(`Adding video ${videoId} to playlist ${playlistId}...`);
    try {
        await youtube.playlistItems.insert({
            part: 'snippet',
            resource: {
                snippet: {
                    playlistId: playlistId,
                    resourceId: {
                        kind: 'youtube#video',
                        videoId: videoId
                    }
                }
            }
        });
        console.log(`Successfully added to playlist.`);
    } catch (err) {
        console.error(`Error adding to playlist: ${err.message}`);
    }
}

/**
 * Main upload function.
 */
async function uploadToYouTube(videoFilePath, info) {
    const { title, description, subject, chapter, stream } = info;

    console.log(`\n📤 Starting YouTube Upload Process for: "${title}"`);
    console.log(`File: ${videoFilePath}`);

    const auth = await authorize();
    const youtube = google.youtube({ version: 'v3', auth });

    // 1. Upload the Video
    console.log('Uploading video (this may take a while)...');
    
    // Use provided SEO enhanced tags, or fall back to default broad tags
    const tags = info.tags || ["education", stream, subject, chapter, "notebooklm", "lecture", "study"];
    
    const res = await youtube.videos.insert({
        part: 'snippet,status',
        notifySubscribers: false,
        resource: {
            snippet: {
                title: title,
                description: description,
                tags: tags,
                categoryId: '27' // Education
            },
            status: {
                privacyStatus: 'unlisted', // Highly recommend unlisted until reviewed! Change to 'public' for full automation
                selfDeclaredMadeForKids: false
            }
        },
        media: {
            body: fs.createReadStream(videoFilePath)
        }
    });

    const videoId = res.data.id;
    const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
    console.log(`✅ Upload complete! Video URL: ${youtubeUrl}`);

    // Set Custom Thumbnail if provided
    if (info.thumbnailPath && fs.existsSync(info.thumbnailPath)) {
        console.log(`🖌️ Uploading custom thumbnail...`);
        try {
            await youtube.thumbnails.set({
                videoId: videoId,
                media: {
                    body: fs.createReadStream(info.thumbnailPath)
                }
            });
            console.log(`✅ Custom thumbnail applied successfully.`);
        } catch (thumbErr) {
            console.error(`⚠️ Failed to set custom thumbnail: ${thumbErr.message}`);
        }
    }

    // 2. Manage Playlists (Subject and Chapter)
    // Create/get Subject playlist
    const subjectPlaylistTitle = `[${stream}] ${subject} Full Course`;
    const subjectPlaylistId = await getOrCreatePlaylist(youtube, subjectPlaylistTitle, `Complete lectures for ${subject} (${stream})`);
    
    // Create/get Chapter playlist
    const chapterPlaylistTitle = `${chapter} | ${subject}`;
    const chapterPlaylistId = await getOrCreatePlaylist(youtube, chapterPlaylistTitle, `Deep dive into ${chapter} for ${subject}`);

    // 3. Add to both playlists
    await addVideoToPlaylist(youtube, videoId, subjectPlaylistId);
    await addVideoToPlaylist(youtube, videoId, chapterPlaylistId);

    console.log("\n🎉 YouTube processing finished.");
    return youtubeUrl;
}

// Command Line execution for testing / standalone
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.log("To generate token only, run with no args. Generating token...");
        authorize().then(() => console.log("Auth success!")).catch(console.error);
    } else if (args.length < 5) {
        console.log("Usage: node youtube_uploader.js <VideoPath> <Title> <Description> <Subject> <Chapter> <Stream>");
    } else {
        const info = {
            title: args[1],
            description: args[2],
            subject: args[3],
            chapter: args[4],
            stream: args[5] || "Education"
        };
        uploadToYouTube(args[0], info).catch(console.error);
    }
}

module.exports = { uploadToYouTube, authorize };
