"""Print the plan's items as <sec>/<n> (the numbers "pin" uses) and write a keep file that carries the reviewed shots
of an old cutlist over to a new timing (after the narration was re-joined or a line was added).
usage: plan_items.py edit.json timeline.json old_cutlist.json out_keep.json [section ...]   (then assign --keep out_keep.json)"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "video"))
import render_v3
edit, tl = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
P = render_v3.plan(edit, tl, os.path.join(os.path.dirname(sys.argv[2]), "narration.wav"))
items = P["items"] if isinstance(P, dict) else P[0]
old = json.load(open(sys.argv[3]))["items"]
by = {}
for o in old:  # same section + same beat query/graphic -> same shot (beats are found in order)
    by.setdefault((o["sec"], str(o.get("q")), o.get("gfx"), o["kind"]), []).append(o)
out, n_sec, hit = [], {}, 0
for it in items:
    n = n_sec[it["sec"]] = n_sec.get(it["sec"], -1) + 1
    k = (it["sec"], str(it.get("q")), it.get("gfx"), it["kind"])
    o = by.get(k, []).pop(0) if by.get(k) else None
    hit += o is not None
    if o and o.get("shot"):
        out.append({"sec": it["sec"], "t0": it["t0"], "shot": o["shot"]})
    if it["sec"] in sys.argv[5:]:
        print(f"{it['sec']}/{n:<3} {it['t0']:7.2f} {it['kind']:5} {(it.get('gfx') or str(it.get('q')))[:70]}  {'' if o else 'NEW'}")
json.dump({"items": out}, open(sys.argv[4], "w"))
print(f"{hit}/{len(items)} items matched an old one", file=sys.stderr)
