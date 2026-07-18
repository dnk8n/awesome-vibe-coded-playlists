# Workflow notes — recipes, pitfalls, worked details

Field notes from real runs of this workflow (first big run: a 122-row, 40-year
genre canon with identity constraints). Read before the first Discogs call on a
sizeable job; skim the section headers on small ones.

## Contents
1. Discogs API mechanics
2. Curation strategy
3. Credit-exactness traps
4. Structured data → generated table
5. YouTube matching in detail
6. Quota economics table
7. Playlist creation & OAuth
8. Honesty patterns that users valued

---

## 1. Discogs API mechanics

- **Auth is required for `/database/search`** — an unauthenticated helper will
  simply not work for search. Token also raises rate limit 25 → 60 req/min.
- Pace at ~1.3 s/request (≈46/min) and back off exponentially on 429/5xx. A
  120-pick job costs roughly 300–700 calls (leads + release fetches) ≈ 10–15
  min of API time; run long batches with `nohup ... &` and poll the log.
- `type=master` search results return **master ids**, not release ids. Fetch
  `/masters/{id}` → `main_release` to get the (usually earliest) release.
- Release JSON fields that matter: `artists[]` (with `anv` and `join`),
  `released` (full date only for digital era), `tracklist[]` (per-track
  `artists[]` on splits/comps), `labels[]` (`name`, `catno`), `videos[]`
  (`uri`, `title`, `duration`), `styles[]`, `uri` (canonical page URL).
- Community style tags are evidence, not gospel: a release tagged "Acid" by
  the community supports a genre claim; absence of the tag doesn't refute it.

## 2. Curation strategy

- **Knowledge-first, Discogs-second.** Draft each slot from what you know, then
  verify. Discogs search is for verification and *discovery in thin spots*, not
  for primary curation — search ranking is not a notability ranking.
- **Style/year scans** (`scan style="X" year=YYYY`) surface real releases for
  thin years. Expect noise; filter hard against the brief's constraints.
- **Prolific artists and labels carry hard stretches.** In any multi-decade
  canon a handful of names fill the gaps; scan their discographies
  (`search artist=`, `scan label=`) before declaring a year empty.
- **Chase original pressings.** Search often surfaces reissues/remix 12"s
  first. Compare years, prefer the original unless the reissue is the story
  (archival unearthing, anniversary remaster) — then say so in Notes.
- **Identity constraints need real verification.** If the brief constrains who
  made the track (nationality, race, gender...), verify via web search — bios,
  interviews, label pages. A name is not evidence. If unverifiable, either
  swap the pick or keep it with an explicit caveat in Notes. Also verify
  *group membership* (duos with one qualifying member: state which member).
- **Aliases are gold.** One artist under five names can legitimately cover five
  slots — note the shared identity so the user sees the concentration.
- **Web-check notability claims** (chart positions, "first ever") before
  putting them in Notes. One wrong #1 claim poisons trust in the whole table.
- **Bandcamp-only releases** have no Discogs anchor. Note them in a research
  queue rather than the table — BUT a mix/compilation page that credits the
  artist and carries the track's video can serve as the anchor if the Notes
  say exactly what's going on (this pattern satisfied a real user).

## 3. Credit-exactness traps

- **Search results flatten join phrases.** "Armando Presents Robert Armani"
  comes back from search as separate artists; naive joining with "&" misquotes
  the page. The bundled `discogs.py release` reconstructs joins — always take
  credits from a release fetch.
- **`anv`** (artist name variation) is the name as printed on the record —
  prefer it over the canonical `name`.
- **Strip `(N)` disambiguators** ("Traxx (4)" → "Traxx") — pages display
  without them.
- **Splits & compilations:** the release-level artist may be "Various" or a
  combined credit; the *track-level* artist is what belongs in the table row.
  On one real run, an archival compilation carried a track credited to a
  legendary dead DJ — a far better row than the compiler's name.
- **Remix credits can violate constraints.** A release by a qualifying artist
  can consist of remixes by non-qualifying ones. When choosing the cut, choose
  a mix whose remixer also satisfies the brief, or the original.
- **Copy track titles verbatim**, including mix parentheticals and even typos.
  The table's claim is "exactly as credited on this page".

## 4. Structured data → generated table

Keep three small JSON files and a generator script (in the scratchpad):

- `results.json` — one record per pick: id, year, released, credited artist,
  chosen track, label+catno, url, bonus flags, notes text.
- `overrides.json` — `{release_id: exact_track_title}` for corrections after
  eyeballing tracklists (hint-matching picks wrong mixes surprisingly often —
  e.g. a hint of "Acid Over" matches "(Piano Mix)" first).
- `yt_final.json` — per pick: chosen video id/title, match type
  (exact/close/alternate/search/skipped), and a ready-made ▶ note.

Regenerate the markdown from these on every change. Hand-editing a 100+ row
table drifts within two edits. Sort key: `released` (normalize `-00` suffixes
away), falling back to year.

