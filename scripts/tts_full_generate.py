"""
tts_full_generate.py
Full TTS generation: chunked Gradio calls + concat + Whisper timestamps.
Bypasses Node.js exec() issues by running entirely in Python.

Supports both Qwen3 and CosyVoice 2 (auto-detected from Gradio API).
When a prosody_map.json is provided, per-chunk instruct_text and speed
are passed to CosyVoice 2's instruct mode for varied, natural delivery.

Usage:
  python tts_full_generate.py <transcript_file> <output_wav> <timestamps_json> <gradio_url> [prosody_map_json]
"""

import sys
import os
import json
import shutil
import time
import tempfile
import subprocess
import whisper

CHUNK_WORD_LIMIT = 100  # ~100 words per chunk — keeps each call under 5 min on T4 GPU
REF_AUDIO = "D:/notebook lm/voice/Recording (14).m4a"
REF_TRANSCRIPT = "Hey everyone, welcome back! Have you ever wondered how artificial intelligence is changing the way we learn? Today, we are going to explore some incredible new concepts together. It's truly fascinating, and I know you're going to love it."
MAX_RETRIES = 3
MIN_WAV_SIZE = 10 * 1024  # 10KB
DEFAULT_INSTRUCT = "Speak clearly and engagingly like a teacher explaining concepts to engineering students"


def split_into_chunks(text):
    """Split text at sentence boundaries into ~100-word chunks."""
    import re
    sentences = re.findall(r'[^.!?]+[.!?]+[\s]*', text)
    if not sentences:
        sentences = [text]

    chunks = []
    current = ''
    current_words = 0

    for sentence in sentences:
        words = len(sentence.strip().split())
        if current_words + words > CHUNK_WORD_LIMIT and current.strip():
            chunks.append(current.strip())
            current = ''
            current_words = 0
        current += sentence
        current_words += words

    if current.strip():
        chunks.append(current.strip())

    return chunks


def detect_api_mode(gradio_url):
    """Detect whether the Gradio server is CosyVoice 2 or Qwen3.
    CosyVoice 2's Gradio API accepts 5 params (text, ref_audio, ref_text, instruct_text, speed).
    Qwen3 accepts 4 params (text, ref_audio, ref_text, language)."""
    from gradio_client import Client
    import httpx

    try:
        client = Client(gradio_url, httpx_kwargs={"timeout": httpx.Timeout(30.0)})
        api_info = client.view_api(print_info=False, return_format="dict")

        # Check named endpoints for our CosyVoice 2 notebook's /predict with 5 params
        for ep_key in api_info.get("named_endpoints", {}):
            ep = api_info["named_endpoints"][ep_key]
            params = ep.get("parameters", [])
            param_names = [p.get("parameter_name", "") for p in params]
            # CosyVoice 2 has instruct_text param; Qwen3 has language param
            if "instruct_text" in param_names:
                return "cosyvoice2"
    except Exception as e:
        print(f"   [WARN] API detection failed: {e} — assuming Qwen3")

    return "qwen3"


