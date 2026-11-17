"""Pace lint for a v3 edit: dead zones, a thin last third and a flat music curve, seen at the edit stage.

  python pace_lint.py <cutlist.json>                                   (a planned or assigned cut list)
  python pace_lint.py --edit <edit.json> --timeline <timeline.json>    (runs render_v3.plan() itself)
         [--window 20] [--gap 30] [--strict] [--energy music_energy.json] [--no-music]
  python pace_lint.py --measure-music <music_dir> [--write]            (re-tag the tracks: music_energy.json)

A visual event is a kinetic headline, key line, number card, name card, recording quote, chapter/title card,
diagram or own graphic, photo, a flash montage, or a whip/flash/dip/flare transition. While a card, graphic or
overlay counts once, where it starts; a gap is the time between two event onsets (or from the last one to the
last spoken word): nothing new appears on screen.
Prints a per-minute table (cuts, overlays by kind, SFX) and warns on (docs/research/improve-2026-11/01, 00 WP2):
  - a gap >= --window s;  - hero > 50% of number cards;  - SFX outside 8-15 a minute;
  - fewer than 15 key lines or 12 headlines per 11 min (scaled);  - the last third with < 25% of the overlays;
  - music: 3 `low` cues in a row, or no `mid`/`high` cue playing after the midpoint (music_energy.json).
Everything is a warning. Exit 1 only with --strict and a gap >= --gap.
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENERGY = os.path.join(HERE, "music_energy.json")
TRANS_EVENT = {"whip", "flash", "dip", "flare"}
SFX_BAND = (8.0, 15.0)
PER_11 = {"keyline": 15, "headline": 12}    # targets per 11 minutes, scaled to the video's length


# ------------------------------------------------------------------ music energy (also used by make_edit.py)
def load_energy(path=ENERGY):
    try:
        return {k: v for k, v in json.load(open(path, encoding="utf-8")).items() if not k.startswith("_")}
    except (OSError, ValueError):
        return {}


def music_warnings(cues, energy, mid, label=None):
    """cues: [(t, track)] in order (t in seconds, or a section index); mid: the midpoint on the same scale;
    label(t): how to print a position (default m:ss)."""
    _l = label or _ts
    out, run = [], []
    tags = [(t, tr, energy.get(tr)) for t, tr in cues]
    for t, tr, e in tags:
        if e is None:
            out.append(f"music: {tr} has no energy tag (scripts/video/music_energy.json; pace_lint.py --measure-music)")
    for t, tr, e in tags + [(None, None, None)]:
        if e == "low":
            run.append((t, tr))
            continue
        if len(run) >= 3:
            out.append(f"music: {len(run)} low-energy cues in a row from {_l(run[0][0])}: "
                       + ", ".join(x[1] for x in run) + " (swap one for a mid/high track)")
        run = []
    live = [x for x in tags if x[0] > mid]
    at_mid = [x for x in tags if x[0] <= mid]
    if at_mid:
        live.insert(0, at_mid[-1])  # the cue playing at the midpoint
    if tags and not any(e in ("mid", "high") for _, _, e in live):
        out.append(f"music: no mid/high cue after the midpoint ({_l(mid)}): the second half winds down")
    return out


def _ts(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def measure_music(music_dir, write):
    """Tag each track low|mid|high from its strong-onset rate (unnormalised onset strength, delta 1.0) and its
    loudness range (EBU R128 LRA): < 0.5 onsets/s = low (a drone); >= 2.5/s with LRA <= 14 LU = high (a steady
    pulse); the rest mid."""
    import re, subprocess
    import librosa
    tags, rows = {}, []
    for f in sorted(os.listdir(music_dir)):
        if not f.lower().endswith(".mp3"):
            continue
        p = os.path.join(music_dir, f)
        y, sr = librosa.load(p, sr=22050, mono=True)
        env = librosa.onset.onset_strength(y=y, sr=sr)
        rate = len(librosa.onset.onset_detect(onset_envelope=env, sr=sr, normalize=False, delta=1.0)) / (len(y) / sr)
        log = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", p, "-af", "ebur128", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        lra = float(re.findall(r"LRA:\s+([\d.]+) LU", log)[-1])
        lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", log)[-1])
        tags[f] = "low" if rate < 0.5 else "high" if rate >= 2.5 and lra <= 14 else "mid"
        rows.append(f"{f:28s} onsets/s {rate:5.2f}  LRA {lra:5.1f} LU  I {lufs:6.1f} LUFS  -> {tags[f]}")
    print("\n".join(rows))
    if write:
        old = json.load(open(ENERGY, encoding="utf-8")) if os.path.exists(ENERGY) else {}
        new = {k: v for k, v in old.items() if k.startswith("_")}
        new.update({k: v for k, v in sorted({**{k: v for k, v in old.items() if not k.startswith("_")}, **tags}.items())})
        json.dump(new, open(ENERGY, "w", encoding="utf-8"), indent=1)
        print("written", ENERGY)


# ------------------------------------------------------------------ the lint
def events(P):
    """[(t0, t1, kind)] of everything that counts as a visual event."""
    ev = []
    items = P["items"]
    for i, it in enumerate(items):
        k = it["kind"]
        if k in ("card", "title"):
            ev.append((it["t0"], it["t1"], k))
        elif k == "num":
            ev.append((it["t0"], it["t1"], "name" if it["num"].get("template") == "name" else "number"))
        elif k == "gfx":
            ev.append((it["t0"], it["t1"], "photo" if it["gfx"].startswith("photo") else "graphic"))
        elif it.get("opt") == "flash" and (i == 0 or items[i - 1].get("opt") != "flash"):
            j = i
            while j + 1 < len(items) and items[j + 1].get("opt") == "flash":
                j += 1
            ev.append((it["t0"], items[j]["t1"], "montage"))
        if it.get("trans") in TRANS_EVENT and i > 0:
            ev.append((it["t0"], it["t0"], "trans"))
    for o in P["ovl"]:
        k = o["kind"]
        if k == "footer":
            continue
        if k == "num":
            k = "name" if o["num"].get("template") == "name" else "number"
        ev.append((o["t0"], o.get("t1", o["t0"]), k))
    return sorted(ev)


def gaps(ev, end):
    """Stretches between event onsets (and from the last one to the last spoken word)."""
    ts = [0.0] + sorted(t0 for t0, _, _ in ev if t0 < end) + [end]
    return [(a, b) for a, b in zip(ts, ts[1:]) if b > a]


def lint(P, window=20.0, gap=30.0, energy=None):
    """Prints the report; returns (warnings, the longest gap)."""
    if P.get("style") != "v3" or "ovl" not in P:
        print("pace lint: not a v3 cut list (no overlays): nothing to check")
        return [], 0.0
    items, ovl, sfx, total = P["items"], P["ovl"], P["sfx"], float(P["total"])
    end = max([c.get("t1", c["t"]) for c in P.get("caps", [])] or [total - 3.0])  # the last spoken line
    mins = end / 60.0
    ev = events(P)
    num_cards = [it["num"] for it in items if it["kind"] == "num"] + [o["num"] for o in ovl if o["kind"] == "num"]
    num_cards = [n for n in num_cards if n.get("template") != "name"]
    cols = ["cuts", "head", "key", "num", "name", "quote", "gfx", "photo", "trans", "sfx"]
    rows = [dict.fromkeys(cols, 0) for _ in range(int(total // 60) + 1)]
    for it in items[1:]:
        rows[int(it["t0"] // 60)]["cuts"] += 1
    kmap = {"headline": "head", "keyline": "key", "number": "num", "name": "name", "quote": "quote",
            "graphic": "gfx", "photo": "photo", "trans": "trans"}
    for t0, _, k in ev:
        if k in kmap:
            rows[int(t0 // 60)][kmap[k]] += 1
    for s in sfx:
        rows[min(int(s[1] // 60), len(rows) - 1)]["sfx"] += 1
    print("min  " + " ".join(f"{c:>5}" for c in cols))
    for m, r in enumerate(rows):
        print(f"{m:>3}  " + " ".join(f"{r[c]:>5}" for c in cols))

    warn = []
    gl = [(a, b) for a, b in gaps(ev, end) if b - a >= window]
    for a, b in gl:
        warn.append(f"gap: nothing new on screen {_ts(a)}-{_ts(b)} ({b - a:.1f}s)"
                    + ("  << over the --gap limit" if b - a >= gap else ""))
    hero = sum(1 for n in num_cards if n.get("template") == "hero")
    if num_cards and hero > len(num_cards) / 2:
        warn.append(f"number cards: {hero}/{len(num_cards)} are hero (keep it <= 50%: scale, equation, route/line, "
                    "progress/gauge, callout - science-edit-plan skill)")
    rate = len(sfx) / mins if mins else 0
    if not SFX_BAND[0] <= rate <= SFX_BAND[1]:
        warn.append(f"sfx: {rate:.1f}/min, outside {SFX_BAND[0]:.0f}-{SFX_BAND[1]:.0f}")
    for kind, per in PER_11.items():
        n, want = sum(1 for o in ovl if o["kind"] == kind), per * mins / 11.0
        if n < want:
            warn.append(f"{kind}s: {n}, want >= {want:.0f} for {mins:.1f} min ({per} per 11 min)")
    texts = [t0 for t0, _, k in ev if k in ("headline", "keyline", "number", "name", "quote")]
    last = sum(1 for t in texts if t >= end * 2 / 3)
    if texts and last < 0.25 * len(texts):
        warn.append(f"last third: {last}/{len(texts)} overlays ({100 * last / len(texts):.0f}%, want >= 25%)")
    if energy is not None and P.get("music"):
        cues = [(m["t"], m["track"]) for m in P["music"]]
        print("music: " + ", ".join(f"{_ts(t)} {tr} ({energy.get(tr, '?')})" for t, tr in cues))
        warn += music_warnings(cues, energy, end / 2)
    longest = max([b - a for a, b in gaps(ev, end)] or [0.0])
    print(f"pace: {mins:.1f} min, {len(items) - 1} cuts, {len(ev)} visual events, {len(sfx)} sfx ({rate:.1f}/min), "
          f"{sum(1 for o in ovl if o['kind'] == 'headline')} headlines, {sum(1 for o in ovl if o['kind'] == 'keyline')} "
          f"key lines, {len(num_cards)} number cards, longest gap {longest:.1f}s")
    for w in warn:
        print("  WARN " + w)
    return warn, longest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlist", nargs="?")
    ap.add_argument("--edit")
    ap.add_argument("--timeline")
    ap.add_argument("--window", type=float, default=20.0)
    ap.add_argument("--gap", type=float, default=30.0)
    ap.add_argument("--strict", action="store_true", help="exit 1 on a gap >= --gap")
    ap.add_argument("--energy", default=ENERGY)
    ap.add_argument("--no-music", action="store_true", help="skip the music check (make_edit.py already ran it)")
    ap.add_argument("--measure-music", metavar="MUSIC_DIR")
    ap.add_argument("--write", action="store_true", help="with --measure-music: update music_energy.json")
    a = ap.parse_args()
    if a.measure_music:
        return measure_music(a.measure_music, a.write)
    if a.edit:
        if not a.timeline:
            ap.error("--edit needs --timeline")
        sys.path.insert(0, HERE)
        import render_v3
        edit, tl = json.load(open(a.edit, encoding="utf-8")), json.load(open(a.timeline, encoding="utf-8"))
        if edit.get("style") != "v3":
            print("pace lint: not a v3 edit: nothing to check")
            return
        P = render_v3.plan(edit, tl, os.path.join(os.path.dirname(os.path.abspath(a.timeline)), "narration.wav"))
    elif a.cutlist:
        P = json.load(open(a.cutlist, encoding="utf-8"))
    else:
        ap.error("give a cutlist.json or --edit and --timeline")
    _, longest = lint(P, a.window, a.gap, None if a.no_music else load_energy(a.energy))
    if a.strict and longest >= a.gap:
        sys.exit(1)


if __name__ == "__main__":
    main()
