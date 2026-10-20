"""On-screen text of a reference video: every text event, its style and how it enters and leaves.

  python text_track.py <video.mp4> <an_dir> [--step 0.5] [--langs hi,en]

OCR (EasyOCR) every --step seconds on 720p frames; detections are linked into events across samples. For each
event, frames at 10 fps around its first and last sample give the exact appearance/disappearance time and the
animation: instant, fade, scale pop (with overshoot), slide (direction), wipe/typewriter, blur-in. Also: box
size and position at 1080p scale, text colour, solid plate behind it, dark outline/shadow, script
(Devanagari/Latin), numbers that change in place (counters). Events are grouped into styles.
Writes <an_dir>/text_events.json and crops of each style's first events: <an_dir>/text/style_NN.jpg.
"""
import argparse, difflib, json, os, re, sys
import numpy as np, cv2

sys.path.insert(0, os.path.dirname(__file__))
from visual_stats import frames, probe  # noqa: E402

FW, FH = 1280, 720   # OCR frame size; set from the video in main() (never upscaled: that only costs time)
S1080 = 1080 / FH


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0


def numeric(s):
    """A number, optionally with a short unit ('150,000,000 KM', '5,500 °C', '93%')."""
    return any(ch.isdigit() for ch in s) and sum(ch.isalpha() for ch in s) <= 4


def value(s):
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def similar(a, b):
    """Text similarity that also links a typewriter's growing prefix to the full line."""
    r = difflib.SequenceMatcher(None, a, b).ratio()
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 2:
        r = max(r, difflib.SequenceMatcher(None, short, long_[:len(short)]).ratio())
    return r


def script_of(s):
    dev = sum(1 for ch in s if "ऀ" <= ch <= "ॿ")
    lat = sum(1 for ch in s if ch.isascii() and ch.isalpha())
    return "devanagari" if dev > lat else "latin" if lat else "digits"


def colour_name(bgr):
    hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0, 0]
    h, s, v = int(hsv[0]) * 2, int(hsv[1]), int(hsv[2])
    if v < 60:
        return "black"
    if s < 45:
        return "white" if v > 190 else "grey"
    for lim, nm in ((15, "red"), (40, "orange"), (68, "yellow"), (160, "green"), (200, "cyan"), (255, "blue"), (300, "purple"), (340, "pink"), (361, "red")):
        if h < lim:
            return nm
    return "?"


def position(box):
    cx, cy = (box[0] + box[2]) / 2 / 1920, (box[1] + box[3]) / 2 / 1080
    col = "left" if cx < 0.36 else "right" if cx > 0.64 else "centre"
    row = "top" if cy < 0.3 else "lower third" if cy > 0.7 else "middle"
    return f"{row} {col}"


def ocr_pass(video, reader, step, dur):
    dets = []
    for i, fr in enumerate(frames(video, 1 / step, FW, FH)):
        t = i * step
        for pts, txt, conf in reader.readtext(fr, detail=1, paragraph=False):
            txt = txt.strip()
            if conf < 0.3 or not txt or not any(ch.isalnum() for ch in txt):
                continue
            p = np.array(pts)
            box = [float(p[:, 0].min()), float(p[:, 1].min()), float(p[:, 0].max()), float(p[:, 1].max())]
            if box[3] - box[1] < 10:
                continue
            dets.append({"t": round(t, 2), "box": box, "text": txt, "conf": round(float(conf), 2)})
        if i % 60 == 0:
            print(f"  ocr {t:.0f}/{dur:.0f}s", flush=True)
    return dets


