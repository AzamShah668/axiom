"""Minimal ElevenLabs client for the Hindi documentary pipeline.

Needs ELEVENLABS_API_KEY in the environment.

  python el.py whoami
  python el.py voices                                   # list voices in the account
  python el.py clone  <name> <sample.wav> [more.wav...] # instant voice clone -> prints voice_id
  python el.py tts    <voice_id> <text.txt> <out.mp3> [--stability 0.55] [--similarity 0.8]
                      [--style 0.0] [--speed 1.0] [--model eleven_multilingual_v2]
"""
import argparse, json, os, sys
import requests

API = "https://api.elevenlabs.io/v1"


def _h():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("set ELEVENLABS_API_KEY")
    return {"xi-api-key": key}


def _check(r):
    if r.status_code >= 300:
        sys.exit(f"HTTP {r.status_code}: {r.text[:500]}")
    return r


def whoami():
    sub = _check(requests.get(f"{API}/user/subscription", headers=_h(), timeout=30)).json()
    print(json.dumps({k: sub.get(k) for k in ("tier", "character_count", "character_limit",
                                              "can_use_instant_voice_cloning",
                                              "can_use_professional_voice_cloning",
                                              "next_character_count_reset_unix")}, indent=1))


def voices():
    for v in _check(requests.get(f"{API}/voices", headers=_h(), timeout=30)).json()["voices"]:
        print(v["voice_id"], "|", v["name"], "|", v.get("category"), "|", (v.get("labels") or {}))


def clone(name, files):
    data = {"name": name, "description": "Hindi documentary narrator (own voice)",
            "remove_background_noise": "false"}
    fs = [("files", (os.path.basename(f), open(f, "rb"), "audio/wav")) for f in files]
    r = _check(requests.post(f"{API}/voices/add", headers=_h(), data=data, files=fs, timeout=300)).json()
    print(r["voice_id"])


def tts(voice_id, text_path, out, stability, similarity, style, speed, model):
    text = open(text_path, encoding="utf-8").read().strip()
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": stability, "similarity_boost": similarity,
                               "style": style, "use_speaker_boost": True, "speed": speed}}
    r = _check(requests.post(f"{API}/text-to-speech/{voice_id}?output_format=mp3_44100_192",
                             headers={**_h(), "Content-Type": "application/json"},
                             data=json.dumps(body), timeout=600))
    open(out, "wb").write(r.content)
    print(f"wrote {out} ({len(r.content) // 1024} KB, {len(text)} chars)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd")
    p.add_argument("args", nargs="*")
    p.add_argument("--stability", type=float, default=0.55)
    p.add_argument("--similarity", type=float, default=0.8)
    p.add_argument("--style", type=float, default=0.0)
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--model", default="eleven_multilingual_v2")
    a = p.parse_args()
    if a.cmd == "whoami":
        whoami()
    elif a.cmd == "voices":
        voices()
    elif a.cmd == "clone":
        clone(a.args[0], a.args[1:])
    elif a.cmd == "tts":
        tts(a.args[0], a.args[1], a.args[2], a.stability, a.similarity, a.style, a.speed, a.model)
    else:
        sys.exit(__doc__)
