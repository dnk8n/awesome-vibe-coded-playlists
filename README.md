# 🎶 awesome-vibe-coded-playlists

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Playlists](https://img.shields.io/badge/playlists-6-8A2BE2)
![Tracks](https://img.shields.io/badge/tracks-497-brightgreen)
![Source of truth](https://img.shields.io/badge/source%20of%20truth-Discogs-333)
![Contributions](https://img.shields.io/badge/contributions-welcome-ff69b4)

Research-grade music playlists, built by handing an AI agent a **brief** and letting it use
**[Discogs](https://www.discogs.com)** as the source of truth — real, human-created releases,
community-verified credits, a hard link for every claim — then wiring the result into a living
**YouTube playlist** that maintains itself.

> **No hallucinated tracklists. Every row survives being clicked.** 👆

Start a brief of your own, argue a pick, or heal a Discogs page — see **[Contributing](#-contributing)**.

## 📑 Table of contents

- [How it works](#-how-it-works)
- [The playlists](#-the-playlists)
- [The skill](#-the-skill)
- [Contributing](#-contributing)
- [Why "vibe-coded"?](#-why-vibe-coded)
- [License](#-license)

## ⚙️ How it works

Each playlist lives in its own folder under [`playlists/`](playlists/) and holds three things:

| File | What it is |
|---|---|
| `*.md` | the human-readable table — release-date sorted, artist & track **exactly as credited on Discogs**, hard links, per-row notes, a ★ confidence rating |
| `playlist_items.json` | the machine-readable items file (`discogs-playlist/v1` schema) — the full research trail plus per-track ratings |
| `research/` | the verified datasets, curator overrides and config that **regenerate** the table |

The tables are never hand-edited — they're rebuilt from verified data by the [skill](#-the-skill).
When the underlying records change on Discogs or YouTube, a re-run picks it up.

## 🎧 The playlists

Six canons so far, **497 tracks**, every one anchored to a Discogs release page and playable on YouTube:

| | Playlist | Era | Tracks | Listen | Table |
|---|---|---|--:|---|---|
| 🧪 | **ACID — A Black-Heritage Canon** | 1986–2026 | 122 | [▶ YouTube](https://www.youtube.com/playlist?list=PLNXi-Q1Sb-_E) | [📄 Doc](playlists/acid/acid-playlist.md) |
| 🏙️ | **Jersey Sound** | 1960–2026 | 199 | [▶ YouTube](https://www.youtube.com/playlist?list=PLWrSMxL0SS2E) | [📄 Doc](playlists/jersey-sound/jersey-sound.md) |
| 💯 | **Jersey Sound — FIDA/ThinkSoul Top 100** | ranked canon | 100 | [▶ YouTube](https://www.youtube.com/playlist?list=PLVkmY-N1Myts) | [📄 Doc](playlists/jersey-sound-top-100/jersey-sound-top-100.md) |
| 🌴 | **Underground Jungle — Deep Cuts** | 1993–1996 | 30 | [▶ YouTube](https://www.youtube.com/playlist?list=PLUp3bmcY-TEQ) | [📄 Doc](playlists/underground-jungle/underground-jungle.md) |
| ⏪ | **Remix Rave — The Originals** | 1983–1999 | 14 | [▶ YouTube](https://www.youtube.com/playlist?list=PLPiwGxvXa6To) | [📄 Doc](playlists/remix-rave-originals/remix-rave-originals.md) |
| 🔄 | **Remix Rave — House, Garage & Acid Reworks** | 2017–2026 | 32 | [▶ YouTube](https://www.youtube.com/playlist?list=PLLBKBwzTyT9Q) | [📄 Doc](playlists/remix-rave/remix-rave.md) |

### 🧪 ACID — A Black-Heritage Canon (1986–2026)

> *"3 notable acid tracks per year from the year acid was incepted — every track produced or with
> core involvement by a Black artist. Bonus points outside UK/Europe/USA; bonus points if non-male.
> Hard links to Discogs, exactly as credited."*

122 tracks, from Sleezy D's *I've Lost Control* (Trax, 1986) to the current year. Identity claims are
verified via sources rather than names; a reconciliation against a third-party tool's attempt at the
same list separated its 6 genuine finds from 36 wrong-version false positives; and Discogs itself was
improved along the way — pages fixed and verified videos contributed, which the maintenance loop feeds
back in.
&nbsp;&nbsp;🔧 [Items file](playlists/acid/playlist_items.json)

### 🏙️ Jersey Sound (1960–2026)

> *A 67-year lineage of the "Jersey Sound" — Club Zanzibar, Newark, Tony Humphries — traced back
> through its soul/gospel/disco roots and forward to today.*

199 picks across all 67 years, 177 with live release-page videos, centred on **Tony Humphries**
himself. Built **twice, independently** — once by hand-guided web research, once with the skill — then
reconciled: ~45 picks landed identically, wrong fan-list dates were caught twice over, and every pick
that didn't make the final cut sits on a bench **with a written reason**. The
[provenance & full-accounting sections](playlists/jersey-sound/jersey-sound.md#provenance--this-canon-was-built-twice)
tell that story; nothing disappeared silently.
&nbsp;&nbsp;🔧 [Items file](playlists/jersey-sound/playlist_items.json)

### 💯 The Jersey Sound — FIDA/ThinkSoul Top 100 (30 Years Later)

A faithful, Discogs-verified rebuild of **the community's own canon** — the FIDA/ThinkSoul Committee's
2019 "Top 100 Tunes (30 Years Later)", reproduced **exactly as ranked**. This is the scene's reckoning,
not a re-curation: every entry re-verified for its exact credit, title, label and pressing.

### 🌴 Underground Jungle — 30 Deep Cuts (1993–1996)

Thirty **lesser-known jungle** records from the golden era, sequenced for a **live DJ set** — rollers,
ragga cuts and darkside choppers that ran on Kool FM but never crossed over. The greatest-hits anthems
are excluded *on purpose*; this is the deep box.

### 🔄 Remix Rave — a matched pair

Two playlists that share the same fourteen numbers, so you can hear a record and what house culture
later did to it:

- **[Remix Rave — The Originals](playlists/remix-rave-originals/remix-rave-originals.md)** — 14 pre-2000 sources, New Order (1983) → Fatboy Slim (1999).
- **[Remix Rave — House, Garage & Acid Reworks](playlists/remix-rave/remix-rave.md)** — up to three 2017-or-later reworks of each, in the house / UK-garage / acid / deep-house family. The [coverage section](playlists/remix-rave/remix-rave.md#coverage--where-the-genre-limit-bites) is honest about where the genre limit leaves a gap.

## 🧩 The skill

[`skill/discogs-playlist/`](skill/discogs-playlist/) packages the whole workflow for
[Claude Code](https://claude.com/claude-code) (or any agent harness that reads `SKILL.md`-style
instructions). The four stages:

1. **Curate & verify** — knowledge-first curation, then every pick verified against the Discogs API:
   exact credited artist (join phrases like *Presents* / *Featuring* reconstructed), exact track title,
   release date, original pressing. Honest statuses — open slots beat padded rows.
2. **YouTube matching** — links come from each release page's own community-curated `videos[]`, walked
   down a ladder (exact cut → mix-variant → alternate track → verified search find → honest skip),
   validated live, with a >15-minute rule that keeps full-album rips out.
3. **Playlist creation** — an idempotent OAuth script diffs your items file against the live playlist
   and applies only the deltas.
4. **Maintenance & giving back** — every item carries a 1–5 rating; a report mode surfaces exactly what
   a human can contribute *back* to Discogs. Contribute → rescrape → sync, and the playlist heals
   itself.

<details>
<summary>🛠️ Install & run</summary>

<br>

**Install (Claude Code):** copy `skill/discogs-playlist/` into `~/.claude/skills/`, then give Claude a
playlist brief. You'll need a free
[Discogs personal access token](https://www.discogs.com/settings/developers) (required — search is
auth-only) and a [YouTube Data API key](https://console.cloud.google.com/apis) (cheap validation;
~1 quota unit per 50 videos). Playlist creation additionally needs a one-time OAuth consent — the
script walks you through it.

The scripts are **stdlib-only Python** and also work standalone:

| Script | Does |
|---|---|
| `discogs.py` | rate-limited Discogs API helper (search, release, fuzzy `find`) |
| `yt_verify.py` | bulk video validation |
| `create_playlist.py` | idempotent YouTube playlist sync (OAuth) |
| `maintain_playlist.py` | gaps report + rescrape |

Read [`references/workflow-notes.md`](skill/discogs-playlist/references/workflow-notes.md) for the
field-tested pitfalls — quota economics, credit traps, dead-embed triage, Discogs contribution
etiquette.

</details>

## 🤝 Contributing

This repo is meant to be argued with. The briefs are subjective, the canons are opinionated, and the
gaps are documented on purpose — all of that is an invitation. A few ways in:

| You want to… | How |
|---|---|
| 🎛️ **Pitch a playlist** | Open an [issue](https://github.com/dnk8n/awesome-vibe-coded-playlists/issues) with your brief — a vibe, an era, a scene, a constraint. The more specific, the better it verifies. |
| 🧠 **Argue a pick** | Benched tracks carry a **written reason** (see each doc's accounting sections). Make the case for one to come off the bench, or challenge one that's in. |
| 🩹 **Heal a Discogs page** | The maintenance reports and [`ROADMAP.md`](ROADMAP.md) list exactly what's missing — empty video pages, dead embeds, missing cuts — often with a ready-to-paste upload. Editing Discogs helps *everyone*, not just this repo. |
| 🔗 **Report a dead link** | Videos rot (~4% per pass). Flag one in an issue and it gets re-matched up the ladder. |
| 🛠️ **Improve the skill** | The scripts are small and stdlib-only. Better matching, new selection rules, more graceful edge cases — PRs welcome. |
| 🎯 **Fill an open slot** | Several canons have honest gaps (jungle years, a Cubik-shaped hole in Remix Rave). Bring a candidate with its Discogs link. |

👉 **[`ROADMAP.md`](ROADMAP.md)** tracks what's genuinely unfinished, in plain terms.

Ground rules are light: keep every claim clickable (Discogs link or it didn't happen), and treat a
benched pick as a conversation, not a deletion.

## 💡 Why "vibe-coded"?

Each playlist started as a conversational brief — a *vibe* — and became a verifiable document through
agent + API + community data. The briefs are quoted at the top of each document, and the failures are
part of the artifact too: the reports here record every dead link found, wrong mix dodged, and date
corrected. The [`evals/`](evals/) folder shows how the skill was tested — the same briefs run with and
without it, with API-backed assertions.

## 📄 License

[MIT](LICENSE). Playlist documents describe and link to works owned by their respective artists and
labels; Discogs data belongs to the Discogs community.
