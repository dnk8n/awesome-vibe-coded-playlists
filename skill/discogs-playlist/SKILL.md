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
- **Credential flexibility (matters for maintenance sessions):** the YouTube scripts accept an OAuth access token wherever a key is expected (detected by its `ya29.` prefix, sent as a Bearer header) — so a single OAuth Playground token can drive validation, metadata reads *and* playlist writes for its ~1-hour life. And `maintain_playlist.py` falls back to **anonymous Discogs release reads** (25 req/min) when no Discogs token is present — the maintenance loop stays runnable after the build token is rotated. Only curation-phase *search* strictly needs a Discogs token.
- **Pin down the brief**: theme, era span, picks per year (or total), *hard constraints* (must-hold, e.g. artist identity, genre) vs *bonuses* (nice-to-have, e.g. geography, gender), and where the output file goes. If the brief is ambiguous on something that changes the whole table (e.g. "when does the genre start?"), decide from research and state your definition in the document header rather than blocking.

## Phase 1 — Curate and verify on Discogs

Use `scripts/discogs.py` (rate-limited, backoff built in) for all API access. Run `python3 scripts/discogs.py --help-commands` or read the script header for usage.

**Curate candidates knowledge-first, then fill gaps with Discogs itself:**
- Start from what you know: canonical tracks, key artists, key labels for the brief.
- For thin years/slots, use `scan` with `style=` + `year=` filters (e.g. `scan style="Acid House" year=1990`) to surface real releases you wouldn't have recalled — then filter by the brief's constraints.
- Artist and label discography searches (`search artist="X"`, `scan label="Y"`) are the best gap-fillers: a handful of prolific artists often carry the hard stretches of any canon.
- Use web search for facts Discogs can't tell you: artist identity (if constraints depend on it), notability claims (chart positions, "first ever X"), and which cut on an EP is the celebrated one. Never assert an identity-based constraint (race, gender, nationality) from a name alone — verify, and if you can't, say so in the Notes or pick someone else.