Table columns (the contract users expect):
`| Release Date | Artist | Track | Link | YouTube | Notes | Status/Progress |`
Link text = label + catalog number (strip label `(N)` disambiguators and a
literal "none" catno). YouTube cell = `[▶ Watch](https://youtu.be/ID)` or `—`.

### 4a. The `discogs-playlist/v1` items schema

`playlist_items.json` is not just feed for playlist creation — it is the
machine-readable form of the whole table, kept rich on purpose so future
scripts (re-validation, syncing, stats, alternate exports) never need to
re-parse markdown. User feedback explicitly asked for this richness.

```json
{
  "schema": "discogs-playlist/v1",
  "playlist": {
    "title": "ACID — A Black-Heritage Canon (1986–2026)",
    "description": "Three notable acid tracks per year ...",
    "privacy": "private"
  },
  "source_of_truth": "discogs.com release pages (videos[]); deviations noted per item",
  "order": "chronological by Discogs release date; year-only dates sort by year",
  "generated_at": "2026-07-17",
  "validation": {
    "method": "YouTube Data API v3 videos.list (status)",
    "validated_at": "2026-07-17",
    "result": "117/117 public"
  },
  "items": [
    {
      "position": 1,
      "video_id": "TxGXehOPe0I",
      "youtube_url": "https://www.youtube.com/watch?v=TxGXehOPe0I",
      "label": "1986 · Sleezy D. – I've Lost Control",
      "artist": "Sleezy D.",
      "track": "I've Lost Control",
      "release": "I've Lost Control",
      "release_label": "Trax Records TX113",
      "released": "1986",
      "year": 1986,
      "discogs_release_id": 2237,
      "discogs_url": "https://www.discogs.com/release/2237-Sleezy-D-Ive-Lost-Control",
      "video_title": "Sleezy D - I've Lost Control (House Side)",
      "match": "exact",
      "video_status": "public",
      "duration_seconds": 748,
      "rating": 5,
      "rating_notes": ""
    }
  ]
}
```

Field rules:
- **Required per item:** `video_id`. Everything else is recommended — populate
  what verification actually established, omit what it didn't (no guessed
  values).
