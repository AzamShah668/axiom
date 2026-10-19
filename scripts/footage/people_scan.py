"""People gate for the footage library: cut presenters, interviews and lab crews out of every shot.

  python people_scan.py <lib> [--threshold 0.5]

Scene detection misses some cuts (a black hole animation that cuts to a NASA presenter becomes one "shot"),
and the text/black/frozen QC in build_shots.py cannot see people. This scores one frame per usable second
with CLIP: people prompts vs space-footage prompts (softmax). Seconds where people win are removed from the
shot's usable ranges (pieces shorter than 1.5 s are dropped). Results are cached in <lib>/people_scan.json,
so re-running after build_shots.py only scans new shots; it must run after every build_shots.py pass.
"""
import argparse, json, os, sys
import numpy as np, cv2

sys.path.insert(0, os.path.dirname(__file__))
import clip_model  # noqa: E402

PEOPLE = ["a person talking to the camera", "a woman speaking in a studio", "a man being interviewed",
          "scientists working in a laboratory", "people in a control room", "a group of people", "a human face"]
SPACE = ["a galaxy in space", "a nebula", "a field of stars", "an animation of a black hole", "a planet in space",
         "a telescope at night", "a rocket launch", "a spacecraft in space", "the Earth from orbit",
         "a diagram of orbits", "the night sky over mountains", "an observatory dome"]


def frames_for(lib, s):
    cap = cv2.VideoCapture(os.path.join(lib, "clips", s["clip"] + ".mp4"))
    out = []
    for r0, r1 in s["usable"]:
        t = r0 + 0.5
        while t < r1:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, f = cap.read()
            if ok:
                if s.get("crop"):
                    x0, y0, x1, y1 = s["crop"]
                    f = f[int(y0 * f.shape[0]):int(y1 * f.shape[0]), int(x0 * f.shape[1]):int(x1 * f.shape[1])]
                out.append((round(t - 0.5, 2), cv2.cvtColor(cv2.resize(f, (384, 216)), cv2.COLOR_BGR2RGB)))
            t += 1.0
    cap.release()
    return out


def cut(usable, secs):
    for sec in sorted(secs):
        usable = [r for a, z in usable for r in ([a, min(z, sec)], [max(a, sec + 1.0), z]) if r[1] - r[0] >= 1.5]
    return usable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("--threshold", type=float, default=0.5)
    a = ap.parse_args()
    sp = os.path.join(a.lib, "shots.json")
    shots = json.load(open(sp))
    cp = os.path.join(a.lib, "people_scan.json")
    cache = json.load(open(cp)) if os.path.exists(cp) else {}
    T = clip_model.embed_texts([f"a photo of {p}" for p in PEOPLE + SPACE])
    todo = [s for s in shots if s["usable"] and s["id"] not in cache]
    print(f"people scan: {len(todo)} new shots ({len(cache)} cached)", flush=True)
    for k in range(0, len(todo), 40):
        batch = todo[k:k + 40]
        fr = [(s["id"], t, im) for s in batch for t, im in frames_for(a.lib, s)]
        if fr:
            E = clip_model.embed_images([im for _, _, im in fr])
            logits = 100.0 * (E @ T.T)
            p = np.exp(logits - logits.max(1, keepdims=True))
            p = p[:, :len(PEOPLE)].sum(1) / p.sum(1)
        for s in batch:
            cache[s["id"]] = [t for (sid, t, _), pp in zip(fr, p if fr else []) if sid == s["id"] and pp > a.threshold]
        json.dump(cache, open(cp, "w"))
        print(f"  {min(k + 40, len(todo))}/{len(todo)}", flush=True)
    hit = 0
    for s in shots:
        secs = cache.get(s["id"], [])
        if secs and s["usable"]:
            s["usable"] = cut(s["usable"], secs)
            s["people_secs"] = secs
            hit += 1
    json.dump(shots, open(sp, "w"))
    print(f"people removed from {hit} shots")


if __name__ == "__main__":
    main()
