"""Turn plan.py + transcript + collected assets into remotion/src/edit.json, sfx.json and music.json.

Also prepares media into remotion/public/a/: cut archival clips, processed stills.
Usage: python3 build_edit.py [--no-media]
"""
import json
import os
import random
import re
import subprocess
import sys
import urllib.parse

from PIL import Image, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import plan  # noqa: E402

FPS = 30
PUB = os.path.join(ROOT, 'remotion', 'public')
A = os.path.join(PUB, 'a')
ARCH = os.path.join(ROOT, 'assets', 'archive')
IMGDIR = os.path.join(ROOT, 'assets', 'img')
WIKIDIR = os.path.join(ROOT, 'assets', 'wiki')
NO_MEDIA = '--no-media' in sys.argv
for d in ('clip', 'img'):
    os.makedirs(os.path.join(A, d), exist_ok=True)
os.makedirs(WIKIDIR, exist_ok=True)

CROPS = {'MDE': 'crop=1232:720:24:0', 'EIC': 'crop=606:478:24:2', 'WAY': 'crop=638:476:0:2', 'NAR': 'null', 'NUR': 'null'}
FLASH_WORDS = {'THE TWIST', 'THE REFRAME', 'THE WARNING', '2 QUESTIONS', '3 LEVELS'}
F = lambda t: int(round(t * FPS))  # noqa: E731

# ------------------------------------------------------------------ words + captions
segs = json.load(open(os.path.join(ROOT, 'transcript.json')))
words = []
for si, s in enumerate(segs):
    for wi, w in enumerate(s['words']):
        txt = w['w']
        if txt in plan.FIXES and not (txt == 'psychiatrist' and si != 96):
            txt = plan.FIXES[txt]
        if si == 40 and txt == 'you' and wi + 1 < len(s['words']) and s['words'][wi + 1]['w'] == 'either':
            txt = "you're"
        if txt.startswith('-') and words:
            words[-1]['w'] += txt
            words[-1]['e'] = w['e']
            continue
        words.append({'w': txt, 's': w['s'], 'e': w['e']})
starts = [w['s'] for w in words]


def snap(t):
    best = min(starts, key=lambda s: abs(s - t))
    return best if abs(best - t) <= 0.25 else t


def phrases():
    out, cur = [], []
    for i, w in enumerate(words):
        if cur:
            prev = cur[-1]
            chars = sum(len(x['w']) + 1 for x in cur)
            if (len(cur) >= 4 or chars + len(w['w']) > 22 or w['s'] - prev['e'] > 0.35
                    or (prev['w'][-1] in '.?!' ) or (prev['w'][-1] in ',;:' and len(cur) >= 2)):
                out.append(cur)
                cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    caps = []
    for k, ph in enumerate(out):
        a = ph[0]['s']
        nxt = out[k + 1][0]['s'] if k + 1 < len(out) else ph[-1]['e'] + 0.6
        b = min(nxt, ph[-1]['e'] + 0.6)
        text = ' '.join(x['w'] for x in ph).rstrip(',.;:')
        caps.append((a, b, text))
    return caps


# ------------------------------------------------------------------ media preparation
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('FAILED:', ' '.join(cmd)[:200], r.stderr[-400:])
    return r


def prep_clip(spec, dur_f):
    src, sec = spec.split(':')
    sec = float(sec)
    out = 'a/clip/%s_%s_%d.mp4' % (src, ('%g' % sec).replace('.', 'p'), dur_f)
    dst = os.path.join(PUB, out)
    if NO_MEDIA or os.path.exists(dst):
        return out
    vf = '%s,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p' % CROPS[src]
    run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.3f' % sec, '-i', os.path.join(ARCH, plan.CLIPS[src]), '-t', '%.3f' % (dur_f / FPS + 0.4),
         '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-g', '15', dst])
    return out


def fit_cover(im, centering=(0.5, 0.38)):
    return ImageOps.fit(im.convert('RGB'), (2112, 1188), Image.LANCZOS, centering=centering)


