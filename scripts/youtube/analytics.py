"""Retention and reach of a published science-channel video, on file next to its production.

  python analytics.py retention <video_id> productions/NN-slug [--out retention.md] [--label 7d]
                      [--from-json curve.json] [--save-json raw.json] [--audience ORGANIC]
  python analytics.py summary <video_id> productions/NN-slug [--out stats.md] [--label 48h]
                      [--impressions 12400 --ctr 4.8] [--from-json summary.json] [--save-json raw.json]

retention: the 100-point audience-retention curve (audienceWatchRatio and relativeRetentionPerformance by
  elapsedVideoTimeRatio) joined to the production's cutlist.json -> retention.md: Intro % (still watching at 30 s),
  the 5 steepest drops after 30 s with the line spoken, the shot and the on-screen text, spikes (rewatches),
  retention per chapter and the relative band against YouTube's similar-length videos.
summary: views, watch time, average view duration and %, likes, subscribers, and views by traffic source,
  appended to stats.md as a dated section. Impressions and CTR are not in the Analytics API: type them in from
  Studio (Reach tab) with --impressions/--ctr.

--from-json reads a saved API response instead of calling YouTube (offline; also the test path):
  retention: {"columnHeaders": [{"name": "elapsedVideoTimeRatio"}, {"name": "audienceWatchRatio"},
              {"name": "relativeRetentionPerformance"}], "rows": [[0.01, 1.0, 0.52], ...]}
  summary:   {"totals": <response with views, ... columns>, "traffic": <response by insightTrafficSourceType>}
--save-json stores the live response in that shape, so a report can be re-made offline.

Needs the yt-analytics.readonly scope: `upload_youtube.py auth-url --analytics`, sign in with the channel's
account, then `upload_youtube.py exchange "<redirect URL>"` (the new token keeps the upload scopes). Credentials
come from upload_youtube.env() and are never printed. Act on patterns seen in 2+ videos, not on one dip.
"""
import argparse, datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
API = "https://youtubeanalytics.googleapis.com/v2/reports"
SUMMARY_METRICS = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,subscribersGained"


# ---------------------------------------------------------------- data in

def query(params):
    """One Analytics API report (live). Imported lazily so --from-json never touches the network code."""
    import requests
    from upload_youtube import env, access_token
    e = env()
    missing = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not e.get(k)]
    if missing:
        raise SystemExit("missing in config/.env: " + ", ".join(missing))
    r = requests.get(API, params={"ids": "channel==MINE", **params},
                     headers={"Authorization": f"Bearer {access_token(e)}"}, timeout=60)
    if r.status_code == 403:
        raise SystemExit("403 from YouTube Analytics: the token lacks yt-analytics.readonly. Run "
                         "`upload_youtube.py auth-url --analytics`, sign in, then `exchange \"<redirect URL>\"`.")
    if r.status_code != 200:
        raise SystemExit(f"analytics query failed: {r.status_code} {r.text[:300]}")
    return r.json()


def table(resp):
    """API response -> list of dicts keyed by column name."""
    cols = [c["name"] for c in resp.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in resp.get("rows", []) or []]


def dates(since):
    return {"startDate": since or "2020-01-01", "endDate": datetime.date.today().isoformat()}


# ---------------------------------------------------------------- cutlist join

def load_cutlist(prod):
    slug = os.path.basename(os.path.normpath(prod))
    for p in (os.path.join(prod, "cutlist.json"), os.path.join(ROOT, "work", slug, "cutlist.json")):
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8")), p
    raise SystemExit(f"no cutlist.json in {prod} or work/{slug}")


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def overlapping(rows, a, b, t0="t0", t1="t1"):
    """Rows whose [t0, t1) overlaps [a, b], longest overlap first."""
    hits = [(min(b, r[t1]) - max(a, r[t0]), r) for r in rows if r[t0] < b and r[t1] > a]
    return [r for ov, r in sorted(hits, key=lambda h: -h[0])]


