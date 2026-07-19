# awesome-vibe-coded-playlists

Research-grade music playlists, built by giving an AI agent a **brief** and letting it use
**[Discogs](https://www.discogs.com)** as the source of truth — real, human-created releases,
community-verified credits, hard links for every claim — then wiring the result into a living
**YouTube playlist** that maintains itself.

No hallucinated tracklists. Every row survives being clicked.

## What's in here

```
skill/discogs-playlist/     the reusable agent skill (workflow + scripts)
playlists/acid/             example: built WITH the skill (co-evolved with it)
playlists/jersey-sound/     example: built BEFORE the skill, then re-run through it
evals/                      how the skill was tested: 2 briefs x with/without skill,
                            API-backed assertions, benchmark + analyst notes
```

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
rating docked per the rules; 12 Discogs pages improved as contributions along the way;
and a reconciliation against a third-party tool's attempt at the same playlist
([the report](playlists/acid/tunemyplaylist-reconciliation.md) separates its 6 genuine
finds from its 36 wrong-version false positives).

📄 [The table](playlists/acid/acid-playlist.md) ·
🎵 [The playlist](https://www.youtube.com/playlist?list=PLNXi-Q1Sb-_E) ·
🔧 [Machine-readable items](playlists/acid/playlist_items.json) (the `discogs-playlist/v1`
schema: full research trail + per-track ratings)

### Jersey Sound (1960–2026)

> *A 67-year lineage of the "Jersey Sound" — Club Zanzibar, Newark, Tony Humphries — traced
> back through its soul/gospel/disco roots and forward to today.*

This one exists in two generations: the **pre-skill** versions
([draft v1](playlists/jersey-sound/jersey-sound-setlist-DRAFT-v1.md),
[v2](playlists/jersey-sound/jersey-sound-setlist-v2.md), plus the
[hand-written verification brief](playlists/jersey-sound/CLAUDE_CODE_HANDOFF.md) whose
hard-won gotchas — unreliable fan-list dates, two different artists named Tony Humphries —
foreshadow half the skill's rules), and the **skill-built v3**: 199 picks across all 67
years (3 per year, two honest open slots), 177 with live release-page videos, plus a
[deviation analysis](playlists/jersey-sound/deviation-analysis.md) comparing the two
generations — ~45 identical picks chosen independently, date corrections cross-validated,
22 authority-attested v2 picks adopted, and the NJ-native proto layer + 2020s depth that
only the skill run surfaced.

📄 [The v3 table](playlists/jersey-sound/jersey-sound-v3.md) ·
🔧 [Machine-readable items](playlists/jersey-sound/playlist_items.json)

## Why "vibe-coded"?

Each playlist started as a conversational brief — a vibe — and became a verifiable
document through agent + API + community data. The prompts are part of the artifact
(see [playlists/acid/playlist-report-prompt.md](playlists/acid/playlist-report-prompt.md)
for one mid-project prompt, verbatim). The failures are part of it too: the reports in
this repo document every dead link found, wrong mix dodged, and date corrected.

## License

[MIT](LICENSE). Playlist documents describe and link to works owned by their respective
artists and labels; Discogs data belongs to the Discogs community.