def fit_contain_blur(im):
    im = im.convert('RGB')
    bg = ImageOps.fit(im, (2112, 1188), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    bg = Image.eval(bg, lambda v: int(v * 0.35))
    fg = ImageOps.contain(im, (2112, 1120), Image.LANCZOS)
    bg.paste(fg, ((2112 - fg.width) // 2, (1188 - fg.height) // 2))
    return bg


def save_img(src_path, out_rel, mode='cover'):
    dst = os.path.join(PUB, out_rel)
    if NO_MEDIA or os.path.exists(dst):
        return out_rel
    try:
        im = Image.open(src_path)
        im = fit_contain_blur(im) if mode == 'contain' else fit_cover(im)
        im.save(dst, quality=90)
    except Exception as e:
        print('IMAGE FAILED', src_path, e)
        Image.new('RGB', (2112, 1188), (10, 0, 0)).save(dst)
    return out_rel


IMG_INDEX = json.load(open(os.path.join(IMGDIR, 'index.json')))
PICKS = json.load(open(os.path.join(ROOT, 'picks.json'))) if os.path.exists(os.path.join(ROOT, 'picks.json')) else {}
MISSING = []


def prep_img(q, k=1):
    ent = IMG_INDEX.get(q) or {}
    combined = (ent.get('cands') or [])[:3] + (ent.get('ov') or [])[:4]
    if not combined:
        MISSING.append(q)
        return 'a/img/_missing.jpg'
    k = min(max(1, k), len(combined))
    c = combined[k - 1]
    return save_img(os.path.join(IMGDIR, c['file']), 'a/img/%s_p%d.jpg' % (ent['id'], k))


GENDIR = os.path.join(ROOT, 'assets', 'gen')


def prep_gen(key):
    src = os.path.join(GENDIR, key + '.jpg')
    if not os.path.exists(src):
        MISSING.append('gen:' + key)
        return 'a/img/_missing.jpg'
    return save_img(src, 'a/img/gen_%s.jpg' % key)


def prep_wiki(key):
    title = plan.WIKI[key]
    raw = os.path.join(WIKIDIR, key + '.img')
    if not os.path.exists(raw):
        url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url', 'iiurlwidth': 1280, 'format': 'json'})
        for _ in range(4):
            r = run(['curl', '-s', '-A', 'AxiomVideoEditor/0.1 (research script)', '--max-time', '30', url])
            try:
                page = next(iter(json.loads(r.stdout)['query']['pages'].values()))
                ii = page['imageinfo'][0]
                u = ii.get('thumburl') or ii['url']
                run(['curl', '-sL', '-A', 'AxiomVideoEditor/0.1 (research script)', '--max-time', '60', '-o', raw, u])
                break
            except Exception:
                subprocess.run(['sleep', '8'])
    mode = 'contain' if key in ('ad', 'scream', 'milgram', 'milgram_young') else 'cover'
    return save_img(raw, 'a/img/wiki_%s.jpg' % key, mode=mode)


def bgspec(bg, dur_f):
    if not bg:
        return None
    if bg == 'laser':
        return 'laser'
    if bg.startswith('img:'):
        return {'src': prep_img(bg[4:])}
    if bg.startswith('gen:'):
        return {'src': prep_gen(bg[4:])}
    if bg.startswith('wiki:'):
        return {'src': prep_wiki(bg[5:])}
    return {'src': prep_clip(bg, dur_f), 'video': True}


# ------------------------------------------------------------------ apply visual picks
import picks  # noqa: E402
ORDER = json.load(open(os.path.join(ROOT, 'review', 'pick_order.json')))
QIDX = {q: i for i, q in enumerate(ORDER)}
beats = []
for (t, kind, arg, opts) in sorted(plan.B, key=lambda b: b[0]):
    o = dict(opts)
    if t in picks.BG_R:
        o['bg'] = picks.BG_R[t]
    r = None
    if kind == 'img':
        r = picks.R.get(QIDX.get(arg))
    elif kind == 'wiki':
        r = picks.WIKI_R.get(t)
    if r is None:
        if kind == 'img':
            print('NO PICK for', t, arg)
        beats.append((t, kind, arg, o))
        continue
    rk = r[0]
    if rk == 'remove':
        continue
    if rk == 'img':
        beats.append((t, 'imgpick', (arg, r[1]), o))
    elif rk == 'imgof':
        beats.append((t, 'imgpick', (ORDER[r[1]], r[2]), o))
    elif rk == 'gen':
        beats.append((t, 'gen', r[1], o))
    elif rk == 'clip':
        beats.append((t, 'clip', r[1], o))
    elif rk in ('gfx', 'word', 'type'):
        o2 = {k: v for k, v in o.items() if k in ('sfx',)} if rk != 'gfx' else {}
        o2.update(r[2] if len(r) > 2 else {})
        beats.append((t, rk, r[1], o2))

# ------------------------------------------------------------------ scenes
times = [b[0] if b[1] in ('black',) else snap(b[0]) for b in beats]
END_F = F(plan.END)
scenes = []
for i, (t0, kind, arg, opts) in enumerate(beats):
    a = F(times[i])
    b = F(times[i + 1]) if i + 1 < len(beats) else END_F
    if b - a < 6:
        print('WARNING very short beat at %.2f (%d frames): %s %s' % (times[i], b - a, kind, arg))
    sc = {'from': a, 'dur': b - a, 't': times[i], 'kind': kind, 'opts': opts, 'arg': arg}
    scenes.append(sc)

# flash + black before chapter cards and section titles
final = []
for i, sc in enumerate(scenes):
    if sc['kind'] == 'card' or (sc['kind'] == 'word' and sc['arg'] in FLASH_WORDS):
        if final and final[-1]['dur'] > 24:
            prev = final[-1]
            cut = 14
            prev['dur'] -= cut
            final.append({'from': prev['from'] + prev['dur'], 'dur': 2, 'kind': 'flash', 'opts': {}, 'arg': '', 't': 0})
            final.append({'from': prev['from'] + prev['dur'] + 2, 'dur': cut - 2, 'kind': 'black', 'opts': {}, 'arg': '', 't': 0})
    final.append(sc)
scenes = final

out_scenes = []
for sc in scenes:
    kind, arg, o, dur = sc['kind'], sc['arg'], sc['opts'], sc['dur']
    base = {'from': sc['from'], 'dur': dur}
    if kind == 'clip':
        base.update(kind='media', src=prep_clip(arg, dur), video=True, grade=o.get('grade', 'ink'), motion=o.get('motion'))
    elif kind == 'img':
        base.update(kind='media', src=prep_img(arg), grade=o.get('grade', 'ink'), motion=o.get('motion'))
    elif kind == 'imgpick':
        base.update(kind='media', src=prep_img(arg[0], arg[1]), grade=o.get('grade', 'ink'), motion=o.get('motion'))
    elif kind == 'gen':
        base.update(kind='media', src=prep_gen(arg), grade=o.get('grade', 'ink'), motion=o.get('motion'))
    elif kind == 'wiki':
        base.update(kind='media', src=prep_wiki(arg), grade=o.get('grade', 'ink'), motion=o.get('motion'))
    elif kind == 'word':
        base.update(kind='word', big=arg, small=o.get('small'), color=o.get('color', 'red'), bg=bgspec(o.get('bg'), dur))
    elif kind == 'type':
        base.update(kind='type', text=arg, sub=o.get('sub'), bg=bgspec(o.get('bg'), dur))
    elif kind == 'carousel':
        base.update(kind='carousel', big=arg, small=o.get('small'), bg=bgspec(o.get('bg'), dur))
    elif kind == 'card':
        base.update(kind='card', label=o.get('label', ''), num=o.get('num', ''), title=arg, icon=o.get('icon', 'eye'))
    elif kind == 'gfx':
        g = {k: v for k, v in o.items() if k not in ('sfx',)}
        if 'marks' in g:
            g['marksF'] = [F(m - sc['t']) for m in g.pop('marks')]
        if 'breakAt' in g:
            g['breakAtF'] = F(g.pop('breakAt') - sc['t'])
        if 'actualAt' in g:
            g['actualAtF'] = F(g.pop('actualAt') - sc['t'])
        base.update(kind='gfx', name=arg, **g)
    else:
        base.update(kind=kind)
    out_scenes.append(base)

# ------------------------------------------------------------------ captions (hidden over titles/cards)
HIDE = {'word', 'type', 'carousel', 'card', 'black', 'flash'}
HIDE_GFX = {'counter', 'voltmeter', 'prediction', 'variations', 'split', 'voltsteps'}
LOW_GFX = {'shockpanel', 'staircase', 'pilllabel'}
captions = []
for a_s, b_s, text in phrases():
    a, b = F(a_s), F(b_s)
    for sc in out_scenes:
        s0, s1 = sc['from'], sc['from'] + sc['dur']
        lo, hi = max(a, s0), min(b, s1)
        if hi - lo < 8:
            continue
        if sc['kind'] in HIDE or (sc['kind'] == 'gfx' and sc['name'] in HIDE_GFX):
            continue
        low = sc['kind'] == 'gfx' and sc['name'] in LOW_GFX
        captions.append({'from': lo, 'dur': hi - lo, 'text': text, 'low': low})

edit = {'durationInFrames': END_F, 'scenes': out_scenes, 'captions': captions}
json.dump(edit, open(os.path.join(ROOT, 'remotion', 'src', 'edit.json'), 'w'), indent=0)

# ------------------------------------------------------------------ sound effects
SFXD = os.path.join(ROOT, 'audio', 'sfx')
S = {
    'impact': ('cinematic_whoosh_deep_impact.mp3', -6), 'boom': ('big_cinematic_impact.mp3', -6),
    'hit': ('hard_horror_hit_drum.mp3', -9), 'whoosh': ('cinematic_whoosh_fast_transition.mp3', -10),
    'glitch': ('glitch_static.mp3', -11), 'shock': ('heavy_electric_shockwave_impact.mp3', -8),
    'buzz': ('wrong_electricity_buzz.mp3', -11), 'bell': ('typewriter_return_bell.mp3', -10),
    'click': ('electric_switch.mp3', -8), 'tick': ('quick_switch_click.mp3', -16),
    'fence': ('short_electric_fence_buzz.mp3', -12), 'heart': ('human_single_heart_beat.mp3', -4),
    'static': ('radio_static_fx.mp3', -12), 'card': ('movie_trailer_epic_impact.mp3', -6),
    'type': ('typewriter_soft_click.mp3', -15), 'blast': ('electricity_lightning_blast.mp3', -9),
    'swoosh': ('fast_whoosh_transition.mp3', -13),
}
cues = []


def cue(t, key, extra_db=0.0):
    f, db = S[key]
    cues.append({'t': round(max(0.0, t), 3), 'file': os.path.join(SFXD, f), 'db': db + extra_db})


rnd = random.Random(7)
for sc in scenes:
    t = sc['from'] / FPS
    d = sc['dur'] / FPS
    o, kind, arg = sc['opts'], sc['kind'], sc['arg']
    sfx = o.get('sfx', '')
    if kind == 'flash':
        cue(t, 'glitch')
        continue
    if kind == 'card':
        cue(t, 'card')
    if kind == 'carousel':
        cue(t - 0.1, 'whoosh')
    if kind == 'type':
        cps = max(22, len(arg) / 0.85)
        n = len(arg)
        for k in range(0, n, 2):
            if arg[k] != ' ':
                cue(t + k / cps, 'type', rnd.uniform(-3, 1))
    if kind == 'word' and not sfx:
        cue(t - 0.08, 'swoosh')
    if kind == 'gfx' and arg == 'counter' and not sfx:
        cue(t, 'swoosh')
    if kind == 'gfx' and arg == 'voltmeter' and not sfx:
        cue(t, 'fence')
    if kind == 'gfx' and arg == 'staircase' and o.get('all'):
        for k in range(30):
            cue(t + (k / 30) * 0.7 * d, 'tick', -2)
    if not sfx:
        continue
    if sfx in ('impact', 'boom', 'hit', 'glitch', 'shock', 'buzz', 'bell', 'static', 'click'):
        cue(t, sfx)
    elif sfx == 'whoosh':
        cue(t - 0.12, 'whoosh')
    elif sfx == 'clicks':
        for k in range(30):
            cue(t + (k / 30) * 0.75 * d, 'tick')
    elif sfx == 'clicks3':
        for fr in (0.12, 0.42, 0.72):
            cue(t + fr * d, 'click')
    elif sfx == 'clicksAll':
        for k in range(30):
            cue(t + (k / 30) * 0.85 * d, 'tick')
        cue(t + 0.85 * d, 'blast')
    elif sfx.startswith('click_at:'):
        cue(float(sfx.split(':')[1]), 'click')
    elif sfx == 'clickbuzz':
        cue(t, 'click')
        cue(t + 0.12, 'fence')
    elif sfx == 'thuds':
        for dt in (0.0, 0.42, 0.84):
            cue(t + dt, 'hit', -2)
    elif sfx == 'heartbeat':
        cue(t + 0.2, 'heart')
        cue(t + 1.15, 'heart')
    elif sfx == 'stepclicks':
        for m in o.get('marks', []):
            cue(m, 'click')
    elif sfx == 'boom_end':
        cue(t + len(arg) / max(22, len(arg) / 0.85) + 0.1, 'boom')
    elif sfx == 'cutsnap':
        cue(t + 0.35 * d, 'click', 2)
        cue(t + 0.35 * d, 'glitch')
        cue(t + 0.35 * d + 0.25, 'hit', -3)
    elif sfx == 'ring':
        cue(t, 'static')
json.dump(sorted(cues, key=lambda c: c['t']), open(os.path.join(ROOT, 'sfx.json'), 'w'), indent=0)

print('scenes:', len(out_scenes), ' captions:', len(captions), ' sfx cues:', len(cues), ' frames:', END_F)
print('missing image queries:', MISSING)
