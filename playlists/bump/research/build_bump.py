#!/usr/bin/env python3
"""Bump series pipeline — one rows-file checkpoint per Bump compilation.

For every track on a Bump tracklist (artist & title quoted VERBATIM from the
Bump release page), hunt the exact quoted mix on Discogs as a
Single -> EP -> Album (never a compilation; a Various release counts as a
compilation whatever its format tags say). Link the master only when the
master's own tracklist quotes the exact mix. Genre/Style/Released come from
the page actually linked. Matching is tiered: a strict hit (distinctive mix
tokens equal) always wins; only when no strict hit exists is a vocal-relaxed
hit acceptable ('Extended Mix' -> 'Extended Vocal Mix'). YouTube is keyless —
release/master page videos first, then scraped searches (with and without the
artist); every pick oEmbed-validated. curator.json (keyed by row ID SS.DD.TT)
pins hand-chosen videos across rebuilds.

Usage (from this research/ dir, DISCOGS_TOKEN in env):
    python3 build_bump.py 1          # build Bump 1 (skips if rows file exists)
    python3 build_bump.py 1 --force  # rebuild
    python3 build_bump.py --all
"""
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SKILL_SCRIPTS = pathlib.Path.home() / ".claude/skills/discogs-playlist/scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
import discogs  # noqa: E402  (rate-limited client, credit reconstruction)

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / "cache"
ROWS = HERE / "rows"
RELEASES = json.loads((HERE / "bump_releases.json").read_text())
CURATOR_FILE = HERE / "curator.json"
CURATOR = json.loads(CURATOR_FILE.read_text()) if CURATOR_FILE.exists() else {}

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
MAX_FETCHES_PER_TRACK = 12  # release fetches while hunting the exact mix
LONG_RIP = 900              # >15 min = full-EP/album rip, never selected
# Generic words sleeves add/drop freely — ignored when comparing mix names
# ('Vibro Dwarfs Mix' == 'Vibro-Dwarfs 12" Mix': mix/remix/12" mean the same)
GENERIC_MIX_TOKENS = {"mix", "remix", "version", "the", "12", "s"}
# Second-tier relaxation: only when NO strict hit exists anywhere is a match
# that adds/drops 'vocal' acceptable ('Extended Mix' -> 'Extended Vocal Mix')
RELAX_MIX_TOKENS = GENERIC_MIX_TOKENS | {"vocal"}
# Text-speak/abbreviation drift between sleeve quotes, pressings and upload
# titles; applied to BOTH sides of a comparison (matching only, never displayed)
CANON = {"u": "you", "ur": "your", "luv": "love", "nite": "night",
         "da": "the", "tha": "the", "n": "and",
         "bros": "brothers", "bro": "brother"}
# Mix-designation words a video may NOT add beyond the quote — an upload
# titled '… (Video Edit)' is not the quoted '… (Mix)' even when every quoted
# token is present.
DANGER_MIX_TOKENS = {"edit", "radio", "video", "short", "dub", "instrumental",
                     "acapella", "accapella", "live", "cover", "remake",
                     "karaoke", "slowed", "reverb", "nightcore", "megamix",
                     "medley"}
SA_MARKERS = re.compile(
    r"south\s*africa|johannesburg|cape\s*town|durban|pretoria|soweto|gauteng",
    re.I)


# ---------- cached fetchers ----------

