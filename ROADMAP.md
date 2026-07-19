# Open items

What's genuinely unfinished, in plain terms. Contributions and arguments welcome.

## Jersey Sound

- **Retire the superseded partial playlists on YouTube.** The
  [live playlist](https://www.youtube.com/playlist?list=PLWrSMxL0SS2E) is now owned by
  the idempotent sync loop (ID recorded in the items file's metadata; live and file
  verified identical). Earlier partial playlists on the channel can be deleted or
  archived — curator's call.
- **Two open slots.** 2008 and 2009 are each one pick short — honest gaps, candidates
  welcome. Related: the document's
  ["One anchor worth revisiting"](playlists/jersey-sound/jersey-sound.md#one-anchor-worth-revisiting)
  note — moving "Hey Hey" to its original 2009 Objektivity pressing fills 2009 and
  re-opens a 2010 seat with named contenders.
- **First maintenance pass.** Ratings exist for all 199 items;
  `maintain_playlist.py report` will surface Discogs contribution opportunities (empty
  pages, dead embeds, missing cuts) the way it did for the acid playlist.
- **Bench arguments.** The
  [full accounting](playlists/jersey-sound/jersey-sound.md#the-original-lineup--a-full-accounting)
  lists every benched pick with its reason. Cases like Jomanda's "Don't You Want My
  Love" (double-attested) and the Michael Watford tribute are open invitations to argue
  a pick back in.

## ACID

- **Phase 2 — before acid.** Trace the lineage backwards from 1985: TB-303 precursors,
  modular squelch, records that sounded acid before the word existed. Seed notes in
  [`playlists/acid/research/ideas-for-pre-acid.md`](playlists/acid/research/ideas-for-pre-acid.md).
- **Chase the remaining sub-5-star slots.** Eleven acid rows still lack an exact
  release-page video (their pages have no short exact cut yet); contributing verified
  uploads to those Discogs pages, then `create_playlist.py --rescrape --prune`, upgrades
  them toward 5/5 and heals the live playlist in place.
