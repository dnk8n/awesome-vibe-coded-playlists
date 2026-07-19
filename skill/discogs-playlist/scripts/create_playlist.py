#!/usr/bin/env python3
"""Create a YouTube playlist from an items file, via OAuth 2.0. Stdlib only.

An API key CANNOT create playlists — playlists.insert requires OAuth user
consent. Copy this script into the user's project next to the items file and
walk them through ONE of the two auth paths below.

Items file: the rich `discogs-playlist/v1` schema (see the skill's
references/workflow-notes.md). Minimal working example:

  {
    "schema": "discogs-playlist/v1",
    "playlist": {"title": "...", "description": "...", "privacy": "private"},
    "items": [{"video_id": "abc123", "label": "1986 · Artist – Track"}, ...]
  }

Title/description/privacy resolve CLI-first, then from the file's `playlist`
block. Legacy inputs also work: a bare list of ids or of {video_id|videoId|id}
objects (then --title is required).

Auth path A — quick, no Cloud Console setup:
  1. https://developers.google.com/oauthplayground
  2. Step 1: YouTube Data API v3 -> scope https://www.googleapis.com/auth/youtube
     -> Authorize APIs (sign in with the account that owns the channel)
  3. Step 2: "Exchange authorization code for tokens" -> copy Access token
  4. python3 create_playlist.py --token 'ya29....' [--items f.json]
  (Playground tokens last ~1 hour; a 120-track run takes ~3 minutes.)

Auth path B — reusable Desktop OAuth client:
  Google Cloud Console -> APIs & Services -> Credentials -> Create credentials
  -> OAuth client ID -> Desktop app (first time: configure consent screen,
  External, add the user as test user), then:
  python3 create_playlist.py --client-id X --client-secret Y
  (Opens the browser; catches the redirect on http://localhost:8765.)

Idempotent: every run diffs the items file against the LIVE playlist
(playlistItems.list, ~1 unit per 50) and only inserts what's missing, at the
right position. --prune also removes live entries no longer in the file
(replaced/dropped videos). --dry-run previews the diff. Combine with
maintain_playlist.py: `--rescrape` re-matches items rated <5 stars against
their Discogs pages first (picking up newly contributed videos), then the
sync applies the changes to the existing playlist.

Adopting an existing playlist (e.g. one the user built by hand on YouTube):
pass --playlist-id once, or record it in the items file as
playlist.playlist_id. Resolution order: --playlist-id, then the items file's
playlist.playlist_id, then the local *_progress.json. A --dry-run reporting
"add: 0 | stale: 0" proves live and file are identical — adoption complete.
Record playlist_id (and url) in the items file's playlist block as the
durable record; the *_progress.json this script writes is local resume state
(gitignore it). Adoption never rewrites the live playlist's title or
description — change those via the playlists.update endpoint if needed.

Quota: playlists.insert = 50 units, each insert/delete = 50 units, listing ~1
per 50. A no-change re-run costs ~5 units; interrupted runs just re-run —
the live diff resumes naturally.
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SCOPE = "https://www.googleapis.com/auth/youtube"
REDIRECT_PORT = 8765


def load_items_file(path):
    """Return (meta_dict, item_dicts). Tolerates v1 schema, bare lists, and
    legacy key spellings (videoId/id, youtube_url/url)."""
    data = json.load(open(path))
    meta = {}
    if isinstance(data, dict):
        pl = data.get("playlist")
        if isinstance(pl, dict):
            meta = pl
        elif isinstance(pl, str):
            meta = {"title": pl, "description": data.get("description", "")}
        items = data.get("items")
        if not isinstance(items, list):
            items = next((v for v in data.values() if isinstance(v, list)), [])
    else:
        items = data
    norm = []
    for it in items:
        if isinstance(it, str):
            norm.append({"video_id": it, "label": it})
            continue
        vid = it.get("video_id") or it.get("videoId") or it.get("id")
        if not vid:
            continue
        label = (it.get("label")
                 or " – ".join(x for x in (it.get("artist"), it.get("track")) if x)
                 or vid)
        norm.append({"video_id": vid, "label": label})
    return meta, norm


def api(method, path, token, body=None, params=None):
    url = f"https://www.googleapis.com/youtube/v3/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if body.strip() else {}  # DELETE returns 204/empty


def oauth_loopback(client_id, client_secret):
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": f"http://localhost:{REDIRECT_PORT}",
        "response_type": "code", "scope": SCOPE, "access_type": "offline", "prompt": "consent"})
    holder = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            holder["code"] = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query).get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write("<h2>Authorized — close this tab and return to the terminal.</h2>".encode())

        def log_message(self, *a):
            pass

    srv = HTTPServer(("localhost", REDIRECT_PORT), H)
    print("\nOpening browser for Google authorization...\nIf it doesn't open, visit:\n" + auth_url + "\n")
    webbrowser.open(auth_url)
    while "code" not in holder:
        srv.handle_request()
    body = urllib.parse.urlencode({
        "code": holder["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": f"http://localhost:{REDIRECT_PORT}",
        "grant_type": "authorization_code"}).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=body), timeout=30))
    print("Authorized OK.")
    return tok["access_token"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default="playlist_items.json")
    ap.add_argument("--title", help="overrides the items file's playlist.title")
    ap.add_argument("--description", help="overrides the items file's playlist.description")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"],
                    help="overrides the file; final fallback is private (let the user opt into public)")
    ap.add_argument("--token", help="OAuth access token (Playground quick path)")
    ap.add_argument("--client-id")
    ap.add_argument("--client-secret")
    ap.add_argument("--playlist-id", help="adopt an existing playlist instead of the progress file / creating one")
    ap.add_argument("--prune", action="store_true",
                    help="also remove live playlist entries no longer in the items file (e.g. replaced videos)")
    ap.add_argument("--dry-run", action="store_true", help="show the planned diff without touching the playlist")
    ap.add_argument("--rescrape", action="store_true",
                    help="first run maintain_playlist.py rescrape on items rated <5 (needs Discogs token)")
    ap.add_argument("--rescrape-all", action="store_true", help="as --rescrape but for every item")
    args = ap.parse_args()

    items_path = pathlib.Path(args.items)

    if args.rescrape or args.rescrape_all:
        import subprocess
        maintain = pathlib.Path(__file__).parent / "maintain_playlist.py"
        if not maintain.exists():
            sys.exit("--rescrape needs maintain_playlist.py next to this script (copy it from the skill).")
        cmd = [sys.executable, str(maintain), "rescrape", "--items", str(items_path)]
        if args.rescrape_all:
            cmd.append("--all")
        subprocess.run(cmd, check=True)

    if args.token:
        token = args.token
    elif args.client_id and args.client_secret:
        token = oauth_loopback(args.client_id, args.client_secret)
    elif args.dry_run:
        token = None
    else:
        sys.exit("Auth needed: --token OR --client-id/--client-secret (see header of this file).")

    meta, items = load_items_file(items_path)
    title = args.title or meta.get("title")
    if not title:
        sys.exit("No playlist title: pass --title or put playlist.title in the items file.")
    description = args.description if args.description is not None else meta.get("description", "")
    privacy = args.privacy or meta.get("privacy") or "private"
    if not items:
        sys.exit("No items with video ids found in the items file.")
    desired = list(dict.fromkeys(it["video_id"] for it in items))  # ordered, deduped
    labels = {it["video_id"]: it["label"] for it in items}

    progress_path = items_path.with_name(items_path.stem + "_progress.json")
    prog = json.load(open(progress_path)) if progress_path.exists() else {}
    playlist_id = args.playlist_id or meta.get("playlist_id") or prog.get("playlist_id")

    if not playlist_id:
        if args.dry_run:
            print(f"DRY: would create playlist '{title}' ({privacy}) and add all {len(desired)} items.")
            return
        pl = api("POST", "playlists", token, params={"part": "snippet,status"}, body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy}})
        playlist_id = pl["id"]
        print(f"Created playlist ({privacy}): https://www.youtube.com/playlist?list={playlist_id}")
    else:
        print(f"Syncing playlist: https://www.youtube.com/playlist?list={playlist_id}")
    progress_path.write_text(json.dumps({"playlist_id": playlist_id}))

    # Idempotency: diff the items file against the LIVE playlist state
    # (playlistItems.list ~1 unit per 50; a no-change re-run costs ~5 units).
    existing, page_token = [], None
    if token:
        while True:
            params = {"part": "snippet", "playlistId": playlist_id, "maxResults": 50}
            if page_token:
                params["pageToken"] = page_token
            d = api("GET", "playlistItems", token, params=params)
            for e in d.get("items", []):
                existing.append({"item_id": e["id"],
                                 "video_id": e["snippet"]["resourceId"].get("videoId")})
            page_token = d.get("nextPageToken")
            if not page_token:
                break
    have = [e["video_id"] for e in existing]
    to_add = [v for v in desired if v not in have]
    to_remove = [e for e in existing if e["video_id"] not in desired]

    print(f"Live: {len(have)} | file: {len(desired)} | add: {len(to_add)} | "
          f"stale: {len(to_remove)}{' (use --prune to remove)' if to_remove and not args.prune else ''}")
    if args.dry_run:
        for v in to_add:
            print(f"  DRY + {labels.get(v, v)} at position {desired.index(v)}")
        for e in to_remove:
            print(f"  DRY - {labels.get(e['video_id'], e['video_id'])}{'' if args.prune else ' (kept without --prune)'}")
        return

    if args.prune:
        for e in to_remove:
            try:
                api("DELETE", "playlistItems", token, params={"id": e["item_id"]})
                print(f"  - removed {labels.get(e['video_id'], e['video_id'])}")
                have.remove(e["video_id"])
            except urllib.error.HTTPError as err:
                print(f"  ! remove failed {e['video_id']}: {err.code}")
            time.sleep(0.3)

    for vid in to_add:
        pos = min(desired.index(vid), len(have))
        body = {"snippet": {"playlistId": playlist_id, "position": pos,
                            "resourceId": {"kind": "youtube#video", "videoId": vid}}}
        for attempt in range(4):
            try:
                api("POST", "playlistItems", token, params={"part": "snippet"}, body=body)
                have.insert(pos, vid)
                print(f"  + {labels.get(vid, vid)}")
                break
            except urllib.error.HTTPError as e:
                err = e.read().decode()[:300]
                if e.code == 403 and "quota" in err.lower():
                    sys.exit("\nDaily quota exhausted — re-run later; the sync resumes from live state.")
                if e.code == 409 or "duplicate" in err.lower():
                    print(f"  = already present: {labels.get(vid, vid)}")
                    break
                if attempt == 3:
                    print(f"  ! FAILED {labels.get(vid, vid)}: {e.code} {err[:120]}")
                    break
                time.sleep(3 * (attempt + 1))
        time.sleep(0.4)

    print(f"\nIn sync: {len([v for v in desired if v in have])}/{len(desired)} tracks")
    print(f"Playlist: https://www.youtube.com/playlist?list={playlist_id}")


if __name__ == "__main__":
    main()
