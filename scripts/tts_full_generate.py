"""
tts_full_generate.py
Full TTS generation: chunked Gradio calls + concat + Whisper timestamps.
Bypasses Node.js exec() issues by running entirely in Python.

Usage:
  python tts_full_generate.py <transcript_file> <output_wav> <timestamps_json> <gradio_url>
"""

import sys
import os
import json
import shutil
import time
import tempfile
import subprocess
import whisper

CHUNK_WORD_LIMIT = 200
REF_AUDIO = "D:/notebook lm/voice/Recording (14).m4a"
REF_TRANSCRIPT = "Hey everyone, welcome back! Have you ever wondered how artificial intelligence is changing the way we learn? Today, we are going to explore some incredible new concepts together. It's truly fascinating, and I know you're going to love it."
MAX_RETRIES = 3
MIN_WAV_SIZE = 10 * 1024  # 10KB


def split_into_chunks(text):
    """Split text at sentence boundaries into ~200-word chunks."""
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


def generate_chunk(gradio_url, text, output_path, attempt=1):
    """Generate TTS for a single chunk via Gradio."""
    from gradio_client import Client, handle_file

    client = Client(gradio_url)
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


def concat_wavs(wav_paths, output_path):
    """Concatenate WAV files using ffmpeg."""
    list_file = os.path.join(tempfile.gettempdir(), f"tts_concat_{int(time.time())}.txt")
    with open(list_file, 'w') as f:
        for p in wav_paths:
            f.write(f"file '{p.replace(os.sep, '/')}'\n")

    cmd = f'ffmpeg -y -f concat -safe 0 -i "{list_file}" -c copy "{output_path.replace(os.sep, "/")}"'
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


def main():
    if len(sys.argv) < 5:
        print("Usage: python tts_full_generate.py <transcript_file> <output_wav> <timestamps_json> <gradio_url>")
        sys.exit(1)

    transcript_file = sys.argv[1]
    output_wav = sys.argv[2]
    timestamps_json = sys.argv[3]
    gradio_url = sys.argv[4]

    text = open(transcript_file, 'r', encoding='utf-8').read().strip()
    word_count = len(text.split())
    print(f"\n[TTS]  TTS Full Generate (Python)")
    print(f"   Words: {word_count}")
    print(f"   Gradio: {gradio_url}")

    chunks = split_into_chunks(text)
    print(f"   Chunks: {len(chunks)}")

    if len(chunks) == 1:
        # Single chunk — direct call
        print(f"\n   Single chunk ({word_count} words)...")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                generate_chunk(gradio_url, chunks[0], output_wav, attempt)
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
            print(f"\n   Chunk {i+1}/{len(chunks)} ({words} words)...")

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    generate_chunk(gradio_url, chunk, chunk_path, attempt)
                    size_kb = os.path.getsize(chunk_path) / 1024
                    print(f"   [OK] {size_kb:.0f} KB")
                    chunk_wavs.append(chunk_path)
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
