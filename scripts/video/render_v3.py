"""v3 documentary editor (docs/style-guide.md): cuts that follow the voice, kinetic type and animated number cards
timed to the syllable, one colour world, designed pauses, a music bed you can hear and rule-based sound design.

  python render_v3.py <cutlist.json> <narration.wav> <edit.json> <timeline.json> <music_dir> <fonts_dir>
                      <assets_dir> <out.mp4> [--workers 4] [--range a,b]

The cut list comes from scripts/footage/assign_shots.py, which runs plan() below (edit["style"] == "v3") and gives
every footage item its own shot. Next to the master it writes <out>.en.srt, the English caption track (CC) built
from the C lines. --range renders only seconds a-b of the timeline (quick checks).

edit.json sections (make_edit.py builds them from edit.spec) may hold, besides v2's "v", "c", "sfx":
  "v"  beats: {"at", "q", "opt"} footage | {"at", "gfx"} diagram | {"at", "num": spec, "q"} number card beat
  "k"  kinetic headlines {"at", "lines": [{"text", "at"}], "kicker", "sub", "pos"}
  "n"  number cards over the running footage {"at", "num": spec}
  "m"  moments {"at", "breath", "riser", "impact", "trans", "drop", "swell"}
  "t"  transition overrides {"at", "trans"};  "s" explicit sounds {"at", "type", "gain"};  "footer" text
Top level: "style": "v3", "lead_in", "title" {"kicker", "main"} or "title_card", "cards", "count_total",
"music" [{"from": section, "track", "gain"}], "grade" {...}, "card_query", "bg_query".
"""
import argparse, json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np, cv2

sys.path.insert(0, os.path.dirname(__file__))
import render_video as rv  # noqa: E402  (diagram graphics)
import render_v2  # noqa: E402  (worker init, zoom/whip transitions)
import mograph as mg  # noqa: E402
import sfx as fx  # noqa: E402
from grade import Grade  # noqa: E402

W, H, FPS, SR = rv.W, rv.H, rv.FPS, rv.SR
G = rv.G
TARGET = {"default": 3.0, "hold": 5.5, "flash": 0.6}   # scene length by beat option (s)
MIN_SCENE = {"default": 1.4, "hold": 3.0, "flash": 0.45}
MAX_SCENE = {"default": 6.5, "hold": 8.0, "flash": 1.0}   # hard cap: may cut under a headline (overlays persist)
MOVES = ["push", "drift", "pull", "push", "roll"]
TD = {"dip": 12, "dissolve": 12, "flare": 10, "flash": 8, "whip": 9, "zoom": 10, "soft": 8}  # transition frames
BED_LU = 16.0      # music bed under the voice while speaking (LU); pauses get +PAUSE_LIFT dB
PAUSE_LIFT = 3.0
DIP_PAUSE = 0.5    # a cut inside a pause at least this long becomes a dip to black


