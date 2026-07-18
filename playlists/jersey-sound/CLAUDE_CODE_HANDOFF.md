# Handoff Brief: Jersey Sound Tracklist — Discogs API Validation

## What this is

A 67-year (1960–2026) DJ setlist tracing the lineage of the "Jersey Sound" (Club Zanzibar, Newark NJ, resident DJ Tony Humphries) back through its soul/gospel/disco roots and forward to today. The working file — `jersey-sound-setlist-DRAFT-v1.md` — has been built up over many rounds of manual web research. **This brief exists because manual web-search verification has proven error-prone** (three wrong release years found and fixed in the last round alone, one track found to have no real Discogs listing at all). The goal now is a proper script hitting the real Discogs API, not more manual searches.

## The task for Claude Code

1. Parse `jersey-sound-setlist-DRAFT-v1.md` — read every row (Year | Position | Artist | Track | Label | Discogs-link-or-note).
2. For every entry, use the Discogs API to independently confirm or correct three things: **(a)** a real release/master exists, **(b)** the track title on that release matches what's claimed, **(c)** the release year matches the row's year. Pull label + catalog number + duration while you're there — the doc wants these as standard discography fields.
3. Where an entry currently uses a 🔎 (generic search link) or is otherwise unconfirmed, find the *specific* release ID that best matches (prefer the original pressing unless the doc's notes say to prefer a specific later mix — see "Known methodology rules" below).
4. Where the current claim is wrong (title, year, or the release doesn't actually exist), fix it and flag what changed.
5. Output: an updated version of the tracklist with every entry either ✅ (verified via API, with the specific release ID, title-match, and year-match all confirmed) or ⚠️ (API search found nothing trustworthy — flag honestly, don't force a weak match).

## Discogs API basics (verify against live docs before coding — API details can drift)

- Developer docs: https://www.discogs.com/developers (fetch this first; don't trust these notes blindly)
- Base URL: `https://api.discogs.com`
- Useful endpoints: `GET /database/search?q=...&type=release` (or `type=master`), `GET /releases/{id}`, `GET /masters/{id}`
- Requires a descriptive `User-Agent` header — Discogs blocks generic/missing ones
- Unauthenticated requests are rate-limited fairly aggressively; a free personal access token (generated from Discogs account settings → Developers) raises the limit substantially. Worth having Dean generate one before running this at scale across 77 rows.
- Responses are JSON — `results[].id`, `results[].title`, `results[].year` from search; full tracklist under `tracklist[]` on the release/master detail endpoint.
- Build in retry/backoff — 77+ lookups will hit rate limits on a naive loop.

## Known methodology rules (don't rediscover these — they came from real back-and-forth in the source conversation)

- **One "slot" per year, but up to 3 tracks where there's genuine contention.** Not every year needs 3 — only add a 2nd/3rd where there's real independent backing (see next point), not just "also a nice song."
- **"Genuine contention" = independently attested**, not just present on one list. Acceptable evidence: Mixmag's "20 Best New Jersey House Records" (Bill Brewster), the fan-compiled "Jersey Sound Top 100," direct Tony Humphries production/remix credit (visible in Discogs credits), Strictly Rhythm's own 30th-anniversary retrospective, or similar primary/authoritative sourcing — not just personal judgment.
- **⚠️ Critical gotcha already found: the "Jersey Sound Top 100" fan list is reliable for *what matters*, not for *what year*.** Three entries sourced primarily from its dates turned out wrong when checked against real Discogs pressings (Intense "Let The Rain Come Down": list said 1989, actually Feb 1990; Phase II "Reachin'": list said 1989, actually Jan 1988). Treat every date from that list as needing independent confirmation — this is probably the single highest-value thing this script can do.
- **When a track has multiple mixes/versions, prefer the most "Jersey Sound" one** (extended mix, the mix actually associated with Zanzibar/Humphries) — but don't discard the truly representative track to chase a rarer mix. If a specific edit is meaningfully more "Jersey Sound" than the original and it doesn't collide with a stronger entry already at that year, its year can be used instead of the original composition year (this happened with First Choice — ultimately reverted to original year because the edit's year collided with something stronger; the logic is documented inline in the doc where it applies).
- **BPM and Camelot key are deliberately excluded** — Dean chose "skip entirely, core Discogs fields only" earlier. Don't add them back in.
- **⚠️ Second critical gotcha: there are (at least) two people named "Tony Humphries" active in music, and they get conflated by streaming platforms.** The Zanzibar/Kiss-FM DJ (b. 1957, Brooklyn) is who this whole document is about. `youtube.com/@tonyhumphriesmusicyt` is a *different*, unrelated hip-hop/rap artist — confirmed via that channel's own listed keywords ("hip hop, rap, Tony Humphries, Hiphopshippy"). Any "Tony Humphries" release from 2020 onward should be checked against his own official site (tonyhumphries.com/discography) or against context that's unambiguously Zanzibar/Kiss-FM/garage-house before being trusted.
- **Jersey Club (the 2000s-onward Newark genre, Brick Bandits/DJ Tameil, ~130-140bpm) is explicitly excluded** — related lore, different genre, no Humphries connection. Don't let it back in.
- Each Discogs link should point to a page that actually contains the named track — a search-query URL or a wrong compilation (this happened once: a constructed search link surfaced a 2023 repress instead of the real 2020 original, and the 2020 original turned out not to have any Discogs listing at all) is exactly the failure mode this whole exercise exists to catch.

## Priority order (highest-risk entries first)

1. **Every entry whose date rationale leans on the Top 100 list alone**, not yet independently checked: Sybil (1986), Jomanda both entries (1988, 1991), Kimara Lovelace (1998), Underground Ministries (1999), Kenny Bobien (1997). Check these first — same failure mode already found three times.
2. **All remaining 🔎 (generic search link) entries** — roughly 30-35 of them — need narrowing to a specific verified release ID.
3. **The one known unsolved gap**: 2020 (Demuir "Lusting U feat. Bluey Robinson") — extensive manual searching found the song is real (Kaoz Theory KT018, May 2020, confirmed on Beatport/Traxsource/Spotify/Apple/Amazon) but *no* Discogs listing for that specific release could be found — only a 2023 repress with a different tracklist context. Worth a proper API search in case manual search simply missed it; if the API also finds nothing, this needs a replacement track for 2020.
4. **Still-genuinely-open years** with no pick at all yet: 2002, 2006, 2010 need track-level narrowing (compilation vs. track issue); 2013, 2016, 2019, 2021 have no pick at all.

## Central/anchor facts that shouldn't change

- Central track (the one answering "what track best defines the Jersey Sound"): **Kerri Chandler – "Atmosphere E.P. Vol. 1," track "Climax 1"** (1993, Shelter Records, SHL-1004). This was a deliberate choice, confirmed with the user — don't let a script "improve" this pick, only verify/strengthen its citation.
- Runner-up to the central track, kept in as podium silver rather than dropped: Hardrive "Deep Inside" (1993, Strictly Rhythm).
