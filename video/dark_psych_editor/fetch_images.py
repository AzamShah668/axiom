"""Collect candidate images for every image query in plan.py via Bing image search.

Writes assets/img/<id>_<n>.<ext> (up to 3 candidates per query) and assets/img/index.json.
"""
import concurrent.futures as cf
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
import plan  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'assets', 'img')
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
BLOCK = ('shutterstock', 'alamy', 'dreamstime', 'istockphoto', 'gettyimages', '123rf', 'depositphotos',
         'stock.adobe', 'ftcdn', 'bigstock', 'canstockphoto', 'featurepics', 'colourbox', 'pond5',
         'agefotostock', 'superstock', 'masterfile', 'fineartamerica', 'vecteezy', 'pixtastock',
         'photocase', 'mediastorehouse', 'granger.com', 'stocksy', 'eyeem', 'yayimages', 'lookandlearn')


def queries():
    qs = []
    for t, kind, arg, opts in plan.B:
        if kind == 'img':
            qs.append(arg)
        bg = opts.get('bg', '')
        if isinstance(bg, str) and bg.startswith('img:'):
            qs.append(bg[4:])
    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


def qid(q):
    slug = re.sub(r'[^a-z0-9]+', '_', q.lower()).strip('_')[:40]
    return slug + '_' + hashlib.md5(q.encode()).hexdigest()[:6]


def search(q):
    url = 'https://www.bing.com/images/search?' + urllib.parse.urlencode(
        {'q': q, 'qft': '+filterui:imagesize-large', 'form': 'IRFLTR', 'first': '1'})
    r = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '25', url], capture_output=True, text=True)
    urls = []
    for m in re.findall(r'm="(\{[^"]+\})"', r.stdout):
        try:
            d = json.loads(html.unescape(m))
        except Exception:
            continue
        u = d.get('murl')
        if u and not any(b in u.lower() for b in BLOCK) and not any(b in (d.get('purl') or '').lower() for b in BLOCK):
            urls.append(u)
    return urls


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                        '-of', 'csv=p=0', path], capture_output=True, text=True)
    try:
        w, h = [int(x) for x in r.stdout.strip().split(',')[:2]]
        return w, h
    except Exception:
        return 0, 0


def fetch(q):
    i = qid(q)
    got = []
    for n, u in enumerate(search(q)[:12]):
        if len(got) >= 3:
            break
        ext = os.path.splitext(urllib.parse.urlparse(u).path)[1].lower()
        ext = ext if ext in ('.jpg', '.jpeg', '.png', '.webp') else '.jpg'
        dst = os.path.join(OUT, '%s_%d%s' % (i, len(got) + 1, ext))
        subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '25', '-o', dst, u], capture_output=True)
        w, h = probe(dst)
        if w >= 700 and h >= 400 and 0.6 <= w / h <= 2.6:
            got.append({'file': os.path.basename(dst), 'w': w, 'h': h, 'url': u})
        else:
            try:
                os.remove(dst)
            except OSError:
                pass
    return q, i, got


if __name__ == '__main__':
    qs = queries()
    print('queries:', len(qs))
    index = {}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for q, i, got in ex.map(fetch, qs):
            index[q] = {'id': i, 'cands': got}
            print('%d  %s' % (len(got), q))
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), indent=1)
    print('queries with 0 candidates:', [q for q, v in index.items() if not v['cands']])
