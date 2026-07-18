#!/usr/bin/env python3
"""Validate YouTube video ids in bulk via videos.list (1 quota unit per 50 ids).

Discogs release pages routinely carry dead/private video embeds, so every id
you plan to put in a playlist must pass through this before you trust it.

Key resolution order: --key, $YOUTUBE_API_KEY, ./.yt_key, ~/.yt_key

Usage:
  yt_verify.py ID [ID ...]
  yt_verify.py --file playlist_items.json      # [{"video_id": ...}, ...]
  yt_verify.py --file ids.txt                  # one id per line

Prints one line per id: status | duration | channel | title.
Exits 1 if any id is missing/non-public (so callers can branch on it).
"""
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request


def find_key(cli_key=None):
    if cli_key:
        return cli_key
    if os.environ.get("YOUTUBE_API_KEY"):
        return os.environ["YOUTUBE_API_KEY"]
    for p in (pathlib.Path(".yt_key"), pathlib.Path.home() / ".yt_key"):
        if p.exists():
            return p.read_text().strip()
    sys.exit("No YouTube API key: pass --key, set YOUTUBE_API_KEY, or write .yt_key")


def load_ids(args):
    if args and args[0] == "--file":
        text = pathlib.Path(args[1]).read_text()
        try:
            data = json.loads(text)
            if isinstance(data, dict):  # discogs-playlist/v1 schema (or similar wrapper)
                data = data.get("items") or next((v for v in data.values() if isinstance(v, list)), [])
            out = []
            for d in data:
                if isinstance(d, dict):
                    out.append(d.get("video_id") or d.get("videoId") or d.get("id"))
                else:
                    out.append(d)
            return [o for o in out if o]
        except json.JSONDecodeError:
            return [l.strip() for l in text.splitlines() if l.strip()]
    return args


def main():
    args = sys.argv[1:]
    key = None
    if "--key" in args:
        i = args.index("--key")
        key = args[i + 1]
        del args[i:i + 2]
    key = find_key(key)
    ids = load_ids(args)
    if not ids:
        sys.exit("No video ids given.")
    seen, ordered = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            ordered.append(i)

    info = {}
    for i in range(0, len(ordered), 50):
        url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({
            "part": "snippet,contentDetails,status", "id": ",".join(ordered[i:i + 50]),
            "key": key, "maxResults": 50})
        d = json.load(urllib.request.urlopen(url, timeout=30))
        for it in d.get("items", []):
            blocked = (it["contentDetails"].get("regionRestriction", {}).get("blocked") or [])
            info[it["id"]] = {
                "status": it["status"]["privacyStatus"],
                "dur": it["contentDetails"].get("duration", "?"),
                "channel": it["snippet"]["channelTitle"],
                "title": it["snippet"]["title"],
                "blocked": blocked,
            }

    bad = []
    for vid in ordered:
        m = info.get(vid)
        if not m:
            print(f"{vid} | DEAD (not returned by API)")
            bad.append(vid)
        elif m["status"] != "public":
            print(f"{vid} | {m['status'].upper()} | {m['title'][:60]}")
            bad.append(vid)
        else:
            note = f" | region-blocked in {len(m['blocked'])} countries" if m["blocked"] else ""
            print(f"{vid} | ok | {m['dur']} | {m['channel'][:24]} | {m['title'][:60]}{note}")

    print(f"\n{len(ordered) - len(bad)}/{len(ordered)} ok" + (f"; PROBLEMS: {bad}" if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
