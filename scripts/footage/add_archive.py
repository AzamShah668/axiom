"""Put real archive footage and recordings into the footage library (owner, 2026-10-27: real clips, 10-20 a video
when they exist, and real voices). Only public-domain or freely licensed sources (NASA, US government, CC BY /
CC BY-SA / CC0): never a TV channel's, a news agency's or another YouTuber's clip.

  python add_archive.py clip <name> <file|url> --ss 34 --t 106 --title "COBE launch, 1989" --source svs \
                        --page https://svs.gsfc.nasa.gov/14715/ [--credit "..."] [--licence "public domain (NASA)"]
  python add_archive.py bites productions/NN/bites.json     # one clip "bite_<name>" per recording with "video": true

<name> becomes work/library/clips/<name>.mp4 (1920x1080, 30 fps, no sound) and a sources.json entry marked
"archival"; the shots are then built (scripts/footage/build_shots.py). Pin a clip's shots to the lines that name it
(edit.base.json "pin"); a recording's clip is pinned automatically to its "V #<name> @ bite:<name>" beat. A bite
clip starts BITE_PRE s before the recording so the scene can open on the person just before they speak."""
import argparse, json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(ROOT, "work", "library")
BITE_PRE, BITE_POST = 1.5, 1.0
VF = "scale=1920:1080:force_original_aspect_ratio=increase:flags=bicubic,crop=1920:1080,fps=30"


def probe(src):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:format=duration", "-of", "json", src])
    d = json.loads(out)
    st = (d.get("streams") or [{}])[0]
    return st.get("width", 0), st.get("height", 0), float(d["format"]["duration"])


def add(name, src, ss, t, entry):
    w, h, dur = probe(src)
    out = os.path.join(LIB, "clips", name + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", str(t), "-i", src, "-an", "-vf", VF,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-g", "30", out],
                   check=True)
    spath = os.path.join(LIB, "sources.json")
    sources = json.load(open(spath))
    sources[name] = {"key": entry.pop("key", name.replace("_", ":", 1)), "url": src if "://" in src else entry.get("url", ""),
                     "src_w": w, "src_h": h, "src_dur": round(dur, 2), "ss": ss, "cap_s": t, "archival": True, **entry}
    json.dump(sources, open(spath, "w"), indent=1)
    print(f"{name}: {w}x{h} {ss}+{t}s")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clip")
    c.add_argument("name")
    c.add_argument("src")
    c.add_argument("--ss", type=float, default=0.0)
    c.add_argument("--t", type=float, required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--source", required=True, help="svs | nasa | another archive key (then give --credit)")
    c.add_argument("--page", default="")
    c.add_argument("--credit", default="")
    c.add_argument("--licence", default="")
    b = sub.add_parser("bites")
    b.add_argument("bites_json")
    a = ap.parse_args()
    if a.cmd == "clip":
        src = a.src if "://" in a.src else os.path.join(ROOT, a.src)
        add(a.name, src, a.ss, a.t, {"title": a.title, "source": a.source, "page": a.page, "credit": a.credit,
                                     "licence": a.licence})
    else:
        for name, sp in json.load(open(a.bites_json, encoding="utf-8")).items():
            if not sp.get("video"):
                continue
            src = sp["file"] if "://" in sp["file"] else os.path.join(ROOT, sp["file"])
            ss = max(0.0, float(sp["ss"]) - BITE_PRE)
            _, _, dur = probe(src)
            add("bite_" + name, src, ss, min(float(sp["ss"]) - ss + float(sp["d"]) + BITE_POST, dur - ss),
                {"key": f"bite:{name}", "title": f"{sp.get('who', name)}, {sp.get('when', '')} (recording)".replace(", (", " ("),
                 "source": sp.get("source", "nasa"), "page": sp.get("url", ""), "credit": sp.get("credit", ""),
                 "licence": sp.get("licence", ""), "bite_pre": round(float(sp["ss"]) - ss, 3)})
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "footage", "build_shots.py"), LIB], check=True)


if __name__ == "__main__":
    main()
