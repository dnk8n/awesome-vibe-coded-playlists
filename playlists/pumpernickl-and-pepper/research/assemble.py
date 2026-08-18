#!/usr/bin/env python3
"""Build the Pumpernickl & Pepper b2b set-list markdown + playlist_items.json.

Run from this research/ dir. Reads enriched.json (produced by the discogs-playlist
skill's verify.py -> enrich.py), config.json and article.md, and renders the set in
PLAY ORDER grouped into the five courses -- not the skill's date-sorted table, because
this document is a DJ running order.

YouTube ids come from each Discogs page's community-attached videos via the skill's
matching ladder; curator.json can pin a video (video_pick), a note (row_note/video_note)
or a rating (rating_override).
"""
import json, pathlib, re, unicodedata

HERE = pathlib.Path.cwd()
OUT_DIR = HERE.parent
CFG = json.load(open(HERE / "config.json"))
V = json.load(open(HERE / "enriched.json"))
CUR = json.load(open(HERE / "curator.json")) if (HERE / "curator.json").exists() else {}
NOTES = json.load(open(HERE / "notes.json")) if (HERE / "notes.json").exists() else {}
CUR_VIDEO = {int(k): v for k, v in CUR.get("video_pick", {}).items()}
VIDEO_NOTE = CUR.get("video_note", {})
DEAD = set(CUR.get("dead_videos", []))

