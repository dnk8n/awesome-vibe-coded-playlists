# Iteration 1 — analyst notes

## Headline numbers (and why they mislead)

Both configs pass 100% of programmatic assertions. Two distortions:

1. **The eval prompts embedded the skill's method.** They spelled out "exactly as
   credited", "YouTube link from the videos on that Discogs page", "validated" —
   so the baseline agents were *prompted into* the skill's workflow and executed
   it competently. The assertions as written measure prompt-following, not the
   skill. Real users write vaguer briefs (see the original session: "I want a
   playlist of 3 notable Acid tracks per year... hard links to discogs...").
   **Iteration-2 suggestion:** re-run with realistic vague prompts ("make me a
   properly researched mini playlist of X with links") where the skill must
   supply the method itself.
2. **The baseline time/token aggregate is broken by the failed run.** Eval-0
   baseline hit the session usage limit; its timing is null → counted as 0,
   producing "2257.9s ± 3193.2s". The only clean comparable pair (eval-1):
   with-skill 4679s / 80.1k tokens vs baseline 4516s / 57.7k tokens.
   Real cost of the skill ≈ +4% time, +39% tokens on this eval.

## Where the skill visibly earned its cost (not captured by assertions)

- **Output contract extras** only in with-skill runs: alternates bench (5 extra
  verified picks in Detroit run), research queue, method header/footer,
  scope-definition note. These match what the original user actually used
  (they swapped a pick from the bench).
- **playlist_items.json compatibility:** with-skill files are directly
  consumable by `create_playlist.py` (list of `{video_id, label}`); both
  baselines wrapped ids in bespoke metadata dicts — the grader had to be
  loosened to read them, and the playlist-creation script would reject them.
  → **Add as an assertion in iteration 2** (discriminating and fair: the file's
  stated purpose is playlist creation).
- **Identity sourcing:** with-skill Detroit run cited 8 external sources for
  the Black-Detroit constraint; baseline asserted identities without sources.
- **Source-of-truth discipline:** with-skill run surfaced the famous Waveform
  Transmission Vol. 1 dating discrepancy (press says 1992, Discogs says 1993)
  and resolved it per the skill's rule, visibly noted.

## Risks/limits observed

- Runs are slow (~75–80 min) — dominated by Discogs pacing and agent
  deliberation, similar in both configs. Skill adds ~22k tokens of process.
- One of four agents died on the session usage limit; outputs survived because
  it wrote incrementally. The skill's "generate table from structured data"
  rule is what made the partial run recoverable.
- Assertion "YouTube pick from page or noted" passed for baselines partly
  because the prompt demanded it — see distortion #1.
