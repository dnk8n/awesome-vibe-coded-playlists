#!/usr/bin/env python3
"""Targeted Discogs lead-finder for the picks flagged in audit.py.

Searches each given rank with several strategies (artist+track, q=, label filter,
year filter) and prints the top candidates with a score, so a human can choose the
right release_id and record it in overrides.json. Prefers ORIGINAL singles over
compilations. Usage: python3 leads.py 22 45 53 80 ...   (default: a built-in list)
"""
import json, pathlib, re, sys, unicodedata
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str((pathlib.Path.home()/".claude/skills/discogs-playlist/scripts").resolve()))
import discogs, os
discogs.TOKEN = os.environ.get("DISCOGS_TOKEN") or discogs.find_token()
PICKS = {p["rank"]: p for p in json.load(open(HERE/"picks.json"))["picks"]}

def norm(s): return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()).strip()
def toks(s): return set(w for w in norm(s).split() if w)
def base(t): b=re.sub(r"\s*\(.*?\)\s*"," ",t or "").strip(" -"); return b or (t or "")
def yh(s):
    m=re.search(r"(19|20)\d\d",s or ""); return int(m.group()) if m else None

def run(artist, track, year, label):
    seen, out = set(), []
    strat = [
        {"artist": artist, "track": base(track)},
        {"artist": artist, "release_title": base(track)},
        {"q": f"{artist} {base(track)}"},
        {"artist": artist},
    ]
    if label and "acetate" not in label.lower():
        strat.insert(0, {"artist": artist, "track": base(track), "label": label})
    for pr in strat:
        d = discogs.call("/database/search", {**pr, "type":"release", "per_page":"12"}) or {}
        for r in d.get("results", []):
            if r["id"] in seen: continue
            seen.add(r["id"]); out.append(r)
    at, tt = toks(artist), toks(base(track))
    for r in out:
        s=0; title=r.get("title",""); tl=toks(title)
        rart = title.split(" - ")[0] if " - " in title else ""
        if at and at & toks(rart): s+=45
        elif at and at & tl: s+=20
        if tt and tt <= tl: s+=40
        ry=r.get("year")
        try: ry=int(ry)
        except: ry=None
        if year and ry: s += 120 if ry==year else 70 if abs(ry-year)==1 else 30 if abs(ry-year)==2 else -8*abs(ry-year)
        fmt=norm(" ".join(r.get("format",[])))
        if "compilation" in fmt or "various" in norm(rart): s-=50
        if "vinyl" in fmt or "12" in fmt: s+=12
        r["_s"]=s; r["_ry"]=ry
    out.sort(key=lambda r:(-r["_s"], r["_ry"] or 9999))
    return out

ranks = [int(a) for a in sys.argv[1:] if a.isdigit()] or sorted(PICKS)
for rk in ranks:
    p = PICKS[rk]; art = p["artist_listed"]; tr = p["track_listed"]
    print(f"\n#### #{rk}  {art} – {tr}   (hint: {p.get('label_hint','')} {p.get('year_hint','')})")
    for r in run(art, tr, yh(p.get("year_hint","")), p.get("label_hint",""))[:6]:
        print(f"   {r['_s']:>4} | {r['id']:>9} | {r.get('year','?')} | {','.join(r.get('label',[])[:1]):<22.22} | "
              f"{','.join(r.get('format',[])[:2]):<16.16} | {r['title'][:64]}")
