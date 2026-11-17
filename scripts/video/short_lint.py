"""Lint a v2 Short before it is recorded or rendered (warnings only; exit code is always 0).

  python short_lint.py productions/NN-slug/shorts/<id> [--max-words 130]

Reads <dir>/short.json, <dir>/tts/captions.hinglish.md (the spoken Roman text; falls back to script.txt) and
<dir>/script.txt, and reports:
- the word count and the predicted length (Rudra/Neel at 1.1x speak about 3.0 Roman words/s; 122 words took 40.4 s
  on 08 hunter) plus the joins and the end card; the owner's budget is 35-60 s (research 02 suggests 30-35 s)
- the hook: a number or the claim in the first 8 words, no comma in the first 3, no date first
- a leftover [SUSPENSE] marker (owner: no suspense stops) or a suspense_after key
- short.json without "speed" (the renderer default is 1.1 now, but say it), end_hold left at 2.4 s
"""
import argparse, json, os, re

WPS = 3.0          # Roman words per second at 1.1x
GAP, END_HOLD = 0.12, 2.4
NUM_WORDS = {"ek", "do", "teen", "char", "chaar", "paanch", "panch", "chhe", "chhah", "saat", "aath", "nau", "das",
             "gyaarah", "barah", "bees", "tees", "chaalis", "pachaas", "sau", "hazaar", "hazar", "lakh", "crore",
             "karod", "arab", "kharab", "million", "billion", "trillion", "aadha", "dugna", "guna"}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december", "janvari", "farvari"}
YEAR = re.compile(r"^(1[5-9]\d\d|20\d\d)$")


def spoken_text(d):
    """[(section id, Roman text)] of what is spoken."""
    cap = os.path.join(d, "tts", "captions.hinglish.md")
    secs = []
    if os.path.exists(cap):
        for ln in open(cap, encoding="utf-8"):
            if ln.startswith("## "):
                secs.append([ln[3:].strip(), ""])
            elif secs and ln.strip() and not ln.startswith("#"):
                secs[-1][1] += " " + ln.strip()
        return [(s, re.sub(r"\{([^|}]+)\|\d+\}", r"\1", t).strip()) for s, t in secs]
    scr = os.path.join(d, "script.txt")
    if not os.path.exists(scr):
        return []
    body = open(scr, encoding="utf-8").read().split("\n\n")[1:]  # skip the header paragraph
    for block in body:
        lines = [x for x in block.strip().splitlines() if x.strip() and not x.startswith("[")]
        if len(lines) >= 2 and lines[0].isupper():
            secs.append((lines[0].strip(), " ".join(lines[1:])))
    return secs


def lint(d, max_words):
    warn, info = [], []
    cfg_p = os.path.join(d, "short.json")
    cfg = json.load(open(cfg_p, encoding="utf-8")) if os.path.exists(cfg_p) else {}
    if not cfg:
        warn.append("no short.json")
    secs = spoken_text(d)
    if not secs:
        warn.append("no spoken text (tts/captions.hinglish.md or script.txt)")
        return warn, info
    words = [w for _, t in secs for w in t.split() if re.search(r"\w", w)]
    speed = float(cfg.get("speed", 1.1))
    hold = float(cfg.get("end_hold", END_HOLD))
    pred = len(words) / WPS * 1.1 / speed + GAP * (len(secs) - 1) + hold
    info.append(f"{len(words)} words in {len(secs)} sections, predicted {pred:.1f} s at {speed}x "
                f"(end card hold {hold} s)")
    if len(words) > max_words:
        warn.append(f"{len(words)} words > {max_words}: cut setup lines first, never the twist")
    if not 35 <= pred <= 60:
        warn.append(f"predicted {pred:.1f} s is outside the owner's 35-60 s")
    elif pred > 35:
        info.append("research 02 suggests 30-35 s (about 100 words) for curiosity Shorts; the owner decides")
    # the hook
    first = secs[0][1].split()
    bare = [re.sub(r"[^\w]", "", w).lower() for w in first]
    if not any(any(c.isdigit() for c in w) or w in NUM_WORDS for w in bare[:8]):
        warn.append("no number in the first 8 words: make sure the claim is there, e.g. "
                    "'Das crore black holes, sirf hamari galaxy mein...'")
    if any("," in w for w in first[:3]):
        warn.append(f"a comma in the first 3 words ({' '.join(first[:3])}): the voice pauses before the hook lands")
    if any(YEAR.match(w) or w in MONTHS for w in bare[:3]):
        warn.append(f"opens on a date ({' '.join(first[:3])}): give the claim first, the date later")
    # owner's rules
    for name in ("script.txt", os.path.join("tts", "narration.hi.md"), os.path.join("tts", "captions.hinglish.md")):
        p = os.path.join(d, name)
        if os.path.exists(p) and "[SUSPENSE" in open(p, encoding="utf-8").read().upper():
            warn.append(f"leftover [SUSPENSE] marker in {name} (owner: no suspense stops)")
    if cfg.get("suspense_after"):
        warn.append("suspense_after is set (owner: no suspense stops)")
    if cfg and "speed" not in cfg:
        warn.append('short.json has no "speed": add "speed": 1.1 (the owner\'s rule for these Shorts)')
    if cfg and "end_hold" not in cfg:
        info.append('end card holds 2.4 s after the last word; "end_hold": 0.7 with "loop": true removes the dead tail')
    return warn, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--max-words", type=int, default=130)
    a = ap.parse_args()
    warn, info = lint(a.dir, a.max_words)
    print(os.path.basename(os.path.normpath(a.dir)))
    for x in info:
        print("  info:", x)
    for x in warn:
        print("  WARN:", x)
    if not warn:
        print("  ok")


if __name__ == "__main__":
    main()
