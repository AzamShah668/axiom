import subprocess, sys, json, os, re
src, key = sys.argv[1], sys.argv[2]
dur = float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',src],capture_output=True,text=True).stdout)
# scene scores via scdet on a downscaled stream (fast); pts_time is the true timeline
r = subprocess.run(['ffmpeg','-v','error','-i',src,'-vf','scale=320:-2,scdet=threshold=12:sc_pass=1,metadata=print:file=-','-an','-f','null','-'],capture_output=True,text=True)
cuts = [float(m) for m in re.findall(r'lavfi\.scd\.time=([\d.]+)', r.stdout)]
bounds = [0.0] + [c for c in cuts] + [dur]
shots = [(a, b) for a, b in zip(bounds, bounds[1:]) if b - a >= 0.8]
os.makedirs('shots_'+key, exist_ok=True)
for i, (a, b) in enumerate(shots):
    mid = (a + b) / 2
    subprocess.run(['ffmpeg','-v','error','-y','-ss','%.2f'%mid,'-i',src,'-frames:v','1','-vf',
        "scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,drawtext=text='%s %.1f-%.1f':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.75" % (key, a, b),
        'shots_%s/s_%04d.png' % (key, i)])
json.dump(shots, open('shots_%s.json' % key, 'w'))
subprocess.run(['ffmpeg','-v','error','-y','-pattern_type','glob','-i','shots_%s/s_*.png' % key,'-vf','tile=6x6:padding=3:color=white','sheets/SHOT_%s_%%02d.png' % key])
print(key, 'shots:', len(shots))
