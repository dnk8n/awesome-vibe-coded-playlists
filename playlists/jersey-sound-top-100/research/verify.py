#!/usr/bin/env python3
"""Verify the Jersey Sound Top 100 picks against the Discogs API.

For each pick in picks.json, resolve a Discogs release_id via:
  1. overrides.json[rank]            (hand-set corrections; highest priority)
  2. pick['known_release_id']         (seeded in picks.json, e.g. the fills)
  3. reuse from the sibling playlist's verified_final.json (artist+track match)
  4. Discogs /database/search auto-pick, scored by year_hint + label_hint

Then release-fetch the chosen id (cached in release_cache.json) as source of
truth, and write verified.json (one row per pick, in rank order) plus a
human-auditable report to stdout. Search results are LEADS ONLY; the top
candidates are stored per row so mis-picks can be corrected via overrides.json.

Usage:  python3 verify.py            # verify all
        python3 verify.py 17 42 96   # only these ranks (still writes full file)
"""
import json, pathlib, re, sys, unicodedata

HERE = pathlib.Path(__file__).parent
for _p in (HERE / "../../../skill/discogs-playlist/scripts",
           pathlib.Path.home() / ".claude/skills/discogs-playlist/scripts"):
    if _p.exists():
        sys.path.insert(0, str(_p.resolve())); break
import discogs
try:
    discogs.TOKEN = discogs.find_token()
    HAVE_TOKEN = True
except SystemExit:
    discogs.TOKEN = None  # anonymous release reads still work (25/min); search does not
    HAVE_TOKEN = False
    print("[no Discogs token — resolving only seed/reuse picks; search picks marked needs-token]", file=sys.stderr)

PICKS = json.load(open(HERE / "picks.json"))["picks"]
OVR = json.load(open(HERE / "overrides.json")) if (HERE / "overrides.json").exists() else {}
CACHE_F = HERE / "release_cache.json"
CACHE = json.load(open(CACHE_F)) if CACHE_F.exists() else {}
only = set(int(a) for a in sys.argv[1:] if a.isdigit())

# ---- reuse map from the sibling 67-year lineage (already Discogs-verified) ----
SIB = HERE / "../../jersey-sound/research/verified_final.json"
REUSE = {}
if SIB.exists():
    for r in json.load(open(SIB)):
        if r.get("release_id"):
            REUSE[(r.get("artist_q","").lower().strip(), r.get("track_q","").lower().strip())] = r["release_id"]

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()
def toks(s): return [w for w in norm(s).split() if w]
def base(t): b = re.sub(r"\s*\(.*?\)\s*", " ", t or "").strip(" -"); return b or (t or "")
def yhint(s):
    m = re.search(r"(19|20)\d\d", s or ""); return int(m.group()) if m else None

def fetch(rid):
    rid = str(rid)
    if rid in CACHE: return CACHE[rid]
    d = discogs.call(f"/releases/{rid}")
    if d:
        CACHE[rid] = {
            "release_id": int(rid), "credit": discogs.credit(d.get("artists")),
            "master_id": d.get("master_id") or 0,
            "title": d.get("title"), "released": d.get("released") or str(d.get("year","")),
            "rel_year": d.get("year"), "country": d.get("country"),
            "labels": [f"{l['name']} {l.get('catno','')}".strip() for l in d.get("labels", [])[:2]],
            "url": d.get("uri"), "styles": d.get("styles", []),
            "tracklist": [{"pos": t.get("position",""), "title": t.get("title",""),
                           "artists": discogs.credit(t.get("artists")) if t.get("artists") else ""}
                          for t in d.get("tracklist", [])],
            "videos": [{"id": discogs.yt_id(v.get("uri")), "title": v.get("title",""),
                        "dur": v.get("duration",0)} for v in d.get("videos", [])
                       if discogs.yt_id(v.get("uri"))],
        }
        json.dump(CACHE, open(CACHE_F,"w"), indent=0, ensure_ascii=False)
    return CACHE.get(rid)

