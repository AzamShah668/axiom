"""Flow check for a Hinglish script (science-script-v2): what would break the voice's read or a channel rule.

  python script_check.py productions/NN-slug/script.txt [--voice neel|rudra] [--wpm N] [--max-holds 5]
                         [--max-repeat 3] [--strict] [--skip hook,person] [--objects "Name One|Name Two"]
  python script_check.py --selftest

script.txt: section label lines (OPENING, CHAPTER: <title>, ENDING; HOOK... in a Short) each followed by text.

"!" lines (exit 1, as always): "..." holds (the voice stops about 1 s on each), catalogue-style names it can't
say (letters and digits mixed, e.g. MoM-z14), phrases of 3+ words repeated too often, questions outside the
opening and ending, viewer address (aap/aapko/dekhiye...).

"~" lines (advice, proposed 2026-11, on trial; they change the exit code only with --strict):
  hook     first sentence over 12 words or hedged (ho sakte/shayad/lagbhag/andaaza); OPENING over --opening-max words
  rhythm   per section: fewer than one line of <=7 words per 120 words, more than 2 flat runs (3 sentences in a
           row, each >=12 words, within 4 words of each other), any sentence over 24 words
  turns    120+ words with no turn word (lekin, magar, par, jabki, phir bhi, balki, asal mein, isliye)
  person   a CHAPTER with no year, or no two-word capitalised name outside the object list (--objects adds more)
  numbers  a big number (billion, crore, lakh, 5,000...) with no everyday picture (jaise, matlab, yaani...) in
           that or the next sentence
  hedges   more than one "lagbhag" per 150 words
  tells    "sabse X ... mein se" (one of the most X), a 2-word phrase in 3+ chapter bridges, 4+ reaction lines
  rehook   a section longer than 95 s at the voice's pace
The pace comes from --wpm, else --voice (neel 147, rudra 170), else the nearest voice-preset.json above the
script. Each section's start time is printed. --skip takes any check name, "!" or "~".
"""
import argparse, collections, json, os, re, sys

ADDRESS = re.compile(r"\b(aap|aapko|aapka|aapke|aapki|dekhiye|sochiye|socho|dekho|kijiye)\b", re.I)
CODE = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*\d)[\w-]{3,}\b")
OK_CODES = {"10²⁶", "BICEP2"}  # spoken naturally ("BICEP two"); extend per video

VOICES = {"neel": 147.0, "rudra": 170.0}  # words a minute at 1.0x (rudra measured on 08: 1,866 words in 11:02)
CHECKS = ["holds", "codes", "address", "questions", "repeats",  # "!" checks (exit 1)
          "hook", "rhythm", "turns", "person", "numbers", "hedges", "tells", "rehook"]  # "~" checks
HEDGE = re.compile(r"\b(ho sakt[eai]|shayad|lagbhag|andaaz?a)\b", re.I)
TURN = re.compile(r"\b(lekin|magar|par|jabki|phir bhi|balki|asal mein|isi?liye)\b", re.I)
YEAR = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")
BIG = re.compile(r"\b(billion|crore|lakh|quadrillion|arab|kharab)\b|\b\d{1,3}(?:,\d{2,3})+\b|\b\d{5,}\b"
                 r"|\b(?!(?:1[5-9]|20)\d\d\b)\d{4}\b", re.I)  # 4-digit years are not big numbers
PICTURE = re.compile(r"\b(jaise|jaisa|jitna|jitni|jitne|matlab|yaani|barabar)\b", re.I)
ONE_OF = re.compile(r"\bsabse (?:\w+ ){1,3}mein se\b", re.I)
REACTION = re.compile(r"\b(achhi khabar|buri khabar|sach kahein)\b", re.I)
# capitalised pairs that are things, not people (--objects adds more), and single words that are never a name
OBJECTS = ("Milky Way|Big Bang|Big Bounce|Cold Spot|Dark Flow|Dark Forest|Great Attractor|Great Nothing|"
           "Great Filter|Great Wall|Bootes Void|Solar System|James Webb|Pale Blue|Blue Dot|Golden Record|"
           "Deep Space|Space Telescope|Event Horizon|Kuiper Belt|Oort Cloud|Wow Signal|Hubble Space|North Pole|"
           "South Pole|New Jersey|Nobel Prize|Andromeda Galaxy|Black Hole|Neutron Star|Red Giant|White Dwarf")
