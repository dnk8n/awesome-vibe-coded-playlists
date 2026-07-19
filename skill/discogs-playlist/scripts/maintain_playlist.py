#!/usr/bin/env python3
"""Maintain a discogs-playlist/v1 items file against Discogs + YouTube. Stdlib only.

Two modes:

  report    Show empty / incorrect / outdated YouTube video slots on the
            Discogs release pages, with a recommended contribution per slot —
            so the user can improve Discogs itself (add our verified video to
            the page, replace dead embeds, or mark the slot for manual search).

  rescrape  Re-match page videos for items rated below 5 stars (or --all),
            picking up newly contributed videos, applying the >15-minute rule,
            and updating video fields + ratings in the items file. Follow with
            `create_playlist.py` (idempotent) to sync the actual playlist.

Rating rubric (stored per item as `rating`, 1-5; user edits are respected —
rescrape only recomputes a rating when it changes the video or none is set):
  5  exact cut, from the Discogs page, live, <=15 min
  4  same cut but not on the page (search-found), or page video w/ different mix
  3  alternate track from the same release
  1  no usable video
  -1 star if the best candidate was a >15-minute rip (full-EP/album signal —
     such videos are never selected).

Usage:
  maintain_playlist.py report   [--items f.json] [--json report.json]
  maintain_playlist.py rescrape [--items f.json] [--all] [--dry-run]

Tokens: Discogs from $DISCOGS_TOKEN / .discogs_token, YouTube from
$YOUTUBE_API_KEY / .yt_key (also checked in the home directory).
- The Discogs token is OPTIONAL here: without one, release reads run
  anonymously at slower pacing (the anonymous limit is 25 req/min) — search
  is the auth-only Discogs endpoint, and these modes never search.
- The YouTube slot accepts either an API key or an OAuth access token
  (detected by its "ya29." prefix, sent as a Bearer header) — so the one
  Playground token used for playlist creation covers this loop too.
Quota: ~1 Discogs call + ~1 YouTube unit per examined item.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

LONG_VIDEO_SECONDS = 900  # >15 min = almost certainly a multi-track rip
TIER = {"exact": 5, "close": 4, "search": 4, "alternate": 3, "none": 1, "skipped": 1}
RANK = {"exact": 50, "search": 40, "close": 39, "alternate": 30, "none": 10}


def find_secret(env, fname, cli=None, required=True):
    if cli:
        return cli
    if os.environ.get(env):
        return os.environ[env]
    for p in (pathlib.Path(fname), pathlib.Path.home() / fname):
        if p.exists():
            return p.read_text().strip()
    if required:
        sys.exit(f"Missing credential: set {env} or write {fname}")
    return None


def discogs_release(rid, token):
    """token=None runs anonymously (works for /releases; paced for 25 req/min)."""
    url = f"https://api.discogs.com/releases/{rid}" + (f"?token={token}" if token else "")
    delay = 5
    for _ in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DiscogsPlaylistMaintain/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            time.sleep(1.3 if token else 2.6)  # 60 vs 25 req/min limits
            return d
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(delay)
            delay *= 2
        except Exception:
            time.sleep(delay)
            delay *= 2
    return None


def yt_id(uri):
    if "youtu" not in (uri or ""):
        return None
    q = urllib.parse.urlparse(uri)
    if q.netloc.endswith("youtu.be"):
        return q.path.lstrip("/") or None
    return urllib.parse.parse_qs(q.query).get("v", [None])[0]


def yt_meta(ids, key):
    """id -> {public: bool, seconds: int, title: str} for existing videos.
    `key` may be an API key or an OAuth access token (ya29... -> Bearer)."""
    out = {}
    ids = [i for i in dict.fromkeys(ids) if i]
    oauth = key.startswith("ya29.")
    for i in range(0, len(ids), 50):
        params = {"part": "status,contentDetails,snippet",
                  "id": ",".join(ids[i:i + 50]), "maxResults": 50}
        if not oauth:
            params["key"] = key
        url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {key}"} if oauth else {})
        d = json.load(urllib.request.urlopen(req, timeout=30))
        for it in d.get("items", []):
            m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", it["contentDetails"].get("duration", ""))
            secs = (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)) if m else 0
            out[it["id"]] = {"public": it["status"]["privacyStatus"] == "public",
                             "seconds": secs, "title": it["snippet"]["title"]}
    return out


# --- fuzzy matching (same recipe as the skill's workflow notes) ---
STOP = {"mix", "remix", "original", "version", "edit", "extended", "the", "a"}


def norm_tokens(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[.']", "", s)
    return [w for w in re.findall(r"[a-z0-9]+", s) if w]


def base_title(t):
    b = re.sub(r"\s*\(.*?\)\s*", " ", t or "").strip(" -–")
    return b or (t or "")


def tokens_in(needle, hay, drop_stop=False):
    nt = norm_tokens(needle)
    if drop_stop:
        nt = [w for w in nt if w not in STOP] or nt
    ht = set(norm_tokens(hay))
    return bool(nt) and all(w in ht for w in nt)


def classify_page(item, release, meta):
    """What state is the Discogs page's video slot in, for this item's track?"""
    page = [{"id": yt_id(v.get("uri")), "title": v.get("title", "")}
            for v in (release or {}).get("videos", []) if yt_id(v.get("uri"))]
    for v in page:
        v.update(meta.get(v["id"], {"public": False, "seconds": 0, "title": v["title"]}))
    live = [v for v in page if v["public"]]
    dead = [v for v in page if not v["public"]]
    track = item.get("track", "")
    exact = [v for v in live if tokens_in(track, v["title"]) or tokens_in(base_title(track), v["title"], drop_stop=True)]
    exact_short = [v for v in exact if 0 < v["seconds"] <= LONG_VIDEO_SECONDS or v["seconds"] == 0]
    return {"page": page, "live": live, "dead": dead, "exact": exact, "exact_short": exact_short}


def best_pick(item, release, meta):
    """Run the ladder over live, <=15-min page videos; compare with the item's
    current video. Returns (video_dict|None, match, long_excluded)."""
    st = classify_page(item, release, meta)
    short = [v for v in st["live"] if v["seconds"] <= LONG_VIDEO_SECONDS]
    track = item.get("track", "")
    # penalty when the cut is only reachable via a >15-min multi-track rip:
    # either the page's exact matches are all long, or the currently selected
    # video (which represented this cut) is itself a long rip
    cur0 = item.get("video_id")
    cur_long = bool(cur0) and meta.get(cur0, {}).get("public") \
        and meta[cur0]["seconds"] > LONG_VIDEO_SECONDS
    # ...but no penalty if the page offers a proper short exact cut to swap in
    long_excluded = (bool(st["exact"]) or cur_long) and not st["exact_short"]

    candidates = []  # (rank, video, match)
    for v in short:
        if tokens_in(track, v["title"]):
            candidates.append((RANK["exact"], v, "exact"))
        elif tokens_in(base_title(track), v["title"], drop_stop=True):
            candidates.append((RANK["close"], v, "close"))
    if not candidates:
        for t in (release or {}).get("tracklist", []):
            for v in short:
                if tokens_in(base_title(t.get("title", "")), v["title"], drop_stop=True):
                    candidates.append((RANK["alternate"], v, "alternate"))
    # current video stays a candidate if still live and short
    cur = item.get("video_id")
    cur_match = item.get("match", "search")
    if cur and meta.get(cur, {}).get("public") and meta[cur]["seconds"] <= LONG_VIDEO_SECONDS:
        # +1 tiebreak: the incumbent wins rank ties, so verified picks never
        # churn sideways (page ordering putting a wrong-remix false-exact
        # first must not displace a hand-verified equal-rank pick)
        candidates.append((RANK.get(cur_match, 20) + 1, {"id": cur, "title": meta[cur]["title"],
                                                         "seconds": meta[cur]["seconds"]}, cur_match))
    if not candidates:
        return None, "none", long_excluded
    candidates.sort(key=lambda c: -c[0])
    rank, v, match = candidates[0]
    return v, match, long_excluded


def compute_rating(match, long_excluded):
    return max(1, TIER.get(match, 1) - (1 if long_excluded else 0))


def load(items_path):
    doc = json.load(open(items_path))
    if not isinstance(doc, dict) or "items" not in doc:
        sys.exit("This tool needs the discogs-playlist/v1 schema (dict with items[]).")
    return doc


def cmd_report(args):
    dtoken = find_secret("DISCOGS_TOKEN", ".discogs_token", required=False)
    if not dtoken:
        print("No Discogs token found — using anonymous release reads (slower pacing).")
    ykey = find_secret("YOUTUBE_API_KEY", ".yt_key")
    doc = load(args.items)
    report = []
    for item in doc["items"]:
        rid = item.get("discogs_release_id")
        if not rid:
            continue
        rel = discogs_release(rid, dtoken)
        ids = [yt_id(v.get("uri")) for v in (rel or {}).get("videos", [])] + [item.get("video_id")]
        meta = yt_meta(ids, ykey)
        st = classify_page(item, rel, meta)
        problems, recommend = [], None
        if not st["page"]:
            problems.append("EMPTY: page has no videos")
        if st["dead"]:
            dead_ids = list(dict.fromkeys(v["id"] for v in st["dead"]))
            problems.append("OUTDATED: dead/non-public embeds: " + ", ".join(dead_ids))
        if st["page"] and not st["exact"]:
            problems.append("INCORRECT/MISSING: no page video for this cut")
        if st["exact"] and not st["exact_short"]:
            problems.append(f"ONLY LONG RIP: exact cut only exists as >15-min video")
        if not problems:
            continue
        vid = item.get("video_id")
        vid_on_page = vid in [v["id"] for v in st["live"]]
        if vid and meta.get(vid, {}).get("public") and item.get("match") in ("search", "exact", "close") \
                and not vid_on_page:
            recommend = f"contribute https://youtu.be/{vid} to the Discogs page (our verified upload of this cut)"
        elif vid_on_page and st["page"] and not st["exact"]:
            recommend = ("our video IS on the page but its title doesn't match the printed track title "
                         "(likely a typo on the page or video) — consider fixing the title on Discogs")
        elif not st["page"] or not st["exact"]:
            recommend = "no verified replacement known — search manually, then add it to the Discogs page"
        report.append({
            "label": item.get("label", vid or "?"),
            "rating": item.get("rating"),
            "discogs_url": item.get("discogs_url"),
            "problems": problems,
            "recommend": recommend,
        })
        print(f"[{item.get('rating', '?')}/5] {item.get('label', '?')}")
        for p in problems:
            print(f"    {p}")
        if recommend:
            print(f"    -> {recommend}")
        print(f"    page: {item.get('discogs_url')}")
    print(f"\n{len(report)} of {len(doc['items'])} slots need attention")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(report, indent=1, ensure_ascii=False))
        print(f"wrote {args.json}")


def cmd_rescrape(args):
    dtoken = find_secret("DISCOGS_TOKEN", ".discogs_token", required=False)
    if not dtoken:
        print("No Discogs token found — using anonymous release reads (slower pacing).")
    ykey = find_secret("YOUTUBE_API_KEY", ".yt_key")
    doc = load(args.items)
    changed = 0
    for item in doc["items"]:
        needs = args.all or item.get("rating") is None or (item.get("rating") or 0) < 5
        rid = item.get("discogs_release_id")
        if not needs or not rid:
            continue
        rel = discogs_release(rid, dtoken)
        ids = [yt_id(v.get("uri")) for v in (rel or {}).get("videos", [])] + [item.get("video_id")]
        meta = yt_meta(ids, ykey)
        v, match, long_excluded = best_pick(item, rel, meta)
        old = item.get("video_id")
        new = v["id"] if v else None
        if new != old or item.get("rating") is None:
            rating = compute_rating(match, long_excluded)
            note = []
            if long_excluded:
                note.append("exact cut on page only as >15-min rip (excluded; -1 star)")
            if new != old:
                if old:
                    item["previous_video_id"] = old
                note.append(f"video {'replaced' if old and new else 'set' if new else 'removed'} by rescrape")
            what = f"{old or '—'} -> {new or '—'} ({match}, {rating}/5)"
            if args.dry_run:
                print(f"DRY  {item.get('label', '?')}: {what} {'| ' + '; '.join(note) if note else ''}")
                continue
            item["video_id"] = new
            item["youtube_url"] = f"https://www.youtube.com/watch?v={new}" if new else None
            item["video_title"] = v["title"] if v else None
            item["duration_seconds"] = v.get("seconds") if v else None
            item["match"] = match if new else "none"
            item["video_status"] = "public" if new else None
            item["rating"] = rating
            if note:
                item["rating_notes"] = "; ".join(note)
            changed += 1
            print(f"UPD  {item.get('label', '?')}: {what}")
        else:
            # video unchanged: refresh duration
            if v:
                item["duration_seconds"] = v.get("seconds")
            # provenance upgrade: the incumbent video may now BE on the page
            # (e.g. after a Discogs contribution). Upgrade match/rating, but
            # only when the stored rating is machine-set (== its match tier) —
            # a hand-edited rating is a quality judgment we must not override.
            old_match = item.get("match")
            if v and match != old_match and item.get("rating") == TIER.get(old_match):
                new_rating = compute_rating(match, long_excluded)
                if new_rating > (item.get("rating") or 0):
                    item["match"] = match
                    item["rating"] = new_rating
                    item["rating_notes"] = f"upgraded by rescrape: video now matches the Discogs page ({old_match} -> {match})"
                    changed += 1
                    if not args.dry_run:
                        print(f"UPG  {item.get('label', '?')}: {old_match} -> {match} ({new_rating}/5)")
                        continue
            print(f"ok   {item.get('label', '?')} ({item.get('rating')}/5)")
    if not args.dry_run:
        from datetime import date
        doc["generated_at"] = date.today().isoformat()
        pathlib.Path(args.items).write_text(json.dumps(doc, indent=1, ensure_ascii=False))
        print(f"\n{changed} item(s) updated in {args.items}")
        print("Next: run create_playlist.py (idempotent) to sync the live playlist.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("report")
    r.add_argument("--items", default="playlist_items.json")
    r.add_argument("--json", help="also write the report as JSON here")
    s = sub.add_parser("rescrape")
    s.add_argument("--items", default="playlist_items.json")
    s.add_argument("--all", action="store_true", help="rescrape every item, not just those rated <5")
    s.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    (cmd_report if args.mode == "report" else cmd_rescrape)(args)


if __name__ == "__main__":
    main()
