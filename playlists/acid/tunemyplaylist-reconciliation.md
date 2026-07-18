# TuneMyPlaylist ↔ Canon reconciliation — Discogs contribution worksheet

Compared **TuneMyPlaylist's** playlist (`PLEdjJ-AI_u5M`, 121 entries, built 2026-07-16)
against the **canon** playlist (`PLNXi-Q1Sb-_E`, 117 entries, synced 2026-07-18) and the
5 slots we skipped for lack of Discogs page videos. Every differing TMP video was
validated (live? ≤15 min?) and title-matched against the exact credited track.

**Result: 71 identical · 6 usable finds (below) · 36 false positives ignored · 9 canon tracks TMP lacked.**

---

## 1 · The contribution shortlist (add these videos on Discogs)

Each line: open the Discogs page → "Contribute" → Videos → paste the YouTube URL.
**Verify by ear first** — all are title/duration/liveness-checked, but only ears confirm the cut.

### Gap fills — slots with NO video on the Discogs page (TMP independently confirmed our search finds)

| Slot | Video to contribute | Discogs page |
|---|---|---|
| 2008 · Hieroglyphic Being – Gargle | https://youtu.be/-3K5AFzMt-U (6:18) | [The Bathroom Sessions Select](https://www.discogs.com/release/1456015-Hieroglyphic-Being-The-Bathroom-Sessions-Select) |
| 2009 · Traxx – Violet Epoch | https://youtu.be/bmptHjrmxTQ (7:06) | [Faith](https://www.discogs.com/release/1950846-Traxx-4-Faith) |
| 2024 · AceMo – Save The World | https://youtu.be/TcE_qZoP30I (7:40) | [Save The World](https://www.discogs.com/release/29948197-AceMo-Save-The-World) |
| 2026 · DJ Pierre – Feel The Spirit Moving! | https://youtu.be/cGn_7-CmpFw (6:25) | [Feel The Spirit Moving EP](https://www.discogs.com/release/37423404-DJ-Pierre-Feel-The-Spirit-Moving-EP) |

*(5th skipped slot — Femanyst – Anal Dud, [CLOAKA](https://www.discogs.com/release/25401913-Femanyst-Cloaka-) — TMP had nothing either; a search-found upload exists: https://youtu.be/TNcxMhJfB6A)*

### TMP finds for slots currently rated <5

| Slot (current state) | TMP's video | Discogs page |
|---|---|---|
| 1992 · K-Alexi – Drugtest (4/5, our upload not on page) | https://youtu.be/3zQjXa4kOTU "K-Alexi - Drugtest (1992)" (5:10) — or ours: https://youtu.be/xLKYpcWismk | [3 Men And A Loft](https://www.discogs.com/release/8596-K-Alexi-3-Men-And-A-Loft) |
| 2026 · Mike Dunn – So Let It Be House (3/5, alternate cut) | https://youtu.be/EngjCkNIZ5I "So Let It Be Houze! [MD-WB-106]" (title-spelling drift hid it from auto-match) | [So Let It Be House (Clone)](https://www.discogs.com/release/37273977-Mike-Dunn-So-Let-It-Be-House) |

### Also still open from the earlier gaps report ([video_gaps_report.json](video_gaps_report.json))

Our verified uploads the pages lack: Batman 6.02 (`QwgIG6ecebg`), Heart Pound (`LzfEXQhjq-M`),
Solely Supported (`yX8n_UgpO5s`), Species (`9bRYskd4baE`), Without Fear (`riMr07afA_0`),
Slikback – Acid (`x7pK_6dqa7U`), Get Straight (`-4Z-lZcHkzs`) — plus ~25 pages with dead
embeds worth flagging/replacing (full list in the JSON).

---

## 2 · False positives — ignored, as instructed (36)

TMP's known failure mode confirmed: wrong mixes and multi-track rips. Highlights so you
can spot-check my judgment: *Circus Bells → Hardfloor Remix* (not Armando's Mix),
*Acid Over → Original Mix* (not Tyree's Mix), *Acid Tracks / Washing Machine → full-LP
rips >15 min*, *Terminal Velocity → Spiderman (Remix)* (different track, same 12"),
*I Am Acid → ACID (Pierre's Acid Face Mix)* (different record entirely). None adopted.

## 3 · FYI — differences that need no action

- **9 canon tracks TMP lacked** (it predates our later upgrades): Badsista – ACID APERTO,
  Ogee, Acid Hang Ups, Terminal Velocity, 100% Of Disin' U, Batman 6.02, Doing It To
  Death, I Am Acid, So Let It Be House.
- **TMP extras not matching any slot**: DJ Rush – Contour / Vaporize (wrong releases),
  100% Of Dissin' You (Warehouse Remix) (mix variant), old canon picks from before our
  swaps (Black Hands Sound 5, Ellipse, Acid Over Tyree Mix upload).

---

## Next steps (agreed sequence)

1. **You**: make the Discogs contributions above (and optionally flag dead embeds).
2. **Then**: delete the TuneMyPlaylist playlist (`PLEdjJ-AI_u5M`) — nothing above depends on it once contributed.
3. **Then**: rescrape + sync — `python3 create_playlist.py --token '<fresh>' --rescrape --prune`
   picks the newly contributed page videos up, upgrades ratings toward 5/5, and updates
   the live playlist in place.
