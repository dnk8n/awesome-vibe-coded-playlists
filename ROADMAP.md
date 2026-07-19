# Open items

What's genuinely unfinished, in plain terms. Contributions and arguments welcome.

## Jersey Sound

- **First idempotent sync of the live playlist.** The playlist
  ([PLWrSMxL0SS2E](https://www.youtube.com/playlist?list=PLWrSMxL0SS2E), created
  manually from `playlists/jersey-sound/playlist_items.json`; its ID is recorded in
  that file's metadata) still needs one `create_playlist.py --playlist-id PLWrSMxL0SS2E
  --prune` run so the sync loop owns it going forward. Older partial playlists can be
  retired after that.
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
- **Pick up the July 2026 Discogs contributions.** Verified videos were contributed to
  the Discogs pages of the below-5-star slots; `create_playlist.py --rescrape --prune`
  re-matches those items against their pages, upgrades ratings toward 5/5, and updates
  the live playlist in place.
