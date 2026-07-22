#!/usr/bin/env python3
"""Pre-finalise self-check for a built playlist — an INDEPENDENT audit (deliberately does
NOT import enrich.py, so its own simple heuristics can catch enrich's bugs). Run from a
playlist's research/ dir after enrich.py. Prints a report and exits 1 if any issue is found:

  * master-link invariant — every row that has a Discogs master IS master-linked
  * wrong-song — the chosen track's base title doesn't match the source title
  * missed cut  — no version was requested and the pick isn't club/extended/long, yet the
                  chosen page's tracklist has one (a better cut the selection skipped)
  * dead video  — a picked video id is in video_fixes.json's dead list

plus a summary: verified/open counts, master/release split, rating spread, source-deviation
count, and any video shared by more than one rank.
"""
import json, math, pathlib, re, sys, unicodedata
from collections import Counter
HERE = pathlib.Path.cwd()
def load(name, default):
    p = HERE / name
    return json.load(open(p)) if p.exists() else default

E = load("enriched.json", [])
RELC = load("release_cache.json", {}); MC = load("master_cache.json", {})
CUR = load("curator.json", {}).get("track_pick", {})
DEAD = set(load("video_fixes.json", {}).get("dead", []))
items_p = HERE.parent / "playlist_items.json"
ITEMS = json.load(open(items_p)).get("items", []) if items_p.exists() else []

def norm(s): return re.sub(r"[.']", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower())
def ntok(s): return set(w for w in re.findall(r"[a-z0-9]+", norm(s)) if w)
def base(t): b = re.sub(r"\s*\([^)]*\)\s*", " ", t or "").strip(" -"); return b or (t or "")
def has(t, *kw): tt = ntok(t); return any(k in tt for k in kw)
def real(tl):
    tl = tl or []
    wp = [t for t in tl if str(t.get("pos") or "").strip() and (t.get("title") or "").strip()]
    return wp or [t for t in tl if (t.get("title") or "").strip()]
VK = {"mix","version","edit","remix","dub","vocal","instrumental","acapella","accapella","radio",
      "club","extended","original","bonus","beats","piano","gospel","classic","main","zanzibar","house","garage"}
def reqver(tk):
    for p in reversed(re.findall(r"\(([^)]*)\)", tk or "")):
        pt = ntok(p)
        if "demo" in pt: continue
        if pt & VK: return p.strip()
    return None

issues = []
verified = [r for r in E if r.get("status") == "verified"]
for r in verified:
    rk = r["rank"]; ch = r.get("chosen_track", ""); pb = ntok(base(r.get("track_listed", "")))
    if r.get("master_id") and r.get("chosen_page") != "master":
        issues.append(f"#{rk}: has master {r['master_id']} but is release-linked")
    titled = any(isinstance(n, str) and n.startswith("source titles") for n in r.get("enrich_notes", []))
    if pb and not titled and len(pb & ntok(base(ch))) < max(1, math.ceil(0.5 * len(pb))):
        issues.append(f"#{rk}: chosen '{ch}' base doesn't match source '{r.get('track_listed')}' (undocumented)")
    if str(rk) not in CUR and not reqver(r.get("track_listed", "")) and not has(ch, "club", "extended", "long"):
        tl = real(MC.get(str(r.get("master_id")), {}).get("tracklist")) if r.get("chosen_page") == "master" \
            else real(RELC.get(str(r.get("release_id")), {}).get("tracklist"))
        cands = [t for t in tl if pb and len(pb & ntok(t["title"])) >= max(1, math.ceil(0.6 * len(pb)))]
        better = [t["title"] for t in cands if has(t["title"], "club", "extended", "long")]
        if better:
            issues.append(f"#{rk}: picked '{ch}' but page has club/extended/long: {better}")
for it in ITEMS:
    if it.get("video_id") in DEAD:
        issues.append(f"#{it.get('rank')}: video {it['video_id']} is in the dead list")

open_rows = [r["rank"] for r in E if r.get("status") != "verified"]
mp = sum(1 for r in verified if r.get("chosen_page") == "master")
ratings = {k: v for k, v in sorted(Counter(it.get("rating") for it in ITEMS).items()) if k is not None}
devs = sum(1 for r in verified for n in r.get("enrich_notes", []) if isinstance(n, str) and n.startswith("source "))
vids = Counter(it.get("video_id") for it in ITEMS)
dups = [v for v, c in vids.items() if v and c > 1]
print(f"verified: {len(verified)}/{len(E)} | open: {open_rows or 'none'}")
print(f"master-linked: {mp} | release-linked: {len(verified) - mp}")
print(f"ratings: {ratings} | source-deviation notes: {devs}")
if dups: print(f"videos shared by >1 rank: {dups}")
print(f"\nISSUES: {len(issues)}")
for i in issues: print("  " + i)
sys.exit(1 if issues else 0)
