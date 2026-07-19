# Detroit Techno Mini-Canon, 1991–1993

Two notable Detroit techno tracks per year (1991–1993), each with core involvement from a Black Detroit artist. Source of truth: **discogs.com** original-pressing release pages (via the Discogs API, retrieved 2026-07-17). Artist and track names are reproduced **exactly as credited** on the linked Discogs release page. Every YouTube link is taken from the videos embedded on that same Discogs release page and was validated as live via the YouTube Data API v3 on 2026-07-17.

| # | Release date (Discogs) | Artist (as credited) | Track (as credited) | Discogs release | YouTube (from Discogs page) | Why it's notable | Status |
|---|---|---|---|---|---|---|---|
| 1 | 1991 | Underground Resistance | Nation 2 Nation | [Nation 2 Nation — UR005](https://www.discogs.com/release/2113-Underground-Resistance-Nation-2-Nation) | [watch?v=rq6ZcR5qgaY](https://www.youtube.com/watch?v=rq6ZcR5qgaY) | Title track (A3) of an early UR 12" on the collective's own Black-owned Detroit label. "Mad" Mike Banks and Jeff Mills at their most utopian — techno as pan-national communication — and a cornerstone of the militant, anti-corporate UR catalog. | Verified: live, public, embeddable (5:13, matches Discogs 5:13) |
| 2 | 1991-09-01 | X-101 | Sonic Destroyer | [X-101 — TRESOR 1](https://www.discogs.com/release/23455-X-101-X-101) | [watch?v=VtqJdISUEtE](https://www.youtube.com/watch?v=VtqJdISUEtE) | A1 of the very first Tresor release. X-101 is UR (Mike Banks, Jeff Mills, Robert Hood); this pounding track sealed the Detroit–Berlin axis and became the founding anthem of the Tresor vault sound. | Verified: live, public, embeddable (5:01, matches Discogs 5:01) |
| 3 | 1992 | Underground Resistance | Jupiter Jazz | [World 2 World — UR020](https://www.discogs.com/release/2123-Underground-Resistance-World-2-World) | [watch?v=bE_GYsbzVXw](https://www.youtube.com/watch?v=bE_GYsbzVXw) | A2 of the World 2 World EP — Mike Banks's melodic masterpiece and UR's pivot from riot techno toward "hi-tech jazz." Its icy string line is one of the most recognizable motifs in Detroit techno. | Verified: live, public, embeddable (4:30, matches Discogs 4:30) |
| 4 | 1992 | Drexciya | Sea Quake | [Deep Sea Dweller — SW1007](https://www.discogs.com/release/12769-Drexciya-Deep-Sea-Dweller) | [watch?v=BWrSpGzbWNc](https://www.youtube.com/watch?v=BWrSpGzbWNc) | A1 of Drexciya's debut EP on Shockwave (a UR sister label). James Stinson and Gerald Donald's opening statement launched the aquatic Afrofuturist mythology that made Drexciya one of electronic music's most storied projects. | Verified: live, public, embeddable (4:34, matches Discogs 4:34) |
| 5 | 1993 | Galaxy 2 Galaxy | Hi-Tech Jazz (The Science) | [Galaxy 2 Galaxy — UR 025](https://www.discogs.com/release/4276-Galaxy-2-Galaxy-Galaxy-2-Galaxy) | [watch?v=355tosXrZBg](https://www.youtube.com/watch?v=355tosXrZBg) | A1 of the double 12" from UR's jazz-fusion alias, led by Mike Banks. "Hi-Tech Jazz" is arguably the most beloved track in the UR catalog — an enduring Detroit anthem that named a whole strain of the city's techno. | Verified: live, public, embeddable (8:08, matches Discogs 8:08) |
| 6 | 1993 | Jeff Mills | Phase 4 | [Waveform Transmission Vol. 1 — Tresor 11](https://www.discogs.com/release/17518-Jeff-Mills-Waveform-Transmission-Vol-1) | [watch?v=MkZ3gPWYxc8](https://www.youtube.com/watch?v=MkZ3gPWYxc8) | A1 opener of Mills's first solo album after leaving UR. Waveform Transmission Vol. 1 is the blueprint for stripped, functional minimal techno and a milestone of the Detroit–Berlin exchange. (Often cited as 1992 elsewhere; Discogs, the source of truth here, dates Tresor 11 to 1993.) | Verified: live, public, embeddable (4:48, matches Discogs 4:48) |

## Black Detroit involvement (core, per track)

1. **Nation 2 Nation** — Underground Resistance: "Mad" Mike Banks and Jeff Mills (both Black Detroit artists; UR co-founders).
2. **Sonic Destroyer** — X-101 is the UR trio Mike Banks, Jeff Mills, and Robert Hood.
3. **Jupiter Jazz** — Underground Resistance, written/produced within UR by Mike Banks.
4. **Sea Quake** — Drexciya: James Stinson and Gerald Donald, both Black Detroit artists.
5. **Hi-Tech Jazz (The Science)** — Galaxy 2 Galaxy, the UR project led by Mike Banks.
6. **Phase 4** — Jeff Mills, solo.

## Methodology / verification notes

- **Source of truth:** Discogs original first-pressing release pages, fetched via the Discogs API (`api.discogs.com/releases/{id}`) on 2026-07-17. Artist names use the release-page artist credit; track titles are copied verbatim from the release tracklist (including subtitles, e.g. "Hi-Tech Jazz (The Science)").
- **Release-date sorting:** Discogs gives a day-level date only for TRESOR 1 (1991-09-01); the other five releases carry year-only precision. Rows are sorted by year, with within-year ties broken deterministically by Discogs release ID (2113 → 23455, 2123 → 12769, 4276 → 17518). This is consistent with the one known exact date.
- **YouTube links:** Each link was taken from the `videos` list embedded on the exact Discogs release page linked in the same row (not from a search). Matching was done by video title and by duration against the Discogs-listed video duration.
- **Liveness validation:** YouTube Data API v3 (`videos?part=status,snippet,contentDetails`) on 2026-07-17. All six returned `uploadStatus=processed`, `privacyStatus=public`, `embeddable=true`, and API durations matched the Discogs-embedded video durations exactly.
- **Companion file:** `playlist_items.json` lists the six validated YouTube video IDs in the chronological order above. Per instructions, no actual YouTube playlist was created (no OAuth).
