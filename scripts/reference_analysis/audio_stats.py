"""Voice / music / SFX measurements from the Demucs stems of a reference video.

  python audio_stats.py <audio_dir> [--words words.json]

Expects <audio_dir>/demucs/htdemucs/mix/vocals.wav and either no_vocals.wav or drums/bass/other.wav
(analyze_video.sh writes both). Writes <audio_dir>/audio_stats.json and <audio_dir>/music_map.jpg.

What it measures (all times in seconds, levels in dBFS / LUFS):
  loudness      BS.1770 integrated + momentary (400 ms) loudness of the mix, voice and music stems
  voice         speech segments (stem VAD), pauses, words per minute (with --words from transcribe.py), pitch
  levels        voice-minus-music gap while speaking, music level in pauses, per minute
  ducking       event-locked music level around speech offsets / onsets: depth, attack and release times
  music         track segments (novelty + gaps), per segment tempo + pulse clarity, key, brightness,
                percussive share, level, fade in / out; segments grouped into distinct tracks
  swells        music rising >= 4 dB over its running median; silences: mix silence + music drop-outs
  sfx           transient events above the music bed (whoosh, riser, boom/hit, sub drop, pop/click,
                glitch, chime) with time, duration, level and spectral shape
The music stem still carries a little voice leakage under speech, so music levels under speech are an upper
bound; levels in pauses are clean.
"""
import argparse, json, os, sys
import numpy as np, soundfile as sf, librosa
from scipy import ndimage, signal

HOP = 0.1          # loudness / level timeline step
FR = 0.02          # fine envelope step for events


# ------------------------------------------------------------------ loudness (ITU-R BS.1770)
def k_weight(x, sr):
    """K-weighting: high shelf + high pass, coefficients as in pyloudnorm / libebur128."""
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    A, w0 = 10 ** (G / 40), 2 * np.pi * fc / sr
    al = np.sin(w0) / (2 * Q)
    b = [A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * np.cos(w0)),
         A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * al)]
    a = [(A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * np.cos(w0)),
         (A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * al]
    x = signal.lfilter(b, a, x, axis=0)
    Q, fc = 0.5003270373238773, 38.13547087602444
    w0 = 2 * np.pi * fc / sr
    al = np.sin(w0) / (2 * Q)
    b = [(1 + np.cos(w0)) / 2, -(1 + np.cos(w0)), (1 + np.cos(w0)) / 2]
    a = [1 + al, -2 * np.cos(w0), 1 - al]
    return signal.lfilter(b, a, x, axis=0)


def loudness(x, sr):
    """-> (momentary LUFS every 100 ms (400 ms window, value at window centre), integrated LUFS)."""
    x = x if x.ndim > 1 else x[:, None]
    z = (k_weight(x, sr) ** 2).sum(1)
    hop, win = int(sr * HOP), int(sr * 0.4)
    c = np.concatenate([[0], np.cumsum(z)])
    starts = np.arange(-win // 2, len(z) - win // 2, hop)
    a, b = np.clip(starts, 0, len(z)), np.clip(starts + win, 0, len(z))
    ms = (c[b] - c[a]) / win
    M = -0.691 + 10 * np.log10(np.maximum(ms, 1e-12))
    full = ms[(starts >= 0) & (starts + win <= len(z))]
    blk = full if len(full) else ms  # gating blocks: 400 ms, 75 % overlap = every 100 ms step
    lk = -0.691 + 10 * np.log10(np.maximum(blk, 1e-12))
    g = blk[lk > -70]
    if not len(g):
        return M, -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = g[(-0.691 + 10 * np.log10(g)) > rel]
    return M, round(float(-0.691 + 10 * np.log10(g.mean())), 1)


def rms_db(x, sr, step):
    hop = int(sr * step)
    n = len(x) // hop
    r = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1))
    return 20 * np.log10(np.maximum(r, 1e-6))


# ------------------------------------------------------------------ voice
def speech_segments(vdb, step, floor=-50):
    """Voice activity from the vocal stem's level: hysteresis around (p97 - 28 dB), gaps < 0.2 s filled."""
    top = np.percentile(vdb, 97)
    on, off = max(top - 26, floor), max(top - 32, floor - 4)
    act, state = np.zeros(len(vdb), bool), False
    for i, v in enumerate(vdb):
        state = v > on if not state else v > off
        act[i] = state
    act = ndimage.binary_closing(act, np.ones(int(0.2 / step) + 1, bool))
    lab, n = ndimage.label(act)
    segs = []
    for k in range(1, n + 1):
        idx = np.where(lab == k)[0]
        if (idx[-1] - idx[0] + 1) * step >= 0.12:
            segs.append([round(idx[0] * step, 2), round((idx[-1] + 1) * step, 2)])
    return segs


def activity(segs, n, step):
    a = np.zeros(n, bool)
    for s, e in segs:
        a[int(s / step):int(e / step)] = True
    return a


# ------------------------------------------------------------------ music analysis helpers
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = "C C# D D# E F F# G G# A A# B".split()


def key_of(chroma_mean):
    best = (-2, "")
    for i in range(12):
        for prof, mode in ((KS_MAJ, "major"), (KS_MIN, "minor")):
            r = np.corrcoef(np.roll(prof, i), chroma_mean)[0, 1]
            if r > best[0]:
                best = (r, f"{NOTES[i]} {mode}")
    return best[1], round(float(best[0]), 2)


