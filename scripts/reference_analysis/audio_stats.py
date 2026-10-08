"""Voice/music stats from demucs stems.
Usage: python audio_stats.py <audio_dir>   (expects demucs/htdemucs/mix/{vocals,no_vocals}.wav)
"""
import sys, json
import numpy as np, soundfile as sf, librosa

d = sys.argv[1]
voc, sr = sf.read(f"{d}/demucs/htdemucs/mix/vocals.wav")
mus, _ = sf.read(f"{d}/demucs/htdemucs/mix/no_vocals.wav")
voc = voc.mean(1) if voc.ndim > 1 else voc
mus = mus.mean(1) if mus.ndim > 1 else mus

hop = int(sr * 0.1)  # 100 ms frames
def db(x):
    r = librosa.feature.rms(y=x, frame_length=hop * 2, hop_length=hop)[0]
    return 20 * np.log10(np.maximum(r, 1e-6))
vdb, mdb = db(voc), db(mus)
n = min(len(vdb), len(mdb)); vdb, mdb = vdb[:n], mdb[:n]
t = np.arange(n) * 0.1

speech = vdb > (vdb.max() - 30)  # voice active
out = {}
out["voice_rms_db_when_speaking"] = round(float(np.median(vdb[speech])), 1)
out["music_rms_db_under_speech"] = round(float(np.median(mdb[speech])), 1)
out["music_rms_db_in_gaps"] = round(float(np.median(mdb[~speech])), 1) if (~speech).any() else None
out["voice_minus_music_db"] = round(out["voice_rms_db_when_speaking"] - out["music_rms_db_under_speech"], 1)
out["speech_fraction"] = round(float(speech.mean()), 3)

# Pauses: runs of non-speech inside the narration span
idx = np.where(speech)[0]
first, last = idx[0], idx[-1]
gaps, run = [], 0
for s in speech[first:last]:
    if not s: run += 1
    else:
        if run: gaps.append(run * 0.1)
        run = 0
gaps = np.array([g for g in gaps if g >= 0.3])
out["narration_start_s"] = round(first * 0.1, 1)
out["narration_end_s"] = round(last * 0.1, 1)
out["pauses_ge_0.3s"] = int(len(gaps))
out["pause_median_s"] = round(float(np.median(gaps)), 2) if len(gaps) else None
out["pause_p90_s"] = round(float(np.percentile(gaps, 90)), 2) if len(gaps) else None
out["pauses_ge_1.5s"] = int((gaps >= 1.5).sum())

# Music loudness timeline (5 s windows) to see builds / drops / track changes
win = 50
tl = [(round(i * 0.1), round(float(np.median(mdb[i:i + win])), 1)) for i in range(0, n, win)]
out["music_db_timeline_5s"] = tl

# Music track-change candidates: chroma + timbre novelty on the music stem
y = librosa.resample(mus.astype(np.float32), orig_sr=sr, target_sr=22050)
chroma = librosa.feature.chroma_cqt(y=y, sr=22050, hop_length=2048)
mfcc = librosa.feature.mfcc(y=y, sr=22050, hop_length=2048, n_mfcc=13)
feat = np.vstack([librosa.util.normalize(chroma, axis=0), librosa.util.normalize(mfcc, axis=1)])
# smooth to ~4 s, then novelty = distance between consecutive 8 s windows
fps = 22050 / 2048
w = int(8 * fps)
nov = []
for i in range(w, feat.shape[1] - w):
    a, b = feat[:, i - w:i].mean(1), feat[:, i:i + w].mean(1)
    nov.append(np.linalg.norm(a - b))
nov = np.array(nov)
peaks = librosa.util.peak_pick(nov, pre_max=int(10 * fps), post_max=int(10 * fps), pre_avg=int(10 * fps), post_avg=int(10 * fps), delta=np.std(nov) * 0.8, wait=int(20 * fps))
out["music_change_candidates_s"] = [round((p + w) / fps, 1) for p in peaks]

# Tempo / key feel of music bed
tempo, _ = librosa.beat.beat_track(y=y, sr=22050)
out["music_tempo_bpm_est"] = round(float(np.atleast_1d(tempo)[0]), 1)
out["music_key_profile"] = [round(float(x), 2) for x in chroma.mean(1)]

# Voice pitch (expressiveness) on a 120 s sample
vy = librosa.resample(voc.astype(np.float32), orig_sr=sr, target_sr=16000)
seg = vy[int(60 * 16000):int(180 * 16000)]
f0, vflag, _ = librosa.pyin(seg, fmin=60, fmax=400, sr=16000, frame_length=1024)
f0 = f0[~np.isnan(f0)]
out["voice_f0_median_hz"] = round(float(np.median(f0)), 1)
out["voice_f0_std_semitones"] = round(float(np.std(12 * np.log2(f0 / np.median(f0)))), 2)

json.dump(out, open(f"{d}/audio_stats.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "music_db_timeline_5s"}, indent=1))
print("timeline:", out["music_db_timeline_5s"])
