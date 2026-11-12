"""Mix voiceover + music bed + sound effects into out/mix.wav (48 kHz stereo float).

Music is ducked under the voice, dips to silence on the black beat before each chapter card,
and every SFX cue from sfx.json is placed sample-accurately. Loudness is mastered afterwards with ffmpeg.
"""
import json
import os
import subprocess

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
SR = 48000
LIB = os.path.join(ROOT, 'audio', 'lib')
OUT = os.path.join(ROOT, 'out')
os.makedirs(OUT, exist_ok=True)
edit = json.load(open(os.path.join(ROOT, 'remotion', 'src', 'edit.json')))
TOTAL = edit['durationInFrames'] / 30.0
N = int(TOTAL * SR)


def decode(path, ss=0.0, t=None):
    cmd = ['ffmpeg', '-v', 'error', '-ss', '%.3f' % ss, '-i', path]
    if t:
        cmd += ['-t', '%.3f' % t]
    cmd += ['-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def db(x):
    return 10 ** (x / 20)


# ---------------- voice: clean, compress, then normalise to about -16 LUFS ----------------
vo = os.path.join(OUT, 'voice_proc.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(ROOT, 'audio', 'voiceover.mp3'), '-af',
                'highpass=f=75,lowpass=f=15000,acompressor=threshold=0.08:ratio=3.5:attack=4:release=110:knee=4:makeup=2.5,'
                'acompressor=threshold=0.25:ratio=8:attack=1:release=40:makeup=1',
                '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_f32le', vo], check=True)
m = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-i', vo, '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
vl = float(m.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])
voice = decode(vo)
v = np.zeros((N, 2), np.float32)
v[:min(N, len(voice))] = voice[:N]
v *= db(-16.0 - vl)
print('voice after compression %.1f LUFS -> gain %.1f dB' % (vl, -16.0 - vl))

# ---------------- music sections: (file, offset_s, start_s, end_s, gain_db) ----------------
SECTIONS = [
    ('Hitman.mp3', 11.5, 0.0, 55.6, -12.0),
    ('Darkest_Child.mp3', 2.0, 55.6, 152.8, -11.0),
    ('Gathering_Darkness.mp3', 1.0, 152.8, 288.4, -8.5),
    ('Echoes_of_Time_v2.mp3', 0.0, 288.4, 410.2, -10.0),
    ('Lightless_Dawn.mp3', 150.0, 410.2, 498.7, -1.0),
    ('Long_Note_Four.mp3', 0.0, 498.7, 600.8, 4.0),
    ('Crypto.mp3', 0.0, 600.8, TOTAL, -10.5),
]
XF = 1.2
music = np.zeros((N, 2), np.float32)
for fname, off, a, b, g in SECTIONS:
    dur = b - a + XF
    seg = decode(os.path.join(LIB, fname), off, dur) * db(g)
    n = len(seg)
    ramp_in = int(0.6 * SR) if a > 0 else int(0.05 * SR)
    ramp_out = int(XF * SR)
    env = np.ones(n, np.float32)
    env[:ramp_in] = np.sin(np.linspace(0, np.pi / 2, ramp_in)) ** 2
    if n > ramp_out:
        env[-ramp_out:] = np.cos(np.linspace(0, np.pi / 2, ramp_out)) ** 2
    s = int(a * SR)
    e = min(N, s + n)
    music[s:e] += seg[:e - s] * env[:e - s, None]

# dips: silence the bed on the flash/black beat before cards, return with the impact
dip = np.ones(N, np.float32)
for sc in edit['scenes']:
    if sc['kind'] == 'flash':
        s = int(sc['from'] / 30 * SR)
        e = int((sc['from'] + 14) / 30 * SR)  # flash + black lasts 14 frames
        fall = int(0.08 * SR)
        rise = int(0.35 * SR)
        dip[s:e] = 0.0
        dip[max(0, s - fall):s] = np.minimum(dip[max(0, s - fall):s], np.linspace(1, 0, s - max(0, s - fall)))
        dip[e:e + rise] = np.minimum(dip[e:e + rise], np.linspace(0, 1, len(dip[e:e + rise])))
# the final black: fade the bed out over the last 2.2 s
tail = int(2.2 * SR)
dip[-tail:] *= np.linspace(1, 0, tail)
music *= dip[:, None]

# ducking: music drops ~7 dB while the voice is speaking (10 ms attack, 350 ms release)
mono = np.abs(v.mean(1))
win = int(0.03 * SR)
env = np.sqrt(np.convolve(mono ** 2, np.ones(win) / win, mode='same'))
att, rel = np.exp(-1 / (0.01 * SR)), np.exp(-1 / (0.35 * SR))
sm = np.empty_like(env)
acc = 0.0
# vectorised one-pole follower is awkward; process in blocks of 1 ms for speed
blk = SR // 1000
envb = env[: len(env) // blk * blk].reshape(-1, blk).max(1)
smb = np.empty_like(envb)
a1, r1 = np.exp(-1 / (0.01 * 1000)), np.exp(-1 / (0.35 * 1000))
for i, x in enumerate(envb):
    acc = a1 * acc + (1 - a1) * x if x > acc else r1 * acc + (1 - r1) * x
    smb[i] = acc
sm = np.repeat(smb, blk)
sm = np.pad(sm, (0, N - len(sm)), mode='edge')
ref = np.percentile(smb[smb > 1e-4], 60)
duck = db(-7.0 * np.clip(sm / ref, 0, 1))
music *= duck[:, None].astype(np.float32)

# ---------------- sound effects ----------------
sfx = np.zeros((N, 2), np.float32)
cache = {}
for c in json.load(open(os.path.join(ROOT, 'sfx.json'))):
    if c['file'] not in cache:
        cache[c['file']] = decode(c['file'])
    clip = cache[c['file']] * db(c['db'])
    s = int(c['t'] * SR)
    e = min(N, s + len(clip))
    if s < N:
        sfx[s:e] += clip[:e - s]

mix = v + music + sfx * db(-3.0)
print('pre-master peak %.2f dBFS' % (20 * np.log10(np.abs(mix).max() + 1e-9)))
raw = os.path.join(OUT, 'mix.f32')
mix.astype('<f4').tofile(raw)
src = ['-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', raw]
# master: static gain to -14 LUFS, then a look-ahead limiter at -1.5 dBFS
m = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', *src, '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
il = float(m.split('Integrated loudness:')[1].split('I:')[1].split('LUFS')[0])
g = -14.0 - il
subprocess.run(['ffmpeg', '-v', 'error', '-y', *src, '-af',
                'volume=%.2fdB,alimiter=limit=0.84:attack=3:release=60:level=disabled' % g,
                '-c:a', 'pcm_s24le', os.path.join(OUT, 'mix.wav')], check=True)
os.remove(raw)
print('premaster %.1f LUFS, gain %.1f dB -> out/mix.wav %.1fs' % (il, g, N / SR))
