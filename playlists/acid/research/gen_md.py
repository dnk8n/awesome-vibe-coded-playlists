#!/usr/bin/env python3
"""Generate the acid playlist markdown from verified results.json."""
import json, pathlib

SC = pathlib.Path(__file__).parent
rows = json.load(open(SC / "results.json"))
YT = {x["id"]: x for x in json.load(open(SC / "yt_final.json"))} if (SC / "yt_final.json").exists() else {}

# Manual track overrides after eyeballing tracklists: {release_id: exact_track_title}
OVERRIDES = json.load(open(SC / "overrides.json")) if (SC / "overrides.json").exists() else {}

BONUS = {"G": "🌍", "F": "♀"}

ARTIST_OVERRIDES = {
 166037: "DJ Deeon Presents The Youngest Female DJ DJ Jana Rush / DJ Deeon",
 1517: "Armando Presents Robert Armani",
 70819: "Photon, Inc. Featuring Paula Brion",
 2133: "Aphrohead AKA Felix Da Housecat",
 32206: "DJ Pierre presents Doomsday",
 65053: "Adonis Presents Hieroglyphic Being",
 1795116: "Adonis Presents Noleian Reusse",
 1169584: "Armando Gallop Featuring Sharvette",
 1534376: "DJ Pierre AKA Da Master Blaster",
 10949063: "Posthuman Ft Josh Caffe",
 14087754: "Paranoid London With Josh Caffe",
 15864769: "Honey Dijon Feat. Josh Caffe",
 26231888: "Josh Caffe W/ Al White",
 16890651: "Abe Duque Vs Blake Baxter",
 14519047: "Fast Eddie X Liquid",
 14921129: "Adonis aka Jak Phrost",
 2869649: "Ron Hardy",
 43814: "DJ Skull",
 6029196: "FunkinEven Feat. Jay Daniel",
 6774268: "Boo Williams Vs Glen Underground",
}

def fmt_date(released, year):
    r = (released or str(year)).replace("-00", "")
    return r

def esc(s):
    return (s or "").replace("|", "\\|")

lines = []
lines.append("# ACID — A Black-Heritage Canon, Year by Year")
lines.append("")
lines.append("A celebration of acid as Black music: three notable acid tracks per year, every entry produced by — or with core creative involvement of — Black artists, from the music's inception to now.")
lines.append("")
lines.append("**Where acid begins.** Acid was invented in Black Chicago. The sound — a Roland TB-303 bassline detuned into a living squelch — was created in **1985** (Phuture's *Acid Tracks* circulating on reel at Ron Hardy's Music Box; Marshall Jefferson & Sleezy D's *I've Lost Control* cut the same year). The first records hit vinyl in **1986**, so the year-by-year canon below starts there. \"Acid\" is read broadly (house, techno, footwork, electro, modular experimentalism) but honestly — where a pick stretches the definition, the notes say so.")
lines.append("")
lines.append("**Legend:** 🌍 = artist from outside UK/Europe/USA · ♀ = non-male core involvement (women, trans and non-binary artists, female vocalists) · 🎧 = release verified on Discogs, but my track pick off it deserves an ear-check.")
lines.append("")
lines.append("Every link goes to the exact Discogs release page; artist and track are copied as credited there. The ▶ YouTube pick for each entry comes from the videos embedded on that Discogs page (validated via the YouTube API); where the page had no working video of the selected cut, the Notes say exactly what was used instead — and 5 entries with no page video at all are skipped from the playlist per the ground rules. (A planned Phase 2 will trace the lineage *backwards* from 1985 — 303 and modular records that sounded acid before acid.)")
lines.append("")
lines.append("| Release Date | Artist | Track | Link | YouTube | Notes | Status/Progress |")
lines.append("|---|---|---|---|---|---|---|")