def tempo_of(y, sr):
    """Tempo plus pulse clarity (0-1: height of the onset autocorrelation peak; < ~0.3 = no steady beat)."""
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    if len(oenv) < 64 or oenv.std() < 1e-6:
        return None, 0.0
    tempo = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=oenv, sr=sr, hop_length=512))[0])
    o = oenv - oenv.mean()
    ac = np.correlate(o, o, "full")[len(o) - 1:]
    ac = ac / (ac[0] + 1e-9)
    fps = sr / 512
    lo, hi = int(fps * 60 / 200), int(fps * 60 / 40)
    clarity = float(ac[lo:hi].max()) if hi < len(ac) else 0.0
    return round(tempo, 1), round(clarity, 2)


def describe(seg):
    """Plain-words mood from the measured features (a hint for the write-up, not a genre classifier)."""
    w = []
    w.append("bright" if seg["centroid_hz"] > 2500 else "dark" if seg["centroid_hz"] < 1200 else "mid")
    if seg["pulse_clarity"] < 0.3:
        w.append("ambient pad / drone, no steady beat")
    else:
        w.append(f"pulse {seg['tempo_bpm']} BPM")
    w.append("percussive" if seg["percussive_share"] > 0.35 else "sustained")
    w.append(seg["key"])
    return ", ".join(w)


def runs(mask, step, min_len):
    lab, n = ndimage.label(mask)
    out = []
    for k in range(1, n + 1):
        idx = np.where(lab == k)[0]
        if (idx[-1] - idx[0] + 1) * step >= min_len:
            out.append((idx[0], idx[-1] + 1))
    return out


