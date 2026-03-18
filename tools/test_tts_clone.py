"""Wrapper to test qwen_tts_engine.py and write ALL output to a log file."""
import sys, traceback, os, io

LOG_FILE = r"d:\notebook lm\tts_full_trace.log"

# Redirect both stdout and stderr to the log file
log_handle = open(LOG_FILE, "w", encoding="utf-8")
sys.stdout = log_handle
sys.stderr = log_handle

sys.path.insert(0, r"C:\Users\AZAM RIZWAN\Desktop\QwenTTS-Automation")

try:
    print("=== Starting TTS Clone Test ===")
    print(f"Python: {sys.executable}")
    print(f"Working dir: {os.getcwd()}")

    # Check ref audio exists
    ref_audio = r"d:\notebook lm\voice\Recording (9).m4a"
    print(f"Ref audio exists: {os.path.exists(ref_audio)}")
    print(f"Ref audio size: {os.path.getsize(ref_audio) if os.path.exists(ref_audio) else 'N/A'}")

    # Check voice.md exists and read contents
    ref_text_file = r"d:\notebook lm\voice\voice.md"
    print(f"Ref text file exists: {os.path.exists(ref_text_file)}")
    if os.path.exists(ref_text_file):
        with open(ref_text_file, "r", encoding="utf-8") as f:
            ref_text_content = f.read().strip()
        print(f"Ref text content (first 200 chars): {ref_text_content[:200]}")
    
    from qwen_tts_engine import find_checkpoint

    # Try to find checkpoint
    ckpt = find_checkpoint("base")
    print(f"Base checkpoint found: {ckpt}")
    
    # Check model files
    from pathlib import Path
    ckpt_path = Path(ckpt)
    print(f"Checkpoint dir contents: {list(ckpt_path.iterdir())}")

    # Now try the actual TTS generation
    import torch
    import soundfile as sf
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

    print(f"\nLoading model from: {ckpt}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")

    dtype = torch.float16
    tts = Qwen3TTSModel.from_pretrained(
        ckpt,
        device_map="cuda:0",
        dtype=dtype,
        attn_implementation=None,
    )
    print("Model loaded successfully!")

    # NOTE: ref_text argument expects the TEXT CONTENT, not a file path
    # Read the voice.md file to get the transcript text
    ref_text_for_clone = None
    if os.path.exists(ref_text_file):
        with open(ref_text_file, "r", encoding="utf-8") as f:
            ref_text_for_clone = f.read().strip()

    print(f"\nGenerating voice clone...")
    print(f"  ref_audio: {ref_audio}")
    print(f"  ref_text: {ref_text_for_clone[:100] if ref_text_for_clone else 'None'}...")
    print(f"  text: Hello world test for voice cloning.")

    wavs, sr = tts.generate_voice_clone(
        text="Hello world test for voice cloning.",
        language="Auto",
        ref_audio=ref_audio,
        ref_text=ref_text_for_clone,
        x_vector_only_mode=False,
    )

    out_path = r"d:\notebook lm\voice\test_output.wav"
    sf.write(out_path, wavs[0], sr)
    print(f"\n=== SUCCESS ===")
    print(f"Output written to: {out_path}")
    print(f"Output size: {os.path.getsize(out_path)} bytes")

except Exception as e:
    print(f"\n=== FULL TRACEBACK ===")
    traceback.print_exc()

finally:
    log_handle.flush()
    log_handle.close()