cur_year = None
count = 0
for r in sorted(rows, key=lambda x: (x["year"], fmt_date(x.get("released"), x["year"]))):
    if "error" in r:
        continue
    year = r["year"]
    track = OVERRIDES.get(str(r["id"]), r["track"])
    artist = ARTIST_OVERRIDES.get(r["id"]) or r.get("track_artist") or r["artist"]
    date = fmt_date(r.get("released"), year)
    bonus = "".join(BONUS[b] for b in r.get("bonus", ""))
    notes = (bonus + " " if bonus else "") + r["notes"]
    matched = r.get("matched") or str(r["id"]) in OVERRIDES or not r.get("hint")
    status = "✅ Verified" if (r.get("matched") or str(r["id"]) in OVERRIDES) else "✅ Verified · 🎧"
    import re as _re
    link_label = _re.sub(r"\s*\(\d+\)", "", r.get("label") or "Discogs").replace(" none", "").strip() or "Discogs"
    yt = YT.get(r["id"], {})
    ytv = yt.get("video")
    ytcell = f"[▶ Watch](https://youtu.be/{ytv['id']})" if ytv else "—"
    if yt.get("ytnote"):
        notes = notes.rstrip(".") + ". " + yt["ytnote"]
    lines.append(f"| {date} | {esc(artist)} | {esc(track)} | [{esc(link_label)}]({r['url']}) | {ytcell} | {esc(notes)} | {status} |")
    count += 1
    # open-slot insertions
    if year == 2004 and r["id"] == 223085:
        lines.append("| 2004 | *TBD* | *third slot open* | — | — | 2004 is the thinnest year found so far. Leading candidate: Felix Da Housecat's *Devin Dazzle & The Neon Fever* LP (acid-adjacent electro-house). | 🔎 Open — research ongoing |")

md = "\n".join(lines)

tail = """

## Alternates bench (verified, ready to swap in)

- **1988:** Fast Eddie – *Acid Thunder* ([D.J. International](https://www.discogs.com/release/2752)) · Phuture – *We Are Phuture* ([Trax](https://www.discogs.com/release/1165)) · Mike Dunn – *So Let It Be Houze!* ([Westbrook](https://www.discogs.com/release/4519)) · Gherkin Jerks – *Stomp The Beat* ([Gherkin](https://www.discogs.com/release/37438)) · D Mob – *We Call It Acieed* (Danny D = Daniel Kojo Poku, Black British; UK #3)
- **1991:** Robert Armani – *Ambulance* ([Dance Mania](https://www.discogs.com/release/1520))
- **1992:** Mike Dunn – *Magic Feet (The Remixes)* ([Djax-Up-Beats](https://www.discogs.com/release/1597)) · Bam Bam – *I Get A Rush* (Westbrook)
- **1993:** Phuture – *Inside Out* ([Strictly Rhythm](https://www.discogs.com/release/4515)) · Robert Armani – *Circus Bells (Rmx)* on *Beat Trax* ([ACV](https://www.discogs.com/release/3391))
- **1996:** Robert Armani – *Circus Bells* ([Djax-Up-Beats](https://www.discogs.com/release/600))
- **1997:** K. Hand – *Project 5 EP* ([Acacia](https://www.discogs.com/release/156003))
- **2016:** Steven Julien – *Fallen* LP ([Apron](https://www.discogs.com/release/8617423)) · Josh Caffe + The Subs – *Revolution* (Batty Bass)
- **2020:** Hieroglyphic Being – *Black Hands Vol 2* ([+ + +](https://www.discogs.com/release/14956367), Techno/Acid-tagged — swapped out for BadSista's ACID APERTO)
- **2018:** Russell E.L. Butler – *The Home I'd Build For Myself And All My Friends* ([Left Hand Path](https://www.discogs.com/release/12816572))
- **2025:** Mike Dunn – *Tracks From The Beginning Vol 1* ([Dance Mutha](https://www.discogs.com/release/32867616), archival originals)

## Research queue

- **2004, third slot** — see open row above.
- **2026** — year in progress (checked through July 2026); replace the Clone reissue row as new originals by Black artists land. Watch: Josh Caffé, DJ Pierre/Afro Acid, Chicago Vinyl Records, HAUS of ALTR, Hakuna Kulala.
- **Track-pick ear-checks (🎧)** — rows where the release is verified but my choice of cut off an EP/LP should be confirmed by listening.
- **Non-Discogs leads** (Bandcamp-only): Turkana (South Sudanese, Hakuna Kulala) — no Discogs entries yet. (BadSista's *ACID APERTO* found its Discogs anchor via her FACT Mix 754 page and now sits in the 2020 slot.)

## Phase 2 (planned): before acid

Tracing backwards from 1985 — TB-303, modular and synth records that made acid sounds before the word existed (e.g. Charanjit Singh's *Ten Ragas to a Disco Beat*, 1982 🌍; early 303 experiments in boogie, Italo and Chicago proto-house; Black modular/synth pioneers). Planned as the next phase; seed notes in [research/ideas-for-pre-acid.md](research/ideas-for-pre-acid.md).

---
*Method: candidates curated from acid history + Discogs style scans, then every pick verified against the Discogs API (release page, credited artist name, tracklist, release date). Sorted by release date; Discogs gives day-level dates only for the digital era, so older entries sort by year.*
"""

out = md + tail
target = SC.parent / "acid-playlist.md"
target.write_text(out)
print(f"Wrote {target} — {count} table rows")