def generate_chunk_cosyvoice2(gradio_url, text, output_path, instruct_text=None, speed=1.0):
    """Generate TTS for a single chunk via CosyVoice 2 Gradio (instruct mode).
    The Gradio API matches our CosyVoice2_TTS_Server.ipynb notebook:
      /predict(text, ref_audio_path, ref_text, instruct_text, speed)
    instruct_text must end with <|endofprompt|> for the model to work correctly."""
    from gradio_client import Client, handle_file
    import httpx

    instruct = instruct_text or DEFAULT_INSTRUCT

    # CosyVoice 2 requires instruct_text to end with <|endofprompt|>
    if instruct and not instruct.strip().endswith('<|endofprompt|>'):
        instruct = instruct.strip() + '<|endofprompt|>'

    client = Client(gradio_url, httpx_kwargs={"timeout": httpx.Timeout(300.0)})

    # Primary: our notebook's /predict API (5 params)
    try:
        result = client.predict(
            text,                           # Text to synthesize
            handle_file(REF_AUDIO),         # Reference audio (voice to clone)
            REF_TRANSCRIPT,                 # Reference text
            instruct,                       # Instruct text (speaking style)
            speed,                          # Speed (0.5-2.0)
            api_name="/predict"
        )
    except Exception as e1:
        # Fallback: zero-shot without instruct (empty instruct_text)
        print(f"   [WARN] Instruct mode failed ({e1}), trying zero-shot...")
        try:
            result = client.predict(
                text,
                handle_file(REF_AUDIO),
                REF_TRANSCRIPT,
                "",                         # Empty instruct = zero-shot mode
                speed,
                api_name="/predict"
            )
        except Exception as e2:
            # Final fallback: Qwen3-style API
            print(f"   [WARN] CosyVoice2 fallback failed ({e2}), trying Qwen3 API...")
            result = client.predict(
                text=text,
                ref_audio_path=handle_file(REF_AUDIO),
                ref_text=REF_TRANSCRIPT,
                language="English",
                api_name="/predict"
            )

    shutil.copy(result, output_path)

    size = os.path.getsize(output_path)
    if size < MIN_WAV_SIZE:
        raise Exception(f"Output too small ({size} bytes)")

    return output_path


def generate_chunk_qwen3(gradio_url, text, output_path):
    """Generate TTS for a single chunk via Qwen3 Gradio (legacy)."""
    from gradio_client import Client, handle_file
    import httpx

    client = Client(gradio_url, httpx_kwargs={"timeout": httpx.Timeout(300.0)})
    result = client.predict(
        text=text,
        ref_audio_path=handle_file(REF_AUDIO),
        ref_text=REF_TRANSCRIPT,
        language="English",
        api_name="/predict"
    )
    shutil.copy(result, output_path)

    size = os.path.getsize(output_path)
    if size < MIN_WAV_SIZE:
        raise Exception(f"Output too small ({size} bytes)")

    return output_path


def generate_chunk(gradio_url, text, output_path, mode="qwen3", instruct_text=None, speed=1.0):
    """Route to the correct TTS backend."""
    if mode == "cosyvoice2":
        return generate_chunk_cosyvoice2(gradio_url, text, output_path, instruct_text, speed)
    else:
        return generate_chunk_qwen3(gradio_url, text, output_path)


def concat_wavs(wav_paths, output_path):
    """Concatenate WAV files using ffmpeg."""
    list_file = os.path.join(tempfile.gettempdir(), f"tts_concat_{int(time.time())}.txt")
    with open(list_file, 'w') as f:
        for p in wav_paths:
            abs_p = os.path.abspath(p).replace(os.sep, '/')
            f.write(f"file '{abs_p}'\n")

    abs_out = os.path.abspath(output_path).replace(os.sep, '/')
    abs_list = list_file.replace(os.sep, '/')
    cmd = f'ffmpeg -y -f concat -safe 0 -i "{abs_list}" -c copy "{abs_out}"'
    subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=60)

    try:
        os.unlink(list_file)
    except:
        pass