NOT_NAME = set("The Earth Suraj Sun Chaand Moon Hubble Webb Planck Chandra Swift Neptune Jupiter Saturn Uranus Mars "
               "Venus Mercury Pluto Voyager Laniakea Hawaii Mexico California Dutch Universe Galaxy Lab Telescope "
               "Satellite Mission Station Observatory Survey".split())


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


def section_ids(secs):
    """Short ids for "~" lines: OPENING, CH1.., ENDING; other labels (HOOK, THE PROBLEM) as written."""
    ids, n = [], 0
    for label, _ in secs:
        if label.startswith("CHAPTER:"):
            n += 1
            ids.append(f"CH{n}")
        else:
            ids.append(label)
    return ids


def sentences(text):
    text = re.sub(r"\[[^\]]*\]", " ", text)  # [bite:x], [SUSPENSE: ...] are not spoken by the narrator
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if re.search(r"\w", s)]


def nwords(s):
    return sum(1 for w in s.split() if re.search(r"\w", w))


def clip(s, n=60):
    return s if len(s) <= n else s[:n - 3].rstrip() + "..."


def mmss(sec):
    s = int(round(sec))
    return f"{s // 60}:{s % 60:02d}"


def preset_voice(path):
    """rudra/neel from the nearest voice-preset.json at or above the script (productions/ holds the default)."""
    d = os.path.dirname(os.path.abspath(path))
    while True:
        p = os.path.join(d, "voice-preset.json")
        if os.path.isfile(p):
            try:
                name = json.load(open(p, encoding="utf-8")).get("voice_name", "").lower()
            except (OSError, ValueError):
                name = ""
            for v in VOICES:
                if v in name:
                    return v, os.path.relpath(p)
        up = os.path.dirname(d)
        if up == d:
            return None, None
        d = up


# ---------------------------------------------------------------- "~" checks: each yields (section id, message)

def check_hook(secs, ids, a):
    if not secs:
        return
    label, body = secs[0]
    sents = sentences(body)
    if sents:
        first, n = sents[0], nwords(sents[0])
        hedges = sorted({m.group(0).lower() for m in HEDGE.finditer(first)})
        why = []
        if n > 12:
            why.append(f"first sentence {n} words (max 12)")
        if hedges:
            why.append("hedged (" + ", ".join(hedges) + ")")
        if why:
            yield ids[0], ", ".join(why) + ": open on a concrete scene the footage can show"
    if label == "OPENING":
        n = nwords(" ".join(sents))
        if n > a.opening_max:
            yield ids[0], (f"{n} words, about {n / a.wpm * 60:.0f} s (target 130 words, about 45 s): "
                           "scene, stakes, 2-3 teasers, nothing else")


def check_rhythm(secs, ids, a):
    for sid, (_, body) in zip(ids, secs):
        lens = [nwords(s) for s in sentences(body)]
        total = sum(lens)
        why = []
        short = sum(1 for n in lens if n <= 7)
        if total >= 60 and short * 120 < total:  # a 40-word Short beat is too small to judge
            why.append(f"{short} lines of <=7 words in {total} words (want 1 per 120)")
        runs, i = [], 0
        while i + 2 < len(lens):
            w = lens[i:i + 3]
            if min(w) >= 12 and max(w) - min(w) <= 4:
                runs.append(f"{w[0]}/{w[1]}/{w[2]}")
                i += 3
            else:
                i += 1
        if len(runs) > 2:
            why.append(f"{len(runs)} flat runs ({', '.join(runs)})")
        long_ = [n for n in lens if n > 24]
        if long_:
            why.append(f"{len(long_)} sentence{'s' if len(long_) > 1 else ''} over 24 words ({', '.join(map(str, long_))})")
        if why:
            yield sid, "; ".join(why) + ": keep the flow, add a 3-7 word line at a turn"


def check_turns(secs, ids, a):
    for sid, (_, body) in zip(ids, secs):
        text = " ".join(sentences(body))
        words = text.split()
        cuts = [0] + [len(text[:m.start()].split()) for m in TURN.finditer(text)] + [len(words)]
        for s, e in zip(cuts, cuts[1:]):
            if e - s >= 120:
                yield sid, f"{e - s} words without a turn (from '{clip(' '.join(words[s:s + 8]), 50)}'): add a lekin / isliye beat"


