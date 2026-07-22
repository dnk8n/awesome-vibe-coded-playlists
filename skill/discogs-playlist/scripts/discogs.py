#!/usr/bin/env python3
"""Discogs API helper — rate-limited, backoff, exact credits. Stdlib only.

Token resolution order: --token, $DISCOGS_TOKEN, ./.discogs_token, ~/.discogs_token
(Authentication is REQUIRED for /database/search; it also raises the rate
limit from 25 to 60 requests/minute.)

Commands:
  search  key=value ...        Lead generation. Any Discogs search params:
                               q=, artist=, track=, label=, year=, style=,
                               genre=, country=, format=, type= (release|master),
                               per_page= (default 8).
  release <id> [<id> ...]      Source of truth for a pick: credited artist
                               (join phrases reconstructed), released date,
                               labels, tracklist w/ per-track artists, and the
                               page's embedded videos with YouTube ids.
  scan    key=value [pages=N]  Deduped compact listing (per_page=100) for
                               style/year/label surveys, e.g.
                               scan style="Acid House" year=1990
  batch   <file>               One search per line: "label :: artist :: track
                               [:: year]" — quick lead pass over many picks.
  find    artist= track=       Fuzzy lead-generation: runs several angles at once
          [year= label=]       (artist+track, title-ONLY to catch a different/featured
                               lead, artist discography, punctuation/text-speak-normalised
                               q) and ranks by token overlap, so the release surfaces
                               under spelling/spacing drift. Use when a plain search says
                               NO RESULTS before ever calling a slot "not on Discogs".

Search results are LEADS ONLY: they flatten artist join phrases and omit
per-track credits. Always `release`-fetch every final pick.
"""
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.discogs.com"
UA = "DiscogsPlaylistSkill/1.0"
SLEEP = 1.3  # ~46 req/min: conservative margin under the 60/min auth limit


def find_token(cli_token=None):
    if cli_token:
        return cli_token
    if os.environ.get("DISCOGS_TOKEN"):
        return os.environ["DISCOGS_TOKEN"]
    for p in (pathlib.Path(".discogs_token"), pathlib.Path.home() / ".discogs_token"):
        if p.exists():
            return p.read_text().strip()
    sys.exit("No Discogs token: pass --token, set DISCOGS_TOKEN, or write .discogs_token")


TOKEN = None


