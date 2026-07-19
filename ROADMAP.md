# Open items

What's genuinely unfinished, in plain terms. Contributions and arguments welcome.

## Jersey Sound

- **Adopt the live YouTube playlist into the sync loop.** The playlist was created
  manually on YouTube from `playlists/jersey-sound/playlist_items.json`. Once its
  playlist ID is recorded in that file's metadata, `create_playlist.py
  --playlist-id <ID> --prune` lets the idempotent sync own it going forward, and older
  partial playlists can be retired.
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
- **Open contribution shortlist.** The
  [reconciliation report](playlists/acid/tunemyplaylist-reconciliation.md) lists videos
  ready to contribute to Discogs pages; each one contributed lets the playlist heal
  itself on the next rescrape + sync.