def link(dets, step):
    tracks = []
    for d in sorted(dets, key=lambda x: x["t"]):
        best, bs = None, 0
        for tr in tracks:
            last = tr[-1]
            if d["t"] - last["t"] > 2.5 * step or d["t"] == last["t"]:
                continue
            ov = iou(d["box"], last["box"])
            if numeric(d["text"]) and numeric(last["text"]):
                # a counter's box grows with its digits: same line, centres close
                h = max(d["box"][3] - d["box"][1], last["box"][3] - last["box"][1])
                same_line = abs((d["box"][1] + d["box"][3]) - (last["box"][1] + last["box"][3])) / 2 < 0.5 * h
                close = abs((d["box"][0] + d["box"][2]) - (last["box"][0] + last["box"][2])) / 2 < 0.5 * max(d["box"][2] - d["box"][0], last["box"][2] - last["box"][0])
                ov, sim = (max(ov, 0.5), 1.0) if same_line and close else (ov, 0.0)
            else:
                sim = similar(d["text"], last["text"])
            sc = ov + sim
            if ov > 0.35 and sim >= 0.5 and sc > bs:
                best, bs = tr, sc
        if best is None:
            tracks.append([d])
        else:
            best.append(d)
    return tracks


def crop(fr, box, pad, padx=None):
    x0, y0, x1, y1 = [int(v / S1080) for v in box]
    h = y1 - y0
    p, px = int(h * pad), int(h * pad if padx is None else padx)
    return fr[max(0, y0 - p):y1 + p, max(0, x0 - px):x1 + px], (max(0, x0 - px), max(0, y0 - p))


def contrast(region, ref, mask):
    """Text-vs-surroundings contrast of a frame region relative to the settled text (0 = absent, 1 = fully in)."""
    den = ref[mask].mean() - ref[~mask].mean()
    return float((region[mask].mean() - region[~mask].mean()) / den) if abs(den) > 1e-6 else 0.0


