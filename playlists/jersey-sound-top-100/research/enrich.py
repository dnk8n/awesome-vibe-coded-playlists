#!/usr/bin/env python3
"""Enrich verified picks with Discogs MASTER preference + exact tracklist item.

For each verified pick (release_id resolved by verify.py):
  * fetch the release's master (if any); the chosen Discogs page = the MASTER when
    one exists, else the specific release.
  * choose ONE track from the chosen page's Tracklist, char-for-char:
      - if the source prompt named a specific version/mix, pick that item
        (from the master; if the version isn't on the master, drop to the
        sub-release that carries it and link that instead);
      - if no version was requested, prefer the 'Radio' item, else the main cut.
  * carry the exact tracklist title, the chosen page url, the page's credit, and
    any extra track info (per-track credit) for the markdown Notes.

Writes enriched.json (consumed by assemble.py). Masters cached in master_cache.json.
"""
import json, math, pathlib, re, sys, unicodedata
HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str((pathlib.Path.home()/".claude/skills/discogs-playlist/scripts").resolve()))
import discogs, os
try:
    discogs.TOKEN = os.environ.get("DISCOGS_TOKEN") or discogs.find_token()
except SystemExit:
    discogs.TOKEN = None  # master/release reads work anonymously (25/min)

V = json.load(open(HERE/"verified.json"))
RELC = json.load(open(HERE/"release_cache.json"))
MC_F = HERE/"master_cache.json"
MC = json.load(open(MC_F)) if MC_F.exists() else {}
CURATOR = json.load(open(HERE/"curator.json")) if (HERE/"curator.json").exists() else {}
CUR_TRACK = CURATOR.get("track_pick", {})  # {rank: exact tracklist title to force}
CUR_ROWNOTE = CURATOR.get("row_note", {})  # {rank: free-form markdown note appended to Notes}

def norm(s): return re.sub(r"[.']","",unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower())
def ntok(s): return [w for w in re.findall(r"[a-z0-9]+", norm(s)) if w]
def base(t): b=re.sub(r"\s*\([^)]*\)\s*"," ",t or "").strip(" -"); return b or (t or "")
VERSION_KW = {"mix","version","edit","remix","dub","vocal","instrumental","acapella","accapella",
              "radio","club","extended","original","bonus","beats","piano","gospel","classic","main",
              "anthem","reprise","interlude","reedit","zanzibar","house","garage"}
def req_version(track):
    parens = re.findall(r"\(([^)]*)\)", track or "")
    for p in reversed(parens):
        pt = set(ntok(p))
        if pt & {"demo"}: continue          # demos -> treat as no specific version
        if pt & VERSION_KW: return p.strip()
    return None
def base_match(prompt_base, title):
    pb = set(ntok(prompt_base))
    if not pb: return False
    ov = pb & set(ntok(title))
    return len(ov) >= max(1, math.ceil(0.6*len(pb)))
def ver_in(ver, title):
    return set(ntok(ver)) <= set(ntok(title))
def real_tracks(tl):
    tl = tl or []
    withpos = [t for t in tl if str(t.get("pos") or "").strip() and (t.get("title") or "").strip()]
    return withpos or [t for t in tl if (t.get("title") or "").strip()]  # digital tracks may lack pos

def get_master(mid):
    mid = str(mid)
    if mid in MC: return MC[mid]
    d = discogs.call(f"/masters/{mid}")
    if d:
        MC[mid] = {"id": int(mid), "credit": discogs.credit(d.get("artists")),
                   "title": d.get("title"), "year": d.get("year"), "uri": d.get("uri"),
                   "main_release": d.get("main_release"),
                   "tracklist": [{"pos": t.get("position",""), "title": t.get("title",""),
                                  "artists": discogs.credit(t.get("artists")) if t.get("artists") else ""}
                                 for t in d.get("tracklist", [])]}
        json.dump(MC, open(MC_F,"w"), indent=0, ensure_ascii=False)
    return MC.get(mid)

def _has(t, *kw):
    tt = ntok(t["title"]); return any(k in tt for k in kw)
