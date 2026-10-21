"""More shots from long source videos: fetch the windows no proxy has taken yet, as extra clips.

  python fetch_segments.py <library_dir> --match "neutron|pulsar|..." [--len 10] [--max-windows 3] [--jobs 3]

Proxies hold only 12 s (or 40 s) of each source, usually its end. Once those shots are used, a later video can
still use other parts of the same source. That is new footage, not a repeat; the look-alike check in
assign_shots.py still catches anything that looks the same. Each window becomes a clip <clip>-win<n> with its own
sources.json entry (same archive key, so credits count the video once). The suffix is "-win<n>": "__"
is taken by the descriptive Drive names, which drive_sync.py cuts at the last "__".
- "Zooming in on ..." videos take only the stretch just before the part already used. Their openings are the
  same all-sky Milky Way panorama, which would look repeated.
- Anything under 3840 px wide is skipped, as everywhere in the library.
"""
import argparse, json, os, re, subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

LOCK = Lock()


def windows(s, used_len, L, max_w, zoom):
    d, ss = float(s.get("src_dur") or 0), float(s.get("ss") or 0)
    if zoom:
        a = max(1.0, ss - L - 0.5)
        return [(a, ss - 0.5)] if ss - 0.5 - a >= 6 else []
    gaps = [(1.0, ss - 0.5), (ss + used_len + 0.5, d - 0.5)]
    out = []
    for a, b in gaps:
        n = int((b - a) // (L + 2))
        if n <= 0:
            continue
        step = (b - a) / n
        out += [(a + k * step, a + k * step + L) for k in range(n)]
    return out[:max_w]


def fetch(job):
    name, url, a, b, out = job
    if os.path.exists(out):
        return name, "have"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", url, "-an",
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase:flags=bilinear,crop=1920:1080,fps=30",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-g", "30", out + ".part.mp4"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode or not os.path.exists(out + ".part.mp4") or os.path.getsize(out + ".part.mp4") < 10000:
        return name, f"failed {r.stderr.strip()[:120]}"
    os.replace(out + ".part.mp4", out)
    return name, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("--match", required=True, help="regex on the source title")
    ap.add_argument("--len", type=float, default=10.0)
    ap.add_argument("--max-windows", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    spath = os.path.join(a.lib, "sources.json")
    src = json.load(open(spath))
    pat = re.compile(a.match, re.I)
    jobs = []
    for c, s in sorted(src.items()):
        if re.search(r"-win\d+$", c) or not pat.search(s.get("title", "")) or (s.get("src_w") or 0) < 3840:
            continue
        used_len = 12.0 if (s.get("cap_s") or 0) <= 30 else 40.0
        zoom = bool(re.search(r"\bzoom", s["title"], re.I))
        for k, (w0, w1) in enumerate(windows(s, used_len, a.len, a.max_windows, zoom), 1):
            name = f"{c}-win{k}"
            jobs.append((name, s["url"], w0, w1, os.path.join(a.lib, "clips", name + ".mp4")))
            src.setdefault(name, {**{x: s[x] for x in ("key", "url", "page", "title", "source", "src_w", "src_h", "src_dur") if x in s},
                                  "ss": round(w0, 2), "cap_s": round(w1 - w0, 2), "window_of": c})
    print(f"{len(jobs)} windows from {len({j[0].rsplit('-win', 1)[0] for j in jobs})} sources", flush=True)
    done = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for name, st in ex.map(fetch, jobs):
            done += 1
            print(f"[{done}/{len(jobs)}] {name:48s} {st}", flush=True)
            if st.startswith("failed"):
                src.pop(name, None)
    with LOCK:
        json.dump(src, open(spath, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
