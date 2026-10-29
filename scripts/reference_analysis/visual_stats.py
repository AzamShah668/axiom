"""Cuts, transitions, camera moves, shot types and grade of a reference video.

  python visual_stats.py <video.mp4> <an_dir>

Reads the PySceneDetect lists in <an_dir>/scenes/ (analyze_video.sh) when present, writes
<an_dir>/visual.json and labelled shot sheets <an_dir>/shots/shots_NN.jpg.

Per frame (10 fps, 240x135 for motion): optical flow fitted with a similarity transform (zoom, rotation, pan),
the residual after motion compensation (~0 for a still image moved by a virtual camera), separate fits for the
centre and the border (different motion = 2.5D parallax layers), sharpness, R/B channel offset (glitch), luma
and Lab colour statistics, flat-area and black-area fractions (graphics), noise floor (grain).
Per cut: the transition type from the full-frame-rate window around it: hard cut, dissolve, flash, light leak,
dip to black, whip/slide (direction), zoom/punch, glitch.
Per shot: duration, camera move (static, push-in, pull-out, pan/tilt direction, parallax, shake), content
(still + move, graphic, footage/animation) and its colour.
"""
import csv, glob, json, math, os, subprocess, sys
import numpy as np, cv2

FPS = 10
W2, H2 = 240, 135          # motion analysis size
SC = 1920 / W2             # px at 240 wide -> px at 1080p


