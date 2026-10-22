"""Build edit.json from a human-editable edit.spec plus edit.base.json.

  python make_edit.py <edit.spec> <edit.base.json> <out edit.json>

edit.spec, one line per item, grouped by "== <section_id>" (section ids = "## " headers of narration.hi.md).
A trigger is the first occurrence of that exact text in the section's narration ("-" = section start).
  V <trigger|-> @ <visual query> [| <alternative> ...] [{opt}]   footage beat, cut into scenes from different shots
                                       v3 {opt}: hold (5.5 s scenes, slow push) | flash (0.6 s montage) | 4s (length)
                                       | shrink (fast pull-back: the subject visibly shrinks)
  G <trigger|-> @ <graphic name>       explanatory diagram (render_video.gfx) over dark footage
  C <trigger|-> | <English sentence> [| big]
                                       v2: caption on screen. v3: the English CC track; "big" also shows the phrase
                                       as a burned-in key line (names, years, short reveals)
  B <trigger>                          boom
v3 only (edit.base.json "style": "v3", see docs/style-guide.md):
  K <trigger|-> @ LINE / *GOLD LINE* [trigger] / LINE [trigger] [| kicker=..] [| sub=..] [| pos=left|center]
                                       kinetic headline: each line rises in when its trigger is spoken
                                       (no trigger: 0.22 s after the line before); *x* = gold
  N <trigger|-> @ <template> | value=.. [| from=..] [| unit=..] [| kicker=..]   templates (scripts/video/mograph.py):
                  hero thermo gauge line scale fact equation progress chart | over footage: callout route hud name
                  [| foot=..] [| land=<trigger>] [| log] [| over] [| q=<background query>] [| dur=<s>] ...
                                       number card; counts land on the "land" trigger. Default: its own beat over
                                       dimmed footage; "over" = on top of the running footage
  M <trigger> [| breath=1.6] [| riser=1.8] [| impact=impact|hit|none] [| trans=flare|flash|dip|cut] [| drop]
              [| swell=7]               designed moment: a silence inserted before the trigger, a riser that ends on
                                       it, an impact, a music swell (drop = the music falls silent for the breath)
  L <trigger> @ <NAME> [| <role line>]  lower third for a person (= N ... @ name | value=NAME | sub=role | over)
  T <trigger> | <cut|dip|dissolve|flare|flash|whip|zoom>    transition override at the cut nearest the trigger
  S <trigger> | <sound> [| gain=<dB>]  extra sound (scripts/video/sfx.py kinds)
  F <text>                             footer text for this section (default: the chapter card title)
edit.base.json holds the rest: lead_in, title_card / title, cards, music, card_query, bg_query, pin, ban, crops,
exclude, and for v3: style, grade, count_total.
"""
import json, re, sys


def _opts(parts):
    kv, flags = {}, []
    for p in parts:
        k, eq, v = p.partition("=")
        if eq:
            kv[k.strip()] = v.strip()
        elif p.strip():
            flags.append(p.strip())
    return kv, flags


def _trig(x):
    x = x.strip()
    return None if x == "-" else x


def parse(spec):
    sections, cur = {}, None
    for n, ln in enumerate(open(spec, encoding="utf-8").read().splitlines(), 1):
        ln = ln.rstrip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("== "):
            cur = sections.setdefault(ln[3:].strip(), {"v": [], "c": [], "sfx": []})
            continue
        kind, rest = ln[0], ln[2:]
        try:
            if kind == "C":
                parts = [x.strip() for x in rest.split("|")]
                c = {"at": _trig(parts[0]), "text": parts[1]}
                if len(parts) > 2 and parts[2] == "big":
                    c["big"] = True
                cur["c"].append(c)
            elif kind in "VG":
                trig, _, what = rest.partition(" @ ")
                if kind == "V":
                    b = {"at": _trig(trig)}
                    m = re.search(r"\{([^}]+)\}\s*$", what)
                    if m:
                        b["opt"], what = m.group(1).strip(), what[:m.start()]
                    b["q"] = [q.strip() for q in what.split("|") if q.strip()]
                    cur["v"].append(b)
                else:
                    cur["v"].append({"at": _trig(trig), "gfx": what.strip()})
            elif kind == "B":
                cur["sfx"].append({"type": "boom", "at": rest.strip()})
            elif kind == "K":
                trig, _, what = rest.partition(" @ ")
                parts = what.split(" | ")
                kv, _ = _opts(parts[1:])
                lines = []
                for x in parts[0].split(" / "):
                    m = re.match(r"^(.*?)\s*\[([^\]]+)\]\s*$", x)
                    lines.append({"text": m.group(1).strip(), "at": m.group(2).strip()} if m else {"text": x.strip(), "at": None})
                lines[0]["at"] = lines[0]["at"] or _trig(trig)
                cur.setdefault("k", []).append({"at": _trig(trig), "lines": lines, **kv})
            elif kind == "N":
                trig, _, what = rest.partition(" @ ")
                parts = [x.strip() for x in what.split("|")]
                kv, flags = _opts(parts[1:])
                num = {"template": parts[0], **{k: v for k, v in kv.items() if k != "q"}}
                for f in flags:
                    if f != "over":
                        num[f] = True
                if "over" in flags:
                    cur.setdefault("n", []).append({"at": _trig(trig), "num": num})
                else:
                    b = {"at": _trig(trig), "num": num}
                    if kv.get("q"):
                        b["q"] = [q.strip() for q in kv["q"].split(";")]
                    cur["v"].append(b)
            elif kind == "L":
                trig, _, what = rest.partition(" @ ")
                parts = [x.strip() for x in what.split("|")]
                num = {"template": "name", "value": parts[0], **({"sub": parts[1]} if len(parts) > 1 else {})}
                cur.setdefault("n", []).append({"at": _trig(trig), "num": num})
            elif kind == "M":
                parts = [x.strip() for x in rest.split("|")]
                kv, flags = _opts(parts[1:])
                m = {"at": parts[0], **{k: (float(v) if re.fullmatch(r"-?[\d.]+", v) else v) for k, v in kv.items()}}
                for f in flags:
                    m[f] = True
                cur.setdefault("m", []).append(m)
            elif kind == "T":
                trig, _, tr = rest.partition("|")
                cur.setdefault("t", []).append({"at": trig.strip(), "trans": tr.strip()})
            elif kind == "S":
                parts = [x.strip() for x in rest.split("|")]
                kv, _ = _opts(parts[2:])
                cur.setdefault("s", []).append({"at": parts[0], "type": parts[1], **kv})
            elif kind == "F":
                cur["footer"] = rest.strip()
            else:
                raise ValueError("unknown line type")
        except (IndexError, ValueError, AttributeError, TypeError) as e:
            raise SystemExit(f"{spec}:{n}: bad line ({e}): {ln}")
    return sections


def main():
    spec, base, out = sys.argv[1:4]
    edit = json.load(open(base, encoding="utf-8"))
    edit["sections"] = parse(spec)
    json.dump(edit, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print({k: {x: len(v[x]) for x in ("v", "c", "k", "n", "m") if v.get(x)} for k, v in edit["sections"].items()})


if __name__ == "__main__":
    main()
