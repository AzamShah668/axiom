import json, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, 'assets', 'img')
idx = json.load(open(os.path.join(IMG, 'index.json')))
qs = list(idx.keys())
font = ImageFont.truetype(os.path.join(ROOT, 'fonts', 'Montserrat-ExtraBold.ttf'), 18)
TW, TH, ROWS = 320, 180, 8
os.makedirs(os.path.join(ROOT, 'review'), exist_ok=True)
json.dump(qs, open(os.path.join(ROOT, 'review', 'order.json'), 'w'), indent=1)
for s in range(0, len(qs), ROWS):
    sheet = Image.new('RGB', (TW * 3 + 8, (TH + 4) * ROWS), 'white')
    d = ImageDraw.Draw(sheet)
    for r, q in enumerate(qs[s:s + ROWS]):
        for c, cand in enumerate(idx[q]['cands'][:3]):
            try:
                im = Image.open(os.path.join(IMG, cand['file'])).convert('RGB')
                im = ImageOps.fit(im, (TW, TH))
            except Exception:
                im = Image.new('RGB', (TW, TH), 'gray')
            sheet.paste(im, (c * (TW + 4), r * (TH + 4)))
            d.rectangle([c * (TW + 4), r * (TH + 4), c * (TW + 4) + 60, r * (TH + 4) + 24], fill='black')
            d.text((c * (TW + 4) + 4, r * (TH + 4) + 2), '%d.%d' % (s + r, c + 1), fill='yellow', font=font)
    sheet.save(os.path.join(ROOT, 'review', 'sheet_%02d.png' % (s // ROWS)))
print('sheets:', (len(qs) + ROWS - 1) // ROWS, 'queries:', len(qs))