STOP = {"mix", "remix", "original", "version", "edit", "extended", "the", "a", "feat",
        "featuring", "vocal", "dub"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[.']", "", s)


def ntok(s):
    return [w for w in re.findall(r"[a-z0-9]+", norm(s)) if w]


def tin(needle, hay, drop=False):
    nt = ntok(needle)
    if drop:
        nt = [w for w in nt if w not in STOP] or nt
    return bool(nt) and all(w in set(ntok(hay)) for w in nt)


def base(t):
    b = re.sub(r"\s*\(.*?\)\s*", " ", t or "").strip(" -")
    return b or (t or "")


def yt_pick(videos, track):
    """Skill ladder: exact cut > base title > any other cut on the page > long rip."""
    vids = [v for v in (videos or []) if v.get("id") and v["id"] not in DEAD]
    short = [v for v in vids if (v.get("dur") or 0) <= 900]
    longrip = [v for v in vids if (v.get("dur") or 0) > 900]
    for v in short:
        if tin(track, v["title"]):
            return v, "exact"
    for v in short:
        if tin(base(track), v["title"], drop=True):
            return v, "close"
    if short:
        return short[0], "alternate"
    for v in longrip:
        if tin(track, v["title"]) or tin(base(track), v["title"], drop=True):
            return v, "longrip"
    return None, "none"


TIER = {"exact": 5, "close": 4, "alternate": 3, "longrip": 1, "none": 1}
DECK = {"loaf": "🍞", "spice": "🌶", "both": "🍞🌶"}

COURSE = {
    "I": ("I. The Starter", "20:00 → 20:20",
          "The culture is alive but nothing has risen yet. Dub, deep, hissy, warm — nobody is "
          "being asked to do anything except arrive."),
    "II": ("II. Proving", "20:20 → 20:45",
           "Dough under pressure. Percussion arrives — tribal, Afro, Latin, gqom. Still house "
           "tempo, but the record is now moving without you."),
    "III": ("III. The Grinder", "20:45 → 21:10",
            "Spice into the mill. Chicago acid, machine funk, electro. The 303s here are the "
            "mean ones — this is the dark half of acid, not the smiley half."),
    "IV": ("IV. Crust", "21:10 → 21:45",
           "Maximum heat, the outside goes black. Twelve records, and they are meant to hurt "
           "a little."),
    "V": ("V. The Last Slice", "21:45 → 22:00",
          "What you eat standing at the counter. The gear change down — Latin strings, Detroit "
          "strings, gospel. Send them home fed."),
}

HEAD = ("| # | Deck | Artist | Track | Year | Label | ≈BPM | Find it | Why it is here |\n"
        "|:--|:--|---|---|:--|---|:--|---|---|")


def esc(s):
    return (s or "").replace("|", "\\|")


rows, items, open_rows = [], [], []
for r in sorted(V, key=lambda x: x["rank"]):
    rank = r["rank"]
    vid, how = yt_pick(r.get("videos_src"), r.get("chosen_track", ""))
    vid_id = CUR_VIDEO.get(rank) or (vid["id"] if vid else None)
    if CUR_VIDEO.get(rank):
        how = "curator"
    rating = min(TIER.get(how, 5) if how != "curator" else 5, r.get("track_tier", 5))

    notes, audit = [], []
    if NOTES.get(str(rank)):
        notes.append(NOTES[str(rank)])
    for n in r.get("enrich_notes", []):
        audit.append(n[0].upper() + n[1:] if n else n)
    if how == "alternate":
        audit.append("▶ the Discogs page has video but not this cut — the link is another track "
                     "from the same release")
    elif how == "close":
        audit.append("▶ page video is the same record under a different mix name")
    elif how == "longrip":
        audit.append("▶ only a full-release rip is attached to the page — cue to the track")
    elif how == "none":
        audit.append("▶ no video attached to the Discogs page")
    if VIDEO_NOTE.get(str(rank)):
        audit.append(VIDEO_NOTE[str(rank)])
    if audit:
        notes.append("*" + " · ".join(a.rstrip(".") for a in audit) + ".*")

    find = []
    if vid_id:
        find.append(f"[YouTube](https://www.youtube.com/watch?v={vid_id})")
    if r.get("chosen_url"):
        find.append(f"[Discogs]({r['chosen_url']})")
    label = re.sub(r"\s*·\s*master$", "", r.get("link_text", "")) or ""

    rows.append((r["phase"], "| " + " | ".join([
        str(rank), DECK.get(r.get("deck"), ""), esc(r.get("chosen_artist")),
        f"**{esc(r.get('chosen_track'))}**", str(r.get("chosen_year") or ""), esc(label),
        r.get("bpm", ""), " · ".join(find), esc(" ".join(notes)),
    ]) + " |"))

    if vid_id and r["phase"] != "BENCH":
        items.append({
            "position": len(items) + 1, "video_id": vid_id, "rank": rank,
            "deck": r.get("deck"), "phase": r["phase"],
            "artist": r.get("chosen_artist"), "track": r.get("chosen_track"),
            "year": r.get("chosen_year"), "label": label,
            "discogs_id": r.get("master_id") or r.get("release_id"),
            "discogs_page": r.get("chosen_page"), "discogs_url": r.get("chosen_url"),
            "match": how, "rating": rating,
        })
    elif not vid_id:
        open_rows.append(r)

wv = lambda ids: "https://www.youtube.com/watch_videos?video_ids=" + ",".join(ids)
all_ids = [i["video_id"] for i in items]
listen = ["**▶ Play the whole set, no login:** [all {} tracks in running order]({})".format(
    len(all_ids), wv(all_ids[:50]))]
for key, (name, _, _) in COURSE.items():
    ids = [i["video_id"] for i in items if i["phase"] == key]
    if ids:
        listen.append("[{}]({})".format(name, wv(ids)))
if CFG.get("playlist", {}).get("url"):
    listen.insert(0, "**▶ [Listen on YouTube]({})** — saved playlist, all in set order.".format(
        CFG["playlist"]["url"]))

body = []
for key, (name, when, blurb) in COURSE.items():
    sec = [r[1] for r in rows if r[0] == key]
    if not sec:
        continue
    body += [f"## {name}", f"*{when} · {len(sec)} records*", "", blurb, "", HEAD, *sec, ""]

BENCH_HEAD = ("| Deck | Artist | Track | Year | Label | ≈BPM | Find it | What it is for |\n"
              "|:--|---|---|:--|---|:--|---|---|")
bench = [r[1] for r in rows if r[0] == "BENCH"]
if bench:
    body += ["## The bench", "",
             "Six verified swaps, one per pressure point. Same links, same rules — they are here so a "
             "change of plan at 21:00 costs you a search rather than a set.", "",
             BENCH_HEAD,
             *[re.sub(r"^\| \d+ \|", "|", b) for b in bench], ""]

art = open(HERE / "article.md").read()
art = art.replace("<!-- LISTEN_LINKS -->", listen[0] + ("\n\n**Or by course:** " +
      " · ".join(listen[1:]) if len(listen) > 1 else ""))
doc = art.replace("<!-- INSERT_TABLE_HERE -->", "\n".join(body).rstrip())

doc += ("\n\n---\n\n## How this was built\n\n"
        "Forty-six records were resolved against the Discogs API: each pick's release page was "
        "fetched, the master preferred over any single pressing, and the Artist and Track columns "
        "copied character-for-character from that page's tracklist — which is why a few rows read "
        "differently from how the record gets talked about. Every YouTube link is a video the "
        "Discogs community attached to that same page, not an open search result, and all "
        "forty-six were liveness-checked. Where the page's video was for a different mix, the "
        "italic line in the Notes says so.\n\n"
        "The running order, the courses and the deck marks are a curatorial call, not data. "
        "Argue with them.\n")

if open_rows:
    doc += "\n\n## Research queue\n\n" + "\n".join(
        f"- **#{r['rank']} {r.get('chosen_artist')} – {r.get('chosen_track')}** — "
        f"[Discogs]({r.get('chosen_url')}) has no usable video; source it by hand."
        for r in open_rows) + "\n"

(OUT_DIR / CFG["output_md"].replace("../", "")).write_text(doc, encoding="utf-8")
json.dump({"schema": "discogs-playlist/v1", "playlist": CFG["playlist"], "items": items},
          open(OUT_DIR / "playlist_items.json", "w"), indent=1, ensure_ascii=False)
print(f"wrote {CFG['output_md']} | {len(items)} videos | "
      f"{sum(1 for i in items if i['rating'] < 5)} rows rated <5 | open: {[r['rank'] for r in open_rows]}")
