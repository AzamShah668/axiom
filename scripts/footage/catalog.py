"""Catalogue of the footage library: what every clip shows, how much of it is usable, which video used it.

  python catalog.py <lib> [--productions productions] [--csv productions/footage-catalog.csv]

For every clip in <lib>/clips:
- category + tags: CLIP zero-shot over a fixed vocabulary (black-hole, galaxy-cluster, observatory, ...):
  the mean image embedding of its usable shots (what is actually on screen), helped by the archive title
  (z-scored over the vocabulary, title weighted 0.6)
- the archive title, usable seconds and shots, and the productions whose cutlist.json used it
Writes <lib>/catalog.json, the CSV (searchable without downloading anything), and <lib>/drive_names.json:
{"<clip>.mp4": "<category>__<title-slug>__<clip>.mp4"}, the descriptive name each clip gets on Google Drive.
drive_sync.py pull turns "<...>__<clip>.mp4" back into "<clip>.mp4", so the pipeline keeps its short ids.
"""
import argparse, csv, json, os, re, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import clip_model  # noqa: E402

VOCAB = {
    "black-hole": "a black hole with a glowing accretion disk",
    "black-hole-merger": "two black holes orbiting each other and merging",
    "tidal-disruption": "a star being torn apart by a black hole into a stream of gas",
    "x-ray-binary": "a black hole pulling gas from a blue companion star",
    "galaxy-jet": "a powerful jet shooting out of the core of a galaxy",
    "quasar": "a brilliant quasar shining in the early universe",
    "neutron-star": "a spinning neutron star with beams of light",
    "supernova": "a supernova explosion",
    "star-closeup": "a bright star up close",
    "giant-star": "a huge red giant star",
    "sun": "the Sun, its glowing surface, solar flares and the solar wind",
    "star-cluster": "a dense cluster of stars",
    "nebula": "a colourful glowing nebula",
    "dark-cloud": "a dark cloud of dust blocking the stars",
    "star-forming": "a star-forming region with young stars",
    "spiral-galaxy": "a spiral galaxy",
    "elliptical-galaxy": "a giant elliptical galaxy",
    "galaxy-cluster": "a cluster of many galaxies",
    "galaxy-merger": "two galaxies colliding",
    "deep-field": "a deep field full of tiny distant galaxies",
    "gravitational-lens": "gravitational lensing arcs around a galaxy cluster",
    "galactic-centre": "the dense glowing centre of the Milky Way",
    "milky-way-sky": "the Milky Way arching across the night sky over a landscape",
    "night-sky": "a starry night sky timelapse",
    "starfield": "a dark field of stars",
    "cosmic-web": "a simulation of the cosmic web of filaments",
    "early-universe": "the early universe with the first galaxies forming",
    "earth": "planet Earth seen from space",
    "planet": "a planet orbiting a star",
    "moon": "the grey cratered surface of the Moon",
    "observatory": "telescope domes of an observatory on a mountain",
    "radio-telescope": "radio telescope dishes",
    "laser-telescope": "a telescope shooting a laser beam into the sky",
    "space-telescope": "a space telescope in orbit",
    "rocket": "a rocket launching",
    "lab-instrument": "a scientific instrument in a laboratory",
    "people": "people, a presenter or scientists at work",
    "diagram": "a diagram or chart with labels",
    "spacetime-grid": "a warped grid representing spacetime",
}


def slug(s, n=60):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "")).strip("-")
    return s[:n].rstrip("-") or "untitled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("--productions", default=os.path.join(os.path.dirname(__file__), "..", "..", "productions"))
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    src = json.load(open(os.path.join(a.lib, "sources.json")))
    shots = json.load(open(os.path.join(a.lib, "shots.json")))
    z = np.load(os.path.join(a.lib, "shots_emb.npz"), allow_pickle=True)
    emb = dict(zip(z["ids"], z["emb"]))
    used = {}
    for d in sorted(os.listdir(a.productions)):
        f = os.path.join(a.productions, d, "cutlist.json")
        if os.path.exists(f):
            for it in json.load(open(f))["items"]:
                if it.get("clip"):
                    used.setdefault(it["clip"], set()).add(d.split("-")[0])
    names = list(VOCAB)
    V = clip_model.embed_texts([f"a photo of {VOCAB[n]}" for n in names])
    by = {}
    for s in shots:
        by.setdefault(s["clip"], []).append(s)
    rows, drive = [], {}
    clips = sorted(f[:-4] for f in os.listdir(os.path.join(a.lib, "clips")) if f.endswith(".mp4"))
    TT = clip_model.embed_texts([f"a video of {src.get(c, {}).get('title', c)}" for c in clips])
    z = lambda x: (x - x.mean()) / (x.std() + 1e-6)
    for ci, clip in enumerate(clips):
        ss = by.get(clip, [])
        good = [s for s in ss if s["usable"] and not s.get("dup_of")]
        es = [emb[s["id"]] for s in (good or ss) if s["id"] in emb]
        sims = 0.6 * z(V @ TT[ci])
        if es:
            e = np.mean(es, 0)
            sims = sims + z(V @ (e / np.linalg.norm(e)))
        top = [names[i] for i in np.argsort(-sims)[:3]]
        meta = src.get(clip, {})
        title = meta.get("title", clip)
        usable_s = sum(r[1] - r[0] for s in good for r in s["usable"])
        rows.append({"clip": clip, "category": top[0], "tags": " ".join(top[1:]), "title": title,
                     "source": meta.get("source", ""), "page": meta.get("page", ""),
                     "shots": len(ss), "usable_shots": len(good), "usable_s": round(usable_s, 1),
                     "used_in": " ".join(sorted(used.get(clip, []))),
                     "drive_name": f"{top[0]}__{slug(title)}__{clip}.mp4"})
        drive[clip + ".mp4"] = rows[-1]["drive_name"]
    json.dump(rows, open(os.path.join(a.lib, "catalog.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(drive, open(os.path.join(a.lib, "drive_names.json"), "w"), indent=1, ensure_ascii=False)
    out = a.csv or os.path.join(a.lib, "catalog.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["category"], r["title"])))
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print(f"{len(rows)} clips catalogued -> {out}")
    print(" ".join(f"{k}:{v}" for k, v in sorted(cats.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