def check_person(secs, ids, a):
    objects = re.compile(r"\b(" + OBJECTS + ("|" + a.objects if a.objects else "") + r")\b")
    lower = set(re.findall(r"\b[a-z]\w*\b", " ".join(b for _, b in secs)))  # sentence starters (Aur, Woh...)
    for sid, (label, body) in zip(ids, secs):
        if not label.startswith("CHAPTER:"):
            continue
        text = objects.sub(" # ", re.sub(r"\[[^\]]*\]", " ", body))
        names = [m.group(1) + " " + m.group(2) for m in re.finditer(r"\b(?=([A-Z][a-z]+) ([A-Z][a-z]+)\b)", text)
                 if not ({m.group(1), m.group(2)} & NOT_NAME) and m.group(1).lower() not in lower
                 and m.group(2).lower() not in lower]
        miss = []
        if not names:
            miss.append("no person named: who found it?")
        if not YEAR.search(body):
            miss.append("no year: when?")
        if miss:
            yield sid, " ".join(miss)


def check_numbers(secs, ids, a):
    for sid, (_, body) in zip(ids, secs):
        sents = sentences(body)
        for i, s in enumerate(sents):
            m = BIG.search(s)
            if m and not PICTURE.search(s) and not (i + 1 < len(sents) and PICTURE.search(sents[i + 1])):
                yield sid, f"bare '{m.group(0)}' in '{clip(s)}': give it an everyday picture (jaise, matlab ...)"


def check_hedges(secs, ids, a):
    per = [(sid, len(re.findall(r"\blagbhag\b", b, re.I))) for sid, (_, b) in zip(ids, secs)]
    n = sum(c for _, c in per)
    words = nwords(" ".join(b for _, b in secs))
    if n > max(1.0, words / 150):
        top = ", ".join(f"{sid} {c}" for sid, c in sorted(per, key=lambda x: -x[1]) if c)
        yield "ALL", (f"'lagbhag' {n} times in {words} words (max 1 per 150 = {max(1, words // 150)}; {clip(top, 70)}): "
                      "keep it where the number really is uncertain")


def check_tells(secs, ids, a):
    for sid, (_, body) in zip(ids, secs):
        for m in ONE_OF.finditer(body):
            yield sid, f"'{m.group(0)}' (one of the most X): show it with a specific instead"
    # a bridge = the last two sentences of a CHAPTER; a template = a 2-word phrase in 3+ bridges that is mostly
    # a bridge habit (a third or more of its uses), so topic words ("black hole") and glue ("hai ki") don't count
    shared = collections.defaultdict(list)
    for sid, (label, body) in zip(ids, secs):
        if label.startswith("CHAPTER:"):
            toks = re.sub(r"[^\w\s]", " ", " ".join(sentences(body)[-2:]).lower()).split()
            for g in {" ".join(toks[i:i + 2]) for i in range(len(toks) - 1)}:
                shared[g].append(sid)
    alltoks = re.sub(r"[^\w\s]", " ", " ".join(" ".join(sentences(b)) for _, b in secs).lower()).split()
    uses = collections.Counter(" ".join(alltoks[i:i + 2]) for i in range(len(alltoks) - 1))
    for g, where in sorted(shared.items(), key=lambda x: (-len(x[1]), x[0])):
        if len(where) >= 3 and len(where) * 3 >= uses[g]:
            yield "ALL", f"'{g}' in {len(where)} bridges ({', '.join(where)}): one template; name the next picture instead"
    n = sum(len(REACTION.findall(b)) for _, b in secs)
    if n > 3:
        yield "ALL", f"{n} reaction lines (Achhi khabar / Buri khabar / Sach kahein; max 3)"


def check_rehook(secs, ids, a):
    for sid, (_, body) in zip(ids, secs):
        d = nwords(" ".join(sentences(body))) / a.wpm * 60
        if d > 95:
            yield sid, f"{d:.0f} s long (max 95 at {a.wpm:.0f} wpm): add a re-hook or split it"


NEW = {"hook": check_hook, "rhythm": check_rhythm, "turns": check_turns, "person": check_person,
       "numbers": check_numbers, "hedges": check_hedges, "tells": check_tells, "rehook": check_rehook}