def pick_track(tracks, prompt_base, ver):
    """Return (track, ok). Selection when the prompt names no version (curator's rule):
    prefer a CLUB version (an extended/long club if present), else any extended/long,
    else the first A-side track. Radio/edit is a last-resort fallback."""
    if not tracks: return None, False
    cands = [t for t in tracks if base_match(prompt_base, t["title"])] or list(tracks)
    if ver:
        hit = [t for t in cands if ver_in(ver, t["title"])]
        if hit: return hit[0], True
        return None, False  # signal: named version not on this page
    exts = [t for t in cands if _has(t, "extended", "long")]   # extended/long wins over club
    if exts:
        return exts[0], True
    clubs = [t for t in cands if _has(t, "club")]
    if clubs:
        return clubs[0], True
    return cands[0], True  # first A-side (cands preserve tracklist order)

def track_tier(title, requested):
    """Rate how well the chosen cut matches the curator's preference (5 = ideal).
    A prompt-requested mix that we honoured is always 5."""
    if requested: return 5
    tt = ntok(title)
    if "club" in tt or "extended" in tt or "long" in tt: return 5
    if "dub" in tt or "instrumental" in tt or "acapella" in tt or "accapella" in tt \
       or "beats" in tt or "bonus" in tt: return 2
    if "radio" in tt or "edit" in tt: return 3
    return 4  # plain / vocal / original / main A-side cut

_JOIN = {"the", "a", "and", "featuring", "feat", "ft", "presents", "pres", "vs", "x"}
_MIXW = {"mix", "version", "edit", "remix", "dub", "club", "radio", "vocal", "instrumental",
         "acapella", "accapella", "original", "extended", "long", "main", "bonus", "beats", "12", "7", "inch"}
def dev_notes(src_artist, src_track, disc_artist, disc_track, existing, is_fill):
    """Notes for how the playlist row deviates from the SOURCE list: a differently
    spelled/credited artist, a title with a word the source used but Discogs doesn't
    (misspelling/different title), or — only when the source itself named a version —
    a different version than the one selected. Fills aren't in the source, so skip them."""
    if is_fill:
        return []
    devs = []
    def anorm(s): return set(ntok(re.sub(r"\(\d+\)", "", s or ""))) - _JOIN
    if anorm(src_artist) and anorm(disc_artist) and anorm(src_artist) != anorm(disc_artist):
        devs.append(f'source credits the artist as "{(src_artist or "").strip()}"')
    # title: flag only when the SOURCE has a word the Discogs title lacks (a real
    # misspelling/different word) — not when Discogs merely has a fuller title/subtitle
    src_base = set(ntok(re.sub(r"\s*\([^)]*\)\s*", " ", src_track or ""))) - {"the", "a"}
    disc_all = set(ntok(disc_track or "")) - {"the", "a"}
    if src_base and not src_base.issubset(disc_all):
        srcbase = re.sub(r"\s*\([^)]*\)\s*", " ", src_track).strip()
        devs.append(f'source titles it "{srcbase}"')
    parens = re.findall(r"\(([^)]*)\)", src_track or "")
    covered = "not on the" in " ".join(existing) or "not catalogued" in " ".join(existing)
    if parens and not covered:                              # source named a version...
        sv = parens[-1].strip()
        distinct = set(ntok(sv)) - _MIXW - {"the", "a"}
        if distinct and not (distinct & set(ntok(disc_track))):   # ...and we picked a different one
            devs.append(f'source specifies "{sv}"')
    return devs

