#!/usr/bin/env python3
"""Batch fuzzy lead-finder: run discogs.find() over a playlist's unresolved picks.

Run from a playlist's research/ dir. With no args it searches every pick that isn't yet
verified (status != 'verified' in verified.json); or pass specific ranks. For each it prints
ranked Discogs candidates so you can choose release_ids for overrides.json. Generalises the
old per-playlist leads.py/refine.py — the search itself is `discogs.find` (free-text q= with
spacing/text-speak variants + a release_title title-only pass + year/label scoring).

Usage:  DISCOGS_TOKEN=... python3 leads.py            # every unresolved pick
        DISCOGS_TOKEN=... python3 leads.py 22 66 93   # only these ranks
"""
import json, os, pathlib, re, sys
HERE = pathlib.Path.cwd()                               # run from the playlist's research/ dir
sys.path.insert(0, str(pathlib.Path(__file__).parent))  # discogs.py is a skill sibling
import discogs
discogs.TOKEN = os.environ.get("DISCOGS_TOKEN") or discogs.find_token()

PICKS = {p["rank"]: p for p in json.load(open(HERE / "picks.json"))["picks"]}
want = set(int(a) for a in sys.argv[1:] if a.isdigit())
if not want:
    V = json.load(open(HERE / "verified.json")) if (HERE / "verified.json").exists() else []
    want = {r["rank"] for r in V if r.get("status") != "verified"}
    if not want:
        sys.exit("All picks resolved. Pass ranks to search anyway, e.g. leads.py 22 66 93")

def primary(a):   # the lead artist, minus featured/joined names — helps the q= angle
    a = re.split(r"\s+(?:feat\.?|ft\.?|featuring|&|vs\.?|/|,)\s+", a or "", 1, flags=re.I)[0]
    return re.sub(r"^the\s+", "", a, flags=re.I).strip()
def yr4(s):
    m = re.search(r"(19|20)\d\d", s or ""); return m.group() if m else ""

for rk in sorted(want):
    p = PICKS.get(rk)
    if not p:
        continue
    print(f"\n#### #{rk}  {p['artist_listed']} – {p['track_listed']}  "
          f"(hint: {p.get('label_hint','')} {p.get('year_hint','')})")
    cands = discogs.find(primary(p["artist_listed"]), p["track_listed"],
                         yr4(p.get("year_hint", "")), p.get("label_hint", ""))
    for r in cands[:8]:
        print(f"   {r['_s']:>3} | {discogs.fmt_result(r)}")
    if not cands:
        print("   NO RESULTS — try spelling variants, the bare title, or a compilation by hand")
