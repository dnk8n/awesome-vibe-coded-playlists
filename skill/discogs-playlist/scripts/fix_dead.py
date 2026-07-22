#!/usr/bin/env python3
"""Validate every playlist video id; for each dead/private one, find a validated
replacement from the SAME Discogs release page (videos_src in enriched.json),
matching the chosen track. Writes video_fixes.json {dead:[...], override:{rank:id}}
which assemble.py merges. Run this (with a YouTube OAuth token or API key), then
re-run assemble.py, then create_playlist.py.

Usage: python3 fix_dead.py <ya29-token-or-api-key>
"""
import json, pathlib, re, sys, unicodedata, urllib.parse, urllib.request
HERE = pathlib.Path.cwd()                    # run from the playlist's research/ dir (data lives here)
KEY = sys.argv[1] if len(sys.argv) > 1 else (pathlib.Path.home()/".yt_key").read_text().strip()
OAUTH = KEY.startswith("ya29.")
ITEMS = json.load(open(HERE.parent/"playlist_items.json"))["items"]
ENR = {r["rank"]: r for r in json.load(open(HERE/"enriched.json"))}
EXIST_DEAD = set()
if (HERE/"video_fixes.json").exists():
    EXIST_DEAD = set(json.load(open(HERE/"video_fixes.json")).get("dead", []))

def norm(s): return re.sub(r"[.']","",unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower())
def ntok(s): return set(w for w in re.findall(r"[a-z0-9]+", norm(s)) if w)
def base(t): b=re.sub(r"\s*\([^)]*\)\s*"," ",t or "").strip(" -"); return b or (t or "")

def validate(ids):
    """Return set of ids that are public/playable."""
    ok = set()
    ids = [i for i in ids if i]
    for i in range(0, len(ids), 50):
        chunk = ids[i:i+50]
        params = {"part":"status,contentDetails","id":",".join(chunk),"maxResults":50}
        if not OAUTH: params["key"] = KEY
        url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization":f"Bearer {KEY}"} if OAUTH else {})
        d = json.load(urllib.request.urlopen(req, timeout=30))
        for it in d.get("items", []):
            if it["status"]["privacyStatus"] == "public":
                ok.add(it["id"])
    return ok

cur = [it["video_id"] for it in ITEMS]
good = validate(cur)
dead_items = [it for it in ITEMS if it["video_id"] not in good]
print(f"{len(good)}/{len(cur)} public | dead: {[ (it['rank'], it['video_id']) for it in dead_items ]}")

new_dead, override = set(EXIST_DEAD), {}
for it in dead_items:
    rk = it["rank"]; new_dead.add(it["video_id"])
    enr = ENR.get(rk, {})
    track = enr.get("chosen_track") or it.get("track_prompt","")
    vids = [v for v in (enr.get("videos_src") or []) if v.get("id") and v["id"] not in new_dead
            and (v.get("dur") or 0) <= 900]
    # rank candidates: exact mix match first, then base title, then any
    def score(v):
        t = ntok(v["title"])
        if ntok(track) <= t: return 3
        if ntok(base(track)) <= t: return 2
        return 1
    cands = sorted(vids, key=score, reverse=True)
    repl = None
    for c in cands:
        if c["id"] in validate([c["id"]]):
            repl = c["id"]; break
        new_dead.add(c["id"])
    if repl:
        override[str(rk)] = repl
        print(f"  #{rk}: {it['video_id']} -> {repl}")
    else:
        print(f"  #{rk}: NO valid replacement on the page (will drop from playlist)")

json.dump({"dead": sorted(new_dead), "override": override},
          open(HERE/"video_fixes.json","w"), indent=1)
print(f"\nwrote video_fixes.json: {len(new_dead)} dead, {len(override)} replacements. "
      f"Now: python3 assemble.py  &&  create_playlist.py --token ...")
