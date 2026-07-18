---
name: discogs-playlist
description: Build a research-grade playlist from a brief or vision, using Discogs as the source of truth for real, human-created, community-verified releases — then optionally create the matching YouTube playlist. Produces a markdown table (release date sorted, artist and track exactly as credited, hard Discogs release links, YouTube links sourced from each release page's embedded videos, notes, per-row status) plus an ordered items file and an OAuth-ready script that creates the actual YouTube playlist. Use this whenever the user gives a playlist brief, theme, or "canon" to research — a genre history, a label or scene retrospective, an N-tracks-per-year selection, tracks meeting identity/geography/era constraints — or mentions Discogs as a source, or wants verified real tracks with hard links, or asks to turn a curated track list into a YouTube playlist. Even a loose "make me a playlist of X, properly researched" should use this skill.
---

# Discogs-verified playlist builder

Turn a playlist brief into three deliverables:

1. **A markdown table** — one row per pick: `Release Date (sorted) | Artist | Track | Link | YouTube | Notes | Status/Progress`, where Artist/Track are copied *exactly as credited* on a specific Discogs release page, and the YouTube link comes from that release page's own embedded videos.
2. **`playlist_items.json`** — the picks in playlist order, validated against the YouTube API.
3. **A created YouTube playlist** on the user's account (OAuth), via the bundled script.

The value of this workflow is *trust*: every row is anchored to a real release page that a human community catalogued, so nothing is hallucinated — and every claim in the table survives being clicked.

## What you need before starting

- **A Discogs personal access token** (required — the `/database/search` endpoint refuses unauthenticated calls, and the token raises the rate limit to 60 req/min). Ask the user for one if not provided ([discogs.com/settings/developers](https://www.discogs.com/settings/developers)).
- **A YouTube Data API key** (needed for Phase 2 validation; cheap — see quota economics below).
- Store both in files in your scratchpad (e.g. `.discogs_token`, `.yt_key`), not in the user's project or in committed files. When the project wraps, remind the user to rotate any token they pasted into chat.
- **Pin down the brief**: theme, era span, picks per year (or total), *hard constraints* (must-hold, e.g. artist identity, genre) vs *bonuses* (nice-to-have, e.g. geography, gender), and where the output file goes. If the brief is ambiguous on something that changes the whole table (e.g. "when does the genre start?"), decide from research and state your definition in the document header rather than blocking.

## Phase 1 — Curate and verify on Discogs

Use `scripts/discogs.py` (rate-limited, backoff built in) for all API access. Run `python3 scripts/discogs.py --help-commands` or read the script header for usage.

**Curate candidates knowledge-first, then fill gaps with Discogs itself:**
- Start from what you know: canonical tracks, key artists, key labels for the brief.
- For thin years/slots, use `scan` with `style=` + `year=` filters (e.g. `scan style="Acid House" year=1990`) to surface real releases you wouldn't have recalled — then filter by the brief's constraints.
- Artist and label discography searches (`search artist="X"`, `scan label="Y"`) are the best gap-fillers: a handful of prolific artists often carry the hard stretches of any canon.
- Use web search for facts Discogs can't tell you: artist identity (if constraints depend on it), notability claims (chart positions, "first ever X"), and which cut on an EP is the celebrated one. Never assert an identity-based constraint (race, gender, nationality) from a name alone — verify, and if you can't, say so in the Notes or pick someone else.

**Then verify every pick with a release fetch.** Search results are only leads. The release JSON is the source of truth for:
- **Exact credited artist** — the script reconstructs join phrases ("Presents", "Featuring", "AKA", "Vs"); search results flatten these and you'll misquote credits if you rely on them.
- **Per-track artists** — on splits and compilations the track you pick may be credited to someone else entirely (this matters doubly when constraints ride on identity; also watch remix credits — a "close enough" remix pick can smuggle in an artist who violates the brief).
- **Exact track title** — copy it verbatim, including mix name, even typos.
- **Released date** — used for sorting; full dates only exist for digital-era releases, older ones sort by year.
- Prefer the *original pressing* over reissues/remix-EPs unless the reissue is the point (then say so in Notes).

**Track statuses honestly.** Use the Status column: `✅ Verified` (release fetched, credits copied), `✅ Verified · 🎧` (release verified but your choice of cut off an EP/LP deserves an ear-check), `🔎 Open` (slot unfilled — say what the leading candidates are). An honest open slot beats a padded row. Keep an "alternates bench" section of verified near-misses — users often swap picks, and this session's users did.

## Phase 2 — YouTube links from the Discogs pages

The `videos[]` array on each release page is community-curated matching — far more trustworthy than open YouTube search. Fetch it with `discogs.py release <id>` (videos are printed with their YouTube ids).

**Matching ladder** (per entry, stop at the first rung that works, and note in the table any rung below the first):
1. **Exact cut** — a page video matches the selected track incl. mix name.
2. **Base title** — same track, mix designation absent/differs. Fine *if* the mix identity doesn't break the brief (don't silently substitute a different remixer).
3. **Alternate track from the same page** — page has videos but not your cut; pick another track from that release and add a Note saying exactly that.
4. **Verified search-found upload of the exact cut** — only when the page's link is dead or missing; Note it as "not from the Discogs page".
5. **Skip** — page has no videos at all; Note it, and include any search-found link in the Note for the user's manual review.

Match titles fuzzily (token overlap, punctuation-insensitive): video titles carry typos ("Cudlees" for "Culdees"), pluralisation drift, and spelling variants — a strict string match loses real matches. But beware the opposite failure: mix names matter, so never treat "(X Remix)" as equal to "(Original)" just because the base tokens match.

**The 15-minute rule:** a video longer than 15 minutes is almost always a full-EP/album rip, not the track. Never select one for the playlist — walk further down the ladder instead — and when the exact cut only exists as a long rip, the entry's quality rating drops one star (see below).

**Rate every entry 1–5 stars** (`rating` in the items file): 5 = exact cut from the page; 4 = same cut but search-found, or a page video with a different mix; 3 = alternate track from the release; 1 = no usable video; −1 if a long rip was the only exact match. The rating is the maintenance hook — anything below 5 is a slot worth revisiting — and the user can overwrite it by hand (e.g. after listening); rescrapes respect hand-set ratings unless the video itself changes.

**Validate every picked video id** with `scripts/yt_verify.py` (batch `videos.list`). Discogs pages routinely carry dead or private embeds; in this workflow's first real run, 5 of 117 page links were dead. Replace dead picks by walking back up the ladder.

**Quota economics (YouTube Data API, 10,000 units/day default)** — this shapes the whole design:
- `search.list` = **100 units** per call → ~100 searches/day maximum. Avoid API search entirely; if you need open YouTube search (ladder rung 4), scrape the public results page instead.
- `videos.list` = **1 unit** per call of up to 50 ids → validation of a whole playlist costs ~3 units.
- `playlistItems.insert` = **50 units** per track → a 120-track playlist ≈ 6,100 units. This only fits in a day *because* search was avoided.

## Phase 3 — Create the YouTube playlist

An API key cannot create playlists — `playlists.insert` requires OAuth user consent. Copy `scripts/create_playlist.py` into the user's project and write `playlist_items.json` in the **`discogs-playlist/v1` schema** (see `references/workflow-notes.md` §4a): playlist metadata (title/description/privacy) plus one item per track carrying the full research trail — video id, label, artist/track as credited, release, Discogs id + URL, match type, validation status — in playlist order, deduped. The rich schema is deliberate: it lets `create_playlist.py` run without CLI args and keeps the file useful for future scripting beyond playlist creation. Then walk the user through **one** of:

- **Quick**: [Google OAuth Playground](https://developers.google.com/oauthplayground) → scope `https://www.googleapis.com/auth/youtube` → authorize → exchange for tokens → user pastes the access token (~1h validity, the run takes minutes): `create_playlist.py --token 'ya29...'`
- **Reusable**: Desktop-app OAuth client in Google Cloud Console → `create_playlist.py --client-id X --client-secret Y` (loopback flow, opens their browser).

The script is **idempotent**: it diffs the items file against the live playlist and only inserts/removes deltas, so re-runs are cheap (~5 units when nothing changed) and interrupted runs just re-run. It creates the playlist **private** by default — let the user opt into public. If the user can't/won't do OAuth, offer anonymous playlist URLs: `https://www.youtube.com/watch_videos?video_ids=ID1,ID2,...` (≤50 ids each) — instant, no login.

## Phase 4 — Maintenance & the community-contribution loop

The playlist is a living object; `scripts/maintain_playlist.py` (copy it next to the items file) drives the loop:

- **`maintain_playlist.py report`** — audits every slot's Discogs page and lists what a human could fix *on Discogs itself*: pages with no videos, dead/non-public embeds, pages missing the exact cut, cuts that only exist as >15-min rips — each with a ready-to-paste recommended video (our verified upload) or "search manually". This is how the workflow gives back to the community that made it possible. The contributions themselves are website-only (the API cannot edit releases) — a logged-in browser session drives `discogs.com/release/{id}/videos/update`; read `references/workflow-notes.md` §7a before doing this (removal discipline, unlisted-vs-deleted, API caching).
- **`maintain_playlist.py rescrape`** — re-matches every item rated <5 (or `--all`) against its Discogs page, picking up newly contributed videos, applying the 15-minute rule, and updating video fields + ratings in the JSON.
- **`create_playlist.py --rescrape --prune`** — rescrape, then sync the live playlist in one command: new/better videos get inserted at the right position, replaced ones removed.

## Output document structure

Header: the brief restated, your working definition of scope/genre boundaries, a legend for any bonus-markers, and one line on method ("every row verified against the Discogs API"). Then the table. Then: **Alternates bench** (verified swaps), **Research queue** (open slots, ear-checks, leads that lack Discogs pages), and any planned next phase. Keep Notes cells short but load-bearing: why the track is notable, plus any YouTube-matching caveat (▶-prefixed).

## Ground rules

- Never fabricate a row. If Discogs doesn't have it, it goes in the research queue (Bandcamp-only releases are real but un-anchorable — note them; a mix/compilation page sometimes carries the video and can serve as the anchor if you say so explicitly).
- Report deviations, don't bury them: alternate cuts, non-page videos, reissues standing in for originals — all get a visible Note.
- Generate the table with a script from structured data (picks + fetched credits), not by hand — 100+ hand-written rows will drift. Keep the data (`results.json`-style) so later edits regenerate cleanly.

For detailed recipes, pitfalls, and worked examples (credit reconstruction, split-release handling, scan strategies, dead-video triage, quota math), read `references/workflow-notes.md` — do this before your first Discogs call on a big job.