def advice(secs, a, skip=()):
    ids = section_ids(secs)
    return [(name, sid, msg) for name, fn in NEW.items() if name not in skip for sid, msg in fn(secs, ids, a)]


# ---------------------------------------------------------------- fixtures: one tripping and one clean text per check

FIXTURES = {
    "hook": ("OPENING\nHamari galaxy mein lagbhag 10 crore black holes ho sakte hain, aur zyaadatar ko kisi ne nahi dekha.",
             "OPENING\nHamari galaxy mein ek black hole akela bhatak raha hai. Na koi taara saath hai, na roshni."),
    "rhythm": ("CHAPTER: X\n" + " ".join(["Yeh ek lamba vaakya hai jo bina ruke chalta hai aur kabhi khatam nahi hota hai."] * 9),
               "CHAPTER: X\n" + " ".join(["Yeh ek lamba vaakya hai jo bina ruke chalta hai aur aage badhta hai.",
                                          "Woh ruka.", "Phir ek aur baat aayi jo thodi chhoti thi lekin zaroori thi.",
                                          "Aur phir ek lambi kahaani shuru hui jo raat bhar chalti rahi, subah tak."] * 3)),
    "turns": ("CHAPTER: X\n" + "Taara chamakta raha aur roshni door tak gayi. " * 16,
              "CHAPTER: X\n" + "Taara chamakta raha aur roshni door tak gayi. " * 8 + "Lekin phir sab badal gaya. "
              + "Taara chamakta raha aur roshni door tak gayi. " * 8),
    "person": ("CHAPTER: X\nWahan ek magnetar hai, Milky Way ke doosre kinare par, aur Big Bang se bhi purana lagta hai.",
               "CHAPTER: X\n1963 mein Dutch astronomer Maarten Schmidt ek neele bindu ki roshni padh rahe the."),
    "numbers": ("CHAPTER: X\nUski magnetic field ek quadrillion guna taakatwar hai. Woh ghoomta rehta hai.",
                "CHAPTER: X\nUski raftaar 600 kilometre har second hai. Matlab Earth se Chaand tak bas 11 minute."),
    "hedges": ("CHAPTER: X\nWoh lagbhag 20 kilometre chauda hai, lagbhag 10 saal purana, aur lagbhag ek lakh guna tez.",
               "CHAPTER: X\nWoh lagbhag 20 kilometre chauda hai, 10 saal purana, aur bahut tez."),
    "tells": ("OPENING\nYeh brahmand ki sabse daravni jagahon mein se ek hai.",
              "OPENING\nYeh jagah Earth se 5,000 light years door hai."),
    "rehook": ("CHAPTER: X\n" + "Taara chamakta raha aur roshni door tak gayi. " * 40,
               "CHAPTER: X\n" + "Taara chamakta raha aur roshni door tak gayi. " * 20),
}


