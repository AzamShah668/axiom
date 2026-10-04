import json, sys, time
from faster_whisper import WhisperModel
src, out = sys.argv[1], sys.argv[2]
t = time.time()
m = WhisperModel('small.en', device='cpu', compute_type='int8', cpu_threads=4)
segs, info = m.transcribe(src, word_timestamps=True, vad_filter=False, beam_size=5)
res = []
for s in segs:
    res.append({'start': s.start, 'end': s.end, 'text': s.text.strip(),
                'words': [{'w': w.word.strip(), 's': round(w.start, 2), 'e': round(w.end, 2)} for w in s.words]})
json.dump(res, open(out, 'w'), indent=1)
print('segments', len(res), 'words', sum(len(r['words']) for r in res), 'secs %.1f' % (time.time() - t))