def search(artist, track, year, label):
    """Return scored candidate list (dicts from Discogs search)."""
    tries = [
        {"artist": artist, "track": base(track)},
        {"q": f"{artist} {base(track)}"},
        {"release_title": base(track), "artist": artist},
    ]
    seen, cands = set(), []
    for params in tries:
        params = {**params, "type": "release", "per_page": "15"}
        d = discogs.call("/database/search", params) or {}
        for r in d.get("results", []):
            if r["id"] in seen: continue
            seen.add(r["id"]); cands.append(r)
        if len(cands) >= 8: break
    at = set(toks(artist))
    tgt = year
    for r in cands:
        s = 0
        ry = r.get("year")
        try: ry = int(ry)
        except (TypeError, ValueError): ry = None
        title = r.get("title","")
        # artist present in "Artist - Title"
        rart = title.split(" - ")[0] if " - " in title else title
        if at and at & set(toks(rart)): s += 40
        if base(track) and set(toks(base(track))) <= set(toks(title)): s += 40
        if tgt and ry:
            dy = abs(ry - tgt)
            s += 120 if dy == 0 else 70 if dy == 1 else 35 if dy == 2 else -10*dy
        if label:
            lab = " ".join(r.get("label", []))
            lt = [w for w in toks(label) if w not in ("records","record","uk","the")]
            if lt and any(w in norm(lab) for w in lt): s += 45
        fmt = norm(" ".join(r.get("format", [])))
        if "vinyl" in fmt or "12" in fmt: s += 12
        if "compilation" in fmt or "album" in fmt: s -= 6
        r["_score"] = s; r["_ry"] = ry
    cands.sort(key=lambda r: (-r["_score"], r["_ry"] or 9999))
    return cands

verified, report = [], []
for p in PICKS:
    rank = p["rank"]
    al, tl = p["artist_listed"], p["track_listed"]
    yr = yhint(p.get("year_hint",""))
    # acetates/demos have no real label to filter on; drop the hint so it doesn't hurt scoring
    lab = "" if "acetate" in p.get("label_hint","").lower() else p.get("label_hint","")
    # resolve release id (acetates/demos are searched too — they sometimes got a later pressing)
    rid, how, cands = None, "", []
    if str(rank) in OVR:
        ov = OVR[str(rank)]
        if not ov:  # override 0/null = force this slot open (searched, no clean Discogs release)
            report.append(f"#{rank:>3} {al} – {tl}: forced open (searched, no clean Discogs release)")
            verified.append({**p, "release_id": None, "status": "unresolved", "forced_open": True}); continue
        rid, how = ov, "override"
    elif p.get("known_release_id"):
        rid, how = p["known_release_id"], "seed"
    elif (norm(al) and (al.lower().strip(), tl.lower().strip()) in REUSE):
        rid, how = REUSE[(al.lower().strip(), tl.lower().strip())], "reuse"
    elif HAVE_TOKEN:
        art = p.get("credit_discrepancy") or al  # e.g. #96 search Karen Anderson
        cands = search(art, tl, yr, lab)
        if cands and cands[0]["_score"] > 40:
            rid, how = cands[0]["id"], "search"
    if not rid:
        if not HAVE_TOKEN:
            report.append(f"#{rank:>3} {al} – {tl}: needs token (search)")
            verified.append({**p, "release_id": None, "status": "needs-token"}); continue
        tops = ", ".join("{}:{}({})".format(c["id"], c["title"][:40], c["_ry"]) for c in cands[:3]) or "none"
        report.append(f"#{rank:>3} {al} – {tl}: NO CONFIDENT MATCH (top: {tops})")
        verified.append({**p, "release_id": None, "status": "unresolved",
                         "candidates": [{"id": c["id"], "title": c["title"], "year": c["_ry"],
                                         "label": c.get("label"), "score": c["_score"]} for c in cands[:5]]})
        continue
    rel = fetch(rid)
    if not rel:
        report.append(f"#{rank:>3} {al} – {tl}: FETCH FAILED for {rid}")
        verified.append({**p, "release_id": rid, "status": "fetch-failed"}); continue
    row = {**p, "release_id": rid, "resolved_by": how, **rel, "status": "verified"}
    if cands:
        row["candidates"] = [{"id": c["id"], "title": c["title"], "year": c["_ry"],
                              "label": c.get("label"), "score": c["_score"]} for c in cands[:5]]
    verified.append(row)
    nv = len([v for v in rel["videos"] if v["id"]])
    report.append(f"#{rank:>3} {al} – {tl}\n      -> [{how}] {rel['credit']} – {rel['title']} "
                  f"| {rel['released']} | {'; '.join(rel['labels'][:1])} | {nv} vids | {rel['url']}")

json.dump(verified, open(HERE / "verified.json","w"), indent=1, ensure_ascii=False)
ok = sum(1 for r in verified if r.get("status")=="verified")
print("\n".join(report))
print(f"\n=== {ok}/{len(PICKS)} verified | unresolved: "
      f"{[r['rank'] for r in verified if r.get('status')=='unresolved']} | "
      f"queued: {[r['rank'] for r in verified if r.get('status','').startswith('queue')]} ===")
