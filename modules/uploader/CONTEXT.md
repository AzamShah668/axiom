# Uploader Module

## Purpose
Handles YouTube OAuth authentication, video uploads, and playlist management.

## Auth Flow
1. First run: Opens browser for Google OAuth consent
2. Saves token to `modules/uploader/token.json` (gitignored)
3. Subsequent runs: Uses cached token, auto-refreshes if expired
4. Client secret: `client_secret_*.json` in project root (gitignored)

## Playlist Strategy
YouTube doesn't support nested playlists. Workaround:
- **Subject Playlist**: `[BTech] Data Structures Full Course`
- **Chapter Playlist**: `Linked Lists | Data Structures`
- Every uploaded video gets added to **both** playlists automatically

## Error Handling
| Error | Action |
|---|---|
| YouTube API quota exceeded | Wait 24h, retry next day |
| Upload auth expired | Re-run `node modules/uploader/youtube_uploader.js` (no args) |