def call(path, params=None):
    params = dict(params or {})
    params["token"] = TOKEN
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    delay = 5
    for _ in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
                time.sleep(SLEEP)
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                time.sleep(SLEEP)
                return None
            print(f"  [HTTP {e.code}; backing off {delay}s]", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
        except Exception as e:
            print(f"  [{e}; retry in {delay}s]", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    return None


def strip_disambig(name):
    """Discogs disambiguates duplicate names as 'Traxx (4)'; pages display without."""
    return re.sub(r"\s*\(\d+\)$", "", name or "")


def credit(artists):
    """Reconstruct the displayed credit incl. join phrases:
    [{name: 'Armando', join: 'Presents'}, {name: 'Robert Armani'}]
      -> 'Armando Presents Robert Armani'"""
    parts = []
    for a in artists or []:
        name = strip_disambig(a.get("anv") or a.get("name"))
        join = (a.get("join") or "").strip()
        if join == ",":
            parts.append(name + ",")
        elif join:
            parts.append(name)
            parts.append(join)
        else:
            parts.append(name)
    return " ".join(p for p in parts if p).strip().rstrip(",")


def yt_id(uri):
    if "youtu" not in (uri or ""):
        return None
    q = urllib.parse.urlparse(uri)
    if q.netloc.endswith("youtu.be"):
        return q.path.lstrip("/") or None
    return urllib.parse.parse_qs(q.query).get("v", [None])[0]


def fmt_result(r):
    return (f"{r['id']} | {r.get('year', '?')} | {r.get('country', '?')} | {r['title']} | "
            f"{','.join(r.get('format', [])[:3])} | {','.join(r.get('label', [])[:2])} | "
            f"{','.join(r.get('style', [])[:4])}")


def parse_kv(args):
    params = {}
    extra = {}
    for a in args:
        k, _, v = a.partition("=")
        (extra if k == "pages" else params)[k] = v
    return params, extra


def cmd_search(args):
    params, _ = parse_kv(args)
    params.setdefault("type", "release")
    params.setdefault("per_page", "8")
    d = call("/database/search", params) or {"results": []}
    for r in d.get("results", []):
        print(fmt_result(r))
    if not d.get("results"):
        print("NO RESULTS")


def cmd_release(args):
    for rid in args:
        d = call(f"/releases/{rid}")
        if not d:
            print(f"ID {rid} | NOT FOUND")
            continue
        labels = ", ".join(f"{l['name']} {l.get('catno', '')}".strip() for l in d.get("labels", [])[:2])
        print(f"ID {rid} | released={d.get('released', '?')} | year={d.get('year', '?')} | country={d.get('country', '?')}")
        print(f"  artist_as_credited: {credit(d.get('artists'))}")
        print(f"  title: {d.get('title')}")
        print(f"  label: {labels}")
        print(f"  styles: {', '.join(d.get('styles', []))}")
        print(f"  url: {d.get('uri')}")
        print("  tracklist:")
        for t in d.get("tracklist", []):
            ta = f"  [{credit(t.get('artists'))}]" if t.get("artists") else ""
            print(f"    {t.get('position', '-'):>4} | {t['title']}{ta}")
        vids = d.get("videos", [])
        print(f"  videos ({len(vids)}):")
        for v in vids:
            vid = yt_id(v.get("uri"))
            print(f"    {vid or '??':>11} | {v.get('duration', 0)}s | {v.get('title', '')[:80]}")


def cmd_scan(args):
    params, extra = parse_kv(args)
    params.setdefault("type", "release")
    params.setdefault("per_page", "100")
    pages = int(extra.get("pages", 1))
    seen = set()
    for p in range(1, pages + 1):
        params["page"] = str(p)
        d = call("/database/search", params) or {}
        for r in d.get("results", []):
            key = r["title"].lower()
            if key in seen:
                continue
            seen.add(key)
            print(f"{r['id']} | {r.get('year', '?')} | {r.get('country', '?')} | {r['title']} | "
                  f"{','.join(r.get('label', [])[:1])}")


def cmd_batch(args):
    for line in pathlib.Path(args[0]).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("::")]
        params = {"type": "release", "per_page": "5", "artist": parts[1], "track": parts[2]}
        if len(parts) > 3 and parts[3]:
            params["year"] = parts[3]
        d = call("/database/search", params) or {"results": []}
        print(f"### {parts[0]} :: {parts[1]} :: {parts[2]}")
        results = d.get("results", [])
        if not results and "year" in params:
            del params["year"]
            results = (call("/database/search", params) or {}).get("results", [])
            print("  (year filter dropped)")
        for r in results[:5]:
            print("  " + fmt_result(r))
        if not results:
            print("  NO RESULTS")


def find(artist, track, year="", label=""):
    """Fuzzy lead-generation -> ranked candidate list (each result dict gets an '_s' score).
    `artist=`+`track=` is brittle on Discogs (it misses even correct spellings), so this leans
    on what works: free-text `q=` with an auto **spacing variant** (JoAnn -> Jo Ann) and a
    text-speak variant (4 Da -> 4 Tha), plus a **`release_title=` title-only** pass that surfaces
    a record credited to a different or featured lead (Ann Robinson demo -> Cookie Watkins;
    Charvoni -> Nu Phonic Featuring Charvoni). Ranked by token overlap + year/label hints.
    Importable by other skill scripts (e.g. leads.py); cmd_find is the CLI wrapper."""
    def toks(s):
        return set(re.findall(r"[a-z0-9]+", (s or "").lower()))
    def base(t):
        return re.sub(r"\s*\([^)]*\)\s*", " ", t or "").strip()
    def spacevar(s):                                   # JoAnn -> Jo Ann, D'Bonneau kept
        return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    combo = f"{artist} {track}".strip()
    loose = combo.lower()
    for pat, rep in ((r"\bda\b", "tha"), (r"\bu\b", "you"), (r"&", "and"), (r"\b2\b", "to")):
        loose = re.sub(pat, rep, loose)
    qvars = list(dict.fromkeys(q for q in (combo, spacevar(combo), loose) if q.strip()))

    tries = [{"q": q} for q in qvars]
    if base(track):
        tries += [{"release_title": base(track)},                       # title-only: any artist
                  {"release_title": base(track), "artist": spacevar(artist)}]
    seen, out = set(), []
    for pr in tries:
        for r in (call("/database/search", {**pr, "type": "release", "per_page": "20"}) or {}).get("results", []):
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            out.append(r)
    want = toks(artist) | toks(base(track))
    yr = int(year) if str(year).isdigit() else None
    lt = [w for w in toks(label) if len(w) > 3 and w not in ("records", "record")]
    for r in out:
        s = 3 * len(want & toks(r.get("title")))
        try:
            ry = int(r.get("year"))
        except (TypeError, ValueError):
            ry = None
        if yr and ry:
            s += 4 if ry == yr else (2 if abs(ry - yr) <= 2 else -1)
        if lt and any(w in " ".join(r.get("label", [])).lower() for w in lt):
            s += 3
        r["_s"] = s
    out.sort(key=lambda r: -r["_s"])
    return out


def cmd_find(args):
    """Fuzzy lead-generation across several angles at once (see find()). Use when a plain
    `search` says NO RESULTS, before ever calling a slot 'not on Discogs'."""
    params, _ = parse_kv(args)
    out = find(params.get("artist", ""), params.get("track", ""),
               params.get("year", ""), params.get("label", ""))
    for r in out[:12]:
        print(f"{r['_s']:>3} | {fmt_result(r)}")
    if not out:
        print("NO RESULTS")
    print("# still missing? retry by hand: spelling/phonetic variants (doubled letters, homophones "
          "— Grandpa/Grampa, Saybrynaah/Sabrynaah), the bare track title as q=, a distinctive "
          "substring, or a Various-artists compilation/EP (search the comp, read its per-track "
          "credits).", file=sys.stderr)


def main():
    args = sys.argv[1:]
    tok = None
    if "--token" in args:
        i = args.index("--token")
        tok = args[i + 1]
        del args[i:i + 2]
    global TOKEN
    TOKEN = find_token(tok)
    if not args or args[0] in ("--help-commands", "-h", "--help"):
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    {"search": cmd_search, "release": cmd_release, "scan": cmd_scan,
     "batch": cmd_batch, "find": cmd_find}[cmd](rest)


if __name__ == "__main__":
    main()