**A search that returns nothing is usually the *search*, not a missing record — sweep hard before calling a slot open.** Discogs' `artist=`+`track=` is brittle (it misses even correctly-spelled records); free-text and title-only searches are what land the match. `scripts/discogs.py find artist= track= [year= label=]` runs the productive angles at once — a spacing-normalised `q=` (`JoAnn`→`Jo Ann`), a text-speak `q=` (`4 Da`→`4 Tha`), and a **`release_title=` title-only** pass — then ranks by title-token overlap plus your year/label hints. The **title-only pass is the workhorse**: because the track title is the most stable field, it surfaces a record even when the scene's **artist attribution is wrong or reshuffled** — a *featured* credit (`Charvoni`→`Nu Phonic Featuring Charvoni`), a different lead entirely (`Ann Robinson` demo → the released `Cookie Watkins`), or a group member — and even under **name misspellings** (`Saybrynaah`→`Sabrynaah`, `Grandpa`→`Grampa`), since the artist string barely counts toward the score. If `find` still comes up empty, retry by hand with the creativity a script lacks: **spelling/phonetic variants** (doubled letters, homophones), the **bare distinctive substring** of the title, or a **Various-artists compilation/EP** — search the comp title or the label, then read its *per-track credits* (`Alex & Rai`'s "4 Da Love Of U" is the track "4 Tha Love Of You" on *Various – Klubhead E.P.*). Only after this does a slot honestly stay open.

**Then verify every pick with a release fetch.** Search results are only leads. The release JSON is the source of truth for:
- **Exact credited artist** — the script reconstructs join phrases ("Presents", "Featuring", "AKA", "Vs"); search results flatten these and you'll misquote credits if you rely on them.
- **Per-track artists** — on splits and compilations the track you pick may be credited to someone else entirely (this matters doubly when constraints ride on identity; also watch remix credits — a "close enough" remix pick can smuggle in an artist who violates the brief).
- **Exact track title** — copy it verbatim, including mix name, even typos.
- **Released date** — used for sorting; full dates only exist for digital-era releases, older ones sort by year.
- Prefer the *original pressing* over reissues/remix-EPs unless the reissue is the point (then say so in Notes).

**Always link the Discogs master release, and let its Tracklist be the final source of truth for the track.** When a release carries a `master_id`, link the **master** (`/master/{id}` / `discogs.com/master/{id}`), never a single pressing — it's the stable, canonical page, and users who want a specific pressing can click **"See all versions"** on the master to dig down themselves. Only link an individual release when the record has **no master at all**. The Track column is a single item copied **character-for-character from that page's Tracklist section**: exact mix/version wording, punctuation, and even typos, verbatim. Choosing *which* tracklist item:
- If the brief/source named a specific version or mix, pick that item **from the master's tracklist**. If that exact version isn't on the master, **stay on the master** and pick the best cut it offers (per the no-version rule below), noting the requested mix wasn't found — do **not** drop to a sub-release to chase the named mix.
- If no version was requested, prefer an **extended/long** version (by title: "Long"/"Extended"), else a **club** version, else the **first A-side** track; a radio/edit is the last resort. Extended/long ranks **above** club (a titled "Long Version" wins even over a longer "Club Mix"). Selection is by the title keyword, not by duration. **Rate the row by how well the cut matches this preference** (5 = a prompt-named mix, or an extended/long/club cut, with an exact page video; drop below 5 when the release only yielded a plain/radio cut or a poorer video, so the slot flags itself for a later hunt). Curators may hand-pin a specific tracklist item or a specific YouTube id per row (an overrides file) — honour those over the automatic pick.
- **Both the artist and the track are taken from Discogs — the chosen tracklist item is the source of truth.** The Artist column is that item's own credit: the **per-track credit** when the tracklist entry carries one (splits/compilations), otherwise the **master/release credit** (reconstructed with its join phrases, character-for-character — including stylised spellings like `JohnnydangerOus` or `C.R.J.`). The source list's artist only *drives the search*; it never overrides what Discogs credits. Any extra track detail goes in the **Notes**.

**Reconcile, never blend: Discogs is the sole source of truth for every column of the table.** Artist, Track, date, Label and link all come from the one chosen master/release; the source list, fan sites and web research only *drive the search* — they never fill a cell. Where sources disagree, the Discogs page wins the cell (a fan-list year yields to the pressing's date; a fan-list credit yields to the credited artist). And a **Note must never contradict its own row's columns** — a Note may add what Discogs lacks (provenance, why a mix was chosen, session/scene history) but must not assert a date, artist, or title the row now shows differently. Notes go stale as picks change: **before finalising, re-read every Note against its row and delete or rewrite any the Discogs data has overtaken.**

**Record the deviations from the source, don't hide them.** Where a cell differs from the list/brief the pick came from — a corrected artist spelling or a different attribution (`JoAnn Jones`→`Jo Ann Jones`, `Ann Robinson`→`Cookie Watkins`), a different title wording (`4 Da Love Of U`→`4 Tha Love Of You`), or a different version than the source *named* — add a short Note stating the source's version (`source credits the artist as "…"`, `source titles it "…"`, `source specifies "…"`). This keeps the reconciliation auditable: the cell is Discogs truth, the Note preserves what the source said. A version the *playlist* chose when the source named none needs no note.

**Track statuses honestly.** Use the Status column: `✅ Verified` (release fetched, credits copied), `✅ Verified · 🎧` (release verified but your choice of cut off an EP/LP deserves an ear-check), `🔎 Open` (slot unfilled — say what the leading candidates are). An honest open slot beats a padded row. Keep an "alternates bench" section of verified near-misses — users swap picks, and a bench swap costs seconds instead of a re-research. Bench entries carry hard links too: the Discogs release link **and** a YouTube link chosen by the same page-video ladder — near-misses stay listenable without being playlist members.

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

**Adoption and the durable record:** users sometimes build the playlist by hand on YouTube from the items file — adopt it with `--playlist-id <ID>` instead of creating a duplicate; a `--dry-run` reporting `add: 0 | stale: 0` is the proof that live and file are identical. Once a live playlist exists (created or adopted), record `playlist_id` and `url` in **`config.json`'s `playlist` block** — that's the durable, committed source of truth. `assemble.py` copies them into the regenerated (gitignored) items file, which is the sync target on later runs (resolution: `--playlist-id` > items-file metadata > local progress file); the `*_progress.json` the script writes is local resume state and belongs in `.gitignore`. On the next `assemble.py`, that `url` also surfaces a **▶ Listen on YouTube** link just under the document's title, so the finished doc points readers straight at the playlist.

## Phase 4 — Maintenance & the community-contribution loop

The playlist is a living object; `scripts/maintain_playlist.py` (copy it next to the items file) drives the loop:

- **`maintain_playlist.py report`** — audits every slot's Discogs page and lists what a human could fix *on Discogs itself*: pages with no videos, dead/non-public embeds, pages missing the exact cut, cuts that only exist as >15-min rips — each with a ready-to-paste recommended video (our verified upload) or "search manually". This is how the workflow gives back to the community that made it possible. The contributions themselves are website-only (the API cannot edit releases) — a logged-in browser session drives `discogs.com/release/{id}/videos/update`; read `references/workflow-notes.md` §7a before doing this (removal discipline, unlisted-vs-deleted, API caching).
- **`maintain_playlist.py rescrape`** — re-matches every item rated <5 (or `--all`) against its Discogs page, picking up newly contributed videos, applying the 15-minute rule, and updating video fields + ratings in the JSON.
- **`create_playlist.py --rescrape --prune`** — rescrape, then sync the live playlist in one command: new/better videos get inserted at the right position, replaced ones removed.

## Output document structure

Header: the brief restated, your working definition of scope/genre boundaries, a legend for any bonus-markers, and one line on method ("every row verified against the Discogs API"). Then the table. Then: **Alternates bench** (verified swaps), **Research queue** (open slots, ear-checks, leads that lack Discogs pages), and any planned next phase. Keep Notes cells short but load-bearing: why the track is notable, plus any YouTube-matching caveat (▶-prefixed).

## The build pipeline — data lives in the playlist, scripts live here

The generation scripts are **generic and live in this skill** (`scripts/`); each playlist keeps
only its **data + config** in its own `research/` dir. Run the scripts *from* that dir (they read
CWD, import their skill siblings). This means improving a script here — a new selection rule, a new
curator override — upgrades **every** playlist and every skill user at once; never fork a script
into a playlist folder.

Per-playlist `research/` holds only:
- `picks.json` — the source list transcribed (rank, artist/track as listed, label/year hints).
- `overrides.json` — `{rank: release_id}` hand-resolutions (`0` = force the slot open).
- `curator.json` — hand overrides applied over the automatic pick: `track_pick` (force an exact
  tracklist title), `video_pick` (force a YouTube id), `video_note`, `row_note` (free-form markdown,
  links ok), `rating_override` (hand-set ★ after listening).
- `article.md` — the intro prose + references, with a `<!-- INSERT_TABLE_HERE -->` marker.
- `config.json` — `output_md` filename, `playlist` metadata (title/description/privacy **and the
  durable `playlist_id`/`url`** once the YouTube playlist exists), optional `reuse_from`.

Everything else the scripts write is a **regenerated build artifact, not source of truth** —
`verified.json`, `enriched.json`, `video_fixes.json`, the `*_cache.json` Discogs caches, and
`../playlist_items.json` + `*_progress.json`. **Gitignore all of these** (see the playlist's
`.gitignore`); commit only the source above plus the deliverable `.md`. Discogs and YouTube are the
live source of truth, fetched just-in-time; the caches are only a local speedup — **delete one to
force a fresh fetch**. Because the same datum (a video id, a credit) otherwise lands in five files,
**never hand-edit the generated `.md` / items / `enriched.json`** — a stray edit there goes stale the
moment anything regenerates. Change the *source* instead: a video → `curator.json` `video_pick`; a
cut → `track_pick`; a rating → `rating_override`; a pressing → `overrides.json` — then rebuild. The
durable YouTube `playlist_id`/`url` live in `config.json`, so the items file stays disposable.

Flow (run from `research/`): `verify.py` (picks→`verified.json`, resolving ids via overrides/seed/
reuse/search) → `enrich.py` (master preference + tracklist pick + artist + rating + deviation notes
→ `enriched.json`) → `audit.py` (an **independent** self-check — master-link invariant, wrong-song,
missed club/extended cuts, dead videos; prints a summary and exits non-zero on any issue) →
`assemble.py` (splices `article.md` + table → the public `.md` and `playlist_items.json`, and once
a YouTube playlist URL is on file, links it as **▶ Listen on YouTube** just under the doc's title) →
`fix_dead.py <yt-token>` (swaps dead embeds) → `create_playlist.py`. When picks resist resolution,
`leads.py` batch-fuzzy-searches every still-open slot (and `discogs.py find artist= track=` does a
single one) — use these before ever calling a slot "not on Discogs".

## Ground rules

- Never fabricate a row. If Discogs doesn't have it, it goes in the research queue (Bandcamp-only releases are real but un-anchorable — note them; a mix/compilation page sometimes carries the video and can serve as the anchor if you say so explicitly).
- Report deviations, don't bury them: alternate cuts, non-page videos, reissues standing in for originals — all get a visible Note.
- Generate the table with a script from structured data (picks + fetched credits), not by hand — 100+ hand-written rows will drift. Keep the data (`results.json`-style) so later edits regenerate cleanly. When the document mixes a generated table with hand-written analysis, regenerate everything above a `<!-- hand-curated -->` marker and have the generator preserve what's below it.
- When a canon is rebuilt or revised, picks that drop out get benched **with a written reason** (and their links) — explicit treatment, not silent disappearance. Curators care about their original picks; a reasoned bench also invites picks to argue their way back in.

For detailed recipes, pitfalls, and worked examples (credit reconstruction, split-release handling, scan strategies, dead-video triage, quota math), read `references/workflow-notes.md` — do this before your first Discogs call on a big job.