out = []
for row in V:
    if row.get("status") != "verified":
        out.append(row); continue
    rid = str(row["release_id"])
    rel = RELC.get(rid, {})
    rel_tracks = real_tracks(rel.get("tracklist"))
    prompt_base = base(row["track_listed"])
    ver = req_version(row["track_listed"])
    mid = rel.get("master_id") or 0
    master = get_master(mid) if mid else None

    page, chosen, note_bits = None, None, []
    mtracks = real_tracks(master["tracklist"]) if master else []
    # Always link the MASTER when one exists — pick from its tracklist; never drop to a
    # specific pressing (users can 'See all versions' on the master to dig down themselves).
    if mtracks:
        cand, ok = pick_track(mtracks, prompt_base, ver)
        if cand and ok:
            page, chosen = "master", cand
        else:  # the prompt's named mix isn't on the master -> best cut the master offers
            cand, _ = pick_track(mtracks, prompt_base, None)
            if cand:
                page, chosen = "master", cand
                if ver: note_bits.append(f"'{ver}' not on the master — using {cand['title']}")
    # No master at all -> the single release is the only page we can link
    if not chosen:
        cand, ok = pick_track(rel_tracks, prompt_base, ver)
        if not (cand and ok):
            alt, _ = pick_track(rel_tracks, prompt_base, None)
            if alt and ver: note_bits.append(f"'{ver}' not on the release — using {alt['title']}")
            cand = alt
        if cand: page, chosen = "release", cand
    # no tracklist anywhere -> link master if present, keep the prompt's track text
    if not chosen:
        page = "master" if master else "release"

    # curator override: force an exact tracklist item (from master, else the release)
    cur_title = CUR_TRACK.get(str(row["rank"]))
    if cur_title:
        want = ntok(cur_title)  # token match ignores spacing/punctuation (e.g. "Problem  #13")
        hit = next((t for t in mtracks if ntok(t["title"]) == want), None)
        if hit:
            page, chosen = "master", hit
        else:
            hit = next((t for t in rel_tracks if ntok(t["title"]) == want), None)
            if hit: page, chosen = "release", hit
        if hit:  # the curator cut supersedes any earlier "not on the master" fallback note
            note_bits[:] = [n for n in note_bits if "not on the" not in n and "not catalogued" not in n]
            note_bits.append("curator-selected cut")

    if page == "master":
        chosen_url = master["uri"]; chosen_credit = master["credit"]
        chosen_year = master.get("year") or rel.get("rel_year")
        released = str(chosen_year) if chosen_year else rel.get("released")
        link_text = re.sub(r"\s*\(\d+\)","", "; ".join(rel.get("labels", [])[:1])) or "Discogs"
        link_text = f"{link_text} · master"
    else:
        chosen_url = rel.get("url"); chosen_credit = rel.get("credit")
        chosen_year = rel.get("rel_year")
        released = rel.get("released") or (str(chosen_year) if chosen_year else "")
        link_text = re.sub(r"\s*\(\d+\)","", "; ".join(rel.get("labels", [])[:1])) or "Discogs"

    chosen_title = chosen["title"] if chosen else row["track_listed"]
    ptart = chosen.get("artists","") if chosen else ""
    # Discogs is source of truth for the artist too: the track's own credit if the
    # tracklist item carries one (splits/comps), else the master/release credit.
    chosen_artist = ptart or chosen_credit or row["artist_listed"]
    cur_applied = "curator-selected cut" in note_bits           # a hand-pinned cut is intentional
    honored = cur_applied or (bool(ver) and chosen is not None and ver_in(ver, chosen_title))
    ttier = track_tier(chosen_title, honored)
    if ttier <= 3 and not any("curator" in n for n in note_bits):  # ★★★★☆ (tier 4) is self-explanatory
        note_bits.append({3: "no club/extended cut — radio/edit is the safest choice",
                          2: "only a dub/instrumental-type cut available"}.get(ttier, ""))
    for d in dev_notes(row["artist_listed"], row["track_listed"], chosen_artist, chosen_title,
                       note_bits, row.get("fill", False)):
        if d not in note_bits: note_bits.append(d)
    if CUR_ROWNOTE.get(str(row["rank"])):
        note_bits.append(CUR_ROWNOTE[str(row["rank"])])

    out.append({**row,
                "chosen_page": page, "chosen_url": chosen_url, "chosen_track": chosen_title,
                "chosen_artist": chosen_artist, "chosen_credit": chosen_credit,
                "chosen_year": chosen_year, "released2": released, "track_tier": ttier,
                "link_text": link_text, "master_id": mid,
                "enrich_notes": [n for n in note_bits if n], "videos_src": rel.get("videos", [])})

json.dump(out, open(HERE/"enriched.json","w"), indent=1, ensure_ascii=False)
nm = sum(1 for r in out if r.get("chosen_page")=="master")
print(f"enriched {len(out)} rows | master-linked: {nm} | release-linked: {sum(1 for r in out if r.get('chosen_page')=='release')}")
