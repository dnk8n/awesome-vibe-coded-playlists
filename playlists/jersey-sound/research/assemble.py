#!/usr/bin/env python3
"""Assemble the Jersey Sound playlist: slot verified rows by true year, rank, pick
3/year, YouTube ladder from stored page videos, emit md + items json.
Regenerates everything ABOVE the hand-curated marker in jersey-sound.md; the
Provenance / accounting sections below the marker are preserved verbatim."""
import json, pathlib, re, sys, unicodedata
HERE = pathlib.Path(__file__).parent
for _p in (HERE / "../../../skill/discogs-playlist/scripts",
           pathlib.Path.home() / ".claude/skills/discogs-playlist/scripts"):
    if _p.exists():
        sys.path.insert(0, str(_p.resolve())); break
import discogs
discogs.TOKEN = discogs.find_token()
REPO = HERE.parent

rows = json.load(open(HERE / "verified_final.json"))
# late additions fetched inline
for key, rid, tags, note in [
    ("2004|Blaze Presents Underground Dance Artists United For Life Feat. Barbara Tucker|Most Precious Love (Dennis Ferrer Remixes)",
     356666, "NJ,SB", "the UDAUFL anthem - US King Street original"),
    ("1964|Marvin Gaye|How Sweet It Is (To Be Loved By You)", 6773229, "SB", "Tamla 45"),
]:
    rel = discogs.call(f"/releases/{rid}")
    if rel:
        rows.append({"key": key, "year": int(key.split("|")[0]), "artist_q": key.split("|")[1],
                     "track_q": key.split("|")[2], "tags": tags, "note": note,
                     "release_id": rid, "credit": discogs.credit(rel.get("artists")),
                     "title": rel.get("title"), "released": rel.get("released") or str(rel.get("year","")),
                     "rel_year": rel.get("year"),
                     "labels": [f"{l['name']} {l.get('catno','')}".strip() for l in rel.get("labels", [])[:2]],
                     "url": rel.get("uri"), "styles": rel.get("styles", []),
                     "tracklist": [t.get("title","") for t in rel.get("tracklist", [])][:20],
                     "videos": [{"id": discogs.yt_id(v.get("uri")), "title": v.get("title",""),
                                 "dur": v.get("duration",0)} for v in rel.get("videos", [])
                                if discogs.yt_id(v.get("uri"))][:15],
                     "year_match": True})

V2_TRACKS = {43497:"Stomp (Move Jump Jack Your Body)",61323:"Love So Special",199959:"Get It Off",
 22684:"Follow Me",43801:"Hideaway",237678:"Why We Sing",4434845:"Love Sensation",7469110:"Waterfall",
 2535620:"At The Club",35924557:"Inside The Shelter",9145353:"Body 'N Deep",9604326:"Hostile Takeover",
 13507589:"Turn Me On",37716645:"My My Lover",14786745:"Stand On The Word",980171:"Church Lady",
 96320:"So Into You",4346:"When I Get Away From Here",8826:"Deconstructed House",75493:"Little Girl",
 38160:"My Beat",23021456:"Never Thought",1589585:"Kong"}
