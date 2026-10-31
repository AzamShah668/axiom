"""Image candidates from Openverse (openly licensed images, keyword search, no key needed).

Adds up to 4 candidates per plan query under index[q]['ov'], using a short keyword query.
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
import fetch_images as F  # noqa: E402

SHORT = {
    'New Haven Connecticut 1960s street black and white photo': 'New Haven 1960s',
    '1960s men walking city street black and white photo': '1960s street men',
    'ordinary working men 1960s black and white portrait': '1960s men portrait',
    'man staring at his reflection in mirror dark illustration': 'man mirror reflection',
    'old wall clock black and white dark': 'old wall clock',
    '1960s men group portrait black and white photo': '1960s group of men',
    '1960s teacher classroom chalkboard black and white photo': '1960s classroom teacher',
    '1960s engineer drafting table black and white photo': 'engineer drafting',
    '1960s factory laborer worker black and white photo': 'factory worker 1960s',
    'fist pounding on wall dark black and white': 'fist',
    'man whispering secret in ear dark illustration': 'whisper',
    'office meeting boss table dark illustration': 'office meeting 1960s',
    'military officer uniform cap portrait black and white photo': 'military officer portrait',
    'human brain wires circuit dark red illustration': 'brain circuit',
    'surreal dark staircase three steps illustration': 'dark staircase',
    'empty hospital corridor night black and white': 'hospital corridor night',
    'stranger in hat and coat silhouette street night': 'man in hat silhouette night',
    'faceless businessman suit dark illustration': 'faceless man suit',
    'white lab coat hanging on hook dark': 'lab coat',
    'Yale University seal emblem': 'Yale University',
    'vintage clipboard with paper black and white': 'clipboard',
    'authority figure silhouette judge dark illustration': 'judge',
    'police badge close up black and white': 'police badge',
    'judge gavel black and white dark': 'gavel',
    'military medals on uniform close up black and white': 'military medals',
    'empty suit hanging dark room': 'suit hanging',
    'cut puppet strings marionette dark illustration': 'marionette strings',
    'person climbing endless stairs dark surreal illustration': 'endless stairs',
    'escher impossible staircase illustration': 'impossible staircase',
    'man climbing stairs into darkness silhouette': 'stairs silhouette',
    'person dissolving into smoke dark illustration': 'smoke portrait',
    'finger on lips silence black and white dark': 'finger on lips',
    'man disintegrating into particles dark': 'disintegration',
    'atlas carrying heavy weight on shoulders dark illustration': 'Atlas statue',
    'smoke rising upward dark': 'smoke black background',
    'puppet master hand controlling marionette strings dark illustration': 'puppeteer hand',
    'marionette puppet man dark': 'marionette',
    'vintage surgical instruments black and white': 'surgical instruments',
    'vintage hospital ward 1960s black and white photo': 'hospital ward',
    'empty hospital corridor night black and white photo': 'hospital corridor',
    '1960s psychiatrist doctor portrait black and white photo': 'doctor portrait 1960s',
    '1960s nurse hospital night shift black and white photo': 'nurse 1960s',
    'nurse station night 1960s black and white photo': 'nurses station',
    'hospital ward beds 1960s black and white photo': 'hospital beds',
    'hospital patient in bed 1960s black and white photo': 'patient hospital bed',
    'vintage hospital medicine cabinet black and white': 'medicine cabinet',
    'nurse filling syringe vintage black and white photo': 'syringe',
    'hand grabbing wrist stop dark': 'hand grabbing wrist',
    'patient sleeping hospital bed black and white': 'sleeping patient',
    'faceless person fading away dark illustration': 'ghost portrait',
    'hands in surgical gloves dark': 'surgical gloves',
    'nurses group 1960s black and white photo': 'nurses',
    'nursing students classroom 1960s black and white photo': 'nursing students',
    'vintage questionnaire paper form': 'questionnaire',
    'old rule book open dark': 'old book',
    'woman looking into broken mirror dark': 'broken mirror',
    'audience silhouettes watching dark': 'audience silhouette',
    'hand pointing finger accusing dark illustration': 'pointing finger',
    'man walking away into light silhouette': 'walking into the light',
    'monster shadow silhouette dark illustration': 'monster shadow',
    '1960s psychiatrists conference black and white photo': 'psychiatrists',
    'crystal ball fortune teller dark vintage': 'crystal ball',
    'sinister smile dark illustration': 'sinister smile',
    'broken man shattered portrait dark': 'shattered face',
    'shattered mirror reflection dark': 'shattered mirror',
    'old handwritten notes notebook black and white': 'handwritten notes',
    'biting lip close up dark': 'biting lip',
    'creepy smiling mask dark': 'creepy mask',
    'pressure gauge needle red zone': 'pressure gauge',
    'closed eye close up black and white': 'closed eye',
    'wide open eye close up dark': 'eye macro',
    'screaming man dark painting': 'scream',
    'blindfolded man dark illustration': 'blindfolded',
    'person watching screen alone dark room silhouette': 'person watching screen dark',
    'anatomical heart dark red illustration': 'anatomical heart',
    'cracked shield dark': 'shield',
    'old light switch off dark': 'light switch',
    'angel and devil on shoulders dark illustration': 'angel and devil',
    'vintage radio microphone broadcast black and white': 'vintage microphone',
    'man shouting megaphone dark': 'megaphone',
    'monster shadow on wall behind man dark': 'shadow on wall',
    'werewolf transformation shadow dark illustration': 'werewolf',
    'hourglass sand dark': 'hourglass',
    'hand raised stop gesture dark': 'stop hand',
    'small notebook in coat pocket vintage': 'notebook pocket',
    'empty room single chair spotlight dark': 'empty chair',
    'man sitting alone dark room window light': 'alone window',
    'marionette strings attached to hands dark illustration': 'puppet hands',
    'soldier silhouette battlefield smoke dark': 'soldier silhouette',
    'man fading into shadow dark illustration': 'man in shadows',
    'small footsteps in snow dark': 'footprints snow',
    'vintage rubber date stamp on document': 'rubber stamp',
    'phishing email on laptop screen dark': 'phishing',
    'urgent bank transfer warning red screen': 'warning screen',
    'dominoes falling in a row dark': 'dominoes falling',
    'stacked wooden blocks tower dark': 'jenga',
    'hand stopping falling dominoes': 'dominoes',
    'man standing up speaking in meeting illustration': 'meeting speaking',
    'man walking away from staircase silhouette': 'walking away silhouette',
    'broken chains dark': 'broken chain',
    'one red figure among gray crowd illustration': 'red umbrella crowd',
    'shabby run down office 1960s black and white': 'old office',
    'white lab coat on hanger dark background': 'lab coat hanger',
    'crowd of people agreeing nodding illustration': 'crowd',
    'puppet breaking free cutting strings illustration': 'puppet',
    'climber on mountain summit silhouette dark': 'summit silhouette',
    'hourglass running out dark': 'hourglass sand',
    'height measuring chart wall vintage': 'height chart',
    'long corridor many doors dark': 'corridor doors',
    'two silhouettes standing side by side dark': 'two silhouettes',
    'one person standing out from crowd red illustration': 'standing out crowd',
    'empty silhouette head dark illustration': 'head silhouette',
    'two people walking together silhouette black and white': 'two people walking silhouette',
    'friends standing together silhouette dusk': 'friends silhouette',
    'hand offering pen to sign contract dark': 'signing contract',
    'city street at night 1960s black and white': 'city street night',
    'crowd of ordinary people 1960s black and white photo': 'crowd 1960s',
    'glowing light bulb in dark room': 'light bulb',
    'man falling into darkness silhouette': 'falling man',
    # replacements for Wikimedia files that were rate-limited
    'wiki:yale': 'Yale Old Campus',
    'wiki:milgram_young': 'Stanley Milgram',
}


def search(q):
    url = 'https://api.openverse.org/v1/images/?' + urllib.parse.urlencode({'q': q, 'page_size': 20, 'size': 'large'})
    for wait in (0, 5, 15):
        time.sleep(wait)
        r = subprocess.run(['curl', '-s', '-A', 'AxiomVideoEditor/0.1', '--max-time', '30', url], capture_output=True, text=True)
        try:
            return json.loads(r.stdout).get('results', [])
        except Exception:
            continue
    return []


def _dl(args):
    n, res, i = args
    u = res.get('url') or ''
    ext = os.path.splitext(urllib.parse.urlparse(u).path)[1].lower()
    ext = ext if ext in ('.jpg', '.jpeg', '.png', '.webp') else '.jpg'
    dst = os.path.join(F.OUT, '%s_ov%d%s' % (i, n, ext))
    subprocess.run(['curl', '-sL', '-A', F.UA, '--max-time', '40', '--max-filesize', '15000000', '-o', dst, u], capture_output=True)
    pw, ph = F.probe(dst)
    if pw >= 800 and ph >= 450:
        return {'file': os.path.basename(dst), 'w': pw, 'h': ph, 'url': u, 'title': res.get('title', ''),
                'license': res.get('license'), 'creator': res.get('creator')}
    if os.path.exists(dst):
        os.remove(dst)
    return None


def fetch(key, q):
    import concurrent.futures as cf
    i = F.qid(key)
    ok = []
    for res in search(q):
        w, h = res.get('width') or 0, res.get('height') or 0
        if w and h and (w < 900 or h < 500 or not 0.6 <= w / h <= 2.6):
            continue
        ok.append(res)
        if len(ok) >= 6:
            break
    with cf.ThreadPoolExecutor(6) as ex:
        got = [g for g in ex.map(_dl, [(n + 1, r, i) for n, r in enumerate(ok)]) if g]
    return got[:4]


if __name__ == '__main__':
    index = json.load(open(os.path.join(F.OUT, 'index.json')))
    keys = F.queries() + ['wiki:yale', 'wiki:milgram_young']
    for n, key in enumerate(keys):
        q = SHORT.get(key, key)
        got = fetch(key, q)
        ent = index.setdefault(key, {'id': F.qid(key), 'cands': []})
        ent['ov'] = got
        json.dump(index, open(os.path.join(F.OUT, 'index.json'), 'w'), indent=1)
        print('%3d/%d  ov=%d ddg=%d  %s  [%s]' % (n + 1, len(keys), len(got), len(ent.get('cands', [])), key[:60], q), flush=True)
        time.sleep(1.0)