# ------------------------------------------------------------------ main analysis
def analyse(d, words_path=None):
    stem = f"{d}/demucs/htdemucs/mix"
    voc, sr = sf.read(f"{stem}/vocals.wav")
    if os.path.exists(f"{stem}/no_vocals.wav"):
        mus, _ = sf.read(f"{stem}/no_vocals.wav")
    else:
        mus = sum(sf.read(f"{stem}/{s}.wav")[0] for s in ("drums", "bass", "other"))
    drums = sf.read(f"{stem}/drums.wav")[0] if os.path.exists(f"{stem}/drums.wav") else None
    mix = sf.read(f"{d}/mix.wav")[0] if os.path.exists(f"{d}/mix.wav") else voc + mus
    n = min(len(voc), len(mus), len(mix))
    voc, mus, mix = voc[:n], mus[:n], mix[:n]
    mono = lambda x: x.mean(1) if x.ndim > 1 else x
    vm, mm = mono(voc), mono(mus)
    dur = n / sr
    out = {"duration_s": round(dur, 2)}

    # loudness
    Mv, Iv = loudness(voc, sr)
    Mm, Im = loudness(mus, sr)
    Mx, Ix = loudness(mix, sr)
    k = min(len(Mv), len(Mm), len(Mx))
    Mv, Mm, Mx = Mv[:k], Mm[:k], Mx[:k]
    out["lufs_integrated"] = {"mix": Ix, "voice": Iv, "music_sfx": Im}
    out["mix_true_peak_dbfs_approx"] = round(float(20 * np.log10(np.abs(signal.resample_poly(mono(mix), 4, 1)).max() + 1e-9)), 1)

    # voice activity, pauses
    vdb_f = rms_db(vm, sr, FR)
    segs = speech_segments(vdb_f, FR)
    sp = activity(segs, k, HOP)
    out["speech_segments"] = segs
    nstart, nend = (segs[0][0], segs[-1][1]) if segs else (0, 0)
    gaps = [(a[1], b[0]) for a, b in zip(segs, segs[1:]) if b[0] - a[1] >= 0.3]
    g = np.array([b - a for a, b in gaps]) if gaps else np.zeros(0)
    out["voice"] = {
        "narration_start_s": nstart, "narration_end_s": nend,
        "speech_fraction_of_runtime": round(float(sp.mean()), 3),
        "pauses_ge_0.3s": int(len(g)),
        "pause_median_s": round(float(np.median(g)), 2) if len(g) else None,
        "pause_p90_s": round(float(np.percentile(g, 90)), 2) if len(g) else None,
        "pauses_ge_1.0s": int((g >= 1.0).sum()), "pauses_ge_1.5s": int((g >= 1.5).sum()),
        "longest_pauses": [[round(a, 1), round(b - a, 2)] for a, b in sorted(gaps, key=lambda x: x[0] - x[1])[:12]],
    }
    if words_path and os.path.exists(words_path):
        wds = json.load(open(words_path))
        wds = wds.get("words", wds)
        if wds:
            span = (wds[-1]["end"] - wds[0]["start"]) / 60
            out["voice"]["words"] = len(wds)
            out["voice"]["wpm_over_narration_span"] = round(len(wds) / span, 1)
            talk = sum(e - s for s, e in segs) / 60
            out["voice"]["wpm_while_speaking"] = round(len(wds) / max(talk, 1e-6), 1)
            per = np.zeros(int(dur // 60) + 1)
            for w in wds:
                per[int(w["start"] // 60)] += 1
            out["voice"]["words_per_minute_by_minute"] = per.astype(int).tolist()
    # pitch on up to 120 s of speech
    try:
        vy = librosa.resample(vm.astype(np.float32), orig_sr=sr, target_sr=16000)
        a0 = int(max(nstart, 0) * 16000)
        seg = vy[a0 + 30 * 16000:a0 + 150 * 16000] if len(vy) > a0 + 60 * 16000 else vy[a0:]
        f0, _, _ = librosa.pyin(seg, fmin=60, fmax=400, sr=16000, frame_length=1024)
        f0 = f0[~np.isnan(f0)]
        out["voice"]["f0_median_hz"] = round(float(np.median(f0)), 1)
        out["voice"]["f0_std_semitones"] = round(float(np.std(12 * np.log2(f0 / np.median(f0)))), 2)
    except Exception as e:  # noqa: BLE001
        out["voice"]["f0_error"] = str(e)[:80]

    # levels: voice vs music while speaking, music in pauses
    live = Mm > -70
    pause = ~sp & (np.arange(k) * HOP > nstart) & (np.arange(k) * HOP < nend)
    lv = {
        "voice_momentary_lufs_speaking": round(float(np.median(Mv[sp])), 1) if sp.any() else None,
        "music_momentary_lufs_under_speech": round(float(np.median(Mm[sp & live])), 1) if (sp & live).any() else None,
        "music_momentary_lufs_in_pauses": round(float(np.median(Mm[pause & live])), 1) if (pause & live).any() else None,
    }
    if lv["voice_momentary_lufs_speaking"] is not None and lv["music_momentary_lufs_under_speech"] is not None:
        lv["voice_minus_music_lu_speaking"] = round(lv["voice_momentary_lufs_speaking"] - lv["music_momentary_lufs_under_speech"], 1)
    if lv["music_momentary_lufs_in_pauses"] is not None and lv["voice_momentary_lufs_speaking"] is not None:
        lv["voice_minus_music_lu_pauses"] = round(lv["voice_momentary_lufs_speaking"] - lv["music_momentary_lufs_in_pauses"], 1)
    per_min = []
    for m0 in range(0, int(np.ceil(dur / 60))):
        sl = slice(int(m0 * 60 / HOP), int((m0 + 1) * 60 / HOP))
        s_, p_, l_ = sp[sl], pause[sl], live[sl]
        per_min.append({
            "min": m0,
            "voice": round(float(np.median(Mv[sl][s_])), 1) if s_.any() else None,
            "music_speech": round(float(np.median(Mm[sl][s_ & l_])), 1) if (s_ & l_).any() else None,
            "music_pause": round(float(np.median(Mm[sl][p_ & l_])), 1) if (p_ & l_).any() else None})
    lv["per_minute"] = per_min
    out["levels"] = lv

    # ducking: music level around speech offsets / onsets (pauses >= 1 s), 50 ms resolution
    mdb = rms_db(mm, sr, 0.05)
    tt = np.arange(-1.5, 2.5, 0.05)

    def locked(times, base):
        rows = []
        for t in times:
            i = int(t / 0.05)
            idx = i + (tt / 0.05).round().astype(int)
            if idx[0] < 0 or idx[-1] >= len(mdb):
                continue
            r = mdb[idx]
            b = r[(tt >= base[0]) & (tt < base[1])]
            if b.max() < -65:
                continue
            rows.append(r - np.median(b))
        return np.median(rows, 0) if rows else None, len(rows)

    long_gaps = [(a, b) for a, b in gaps if b - a >= 1.0]
    off_c, n_off = locked([a for a, b in long_gaps], (-1.5, -0.3))
    on_c, n_on = locked([b for a, b in long_gaps], (-1.2, -0.2))
    duck = {"events": n_off}
    if off_c is not None:
        rise = off_c[(tt > 0.6) & (tt < 1.0)].mean() if (tt > 0.6).any() else 0
        duck["depth_db"] = round(float(rise), 1)
        if rise > 2:
            j = np.where((tt > 0) & (off_c >= 0.9 * rise))[0]
            duck["release_s_to_90pct"] = round(float(tt[j[0]]), 2) if len(j) else None
        duck["curve_after_speech_ends"] = [[round(float(a), 2), round(float(b), 1)] for a, b in zip(tt[::2], off_c[::2])]
    if on_c is not None:
        drop = on_c[(tt > 0.6) & (tt < 1.2)].mean()
        duck["drop_when_speech_resumes_db"] = round(float(drop), 1)
        if drop < -2:
            j = np.where((tt > 0) & (on_c <= 0.9 * drop))[0]
            duck["attack_s_to_90pct"] = round(float(tt[j[0]]), 2) if len(j) else None
        duck["curve_after_speech_resumes"] = [[round(float(a), 2), round(float(b), 1)] for a, b in zip(tt[::2], on_c[::2])]
    out["ducking"] = duck

    # ---- music bed vs transients on a mel spectrogram of the music stem
    y = librosa.resample(mm.astype(np.float32), orig_sr=sr, target_sr=22050)
    srr, hop = 22050, 441  # 20 ms
    S = librosa.feature.melspectrogram(y=y, sr=srr, n_fft=2048, hop_length=hop, n_mels=96, fmax=11025, power=2.0)
    freqs = librosa.mel_frequencies(n_mels=96, fmax=11025)
    # the bed: 30th percentile over 4 s (0.2 s blocks), so sounds up to ~2.5 s long stay out of it
    blk = int(0.2 / FR)
    nb = int(np.ceil(S.shape[1] / blk))
    Sb = np.pad(S, ((0, 0), (0, nb * blk - S.shape[1])), mode="edge").reshape(S.shape[0], nb, blk).mean(2)
    bedb = ndimage.percentile_filter(Sb, 30, size=(1, 21), mode="nearest")
    bed = np.repeat(bedb, blk, axis=1)[:, :S.shape[1]]
    res = np.maximum(S - 1.6 * bed, 0)  # what the slow-moving bed does not explain: notes, hits, edit sounds
    # calibrate mel power to the signal's RMS power, so the levels below read as dBFS (RMS per 20 ms frame)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0][:S.shape[1]]
    live_ = rms > 1e-4
    ref = float(np.median(S.sum(0)[:len(rms)][live_] / rms[live_] ** 2)) if live_.any() else 1.0
    db_ = lambda x: 10 * np.log10(x / ref + 1e-13)
    e_tot = db_(S.sum(0))
    nf = len(e_tot)

    # music presence + segments
    harm = librosa.effects.harmonic(y, margin=2.0)
    chroma = librosa.feature.chroma_cqt(y=harm, sr=srr, hop_length=2048)
    mf = librosa.feature.mfcc(S=librosa.power_to_db(bed + 1e-10), n_mfcc=13)
    cfps, mfps = srr / 2048, 1 / FR
    # music level: power average over 1 s, steady for sustained pads and plucked notes alike
    bed_s = db_(ndimage.uniform_filter1d(S.sum(0), int(1.0 / FR)))
    present = bed_s > -60  # Demucs leaves the music stem near -70 dBFS where there is no music
    mfc = mf[:, np.minimum((np.arange(chroma.shape[1]) * mfps / cfps).astype(int), mf.shape[1] - 1)]
    feat = np.vstack([librosa.util.normalize(chroma, axis=0), librosa.util.normalize(mfc, axis=1)])
    w = int(6 * cfps)
    nov = np.zeros(feat.shape[1])
    for i in range(w, feat.shape[1] - w):
        nov[i] = np.linalg.norm(feat[:, i - w:i].mean(1) - feat[:, i:i + w].mean(1))
    pk = librosa.util.peak_pick(nov, pre_max=int(8 * cfps), post_max=int(8 * cfps), pre_avg=int(8 * cfps),
                                post_avg=int(8 * cfps), delta=float(np.std(nov)) * 0.9, wait=int(12 * cfps))
    bounds = {round(p / cfps, 1) for p in pk}
    for a, b in runs(~present, FR, 1.0):  # music gaps split segments too
        bounds |= {round(a * FR, 1), round(b * FR, 1)}
    bounds = sorted(b for b in bounds if 1 < b < dur - 1) + [round(dur, 1)]
    segs_m, t0 = [], 0.0
    for b in bounds:
        if b - t0 < 4:
            continue
        segs_m.append([t0, b])
        t0 = b
    if segs_m and dur - segs_m[-1][1] > 0.5:
        segs_m[-1][1] = round(dur, 1)
    music = []
    dfull = mono(drums) if drums is not None else None
    for a, b in segs_m:
        fa, fb = int(a / FR), min(nf, int(b / FR))
        pres = present[fa:fb]
        if pres.mean() < 0.4:
            music.append({"start": a, "end": b, "music": False})
            continue
        ya = y[int(a * srr):int(b * srr)]
        tempo, clar = tempo_of(ya, srr)
        cm = chroma[:, int(a * cfps):int(b * cfps)].mean(1)
        key, kconf = key_of(cm)
        cen = librosa.feature.spectral_centroid(S=np.sqrt(bed[:, fa:fb]), freq=freqs).ravel()
        seg = {"start": a, "end": b, "music": True, "tempo_bpm": tempo, "pulse_clarity": clar, "key": key, "key_conf": kconf,
               "centroid_hz": int(np.median(cen)),
               "bed_level_dbfs": round(float(np.median(bed_s[fa:fb][pres])), 1)}
        if dfull is not None:
            dseg = dfull[int(a * sr):int(b * sr)]
            mseg = mm[int(a * sr):int(b * sr)]
            seg["percussive_share"] = round(float((dseg ** 2).sum() / ((mseg ** 2).sum() + 1e-12)), 2)
        else:
            Hh, Pp = librosa.decompose.hpss(np.abs(librosa.stft(ya[:srr * 60], hop_length=512)))
            seg["percussive_share"] = round(float((Pp ** 2).sum() / ((Hh ** 2).sum() + (Pp ** 2).sum() + 1e-12)), 2)
        ia, ib = int(a / HOP), min(k, int(b / HOP))
        s_, p_ = sp[ia:ib], pause[ia:ib]
        seg["lufs_under_speech"] = round(float(np.median(Mm[ia:ib][s_])), 1) if s_.any() else None
        seg["lufs_in_pauses"] = round(float(np.median(Mm[ia:ib][p_])), 1) if p_.any() else None
        lvl = bed_s[fa:fb]
        steady = np.median(lvl)
        up = np.where(lvl >= steady - 3)[0]
        seg["fade_in_s"] = round(float(up[0] * FR), 1) if len(up) else None
        seg["fade_out_s"] = round(float((len(lvl) - 1 - up[-1]) * FR), 1) if len(up) else None
        seg["chroma_profile"] = [round(float(v), 3) for v in cm / (cm.sum() + 1e-9)]
        seg["timbre_profile"] = [round(float(v), 2) for v in mf[:, fa:fb].mean(1)]
        seg["mood_hint"] = describe(seg)
        music.append(seg)
    # group segments into distinct tracks (same chroma + timbre profile = same track resumed)
    tid = 0
    for i, s in enumerate(music):
        if not s["music"]:
            continue
        for p in music[:i]:
            if p.get("track") is None:
                continue
            c = np.dot(s["chroma_profile"], p["chroma_profile"]) / (np.linalg.norm(s["chroma_profile"]) * np.linalg.norm(p["chroma_profile"]) + 1e-9)
            pulse = s["pulse_clarity"] >= 0.3 and p["pulse_clarity"] >= 0.3
            same_tempo = (not pulse) or min(abs(s["tempo_bpm"] / p["tempo_bpm"] - r) for r in (0.5, 1, 2)) < 0.06
            if c > 0.95 and s["key"] == p["key"] and same_tempo:
                s["track"] = p["track"]
                break
        if s.get("track") is None:
            tid += 1
            s["track"] = tid
    out["music_segments"] = music
    out["music_distinct_tracks"] = tid
    out["music_novelty_peaks_s"] = sorted(bounds[:-1])

    # ---- SFX events: band-wise onsets of energy that the music bed does not explain
    floor = S.max() * 1e-7
    Rdb = 10 * np.log10(res + floor)
    Sdb = 10 * np.log10(S + floor)
    flux = Rdb[:, 2:] - np.maximum(Rdb[:, 1:-1], Rdb[:, :-2])
    flux = np.pad(flux, ((0, 0), (2, 0)))
    on = (flux > 9) & (Rdb > Sdb - 6) & (res > ref * 10 ** (-75 / 10))
    O = db_((on * res).sum(0) + 1e-30)
    cand, _ = signal.find_peaks(np.where(on.any(0), O, -200), height=-62, distance=int(0.06 / FR))
    od = librosa.onset.onset_strength(y=y, sr=srr, hop_length=hop)
    # every onset, however quiet (music under the voice included): the reference set for "does this repeat?"
    on_all = (flux > 6) & (res > ref * 10 ** (-90 / 10))
    allc, _ = signal.find_peaks(np.where(on_all.any(0), db_((on_all * res).sum(0) + 1e-30), -200), height=-80, distance=int(0.06 / FR))
    inc = lambda p0: np.sqrt(np.maximum(S[:, p0:p0 + 2].max(1) - S[:, max(0, p0 - 4):max(1, p0 - 1)].mean(1), 0))
    ref_on = [(int(c), v / (np.linalg.norm(v) + 1e-30)) for c in allc for v in [inc(c)]]
    ref_t = np.array([c for c, _ in ref_on])
    # onset level relative to the music around it (+-0.5 s): about the same for a drum hit under the voice and in
    # a pause, so ducking does not make repeats look different
    Ssum = S.sum(0)
    onset_db = lambda p0: float(db_(S[:, p0:p0 + 2].max(1).sum()) - db_(Ssum[max(0, p0 - 25):p0 + 25].mean() + 1e-30))
    ref_lv = np.array([onset_db(c) for c in ref_t])
    lowb, highb = freqs < 150, freqs > 4000
    raw = []
    for p0 in cand:
        M = on[:, p0:p0 + 3].any(1)
        if M.sum() == 0:
            continue
        e = db_(res[M].sum(0) + 1e-30)
        # the peak: follow the envelope while it is still near its running maximum; a drop of 10 dB ends the sound
        j, top, pk = p0, e[p0], p0
        while j + 1 < min(nf, p0 + int(3 / FR)) and e[j + 1] > top - 10:
            j += 1
            if e[j] > top:
                top, pk = e[j], j
        lvl = e[pk]
        end = pk
        while end < nf - 1 and e[end + 1] > lvl - 20 and end - pk < int(4 / FR):
            end += 1
        bed_in = db_(bed[M, pk].sum() + S[M, pk].sum() * 1e-3)
        R = res[M][:, p0:end + 1]
        Rf = res[:, p0:end + 1] * M[:, None]
        tot = Rf.sum() + 1e-30
        cen = (freqs[:, None] * Rf).sum(0) / (Rf.sum(0) + 1e-30)
        lc = np.log2(np.maximum(cen, 20))
        dom = (res[:, pk] > 0.5 * S[:, pk]) & (S[:, pk] > S[:, pk].max() * 1e-4)  # bands the sound owns at its peak
        # what the onset added to the spectrum (independent of the music's level) -> similarity of repeats
        pr = inc(p0)
        rp = res[:, pk]
        cum = np.cumsum(rp) / (rp.sum() + 1e-30)
        lo_f, hi_f = freqs[min(95, int(np.searchsorted(cum, 0.1)))], freqs[min(95, int(np.searchsorted(cum, 0.9)))]
        raw.append({"p0": p0, "pk": pk, "end": end, "M": M, "prof": pr / (np.linalg.norm(pr) + 1e-30),
                    "noisiness": noisiness(y, srr, pk * FR, lo_f, hi_f),
                    "t": round(p0 * FR, 2), "peak_t": round(pk * FR, 2), "dur": round((end - p0 + 1) * FR, 2),
                    "attack": round((pk - p0) * FR, 2), "decay": round((end - pk) * FR, 2),
                    "peak_dbfs": round(float(lvl), 1), "above_bed_db": round(float(lvl - bed_in), 1),
                    "low_share": round(float(Rf[lowb].sum() / tot), 2), "high_share": round(float(Rf[highb].sum() / tot), 2),
                    "centroid_hz": int(np.median(cen)), "centroid_slope_oct_s": round(float(np.polyfit(np.arange(len(lc)) * FR, lc, 1)[0]), 2) if len(lc) > 3 else 0.0,
                    "bandwidth": round(float(dom.mean()), 2)})
    # one sound often produces a few onsets while it builds: merge onsets that fall inside an earlier event's
    # attack in overlapping bands
    merged = []
    for ev in raw:
        prev = merged[-1] if merged else None
        if prev and ev["p0"] <= prev["pk"] + 2 and (ev["M"] & prev["M"]).sum() >= 0.3 * min(ev["M"].sum(), prev["M"].sum()):
            prev["M"] = prev["M"] | ev["M"]
            continue
        merged.append(ev)
    # notes and drum hits repeat in a regular rhythm: an onset with two or more look-alikes within +-4 s that
    # fall on a regular grid with it is part of the music, not an edit sound
    keep_raw = []
    for ev in merged:
        p = ev["p0"]
        near = np.where((np.abs(ref_t - p) <= int(4 / FR)) & (np.abs(ref_t - p) >= int(0.1 / FR)))[0]
        sim = [i for i in near if float(ref_on[i][1] @ ev["prof"]) > 0.8]
        rep = False
        if len(sim) >= 2:
            ts_ = np.sort(ref_t[sim]).astype(float)
            ioi = np.diff(np.sort(np.r_[ts_, p]))
            m = float(np.median(ioi)) if len(ioi) else 0.0
            if m > 0:
                regular = np.mean(np.abs(ioi / m - np.round(ioi / m)) < 0.15) >= 0.75
                ph = np.angle(np.exp(2j * np.pi * ts_ / m).mean())  # the grid's phase from the look-alikes
                on_grid = abs(np.angle(np.exp(1j * (2 * np.pi * p / m - ph)))) < 2 * np.pi * 0.12
                louder = onset_db(p) >= float(np.max(ref_lv[sim])) + 6  # an edit sound laid on the beat
                rep = bool(regular and on_grid and not louder)
        ev["on_beat"] = rep
        if ev["above_bed_db"] < 6 and not rep:
            continue
        keep_raw.append(ev)
    events, beat = [], []
    for ev in keep_raw:
        nb = bursts(y, srr, ev["p0"] * FR, min(ev["end"], ev["p0"] + int(1.0 / FR)) * FR)
        if nb >= 3 and ev["low_share"] < 0.4:
            ev.update({"type": "glitch", "bursts": nb})
        else:
            if ev["low_share"] > 0.4:
                ev["low_pitch_fall_oct"] = low_pitch_fall(y, srr, ev["p0"] * FR, ev["end"] * FR)
            ev["type"] = classify(ev)
        for k_ in ("p0", "pk", "end", "M", "prof"):
            ev.pop(k_, None)
        (beat if ev.pop("on_beat") else events).append(ev)
    # repeating on the music's rhythm = notes / drum hits. Kept apart: an edit sound laid exactly on a beat lands
    # here too, and report.py lists the ones that coincide with a cut or a text pop
    out["music_beat_transients"] = beat
    # risers: rising high-band energy over >= 1.2 s that ends in a peak or a sudden drop
    hb = db_(S[freqs > 2000].sum(0))
    hbs = ndimage.uniform_filter1d(hb, int(0.2 / FR))
    L = int(1.2 / FR)
    i = L
    while i < nf - 1:
        x = hbs[i - L:i]
        r = np.corrcoef(np.arange(L), x)[0, 1] if x.std() > 1e-6 else 0
        if r > 0.93 and x[-1] - x[0] > 8 and hbs[i] > -55:
            j = i
            while j < nf - 1 and hbs[j + 1] >= hbs[j] - 0.3 and j - i < int(4 / FR):
                j += 1
            bg = np.percentile(hbs[max(0, j - int(6 / FR)):j], 20)
            a = j
            while a > 0 and hbs[a - 1] > bg + 3 and j - a < int(6 / FR):
                a -= 1
            events.append({"t": round(a * FR, 2), "peak_t": round(j * FR, 2), "dur": round((j - a) * FR, 2),
                           "attack": round((j - a) * FR, 2), "decay": 0.0, "peak_dbfs": round(float(e_tot[j]), 1),
                           "above_bed_db": round(float(hbs[j] - bg), 1), "rise_db": round(float(hbs[j] - bg), 1), "type": "riser"})
            i = j + int(1 / FR)
            continue
        i += 2
    events.sort(key=lambda e: e["t"])
    # a riser's build-up is often also picked as a whoosh: keep the riser (hits and booms that land on its end stay)
    keep = []
    for e in events:
        if e["type"] in ("whoosh", "other", "chime/tonal") and any(r["type"] == "riser" and r["t"] <= e["peak_t"] <= r["peak_t"] + 0.15 for r in events):
            continue
        keep.append(e)
    out["sfx_events"] = keep
    cnt = {}
    for e in keep:
        cnt[e["type"]] = cnt.get(e["type"], 0) + 1
    out["sfx_counts"] = cnt

    # swells: music rising >= 4 dB above its usual level in the same state (speech or pause), so the normal
    # ducking release in a pause is not counted as a swell
    spf = np.repeat(sp, int(round(HOP / FR)))[:nf]
    spf = np.pad(spf, (0, nf - len(spf)), mode="edge")
    base = np.zeros(nf)
    for state in (True, False):
        m = spf == state
        if not m.any():
            continue
        blk = int(1 / FR)
        meds = np.array([np.median(bed_s[i:i + blk][m[i:i + blk]]) if m[i:i + blk].any() else np.nan for i in range(0, nf, blk)])
        run = np.array([np.nanmedian(meds[max(0, j - 10):j + 11]) if np.isfinite(meds[max(0, j - 10):j + 11]).any() else np.nan
                        for j in range(len(meds))])
        run = np.repeat(np.nan_to_num(run, nan=float(np.median(bed_s[m]))), blk)[:nf]
        base[m] = run[m]
    sw = []
    resumed = np.zeros(nf, bool)
    for s0, _ in segs:
        resumed[int(s0 / FR):int((s0 + 1.0) / FR)] = True
    for e in keep + [b for b in beat if b["type"] in ("boom", "sub drop", "riser")]:  # a loud sound lifts the 1 s average: not a swell
        resumed[int(e["t"] / FR):int((e["t"] + e["dur"] + 0.5) / FR)] = True
    for a, b in runs((bed_s - base > 4) & present & ~resumed, FR, 0.6):
        j = a + int(np.argmax(bed_s[a:b] - base[a:b]))
        sw.append({"start": round(a * FR, 2), "peak": round(j * FR, 2), "end": round(b * FR, 2),
                   "rise_db": round(float(bed_s[j] - base[j]), 1), "in_pause": bool(not spf[j])})
    out["swells"] = sw
    mixdb = rms_db(mono(mix), sr, FR)
    sil = [{"start": round(a * FR, 2), "dur": round((b - a) * FR, 2)} for a, b in runs(mixdb[:nf] < -50, FR, 0.3)]
    tot_s = ndimage.uniform_filter1d(e_tot, int(0.3 / FR))
    tmed = ndimage.median_filter(tot_s, size=int(8 / FR) | 1, mode="nearest")
    drop = [{"start": round(a * FR, 2), "dur": round((b - a) * FR, 2), "drop_db": round(float(np.median(tmed[a:b] - tot_s[a:b])), 1)}
            for a, b in runs((tmed - tot_s > 15) & (tmed > -60), FR, 0.35)]
    out["silences"] = {"mix_below_-50dbfs": sil, "music_dropouts": drop}

    music_map(f"{d}/music_map.jpg", S, freqs, segs, music, keep, sw, dur)
    return out


def low_pitch_fall(y, sr, t0, t1):
    """How many octaves the strongest component below 200 Hz falls over the sound (a 'sub drop' falls >= ~1)."""
    a, b = int(t0 * sr), int(t1 * sr)
    if b - a < sr // 4:
        return 0.0
    X = np.abs(librosa.stft(y[a:b], n_fft=8192, hop_length=441))
    f = librosa.fft_frequencies(sr=sr, n_fft=8192)
    band = (f >= 20) & (f <= 200)
    Xb = X[band]
    e = Xb.max(0)
    ok = e > e.max() * 0.1
    if ok.sum() < 4:
        return 0.0
    pk = f[band][np.argmax(Xb, 0)][ok]
    tt = np.arange(X.shape[1])[ok] * 441 / sr
    slope = float(np.polyfit(tt, np.log2(pk), 1)[0])
    return round(-slope * (tt[-1] - tt[0]), 2)


def noisiness(y, sr, t, lo, hi):
    """Spectral flatness (0 tonal .. 1 noise) of the STFT around t, averaged over octave bands between lo and hi
    (the range holding 80 % of the sound's energy), so a coloured noise still reads as noise."""
    a = max(0, int((t - 0.03) * sr))
    X = (np.abs(librosa.stft(y[a:a + int(0.12 * sr)], n_fft=1024, hop_length=256)) ** 2).mean(1)
    f = librosa.fft_frequencies(sr=sr, n_fft=1024)
    lo, hi = max(lo, 60.0), max(hi, lo * 2.01)
    vals, f0 = [], lo
    while f0 < hi:
        m = (f >= f0) & (f < f0 * 2)
        if m.sum() >= 4:
            x = X[m]
            vals.append(np.exp(np.mean(np.log(x + 1e-20))) / (np.mean(x) + 1e-20))
        f0 *= 2
    return round(float(np.mean(vals)), 3) if vals else 0.0


def bursts(y, sr, t0, t1):
    """Separate bursts in a sound (5 ms envelope above 1 kHz, dips >= 6 dB): >= 3 = glitch / stutter."""
    a, b = int(t0 * sr), int(t1 * sr)
    if b - a < int(0.05 * sr):
        return 1
    x = signal.sosfilt(signal.butter(4, 1000, "high", fs=sr, output="sos"), y[a:b])
    h = int(0.005 * sr)
    n = len(x) // h
    e = 10 * np.log10((x[:n * h].reshape(n, h) ** 2).mean(1) + 1e-12)
    pk, _ = signal.find_peaks(e, prominence=6, distance=5, height=e.max() - 12)
    return int(len(pk))


def classify(e):
    if e["dur"] <= 0.2 and e["low_share"] < 0.3:
        return "pop/click"
    if e["low_share"] > 0.4:
        if e["low_share"] >= 0.9 and e["bandwidth"] < 0.12 and e.get("low_pitch_fall_oct", 0) >= 0.8 and e["dur"] >= 0.5:
            return "sub drop"  # a smooth falling sub tone, no impact noise
        if e["attack"] <= 0.12:
            return "boom" if e["decay"] >= 0.25 else "hit"
    if e["bandwidth"] >= 0.15 and e["noisiness"] >= 0.3 and 0.25 <= e["dur"] <= 2.5 and e["attack"] >= 0.08:
        return "whoosh"
    if e["bandwidth"] < 0.1 and e["dur"] >= 0.3:
        return "chime/tonal"
    if e["attack"] <= 0.06:
        return "hit"
    return "other"


def music_map(path, S, freqs, segs, music, sfx, swells, dur):
    """Spectrogram of the music stem in 2-minute rows with speech (blue), music segments (labels), SFX (red),
    swells (yellow) marked: for checking the automatic segmentation by eye."""
    import cv2
    D = librosa.power_to_db(S + 1e-10, ref=np.max)
    D = np.clip((D + 80) / 80, 0, 1)
    row_s, px_s = 120, 10
    rows = int(np.ceil(dur / row_s))
    hgt = 96 * 2
    img = np.zeros((rows * (hgt + 40), row_s * px_s, 3), np.uint8)
    for r in range(rows):
        a, b = int(r * row_s / FR), int(min(dur, (r + 1) * row_s) / FR)
        if b <= a:
            continue
        seg = D[::-1, a:b]
        seg = cv2.resize((seg * 255).astype(np.uint8), (int((b - a) * FR * px_s), hgt), interpolation=cv2.INTER_AREA)
        y0 = r * (hgt + 40) + 30
        img[y0:y0 + hgt, :seg.shape[1]] = cv2.applyColorMap(seg, cv2.COLORMAP_INFERNO)
        X = lambda t: int((t - r * row_s) * px_s)
        for s, e in segs:
            if e > r * row_s and s < (r + 1) * row_s:
                cv2.line(img, (max(0, X(s)), y0 - 4), (min(row_s * px_s - 1, X(e)), y0 - 4), (255, 160, 60), 3)
        for m in music:
            if r * row_s <= m["start"] < (r + 1) * row_s:
                cv2.line(img, (X(m["start"]), y0 - 28), (X(m["start"]), y0 + hgt), (0, 255, 0), 2)
                lab = f"T{m.get('track', '-')} {m.get('tempo_bpm') or ''}bpm {m.get('key', '')}" if m["music"] else "no music"
                cv2.putText(img, lab, (X(m["start"]) + 4, y0 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        for ev in sfx:
            if r * row_s <= ev["t"] < (r + 1) * row_s:
                cv2.line(img, (X(ev["t"]), y0 + hgt - 30), (X(ev["t"]), y0 + hgt), (60, 60, 255), 2)
        for s in swells:
            if r * row_s <= s["peak"] < (r + 1) * row_s:
                cv2.circle(img, (X(s["peak"]), y0 + 10), 6, (0, 230, 255), -1)
        for m in range(0, row_s + 1, 10):
            cv2.putText(img, f"{(r * row_s + m) // 60}:{(r * row_s + m) % 60:02d}", (m * px_s + 2, y0 + hgt + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    cv2.imwrite(path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio_dir")
    ap.add_argument("--words", default=None)
    a = ap.parse_args()
    out = analyse(a.audio_dir, a.words)
    json.dump(out, open(f"{a.audio_dir}/audio_stats.json", "w"), indent=1)
    print(json.dumps({"lufs": out["lufs_integrated"], "voice": {k: v for k, v in out["voice"].items() if not isinstance(v, list)},
                      "levels": {k: v for k, v in out["levels"].items() if k != "per_minute"},
                      "ducking": {k: v for k, v in out["ducking"].items() if not k.startswith("curve")}}, indent=1))
    for m in out["music_segments"]:
        print("music", {k: v for k, v in m.items() if k not in ("chroma_profile", "timbre_profile")})
    print("sfx", out["sfx_counts"], "swells", len(out["swells"]))


if __name__ == "__main__":
    sys.exit(main())
