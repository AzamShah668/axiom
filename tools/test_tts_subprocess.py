"""Subprocess wrapper to test TTS clone with WAV reference audio."""
import subprocess, sys

python = r"C:\Users\AZAM RIZWAN\qwen-tts-gpu\Scripts\python.exe"
script = r"C:\Users\AZAM RIZWAN\Desktop\QwenTTS-Automation\qwen_tts_engine.py"

# Read voice.md for ref-text
with open(r"d:\notebook lm\voice\voice.md", "r", encoding="utf-8") as f:
    ref_text = f.read().strip()

cmd = [
    python, script,
    "--mode", "clone",
    "--ref-audio", r"d:\notebook lm\voice\short_ref.wav",
    "--ref-text", "Hello my name is Azam Rizwan",
    "--text", "Hello world, this is a voice cloning test for the Axiom YouTube channel.",
    "--out", r"d:\notebook lm\voice\test_output.wav",
    "--language", "en",
    "--device", "cuda:0",
]

print(f"Running TTS clone test with WAV reference...")
print(f"Ref audio: {cmd[5]}")
print(f"Ref text (first 80): {ref_text[:80]}...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

log_path = r"d:\notebook lm\tts_subprocess_log.txt"
with open(log_path, "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout or "(empty)")
    f.write("\n\n=== STDERR ===\n")
    f.write(result.stderr or "(empty)")
    f.write(f"\n\n=== EXIT CODE: {result.returncode} ===\n")

print(f"Exit code: {result.returncode}")
print(f"Log written to: {log_path}")

import os
out_path = r"d:\notebook lm\voice\test_output.wav"
if os.path.exists(out_path):
    print(f"SUCCESS! Output file: {out_path} ({os.path.getsize(out_path)} bytes)")
else:
    print("FAILED - output file not created")
    stderr_tail = (result.stderr or "")[-500:]
    print(f"STDERR tail: {stderr_tail}")
