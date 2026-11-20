"""Beat sync with librosa: choose where the music starts so its beats land on our cuts.
Cuts stay on the spoken words (owner rule: what is said is shown); only the music offset moves.

  python scripts/video/beats.py <music.mp3> <cut seconds, comma separated> [--lo 28 --hi 40]
"""
import sys
import numpy as np


def beat_times(music, sr=22050):
    import librosa
    y, sr = librosa.load(music, sr=sr)
    _, onset = librosa.beat.beat_track(y=y, sr=sr, units="time")
    return np.asarray(onset)


def best_offset(music, cuts, lo=28.0, hi=40.0, step=0.02, beats=None):
    """Music start (s) in [lo, hi] whose beats are nearest the cut times; returns (offset, mean miss in s)."""
    b = beat_times(music) if beats is None else beats
    cuts = np.asarray(sorted(cuts), float)
    best = (lo, 9.0)
    for off in np.arange(lo, hi, step):
        miss = np.abs(b[None, :] - (cuts[:, None] + off)).min(1).mean()
        if miss < best[1]:
            best = (round(float(off), 2), float(miss))
    return best


if __name__ == "__main__":
    a = sys.argv[1:]
    lo = float(a[a.index("--lo") + 1]) if "--lo" in a else 28.0
    hi = float(a[a.index("--hi") + 1]) if "--hi" in a else 40.0
    off, miss = best_offset(a[0], [float(x) for x in a[1].split(",")], lo, hi)
    print(f"start music at {off:.2f}s (cuts miss beats by {miss * 1000:.0f} ms on average)")