def selftest():
    a = argparse.Namespace(wpm=VOICES["rudra"], opening_max=140, objects="")
    bad = 0
    for name, (trip, clean) in FIXTURES.items():
        got_trip = [m for c, _, m in advice(sections(trip), a) if c == name]
        got_clean = [m for c, _, m in advice(sections(clean), a) if c == name]
        ok = bool(got_trip) and not got_clean
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {name:8s} trips: {clip(got_trip[0], 80) if got_trip else '-'}"
              + (f" | clean flagged: {got_clean[0]}" if got_clean else ""))
    # bridges: three chapters ending on the same 2-word template
    t = "\n".join(f"CHAPTER: C{i}\nYeh ek jagah thi. Woh kam se kam chup to tha, lekin agli jagah alag hai." for i in range(4))
    got = [m for c, _, m in advice(sections(t), a) if c == "tells" and "bridges" in m]
    bad += not got
    print(f"{'ok ' if got else 'BAD'} tells    bridges: {clip(got[0], 80) if got else '-'}")
    print("selftest passed" if not bad else f"selftest: {bad} failing")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script", nargs="?")
    ap.add_argument("--voice", choices=sorted(VOICES), help="sets the pace; default: nearest voice-preset.json")
    ap.add_argument("--wpm", type=float, help="words a minute at 1.0x (wins over --voice)")
    ap.add_argument("--max-holds", type=int, default=5)
    ap.add_argument("--max-repeat", type=int, default=3)
    ap.add_argument("--opening-max", type=int, default=140,
                    help="hook: OPENING word limit (target 130, about 45 s; 140 lets a near miss pass)")
    ap.add_argument("--objects", default="", help="extra 'Two Words|...' that are things, not people (person check)")
    ap.add_argument("--skip", action="append", default=[], help="checks to turn off, comma-separated: " + ",".join(CHECKS))
    ap.add_argument("--strict", action="store_true", help="the '~' advice also sets exit 1")
    ap.add_argument("--selftest", action="store_true", help="run the built-in fixtures")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if not a.script:
        ap.error("script is required")
    skip = {s.strip() for v in a.skip for s in v.split(",") if s.strip()}
    for s in skip - set(CHECKS):
        ap.error(f"unknown check '{s}' (known: {', '.join(CHECKS)})")
    src = "--wpm"
    if a.wpm is None:
        voice, src = (a.voice, "--voice") if a.voice else preset_voice(a.script)
        voice = voice or "neel"
        a.wpm, src = VOICES[voice], f"{voice}, from {src or 'the default'}"
    secs = sections(open(a.script, encoding="utf-8").read())
    body = " ".join(b for _, b in secs)
    words = body.split()
    flags = 0
    holds = body.count("...")
    print(f"{len(words)} words, about {len(words) / a.wpm:.1f} min at 1.0x and {len(words) / a.wpm / 1.2:.1f} min at 1.2x; "
          f"{len(secs)} sections ({a.wpm:.0f} wpm: {src})")
    t = 0.0
    for sid, (label, b) in zip(section_ids(secs), secs):
        n = nwords(" ".join(sentences(b)))
        title = label.split(":", 1)[1].strip() if label.startswith("CHAPTER:") else ""
        print(f"  {mmss(t):>5}  {sid:<8} {n:4d} w  {mmss(n / a.wpm * 60):>5}  {title}")
        t += n / a.wpm * 60
    if holds > a.max_holds and "holds" not in skip:
        flags += 1
        print(f'! {holds} "..." holds (max {a.max_holds}): keep them for the reveal words, use commas elsewhere')
    for label, b in secs:
        for c in sorted({m.group(0) for m in CODE.finditer(b)} - OK_CODES) if "codes" not in skip else []:
            flags += 1
            print(f"! [{label}] '{c}' is hard to speak: say what it is, put the name on screen")
        for sent in re.split(r"(?<=[.?!])\s+", b) if "address" not in skip else []:
            if re.search(r"\b(kaha|likha|bole|poocha)\b", sent, re.I):  # a character speaking, not the narrator
                continue
            for m in ADDRESS.finditer(sent):
                flags += 1
                print(f"! [{label}] viewer address '{m.group(0)}' (the narrator tells a story, never talks to the viewer)")
        qs = [q.strip() for q in re.findall(r"[^.?!]*\?", b)]
        if qs and not label.startswith(("OPENING", "ENDING")) and "questions" not in skip:
            for q in qs:
                flags += 1
                print(f"! [{label}] narrator question: '{q[-60:]}' (make it a statement, unless a character asks it)")
    norm = re.sub(r"[^\w\s]", " ", body.lower()).split()
    grams = collections.Counter(" ".join(norm[i:i + 3]) for i in range(len(norm) - 2))
    common = {"ke hisaab se", "ek doosre se", "big bang ke", "ki ek shuruaat", "se pehle kya", "big bang se", "bang se pehle"}
    for g, n in grams.most_common(40) if "repeats" not in skip else []:
        if n > a.max_repeat and g not in common:
            flags += 1
            print(f"! '{g}' said {n} times (max {a.max_repeat}): vary it")
    tips = advice(secs, a, skip)
    for name, sid, msg in tips:
        print(f"~ [{sid}] {name}: {msg}")
    summary = "OK: nothing flagged" if not flags else f"{flags} things to look at"
    if tips:
        summary += f"; {len(tips)} advice lines (~){', counted by --strict' if a.strict else ', not counted (--strict counts them)'}"
    print(summary)
    sys.exit(1 if flags or (a.strict and tips) else 0)


if __name__ == "__main__":
    main()
