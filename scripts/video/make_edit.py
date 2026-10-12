"""Build edit.json from a human-editable edit.spec plus edit.base.json.

  python make_edit.py <edit.spec> <edit.base.json> <out edit.json>

edit.spec, one line per item, grouped by "== <section_id>" (section ids = "## " headers of narration.hi.md):
  V <trigger|-> @ <visual query> [| <alternative query> ...]   footage beat; scenes are cut every ~2.5 s,
                                                                 each from a different shot that best matches
  G <trigger|-> @ <graphic name>                                 explanatory graphic (render_video.gfx) over dark footage
  C <trigger|-> | <English caption> [| big]                      caption shown when the trigger is spoken
  B <trigger>                                                    boom sound effect
A trigger is the first occurrence of that exact text in the section's narration ("-" = section start).
edit.base.json holds the rest: lead_in, title_card, cards, music, card_query, bg_query, pin, ban, crops, exclude.
"""
import json, sys


def parse(spec):
    sections, cur = {}, None
    for ln in open(spec, encoding="utf-8").read().splitlines():
        ln = ln.rstrip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("== "):
            cur = sections.setdefault(ln[3:].strip(), {"v": [], "c": [], "sfx": []})
            continue
        kind, rest = ln[0], ln[2:]
        if kind == "C":
            parts = [x.strip() for x in rest.split("|")]
            c = {"at": None if parts[0] == "-" else parts[0], "text": parts[1]}
            if len(parts) > 2 and parts[2] == "big":
                c["big"] = True
            cur["c"].append(c)
        elif kind in "VG":
            trig, _, what = rest.partition(" @ ")
            at = None if trig.strip() == "-" else trig.strip()
            if kind == "V":
                cur["v"].append({"at": at, "q": [q.strip() for q in what.split("|") if q.strip()]})
            else:
                cur["v"].append({"at": at, "gfx": what.strip()})
        elif kind == "B":
            cur["sfx"].append({"type": "boom", "at": rest.strip()})
        else:
            raise SystemExit(f"bad spec line: {ln}")
    return sections


def main():
    spec, base, out = sys.argv[1:4]
    edit = json.load(open(base, encoding="utf-8"))
    edit["sections"] = parse(spec)
    json.dump(edit, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print({k: (len(v["v"]), len(v["c"])) for k, v in edit["sections"].items()})


if __name__ == "__main__":
    main()
