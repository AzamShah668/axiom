"""Check narration.hi.md (the exact text ElevenLabs will read) before any recording, so every section is right
the first time and never has to be paid for twice (owner, 2026-10-27). Exit 1 if anything is flagged.

  python scripts/elevenlabs/tts_check.py productions/NN-slug/tts/narration.hi.md [--allow-pauses]

Checks: words from productions/tts-lexicon.json "replace" (mispronounced or unwanted, with the fix); "..." and
other pause marks (no pauses since 2026-10-27); digits and symbols ElevenLabs reads oddly; Latin acronyms that
are not in "acronyms_ok" (write them the way they are said, in Devanagari); catalogue codes; Latin-script Hindi;
sentences over 28 words; [bite:x] markers missing from bites.json. Prints the new names and English terms that
were never heard yet ("verified"): probe them first with probe_words.py.
Roman-letter Hinglish is refused for eleven_multilingual_v2 (the locked model): it can't be told the language and
half-reads Roman Hindi as English. Owner, 2026-10-29, after an A/B of the same sentences: "butchering the words" in
Roman letters, "exactly what I want" in Devanagari. (v3/v4 with language_code "hi" can read Roman Hindi, but the
owner prefers the old model's sound.) With such a model, Roman Hindi and digits pass and a sentence's first word
is not taken for a name."""
import json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LEX = json.load(open(os.path.join(ROOT, "productions", "tts-lexicon.json"), encoding="utf-8"))
HINGLISH = {"hai", "hain", "tha", "thi", "aur", "ki", "ka", "ke", "mein", "se", "ko", "ne", "nahi", "naye", "bhi", "ek",
            "yeh", "woh", "jo", "kya", "sab", "toh", "par", "ab", "tak"}
BITE = re.compile(r"\[bite:([\w-]+)\]")


def check(path, allow_pauses=False):
    """([problem lines], {new name or term: where}, {new term: the sentence it is in})"""
    bites = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), "bites.json")
    bites = json.load(open(bites, encoding="utf-8")) if os.path.exists(bites) else {}
    verified = {w.lower() for v in LEX["verified"] for w in v.split()}
    body = open(path, encoding="utf-8").read()
    common = {w.lower() for w in re.findall(r"\b[a-z][a-z]+\b", body)}  # also used lowercase
    hinglish = not re.search(r"[\u0900-\u097F]", "".join(l for l in body.splitlines() if not l.startswith("#")))
    preset = json.load(open(os.path.join(ROOT, "productions", "voice-preset.json")))
    if hinglish and not preset.get("language_code"):
        problems_pre = [f"the narration is in Roman letters, but {preset['model_id']} can't be told it is Hindi and half-reads "
                        "it as English (owner, 2026-10-29): write it in Devanagari, English words in Latin letters"]
    else:
        problems_pre = []
    problems, new_terms, ctx, sec = problems_pre, {}, {}, None
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if line.startswith("## "):
            sec = line[3:].strip()
            continue
        if line.startswith("#") or not line.strip():
            continue
        where = f"{sec} (line {n})"
        for name in BITE.findall(line):
            if name not in bites:
                problems.append(f"{where}: [bite:{name}] is not defined in bites.json")
        text = BITE.sub(" ", line)
        for w, fix in LEX["replace"].items():
            if re.search(rf"(?<![\wऀ-ॿ]){re.escape(w)}(?![\wऀ-ॿ])", text):
                problems.append(f"{where}: '{w}' -> {fix['use']}  ({fix['why']})")
        if not allow_pauses and re.search(r"\.\.\.|…|—|–", text):
            problems.append(f"{where}: pause mark ('...', '…' or a dash): use a comma, the voice never waits")
        for m in re.findall(r"[%×~&@#/+=<>]+" if hinglish else r"[0-9%×~&@#/+=<>]+", text):
            problems.append(f"{where}: '{m}': write numbers and symbols as words")
        for m in re.findall(r"\b(?=\w*[A-Za-z])(?=\w*\d)[\w-]{3,}\b", text):
            problems.append(f"{where}: catalogue code '{m}': say what it is, put the name on screen")
        for m in re.findall(r"\b[A-Z]{2,}\b", text):
            if m not in LEX["acronyms_ok"] and m not in LEX["replace"]:
                problems.append(f"{where}: acronym '{m}': write it the way it is said, in Devanagari (e.g. बाइसेप)")
        for m in ([] if hinglish else re.findall(r"\b[a-z]+\b", text)):
            if m in HINGLISH:
                problems.append(f"{where}: '{m}' is Hindi in Latin letters: write it in Devanagari")
        for s in re.split(r"[।?!.][\"”]?\s", text):
            if len(s.split()) > 28:
                problems.append(f"{where}: a {len(s.split())}-word sentence: split it (long sentences lose their tune)")
        for m in re.finditer(r"\b[A-Z][\w'’]*(?:\s+[A-Z][\w'’]*)*", text):  # names and English terms never heard yet
            t = m.group(0)
            if hinglish and re.search(r"(^|[.?!।\"]\s*)$", text[:m.start()]):  # a sentence's first word: drop it
                t = " ".join(t.split()[1:])
                if not t:
                    continue
            if any(w.lower() not in verified | common for w in t.split()) and not t.isupper():
                new_terms.setdefault(t, where)
                ctx.setdefault(t, next(x for x in re.split(r"(?<=[।?!])\s+", text.strip()) if t in x))
    return problems, new_terms, ctx


def main():
    path = sys.argv[1]
    problems, new_terms, _ = check(path, "--allow-pauses" in sys.argv)
    for p in problems:
        print("FLAG", p)
    if new_terms:
        print("never heard yet (probe first: python scripts/elevenlabs/probe_words.py " + path + "):")
        for t, where in new_terms.items():
            print(f"  {t}   ({where})")
    print(f"{len(problems)} problems, {len(new_terms)} new names/terms")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
