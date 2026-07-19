#!/usr/bin/env python3
"""Programmatic grader for discogs-playlist skill evals.

Checks an outputs directory against the workflow's verifiable claims:
table row count, Discogs links resolve, artist credit exactness, track on
release, YouTube ids live, YouTube pick traceable to the Discogs page (or
noted), rows date-sorted, optional label/year/distinct-artist constraints.

Usage:
  check_outputs.py <outputs_dir> --rows 6 [--require-label "Dance Mania"]
                   [--years 1994-1996] [--distinct-artists]
Emits JSON: {"expectations": [{"text","passed","evidence"}...]}
"""
import argparse, json, pathlib, re, sys, unicodedata

sys.path.insert(0, str(pathlib.Path.home() / ".claude/skills/discogs-playlist/scripts"))
import discogs  # noqa: E402


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def find_file(d, pattern):
    hits = sorted(d.rglob(pattern), key=lambda p: -p.stat().st_size)
    return hits[0] if hits else None


def parse_table(md_text):
    rows = []
    for line in md_text.splitlines():
        if re.match(r"#+\s*(alternates|bench|research)", line.strip(), re.I):
            break
        if not line.strip().startswith("|") or "discogs.com/release" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.search(r"discogs\.com/release/(\d+)", line)
        y = re.search(r"youtu\.be/([\w-]{6,})|youtube\.com/watch\?v=([\w-]{6,})", line)
        rows.append({
            "cells": cells,
            "release_id": int(m.group(1)) if m else None,
            "yt": (y.group(1) or y.group(2)) if y else None,
            "raw": line,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outputs_dir")
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--require-label")
    ap.add_argument("--years")
    ap.add_argument("--distinct-artists", action="store_true")
    args = ap.parse_args()

    d = pathlib.Path(args.outputs_dir)
    exp = []

    def check(text, passed, evidence):
        exp.append({"text": text, "passed": bool(passed), "evidence": str(evidence)[:400]})

    md = find_file(d, "*.md")
    items_f = find_file(d, "playlist_items.json")
    if not md:
        check(f"Markdown table with {args.rows} verified rows exists", False, "no .md file in outputs")
        print(json.dumps({"expectations": exp}, indent=1))
        return
    rows = parse_table(md.read_text())
    check(f"Markdown table has {args.rows} rows with Discogs release links",
          len(rows) == args.rows, f"found {len(rows)} rows in {md.name}")

    # fetch all releases once
    discogs.TOKEN = discogs.find_token()
    releases = {}
    for r in rows:
        if r["release_id"] and r["release_id"] not in releases:
            releases[r["release_id"]] = discogs.call(f"/releases/{r['release_id']}")

    ok = [rid for rid, d_ in releases.items() if d_]
    check("Every Discogs link resolves to a real release via the API",
          len(ok) == len(releases) and len(releases) > 0,
          f"{len(ok)}/{len(releases)} resolved")

    # artist credit exactness: some cell must equal the join-aware credit
    bad_credit, bad_track = [], []
    for r in rows:
        rel = releases.get(r["release_id"])
        if not rel:
            continue
        release_credit = norm(discogs.credit(rel.get("artists")))
        track_credits = {norm(discogs.credit(t.get("artists"))) for t in rel.get("tracklist", []) if t.get("artists")}
        cred_ok = any(release_credit and release_credit in norm(c) for c in r["cells"] if c) or \
                  any(tc and tc in norm(c) for c in r["cells"] if c for tc in track_credits)
        if not cred_ok:
            bad_credit.append(f"{r['release_id']}: expected '{discogs.credit(rel.get('artists'))}'")
        titles = {norm(t["title"]) for t in rel.get("tracklist", []) if t.get("title")}
        tr_ok = any(t and t in norm(c) for c in r["cells"] if c for t in titles if len(t) > 2)
        if not tr_ok:
            bad_track.append(str(r["release_id"]))
    check("Artist cell matches the release-page credit exactly (join phrases included)",
          not bad_credit, bad_credit or "all match")
    check("Track cell matches a title on the release's tracklist verbatim",
          not bad_track, bad_track or "all match")

    # YouTube from page or noted
    unnoted = []
    for r in rows:
        rel = releases.get(r["release_id"])
        if not rel:
            continue
        page_ids = {discogs.yt_id(v.get("uri")) for v in rel.get("videos", [])}
        if r["yt"]:
            if r["yt"] not in page_ids and not re.search(r"not from|search-found|alternate", r["raw"], re.I):
                unnoted.append(f"{r['release_id']}:{r['yt']}")
        else:
            if not re.search(r"skip|no video|none", r["raw"], re.I):
                unnoted.append(f"{r['release_id']}: no yt link and no skip note")
    check("Every YouTube pick comes from the release page's videos, or the deviation/skip is noted in the row",
          not unnoted, unnoted or "all traceable or noted")

    # playlist items + liveness
    if items_f:
        try:
            items = json.load(open(items_f))
            if isinstance(items, dict):
                items = next((v for v in items.values() if isinstance(v, list)), [])
            ids = [(i.get("video_id") or i.get("id") or i.get("videoId")) if isinstance(i, dict) else i for i in items]
            ids = [i for i in ids if i]
            import urllib.request, urllib.parse
            import os
            key = os.environ.get("YOUTUBE_API_KEY") or next(
                (q.read_text().strip() for q in (pathlib.Path(".yt_key"), pathlib.Path.home() / ".yt_key") if q.exists()), None)
            if not key:
                raise RuntimeError("set YOUTUBE_API_KEY or write .yt_key")
            live = {}
            for i in range(0, len(ids), 50):
                url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(
                    {"part": "status", "id": ",".join(ids[i:i + 50]), "key": key, "maxResults": 50})
                dd = json.load(urllib.request.urlopen(url, timeout=30))
                for it in dd.get("items", []):
                    live[it["id"]] = it["status"]["privacyStatus"]
            dead = [i for i in ids if live.get(i) != "public"]
            check("playlist_items.json exists and every video id is live and public",
                  not dead and len(ids) > 0, f"{len(ids)} ids, dead/non-public: {dead or 'none'}")
        except Exception as e:
            check("playlist_items.json exists and every video id is live and public", False, f"error: {e}")
    else:
        check("playlist_items.json exists and every video id is live and public", False, "file missing")

    # sorted by date (first cell that starts with a 4-digit year)
    years = []
    for r in rows:
        for c in r["cells"]:
            m = re.search(r"\b(19\d\d|20\d\d)\b", c)
            if m:
                years.append(int(m.group(1)))
                break
    check("Rows are sorted ascending by release date",
          years == sorted(years) and len(years) == len(rows), f"years: {years}")

    if args.require_label:
        wrong = [rid for rid, rel in releases.items() if rel and
                 not any(args.require_label.lower() in (l.get("name", "").lower()) for l in rel.get("labels", []))]
        check(f"Every release is on the required label ({args.require_label})", not wrong, wrong or "all on label")
    if args.years:
        lo, hi = (int(x) for x in args.years.split("-"))
        wrong = [rid for rid, rel in releases.items() if rel and not (lo <= (rel.get("year") or 0) <= hi)]
        check(f"Every release year within {args.years}", not wrong, wrong or "all in range")
    if args.distinct_artists:
        creds = [norm(discogs.credit(rel.get("artists"))) for rel in releases.values() if rel]
        check("Max one release per artist (all artists distinct)",
              len(set(creds)) == len(creds), creds)

    print(json.dumps({"expectations": exp}, indent=1))


if __name__ == "__main__":
    main()