TRACK_PICK = {  # release-level rows -> the cut
 "1993|Kerri Chandler|Climax 1": "Climax 1",
 "2022|Kerri Chandler|Spaces And Places": "You Get Lost In It",
 "2023|Demuir Featuring Bluey Robinson / DJ Sneak|Organized Kaoz EP 3": "Lusting U",
 "1992|Kerri Chandler|Panic E.P.": "Panic",
}
STOP = {"mix","remix","original","version","edit","extended","the","a","feat","featuring"}
def ntok(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii","ignore").decode().lower()
    s = re.sub(r"[.']","",s)
    return [w for w in re.findall(r"[a-z0-9]+", s) if w]
def tin(needle, hay, drop=False):
    nt = ntok(needle)
    if drop: nt = [w for w in nt if w not in STOP] or nt
    return bool(nt) and all(w in set(ntok(hay)) for w in nt)
def base(t): 
    b = re.sub(r"\s*\(.*?\)\s*"," ",t or "").strip(" -"); return b or (t or "")

def choose_track(r):
    forced = TRACK_PICK.get(r["key"]) or V2_TRACKS.get(r.get("release_id"))
    tl = r.get("tracklist") or []
    if forced:
        for t in tl:
            if tin(forced, t, drop=True): return t, True
        return forced, False
    tq = r["track_q"]
    for t in tl:
        if tin(tq, t) or tin(t, tq): return t, True
    for t in tl:
        if tin(base(tq), t, drop=True): return t, True
    return (tl[0], False) if tl else (tq, False)

def yt_pick(r, track):
    vids = [v for v in (r.get("videos") or []) if v["id"]]
    short = [v for v in vids if (v.get("dur") or 0) <= 900]
    for v in short:
        if tin(track, v["title"]): return v, "exact"
    for v in short:
        if tin(base(track), v["title"], drop=True): return v, "close"
    for t in (r.get("tracklist") or []):
        for v in short:
            if tin(base(t), v["title"], drop=True): return v, "alternate"
    return None, "none"
TIER = {"exact":5,"close":4,"alternate":3,"none":1}

def rank(r):
    tags = r.get("tags","")
    s = 0
    if "ANCHOR" in tags: s -= 1000
    if "V2" in tags: s -= 50
    if not r.get("release_id"): s += 500
    if r.get("rel_year") != r["year"] and r.get("rel_year"): s += 0  # year already reslotted
    if "NJ" in tags: s -= 30
    if "TH" in tags: s -= 20
    if "SB" in tags: s -= 10
    return s

byyear = {}
for r in rows:
    if not r.get("release_id"): continue
    y = r.get("rel_year") or r["year"]
    if not isinstance(y, int): continue
    byyear.setdefault(y, []).append(r)

picks, bench, gaps = [], [], []
for y in range(1960, 2027):
    cands = sorted(byyear.get(y, []), key=rank)
    seen_rel = set()
    main = []
    for c in cands:
        if c["release_id"] in seen_rel: continue
        seen_rel.add(c["release_id"])
        (main if len(main) < 3 else bench).append(c)
    picks.extend(main)
    if len(main) < 3:
        gaps.append((y, 3 - len(main)))

# build items + md rows
items, mdrows = [], []
for r in sorted(picks, key=lambda x: (x.get("rel_year") or x["year"], x.get("released") or "")):
    track, tmatched = choose_track(r)
    v, match = yt_pick(r, track)
    rating = TIER[match]
    y = r.get("rel_year") or r["year"]
    tagnote = []
    if "NJ" in r.get("tags",""): tagnote.append("NJ")
    if "TH" in r.get("tags",""): tagnote.append("TH")
    if "ANCHOR" in r.get("tags",""): tagnote.append("ANCHOR")
    notes = (("["+ "/".join(tagnote) + "] ") if tagnote else "") + (r.get("note") or "")
    if not tmatched: notes += " 🎧 track pick from release needs ear-check"
    if match == "alternate" and v: notes += f" ▶ page video is '{v['title'][:40]}'"
    if match == "none": notes += " ▶ no usable page video"
    rel = (r.get("released") or str(y)).replace("-00","")
    lab = re.sub(r"\s*\(\d+\)","", "; ".join(r.get("labels", [])[:1])) or "Discogs"
    ytcell = f"[▶ Watch](https://youtu.be/{v['id']})" if v else "—"
    mdrows.append(f"| {rel} | {r['credit']} | {track} | [{lab}]({r['url']}) | {ytcell} | {notes.strip()} | {'✅ Verified' if tmatched else '✅ Verified · 🎧'} |")
    item = {"position": len(items)+1, "video_id": v["id"] if v else None,
            "youtube_url": f"https://www.youtube.com/watch?v={v['id']}" if v else None,
            "label": f"{y} · {r['credit']} – {track}", "artist": r["credit"], "track": track,
            "release": r.get("title"), "release_label": lab, "released": rel, "year": y,
            "discogs_release_id": r["release_id"], "discogs_url": r["url"],
            "video_title": v["title"] if v else None, "match": match,
            "rating": rating, "duration_seconds": (v.get("dur") if v else None)}
    items.append(item)

doc = {"schema": "discogs-playlist/v1",
       "playlist": {"title": "Jersey Sound (1982-2026) — A 67-Year Lineage (including proto-era, 1960-1982)",
                    "description": "The Jersey Sound, centered on Tony Humphries — Club Zanzibar resident, KISS-FM Mastermix — traced from soul/gospel/disco roots (1960) to today. 3 tracks per year, Discogs-verified; his mix credits thread the decades. Built with the discogs-playlist skill (see https://github.com/dnk8n/awesome-vibe-coded-playlists/tree/main/playlists/jersey-sound); v3 of the Jersey Sound project.",
                    "privacy": "public",
                    "playlist_id": "PLWrSMxL0SS2E",
                    "url": "https://www.youtube.com/playlist?list=PLWrSMxL0SS2E"},
       "source_of_truth": "discogs.com release pages (videos[]); per-item match notes deviations",
       "order": "chronological by verified Discogs release year",
       "generated_at": "2026-07-19",
       "validation": {"method": "YouTube Data API v3 videos.list", "validated_at": None, "result": "pending"},
       "items": items}
REPO.mkdir(parents=True, exist_ok=True)
(REPO / "playlist_items.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))

hdr = """# Jersey Sound — A 67-Year Lineage (1960–2026)

Three tracks per year tracing the **Jersey Sound** — Club Zanzibar, Newark NJ, resident DJ
Tony Humphries — back through its soul/gospel/disco roots (proto years favour the
Zanzibar/garage songbook; New Jersey-native artists tagged) and forward to today. The
brief locked **Kerri Chandler – Climax 1** (Atmosphere E.P. Vol. 1, Shelter, 1993) as its
anchor, with **Hardrive – Deep Inside** as podium silver. Jersey Club (the 2000s Newark
genre — same city, different music) is excluded. Every row was verified against the
Discogs API; YouTube links come from each release page's own community-added videos.
Built with the [discogs-playlist skill](../../skill/discogs-playlist/) — and built
**twice, independently**: see [Provenance](#provenance--this-canon-was-built-twice) at
the end of this document for how the two builds converged, and
[the full accounting](#the-original-lineup--a-full-accounting) of every original pick.

**Legend:** [NJ] New Jersey artist/label · [TH] Tony Humphries association · [ANCHOR]
locked by the brief · 🎧 release verified, but the cut picked off it deserves an ear-check

**The center of this canon is not a record — it is Tony Humphries.** The Zanzibar
resident (1982–early '90s), the KISS-FM Mastermix, the mix credits threaded through the
decades: his own *Master Mix Medley* (1982), the Joubert Singers (1985), *Ma Foom Bey*
(1986), Intense (1990), *Feel The Light* (1996), *Hostile Takeover* on his own TR Records
(2013), his Nina Simone dub (2019), and the 2026 *Running Back Mastermix* cut from his
own DAT archive. The [TH] tag marks his hand; the two records most often argued as THE
central track — *Climax 1* (the brief's anchor) and *Let The Rain Come Down* (the scene's
own Top 100 #1, mixed by Humphries) — hold their years as era-peaks in his orbit.
(Curator's call: Dean Kayton, July 2026.)

| Release Date | Artist | Track | Link | YouTube | Notes | Status/Progress |
|---|---|---|---|---|---|---|
"""
tail = "\n\n## Open slots\n\n" + "\n".join(f"- **{y}**: {n} slot(s) unfilled" for y, n in gaps) if gaps else ""
tail += "\n\n## Bench (verified near-misses)\n\n" + "\n".join(
    f"- {b.get('rel_year')} · {b.get('credit')} – {b.get('title')} ([Discogs]({b.get('url')}))"
    for b in sorted(bench, key=lambda x: x.get("rel_year") or 0) if b.get("release_id"))[:6000]
MARKER = "<!-- hand-curated: everything below this line is preserved by research/assemble.py -->"
out = REPO / "jersey-sound.md"
curated = ""
if out.exists() and MARKER in (prev := out.read_text()):
    curated = "\n\n" + MARKER + prev.split(MARKER, 1)[1].rstrip() + "\n"
out.write_text(hdr + "\n".join(mdrows) + tail + (curated or "\n"))
print(f"main picks: {len(picks)} | bench: {len(bench)} | gap years: {len(gaps)}")
print("gaps:", gaps)
