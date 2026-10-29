"""Flow check for a Hinglish script (science-script-v2): what would break Neel's read or a channel rule.

  python script_check.py productions/NN-slug/script.txt [--wpm 147] [--max-holds 5] [--max-repeat 3]

script.txt: section label lines (OPENING, CHAPTER: <title>, ENDING) each followed by one paragraph.
Reports: "..." holds (Neel stops about 1 s on each), catalogue-style names he can't say (letters and digits
mixed, e.g. MoM-z14), phrases of 3+ words repeated too often, questions outside the agreed ending debate,
viewer address (aap/aapko/dekhiye...), and the length at --wpm words a minute. Exit 1 if anything is flagged.
"""
import argparse, collections, re, sys

ADDRESS = re.compile(r"\b(aap|aapko|aapka|aapke|aapki|dekhiye|sochiye|socho|dekho|kijiye)\b", re.I)
CODE = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*\d)[\w-]{3,}\b")
OK_CODES = {"10²⁶", "BICEP2"}  # spoken naturally ("BICEP two"); extend per video


def sections(text):
    out, cur = [], None
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.isupper() or s.startswith("CHAPTER:"):
            cur = [s, ""]
            out.append(cur)
        elif cur is not None:
            cur[1] += " " + s
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--wpm", type=float, default=147.0, help="Neel at 1.0x")
    ap.add_argument("--max-holds", type=int, default=5)
    ap.add_argument("--max-repeat", type=int, default=3)
    a = ap.parse_args()
    secs = sections(open(a.script, encoding="utf-8").read())
    body = " ".join(b for _, b in secs)
    words = body.split()
    flags = 0
    holds = body.count("...")
    print(f"{len(words)} words, about {len(words) / a.wpm:.1f} min at 1.0x and {len(words) / a.wpm / 1.2:.1f} min at 1.2x; "
          f"{len(secs)} sections")
    if holds > a.max_holds:
        flags += 1
        print(f'! {holds} "..." holds (max {a.max_holds}): keep them for the reveal words, use commas elsewhere')
    for label, b in secs:
        for c in sorted({m.group(0) for m in CODE.finditer(b)} - OK_CODES):
            flags += 1
            print(f"! [{label}] '{c}' is hard to speak: say what it is, put the name on screen")
        for sent in re.split(r"(?<=[.?!])\s+", b):
            if re.search(r"\b(kaha|likha|bole|poocha)\b", sent, re.I):  # a character speaking, not the narrator
                continue
            for m in ADDRESS.finditer(sent):
                flags += 1
                print(f"! [{label}] viewer address '{m.group(0)}' (the narrator tells a story, never talks to the viewer)")
        qs = [q.strip() for q in re.findall(r"[^.?!]*\?", b)]
        if qs and not label.startswith(("OPENING", "ENDING")):
            for q in qs:
                flags += 1
                print(f"! [{label}] narrator question: '{q[-60:]}' (make it a statement, unless a character asks it)")
    norm = re.sub(r"[^\w\s]", " ", body.lower()).split()
    grams = collections.Counter(" ".join(norm[i:i + 3]) for i in range(len(norm) - 2))
    common = {"ke hisaab se", "ek doosre se", "big bang ke", "ki ek shuruaat", "se pehle kya", "big bang se", "bang se pehle"}
    for g, n in grams.most_common(40):
        if n > a.max_repeat and g not in common:
            flags += 1
            print(f"! '{g}' said {n} times (max {a.max_repeat}): vary it")
    print("OK: nothing flagged" if not flags else f"{flags} things to look at")
    sys.exit(1 if flags else 0)


if __name__ == "__main__":
    main()