def _ckey(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()


def _cached(subdir, key, fetch):
    d = CACHE / subdir
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    data = fetch()
    f.write_text(json.dumps(data))
    return data


def dg(path, params=None):
    """Cached Discogs GET (rate limiting lives in discogs.call)."""
    return _cached("discogs", _ckey(path, json.dumps(params or {}, sort_keys=True)),
                   lambda: discogs.call(path, params))


def yt_search(query):
    def fetch():
        url = ("https://www.youtube.com/results?search_query="
               + urllib.parse.quote(query))
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        m = re.search(r"var ytInitialData = (\{.*?\});</script>", html)
        time.sleep(1.0)
        if not m:
            return []
        vids, seen = [], set()

        def walk(o):
            if isinstance(o, dict):
                if "videoRenderer" in o:
                    v = o["videoRenderer"]
                    vid = v.get("videoId")
                    if vid and vid not in seen:
                        seen.add(vid)
                        title = "".join(r["text"] for r in
                                        v.get("title", {}).get("runs", []))
                        vids.append({"id": vid, "title": title,
                                     "secs": _dur_secs(v.get("lengthText", {})
                                                       .get("simpleText", ""))})
                for x in o.values():
                    walk(x)
            elif isinstance(o, list):
                for x in o:
                    walk(x)
        walk(json.loads(m.group(1)))
        return vids[:20]
    return _cached("yt_search", _ckey(query), fetch)


def oembed(vid):
    """None = dead/private. Else {'title': ...}."""
    def fetch():
        url = ("https://www.youtube.com/oembed?url="
               "https://www.youtube.com/watch?v=" + vid + "&format=json")
        try:
            req = urllib.request.Request(url, headers=UA)
            data = json.load(urllib.request.urlopen(req, timeout=20))
            time.sleep(0.3)
            return {"title": data.get("title", "")}
        except Exception:
            time.sleep(0.3)
            return None
    return _cached("yt_oembed", vid, fetch)


def _dur_secs(text):
    parts = [p for p in text.split(":") if p.strip().isdigit()]
    if not parts:
        return None
    s = 0
    for p in parts:
        s = s * 60 + int(p)
    return s


def sa_confirmed(artist_ids):
    """Confirmed South African artist: Discogs profile text names SA/SA city.
    Evidence only — never inferred from a name or a pressing country."""
    for aid in artist_ids:
        if not aid:
            continue
        prof = dg(f"/artists/{aid}") or {}
        if SA_MARKERS.search(prof.get("profile", "") or ""):
            return True
    return False


# ---------- text matching ----------

def norm(s):
    s = (s or "").lower().replace("’", "'").replace("‘", "'")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    out = []
    for t in s.split():
        t = CANON.get(t, t)
        if re.fullmatch(r"(19|20)\d{2}", t):
            t = t[2:]  # '1997' == \"'97\"
        out.append(t)
    return " ".join(out)


def toks(s):
    return set(norm(s).split())


def squash(s):
    """Collapse doubled letters: 'afflitto' -> 'aflito' (spelling drift)."""
    return re.sub(r"(.)\1+", r"\1", s)


def base_eq(a, b):
    na, nb = norm(a), norm(b)
    return na == nb or squash(na) == squash(nb)


def set_eq(a, b):
    return a == b or {squash(t) for t in a} == {squash(t) for t in b}


def toks_in(need, have):
    hs = {squash(t) for t in have}
    return all(t in have or squash(t) in hs for t in need)


def parse_mix(title):
    """Leading text = base; LAST top-level (...) group = mix (nested parens
    flatten); MIDDLE groups are subtitles and ignored, so a sleeve-truncated
    title still matches: '9PM (Till I Come) (Club Mix)' -> ('9PM', 'Club Mix'),
    'Afflitto (Single Mix (Vocal))' -> ('Afflitto', 'Single Mix Vocal').
    Brackets count as parens ('Requiem [Of A Junkies Dream] (…)')."""
    t = title.strip().replace("[", "(").replace("]", ")")
    if "(" not in t or not t.endswith(")"):
        return title.strip(), None
    depth, start, lead_end, groups = 0, None, None, []
    for i, ch in enumerate(t):
        if ch == "(":
            if depth == 0:
                start = i
                if lead_end is None:
                    lead_end = i
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
            if depth == 0 and start is not None:
                groups.append(t[start + 1:i])
                start = None
    base = t[:lead_end].strip() if lead_end else ""
    if not base or not groups:
        return title.strip(), None  # '(You Make Me Feel) Mighty Real'
    mix = re.sub(r"[()]+", " ", groups[-1]).strip()
    return base, (mix or None)


def mix_equal(quoted, pressed, artist="", relax=False):
    """Same base + same DISTINCTIVE mix tokens. Generic mix words drop out;
    the row's OWN artist name in a mix is self-credit and drops out too; a
    FOREIGN remixer credit stays distinctive. relax=True additionally treats
    'vocal' as generic (second-tier only — a strict hit always wins)."""
    qb, qm = parse_mix(quoted)
    pb, pm = parse_mix(pressed)
    if not base_eq(qb, pb):
        return False
    if (qm is None) != (pm is None):
        # a named mix never equals an unnamed cut ('Refugee Mix' != 'Da Dip')
        return False
    drop = (RELAX_MIX_TOKENS if relax else GENERIC_MIX_TOKENS) | toks(artist)
    return set_eq(toks(qm or "") - drop, toks(pm or "") - drop)


GENERIC_ARTIST_TOKENS = {"feat", "featuring", "ft", "the", "and", "dj", "mc",
                         "presents", "vs", "versus", "his", "her"}


def artist_match(bump_artist, rel, track_item=None):
    """Candidate must share a distinctive artist token with the Bump credit —
    release-level or per-track — so a soundalike act's title can't hijack the
    original's pressing (or vice versa). Tolerant of Feat./attribution drift."""
    want = toks(bump_artist) - GENERIC_ARTIST_TOKENS
    if not want:
        return True
    have = toks(discogs.credit(rel.get("artists"))) | toks(rel.get("artists_sort", ""))
    if track_item:
        have |= toks(discogs.credit(track_item.get("artists")))
    return bool(want & (have - GENERIC_ARTIST_TOKENS))


def title_has_mix(video_title, base, mix, strict=True, relax_vocal=False):
    """Base tokens present + all distinctive mix tokens present + (strict)
    no danger mix-words beyond what the quote or the song's title carries.
    strict=False is the fallback rung: any version of the track, note names it."""
    vt = toks(video_title)
    if not toks_in(toks(base), vt):
        return False
    allowed = toks(base) | toks(mix or "")
    if strict and (vt & DANGER_MIX_TOKENS) - allowed:
        return False
    if mix is None:
        return True
    drop = RELAX_MIX_TOKENS if relax_vocal else GENERIC_MIX_TOKENS
    need = toks(mix) - drop
    return toks_in(need, vt) if need else toks_in(toks(mix), vt)


# ---------- Discogs candidate hunt ----------

def fmt_tier(fmt_strings):
    """0 Single / 1 EP / 2 Album / 3 other; None = compilation/mixed (excluded)."""
    fl = {f.lower().strip('"') for f in fmt_strings}
    if "compilation" in fl or "mixed" in fl:
        return None
    tier = 3
    if fl & {"single", "maxi-single", "maxi single", "7\"", "7"}:
        tier = 0
    elif "ep" in fl or "mini-album" in fl:
        tier = 1
    elif fl & {"album", "lp"}:
        tier = 2
    if "unofficial release" in fl:
        tier += 10
    return tier


TIER_NAME = {0: "Single", 1: "EP", 2: "Album", 3: "12\"", 10: "Single*",
             11: "EP*", 12: "Album*", 13: "12\"*"}


def release_formats(rel):
    out = []
    for f in rel.get("formats", []):
        out.append(f.get("name", ""))
        out.extend(f.get("descriptions", []) or [])
    return out


def search_candidates(artist, base):
    """Merged leads from 2-3 search angles; comps kept only as master hints."""
    results = []
    seen = set()
    angles = [
        {"artist": artist, "track": base, "type": "release", "per_page": 50},
        {"q": f"{artist} {base}", "type": "release", "per_page": 50},
    ]
    plain = re.sub(r"[^a-z0-9]+", " ", base.lower().replace("’", "'")).strip()
    if norm(base) != plain:
        # text-speak drift (U/You, Da/The …): search the canonical wording too
        angles.append({"q": f"{artist} {norm(base)}", "type": "release",
                       "per_page": 50})
    for params in angles:
        data = dg("/database/search", params) or {}
        for r in data.get("results", []):
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append(r)
    if not any(fmt_tier(r.get("format", [])) is not None for r in results):
        data = dg("/database/search",
                  {"release_title": base, "type": "release", "per_page": 50}) or {}
        for r in data.get("results", []):
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append(r)
    return results


def _released_of(rel):
    d = (rel.get("released") or "").strip()
    d = re.sub(r"(-00)+$", "", d)
    return d or (str(rel.get("year")) if rel.get("year") else "")


def _make_found(quoted_title, artist, rel, real_tier, hit, relax):
    """Build the found-row dict; master preferred only when the master's own
    tracklist quotes the (same-tier) matching mix. Genre/Style/Released come
    from the page actually linked."""
    master = dg(f"/masters/{rel['master_id']}") if rel.get("master_id") else None
    kind = TIER_NAME.get(real_tier, "Release")
    url = rel.get("uri") or f"https://www.discogs.com/release/{rel['id']}"
    page = rel
    released = _released_of(rel)
    if master and any(mix_equal(quoted_title, t.get("title", ""), artist,
                                relax=relax)
                      for t in master.get("tracklist", [])):
        kind, page = "Master", master
        url = master.get("uri") or f"https://www.discogs.com/master/{master['id']}"
        released = str(master.get("year") or "")
    notes = []
    hb, _ = parse_mix(hit.get("title", ""))
    qb, _ = parse_mix(quoted_title)
    if norm(hb) != norm(qb):
        notes.append(f"Pressed as “{hit.get('title', '')}”")
    videos = (rel.get("videos") or []) + ((master or {}).get("videos") or [])
    return {"found": True, "kind": kind, "url": url,
            "year": rel.get("year") or (master or {}).get("year"),
            "released": released,
            "genre": ", ".join(page.get("genres") or []),
            "style": ", ".join(page.get("styles") or []),
            "videos": videos, "release_id": rel["id"], "notes": notes}


def curated_source(artist, quoted_title, release_id):
    """curator.json dg_pick: the user hand-resolved the source release —
    honour it, choosing the best tracklist item (strict, then vocal-relaxed,
    then same-base)."""
    rel = dg(f"/releases/{release_id}")
    real_tier = fmt_tier(release_formats(rel))
    base, _ = parse_mix(quoted_title)
    hit = next((t for t in rel.get("tracklist", [])
                if mix_equal(quoted_title, t.get("title", ""), artist)), None)
    relax = False
    if not hit:
        hit = next((t for t in rel.get("tracklist", [])
                    if mix_equal(quoted_title, t.get("title", ""), artist,
                                 relax=True)), None)
        relax = hit is not None
    if not hit:
        hit = next((t for t in rel.get("tracklist", [])
                    if base_eq(parse_mix(t.get("title", ""))[0], base)),
                   rel.get("tracklist", [{}])[0])
    return _make_found(quoted_title, artist, rel, real_tier, hit, relax=relax)


def hunt_exact_mix(artist, quoted_title, bump_year):
    """Return dict describing the linked page (or the miss)."""
    base, mix = parse_mix(quoted_title)
    results = search_candidates(artist, base)

    cands, master_hints = [], []
    for r in results:
        tier = fmt_tier(r.get("format", []))
        if r.get("master_id"):
            master_hints.append(r)
        if tier is None:
            continue
        if r.get("title", "").lower().startswith("various - "):
            continue  # V/A = compilation even when the format tags omit it
        year = int(r.get("year") or 9999)
        # Year PROXIMITY to the Bump volume, not earliest-first: a comp
        # licenses the mixes current at its release, and a quoted remix
        # usually lives on a remix pressing years after the original single.
        prox = abs(year - bump_year) if bump_year and year != 9999 else 99
        fl = {f.lower() for f in r.get("format", [])}
        promo = 1 if fl & {"promo", "test pressing", "white label"} else 0
        title_bonus = 0 if norm(base) in norm(r.get("title", "")) else 1
        cands.append((tier, prox, promo, year, title_bonus, r))
    cands.sort(key=lambda c: c[:5])

    qmix = toks(mix or "") - GENERIC_MIX_TOKENS
    near = None          # best same-base different-mix pressing (miss note)
    relaxed = None       # first vocal-relaxed hit — used only if no strict hit
    fetched = 0
    for tier, _, _, year, _, r in cands:
        if fetched >= MAX_FETCHES_PER_TRACK:
            break
        rel = dg(f"/releases/{r['id']}")
        fetched += 1
        if not rel:
            continue
        real_tier = fmt_tier(release_formats(rel))
        if real_tier is None:
            continue
        if norm(discogs.credit(rel.get("artists"))) == "various":
            continue  # V/A = compilation even when the format tags omit it
        hit = next((t for t in rel.get("tracklist", [])
                    if mix_equal(quoted_title, t.get("title", ""), artist)
                    and artist_match(artist, rel, t)), None)
        if hit:
            return _make_found(quoted_title, artist, rel, real_tier, hit,
                               relax=False)
        if relaxed is None:
            rhit = next((t for t in rel.get("tracklist", [])
                         if mix_equal(quoted_title, t.get("title", ""), artist,
                                      relax=True)
                         and artist_match(artist, rel, t)), None)
            if rhit:
                relaxed = (rel, real_tier, rhit)
        for t in rel.get("tracklist", []):
            pb, pm = parse_mix(t.get("title", ""))
            if not base_eq(pb, base) or not artist_match(artist, rel, t):
                continue
            pmix = toks(pm or "") - GENERIC_MIX_TOKENS
            overlap = len(qmix & pmix) - 0.1 * len(pmix ^ qmix)
            if near is None or overlap > near["overlap"]:
                murl = (f"https://www.discogs.com/master/{rel['master_id']}"
                        if rel.get("master_id") else None)
                near = {"overlap": overlap, "pressed": t.get("title", ""),
                        "kind": "Master" if murl else TIER_NAME.get(real_tier,
                                                                    "Release"),
                        "year": rel.get("year"),
                        "url": murl or rel.get("uri"), "rel": rel}

    if relaxed is not None:
        return _make_found(quoted_title, artist, *relaxed, relax=True)

    # Miss: defining master (note + Genre/Style + videos), near pressing note.
    master, master_title, master_foreign = None, None, False
    for r in sorted(master_hints, key=lambda r: int(r.get("year") or 9999)):
        if norm(base) in norm(r.get("title", "")):
            master = dg(f"/masters/{r['master_id']}")
            if master:
                master_title = r.get("title", "")
                master_foreign = not bool(
                    (toks(artist) - GENERIC_ARTIST_TOKENS) & toks(master_title))
                break
    gs = master or (near or {}).get("rel") or {}
    videos = ((near or {}).get("rel") or {}).get("videos") or []
    videos = videos + ((master or {}).get("videos") or [])
    note = None
    if near:
        note = (f"Closest pressed mix: “{near['pressed']}” on "
                f"[{near['kind']} · {near['year']}]({near['url']})")
    return {"found": False, "kind": None, "url": None, "year": None,
            "released": "",
            "genre": ", ".join(gs.get("genres") or []),
            "style": ", ".join(gs.get("styles") or []),
            "videos": videos,
            "master_url": (master or {}).get("uri"),
            "master_title": master_title, "master_foreign": master_foreign,
            "near_note": note,
            "any_results": bool(results)}


# ---------- YouTube ladder ----------

def alive(vid):
    return oembed(vid) is not None


def pick_video(artist, quoted_title, page_videos, require_artist=False,
               flag_unattributed=False):
    """(id, oembed_title, match_kind, note) — match_kind: exact|fallback|none.
    require_artist: exact rungs also need a distinctive artist token in the
    video title (soundalike rows, where the original act's upload would
    otherwise pass as exact). flag_unattributed: keep the exact match but
    note it when the upload title names no artist (Discogs-MISS rows only —
    nothing else anchors those rows)."""
    base, mix = parse_mix(quoted_title)
    a_want = toks(artist) - GENERIC_ARTIST_TOKENS

    def artist_ok(title):
        return not require_artist or bool(a_want & toks(title))

    page = []
    for v in page_videos:
        vid = discogs.yt_id(v.get("uri"))
        if vid:
            page.append({"id": vid, "title": v.get("title", ""),
                         "secs": v.get("duration")})

    def usable(v):
        return (v["secs"] is None or v["secs"] <= LONG_RIP) and alive(v["id"])

    def exact_note(title):
        if flag_unattributed and not (a_want & toks(title)):
            return f"▶ upload title omits the artist — verify by ear: “{title}”"
        return None

    queries = [f"{artist} {base}" + (f" {mix}" if mix else "")]
    if mix:
        queries.append(f"{base} {mix}")  # uploads often omit the artist

    # exact rungs: page videos then scraped searches; strict first, then
    # vocal-relaxed (same tiering as the Discogs hunt)
    for relax in (False, True):
        for v in page:
            if title_has_mix(v["title"], base, mix, relax_vocal=relax) \
                    and artist_ok(v["title"]) and usable(v):
                t = oembed(v["id"])["title"]
                return v["id"], t, "exact", exact_note(t)
        for q in queries:
            for v in yt_search(q):
                if title_has_mix(v["title"], base, mix, relax_vocal=relax) \
                        and artist_ok(v["title"]) and usable(v):
                    t = oembed(v["id"])["title"]
                    return v["id"], t, "exact", exact_note(t)
        if mix is None:
            break  # nothing to relax

    # fallback: base-title match, page first then search
    fb_note = ("▶ may be the original act, not this soundalike: “{}”"
               if require_artist else "▶ quoted mix not found; video is “{}”")
    for v in page:
        if title_has_mix(v["title"], base, None, strict=False) and usable(v):
            t = oembed(v["id"])["title"]
            return v["id"], t, "fallback", fb_note.format(t)
    pool = [v for q in queries for v in yt_search(q)]
    if mix:
        pool += yt_search(f"{artist} {base}")
    for v in pool:
        if title_has_mix(v["title"], base, None, strict=False) and usable(v):
            t = oembed(v["id"])["title"]
            return v["id"], t, "fallback", fb_note.format(t)

    return None, None, "none", "▶ no usable YouTube upload found"


# ---------- per-Bump build ----------

def bump_source(n):
    spec = RELEASES[str(n)]
    if "master" in spec:
        m = dg(f"/masters/{spec['master']}")
        rel = dg(f"/releases/{m['main_release']}")
    else:
        rel = dg(f"/releases/{spec['release']}")
    return rel


def parse_pos(pos, seq_in_disc):
    """'2-05'/'2.05'/'CD2-5' -> (2, 5); plain '7' -> (1, 7); else sequential."""
    p = (pos or "").strip()
    m = re.match(r"^(?:cd)?(\d+)[-.](\d+)$", p, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    if p.isdigit():
        return 1, int(p)
    return 1, seq_in_disc


def build(n, force=False):
    ROWS.mkdir(exist_ok=True)
    out = ROWS / f"bump_{int(n):02d}.json"
    if out.exists() and not force:
        print(f"bump {n}: rows file exists, skipping")
        return
    rel = bump_source(n)
    if not rel:
        print(f"bump {n}: SOURCE FETCH FAILED")
        return
    tracks = [t for t in rel.get("tracklist", []) if t.get("type_") == "track"]
    doc = {"bump_n": int(n), "release_id": rel["id"],
           "title": rel.get("title"), "year": rel.get("year"),
           "url": rel.get("uri"),
           "label": ", ".join(f"{l.get('name')} {l.get('catno', '')}".strip()
                              for l in rel.get("labels", [])[:1]),
           "rows": []}
    print(f"bump {n}: {doc['title']} ({doc['year']}) — {len(tracks)} tracks")
    seq = 0
    last_disc = 1
    for i, t in enumerate(tracks, 1):
        artist = discogs.credit(t.get("artists")) or rel.get("artists_sort", "")
        quoted = t.get("title", "").strip()
        disc, tno = parse_pos(t.get("position"), seq + 1)
        if disc != last_disc:
            seq = 0
            last_disc = disc
        seq += 1
        row_id = f"{int(n):02d}.{disc:02d}.{tno:02d}"

        cur = CURATOR.get(row_id) or {}
        if cur.get("dg_pick"):
            d = curated_source(artist, quoted, cur["dg_pick"])
        else:
            d = hunt_exact_mix(artist, quoted, rel.get("year"))
        vid, vtitle, vmatch, vnote = pick_video(
            artist, quoted, d["videos"],
            require_artist=(not d["found"] and d.get("master_foreign", False)),
            flag_unattributed=not d["found"])
        notes = list(d.get("notes") or [])
        if not d["found"]:
            if d.get("near_note"):
                notes.append("Quoted mix not on any single/EP/album. "
                             + d["near_note"])
            elif d.get("master_url") and d.get("master_foreign"):
                notes.append(f"No single/EP/album under this artist; the song "
                             f"originates as [{d['master_title']}]"
                             f"({d['master_url']})")
            elif d.get("master_url"):
                notes.append(f"Quoted mix not on any single/EP/album; "
                             f"[master]({d['master_url']}) defines the track")
            elif d.get("any_results"):
                notes.append("Quoted mix not on any single/EP/album on Discogs")
            else:
                notes.append("No Discogs entry found")
        if vnote:
            notes.append(vnote)

        if cur.get("video_pick"):
            pin = cur["video_pick"]
            o = oembed(pin)
            if o:
                vid, vtitle, vmatch = pin, o["title"], "exact"
                notes = [x for x in notes if not x.startswith("▶")]
                if cur.get("video_note"):
                    notes.append("▶ " + cur["video_note"])
            else:
                notes.append(f"▶ curator pick {pin} is dead — kept automatic")

        sa = sa_confirmed([a.get("id") for a in (t.get("artists") or [])])
        row = {"id": row_id, "series": int(n), "rank": i, "disc": disc,
               "tno": tno, "pos": t.get("position"), "artist": artist,
               "track": quoted, "genre": d["genre"], "style": d["style"],
               "released": d.get("released", ""), "sa": sa,
               "dg_kind": d["kind"], "dg_url": d["url"], "dg_year": d["year"],
               "yt_id": vid, "yt_title": vtitle, "yt_match": vmatch,
               "notes": notes}
        doc["rows"].append(row)
        out.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
        dgs = f"{d['kind']} {d['year']}" if d["found"] else "MISS"
        print(f"  {row_id} {artist} — {quoted}  [{dgs}] [yt:{vmatch}]"
              f"{' [SA]' if sa else ''}")
    print(f"bump {n}: done -> {out.name}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    discogs.TOKEN = discogs.find_token()
    ns = sorted(int(k) for k in RELEASES) if "--all" in sys.argv else [int(a) for a in args]
    for n in ns:
        build(n, force=force)


if __name__ == "__main__":
    main()
