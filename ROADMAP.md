# Roadmap — next session

Working notes for the next work session (and a window into how this repo is built —
each session hands off to the next, the way the original Jersey handoff brief did).

## 1 · Consolidate on the FINAL Jersey Sound playlist

The curator has **manually created the v3 YouTube playlist** from
`playlists/jersey-sound/playlist_items.json`. Next session:

- Get its playlist ID (list playlists via OAuth, or ask), then adopt it with
  `create_playlist.py --playlist-id <ID> --prune --dry-run` → sync so the idempotent
  loop owns it going forward. Record the ID in `playlist_items.json`'s metadata.
- Retire older playlist generations: the 77-item "Jersey Sound (including Proto Jersey)"
  (`PLI93n9RIoHm8`) is superseded — curator decides delete vs archive.
- One document of record: `jersey-sound-v3.md` becomes THE Jersey document; consider
  renaming (drop the "v3").

## 2 · Restructure the repo for final presentation

The curator keeps history copies elsewhere — **lean into the final presentation**:

- Fold/remove superseded files: `jersey-sound-setlist-DRAFT-v1.md`, possibly
  `jersey-sound-setlist-v2.md` (the deviation analysis quotes what matters — but see
  task 3 first: v2 is the source of the original-picks sweep), `CLAUDE_CODE_HANDOFF.md`
  (historic; its lessons now live in the skill's workflow-notes).
- Same lens on acid: `video_gaps_report.json`, `playlist-report-prompt.md`,
  `tunemyplaylist-reconciliation.md` — keep what tells the story, fold the rest.
- `research/` dirs (added this session) hold the regeneration datasets:
  `verified_final.json` + `assemble.py` (jersey), `results.json`/`yt_final.json`/
  `overrides.json` + `gen_md.py` (acid). **Never hand-edit the tables — regenerate.**
  Decide final placement/naming; scripts may need path tweaks after any move.

## 3 · Honor the ORIGINAL Jersey picks — bench-with-reasons sweep

Principle from the curator: tracks that were present from the beginning deserve explicit
treatment, not silent disappearance. **Example: Sam Cooke "Chain Gang" (1960) — v1/v2's
opening pick — is absent from v3** (which chose Shirelles/Drifters/James Cleveland for
1960) with no stated reason.

- Sweep EVERY v1/v2 pick: if in v3 → fine; if not → add to the bench with a
  written "why not" (the deviation analysis §5 covers categories; this sweep is
  per-pick). Known cases: Chain Gang, Mary Wells, Supremes, Four Tops, My Girl,
  Betty Wright, Back Stabbers, Delfonics, George McCrae, Loleatta "Cry To Me",
  Cher "Take Me Home" (Humphries-attested — strongest bench case), Aly-Us-era
  alternates. Some may argue their way back INTO slots.

## Also open

- Jersey 2008 + 2009: one slot short each (honest gaps — candidates welcome).
- Jersey maintenance loop not yet run (ratings exist; `maintain_playlist.py report`
  will surface Discogs contribution gaps like it did for acid).
- Acid Phase 2: the pre-acid lineage (1960s–1985 proto-303/modular; see
  `playlists/acid/ideas-for-pre-acid.md`).
- Curator should rotate the Discogs token + YouTube API key used during the build.
- Push this repo to a public remote.
