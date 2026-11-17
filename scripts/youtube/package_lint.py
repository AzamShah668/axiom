"""Lint a production's YouTube package (youtube.md). Warnings only: it always exits 0.

  python package_lint.py productions/NN-slug/youtube.md

Checks (docs/research/improve-2026-11/03-packaging.md P1-b, P2-a):
  - every title (**Title** and the optional **Titles (A/B)** block) is <= 60 characters, with the hook in the first
    45: the language/branding tag ("| Hindi Documentary", "(Hindi)") goes last
  - few ALL-CAPS words and no emoji in a title
  - description line 1 is not the title (it is the search snippet: a hook with the keyword)
  - <= 12 tags (tags matter little: the keyword, Hindi forms, misspellings)
  - credits present: footage credit, CC BY licence, music credit when music is named
  - description < 5,000 bytes with no < or > (YouTube refuses it otherwise), <= 15 hashtags, chapters from 0:00
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upload_youtube import parse_titles  # noqa: E402

TAG = re.compile(r"\s*(?:\|\s*[^|]*(?:hindi|documentary)[^|]*|\((?:in )?hindi\)|-\s*hindi\b.*)$", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def lint(path):
    s = open(path, encoding="utf-8").read()
    warn, info = [], []
    m = re.search(r"\*\*Title\*\*\s*\n(.+)", s)
    titles = ([m.group(1).strip()] if m else []) + [t for t in parse_titles(s) if not m or t != m.group(1).strip()]
    if not titles:
        warn.append("no **Title** line and no **Titles (A/B)** block")
    for t in titles:
        hook = TAG.sub("", t).strip()
        if len(t) > 60:
            warn.append(f"title is {len(t)} chars (> 60, cut off in the feed): {t}")
        if len(hook) > 45:
            warn.append(f"hook is {len(hook)} chars before the tag (> 45; mobile shows ~45): {hook}")
        if hook != t and not TAG.search(t):
            warn.append(f"language tag is not at the end: {t}")
        caps = [w for w in re.findall(r"[A-Za-z]{4,}", t) if w.isupper()]
        if len(caps) > 1:
            warn.append(f"{len(caps)} ALL-CAPS words in a title (limit them): {t}")
        if EMOJI.search(t):
            warn.append(f"emoji in a title: {t}")
        info.append(f"title {len(t)} chars, hook {len(hook)}: {t}")
    if len(titles) == 1:
        info.append("one title: an A/B test needs a **Titles (A/B)** block (T1 search, T2 number, T3 Hinglish)")

    d = re.search(r"\*\*Description\*\*\s*\n```\n(.*?)\n```", s, re.S)
    if not d:
        warn.append("no **Description** ``` block")
        desc = ""
    else:
        desc = d.group(1).strip()
        first = desc.splitlines()[0].strip() if desc else ""
        if any(norm(first) == norm(t) or norm(first).startswith(norm(TAG.sub("", t))) for t in titles):
            warn.append(f"description line 1 repeats the title (make it a hook with the keyword): {first}")
        if len(desc.encode()) > 5000:
            warn.append(f"description is {len(desc.encode())} bytes (YouTube max 5000)")
        if "<" in desc or ">" in desc:
            warn.append("description contains < or > (YouTube refuses it)")
        if not re.search(r"credit|footage", desc, re.I) or not re.search(r"\b(ESO|ESA|NASA|Hubble|Webb|Pexels)\b", desc):
            warn.append("no footage credit line (ESO / ESA/Hubble / ESA/Webb / NASA)")
        if re.search(r"\b(ESO|ESA/Hubble|ESA/Webb|Kevin MacLeod)\b", desc) and not re.search(
                r"CC BY|Creative Commons|creativecommons\.org", desc):
            warn.append("CC BY footage or music named but no licence (CC BY 4.0)")
        if re.search(r"music", desc, re.I) is None:
            warn.append("no music credit line")
        elif re.search(r"Kevin MacLeod", desc) and not re.search(r"\"[^\"]+\"", desc):
            warn.append("Kevin MacLeod music needs the exact track titles in quotes")
        tags_h = re.findall(r"(?<!\w)#\w+", desc)
        if len(tags_h) > 15:
            warn.append(f"{len(tags_h)} hashtags (> 15: YouTube ignores them all)")
        chap = re.findall(r"^(\d+:\d{2})\s+\S", desc, re.M)
        if chap and chap[0] != "0:00":
            warn.append(f"chapters must start at 0:00 (first is {chap[0]})")
        if chap and len(chap) < 3:
            warn.append("YouTube needs >= 3 chapters to show them")
        info.append(f"description {len(desc.encode())} bytes, {len(chap)} chapters, {len(tags_h)} hashtags")

    t = re.search(r"\*\*Tags\*\*\s*\n(.+)", s)
    tags = [x.strip() for x in t.group(1).split(",") if x.strip()] if t else []
    if not tags:
        warn.append("no **Tags** line")
    elif len(tags) > 12:
        warn.append(f"{len(tags)} tags (> 12: keep the keyword, Hindi forms and misspellings)")
    info.append(f"{len(tags)} tags")
    return warn, info


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for path in sys.argv[1:]:
        warn, info = lint(path)
        print(f"== {path}: {len(warn)} warning(s)")
        for w in warn:
            print("  WARN", w)
        for i in info:
            print("  ok  ", i)
    return 0


if __name__ == "__main__":
    sys.exit(main())