def probe(path):
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate:format=duration", "-of", "json", path],
                                  capture_output=True, text=True).stdout)
    s = p["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return float(p["format"]["duration"]), float(a) / float(b), s["width"], s["height"]


def frames(path, fps, w, h, ss=None, dur=None):
    """Decoded frames (BGR). With fps, frame k is the source frame at ss + k / fps exactly: ffmpeg's fps filter
    otherwise hands out frames up to half an output interval late (0.25 s at 2 fps)."""
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{ss:.3f}"] if ss else []) + ["-i", path] + \
          (["-t", f"{dur:.3f}"] if dur else []) + ["-vf", f"fps={fps}:round=up,scale={w}:{h}:flags=area" if fps else f"scale={w}:{h}:flags=area",
                                                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    finally:  # the caller may stop early (next(...)): end ffmpeg quietly instead of a broken pipe
        if p.poll() is None:
            p.kill()
        p.stdout.close()
        p.wait()


GRID = None


def sim_fit(flow, mask=None):
    """Similarity transform fitted to a dense flow field -> (M, median residual px, n points)."""
    global GRID
    if GRID is None:
        ys, xs = np.mgrid[6:H2 - 6:5, 6:W2 - 6:5]
        GRID = np.stack([xs.ravel(), ys.ravel()], 1).astype(np.float32)
    pts = GRID if mask is None else GRID[mask(GRID)]
    d = flow[pts[:, 1].astype(int), pts[:, 0].astype(int)]
    dst = pts + d
    M, inl = cv2.estimateAffinePartial2D(pts, dst, method=cv2.RANSAC, ransacReprojThreshold=0.7, maxIters=200)
    if M is None:
        return None, 99.0, len(pts)
    pr = pts @ M[:, :2].T + M[:, 2]
    return M, float(np.median(np.linalg.norm(pr - dst, axis=1))), len(pts)


def centre_move(M):
    c = np.array([W2 / 2, H2 / 2])
    m = M[:, :2] @ c + M[:, 2] - c
    return float(m[0]), float(m[1]), float(math.hypot(M[0, 0], M[1, 0])), float(math.degrees(math.atan2(M[1, 0], M[0, 0])))


def hs_hist(sm):
    h = cv2.calcHist([cv2.cvtColor(sm, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256]).ravel()
    return h / (h.sum() + 1e-9)


INNER = lambda p: (p[:, 0] > W2 * .3) & (p[:, 0] < W2 * .7) & (p[:, 1] > H2 * .3) & (p[:, 1] < H2 * .7)
OUTER = lambda p: (p[:, 0] < W2 * .2) | (p[:, 0] > W2 * .8) | (p[:, 1] < H2 * .2) | (p[:, 1] > H2 * .8)


def frame_stats(fr):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
    L = lab[:, 0]
    sh, hi = L < 64, L > 191
    p = np.percentile(g, [1, 5, 50, 95, 99])
    blk = g[:H2 // 8 * 8, :W2 // 8 * 8].reshape(H2 // 8, 8, W2 // 8, 8).std((1, 3))
    hp = g.astype(np.float32) - cv2.GaussianBlur(g.astype(np.float32), (0, 0), 1.0)
    tex = cv2.GaussianBlur(g.astype(np.float32), (0, 0), 3)
    tex_std = np.abs(cv2.Laplacian(tex, cv2.CV_32F))
    calm = (tex_std < 1.0) & (g > 30) & (g < 220)
    return {
        "luma": float(g.mean()), "p1": float(p[0]), "p5": float(p[1]), "p50": float(p[2]), "p95": float(p[3]), "p99": float(p[4]),
        "sat": float(hsv[..., 1].mean()), "a": float(lab[:, 1].mean() - 128), "b": float(lab[:, 2].mean() - 128),
        "sh_a": float(lab[sh, 1].mean() - 128) if sh.sum() > 50 else 0.0, "sh_b": float(lab[sh, 2].mean() - 128) if sh.sum() > 50 else 0.0,
        "hi_a": float(lab[hi, 1].mean() - 128) if hi.sum() > 50 else 0.0, "hi_b": float(lab[hi, 2].mean() - 128) if hi.sum() > 50 else 0.0,
        "flat": float((blk < 2.5).mean()), "black": float((g < 14).mean()),
        "noise": float(np.median(np.abs(hp[calm]))) if calm.sum() > 200 else -1.0,
        "rb": float(fr[..., 2].mean() - fr[..., 0].mean()),
    }


def main_pass(video, dur):
    keys = None
    rows, thumbs, hists = [], [], []
    prev = None
    for i, fr in enumerate(frames(video, FPS, W2 * 2, H2 * 2)):
        sm = cv2.resize(fr, (W2, H2), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
        st = frame_stats(sm)
        st["sharp"] = float(cv2.Laplacian(g, cv2.CV_64F).var())
        st["rgb_split"] = rgb_split(sm, 6)
        st.update({"diff": 0.0, "comp": 0.0, "tx": 0.0, "ty": 0.0, "zoom": 1.0, "rot": 0.0, "res": 0.0, "par": 0.0})
        if prev is not None:
            st["diff"] = float(np.abs(g.astype(np.int16) - prev.astype(np.int16)).mean())
            flow = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            M, res, _ = sim_fit(flow)
            if M is not None:
                st["tx"], st["ty"], st["zoom"], st["rot"] = centre_move(M)
                st["res"] = res
                wp = cv2.warpAffine(prev, M, (W2, H2), borderMode=cv2.BORDER_REPLICATE)
                st["comp"] = float(np.abs(wp[12:-12, 20:-20].astype(np.int16) - g[12:-12, 20:-20].astype(np.int16)).mean())
                Mi, ri, _ = sim_fit(flow, INNER)
                Mo, ro, _ = sim_fit(flow, OUTER)
                if Mi is not None and Mo is not None and ri < 0.35 and ro < 0.35:
                    xi, yi, zi, _ = centre_move(Mi)
                    xo, yo, zo, _ = centre_move(Mo)
                    # compare the two layers' motion at the same point (the centre) in px/frame
                    st["par"] = float(math.hypot(xi - xo, yi - yo) + abs(zi - zo) * W2 / 2)
        prev = g
        if keys is None:
            keys = list(st.keys())
        rows.append([st[k] for k in keys])
        thumbs.append(cv2.resize(sm, (64, 36), interpolation=cv2.INTER_AREA))
        hists.append(hs_hist(sm))
        if i % 600 == 0:
            print(f"  visual pass {i / FPS:.0f}/{dur:.0f}s", flush=True)
    A = np.array(rows, np.float32)
    F = {k: A[:, j] for j, k in enumerate(keys)}
    F["hist"] = np.array(hists, np.float32)
    return F, np.array(thumbs)


def read_scenes(an):
    cuts = {}
    for name in ("content", "adaptive"):
        for f in glob.glob(f"{an}/scenes/*{name}.csv"):
            rows = list(csv.reader(open(f)))
            hi = next((i for i, r in enumerate(rows) if "Start Time (seconds)" in r), None)
            if hi is None:
                continue
            col = rows[hi].index("Start Time (seconds)")
            for r in rows[hi + 1:]:
                t = float(r[col])
                if t > 0.05:
                    cuts.setdefault(name, []).append(t)
    return cuts


def gradual_candidates(F, thumbs):
    """Transitions spread over several frames that a content detector misses (dissolves, slow wipes): the colour
    histogram 1 s apart peaks there, while inside a shot (even a moving one) it changes slowly."""
    hs = F["hist"]
    n = len(hs)
    out = []
    if n < 30:
        return out
    dist = np.zeros(n)
    for k in range(5, n - 5):
        dist[k] = 0.5 * np.abs(hs[k + 5] - hs[k - 5]).sum()  # total variation, 0..1
    d = F["diff"]
    for k in range(12, n - 12):
        if dist[k] < 0.25 or dist[k] < dist[k - 1] or dist[k] < dist[k + 1]:
            continue
        if max(dist[k - 11], dist[k + 11]) > 0.5 * dist[k]:
            continue  # the shot keeps changing colour: not one transition
        inside = d[k - 3:k + 4]
        if inside.max() < 0.6 * inside.sum():  # spread out, not one spike (a hard cut is found by the detectors)
            out.append(k / FPS)
    return out


def merge_cuts(c, dur):
    pri = sorted([(t, "content") for t in c.get("content", [])] + [(t, "adaptive") for t in c.get("adaptive", [])] +
                 [(t, "gradual") for t in c.get("gradual", [])])
    hard = [t for t, src in pri if src != "gradual"]
    out = []
    for t, src in pri:
        if t < 0.2 or t > dur - 0.2:
            continue
        if src == "gradual" and any(abs(t - h) < 1.0 for h in hard):
            continue  # the detectors already have this transition
        if out and t - out[-1]["t"] < 0.4:
            if src == "content" and out[-1]["src"] != "content":
                out[-1] = {"t": t, "src": src}
            continue
        out.append({"t": round(t, 3), "src": src})
    return out


def rgb_split(f, maxs=12):
    """Horizontal offset in px between the red and blue channels' vertical edges: ~0 in normal frames, the split
    distance in an RGB-split glitch. Brute-force search over +-maxs px (phase correlation fails on colourful
    images whose channels differ)."""
    r, b = (cv2.Sobel(f[..., c].astype(np.float32), cv2.CV_32F, 1, 0, ksize=3) for c in (2, 0))
    r, b = np.abs(r[:, maxs:-maxs]), np.abs(b)
    r = (r - r.mean()) / (r.std() + 1e-6)
    best, c0 = (-9, 0), 0.0
    for sft in range(-maxs, maxs + 1):
        bb = b[:, maxs + sft:b.shape[1] - maxs + sft]
        c = float((r * (bb - bb.mean())).mean() / (bb.std() + 1e-6))
        if sft == 0:
            c0 = c
        if c > best[0]:
            best = (c, sft)
    return float(abs(best[1])) if best[0] - c0 > 0.05 else 0.0


def classify_transition(video, t, fps):
    """Look at the full frame-rate window around a cut and name the transition."""
    pre = 1.0
    big = list(frames(video, None, W2 * 2, H2 * 2, ss=max(0, t - pre), dur=2 * pre))
    if len(big) < 8:
        return {"type": "cut"}
    fr = [cv2.resize(f, (W2, H2), interpolation=cv2.INTER_AREA) for f in big]
    g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in fr]
    n = len(g)
    L = np.array([x.mean() for x in g])
    d = np.array([0] + [np.abs(g[i].astype(np.int16) - g[i - 1].astype(np.int16)).mean() for i in range(1, n)])
    sh = np.array([cv2.Laplacian(x, cv2.CV_64F).var() for x in g])
    split = np.array([rgb_split(f) for f in big])
    rb = np.array([f[..., 2].mean() - f[..., 0].mean() for f in fr])
    mv = [(0, 0, 1, 0)]
    for i in range(1, n):
        flow = cv2.calcOpticalFlowFarneback(g[i - 1], g[i], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        M, res, _ = sim_fit(flow)
        mv.append(centre_move(M) if M is not None and res < 1.5 else (0, 0, 1, 0))
    mv = np.array(mv)
    mid = slice(max(1, n // 2 - int(0.7 * fps)), n // 2 + int(0.7 * fps))  # the change lies within +-0.7 s of t
    c = mid.start + int(np.argmax(d[mid]))
    # the transition = the run of frames around the peak that change faster than the shot on that side moves
    base_l = max(1.5, float(np.median(d[1:6])) * 1.6)
    base_r = max(1.5, float(np.median(d[-5:])) * 1.6)
    a = b = c
    while a - 1 >= 1 and c - a < 20 and (d[a - 1] > base_l or (a - 2 >= 1 and d[a - 2] > base_l)):
        a -= 1
    while b + 1 < n and b - c < 20 and (d[b + 1] > base_r or (b + 2 < n and d[b + 2] > base_r)):
        b += 1
    k = b - a + 1
    Lpre, Lpost = np.median(L[:5]), np.median(L[-5:])
    win = slice(max(0, a - 2), min(n, b + 3))
    info = {"frames": int(k), "dur_s": round(k / fps, 2)}
    lmax, lmin = L[win].max(), L[win].min()
    if lmax > max(Lpre, Lpost) + 30 and lmax > 140:
        j = win.start + int(np.argmax(L[win]))
        info["type"] = "light leak" if rb[j] > 30 else "flash"
        info["peak_luma"] = int(lmax)
        return info
    if lmin < 12 and min(Lpre, Lpost) > 15 and lmin < 0.35 * min(Lpre, Lpost):
        info["type"] = "dip to black"
        return info
    side = float(np.median(np.r_[split[:5], split[-5:]]))
    if split[win].max() > max(2.0, 3 * side + 1.0):
        info["type"] = "glitch"
        info["rgb_split_px_1080p"] = int(split[win].max() * 1920 / (W2 * 2))  # distance between the red and blue copies
        return info
    sharp_out = np.median(np.r_[sh[:3], sh[-3:]]) + 1e-6
    blur = sh[win].min() / sharp_out
    tmax = np.abs(mv[win, :2]).max(0)
    zmax = np.abs(mv[win, 2] - 1).max()
    if max(tmax) > 5:
        ax = 0 if tmax[0] >= tmax[1] else 1
        j = win.start + int(np.argmax(np.abs(mv[win, ax])))
        direc = ("left" if mv[j, 0] < 0 else "right") if ax == 0 else ("up" if mv[j, 1] < 0 else "down")
        info["type"] = ("whip" if blur < 0.5 else "slide") + f" (content moves {direc})"
        info["max_speed_px_per_frame_1080p"] = int(max(tmax) * SC)
        return info
    if zmax > 0.035:
        j = win.start + int(np.argmax(np.abs(mv[win, 2] - 1)))
        info["type"] = "zoom " + ("in" if mv[j, 2] > 1 else "out") + (" + blur" if blur < 0.5 else "")
        info["max_zoom_per_frame"] = round(float(zmax), 3)
        return info
    near = np.sort(d[max(1, c - 3):c + 4])
    if len(near) >= 2 and d[c] > 3 * near[-2]:  # one frame carries the change: a cut (into moving content)
        info.update({"type": "cut", "frames": 1, "dur_s": round(1 / fps, 2)})
        return info
    if k >= 3 and a >= 2 and b <= n - 2:
        A, B = g[a - 1].astype(np.float32), g[b + 1].astype(np.float32) if b + 1 < n else g[b].astype(np.float32)
        AB = B - A
        den = (AB ** 2).sum() + 1e-6
        rel = []
        alphas = []
        for i in range(a, b + 1):
            F = g[i].astype(np.float32)
            al = float(((F - A) * AB).sum() / den)
            alphas.append(al)
            rel.append(np.abs(F - (A + al * AB)).mean() / (np.abs(AB).mean() + 1e-6))
        mids = sum(1 for x in alphas if 0.2 < x < 0.8)
        if mids >= 2 and np.mean(rel) < 0.45 and np.all(np.diff(alphas) > -0.15):
            info["type"] = "dissolve"
            return info
        info["type"] = "gradual (other)"
        return info
    info["type"] = "cut"
    return info


def classify_shot(F, i0, i1):
    sl = slice(i0, i1)
    z = F["zoom"][sl]
    zr = float(np.mean(np.log(np.maximum(z, 1e-3)))) * FPS * 100  # % per second
    tx, ty = F["tx"][sl] * SC * FPS, F["ty"][sl] * SC * FPS          # px/s at 1080p
    mx, my = float(np.median(tx)), float(np.median(ty))
    speed = math.hypot(mx, my)
    rot = float(np.median(F["rot"][sl])) * FPS
    k = max(3, (i1 - i0) // 6)
    good = F["res"][sl] < 0.35  # shake only means something where one rigid motion explains the frame
    jit = float(np.std((tx - np.convolve(tx, np.ones(k) / k, "same"))[good])) if i1 - i0 > 6 and good.mean() > 0.6 else 0.0
    comp = float(np.median(F["comp"][sl]))
    par = float(np.mean(F["par"][sl] > 0.25))
    flat, black = float(np.median(F["flat"][sl])), float(np.median(F["black"][sl]))
    m = []
    if abs(zr) >= 0.4:
        m.append(f"push-in {zr:.1f}%/s" if zr > 0 else f"pull-out {-zr:.1f}%/s")
    if speed >= 8:
        if abs(mx) >= abs(my):
            m.append(f"pan {'right' if mx < 0 else 'left'} {speed:.0f}px/s")
        else:
            m.append(f"tilt {'down' if my < 0 else 'up'} {speed:.0f}px/s")
    if abs(rot) > 0.3:
        m.append(f"roll {rot:.1f}deg/s")
    if par > 0.4:
        m.append("2.5D parallax")
    if jit > 6:
        m.append("shake")
    motion = ", ".join(m) or "static"
    if flat > 0.5 or (black > 0.55 and flat > 0.3):
        content = "graphic"
    elif comp < 2.2 and float(np.median(F["res"][sl])) < 0.35:
        content = "still + camera move" if motion != "static" else "still"
        if par > 0.4:
            content = "2.5D still (parallax layers)"
    else:
        content = "footage/animation"
    return {"motion": motion, "content": content, "zoom_pct_s": round(zr, 2), "pan_px_s": [round(mx), round(my)],
            "roll_deg_s": round(rot, 2), "shake_px": round(jit, 1), "comp_residual": round(comp, 2), "parallax_frac": round(par, 2),
            "flat": round(flat, 2), "black": round(black, 2), "luma": round(float(np.median(F["luma"][sl]))),
            "sat": round(float(np.median(F["sat"][sl]))), "lab_ab": [round(float(np.median(F["a"][sl])), 1), round(float(np.median(F["b"][sl])), 1)],
            "shadow_ab": [round(float(np.median(F["sh_a"][sl])), 1), round(float(np.median(F["sh_b"][sl])), 1)],
            "highlight_ab": [round(float(np.median(F["hi_a"][sl])), 1), round(float(np.median(F["hi_b"][sl])), 1)],
            "noise": round(float(np.median(F["noise"][sl])), 2)}


def grade(F, thumbs):
    g = thumbs.astype(np.float32).mean(3)
    med = np.median(g[::3], 0)
    ctr = med[12:24, 22:42].mean() + 1e-6
    corners = np.mean([med[:5, :8].mean(), med[:5, -8:].mean(), med[-5:, :8].mean(), med[-5:, -8:].mean()])
    rowmax = g.max((0, 2))
    bars = int(np.argmax(rowmax > 12)) if rowmax[0] <= 12 else 0
    q = lambda k: round(float(np.median(F[k])), 1)
    lit = F["luma"] > 25
    return {
        "luma_median": q("luma"), "black_point_p1": q("p1"), "white_point_p99": q("p99"),
        "contrast_p95_p5": round(float(np.median(F["p95"] - F["p5"])), 1), "saturation_median": q("sat"),
        "lab_a_b": [q("a"), q("b")], "shadow_tint_ab": [q("sh_a"), q("sh_b")], "highlight_tint_ab": [q("hi_a"), q("hi_b")],
        "vignette_corner_to_centre": round(float(corners / ctr), 2),
        "vignette_stops": round(float(math.log2(max(corners, 1e-3) / ctr)), 2),
        "letterbox_rows_of_36": bars,
        "noise_floor_median": round(float(np.median(F["noise"][F["noise"] >= 0])), 2) if (F["noise"] >= 0).any() else None,
        "dark_frames_frac": round(float(1 - lit.mean()), 3),
    }


def shot_sheets(video, shots, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    tiles = []
    for s in shots:
        t = (s["start"] + s["end"]) / 2
        fr = next(frames(video, None, 320, 180, ss=t, dur=0.2), np.zeros((180, 320, 3), np.uint8)).copy()
        lab1 = f"#{s['i']} {int(s['start'] // 60)}:{s['start'] % 60:04.1f} {s['dur']:.1f}s"
        lab2 = s["content"][:22]
        lab3 = s["motion"][:34]
        for j, l in enumerate((lab1, lab2, lab3)):
            cv2.putText(fr, l, (4, 16 + 16 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
            cv2.putText(fr, l, (4, 16 + 16 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        tiles.append(fr)
    per = 30
    for k in range(0, len(tiles), per):
        grp = tiles[k:k + per] + [np.zeros((180, 320, 3), np.uint8)] * (-len(tiles[k:k + per]) % 6)
        rows = [np.hstack(grp[r:r + 6]) for r in range(0, len(grp), 6)]
        cv2.imwrite(f"{out_dir}/shots_{k // per + 1:02d}.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])


def analyse(video, an):
    dur, fps, w, h = probe(video)
    F, thumbs = main_pass(video, dur)
    np.savez_compressed(f"{an}/frames10.npz", thumbs=thumbs, **F)
    c = read_scenes(an)
    c["gradual"] = gradual_candidates(F, thumbs)
    cuts = merge_cuts(c, dur)
    for k, cu in enumerate(cuts):
        cu.update(classify_transition(video, cu["t"], fps))
        if k % 50 == 0:
            print(f"  transitions {k}/{len(cuts)}", flush=True)
    cuts = [cu for cu in cuts if not (cu["src"] == "gradual" and cu["type"] in ("cut", "gradual (other)"))]
    # a flash, whip or dissolve often trips the detectors twice (going in and coming out): keep one
    special = lambda c: c["type"] not in ("cut", "gradual (other)")
    m = []
    for cu in cuts:
        if m and cu["t"] - m[-1]["t"] < 0.7 and (special(cu) or special(m[-1])):
            if special(cu) and not special(m[-1]):
                m[-1] = cu
            continue
        m.append(cu)
    cuts = m
    # flash frames that are not cuts
    L = F["luma"]
    flashes = [round(i / FPS, 1) for i in range(2, len(L) - 2)
               if L[i] > max(L[i - 2], L[i + 2]) + 35 and L[i] > 150 and all(abs(i / FPS - cu["t"]) > 0.5 for cu in cuts)]
    bounds = [0.0] + [cu["t"] for cu in cuts] + [dur]
    shots = []
    for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
        i0, i1 = int(a * FPS) + 2, max(int(a * FPS) + 3, int(b * FPS) - 2)
        s = {"i": i, "start": round(a, 2), "end": round(b, 2), "dur": round(b - a, 2)}
        s.update(classify_shot(F, min(i0, len(L) - 1), min(i1, len(L))))
        s["in_transition"] = cuts[i - 1]["type"] if i else "start"
        shots.append(s)
    out = {"duration_s": round(dur, 2), "fps": round(fps, 3), "size": [w, h], "analysis_fps": FPS,
           "cuts": cuts, "shots": shots, "flash_frames": flashes, "grade": grade(F, thumbs),
           "scene_detector_counts": {k: len(v) for k, v in c.items()}}
    shot_sheets(video, shots, f"{an}/shots")
    return out


def main():
    video, an = sys.argv[1], sys.argv[2]
    os.makedirs(an, exist_ok=True)
    out = analyse(video, an)
    json.dump(out, open(f"{an}/visual.json", "w"), indent=1)
    from collections import Counter
    print(len(out["shots"]), "shots;", Counter(c["type"].split(" (")[0] for c in out["cuts"]))
    print(Counter(s["content"] for s in out["shots"]))
    print(out["grade"])


if __name__ == "__main__":
    main()
