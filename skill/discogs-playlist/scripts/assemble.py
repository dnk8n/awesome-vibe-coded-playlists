#!/usr/bin/env python3
"""Assemble the playlist markdown doc + items file from enriched.json.

Run from a playlist's research/ dir. Reads config.json (output_md filename + playlist
title/description/privacy), article.md (prose, spliced at <!-- INSERT_TABLE_HERE -->),
enriched.json, and curator.json (video_pick / video_note / rating_override). Writes the
composed markdown to ../<output_md> and ../playlist_items.json (discogs-playlist/v1).

Renders the date-sorted table — Artist/Track taken char-for-char from Discogs, master
link, YouTube from the page-video ladder, deviation + curator Notes, and a ★ Confidence
rating — plus a research queue for any unresolved rows. Rating precedence: curator
rating_override, else min(video-match tier, track-cut tier); <5 flags a slot to revisit.
"""
import json, pathlib, re, unicodedata

HERE = pathlib.Path.cwd()          # run from the playlist's research/ dir (data lives here)
REPO = HERE.parent                 # the playlist dir (public .md + items.json go here)
CFG = json.load(open(HERE / "config.json"))
V = json.load(open(HERE / "enriched.json"))

STOP = {"mix","remix","original","version","edit","extended","the","a","feat","featuring","vocal","dub"}
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[.']","",s)
def ntok(s): return [w for w in re.findall(r"[a-z0-9]+", norm(s)) if w]
def tin(needle, hay, drop=False):
    nt = ntok(needle)
    if drop: nt = [w for w in nt if w not in STOP] or nt
    return bool(nt) and all(w in set(ntok(hay)) for w in nt)
def base(t): b = re.sub(r"\s*\(.*?\)\s*"," ",t or "").strip(" -"); return b or (t or "")

# YouTube embeds that failed yt_verify.py (dead/private) — never pick these
DEAD_VIDEOS = {"NB5d3M-oThI", "rIixdotQTSI", "yCvzviAfxPA"}
# hand-picked replacements (validated page videos from the same release), by rank
VIDEO_OVERRIDE = {94: "vuHhiryzt6E", 43: "KJUnyfKsw7k", 51: "Ly32T1huzgQ"}
# fix_dead.py appends newly-discovered dead embeds + validated replacements here
_fx = HERE / "video_fixes.json"
if _fx.exists():
    _f = json.load(open(_fx))
    DEAD_VIDEOS |= set(_f.get("dead", []))
    VIDEO_OVERRIDE.update({int(k): v for k, v in _f.get("override", {}).items()})
# curator's explicit video choices (highest precedence) + factual video notes
_cur = json.load(open(HERE / "curator.json")) if (HERE / "curator.json").exists() else {}
CURATOR_VIDEO = {int(k): v for k, v in _cur.get("video_pick", {}).items()}
VIDEO_NOTE = _cur.get("video_note", {})
RATING_OVERRIDE = {int(k): int(v) for k, v in _cur.get("rating_override", {}).items()}  # hand-set after listening

def yt_pick(videos, track):
    vids = [v for v in (videos or []) if v.get("id") and v["id"] not in DEAD_VIDEOS]
    short = [v for v in vids if (v.get("dur") or 0) <= 900]
    longrip = [v for v in vids if (v.get("dur") or 0) > 900]
    for v in short:
        if tin(track, v["title"]): return v, "exact"
    for v in short:
        if tin(base(track), v["title"], drop=True): return v, "close"
    if short: return short[0], "alternate"
    for v in longrip:
        if tin(track, v["title"]) or tin(base(track), v["title"], drop=True): return v, "longrip"
    return None, "none"
TIER = {"exact":5,"close":4,"alternate":3,"longrip":1,"none":1}

def yhint(s):
    m = re.search(r"(19|20)\d\d", s or ""); return int(m.group()) if m else 9999
def sort_year(row):
    return row.get("chosen_year") or row.get("rel_year") or yhint(row.get("year_hint",""))
def rel_str(row):
    return (row.get("released2") or str(row.get("chosen_year") or "") or row.get("year_hint","")).replace("-00","")

rows = sorted(V, key=lambda r: (sort_year(r), rel_str(r), r["rank"]))

mdrows, items, queue = [], [], []
for row in rows:
    rank = row["rank"]
    al, tl_ = row["artist_listed"], row["track_listed"]
    fill = row.get("fill", False)
    ann = row.get("annotation","")
    if row.get("status") != "verified":
        st = row.get("status")
        default = {"queue-acetate": "acetate/demo — likely no catalogued release",
                   "needs-token": "pending Discogs search",
                   "fetch-failed": "release fetch failed — retry"}.get(st, "no confident Discogs match")
        note = ann or default
        badge = "[FILL] " if fill else ""
        mdrows.append(f"| {rank} | {row.get('year_hint','?')} | {al} | {tl_} | — | — | {badge}🔎 {note} | 🔎 Open |")
        cand = row.get("candidates", [])
        cstr = "; ".join(f"[{c['id']}] {c['title']} ({c.get('year')})" for c in cand[:4]) if cand else "search manually"
        queue.append(f"- **#{rank} {al} – {tl_}** ({row.get('label_hint','')} {row.get('year_hint','')}) — {st}; candidates: {cstr}")
        continue

    track = row.get("chosen_track") or tl_          # exact Discogs tracklist item
    art = row.get("chosen_artist") or al            # Discogs artist (source of truth)
    ttier = row.get("track_tier", 5)                 # how well the cut matches the club-preference
    v, match = yt_pick(row.get("videos_src"), track)
    curator_vid = False
    if rank in CURATOR_VIDEO:                         # curator hand-picked this video
        vid = CURATOR_VIDEO[rank]
        v = next((x for x in (row.get("videos_src") or []) if x.get("id") == vid), None) \
            or {"id": vid, "title": "(curator-selected)", "dur": 0}
        match, curator_vid = "curator", True
    elif rank in VIDEO_OVERRIDE:                      # swap a dead auto-pick for a validated page alternate
        ov = next((x for x in (row.get("videos_src") or []) if x.get("id") == VIDEO_OVERRIDE[rank]), None)
        if ov: v, match = ov, ("exact" if tin(track, ov["title"]) else "close")
    vtier = 5 if curator_vid else TIER[match]
    rating = min(vtier, ttier)                        # <5 flags a slot to hunt alternatives for
    rating = RATING_OVERRIDE.get(rank, rating)         # curator's hand-set rating wins
    y = sort_year(row)
    rel = rel_str(row)
    url = row.get("chosen_url"); link_text = row.get("link_text") or "Discogs"

    n = []
    if fill: n.append("**[FILL]**")
    if ann: n.append(ann)
    for eb in row.get("enrich_notes", []): n.append(eb)
    if str(rank) in VIDEO_NOTE: n.append("▶ " + VIDEO_NOTE[str(rank)])
    if not curator_vid:
        if match == "alternate" and v and str(rank) not in VIDEO_NOTE:  # a curator video_note supersedes it
            n.append(f"▶ page video is '{v['title'][:38]}'")
        if match == "longrip" and v: n.append("▶ only a >15-min full rip on the page — not added to the playlist")
        if match == "none": n.append("▶ no usable page video")
    notes = " · ".join(n)
    ytcell = f"[▶ Watch](https://youtu.be/{v['id']})" if v and match != "longrip" else "—"
    stars = "★"*rating + "☆"*(5-rating)              # 5 = ideal cut+video; <5 = revisit
    mdrows.append(f"| {rank} | {rel} | {art} | {track} | [{link_text}]({url}) | {ytcell} | {notes} | ✅ {stars} |")
    if v and match != "longrip":
        items.append({"position": len(items)+1, "rank": rank, "video_id": v["id"],
                      "youtube_url": f"https://www.youtube.com/watch?v={v['id']}",
                      "label": f"#{rank} · {art} – {track}", "artist": art, "artist_prompt": al, "track_prompt": tl_,
                      "discogs_track": track, "discogs_credit": row.get("chosen_credit"),
                      "chosen_page": row.get("chosen_page"), "release": row.get("title"),
                      "discogs_url": url, "discogs_release_id": row["release_id"],
                      "master_id": row.get("master_id") or None, "released": rel, "year": y,
                      "video_title": v["title"], "match": match, "rating": rating,
                      "duration_seconds": v.get("dur"), "fill": fill})

TABLE = ("| Rank | Released | Artist | Track | Discogs | YouTube | Notes | Confidence |\n"
         "|---|---|---|---|---|---|---|---|\n" + "\n".join(mdrows))
if queue:
    TABLE += ("\n\n## Research queue — unverified slots\n\n"
              "Entries the source lists that lack a confident Discogs release (several were pressed "
              "only as acetates/demos). Kept visible above as open rows; leads for a manual pass:\n\n"
              + "\n".join(queue))

# The YouTube playlist id/url are DURABLE source-of-truth in config.json's playlist block.
# (Migration) if config lacks them but an older items file has them, adopt them.
plmeta = dict(CFG["playlist"])
if not plmeta.get("playlist_id") and (REPO / "playlist_items.json").exists():
    _old = (json.load(open(REPO / "playlist_items.json")).get("playlist") or {})
    plmeta.setdefault("playlist_id", _old.get("playlist_id"))
    plmeta.setdefault("url", _old.get("url"))

art = (HERE / "article.md").read_text()
doc = art.replace("<!-- INSERT_TABLE_HERE -->", TABLE)
if plmeta.get("url"):   # once the YouTube playlist exists, link it just under the H1 title
    doc = re.sub(r"^(#[^\n]*\n)",
                 lambda m: m.group(1) + f"\n**[▶ Listen — the full playlist on YouTube]({plmeta['url']})**\n",
                 doc, count=1)
(REPO / CFG["output_md"]).write_text(doc)

out = {"schema": "discogs-playlist/v1",
       "playlist": plmeta,
       "source_of_truth": "The Discogs master release is always linked when one exists; Artist and Track are both taken character-for-character from the master's tracklist. Track = the version the source named, else an extended/long cut, else a club cut, else the first A-side (radio/edit last). Artist = the item's Discogs credit (per-track on comps, else the master credit). A per-item ★ rating (1-5) flags sub-ideal cuts/videos to revisit.",
       "order": "chronological by the chosen Discogs master/release year; each item keeps its Top-100 rank",
       "generated_at": "2026-07-22",
       "validation": {"method": "YouTube Data API v3 videos.list", "validated_at": None, "result": "pending"},
       "items": items}
(REPO / "playlist_items.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
nver = sum(1 for r in V if r.get("status")=="verified")
nmaster = sum(1 for r in V if r.get("chosen_page")=="master")
print(f"rows: {len(V)} | verified: {nver} | master-linked: {nmaster} | playlist items: {len(items)} | queued: {len(queue)}")