def animation(video, box, t_ref, t_edge, entering):
    """Frames at 10 fps across the entry (or exit) -> exact time and the kind of animation."""
    # entering: t_edge = first OCR sample with the text (it may still be mid-animation); exiting: the last one
    t0 = t_edge - 1.0 if entering else t_edge - 0.3
    seq = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames(video, 10, FW, FH, ss=max(0, t0), dur=2.2 if entering else 2.0)]
    t0 = max(0, t0)
    ref_fr = next(frames(video, None, FW, FH, ss=t_ref, dur=0.1), None)
    if not seq or ref_fr is None:
        return {}
    ref, (rx, ry) = crop(cv2.cvtColor(ref_fr, cv2.COLOR_BGR2GRAY).astype(np.float32), box, 0.0)
    if ref.size == 0 or ref.std() < 5:
        return {}
    mask = np.abs(ref - np.median(ref)) > max(35, 0.35 * (np.percentile(ref, 99) - np.percentile(ref, 1)))
    if mask.sum() < 20 or (~mask).sum() < 20 or abs(ref[mask].mean() - ref[~mask].mean()) < 15:
        return {}
    bh, bw = ref.shape
    tpl0 = ref.astype(np.uint8)
    vis, best, colfrac = [], [], []
    mcols = mask.sum(0) >= 2
    for g in seq:
        region = g[ry:ry + bh, rx:rx + bw]
        if region.shape != ref.shape:
            vis.append(0.0); best.append((-1, 1.0, 0, 0)); colfrac.append(None)
            continue
        vis.append(contrast(region, ref, mask))
        win, (wx, wy) = crop(g, box, 1.2, padx=max(1.2 * bh, 0.8 * bw))
        win = win.astype(np.uint8)
        bb = (-1, 1.0, 0, 0)
        for s in (0.5, 0.65, 0.8, 0.9, 1.0, 1.1, 1.25):
            tpl = cv2.resize(tpl0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            if tpl.shape[0] >= win.shape[0] or tpl.shape[1] >= win.shape[1] or tpl.shape[0] < 6 or tpl.std() < 3:
                continue
            r = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            if mx > bb[0]:
                bb = (mx, s, wx + loc[0] + tpl.shape[1] / 2 - (rx + bw / 2), wy + loc[1] + tpl.shape[0] / 2 - (ry + bh / 2))
        best.append(bb)
        cm = []
        for c in np.where(mcols)[0]:
            m = mask[:, c]
            dn = ref[m, c].mean() - ref[~m, c].mean() if (~m).any() else 0
            cm.append((region[m, c].mean() - region[~m, c].mean()) / dn > 0.6 if abs(dn) > 10 else False)
        colfrac.append(np.array(cm))
    vis = np.array(vis)
    # visible: the text's contrast is up, a copy of it is found (moved / scaled), or some of its columns are in
    # place (a wipe or typewriter shows a few full-contrast letters first)
    present = np.array([v > 0.15 or b[0] > 0.6 or (c is not None and len(c) and c.mean() > 0.08)
                        for v, b, c in zip(vis, best, colfrac)])
    settled = np.array([v > 0.85 and abs(b[1] - 1) < 0.06 and abs(b[2]) < 0.2 * bh + 3 for v, b in zip(vis, best)])
    times = t0 + np.arange(len(seq)) / 10
    out = {}
    if entering:
        on = np.where(settled)[0]
        if not len(on):
            return {}
        full = on[0]
        off = np.where(~present[:full])[0]
        first = off[-1] + 1 if len(off) else 0
        ramp = list(range(first, full + 1))
        out["t_visible"] = round(float(times[first]), 2)
        out["t_settled"] = round(float(times[full]), 2)
    else:
        gone = np.where(~present)[0]
        gone = gone[gone > 0]
        if not len(gone):
            return {}
        last = gone[0]
        on = np.where(settled[:last])[0]
        start = on[-1] if len(on) else 0
        ramp = list(range(start, last + 1))
        out["t_start"] = round(float(times[start]), 2)
        out["t_gone"] = round(float(times[last]), 2)
    n = len(ramp) - 1  # frames between "first seen" and "settled" (or "leaving" and "gone")
    out["frames"] = n
    if n <= 1:
        out["kind"] = "cut"
        return out
    inner = [i for i in ramp if best[i][0] > 0.55]
    scales = [best[i][1] for i in inner]
    if len(scales) >= 2 and max(scales) - min(scales) >= 0.2:
        over = any(s > 1.05 for s in scales)
        grow = scales[-1] > scales[0]
        out["kind"] = ("scale pop" + (" with overshoot" if over else "") if entering else "scale out") + (" (grows)" if grow else " (shrinks)")
        out["scales"] = [round(s, 2) for s in scales]
        return out
    shifts = [(best[i][2], best[i][3]) for i in inner]
    if len(shifts) >= 2:
        dx, dy = shifts[-1][0] - shifts[0][0], shifts[-1][1] - shifts[0][1]
        if max(abs(dx), abs(dy)) > 0.35 * bh:
            if entering:
                came = ("left" if dx > 0 else "right") if abs(dx) > abs(dy) else ("above" if dy > 0 else "below")
                out["kind"] = f"slide in from {came}"
            else:
                went = ("right" if dx > 0 else "left") if abs(dx) > abs(dy) else ("down" if dy > 0 else "up")
                out["kind"] = f"slide out {went}"
            out["travel_px_1080p"] = int(max(abs(dx), abs(dy)) * S1080)
            return out
    # column-wise reveal (wipe / typewriter): the matched columns' centre moves across the text
    cen = [(np.mean(np.where(colfrac[i])[0]) / len(colfrac[i]), colfrac[i].mean()) for i in ramp
           if colfrac[i] is not None and len(colfrac[i]) and 0.1 < colfrac[i].mean() < 0.9]
    if len(cen) >= 2 and abs(cen[-1][0] - cen[0][0]) > 0.1 and cen[-1][1] > cen[0][1]:
        d_ = "L->R" if cen[-1][0] > cen[0][0] else "R->L"
        out["kind"] = f"wipe/typewriter {d_}" if entering else f"wipe out {d_}"
        return out
    out["kind"] = "fade " + ("in" if entering else "out")
    out["dur_s"] = round(n / 10, 1)
    return out


def look(video, box, t):
    """Colour of the text, a plate behind it, a dark outline / shadow."""
    fr = next(frames(video, None, FW, FH, ss=t, dur=0.1), None)
    if fr is None:
        return {}
    inner, _ = crop(fr, box, 0.0)
    outer, _ = crop(fr, box, 0.45)
    if inner.size == 0 or outer.size == 0:
        return {}
    px = inner.reshape(-1, 3).astype(np.float32)
    ring = np.concatenate([outer[:4].reshape(-1, 3), outer[-4:].reshape(-1, 3), outer[:, :4].reshape(-1, 3), outer[:, -4:].reshape(-1, 3)]).astype(np.float32)
    bg_out = np.median(ring, 0)
    _, lab, cen = cv2.kmeans(px, 2, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3, cv2.KMEANS_PP_CENTERS)
    lab = lab.ravel()
    sizes = np.bincount(lab, minlength=2)
    # text = the cluster farther from the surroundings, unless it fills most of the box (then it is a plate)
    far = int(np.argmax(np.linalg.norm(cen - bg_out, axis=1)))
    near = 1 - far
    out = {}
    plate_like = sizes[far] > 0.62 * len(lab) and np.linalg.norm(cen[far] - bg_out) > 45
    if plate_like:  # big uniform block different from the frame: a plate; text is the other cluster
        out["plate"] = colour_name(cen[far]) + f" rgb{tuple(int(c) for c in cen[far][::-1])}"
        tc = cen[near]
    else:
        tc = cen[far]
        bgi = px[lab == near]
        if len(bgi) and bgi.std(0).mean() < 14 and np.linalg.norm(cen[near] - bg_out) > 40:
            out["plate"] = colour_name(cen[near]) + f" rgb{tuple(int(c) for c in cen[near][::-1])}"
    out["colour"] = colour_name(tc)
    out["rgb"] = [int(c) for c in tc[::-1]]
    g = cv2.cvtColor(inner, cv2.COLOR_BGR2GRAY)
    tm = (np.linalg.norm(inner.astype(np.float32) - tc, axis=2) < 50).astype(np.uint8)
    edge = cv2.dilate(tm, np.ones((5, 5), np.uint8)) - tm
    if edge.sum() > 20 and "plate" not in out:
        el, bl = g[edge > 0].mean(), np.mean(cv2.cvtColor(bg_out[None, None].astype(np.uint8), cv2.COLOR_BGR2GRAY))
        if g[tm > 0].mean() > 150 and el < min(bl, 120) - 25:
            out["outline_or_shadow"] = "dark"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("an")
    ap.add_argument("--step", type=float, default=1.0)
    ap.add_argument("--langs", default="hi,en")
    a = ap.parse_args()
    import torch, easyocr
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    reader = easyocr.Reader(a.langs.split(","), gpu=False, verbose=False)
    global FW, FH, S1080
    dur, _, vw, vh = probe(a.video)
    if vh < FH:
        FW, FH = vw - vw % 2, vh - vh % 2
        S1080 = 1080 / FH
    cache = f"{a.an}/ocr_raw.json"
    if os.path.exists(cache):
        dets = json.load(open(cache))
    else:
        dets = ocr_pass(a.video, reader, a.step, dur)
        json.dump(dets, open(cache, "w"), ensure_ascii=False)
    events = []
    for tr in link(dets, a.step):
        txt = max(tr, key=lambda d: d["conf"])["text"]
        box = np.median([d["box"] for d in tr], 0)
        box = [round(float(v * S1080)) for v in box]
        e = {"t_first": tr[0]["t"], "t_last": tr[-1]["t"], "text": txt, "box_1080p": box, "height_px": box[3] - box[1],
             "position": position(box), "script": script_of(txt), "samples": len(tr), "conf": max(d["conf"] for d in tr)}
        vals = [value(d["text"]) for d in tr if numeric(d["text"])]
        vals = [v for v in vals if v is not None]
        if len(set(vals)) >= 3:  # a number that changes in place, steadily one way and by a lot: a counter
            steps = np.diff(vals)
            mono = max((steps >= 0).mean(), (steps <= 0).mean())
            if mono >= 0.8 and max(vals) >= 1.5 * max(1, min(vals)) and max(vals) - min(vals) >= 10:
                e["counter"] = {"from": tr[0]["text"], "to": tr[-1]["text"], "distinct_values": len(set(vals)),
                                "duration_s": round(tr[-1]["t"] - tr[0]["t"], 1)}
        events.append(e)
    events.sort(key=lambda e: e["t_first"])
    # merge words of one line that EasyOCR split (same sample times, same baseline, adjacent)
    merged = []
    for e in events:
        m = next((p for p in merged[-6:] if abs(p["t_first"] - e["t_first"]) <= a.step and abs(p["t_last"] - e["t_last"]) <= a.step
                  and abs(p["box_1080p"][1] - e["box_1080p"][1]) < 0.4 * e["height_px"] and abs(p["height_px"] - e["height_px"]) < 0.45 * max(p["height_px"], e["height_px"])
                  and 0 <= e["box_1080p"][0] - p["box_1080p"][2] < 1.5 * e["height_px"]), None)
        if m:
            m["text"] += " " + e["text"]
            m["box_1080p"][2] = max(m["box_1080p"][2], e["box_1080p"][2])
            m["box_1080p"][3] = max(m["box_1080p"][3], e["box_1080p"][3])
            m["position"] = position(m["box_1080p"])
            continue
        merged.append(e)
    # one-character reads are mostly round or straight shapes in the picture (a planet read as "0"): drop them
    events = [e for e in merged if (e["samples"] >= 2 or e["height_px"] >= 40) and len(e["text"].replace(" ", "")) >= 2]
    for k, e in enumerate(events):
        tref = min(e["t_first"] + a.step, e["t_last"])
        e["entry"] = animation(a.video, e["box_1080p"], tref, e["t_first"], True)
        e["exit"] = animation(a.video, e["box_1080p"], max(e["t_last"] - a.step, e["t_first"]), e["t_last"], False)
        e.update(look(a.video, e["box_1080p"], tref))
        t_on = e["entry"].get("t_visible", e["t_first"])
        t_off = e["exit"].get("t_gone", e["t_last"] + a.step / 2)
        e["on_screen_s"] = round(t_off - t_on, 2)
        if k % 20 == 0:
            print(f"  text events {k}/{len(events)}", flush=True)
    # styles
    styles = {}
    for e in events:
        key = (e["script"], int(round(e["height_px"] / 20) * 20), e.get("colour", "?"), e["position"], "plate" if e.get("plate") else "")
        styles.setdefault(key, []).append(e)
    out_styles = []
    os.makedirs(f"{a.an}/text", exist_ok=True)
    for sid, (key, evs) in enumerate(sorted(styles.items(), key=lambda kv: -len(kv[1]))):
        for e in evs:
            e["style"] = sid
        ent = {}
        for e in evs:
            ent[e["entry"].get("kind", "?")] = ent.get(e["entry"].get("kind", "?"), 0) + 1
        ext = {}
        for e in evs:
            ext[e["exit"].get("kind", "?")] = ext.get(e["exit"].get("kind", "?"), 0) + 1
        out_styles.append({"style": sid, "script": key[0], "height_px": key[1], "colour": key[2], "position": key[3], "plate": key[4],
                           "count": len(evs), "median_on_screen_s": round(float(np.median([e["on_screen_s"] for e in evs])), 2),
                           "entries": ent, "exits": ext, "examples": [[e["t_first"], e["text"][:40]] for e in evs[:5]]})
        tiles = []
        for e in evs[:6]:
            fr = next(frames(a.video, None, FW, FH, ss=min(e["t_first"] + a.step, e["t_last"]), dur=0.1), None)
            if fr is None:
                continue
            c, _ = crop(fr, e["box_1080p"], 0.6)
            if c.size:
                c = cv2.resize(c, (int(c.shape[1] * 120 / c.shape[0]), 120))[:, :900]
                tiles.append(np.pad(c, ((4, 4), (0, 904 - c.shape[1]), (0, 0))))
        if tiles:
            cv2.imwrite(f"{a.an}/text/style_{sid:02d}.jpg", np.vstack(tiles))
    json.dump({"events": events, "styles": out_styles}, open(f"{a.an}/text_events.json", "w"), ensure_ascii=False, indent=1)
    print(len(events), "text events,", len(out_styles), "styles")
    for s in out_styles[:15]:
        print(s)


if __name__ == "__main__":
    main()