- `rating` (1–5) is the maintenance hook: 5 = exact page cut · 4 = search-found
  exact cut or page video with different mix · 3 = alternate track · 1 = no
  usable video · −1 star when the exact cut only exists as a >15-min rip
  (never select those — they're multi-track). Hand-edited ratings survive
  rescrapes unless the video itself changes; `rating_notes` says why a rating
  isn't 5. `previous_video_id` keeps an audit trail across replacements.
- `duration_seconds` comes from the YouTube API (Discogs durations are often
  0) and enforces the 15-minute rule.
- `label` is the human one-liner used in playlist-creation logs; if omitted,
  consumers derive `artist – track`.
- `match` uses the ladder vocabulary: `exact | close | alternate | search |
  skipped` (skipped items may appear with no `video_id` in the table but are
  left OUT of this file, since it feeds the playlist).
- `release_label` is the label + catalog number as displayed on the doc's link
  text (free-form string; don't fragile-split it).
- Consumers must stay tolerant: the bundled `create_playlist.py` and
  `yt_verify.py` also accept bare id lists and legacy key spellings
  (`videoId`, `id`, `url`), but always *write* the v1 schema.

## 5. YouTube matching in detail

**Why page videos first:** the `videos[]` on a release page were attached by
collectors of that exact record — a far higher-precision source than YouTube
search, which returns covers, re-records, unrelated same-title tracks, and
full-album rips.

**Matching ladder** (note everything below rung 1 in the table):
1. exact cut (mix name included) among page videos
2. base-title match (mix absent/differs — only if mix identity is harmless)
3. another track from the same release that does have a page video
4. verified search-found upload of the exact cut (page link dead/missing)
5. skip, with the reason and any search-found lead in Notes

**Fuzzy matching that works:** lowercase; strip punctuation *inside* words
("K.M.T." → "kmt", "Let'n" → "letn"); token-set containment; treat
mix/remix/original/version/edit as stopwords for rung-2 *only after* rung-1
failed with them included. Real failures caught this way: "Cudlees" vs
"Culdees" (uploader typo — matched by hand), "Black Hands" vs "Black Hand"
(plural drift), "Jacqueline" vs "Jaqueline" (the *Discogs tracklist* had the
typo). When tokens fail, eyeball the page's video list before declaring rung 3.

**Traps:**
- Stopword-stripping makes every "(X Remix)" match the original's tokens —
  which silently swaps in a different artist's version. After a rung-1 failure,
  *choose* the substitute mix deliberately, checking the remixer against the
  brief.
- Videos with `duration: 0` are often full-EP/album streams — usable, but note
  "full-EP stream (includes the cut)".
- **Expect dead embeds.** ~4% of page videos were dead/private in a real run.
  Validate everything with `yt_verify.py`; on failure walk back up the ladder.
- If open YouTube search is needed (rung 4), scrape the public results page
  (`youtube.com/results?search_query=...`, parse `ytInitialData`, consent
  cookie `SOCS=CAI`) — **never** `search.list` (see quota). Score candidates:
  prefer "- Topic" channels (official audio), sane durations (90 s–20 min),
  penalize "full album", "live", "boiler room", "cover", "remake".

## 6. Quota economics (YouTube Data API v3, default 10,000 units/day)

| Operation             | Cost | Implication                                    |
|-----------------------|------|------------------------------------------------|
| `search.list`         | 100  | ~100/day max — never use for bulk matching     |
| `videos.list` (≤50 id)| 1    | validate a whole playlist for ~3 units         |
| `playlists.insert`    | 50   | one-off                                        |
| `playlistItems.insert`| 50   | 120 tracks ≈ 6,000 units — most of a day       |

Budget rule: keep read-side usage near zero (scrape search, batch validate) so
the write-side (playlist creation) fits in the same day. If inserts hit quota
mid-run anyway, the bundled script saves progress and resumes next day.

## 7. Playlist creation & OAuth

- API keys authenticate *requests*, OAuth authenticates *a user* — playlist
  creation needs the latter. No way around the user doing a consent step.
- Offer both: OAuth Playground access token (zero setup, ~1 h validity,
  fine for a single run) or a Desktop-app OAuth client (reusable; loopback
  redirect on localhost — works because Claude Code runs on the user's
  machine). The bundled `create_playlist.py` implements both.
- Create **private** by default; the user flips visibility.
- No-auth fallback: `youtube.com/watch_videos?video_ids=ID1,...` (≤50 ids per
  URL) gives instant anonymous playlists — offer when OAuth is friction.
- Token hygiene: keys/tokens pasted into chat should be rotated after the
  project; keep them in scratchpad dot-files, never in project files or git.

### 7a. Making the Discogs contributions (browser only — the API cannot)

Verified empirically: `POST /releases/{id}/videos` → 404, `PUT /releases/{id}` →
405. A personal access token authorizes reads + collection/marketplace, never
database edits. Contributions go through the website with a logged-in session
(the user logs in themselves — never handle credentials):

- Go straight to `discogs.com/release/{id}/videos/update` ("Manage Videos").
- Paste a **YouTube URL into the search box** — it resolves to exactly that
  video; click Add, then Save Changes. Edits apply instantly (no review queue).
- The page's related/search results often surface **official "- Topic"
  uploads** of the exact release — frequently better than the video you came
  to add; prefer them, and consider healing the whole release (all tracks)
  while you're there.
- **Removal discipline:** only remove videos with GREY/broken thumbnails
  (truly deleted). A live thumbnail may be an *unlisted* video that still
  plays embedded — removing it harms the page. And dead-flags rot fast:
  in one real run, two pages self-healed within a day (distributor
  re-uploads; temporarily-private videos returning). Re-verify liveness the
  same day you act.
- **Discogs API caches release JSON for hours** — a rescrape right after
  contributing may not see the new videos. Re-run the next day; the
  provenance-upgrade rule in `maintain_playlist.py` then lifts ratings even
  when the video id didn't change (your search-found id may turn out to BE
  the page's video).
- Spelling-variant drift defeats token matching ("So Let It Be **Houze!**"
  vs tracklist "...House") — those need an eyeball pass and a manual set.

### 7b. The maintenance loop (report → contribute → rescrape → sync)

Discogs pages improve over time (and rot: ~4% dead embeds per run). The loop:

1. `maintain_playlist.py report` — per problem slot prints the failure class
   (EMPTY page / OUTDATED dead embeds / MISSING exact cut / ONLY LONG RIP) and
   a recommendation: usually "contribute our verified upload to the page"
   (search-found exact cuts are exactly what the page is missing) or "search
   manually, then add it to Discogs". The user makes the edits on Discogs —
   the workflow feeding the community that feeds it.
2. Wait for contributions to land (theirs or others').
3. `maintain_playlist.py rescrape` — re-runs the ladder for items rated <5;
   a page that gained the exact cut upgrades the item to 5 and swaps the
   video in (old id preserved as `previous_video_id`).
4. `create_playlist.py --prune` — idempotent live-playlist sync: inserts new
   ids at the right chronological position, removes replaced ones. A no-op
   sync costs ~5 quota units, so it's safe to run routinely.
   (`create_playlist.py --rescrape --prune` does steps 3+4 together.)

## 8. Honesty patterns that users valued

- Open slots stated as open ("🔎 Open — leading candidates: ...") rather than
  padded with weak picks.
- Every deviation visible in the row itself: alternate cut used, video not
  from the page, reissue standing in for an original, definition stretches
  ("acid-adjacent — the notes say so").
- An **alternates bench** of verified near-misses: users swap picks, and a
  bench swap costs seconds instead of a re-research.
- A **research queue**: ear-checks pending, Bandcamp-only leads, the current
  year marked in-progress.
- Method note in the doc footer (what was verified, how, when) — it makes the
  table auditable long after the session.
