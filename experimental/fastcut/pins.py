"""Pin every marked visual of a fast-cut plan to its clip: [F:<flow id>] -> flow10_<id>, [M:<name>] -> mg10_<name>,
[W:<name>] -> web10_<name>, [3:<name>] -> web3d10_<name>. Writes "pin" into the project's edit.base.json.
  python experimental/fastcut/pins.py <edit.json> <timeline.json> <edit.base.json>
"""
import json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "video"))
import render_v3  # noqa: E402  (read-only: its plan() numbers the items)

edit, tl = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
P = render_v3.plan(edit, tl, os.path.join(os.path.dirname(sys.argv[2]), "narration.wav"))
items = P["items"] if isinstance(P, dict) else P[0]
PRE = {"F": "flow10_", "M": "mg10_", "W": "web10_", "3": "web3d10_"}
pins, n, seen = {}, {}, set()
for it in items:
    k = n[it["sec"]] = n.get(it["sec"], -1) + 1
    m = re.search(r"\[([FMW3]):([^\]]+)\]", str(it.get("q")))
    if not m:
        continue
    clip = PRE[m.group(1)] + m.group(2).replace("-", "_")
    if clip in seen:
        print("second scene for", clip, f"{it['sec']}/{k}: left to the matcher")
        continue
    seen.add(clip)
    pins[f"{it['sec']}/{k}"] = clip + "#0"
b = json.load(open(sys.argv[3])); b["pin"] = pins
json.dump(b, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
print(len(pins), "pins")
