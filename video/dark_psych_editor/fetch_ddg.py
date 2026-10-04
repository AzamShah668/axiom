"""Image candidates via DuckDuckGo image search (sequential, paced, with backoff).

Bing returns degraded results from this server, so this replaces fetch_images.search().
Usage: python3 fetch_ddg.py [query ...]   (no args = every image query in plan.py)
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
import fetch_images as F  # noqa: E402  (reuses qid, queries, probe, BLOCK, OUT)

UA = F.UA
INDEX = os.path.join(F.OUT, 'index.json')


def curl(url, extra=()):
    return subprocess.run(['curl', '-sL', '-A', UA, '-H', 'Accept-Language: en-US,en;q=0.9', '--max-time', '25',
                           *extra, url], capture_output=True, text=True).stdout


def ddg_results(q):
    for k, wait in enumerate((0, 3, 6, 10, 15, 25)):
        time.sleep(wait)
        page = curl('https://duckduckgo.com/?' + urllib.parse.urlencode({'q': q, 'iax': 'images', 'ia': 'images'}))
        m = re.search(r'vqd=["\']?(\d-[\d-]+)', page)
        if not m:
            continue
        r = curl('https://duckduckgo.com/i.js?' + urllib.parse.urlencode(
            {'l': 'us-en', 'o': 'json', 'q': q, 'vqd': m.group(1), 'f': ',size:Large,,,,', 'p': '1'}),
            ('-H', 'Referer: https://duckduckgo.com/'))
        try:
            return json.loads(r)['results']
        except Exception:
            continue
    return []


def fetch(q):
    i = F.qid(q)
    got = []
    for res in ddg_results(q):
        if len(got) >= 3:
            break
        u, src = res.get('image', ''), res.get('url', '')
        if any(b in u.lower() or b in src.lower() for b in F.BLOCK):
            continue
        w, h = res.get('width') or 0, res.get('height') or 0
        if w and h and (w < 800 or h < 450 or not 0.6 <= w / h <= 2.6):
            continue
        ext = os.path.splitext(urllib.parse.urlparse(u).path)[1].lower()
        ext = ext if ext in ('.jpg', '.jpeg', '.png', '.webp') else '.jpg'
        dst = os.path.join(F.OUT, '%s_%d%s' % (i, len(got) + 1, ext))
        subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '25', '-o', dst, u], capture_output=True)
        pw, ph = F.probe(dst)
        if pw >= 700 and ph >= 400:
            got.append({'file': os.path.basename(dst), 'w': pw, 'h': ph, 'url': u, 'title': res.get('title', '')})
        elif os.path.exists(dst):
            os.remove(dst)
    return got


if __name__ == '__main__':
    qs = sys.argv[1:] or F.queries()
    index = json.load(open(INDEX)) if os.path.exists(INDEX) else {}
    for n, q in enumerate(qs):
        # clear old candidates for this query (Bing results were unreliable)
        for c in index.get(q, {}).get('cands', []):
            p = os.path.join(F.OUT, c['file'])
            if os.path.exists(p):
                os.remove(p)
        got = fetch(q)
        index[q] = {'id': F.qid(q), 'cands': got}
        json.dump(index, open(INDEX, 'w'), indent=1)
        print('%3d/%d  %d  %s' % (n + 1, len(qs), len(got), q), flush=True)
        time.sleep(2.5)
    print('empty:', [q for q in qs if not index[q]['cands']])
