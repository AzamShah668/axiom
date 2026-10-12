"""Credits block (and YouTube chapters) for the description, from what the final cut actually uses.

  python credits.py <cutlist.json> <library_dir> <edit.json> [--assets credits.json]

ESO, ESA/Hubble and ESA/Webb footage is CC BY 4.0 (credit + licence link); NASA SVS footage is credited to
NASA's Goddard Space Flight Center. Kevin MacLeod music is CC BY 4.0 and needs the exact title list.
"""
import argparse, json, os, string

ARCHIVE = {
    "eso": "ESO (eso.org), CC BY 4.0",
    "esahubble": "ESA/Hubble (esahubble.org), CC BY 4.0",
    "esawebb": "ESA/Webb (esawebb.org), CC BY 4.0",
    "svs": "NASA's Goddard Space Flight Center / Scientific Visualization Studio (svs.gsfc.nasa.gov)",
}
GFX_IMAGES = {"mw_spiral": "milkyway", "halo_expand": "milkyway", "halo_full": "milkyway", "galactic_orbit": "milkyway",
              "spectrum": "chandra_tel", "wind": "earth"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cutlist")
    ap.add_argument("lib")
    ap.add_argument("edit")
    ap.add_argument("--assets", default="")
    a = ap.parse_args()
    cl = json.load(open(a.cutlist))
    src = json.load(open(os.path.join(a.lib, "sources.json")))
    edit = json.load(open(a.edit))
    by = {}
    for it in cl["items"]:
        s = src[it["clip"]]
        by.setdefault(s["source"], {})[s["key"].split(":", 1)[1]] = s["title"]
    lines = ["Footage credits:"]
    for k in ("eso", "esahubble", "esawebb", "svs"):
        if k in by:
            ids = sorted(by[k])
            lines.append(f"- {ARCHIVE[k]}: " + ", ".join(ids))
    imgs = sorted({GFX_IMAGES[it["gfx"]] for it in cl["items"] if it.get("gfx") in GFX_IMAGES})
    if imgs and a.assets and os.path.exists(a.assets):
        cred = json.load(open(a.assets))
        lines.append("Image credits (graphics):")
        lines += [f"- {cred[i]}" for i in imgs if i in cred]
    lines.append("Graphics and animation: original.")
    tracks = [m["track"].rsplit(".", 1)[0].replace("_", " ") for m in edit.get("music", [])]
    if tracks:
        lines += ["", "Music by Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0 License "
                      "(http://creativecommons.org/licenses/by/4.0/):", ", ".join(f'"{t}"' for t in tracks)]
    chapters = ["", "Chapters:", "0:00 Intro"]
    for it in cl["items"]:
        if it["kind"] == "card":
            t = int(it["t0"])
            num, title = it["text"]
            chapters.append(f"{t // 60}:{t % 60:02d} {num.title()}: {string.capwords(title.lower())}")
    print("\n".join(lines + chapters))


if __name__ == "__main__":
    main()