def ovl_text(o):
    if o["kind"] == "num":
        n = o["num"]
        return " ".join(str(n.get(k, "")) for k in ("value", "unit")).strip() + f" [{n.get('template', 'num')} card]"
    if o["kind"] in ("headline", "keyline"):
        return " / ".join(ln["text"].replace("*", "") for ln in o.get("lines", [])) + f" [{o['kind']}]"
    if o["kind"] == "footer":
        return None  # the chapter footer is on screen for the whole chapter: not an event
    return o["kind"]


def context(cl, a, b):
    """What the viewer heard and saw between a and b seconds."""
    caps = [{**c, "t0": c["t"], "t1": c.get("t1", c.get("end", c["t"]))} for c in cl.get("caps", [])]
    said = [c["text"] for c in overlapping(caps, a, b)][:2]
    shots = []
    for it in overlapping(cl.get("items", []), a, b):
        lab = it.get("shot") or it.get("clip") or "?"
        if it.get("kind") != "clip":
            lab = f"{it['kind']}{':' + it['gfx'] if it.get('gfx') else ''} ({lab})"
        if it.get("opt") not in (None, "", "default"):
            lab += f" {it['opt']}"
        shots.append(f"{lab} ({it.get('t1', 0) - it.get('t0', 0):.1f} s)")
    shown = [t for t in (ovl_text(o) for o in overlapping(cl.get("ovl", []), a, b)) if t]
    return said, shots[:2], shown[:2]


def chapters(cl):
    """[(name, start)] from the cutlist's sections, named by the chapter footer when there is one."""
    starts = {}
    for it in cl.get("items", []):
        starts.setdefault(it.get("sec", "?"), it["t0"])
    foot = [o for o in cl.get("ovl", []) if o["kind"] == "footer"]
    out = []
    for sec, t in sorted(starts.items(), key=lambda kv: kv[1]):
        f = next((o.get("right") or o.get("left") for o in foot if t - 1 <= o["t0"] <= t + 15), "")
        out.append((f"{sec}" + (f" {f.title()}" if f else ""), t))
    return out


# ---------------------------------------------------------------- retention

def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            f = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]


def pick_peaks(vals, n, min_gap=3, floor=0.0):
    """Indices of the n largest values, at least min_gap points apart, each above floor."""
    out = []
    for i in sorted(range(len(vals)), key=lambda i: -vals[i]):
        if vals[i] <= floor or len(out) >= n:
            break
        if all(abs(i - j) >= min_gap for j in out):
            out.append(i)
    return out


def band(rel):
    return "above typical" if rel > 0.66 else "below typical" if rel < 0.33 else "typical"


