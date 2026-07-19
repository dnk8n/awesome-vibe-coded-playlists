# Skill evaluation — how discogs-playlist was tested

The skill was evaluated by giving the **same two mini-briefs** to fresh agents twice:
once **with the skill**, once **without** (baseline), then grading every output with an
**API-backed grader** rather than eyeballing — the assertions call the live Discogs and
YouTube APIs to check the outputs' actual claims.

## The test playlists

- **detroit-mini-canon** — "2 notable Detroit techno tracks per year 1991–1993, every
  track with core involvement from a Black Detroit artist" (tests identity constraints,
  credit exactness, page-video matching)
- **dance-mania-label-retro** — "5 essential Dance Mania releases 1994–96, max one per
  artist" (tests label-scan curation and the honest-skip rule)

All four runs (2 briefs × with/without skill) are preserved verbatim under
[`runs/`](runs/), with per-run `grading.json` and `timing.json`.

## The "unit tests"

[`evals.json`](evals.json) holds the prompts + assertions;
[`check_outputs.py`](check_outputs.py) executes them: table row counts, every Discogs
link resolves via the API, artist credits match the release page verbatim (join phrases
included), tracks exist on the linked releases' tracklists, YouTube picks are traceable
to page videos or explicitly noted, ids are live and public, rows date-sorted, plus
brief-specific constraints (label, year window, distinct artists).

Needs `DISCOGS_TOKEN` and `YOUTUBE_API_KEY` (env vars or `.discogs_token`/`.yt_key`
files):

```
python3 check_outputs.py runs/eval-1-dance-mania-label-retro/with_skill/run-1/outputs \
  --rows 5 --require-label "Dance Mania" --years 1994-1996 --distinct-artists
```

## Results — and the honest caveats

Headline: **100% assertion pass rate in BOTH configurations**
([benchmark](runs/benchmark.md)). The [analyst notes](runs/analysis.md) explain why that
headline undersells the skill: the test prompts spelled out the method ("exactly as
credited", "video from the Discogs page"), effectively teaching the baseline the
workflow — real briefs are vaguer. The differences showed up **outside** the assertions:
only with-skill runs produced the alternates bench, research queue, and schema-compatible
items files (both baselines invented incompatible JSON wrappers); the with-skill Detroit
run cited 8 sources for its identity claims and surfaced the famous Waveform
Transmission 1992/1993 dating discrepancy. Cost of the skill on the one cleanly
comparable pair: ~+4% time, +39% tokens. [`runs/feedback.json`](runs/feedback.json) is
the human review verbatim — it's where the `discogs-playlist/v1` rich schema was born
("I prefer this richer json format" → merged from the two baselines' ad-hoc formats).