# ------------------------------------------------------------------ timing
def pauses_from_wav(path):
    """Pauses (s, narration time) >= 0.16 s: 10 ms RMS more than 38 dB under the speech level."""
    import soundfile as sf
    v, sr = sf.read(path)
    v = v.mean(1) if v.ndim > 1 else v
    hop = int(sr * 0.01)
    n = len(v) // hop
    r = np.sqrt((v[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9
    quiet = r < np.percentile(r, 95) * 10 ** (-38 / 20)
    out, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= 0.16:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


class Timing:
    """Narration time (timeline.json) <-> video time: lead-in offset plus the breaths inserted before moments."""

    def __init__(self, edit, tl, pauses):
        self.off = edit.get("lead_in", 2.0)
        self.secs = {s["id"]: s for s in tl["sections"]}
        self.order = [s["id"] for s in tl["sections"]]
        self.pauses = pauses
        self.breaths = []  # (narration time, seconds)

    def idx(self, sid, trig, after=0):
        """Character index of the first occurrence of trig in the section at or after `after`."""
        if trig is None:
            return after
        i = "".join(self.secs[sid]["chars"]).find(trig, after)
        if i < 0:
            raise SystemExit(f"[{sid}] trigger not found{' after the line before' if after else ''}: {trig!r}")
        return i

    def tn(self, sid, trig, after=0):
        s = self.secs[sid]
        if trig is None and not after:
            return s["start"]
        return s["char_start"][self.idx(sid, trig, after)]

    def v(self, tn):
        return tn + self.off + sum(d for b, d in self.breaths if tn >= b - 1e-6)

    def vt(self, sid, trig, after=0):
        return self.v(self.tn(sid, trig, after))

    def pause_before(self, tn, look=0.3):
        """The pause that ends right at narration time tn (a word start), or None."""
        for a, b in self.pauses:
            if tn - look <= b <= tn + 0.08 and a < tn:
                return a, b
        return None

    def cut_at(self, tn):
        """A cut for a beat whose first word starts at tn: inside the pause before it if there is one."""
        p = self.pause_before(tn)
        if p and p[1] - p[0] >= 0.12:
            return self.v(p[0] + 0.55 * (p[1] - p[0]))
        return self.v(tn) - 0.04

    def words(self, sid):
        s = self.secs[sid]
        ch, cs = s["chars"], s["char_start"]
        return [self.v(cs[i]) for i in range(len(ch)) if not ch[i].isspace() and (i == 0 or ch[i - 1].isspace())]

    def pause_mids(self, t0, t1):
        return [(self.v((a + b) / 2), b - a) for a, b in self.pauses if t0 <= self.v((a + b) / 2) <= t1]


def card_parts(edit, sid):
    num, title = edit["cards"][sid]
    digits = "".join(ch for ch in num if ch.isdigit())
    return (int(digits) if digits else num), title


COUNTING = {"hero", "scale", "thermo", "gauge", "line", "equation", "progress", "route", "hud"}


def card_sfx(ns, t0):
    """Sounds for a number card / overlay starting at t0: a roll while it counts and a hit on landing; a pop for
    callouts, lower thirds and fact cards; a hit on each chart marker."""
    tp = ns.get("template", "hero")
    if tp in COUNTING and mg.parse_num(ns.get("value")) is not None:
        return [("roll", t0 + ns["land_t"] - ns["count_s"], 0, {"d": round(ns["count_s"], 2)}), ("hit", t0 + ns["land_t"] - 0.01, 0)]
    if tp == "chart":
        return [("whoosh", t0 + 0.1, -4, {"d": float(ns.get("draw", 2.0)), "f0": 300, "f1": 1800})]
    return [("pop", t0 + (0.12 if tp == "name" else 0.05), -2)]


# ------------------------------------------------------------------ planning
def plan(edit, tl, voice_wav=None):
    pauses = tl.get("pauses") or (pauses_from_wav(voice_wav) if voice_wav and os.path.exists(voice_wav) else [])
    T = Timing(edit, tl, pauses)
    S = edit["sections"]
    order = T.order
    # 1. breaths before moments (they shift everything after them)
    for sid in order:
        for m in S.get(sid, {}).get("m", []):
            tn = T.tn(sid, m["at"])
            p = T.pause_before(tn)
            tb = (p[0] + p[1]) / 2 if p else tn - 0.02
            m["_tb"] = tb
            T.breaths.append((tb, float(m.get("breath", 1.6))))
    T.breaths.sort()
    total = T.v(tl["total"]) + 3.0
    cards = edit.get("cards", {})
    n_total = edit.get("count_total", len(cards))
    first_card = next((k for k, sid in enumerate(order) if sid in cards), None)
    title = edit.get("title") or {}
    if not title and edit.get("title_card"):
        tc = edit["title_card"]
        kick, _, main = tc.partition(" ABOUT ")
        title = {"kicker": kick + " ABOUT", "main": main} if main else {"kicker": "", "main": tc}

    items, ovl, caps, sfx, mus = [], [], [], [], []
    moments = {}     # video time of the reveal word -> moment spec (with "_vb": video time the breath starts)
    for sid in order:
        for m in S.get(sid, {}).get("m", []):
            m["_vb"] = T.v(m["_tb"]) - float(m.get("breath", 1.6))
            moments[round(T.vt(sid, m["at"]), 3)] = m

    # 2. where each section's own picture starts (cards and titles sit in the gap before a section)
    heads = {}
    for k, sid in enumerate(order):
        s = T.secs[sid]
        if k == 0:
            heads[sid] = {"t": 0.0, "first": 0.0}
            continue
        prev_end = T.v(T.secs[order[k - 1]]["end"]) + 0.3
        on_start = round(T.v(s["start"]), 3) in moments  # a moment on the first word: cut right on it
        h = {"t": prev_end, "first": T.v(s["start"]) if on_start else T.cut_at(s["start"])}
        if sid in cards:  # the chapter card runs into the first words; longer after the title card
            h["first"] = T.v(s["start"]) + (1.2 if k == first_card and title else 0.9)
        heads[sid] = h

    for k, sid in enumerate(order):
        s, spec, h = T.secs[sid], S.get(sid, {"v": [], "c": []}), heads[sid]
        nxt = order[k + 1] if k + 1 < len(order) else None
        sec_end = total if nxt is None else heads[nxt]["t"] if nxt in cards else heads[nxt]["first"]
        if sid in cards:
            c0 = h["t"]
            if k == first_card and title:
                items.append({"kind": "title", "sec": sid, "t0": c0, "t1": c0 + 2.4, "ttl": title,
                              "q": edit["card_query"], "trans": "dip"})
                sfx += [("sting", c0 + 0.05, 0), ("whoosh_big", c0 - 0.55, -3)]
                mus.append({"kind": "swell", "t0": c0 - 0.3, "peak": c0 + 0.4, "t1": c0 + 3.0, "db": 4.0})
                c0 += 2.4
            num, ctitle = card_parts(edit, sid)
            items.append({"kind": "card", "sec": sid, "t0": c0, "t1": h["first"], "num": num, "ctitle": ctitle,
                          "n_total": n_total, "q": edit["card_query"], "trans": "dip" if k != first_card else "soft"})
            sfx += [("whoosh_big", c0 - 0.6, 0), ("hit", c0 + 0.28, -2)]
            sfx += [("tick", c0 + 0.45 + 0.06 * i, -4) for i in range(len(ctitle.split()))]
            fl = spec.get("footer") or ctitle.replace("*", "")
            ovl.append({"kind": "footer", "t0": h["first"], "t1": sec_end, "left": f"FACT {num} / {n_total}", "right": fl})
        first = h["first"]
        # kinetic headlines first: their windows are protected from scene cuts
        heads_k = []
        for kk in spec.get("k", []):
            lines, t_prev = [], max(first, T.vt(sid, kk["at"])) if kk["at"] else first + 0.3
            pos = T.idx(sid, kk["at"]) if kk["at"] else 0  # line triggers are found after the headline's own trigger
            for i, ln in enumerate(kk["lines"]):
                if ln.get("at"):
                    pos = T.idx(sid, ln["at"], pos)
                t = max(first, T.v(T.secs[sid]["char_start"][pos])) if ln.get("at") else (t_prev if i == 0 else t_prev + 0.22)
                lines.append({"text": ln["text"], "t": t})
                t_prev = t
                sfx.append(("tick", t - 0.01, 0))
            hk = {"kind": "headline", "lines": lines, "kicker": kk.get("kicker"), "sub": kk.get("sub"),
                  "pos": kk.get("pos", "left"), "t0": lines[0]["t"] - 0.1, "t_last": lines[-1]["t"]}
            if hk["kicker"]:
                hk["kicker_t"] = lines[0]["t"] - 0.08
            if hk["sub"]:
                hk["sub_t"] = max(first, T.vt(sid, kk["sub_at"], pos)) if kk.get("sub_at") else lines[-1]["t"] + 0.25
            heads_k.append(hk)
        protect = [(hk["t0"] - 0.2, hk["t_last"] + 1.6) for hk in heads_k]
        for nn in spec.get("n", []):  # number cards over footage: no cut while the number counts
            t0 = max(first, T.vt(sid, nn["at"])) if nn["at"] else first
            ld = nn["num"].get("land")
            land = T.vt(sid, ld, T.idx(sid, nn["at"])) if ld else t0 + 1.3
            protect.append((t0 - 0.2, max(t0 + 1.0, land + 0.5)))
        # beats -> scenes
        vb = spec["v"]
        starts = []
        for j, b in enumerate(vb):
            if j == 0:
                starts.append(first)
                continue
            tn = T.tn(sid, b["at"])
            tv = T.v(tn)
            starts.append(max(first, tv if round(tv, 3) in moments else T.cut_at(tn)))
        words = [w for w in T.words(sid)]
        for j, b in enumerate(vb):
            b0, b1 = starts[j], (starts[j + 1] if j + 1 < len(vb) else sec_end)
            if b1 - b0 < 0.4:
                continue
            base = {"sec": sid, "beat": j}
            if "gfx" in b:
                items.append({**base, "kind": "gfx", "t0": b0, "t1": b1, "gfx": b["gfx"], "q": edit["bg_query"]})
                continue
            if "num" in b:
                ns = dict(b["num"])
                land = T.vt(sid, ns["land"], T.idx(sid, b["at"])) if ns.get("land") else b0 + 1.3
                ns["land_t"] = max(0.35, land - b0)
                ns["count_s"] = min(float(ns.get("count", 1.3)), ns["land_t"] - 0.15)
                items.append({**base, "kind": "num", "t0": b0, "t1": b1, "num": ns, "q": b.get("q") or edit["bg_query"]})
                sfx += card_sfx(ns, b0) + [("whoosh", b0 - 0.3, -4)]
                continue
            opt = b.get("opt", "default")
            tgt = float(opt[:-1]) if opt.endswith("s") and opt[:-1].replace(".", "").isdigit() else TARGET.get(opt, 3.0)
            mn = MIN_SCENE.get(opt if opt in MIN_SCENE else "default", 1.4)
            L = b1 - b0
            n = max(1, round(L / tgt))
            cands = [(w, 0.0) for w in words if b0 + mn <= w <= b1 - mn] + \
                    [(t, d) for t, d in T.pause_mids(b0 + mn, b1 - mn)]
            cuts = [b0]
            for q in range(1, n):
                ideal = b0 + L * q / n
                ok = [(t, d) for t, d in cands if abs(t - ideal) <= 0.9 and t - cuts[-1] >= mn and b1 - t >= mn
                      and not any(a_ <= t <= z_ for a_, z_ in protect)]
                if ok:
                    cuts.append(min(ok, key=lambda c: abs(c[0] - ideal) - (0.6 if c[1] >= 0.15 else 0))[0])
                elif ideal - cuts[-1] >= mn and not any(a_ <= ideal <= z_ for a_, z_ in protect):
                    cuts.append(ideal)
            cuts.append(b1)
            mx = MAX_SCENE.get(opt if opt in MAX_SCENE else "default", 6.5)
            q = 0
            while q < len(cuts) - 1:  # split anything still longer than the cap, protected windows or not
                c0, c1 = cuts[q], cuts[q + 1]
                if c1 - c0 <= mx:
                    q += 1
                    continue
                mid = (c0 + c1) / 2
                ok = [(t, d) for t, d in cands if c0 + mn <= t <= c1 - mn]
                cut = min(ok, key=lambda c: abs(c[0] - mid) - (0.6 if c[1] >= 0.15 else 0))[0] if ok else mid
                cuts.insert(q + 1, cut)
            for q in range(len(cuts) - 1):
                items.append({**base, "kind": "clip", "t0": cuts[q], "t1": cuts[q + 1], "q": b["q"], "opt": opt})
        # number cards over the running footage
        for nn in spec.get("n", []):
            ns = dict(nn["num"])
            t0 = max(first, T.vt(sid, nn["at"])) if nn["at"] else first
            land = T.vt(sid, ns["land"], T.idx(sid, nn["at"])) if ns.get("land") else t0 + 1.3
            ns["land_t"] = max(0.35, land - t0)
            ns["count_s"] = min(float(ns.get("count", 1.3)), ns["land_t"] - 0.15)
            t1 = t0 + float(ns.get("dur", 3.5 if ns.get("template") == "name" else ns["land_t"] + 2.2))
            ns["dur"] = t1 - t0
            ovl.append({"kind": "num", "t0": t0, "t1": t1, "num": ns})
            sfx += card_sfx(ns, t0)
        # captions: all go to the CC track; big ones also become a burned-in key line
        for c in spec.get("c", []):
            t = first if c["at"] is None else max(first, T.vt(sid, c["at"]))
            caps.append({"sec": sid, "t": t, "end": T.v(s["end"]), "text": c["text"], "big": c.get("big", False)})
        for fx_ in spec.get("sfx", []):
            sfx.append((fx_["type"], T.vt(sid, fx_["at"]), 0))
        for fx_ in spec.get("s", []):
            sfx.append((fx_["type"], T.vt(sid, fx_["at"]), float(fx_.get("gain", 0))))
        for hk in heads_k:
            ovl.append(hk)
    caps.sort(key=lambda c: c["t"])
    for i, c in enumerate(caps):
        nxt = caps[i + 1]["t"] if i + 1 < len(caps) else total
        c["t1"] = min(nxt, c["t"] + 7.0, c["end"] + 0.3)
    busy = [(o["t0"], o["t_last"] + 1.6) if o["kind"] == "headline" else (o["t0"], o["t1"]) for o in ovl
            if o["kind"] == "headline" or (o["kind"] == "num" and o["num"].get("template") != "name")]
    busy += [(it["t0"], it["t1"]) for it in items if it["kind"] in ("num", "card", "title", "gfx")]
    for i, c in enumerate(caps):
        if not c["big"]:
            continue
        nxt_big = next((d["t"] for d in caps[i + 1:] if d["big"]), total)
        t1 = min(c["t"] + 2.6, nxt_big - 0.1, c["end"] + 0.4)
        if any(a_ - 0.2 < c["t"] < z_ for a_, z_ in busy):
            print(f"  note: key line {c['text']!r} at {c['t']:.1f}s overlaps a headline/number card - skipped")
            continue
        ovl.append({"kind": "keyline", "t0": c["t"], "t1": t1, "text": c["text"]})
        sfx.append(("pop", c["t"] - 0.01, 0))
        sfx += [("tick", c["t"] + 0.07 * i, -5) for i in range(1, len(c["text"].split()))]

    items.sort(key=lambda it: it["t0"])
    # 3. transitions, camera moves, moments
    tov = {}
    for sid in order:
        for t_ in S.get(sid, {}).get("t", []):
            tov[round(T.vt(sid, t_["at"]), 3)] = t_["trans"]
    mv = 0
    for i, it in enumerate(items):
        if i == 0:
            it["trans"] = "cut"
        elif "trans" not in it:
            prev = items[i - 1]
            hit_m = next((m for tm, m in moments.items() if abs(tm - it["t0"]) < 0.06), None)
            near_t = next((tr for tm, tr in tov.items() if abs(tm - it["t0"]) < 0.35), None)
            pm = [d for t, d in T.pause_mids(it["t0"] - 0.35, it["t0"] + 0.35)]
            if near_t:
                it["trans"] = near_t
            elif hit_m:
                it["trans"] = hit_m.get("trans", "flare")
            elif prev["kind"] in ("card", "title"):
                it["trans"] = "soft"
            elif pm and max(pm) >= DIP_PAUSE:
                it["trans"] = "dip"
            else:
                it["trans"] = "cut"
        if it["kind"] == "clip":
            hit_m = next((m for tm, m in moments.items() if abs(tm - it["t0"]) < 0.06), None)
            opt = it.get("opt", "default")
            if hit_m or opt == "flash":
                it["move"], it["rate"] = "impact", 0.12
            elif opt == "shrink":  # a fast pull-back: the subject visibly shrinks ("squeeze the whole Earth")
                it["move"], it["rate"] = "pull", 0.22
            else:
                it["move"] = MOVES[mv % len(MOVES)]
                it["rate"] = 0.015 if opt == "hold" else 0.032
                it["dir"] = 1 if (mv // len(MOVES)) % 2 == 0 else -1
                mv += 1
        tr = it["trans"]
        if it["kind"] in ("card", "title"):
            continue  # their whoosh is already placed
        if tr == "dip":
            sfx.append(("whoosh", it["t0"] - 0.2, -2, {"d": 0.6}))
        elif tr == "flare":
            sfx.append(("flare", it["t0"] - 0.08, 0))
        elif tr == "flash":
            sfx.append(("hit", it["t0"], 0))
        elif tr in ("whip", "zoom"):
            sfx.append(("whoosh", it["t0"] - 0.2, 0, {"d": 0.4, "f0": 700, "f1": 3800}))
    for tm, m in moments.items():
        r = float(m.get("riser", 1.8))
        if r > 0:
            sfx.append(("riser", tm - r, 0, {"d": r}))
        imp = m.get("impact", "impact")
        if imp and imp != "none":
            sfx.append((imp, tm, 0))
        tb = m["_vb"]
        if m.get("drop"):
            mus.append({"kind": "drop", "t0": tb, "t1": tm})
            mus.append({"kind": "swell", "t0": tm, "peak": tm + 0.05, "t1": tm + 2.5, "db": 4.0})
        else:
            mus.append({"kind": "swell", "t0": tb - 0.2, "peak": tm, "t1": tm + 1.8, "db": float(m.get("swell", 7.0))})
    # headline end: the first cut after its last line has been read (1.6 s), at most 4 s after it
    bounds = [it["t0"] for it in items]
    for o in ovl:
        if o["kind"] == "headline":
            after = [b for b in bounds if b >= o["t_last"] + 1.6]
            o["t1"] = min(after[0] if after else o["t_last"] + 3.0, o["t_last"] + 4.0)
            nxt = [p["t0"] for p in ovl if (p["kind"] in ("keyline", "headline") or (p["kind"] == "num" and
                   p["num"].get("template") != "name")) and o["t_last"] < p["t0"] < o["t1"]]
            if nxt:  # make way for the next key line / number card
                o["t1"] = max(o["t_last"] + 0.8, min(nxt) - 0.12)
    full = [it["t0"] for it in items if it["kind"] in ("card", "title")]
    for o in ovl:  # nothing runs over a chapter or title card: it is gone by the time the card cuts in
        hit = [t for t in full if o["kind"] != "footer" and o["t0"] < t < o["t1"]]
        if hit:
            o["t1"] = min(hit) - 0.1
    for it in items:
        it["f0"], it["f1"] = round(it["t0"] * FPS), round(it["t1"] * FPS)
    items[-1]["f1"] = round(total * FPS)
    for m in moments.values():
        m.pop("_tb", None), m.pop("_vb", None)
    sfx = [list(x) for x in sorted(sfx, key=lambda x: x[1])]
    music = []
    starts = {s["id"]: T.v(s["start"]) for s in tl["sections"]}
    for i, m in enumerate(edit.get("music", [])):
        music.append({"t": 0.0 if i == 0 else starts[m["from"]] - 1.5, "track": m["track"], "gain": m.get("gain", 0.0)})
    return {"style": "v3", "items": items, "ovl": ovl, "caps": caps, "sfx": sfx, "mus": mus, "music": music,
            "breaths": T.breaths, "total": total, "off": T.off, "grade": edit.get("grade", {})}


# ------------------------------------------------------------------ frames
class Readers:
    """One decoder per footage item, read sequentially; reopened (seek) when a chunk starts mid-item."""

    def __init__(self):
        self.r = {}

    def get(self, it, f):
        key = id(it)
        rel = f - it["f0"]
        rd = self.r.get(key)
        if rd is None or rd[1] != rel:
            if rd:
                rd[0].cap.release()
            rd = [render_v2.ClipReader(os.path.join(G["clips"], it["clip"] + ".mp4"), it["ss"] + max(0, rel) / FPS,
                                       it.get("crop")), rel]
            self.r[key] = rd
        fr = rd[0].read()
        rd[1] = rel + 1
        return fr

    def close(self):
        for rd in self.r.values():
            rd[0].cap.release()
        self.r = {}


def camera(fr, it, t, D):
    m, r, d = it.get("move", "push"), it.get("rate", 0.03), it.get("dir", 1)
    z, rot, dx, dy = 1.0, 0.0, 0.0, 0.0
    if m == "push":
        z = 1.02 + r * t
    elif m == "pull":
        z = 1.02 + r * max(0.0, D - t)
    elif m == "drift":
        z, dx = 1.07, d * (t / max(D, 0.1) - 0.5) * W * 0.035
    elif m == "roll":
        z, rot = 1.07 + 0.01 * t, d * (t / max(D, 0.1) - 0.5) * 2.2
    elif m == "impact":
        z = 1.0 + 0.1 * mg.ease_out(t / 0.45) + 0.012 * t
        k = math.exp(-t / 0.22)
        dx, dy = 9 * math.sin(2 * math.pi * 9 * t) * k, 7 * math.sin(2 * math.pi * 11 * t + 1) * k
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, z)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def dim(fr, k=0.45, blur=2.5):
    return (cv2.GaussianBlur(fr, (0, 0), blur) * k).astype(np.uint8)


def item_frame(it, f):
    t = (f - it["f0"]) / FPS
    D = max((it["f1"] - it["f0"]) / FPS, 0.1)
    src = G["grade"](G["rd"].get(it, f), f)
    if it["kind"] == "clip":
        return camera(src, it, t, D)
    bg = camera(src, {"move": "push", "rate": 0.012}, t, D)
    if it["kind"] == "num":
        fr = dim(bg, 0.5, 2.0)
        return mg.card(fr, it["num"], t, D)
    if it["kind"] == "card":
        fr = dim(bg, 0.42)
        mg.chapter(fr, it["num"], it["n_total"], it["ctitle"], t, D)
        return fr
    if it["kind"] == "title":
        fr = dim(bg, 0.42)
        mg.title(fr, it["ttl"].get("kicker", ""), it["ttl"]["main"], t, D)
        return fr
    G["bgframe"] = dim(bg, 0.4)
    it.setdefault("flash_t", D * 0.45)
    fr = rv.gfx(it["gfx"], t, D, it)
    G["bgframe"] = None
    return fr


def _flare_light(p):
    """Warm light leak sweeping left to right; peak in the middle of the transition."""
    if "flare" not in G:
        yy, xx = np.mgrid[0:H // 4, 0:W // 2].astype(np.float32)
        G["flare"] = (yy, xx)
    yy, xx = G["flare"]
    cx = (-0.25 + 1.5 * p) * (W // 2)
    a = np.exp(-(((xx - cx) / (W * 0.16)) ** 2) - (((yy - H / 8) / (H * 0.22)) ** 2))
    k = math.sin(math.pi * p) ** 1.4
    light = np.dstack([a * 90, a * 175, a * 255]) * k + np.array([30, 70, 120]) * k * 0.6
    return cv2.resize(light.astype(np.float32), (W, H))


def transition(a, b, p, kind):
    if kind == "dip":
        e = mg.ease_in_out(p)
        return (a * (1 - 2 * e)).astype(np.uint8) if e < 0.5 else (b * (2 * e - 1)).astype(np.uint8)
    if kind in ("dissolve", "soft"):
        return cv2.addWeighted(a, 1 - mg.ease_in_out(p), b, mg.ease_in_out(p), 0)
    if kind == "flare":
        w = np.clip((p - 0.35) / 0.3, 0, 1)
        base = cv2.addWeighted(a, 1 - w, b, w, 0).astype(np.float32)
        light = _flare_light(p)
        return np.clip(255 - (255 - base) * (255 - light) / 255, 0, 255).astype(np.uint8)
    return render_v2.transition(a, b, p, kind)


def draw_ovl(fr, ovl, t):
    for o in ovl:
        if not (o["t0"] - 0.05 <= t < o["t1"]):
            continue
        k = o["kind"]
        if k == "headline":
            mg.headline(fr, {**o, "t1": o["t1"]}, t)
        elif k == "keyline":
            mg.keyline(fr, {"text": o["text"], "t": o["t0"], "t1": o["t1"]}, t)
        elif k == "num":
            tt = t - o["t0"]
            op = mg.clamp01((o["t1"] - t) / 0.25)
            if op < 1:
                tmp = fr.copy()
                mg.card(tmp, o["num"], tt, o["t1"] - o["t0"])
                cv2.addWeighted(tmp, op, fr, 1 - op, 0, fr)
            else:
                mg.card(fr, o["num"], tt, o["t1"] - o["t0"])
        elif k == "footer":
            op = 0.5 * mg.clamp01((t - o["t0"]) / 0.5) * mg.clamp01((o["t1"] - t) / 0.4)
            mg.footer(fr, o["left"], o["right"], op)
        elif k == "endcard":
            mg.endcard(fr, t, o["t0"], o["t1"])


def init(clips, fonts, assets, grade):
    render_v2.init(clips, fonts, assets)
    mg.set_fonts(fonts)
    G["grade"] = Grade(**grade)
    G["rd"] = Readers()


def render_chunk(args):
    c0, c1, items, ovl, total_f, path = args
    if os.path.exists(path):
        return path
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-g", "60",
                           path + ".part.mp4"], stdin=subprocess.PIPE)
    k = 0
    for f in range(c0, c1):
        while k + 1 < len(items) and f >= items[k + 1]["f0"]:
            k += 1
        it = items[k]
        fr = item_frame(it, f)
        tr = it.get("trans", "cut")
        if k > 0 and tr in TD and f - it["f0"] < TD[tr]:
            fr = transition(item_frame(items[k - 1], f), fr, (f - it["f0"] + 1) / (TD[tr] + 1), tr)
        t = f / FPS
        draw_ovl(fr, ovl, t)
        fi, fo = G.get("fade_in", 12), G.get("fade_out", 75)  # Shorts: 0, 0 (the hook hits on frame 0, the end loops)
        mg.logo(fr, 0.8 * mg.clamp01((t - 0.6) / 0.5) * (mg.clamp01((total_f - f) / 60) if fo else 1.0))
        if f < fi:
            fr = (fr * (f / fi)).astype(np.uint8)
        elif fo and f > total_f - fo:
            fr = (fr * max(0, (total_f - f) / fo)).astype(np.uint8)
        ff.stdin.write(np.ascontiguousarray(fr).tobytes())
    ff.stdin.close()
    ff.wait()
    G["rd"].close()
    os.replace(path + ".part.mp4", path)
    return path


# ------------------------------------------------------------------ audio
def _load(path, n_ch=2):
    import soundfile as sf
    y, sr = sf.read(path, always_2d=True)
    if sr != SR:
        from scipy.signal import resample_poly
        g = math.gcd(SR, sr)
        y = resample_poly(y, SR // g, sr // g, axis=0)
    if n_ch == 1:
        return y.mean(1)
    return y if y.shape[1] == 2 else np.repeat(y[:, :1], 2, 1)


def _curve(n, pts):
    """Piecewise-linear gain curve (dB) from [(t, db), ...]."""
    ts = np.array([p[0] for p in pts]) * SR
    return np.interp(np.arange(n), ts, [p[1] for p in pts])


def _loop(y, L, xf):
    """y repeated to L samples with crossfaded joins."""
    if len(y) >= L:
        return y[:L].copy()
    out, pos = np.zeros((L, 2)), 0
    while pos < L:
        c = y[:L - pos].copy()
        if pos:
            m = min(xf, len(c))
            c[:m] *= np.linspace(0, 1, m)[:, None]
            out[pos:pos + m] *= np.linspace(1, 0, m)[:, None]
        out[pos:pos + len(c)] += c
        pos += len(c) - xf if len(c) == len(y) else len(c)
    return out


def _level(x, keep=0.25, win=3.0):
    """Slow leveller for a music bed: the 3 s loudness keeps only `keep` of its swing around the integrated
    loudness (a track with a quiet intro and a loud hit becomes a steady bed). Returns (levelled, integrated)."""
    M, I = fx.loudness(x)
    p = 10 ** (M / 10)
    k = max(1, int(win / 0.1))
    st = 10 * np.log10(np.convolve(p, np.ones(k) / k, "same") + 1e-12)
    corr = np.clip((1 - keep) * (I - st), -12, 9)
    corr = np.convolve(corr, np.ones(10) / 10, "same")
    g = np.interp(np.arange(len(x)), np.arange(len(corr)) * 0.1 * SR, corr)
    y = x * (10 ** (g / 20))[:, None]
    return y, fx.loudness(y)[1]


def voice_track(narr, P):
    """The narration on the video clock: breaths spliced in, shifted by the lead-in (mono, P["total"] long)."""
    total, off = P["total"], P["off"]
    n = int(total * SR)
    v = _load(narr, 1)
    # splice the breaths into the voice (silence at the quietest point near each insertion)
    parts, last = [], 0
    for tb, d in P["breaths"]:
        i = int(tb * SR)
        w = v[max(0, i - int(0.08 * SR)):i + int(0.08 * SR)]
        if len(w):
            e = np.convolve(np.abs(w), np.ones(220) / 220, "same")
            i = max(0, i - int(0.08 * SR)) + int(np.argmin(e))
        parts += [v[last:i], np.zeros(int(d * SR))]
        last = i
    v = np.concatenate(parts + [v[last:]])
    voice = np.zeros(n)
    o = int(off * SR)
    voice[o:o + len(v)] = v[:n - o]
    return voice


def mix(narr, P, music_dir):
    total = P["total"]
    n = int(total * SR)
    voice = voice_track(narr, P)
    M, _ = fx.loudness(voice)
    speech = M[M > -45]
    # the mono voice plays on both channels: +3 dB in BS.1770 terms, which is what the music and SFX sit against
    Vm = (float(np.median(speech)) if len(speech) else -18.0) + 10 * math.log10(2)
    # speaking mask -> gentle lift of the bed in pauses
    env = np.convolve(np.abs(voice), np.ones(int(0.05 * SR)) / int(0.05 * SR), "same")
    thr = np.percentile(env[env > 1e-4], 50) * 0.25 if (env > 1e-4).any() else 1e-3
    spk = (env > thr).astype(float)
    k = int(0.35 * SR)
    spk = np.convolve(spk, np.ones(k) / k, "same")  # ~0.35 s attack/release
    lift = PAUSE_LIFT * (1 - np.clip(spk * 1.5, 0, 1))
    # music cues, each levelled to BED_LU under the voice, 2.5 s crossfades, looped with crossfades
    music = np.zeros((n, 2))
    xf = int(2.5 * SR)
    cues = P["music"] + [{"t": total}]
    for c, nxt in zip(cues, cues[1:]):
        y = _load(os.path.join(music_dir, c["track"]))
        a, b = int(c["t"] * SR), min(n, int(nxt["t"] * SR) + xf)
        L = b - a
        seg = _loop(y, L, xf)
        seg, I = _level(seg)
        seg *= 10 ** ((Vm - BED_LU + c.get("gain", 0.0) - I) / 20)
        g = np.ones(L)
        m = min(xf, L)
        if c["t"] > 0:
            g[:m] = np.linspace(0, 1, m)
        g[-m:] = np.minimum(g[-m:], np.linspace(1, 0, m))
        music[a:b] += seg * g[:, None]
    db = lift.copy()
    for e in P["mus"]:
        if e["kind"] == "swell":
            db += _curve(n, [(0, 0), (e["t0"], 0), (e["peak"], e["db"]), (e["peak"] + 0.3, e["db"]), (e["t1"], 0), (total, 0)])
        elif e["kind"] == "drop":
            db += _curve(n, [(0, 0), (e["t0"], 0), (e["t0"] + 0.25, -35), (e["t1"] - 0.02, -35), (e["t1"], 0), (total, 0)])
    tail = np.clip((total - np.arange(n) / SR) / 4, 0, 1)
    music *= (10 ** (db / 20) * tail)[:, None]
    # sound effects, levelled by their loudest 400 ms against the voice
    sfx = np.zeros((n, 2))
    for ev in P["sfx"]:
        kind, at, gain = ev[0], ev[1], ev[2]
        kw = ev[3] if len(ev) > 3 else {}
        x, pl = fx.make(kind, **kw)
        i = int(at * SR)
        if i >= n or i + len(x) <= 0:
            continue
        x = x * 10 ** ((Vm + fx.LEVEL.get(kind, -15) + gain - pl) / 20)
        j0 = max(0, -i)
        x = x[j0:n - i]
        sfx[i + j0:i + j0 + len(x)] += x
    out = voice[:, None] + music + sfx
    stems = {"voice": voice, "music": music, "sfx": sfx}
    return out, stems, Vm


def write_srt(caps, path):
    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(caps, 1):
            text = c["text"].strip('"')
            f.write(f"{i}\n{ts(c['t'])} --> {ts(max(c['t1'], c['t'] + 0.8))}\n{text}\n\n")


def main():
    ap = argparse.ArgumentParser()
    for a in ("cutlist", "narration", "edit", "timeline", "music", "fonts", "assets", "out"):
        ap.add_argument(a)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--range", default="", help="a,b: render only these seconds of the timeline")
    ap.add_argument("--chunk", type=float, default=10.0)
    a = ap.parse_args()
    P = json.load(open(a.cutlist))
    items, ovl, total = P["items"], P["ovl"], P["total"]
    total_f = round(total * FPS)
    r0, r1 = (float(x) for x in a.range.split(",")) if a.range else (0.0, total)
    f_a, f_b = round(r0 * FPS), min(total_f, round(r1 * FPS))
    print(f"{len(items)} items, {len(ovl)} overlays, {len(P['caps'])} captions, {len(P['sfx'])} sfx, {total:.1f}s")
    work = os.path.splitext(a.out)[0] + "_work"
    os.makedirs(work, exist_ok=True)
    step = int(a.chunk * FPS)
    jobs = [(c, min(c + step, f_b), items, ovl, total_f, os.path.join(work, f"v3_{c:06d}_{min(c + step, f_b):06d}.mp4"))
            for c in range(f_a, f_b, step)]
    with Pool(a.workers, initializer=init, initargs=(P["clips_dir"], a.fonts, a.assets, P.get("grade", {}))) as pool:
        for k, pth in enumerate(pool.imap(render_chunk, jobs)):
            print(f"  [{k + 1}/{len(jobs)}] {os.path.basename(pth)}", flush=True)
    import soundfile as sf
    out, stems, Vm = mix(a.narration, P, a.music)
    _, I = fx.loudness(out)
    out *= 10 ** ((-14.0 - I) / 20)  # linear gain to -14 LUFS; the limiter below only catches peaks
    wav = os.path.join(work, "mix.wav")
    sf.write(wav, out.astype(np.float32), SR, subtype="FLOAT")
    for k_, x in stems.items():
        sf.write(os.path.join(work, f"stem_{k_}.wav"), np.clip(x, -1, 1).astype(np.float32), SR)
    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.basename(j[5])}'\n" for j in jobs))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ss", f"{r0:.3f}", "-t", f"{(f_b - f_a) / FPS:.3f}",
                    "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "alimiter=limit=0.84:attack=3:release=80:level=false",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", a.out], check=True)
    srt = os.path.splitext(a.out)[0] + ".en.srt"
    write_srt([dict(c, t=c["t"] - r0, t1=c["t1"] - r0) for c in P["caps"] if r0 <= c["t"] < r1], srt)
    print("wrote", a.out, "and", srt, f"(mix {I:.1f} LUFS -> -14 linear, voice {Vm:.1f} LUFS while speaking)")


if __name__ == "__main__":
    main()