def retention(a):
    cl, cl_path = load_cutlist(a.prod)
    total = float(cl["total"])
    if a.from_json:
        resp = json.load(open(a.from_json, encoding="utf-8"))
    else:
        filt = f"video=={a.video_id}" + (f";audienceType=={a.audience}" if a.audience else "")
        resp = query({**dates(a.since), "metrics": "audienceWatchRatio,relativeRetentionPerformance",
                      "dimensions": "elapsedVideoTimeRatio", "filters": filt, "sort": "elapsedVideoTimeRatio"})
        if a.save_json:
            json.dump(resp, open(a.save_json, "w"), indent=1)
    rows = sorted(table(resp), key=lambda r: r["elapsedVideoTimeRatio"])
    if len(rows) < 10:
        raise SystemExit(f"only {len(rows)} retention points (a new or little-watched video has no curve yet)")
    xs = [r["elapsedVideoTimeRatio"] * total for r in rows]
    w = [float(r["audienceWatchRatio"]) for r in rows]
    rel = [float(r.get("relativeRetentionPerformance") or 0) for r in rows]
    intro = interp(xs, w, 30.0)
    rel30 = interp(xs, rel, 30.0)
    rel_mean = sum(rel) / len(rel)
    avg_pct = sum(w) / len(w)  # mean of the curve ~ average percentage viewed

    L = [f"# Retention: {os.path.basename(os.path.normpath(a.prod))}" + (f" ({a.label})" if a.label else ""),
         "",
         f"Video `{a.video_id}`, {'offline from ' + os.path.basename(a.from_json) if a.from_json else 'YouTube Analytics'}"
         f" on {datetime.date.today().isoformat()}{', audience ' + a.audience if a.audience else ''}. "
         f"Times from `{os.path.relpath(cl_path, ROOT)}` (total {mmss(total)}); "
         f"each point covers {total / len(rows):.1f} s.",
         "",
         "| Measure | Value |", "|---|---|",
         f"| Intro (still watching at 0:30) | **{intro * 100:.0f}%** |",
         f"| Mean of the curve (~ average % viewed) | {avg_pct * 100:.0f}% |",
         f"| Still watching at the end | {w[-1] * 100:.0f}% |",
         f"| Relative retention at 0:30 | {rel30:.2f} ({band(rel30)}) |",
         f"| Relative retention, whole video | {rel_mean:.2f} ({band(rel_mean)}) |",
         "",
         "Relative retention compares this video with YouTube videos of similar length (0-1, 0.5 = typical).",
         ""]

    # drops: loss between consecutive points, ranked after the intro (the Intro row covers the first 30 s)
    drop = [0.0] + [w[i - 1] - w[i] for i in range(1, len(w))]
    gate = [d if xs[i - 1 if i else 0] >= 30.0 else 0.0 for i, d in enumerate(drop)]
    med = sorted(d for d in gate if d > 0)[len([d for d in gate if d > 0]) // 2] if any(d > 0 for d in gate) else 0
    L += ["## 5 steepest drops (after 0:30)", "",
          "| When | Lost | vs usual | Line spoken | Shot | On screen |", "|---|---|---|---|---|---|"]
    for i in sorted(pick_peaks(gate, 5), key=lambda i: xs[i]):
        t0, t1 = xs[i - 1], xs[i]
        said, shots, shown = context(cl, t0, t1)
        L.append(f"| {mmss(t0)}-{mmss(t1)} | {drop[i] * 100:.1f} pts | {drop[i] / med if med else 0:.1f}x | "
                 f"{' / '.join(said) or '(no line)'} | {'; '.join(shots) or '-'} | {'; '.join(shown) or '-'} |")
    L += ["", "\"vs usual\" = this drop over the median drop per point after 0:30.", ""]

    rise = [0.0] + [w[i] - w[i - 1] for i in range(1, len(w))]
    sp = sorted(pick_peaks(rise, 3, floor=0.002), key=lambda i: xs[i])
    L += ["## Spikes (rewatched or skipped to)", ""]
    if sp:
        L += ["| When | Gained | Line spoken | Shot | On screen |", "|---|---|---|---|---|"]
        for i in sp:
            said, shots, shown = context(cl, xs[i - 1], xs[i])
            L.append(f"| {mmss(xs[i - 1])}-{mmss(xs[i])} | +{rise[i] * 100:.1f} pts | {' / '.join(said) or '(no line)'} | "
                     f"{'; '.join(shots) or '-'} | {'; '.join(shown) or '-'} |")
    else:
        L.append("None: the curve never rises.")
    L.append("")

    ch = chapters(cl)
    L += ["## By chapter", "", "| Chapter | Starts | Watching at start | Lost in chapter | Lost per minute |",
          "|---|---|---|---|---|"]
    for k, (name, t) in enumerate(ch):
        end = ch[k + 1][1] if k + 1 < len(ch) else total
        s, e_ = interp(xs, w, max(t, xs[0])), interp(xs, w, end)
        L.append(f"| {name} | {mmss(t)} | {s * 100:.0f}% | {(s - e_) * 100:.1f} pts | "
                 f"{(s - e_) * 100 / max((end - t) / 60, 1e-6):.1f} pts |")
    L += ["", "Act on a pattern seen in 2+ videos, not on one dip."]
    out = a.out or os.path.join(a.prod, "retention.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", out)


# ---------------------------------------------------------------- summary

def summary(a):
    cl, _ = load_cutlist(a.prod)
    total = float(cl["total"])
    if a.from_json:
        raw = json.load(open(a.from_json, encoding="utf-8"))
    else:
        filt = f"video=={a.video_id}"
        raw = {"totals": query({**dates(a.since), "metrics": SUMMARY_METRICS, "filters": filt}),
               "traffic": query({**dates(a.since), "metrics": "views,estimatedMinutesWatched",
                                 "dimensions": "insightTrafficSourceType", "filters": filt, "sort": "-views"})}
        if a.save_json:
            json.dump(raw, open(a.save_json, "w"), indent=1)
    tot = (table(raw.get("totals", {})) or [{}])[0]
    traffic = sorted(table(raw.get("traffic", {})), key=lambda r: -r.get("views", 0))
    views = tot.get("views", 0) or 0
    avd = tot.get("averageViewDuration", 0) or 0
    L = [f"## {datetime.date.today().isoformat()}" + (f" ({a.label})" if a.label else "") + f": video `{a.video_id}`", "",
         "| Measure | Value |", "|---|---|",
         f"| Views | {views:,} |",
         f"| Watch time | {(tot.get('estimatedMinutesWatched', 0) or 0) / 60:,.1f} h |",
         f"| Average view duration | {mmss(avd)} of {mmss(total)} |",
         f"| Average % viewed | {tot.get('averageViewPercentage', avd / total * 100 if total else 0):.1f}% |",
         f"| Likes | {tot.get('likes', 0) or 0:,} |",
         f"| Subscribers gained | {tot.get('subscribersGained', 0) or 0:,} |"]
    if a.impressions is not None:
        L.append(f"| Impressions (Studio) | {a.impressions:,} |")
    if a.ctr is not None:
        L.append(f"| Impressions CTR (Studio) | {a.ctr:.1f}% |")
    if a.impressions is None and a.ctr is None:
        L.append("| Impressions, CTR | type in from Studio > Reach (--impressions, --ctr) |")
    if a.note:
        L.append(f"| Note | {a.note} |")
    L += ["", "| Traffic source | Views | Share | Watch time |", "|---|---|---|---|"]
    for r in traffic:
        v = r.get("views", 0) or 0
        L.append(f"| {r.get('insightTrafficSourceType', '?')} | {v:,} | {v * 100 / views if views else 0:.0f}% | "
                 f"{(r.get('estimatedMinutesWatched', 0) or 0) / 60:,.1f} h |")
    L.append("")
    out = a.out or os.path.join(a.prod, "stats.md")
    head = "" if os.path.exists(out) else (
        f"# Stats: {os.path.basename(os.path.normpath(a.prod))}\n\n"
        "One section per snapshot (48 h, 7 d, 28 d; add the A/B test result by hand).\n\n")
    with open(out, "a", encoding="utf-8") as f:
        f.write(head + "\n".join(L) + "\n")
    print("appended to", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("retention", "summary"):
        p = sub.add_parser(name)
        p.add_argument("video_id")
        p.add_argument("prod", help="production directory (productions/NN-slug); cutlist.json there or in work/NN-slug")
        p.add_argument("--out", default="", help=f"default <prod>/{'retention' if name == 'retention' else 'stats'}.md")
        p.add_argument("--label", default="", help="snapshot label, e.g. 48h, 7d, 28d")
        p.add_argument("--from-json", default="", help="saved API response: offline, no network call")
        p.add_argument("--save-json", default="", help="also save the live API response here")
        p.add_argument("--since", default="", help="startDate (default 2020-01-01; the end is today)")
        if name == "retention":
            p.add_argument("--audience", default="", choices=["", "ORGANIC", "AD_INSTREAM", "AD_INDISPLAY"])
        else:
            p.add_argument("--impressions", type=int, default=None, help="from Studio > Reach")
            p.add_argument("--ctr", type=float, default=None, help="impressions click-through rate %%, from Studio")
            p.add_argument("--note", default="", help="e.g. the A/B test result")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", a.video_id):
        raise SystemExit(f"not a video id: {a.video_id}")
    retention(a) if a.cmd == "retention" else summary(a)


if __name__ == "__main__":
    main()
