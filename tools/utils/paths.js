/**
 * Centralized path constants for the EduContent pipeline.
 * Import from here instead of hardcoding paths across modules.
 */
const path = require('path');

const ROOT           = path.resolve(__dirname, '..', '..');
const OUTPUT_DIR     = path.join(ROOT, 'output');
const VIDEOS_DIR     = path.join(OUTPUT_DIR, 'videos');
const NOTEBOOKLM_RAW = path.join(OUTPUT_DIR, 'notebooklm_raw');
const SNAPSHOTS_DIR  = path.join(OUTPUT_DIR, 'snapshots');
const LOGS_DIR       = path.join(ROOT, 'logs');
const DATA_DIR       = path.join(ROOT, 'data');
const ASSETS_DIR     = path.join(ROOT, 'assets');
const VOICE_DIR      = path.join(ROOT, 'voice');

const CHROME_EXE       = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const CHROME_USER_DATA = 'C:\\Users\\AZAM RIZWAN\\AppData\\Local\\Google\\Chrome\\User Data';
const CHROME_PROFILE   = 'Profile 4';
const DEBUG_PORT       = 9222;

const PYTHON_EXECUTABLE = 'C:\\Users\\AZAM RIZWAN\\qwen-tts-gpu\\Scripts\\python.exe';
const REF_AUDIO_PATH    = path.join(VOICE_DIR, 'Recording (14).m4a');

const FONT_PATH = 'C\\:/Windows/Fonts/arialbd.ttf'; // FFmpeg drawtext format

module.exports = {
    ROOT, OUTPUT_DIR, VIDEOS_DIR, NOTEBOOKLM_RAW, SNAPSHOTS_DIR,
    LOGS_DIR, DATA_DIR, ASSETS_DIR, VOICE_DIR,
    CHROME_EXE, CHROME_USER_DATA, CHROME_PROFILE, DEBUG_PORT,
    PYTHON_EXECUTABLE, REF_AUDIO_PATH, FONT_PATH,
};
