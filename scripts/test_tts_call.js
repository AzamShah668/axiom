// Quick test: does tts_generator.js work end-to-end?
const path = require('path');
const fs = require('fs');
const os = require('os');
const { execSync } = require('child_process');

const GRADIO_URL = 'https://6296ff3a42a4c70d09.gradio.live';
const REF_AUDIO = 'D:/notebook lm/voice/Recording (14).m4a';
const REF_TRANSCRIPT = "Hey everyone, welcome back!";
const OUTPUT_WAV = 'd:/notebook lm/data/test_tts_node.wav';

const pyCode = [
    'import sys, shutil',
    'from gradio_client import Client, handle_file',
    '',
    'print("Starting...")',
    'try:',
    `    client = Client("${GRADIO_URL}")`,
    '    print("Connected, calling predict...")',
    '    result = client.predict(',
    '        text="Hello this is a short test of TTS.",',
    `        ref_audio_path=handle_file(r"${REF_AUDIO}"),`,
    `        ref_text="${REF_TRANSCRIPT}",`,
    '        language="English",',
    '        api_name="/predict"',
    '    )',
    `    shutil.copy(result, "${OUTPUT_WAV.replace(/\\/g, '/')}")`,
    '    print("SUCCESS|" + str(result))',
    'except Exception as e:',
    '    import traceback',
    '    print("ERROR|" + str(e))',
    '    traceback.print_exc()',
    '    sys.exit(1)',
].join('\n');

const tempScript = path.join(os.tmpdir(), 'tts_debug.py');
fs.writeFileSync(tempScript, pyCode, 'utf8');

console.log('Script:', tempScript);
console.log('Content:');
console.log(pyCode);
console.log('---');

try {
    execSync(`"C:\\Users\\AZAM RIZWAN\\qwen-tts-gpu\\Scripts\\python.exe" "${tempScript}"`, {
        stdio: 'inherit',
        timeout: 180000
    });
    console.log('Done!');
    if (fs.existsSync(OUTPUT_WAV)) {
        console.log('Output size:', fs.statSync(OUTPUT_WAV).size, 'bytes');
    }
} catch (e) {
    console.log('Failed:', e.status, e.signal);
}
