# awesome-vibe-coded-playlists

Research-grade music playlists, built by giving an AI agent a **brief** and letting it use
**[Discogs](https://www.discogs.com)** as the source of truth — real, human-created releases,
community-verified credits, hard links for every claim — then wiring the result into a living
**YouTube playlist** that maintains itself.

No hallucinated tracklists. Every row survives being clicked.

## What's in here

```
skill/discogs-playlist/     the reusable agent skill (workflow + scripts)
playlists/acid/             ACID — a Black-heritage canon of acid, 1986–2026
playlists/jersey-sound/     Jersey Sound — a 67-year lineage, 1960–2026
evals/                      how the skill was tested: 2 briefs x with/without skill,
                            API-backed assertions, benchmark + analyst notes
```

Each playlist folder holds the human-readable table (`*.md`), the machine-readable items
file (`playlist_items.json` — the `discogs-playlist/v1` schema: full research trail plus
per-track ratings), and a `research/` directory with the verified datasets, working notes
and scripts that **regenerate** the table. The tables are never hand-edited; they are
rebuilt from verified data.

## The skill

[`skill/discogs-playlist/`](skill/discogs-playlist/) packages the whole workflow for
[Claude Code](https://claude.com/claude-code) (or any agent harness that reads
`SKILL.md`-style instructions):

1. **Curate & verify** — knowledge-first curation, then every pick verified against the
   Discogs API: exact credited artist (join phrases like *Presents*/*Featuring*
   reconstructed), exact track title, release date, original pressing. Honest statuses;
   open slots beat padded rows.
2. **YouTube matching** — video links come from each release page's own community-curated
   `videos[]`, walked down a matching ladder (exact cut → mix-variant → alternate track →
   verified search find → honest skip), validated live, with a >15-minute rule that keeps
   full-album rips out.
3. **Playlist creation** — an idempotent OAuth script diffs your items file against the
   live playlist and applies only deltas.
4. **Maintenance & giving back** — every item carries a 1–5 rating; a report mode surfaces
   exactly what a human can contribute back to Discogs (empty pages, dead embeds, missing
   cuts, ready-to-paste replacement uploads). Contribute → rescrape → sync, and the
   playlist heals itself. The loop has been proven end-to-end: videos we contributed to
   Discogs pages flowed back into the playlist as exact matches within a day.

**Install (Claude Code):** copy `skill/discogs-playlist/` into `~/.claude/skills/`, then
give Claude a playlist brief. You'll need a free
[Discogs personal access token](https://www.discogs.com/settings/developers) (required —
search is auth-only) and a [YouTube Data API key](https://console.cloud.google.com/apis)
(cheap validation; ~1 quota unit per 50 videos). Playlist creation additionally needs a
one-time OAuth consent — the script walks you through it.

The scripts are stdlib-only Python and also work standalone:
`discogs.py` (rate-limited API helper), `yt_verify.py` (bulk video validation),
`create_playlist.py` (idempotent playlist sync), `maintain_playlist.py` (gaps report +
rescrape). Read `references/workflow-notes.md` for the field-tested pitfalls — quota
economics, credit traps, dead-embed triage, Discogs contribution etiquette.

## The playlists

### ACID — A Black-Heritage Canon (1986–2026)

> *"3 notable acid tracks per year from the year acid was incepted — every track produced
> or with core involvement by a Black artist. Bonus points outside UK/Europe/USA; bonus
> points if non-male. Hard links to Discogs, exactly as credited."*

122 tracks, every one anchored to a Discogs release page, from Sleezy D's *I've Lost
Control* (Trax, 1986) to releases from the current year. Highlights of the method:
identity claims verified via sources rather than names; a >15-min EP rip demoted with its
rating docked per the rules; a reconciliation against a third-party tool's attempt at
the same playlist that separated its 6 genuine finds from 36 wrong-version false
positives; and Discogs itself improved along the way — pages fixed and verified videos
contributed, which the maintenance loop then feeds back into the playlist.

📄 [The table](playlists/acid/acid-playlist.md) ·
🎵 [The playlist](https://www.youtube.com/playlist?list=PLNXi-Q1Sb-_E) ·
🔧 [Machine-readable items](playlists/acid/playlist_items.json)

### Jersey Sound (1960–2026)

> *A 67-year lineage of the "Jersey Sound" — Club Zanzibar, Newark, Tony Humphries — traced
> back through its soul/gospel/disco roots and forward to today.*

199 picks across all 67 years (three per year, two honest open slots), 177 with live
release-page videos. The canon centers **Tony Humphries himself** — Zanzibar resident,
KISS-FM Mastermix — with his mix credits threaded from his own 1982 *Master Mix Medley*
to the 2026 archive release cut from his own DAT tapes.

This canon was **built twice, independently** — once by hand-guided web research
against the scene's own authorities, once with the skill — and then reconciled: about 45
picks landed identically (several to the very same pressing), wrong fan-list dates were
caught twice over, 22 picks were adopted on scene-authority attestation, and every
original pick that didn't make the final table sits on a bench **with a written reason**.
The [Provenance and full-accounting sections](playlists/jersey-sound/jersey-sound.md#provenance--this-canon-was-built-twice)
at the end of the document tell that story; nothing disappeared silently.

📄 [The table](playlists/jersey-sound/jersey-sound.md) ·
🎵 [The playlist](https://www.youtube.com/playlist?list=PLWrSMxL0SS2E) ·
🔧 [Machine-readable items](playlists/jersey-sound/playlist_items.json)

## Why "vibe-coded"?

Each playlist started as a conversational brief — a vibe — and became a verifiable
document through agent + API + community data. The briefs are quoted at the top of each
playlist document, and the failures are part of the artifact too: the reports in this
repo document every dead link found, wrong mix dodged, and date corrected.

## License

[MIT](LICENSE). Playlist documents describe and link to works owned by their respective
artists and labels; Discogs data belongs to the Discogs community.
