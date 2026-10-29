"""Merge the measurements of a reference video into one report, and cut 10 fps frame strips of every event type.

  python report.py <an_dir> [--meta meta.json] [--topic "sun,सूरज,सूर्य"] [--intro 90] [--sections 0,95,210,...]
                   [--no-strips]

Inputs (from analyze_video.sh): visual.json, text_events.json, audio/audio_stats.json, transcript/words.json.
Writes <an_dir>/report.md (tables to copy into docs/research/...), <an_dir>/summary.json and
<an_dir>/sequences/*.jpg (20 frames, 10 fps x 2 s, per transition type, text style, camera move, SFX hit, ...).
The report quotes the transcript, so it stays with the reference material on Drive, never in the repo.
"""
import argparse, bisect, json, os, re, sys
from collections import Counter
import numpy as np, cv2

sys.path.insert(0, os.path.dirname(__file__))
from visual_stats import frames  # noqa: E402


def ts(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def load(p, default=None):
    return json.load(open(p)) if os.path.exists(p) else default


def nearest(sorted_vals, t):
    i = bisect.bisect_left(sorted_vals, t)
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(sorted_vals) and (best is None or abs(sorted_vals[j] - t) < abs(best - t)):
            best = sorted_vals[j]
    return best


def strip(video, t0, dur, out, label, fps=10, cols=5, w=384):
    h = w * 9 // 16
    fr = list(frames(video, fps, w, h, ss=max(0, t0), dur=dur))
    if not fr:
        return
    tiles = []
    for i, f in enumerate(fr):
        f = f.copy()
        cv2.putText(f, ts(t0 + i / fps), (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(f, ts(t0 + i / fps), (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        tiles.append(f)
    tiles += [np.zeros_like(tiles[0])] * (-len(tiles) % cols)
    img = np.vstack([np.hstack(tiles[r:r + cols]) for r in range(0, len(tiles), cols)])
    bar = np.zeros((26, img.shape[1], 3), np.uint8)
    cv2.putText(bar, label[:120], (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.imwrite(out, np.vstack([bar, img]), [cv2.IMWRITE_JPEG_QUALITY, 80])


SIGNPOSTS = {
    "ordinal (pehla/doosra/teesra...)": r"पहल[ाीे]|दूसर[ाीे]|तीसर[ाीे]|चौथ[ाीे]|पां?च[वँ]|पाँचव|आखिरी|आख़िरी|अंतिम",
    "numbered ('number', 'nambar')": r"नंबर|नम्बर|number",
    "now / next ('ab', 'ab baat')": r"(^|\s)अब(\s|$)",
    "but / however ('lekin', 'magar')": r"लेकिन|मगर|परंतु|पर\s",
    "so ('to')": r"(^|\s)तो(\s|$)",
    "viewer address ('aap', 'aapko', 'dosto')": r"(^|\s)आप|आपको|आपके|आपने|दोस्तों|दोस्तो",
    "imagine / think ('sochiye', 'imagine')": r"सोचि|सोचो|कल्पना|imagine|इमैजिन",
    "we ('hum', 'hamara')": r"(^|\s)हम(\s|$)|हमारा|हमारी|हमें",
    "question words ('kya', 'kaise', 'kyon')": r"(^|\s)क्या(\s|$)|कैसे|क्यों|कितना|कितनी",
    "what if ('agar')": r"(^|\s)अगर(\s|$)|what if",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("an")
    ap.add_argument("--video", default=None)
    ap.add_argument("--meta", default=None)
    ap.add_argument("--topic", default="")
    ap.add_argument("--intro", type=float, default=90)
    ap.add_argument("--sections", default="")
    ap.add_argument("--no-strips", action="store_true")
    a = ap.parse_args()
    an = a.an
    video = a.video or os.path.join(os.path.dirname(os.path.abspath(an)), "video.mp4")
    V = load(f"{an}/visual.json", {})
    T = load(f"{an}/text_events.json", {"events": [], "styles": []})
    A = load(f"{an}/audio/audio_stats.json", {})
    Wd = load(f"{an}/transcript/words.json", {})
    meta = load(a.meta, None) if a.meta else None
    meta = meta[0] if isinstance(meta, list) and meta else meta
    words = Wd.get("words", [])
    wstarts = [w["start"] for w in words]
    dur = V.get("duration_s") or A.get("duration_s")
    shots, cuts = V.get("shots", []), V.get("cuts", [])
    texts = T.get("events", [])
    md, S = [], {}
    sfx = A.get("sfx_events", [])
    # SFX candidates also catch details of the music. Keep the level band that is synced to the picture: the
    # lowest 4 dB peak-level band from which candidates land on a cut or text entry >= 1.5x as often as chance
    vis = np.sort(np.r_[[c["t"] for c in V.get("cuts", [])], [e.get("entry", {}).get("t_visible", e["t_first"]) for e in T.get("events", [])]])
    near_v = lambda t: float(np.min(np.abs(vis - t))) if len(vis) else 9.0
    sync_t = lambda e: e["peak_t"] if e["type"] in ("whoosh", "riser") else e["t"]
    sfx_floor = -36.0
    if len(vis) and sfx and V.get("duration_s"):
        chance = float(np.mean([near_v(t) <= 0.2 for t in np.arange(0, V["duration_s"], 0.05)]))
        for lo in range(-60, -28, 2):
            band = [e for e in sfx if lo <= e["peak_dbfs"] < lo + 4]
            if len(band) >= 15 and np.mean([near_v(sync_t(e)) <= 0.2 for e in band]) >= 1.5 * chance:
                sfx_floor = float(lo)
                break
        S["sfx_calibration"] = {"chance_on_visual_event": round(chance, 2), "peak_floor_dbfs": sfx_floor,
                                "candidates": len(sfx), "kept": sum(1 for e in sfx if e["peak_dbfs"] >= sfx_floor)}
    sfx = [e for e in sfx if e["peak_dbfs"] >= sfx_floor]
    # beat-aligned transients that land on a cut or a text pop are edit sounds laid on the music's beat
    cut0 = sorted(c["t"] for c in V.get("cuts", []))
    for e in A.get("music_beat_transients", []):
        if e["type"] in ("boom", "whoosh", "riser", "sub drop", "glitch") and any(abs(e["t"] - c) <= 0.1 for c in cut0):
            sfx.append(dict(e, on_music_beat=True))
    sfx.sort(key=lambda e: e["t"])
    segs = A.get("speech_segments", [])
    cut_t = sorted(c["t"] for c in cuts)
    tv = lambda e: e.get("entry", {}).get("t_visible", e["t_first"])

    # ---- summary
    L = np.array([s["dur"] for s in shots]) if shots else np.zeros(1)
    by_content = Counter()
    for s in shots:
        by_content[s["content"]] += s["dur"]
    tr_count = Counter(c["type"].split(" (")[0] for c in cuts)
    on_screen = np.zeros(int(dur * 10) + 1, bool)
    for e in texts:
        if e.get("on_screen_s", 1) > 0.5 * dur:
            continue  # a logo bug or watermark, not a text the edit puts up
        on_screen[int(tv(e) * 10):int((tv(e) + e.get("on_screen_s", 1)) * 10)] = True
    lv, dk, vo = A.get("levels", {}), A.get("ducking", {}), A.get("voice", {})
    S["summary"] = {
        "duration": dur, "size": V.get("size"), "fps": V.get("fps"),
        "shots": len(shots), "shot_median_s": round(float(np.median(L)), 2), "shot_mean_s": round(float(L.mean()), 2),
        "shot_p10_p90_s": [round(float(np.percentile(L, 10)), 2), round(float(np.percentile(L, 90)), 2)],
        "cuts_per_min": round(len(cuts) / dur * 60, 1) if dur else None,
        "content_share_pct": {k: round(100 * v / dur, 1) for k, v in by_content.most_common()},
        "transitions": dict(tr_count.most_common()),
        "text_events": len(texts), "text_styles": len(T.get("styles", [])),
        "text_on_screen_pct": round(100 * float(on_screen.mean()), 1),
        "wpm": vo.get("wpm_over_narration_span"), "wpm_speaking": vo.get("wpm_while_speaking"),
        "speech_pct": round(100 * vo.get("speech_fraction_of_runtime", 0), 1),
        "lufs": A.get("lufs_integrated"), "true_peak_dbfs": A.get("mix_true_peak_dbfs_approx"),
        "voice_minus_music_lu": [lv.get("voice_minus_music_lu_speaking"), lv.get("voice_minus_music_lu_pauses")],
        "ducking_db": dk.get("depth_db"), "music_tracks": A.get("music_distinct_tracks"),
        "sfx": A.get("sfx_counts"), "sfx_per_min": round(len(sfx) / dur * 60, 1) if dur else None,
        "grade": V.get("grade"),
    }
    md.append("# Measurements\n")
    md.append("| Metric | Value |\n|---|---|")
    for k, v in S["summary"].items():
        md.append(f"| {k} | {json.dumps(v, ensure_ascii=False)} |")

    # ---- SFX triggers
    pauses_end = [b0 for (a0, a1), (b0, b1) in zip(segs, segs[1:]) if b0 - a1 >= 0.8]
    big_text = [tv(e) for e in texts if e["height_px"] >= 90]
    for ev in sfx:
        t_on, t_pk = ev["t"], ev["peak_t"]
        trig = "none"
        txt = min(texts, key=lambda e: abs(tv(e) - t_on), default=None)
        c = nearest(cut_t, t_pk if ev["type"] in ("riser", "whoosh") else t_on)
        if txt is not None and abs(tv(txt) - t_on) <= 0.15:
            trig = f"text pop: {txt['text'][:30]}"
        elif c is not None and abs(c - (t_pk if ev["type"] in ("riser", "whoosh") else t_on)) <= 0.3:
            ct = next(x for x in cuts if x["t"] == c)
            trig = f"cut ({ct['type']})"
        elif txt is not None and abs(tv(txt) - t_on) <= 0.35:
            trig = f"text: {txt['text'][:30]}"
        elif any(0 <= t_on - p <= 0.5 for p in pauses_end) or any(abs(b - t_on) <= 0.4 for b in big_text):
            trig = "reveal (after a pause / big text)"
        ev["trigger"] = trig
    tcount = Counter((e["type"], e["trigger"].split(":")[0].split(" (")[0]) for e in sfx)
    cuts_with_sfx = sum(1 for c in cuts if any(abs(c["t"] - (e["peak_t"] if e["type"] in ("riser", "whoosh") else e["t"])) <= 0.3 for e in sfx))
    text_with_sfx = sum(1 for e in texts if any(abs(tv(e) - s_["t"]) <= 0.35 for s_ in sfx))
    S["sfx_triggers"] = {f"{k[0]} <- {k[1]}": v for k, v in tcount.most_common()}
    S["sfx_on_cuts_pct"] = round(100 * cuts_with_sfx / max(1, len(cuts)), 1)
    S["sfx_on_text_pct"] = round(100 * text_with_sfx / max(1, len(texts)), 1)
    md.append(f"\n## SFX ({len(sfx)} events; {S['sfx_on_cuts_pct']}% of cuts and {S['sfx_on_text_pct']}% of text events carry one)\n")
    md.append(f"Calibration: {json.dumps(S.get('sfx_calibration'))}\n")
    md.append("| Type <- trigger | Count |\n|---|---|")
    for k, v in S["sfx_triggers"].items():
        md.append(f"| {k} | {v} |")
    md.append("\n| Time | Type | Dur | Peak dBFS | Above bed | Trigger |\n|---|---|---|---|---|---|")
    for e in sfx:
        md.append(f"| {ts(e['t'])} | {e['type']}{' (on the music beat)' if e.get('on_music_beat') else ''} | {e['dur']} | {e['peak_dbfs']} | "
                  f"{e['above_bed_db']} | {e['trigger']} |")

    # ---- music
    md.append(f"\n## Music: {A.get('music_distinct_tracks')} distinct tracks\n")
    md.append("| Start | End | Track | Tempo (clarity) | Key | Centroid | Level speech / pauses (LUFS) | Fade in/out | Mood hint |\n|---|---|---|---|---|---|---|---|---|")
    for m in A.get("music_segments", []):
        if not m["music"]:
            md.append(f"| {ts(m['start'])} | {ts(m['end'])} | - | no music | | | | | |")
            continue
        md.append(f"| {ts(m['start'])} | {ts(m['end'])} | T{m['track']} | {m['tempo_bpm']} ({m['pulse_clarity']}) | {m['key']} | {m['centroid_hz']} | "
                  f"{m['lufs_under_speech']} / {m['lufs_in_pauses']} | {m['fade_in_s']} / {m['fade_out_s']} | {m['mood_hint']} |")
    md.append(f"\nLevels: {json.dumps({k: v for k, v in lv.items() if k != 'per_minute'})}")
    md.append(f"\nDucking: {json.dumps({k: v for k, v in dk.items() if not k.startswith('curve')})}")
    for k in ("curve_after_speech_ends", "curve_after_speech_resumes"):
        if k in dk:
            md.append(f"- {k}: " + " ".join(f"{t:+.1f}s:{v:+.1f}" for t, v in dk[k]))
    md.append("\nSwells:")
    for s_ in A.get("swells", []):
        near_c = nearest(cut_t, s_["peak"])
        near_t = min(texts, key=lambda e: abs(tv(e) - s_["peak"]), default=None)
        ctx = []
        if near_c is not None and abs(near_c - s_["peak"]) < 1.0:
            ctx.append(f"cut {near_c - s_['peak']:+.1f}s")
        if near_t is not None and abs(tv(near_t) - s_["peak"]) < 1.0:
            ctx.append(f"text '{near_t['text'][:24]}'")
        md.append(f"- {ts(s_['start'])}-{ts(s_['end'])} peak {ts(s_['peak'])} +{s_['rise_db']} dB {'(pause)' if s_['in_pause'] else '(under speech)'} {'; '.join(ctx)}")
    sil = A.get("silences", {})
    md.append(f"\nSilences (mix < -50 dBFS): {[(ts(x['start']), x['dur']) for x in sil.get('mix_below_-50dbfs', [])]}")
    md.append(f"Music drop-outs: {[(ts(x['start']), x['dur'], x['drop_db']) for x in sil.get('music_dropouts', [])]}")
    if lv.get("per_minute"):
        md.append("\n| Minute | Voice | Music under speech | Music in pauses |\n|---|---|---|---|")
        for r in lv["per_minute"]:
            md.append(f"| {r['min']} | {r['voice']} | {r['music_speech']} | {r['music_pause']} |")

    # ---- transitions + shots
    md.append("\n## Transitions\n")
    md.append("| Type | Count | Median frames | Examples |\n|---|---|---|---|")
    groups = {}
    for c in cuts:
        groups.setdefault(c["type"], []).append(c)
    for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        md.append(f"| {k} | {len(v)} | {int(np.median([c.get('frames', 1) for c in v]))} | {', '.join(ts(c['t']) for c in v[:6])} |")
    md.append("\n## Camera moves and content\n")
    mv = Counter()
    for s in shots:
        for part in s["motion"].split(", "):
            mv[re.sub(r" [-\d.]+(%/s|px/s|deg/s)", "", part)] += 1
    md.append("| Move | Shots |\n|---|---|")
    for k, v in mv.most_common():
        md.append(f"| {k} | {v} |")
    zs = [abs(s["zoom_pct_s"]) for s in shots if abs(s["zoom_pct_s"]) >= 0.4]
    ps = [abs(s["pan_px_s"][0]) for s in shots if abs(s["pan_px_s"][0]) >= 8]
    S["moves"] = {"zoom_pct_s_median": round(float(np.median(zs)), 2) if zs else None, "pan_px_s_median": int(np.median(ps)) if ps else None}
    md.append(f"\nZoom speed median {S['moves']['zoom_pct_s_median']} %/s, pan speed median {S['moves']['pan_px_s_median']} px/s (1080p)")
    md.append("\n| Content | Share of runtime | Shots | Median shot |\n|---|---|---|---|")
    for k, v in by_content.most_common():
        ds = [s["dur"] for s in shots if s["content"] == k]
        md.append(f"| {k} | {100 * v / dur:.1f}% | {len(ds)} | {np.median(ds):.1f}s |")

    # ---- pacing
    bins = [0, 1, 2, 3, 4, 6, 8, 12, 20, 1e9]
    hist = np.histogram(L, bins)[0]
    md.append("\n## Pacing\n")
    md.append("| Shot length | " + " | ".join(f"{bins[i]}-{bins[i + 1] if bins[i + 1] < 1e8 else '+'}s" for i in range(len(bins) - 1)) + " |")
    md.append("|---" * len(bins) + "|")
    md.append("| shots | " + " | ".join(str(int(h)) for h in hist) + " |")
    per_min = np.bincount([int(t // 60) for t in cut_t], minlength=int(dur // 60) + 1)
    S["cuts_by_minute"] = per_min.tolist()
    md.append(f"\nCuts per minute, minute by minute: {' · '.join(map(str, per_min))}")
    secs = [float(x) for x in a.sections.split(",") if x] if a.sections else []
    if secs:
        edges = secs + [dur]
        md.append("\n| Section | Start | Length | Shots | Cuts/min | Median shot | Footage % | Still % | Graphic % | WPM |\n|---|---|---|---|---|---|---|---|---|---|")
        for i, (s0, s1) in enumerate(zip(edges, edges[1:])):
            ss = [s for s in shots if s0 <= s["start"] < s1]
            ov = lambda s: max(0.0, min(s1, s["end"]) - max(s0, s["start"]))
            sh = lambda key: 100 * sum(ov(s) for s in shots if key in s["content"]) / max(1e-6, s1 - s0)
            nw = sum(1 for w in words if s0 <= w["start"] < s1)
            md.append(f"| {i + 1} | {ts(s0)} | {s1 - s0:.0f}s | {len(ss)} | {len(ss) / (s1 - s0) * 60:.1f} | "
                      f"{np.median([s['dur'] for s in ss]) if ss else 0:.1f} | {sh('footage'):.0f} | {sh('still'):.0f} | {sh('graphic'):.0f} | "
                      f"{nw / (s1 - s0) * 60:.0f} |")
    # sync of cuts with narration
    if words:
        off = [c - nearest(wstarts, c) for c in cut_t]
        in_pause = sum(1 for c in cut_t if not any(s0 <= c <= s1 for s0, s1 in segs))
        S["cut_sync"] = {"within_0.2s_of_word_start_pct": round(100 * np.mean([abs(o) <= 0.2 for o in off]), 1),
                         "median_abs_offset_s": round(float(np.median(np.abs(off))), 2), "in_pause_pct": round(100 * in_pause / max(1, len(cut_t)), 1)}
        md.append(f"\nCut sync: {S['cut_sync']}")
        # numbers on screen vs when they are spoken
        delays = []
        for e in texts:
            nums = re.findall(r"\d+", e["text"].replace(",", ""))
            if not nums:
                continue
            for w in words:
                if nums[0] in w["w"].replace(",", "") and abs(w["start"] - tv(e)) < 4:
                    delays.append(tv(e) - w["start"])
                    break
        if delays:
            S["number_text_delay_s"] = {"n": len(delays), "median": round(float(np.median(delays)), 2)}
            md.append(f"Numbers on screen vs spoken: {S['number_text_delay_s']} (positive = text after the word)")

    # ---- text styles
    md.append("\n## Text styles\n")
    md.append("| Style | Script | Height px | Colour | Position | Plate | Count | Median on screen | Entries | Exits | Examples |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for s in T.get("styles", []):
        md.append(f"| {s['style']} | {s['script']} | {s['height_px']} | {s['colour']} | {s['position']} | {s['plate']} | {s['count']} | "
                  f"{s['median_on_screen_s']} | {json.dumps(s['entries'])} | {json.dumps(s['exits'])} | "
                  f"{'; '.join(f'{ts(t)} {x}' for t, x in s['examples'][:3])} |")
    ctr = [e for e in texts if e.get("counter")]
    if ctr:
        md.append("\nCounters: " + "; ".join(f"{ts(e['t_first'])} {e['counter']['from']} -> {e['counter']['to']}" for e in ctr))

    # ---- voice
    md.append("\n## Voice\n")
    md.append(json.dumps({k: v for k, v in vo.items() if k != "words_per_minute_by_minute"}, ensure_ascii=False))
    if vo.get("words_per_minute_by_minute"):
        md.append(f"\nWords per minute, minute by minute: {' · '.join(map(str, vo['words_per_minute_by_minute']))}")
    if Wd.get("segments"):
        text_all = [(s_["start"], s_["text"]) for s_ in Wd["segments"]]
        md.append("\n| Signpost | Count | First times |\n|---|---|---|")
        S["signposts"] = {}
        for name, rx in SIGNPOSTS.items():
            hits = [t for t, x in text_all for _ in re.finditer(rx, x, re.I)]
            S["signposts"][name] = len(hits)
            md.append(f"| {name} | {len(hits)} | {', '.join(ts(t) for t in hits[:6])} |")
        q = sum(1 for _, x in text_all if x.strip().endswith("?"))
        md.append(f"\nSentences ending in '?': {q} of {len(text_all)} segments")

    # ---- intro timeline
    I = a.intro
    ev = []
    for s in shots:
        if s["start"] < I:
            ev.append((s["start"], f"SHOT #{s['i']} {s['dur']:.1f}s {s['content']}; {s['motion']}; in: {s['in_transition']}"))
    for e in texts:
        if tv(e) < I:
            ev.append((tv(e), f"TEXT [{e['position']}, {e['height_px']}px, {e.get('colour', '?')}{', plate' if e.get('plate') else ''}] "
                              f"'{e['text']}' entry={e['entry'].get('kind', '?')} exit={e['exit'].get('kind', '?')} {e.get('on_screen_s', '?')}s"))
    for e in sfx:
        if e["t"] < I:
            ev.append((e["t"], f"SFX {e['type']} {e['dur']}s {e['peak_dbfs']} dBFS ({e['trigger']})"))
    for m in A.get("music_segments", []):
        if m["start"] < I:
            ev.append((m["start"], f"MUSIC {'T' + str(m['track']) + ' ' + m['mood_hint'] if m['music'] else 'none'}"))
    for s_ in A.get("swells", []):
        if s_["peak"] < I:
            ev.append((s_["peak"], f"MUSIC SWELL +{s_['rise_db']} dB"))
    for s_ in Wd.get("segments", []):
        if s_["start"] < I:
            ev.append((s_["start"], f"VOICE \"{s_['text']}\""))
    topic = [k.strip().lower() for k in a.topic.split(",") if k.strip()]
    first_topic = next((w for w in words if any(k in w["w"].lower() for k in topic)), None) if topic else None
    title_words = set(re.findall(r"\w+", (meta or {}).get("title", "").lower())) - {"what", "if", "we", "on", "the", "ep", "2"}
    title_cands = [e for e in texts if tv(e) < 150 and (e["height_px"] >= 80 or
                                                         len(title_words & set(re.findall(r"\w+", e["text"].lower()))) >= 2)]
    S["intro"] = {"narration_start_s": vo.get("narration_start_s"),
                  "topic_first_named_s": first_topic["start"] if first_topic else None,
                  "topic_word": first_topic["w"] if first_topic else None,
                  "title_card_candidates": [[tv(e), e["text"], e["height_px"]] for e in title_cands[:6]],
                  "shots_in_intro": sum(1 for s in shots if s["start"] < I),
                  "cuts_per_min_intro": round(sum(1 for c in cut_t if c < I) / I * 60, 1)}
    md.append(f"\n## Intro (0-{I:.0f} s)\n")
    md.append(json.dumps(S["intro"], ensure_ascii=False))
    md.append("")
    for t, x in sorted(ev):
        md.append(f"- {ts(t)} {x}")

    open(f"{an}/report.md", "w").write("\n".join(md) + "\n")
    json.dump(S, open(f"{an}/summary.json", "w"), ensure_ascii=False, indent=1)
    print("\n".join(md[:40]))

    if a.no_strips or not os.path.exists(video):
        return
    sq = f"{an}/sequences"
    os.makedirs(sq, exist_ok=True)
    jobs = []
    for k, v in groups.items():
        for c in v[:3 if k != "cut" else 2]:
            jobs.append((c["t"] - 1.0, 2.0, f"transition_{k.split(' (')[0].replace(' ', '-').replace('/', '-')}_{c['t']:.1f}", f"{k} at {ts(c['t'])}"))
    for s in T.get("styles", [])[:12]:
        evs = [e for e in texts if e.get("style") == s["style"]][:2]
        for e in evs:
            t0 = tv(e)
            jobs.append((t0 - 0.5, 2.0, f"text-in_s{s['style']:02d}_{t0:.1f}", f"style {s['style']} entry {e['entry'].get('kind')} '{e['text'][:30]}'"))
            t1 = e["exit"].get("t_gone", e["t_last"])
            jobs.append((t1 - 1.5, 2.0, f"text-out_s{s['style']:02d}_{t1:.1f}", f"style {s['style']} exit {e['exit'].get('kind')}"))
    seen = Counter()
    for s in shots:
        key = (s["content"], s["motion"].split(" ")[0])
        if seen[key] < 2 and s["dur"] >= 2.2:
            seen[key] += 1
            m = (s["start"] + s["end"]) / 2
            jobs.append((m - 1.0, 2.0, f"shot_{key[0].split(' ')[0].replace('/', '-')}_{key[1]}_{s['start']:.1f}",
                         f"shot #{s['i']} {s['content']} / {s['motion']}"))
    for typ in ("boom", "hit", "riser", "glitch", "sub drop", "whoosh", "pop/click"):
        for e in [e for e in sfx if e["type"] == typ][:2]:
            jobs.append((e["t"] - 1.0, 2.0, f"sfx_{typ.replace('/', '-').replace(' ', '-')}_{e['t']:.1f}", f"SFX {typ} at {ts(e['t'])}: {e['trigger']}"))
    for t in V.get("flash_frames", [])[:4]:
        jobs.append((t - 1.0, 2.0, f"flashframe_{t:.1f}", f"flash frame {ts(t)}"))
    jobs.append((0, min(I, dur), "intro_1fps", "intro, 1 frame per second"))
    for t0, d, name, label in jobs:
        out = f"{sq}/{name}.jpg"
        if os.path.exists(out):
            continue
        if name == "intro_1fps":
            strip(video, t0, d, out, label, fps=1, cols=10, w=256)
        else:
            strip(video, t0, d, out, label)
    print(len(jobs), "strips ->", sq)


if __name__ == "__main__":
    main()