def run_whisper(audio_path, output_json):
    """Run Whisper on audio to get word-level timestamps."""
    print(f"\n[WHISPER] Running Whisper on TTS output...")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, language="en", word_timestamps=True, verbose=False)

    words = []
    segments = []
    for seg in result.get("segments", []):
        seg_data = {
            "id": seg["id"],
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip(),
            "words": []
        }
        for w in seg.get("words", []):
            wd = {"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)}
            seg_data["words"].append(wd)
            words.append(wd)
        segments.append(seg_data)

    output = {
        "duration": round(segments[-1]["end"], 3) if segments else 0,
        "total_words": len(words),
        "total_segments": len(segments),
        "full_text": result.get("text", "").strip(),
        "segments": segments,
        "words": words
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[OK] Whisper: {output['total_words']} words, {output['duration']:.1f}s")
    return output


def load_prosody_map(prosody_path):
    """Load the prosody instruction map generated by gemini_prosody_director.js."""
    if not prosody_path or not os.path.exists(prosody_path):
        return None
    try:
        with open(prosody_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"   [WARN] Could not load prosody map: {e}")
        return None


def get_chunk_instruction(prosody_map, chunk_index):
    """Get instruct_text and speed for a specific chunk from the prosody map."""
    if not prosody_map:
        return DEFAULT_INSTRUCT, 1.0
    for entry in prosody_map:
        if entry.get("index") == chunk_index:
            return entry.get("instruct", DEFAULT_INSTRUCT), entry.get("speed", 1.0)
    return DEFAULT_INSTRUCT, 1.0


def main():
    if len(sys.argv) < 5:
        print("Usage: python tts_full_generate.py <transcript_file> <output_wav> <timestamps_json> <gradio_url> [prosody_map_json]")
        sys.exit(1)

    transcript_file = sys.argv[1]
    output_wav = sys.argv[2]
    timestamps_json = sys.argv[3]
    gradio_url = sys.argv[4]
    prosody_path = sys.argv[5] if len(sys.argv) > 5 else None

    text = open(transcript_file, 'r', encoding='utf-8').read().strip()
    word_count = len(text.split())

    # Load prosody map if available
    prosody_map = load_prosody_map(prosody_path)
    has_prosody = prosody_map is not None
    print(f"\n[TTS]  TTS Full Generate (Python)")
    print(f"   Words: {word_count}")
    print(f"   Gradio: {gradio_url}")
    print(f"   Prosody map: {'loaded (' + str(len(prosody_map)) + ' instructions)' if has_prosody else 'none (using defaults)'}")

    # Detect TTS model
    mode = detect_api_mode(gradio_url)
    print(f"   TTS engine: {mode.upper()}")

    chunks = split_into_chunks(text)
    print(f"   Chunks: {len(chunks)}")

    if len(chunks) == 1:
        # Single chunk — direct call
        instruct, speed = get_chunk_instruction(prosody_map, 0)
        print(f"\n   Single chunk ({word_count} words)...")
        if mode == "cosyvoice2":
            print(f"   Instruct: \"{instruct[:60]}...\"  Speed: {speed}")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                generate_chunk(gradio_url, chunks[0], output_wav, mode, instruct, speed)
                print(f"   [OK] Done!")
                break
            except Exception as e:
                print(f"   [FAIL] Attempt {attempt} failed: {e}")
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(5 * attempt)
    else:
        # Multi-chunk: generate each, then concat
        chunk_wavs = []
        for i, chunk in enumerate(chunks):
            words = len(chunk.split())
            chunk_path = output_wav.replace('.wav', f'_chunk{i}.wav')
            instruct, speed = get_chunk_instruction(prosody_map, i)

            print(f"\n   Chunk {i+1}/{len(chunks)} ({words} words)...")
            if mode == "cosyvoice2":
                print(f"   Instruct: \"{instruct[:60]}...\"  Speed: {speed}")

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    generate_chunk(gradio_url, chunk, chunk_path, mode, instruct, speed)
                    size_kb = os.path.getsize(chunk_path) / 1024
                    print(f"   [OK] {size_kb:.0f} KB")
                    chunk_wavs.append(chunk_path)
                    # Small delay between chunks to let Gradio server recover
                    if i < len(chunks) - 1:
                        time.sleep(3)
                    break
                except Exception as e:
                    print(f"   [FAIL] Attempt {attempt} failed: {e}")
                    if attempt == MAX_RETRIES:
                        raise
                    time.sleep(5 * attempt)

        print(f"\n   Concatenating {len(chunk_wavs)} chunks...")
        concat_wavs(chunk_wavs, output_wav)

        # Cleanup chunks
        for p in chunk_wavs:
            try:
                os.unlink(p)
            except:
                pass

    size_mb = os.path.getsize(output_wav) / (1024 * 1024)
    print(f"\n[OK] TTS audio: {output_wav} ({size_mb:.1f} MB)")

    # Step 2: Whisper timestamps
    run_whisper(output_wav, timestamps_json)

    print(f"\n[DONE] TTS + Timestamps complete!")


if __name__ == "__main__":
    main()
