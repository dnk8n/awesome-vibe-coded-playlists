#!/usr/bin/env python3
"""Second-pass search for still-unresolved picks: strip feat./ft./&/vs suffixes
and search the PRIMARY artist only (+ base track, + artist-only), print candidates."""
import json, pathlib, re, sys, unicodedata
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str((pathlib.Path.home()/".claude/skills/discogs-playlist/scripts").resolve()))
import discogs, os
discogs.TOKEN = os.environ.get("DISCOGS_TOKEN") or discogs.find_token()
PICKS = {p["rank"]: p for p in json.load(open(HERE/"picks.json"))["picks"]}
def norm(s): return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()).strip()
def toks(s): return set(w for w in norm(s).split() if w)
def base(t): b=re.sub(r"\s*\(.*?\)\s*"," ",t or "").strip(" -"); return b or (t or "")
def primary(a):
    a = re.split(r"\s+(?:feat\.?|ft\.?|featuring|&|vs\.?|/|,)\s+", a, 1, flags=re.I)[0]
    return re.sub(r"^the\s+","",a,flags=re.I).strip()
def yh(s):
    m=re.search(r"(19|20)\d\d",s or ""); return int(m.group()) if m else None
def go(rk):
    p=PICKS[rk]; art=primary(p["artist_listed"]); tr=p["track_listed"]; yr=yh(p.get("year_hint",""))
    seen,out=set(),[]
    for pr in [{"artist":art,"track":base(tr)},{"q":f"{art} {base(tr)}"},{"artist":art},{"q":f"{art} {tr}"}]:
        d=discogs.call("/database/search",{**pr,"type":"release","per_page":"15"}) or {}
        for r in d.get("results",[]):
            if r["id"] in seen: continue
            seen.add(r["id"]); out.append(r)
    at,tt=toks(art),toks(base(tr))
    for r in out:
        s=0; title=r.get("title",""); tl=toks(title)
        rart=title.split(" - ")[0] if " - " in title else ""
        if at and at<=toks(rart): s+=50
        elif at and at & tl: s+=20
        if tt and tt<=tl: s+=45
        ry=r.get("year")
        try: ry=int(ry)
        except: ry=None
        if yr and ry: s+= 120 if ry==yr else 70 if abs(ry-yr)==1 else 30 if abs(ry-yr)==2 else -6*abs(ry-yr)
        if "compilation" in norm(" ".join(r.get("format",[]))) or "various" in norm(rart): s-=40
        r["_s"]=s; r["_ry"]=ry
    out.sort(key=lambda r:(-r["_s"],r["_ry"] or 9999))
    print(f"\n#### #{rk}  {p['artist_listed']} – {tr}  [primary='{art}' hint {p.get('label_hint','')} {p.get('year_hint','')}]")
    for r in out[:6]:
        print(f"   {r['_s']:>4} | {r['id']:>9} | {r.get('year','?')} | {','.join(r.get('label',[])[:1]):<20.20} | "
              f"{','.join(r.get('format',[])[:2]):<14.14} | {r['title'][:60]}")
    if not out: print("   (no results)")
for rk in [int(a) for a in sys.argv[1:] if a.isdigit()]:
    go(rk)
