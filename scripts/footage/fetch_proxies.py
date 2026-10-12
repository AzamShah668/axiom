"""Transcode picked 4K source videos into 1080p30 editing proxies (streamed straight from the archive URL).

  python fetch_proxies.py <picks.json> <library_dir> [--jobs 3] [--min-width 3840]

Sources narrower than --min-width are skipped (the channel only uses 4K-sourced footage).
Writes <library_dir>/clips/<name>.mp4 and <library_dir>/sources.json {name: {key, url, page, title, source,
src_w, src_h, src_dur, cap_s}}. Re-running skips finished clips; failed ones are retried.
"""
import argparse, json, os, re, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor

LOCK = threading.Lock()


def probe(url):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", url], capture_output=True, text=True, timeout=120)
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    return st.get("width", 0), st.get("height", 0), float((d.get("format") or {}).get("duration") or 0)


def name_of(key):
    return re.sub(r"[^A-Za-z0-9_-]", "_", key.replace(":", "_"))


def work(p, lib, minw, sources):
    name = name_of(p["key"])
    out = os.path.join(lib, "clips", name + ".mp4")
    if os.path.exists(out) and name in sources:
        return name, "have"
    try:
        w, h, dur = probe(p["url"])
    except Exception as e:  # noqa: BLE001
        return name, f"probe failed {e}"
    if w < minw:
        return name, f"skip {w}x{h}"
    ss = 1.0 if dur > 8 else 0.0  # skip fade-in from black
    t = max(2.0, min(p["cap_s"], dur - ss - 0.5))
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", f"{t:.2f}", "-i", p["url"], "-an",
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase:flags=bilinear,crop=1920:1080,fps=30",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-g", "30", out + ".part.mp4"]
    for attempt in range(2):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.getsize(out + ".part.mp4") > 10000:
            os.replace(out + ".part.mp4", out)
            with LOCK:
                sources[name] = {"key": p["key"], "url": p["url"], "page": p.get("page", ""), "title": p["title"],
                                 "source": p["source"], "src_w": w, "src_h": h, "src_dur": round(dur, 2),
                                 "ss": ss, "cap_s": round(t, 2)}
            return name, f"ok {w}x{h} {t:.0f}s"
    return name, "ffmpeg failed: " + r.stderr[-200:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("picks")
    ap.add_argument("lib")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--min-width", type=int, default=3840)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.lib, "clips"), exist_ok=True)
    spath = os.path.join(a.lib, "sources.json")
    sources = json.load(open(spath)) if os.path.exists(spath) else {}
    picks = json.load(open(a.picks))
    done = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for name, msg in ex.map(lambda p: work(p, a.lib, a.min_width, sources), picks):
            done += 1
            print(f"[{done}/{len(picks)}] {name:40s} {msg}", flush=True)
            if done % 10 == 0:
                with LOCK:
                    json.dump(sources, open(spath, "w"), indent=1, ensure_ascii=False)
    json.dump(sources, open(spath, "w"), indent=1, ensure_ascii=False)
    print(f"{len(sources)} 4K-sourced proxies in {a.lib}/clips")


if __name__ == "__main__":
    sys.exit(main())
