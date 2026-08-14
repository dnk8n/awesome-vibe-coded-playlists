"""Build the public set-list markdown + playlist_items.json from resolved.json."""
import json, os

OUT = '../Friday Warm-Up Set — 20:30-22:30.md'
res = json.load(open('resolved.json'))
ov = json.load(open('link_overrides.json'))

PHASE = {
    'A': ('I. Disco, funky, soulful', '20:30 → ~20:45',
          'Warm and unhurried, but already moving. Every record here is a loft-lineage '
          'groove made in the 2020s — nothing to decode, everything to dance to.'),
    'B': ('II. Deep, introspective, acid', '~20:45 → ~21:00',
          'The descent. Chords, space and patience first, then the 303 arrives — cheerful '
          'acid rather than menacing, so the room gets hypnotised without getting gloomy.'),
    'C': ('III. Heavier, faster, funk intact', '~21:00 → 21:10',
          'Bass weight and pace arrive together. Still swung, still soulful, but now it '
          'hits like a rave record — the handover point.'),
}


def apply_ov(r):
    k = f"{r['artist']} :: {r['track']}"
    if k in ov:
        for f in ('yt', 'sc', 'bc'):
            if f in ov[k]:
                r[f] = ov[k][f]
        r['sc_note'] = ov[k].get('sc_note')
    return r


def links(r):
    out = []
    if r.get('yt'):
        out.append(f"[YouTube](https://www.youtube.com/watch?v={r['yt']})")
    if r.get('sc'):
        lbl = 'SoundCloud' + ('*' if r.get('sc_note') else '')
        out.append(f"[{lbl}]({r['sc']})")
    if r.get('bc'):
        out.append(f"[Bandcamp]({r['bc']})")
    if r.get('dc_url'):
        out.append(f"[Discogs]({r['dc_url']})")
    return ' · '.join(out)


def esc(s):
    return (s or '').replace('|', '\\|')


def row(r, n=True):
    cells = [str(r['n'])] if n else []
    cells += [esc(r['artist']), f"**{esc(r['track'])}**", str(r['year']),
              esc(r['label']), r.get('bpm', ''), links(r), esc(r['note'])]
    return '| ' + ' | '.join(cells) + ' |'


HEAD_N = ('| # | Artist | Track | Year | Label | ≈BPM | Find it | Why it is here |\n'
          '|:--|---|---|:--|---|:--|---|---|')
HEAD = ('| Artist | Track | Year | Label | Find it | Why it is benched |\n'
        '|---|---|:--|---|---|---|')

for k in res:
    res[k] = [apply_ov(r) for r in res[k]]

s1, s2, bench = res['set1'], res['set2'], res['bench']
ids_all = [r['yt'] for r in s1 + s2 if r.get('yt')]
ids1 = [r['yt'] for r in s1 if r.get('yt')]
ids2 = [r['yt'] for r in s2 if r.get('yt')]
wv = lambda ids: 'https://www.youtube.com/watch_videos?video_ids=' + ','.join(ids)

L = []
A = L.append
A('# Friday Warm-Up — 20:30 to 22:30')
A('')
A('**40 modern records, all of them made by people on your GOAT list, arranged as one '
  'continuous arc: disco and soul → deep and acid → heavy, fast and funky → straight into '
  'the b2b.** Set one is yours alone and carries the whole journey. Set two is the handover, '
  'stocked for a partner playing faster, harder UK garage and rave. Nothing here is pop, '
  'nothing here is a reissue of an old record — these are 2020s releases by the people who '
  'built the genres.')
A('')
cfg = json.load(open('config.json')) if os.path.exists('config.json') else {}
saved = (cfg.get('playlist') or {}).get('url')
if saved:
    A(f'**▶ [Listen on YouTube]({saved})** — saved playlist, all {len(ids_all)} tracks in set order '
      '(private to your account).')
    A('')
A(f'**▶ Or instantly, with no login:** [all {len(ids_all)} tracks in set order]({wv(ids_all)}) '
  f'· [set one only — the solo arc]({wv(ids1)}) · [set two only — the b2b bench]({wv(ids2)})')
A('')
A('---')
A('')
A('## How this was built')
A('')
A('**The allowed list is your document.** Every record below has at least one artist from '
  '*The Rave Canon* on it — as producer, remixer, vocalist, edit-maker or featured guest. '
  'Remix and edit credits count, which is where a lot of the best modern material by these '
  'people actually lives: Karizma turns up as Kaytronik, Robert Hood as Floorplan, Josh Milan '
  'as Blaze, Larry Heard as Mr. Fingers. Several rows carry **two** allowed-list names.')
A('')
A('**Modern, not remastered.** Everything is a 2020-or-later release of *new* material or a '
  '*new* remix/edit. Reissues and remasters of old records were excluded even where they '
  'charted well, because you asked for records made now, not records re-pressed now.')
A('')
A('**No pop.** Some of these artists have huge crossover records in this window — the '
  'Kylie and Dua Lipa collaborations, the chart remixes, the major-label box sets. All '
  'excluded on purpose. What is here is club music that got talked about in club places: '
  'label pages, RA and Mixmag coverage, Traxsource and Beatport garage charts, and the '
  'Discogs want-lists of people who buy this on vinyl.')
A('')
A('**Every link is checked.** Artist and track names are copied from the linked Discogs '
  'release page. YouTube IDs come from those same release pages (community-attached video, '
  'not open search) and every one was liveness-tested. SoundCloud and Bandcamp were matched '
  'against the exact credited mix — where the only hit was a *different* version of the same '
  'record, the link was dropped rather than fudged, which is why some rows have fewer '
  'platforms than others.')
A('')
A('**≈BPM is a feel estimate**, offered for sequencing only. These are my read of the record, '
  'not measured values — trust your player, not this column.')
A('')
A('An asterisk on a SoundCloud link means it is a snippet or preview, not the full cut.')
A('')
A('---')
A('')
A('# Set one — 20:30 to 21:10 · you, alone')
A('')
A(f'**{len(s1)} options for roughly 13 plays.** The three phases below are the brief: start '
  'disco/funky/soulful, cross into deep/introspective/acid, then go heavy and fast without '
  'dropping the funk. Play in order and the arc happens on its own; the surplus is there so '
  'you can read the floor rather than obey a list.')
A('')
for ph in ('A', 'B', 'C'):
    title, clock, blurb = PHASE[ph]
    rows = [r for r in s1 if r['phase'] == ph]
    A(f'## {title}')
    A(f'*{clock} · {len(rows)} options*')
    A('')
    A(blurb)
    A('')
    A(HEAD_N)
    for r in rows:
        A(row(r))
    A('')
A('---')
A('')
A('# Set two — 21:10 to 21:50 · the b2b · faster, harder, still funky')
A('')
A(f'**{len(s2)} options for roughly 6 plays.** Built for trading with a partner playing quick '
  'UK garage and rave. It opens on bumpy 4x4 garage, has two darker El-B tension records for '
  'when the room needs a breath before it accelerates, and finishes on full acid-rave. The '
  'hard-techno crowd gets its pressure; the smile stays on.')
A('')
A(HEAD_N)
for r in s2:
    A(row(r))
A('')
A('---')
A('')
A('## Alternates bench')
A('')
A('Verified swaps — same allowed list, same era, same checks. Drop one in when a row above '
  'does not suit the room.')
A('')
A(HEAD)
for r in bench:
    A('| ' + ' | '.join([esc(r['artist']), f"**{esc(r['track'])}**", str(r['year']),
                         esc(r['label']), links(r), esc(r['note'])]) + ' |')
A('')
A('---')
A('')
A('## Notes on the dig')
A('')
A('**Who carried it.** The names from your list with the strongest 2020s club output are '
  'Floorplan/Robert Hood, Kerri Chandler, Louie Vega, Mr. G, Hardfloor, El-B, Zed Bias, '
  'Karizma, Honey Dijon, Larry Heard, Miss Djax and Ellen Allien. If you want to dig further '
  'in the same window, those are the discographies with more where this came from.')
A('')
A('**Who could not be used.** A large part of the document is historical — Mancuso, Gibbons, '
  'Levan, Knuckles, Ron Hardy, Armando, Adonis, Bam Bam, Kemistry, Liza \'N\' Eliaz and others '
  'have no new 2020s material by definition, and their catalogue activity in this window is '
  'reissue and remaster work, which the brief rules out. Andrew Weatherall\'s posthumous '
  'releases are new-to-press but recorded before 2020, so they are out on the same test.')
A('')
A('**Where the arc is thinnest.** Straight *2-step* by the original UKG names is the hardest '
  'thing to find made new in this window. Wookie and Steve Gurley have essentially nothing '
  'since 2020 — their presence on Discogs in this period is compilation licensing of old cuts. '
  'MJ Cole is the exception and his 2024 fabric single is in the table. Set two therefore '
  'leans on El-B and Zed Bias, who did keep going, plus 4x4 and bassline from Grant Nelson. If '
  'your b2b partner wants heavier modern 2-step than that, the gap is best filled from outside '
  'your document.')
A('')
A('**Two-for-one rows.** Records carrying two allowed-list names, if you like that as a '
  'talking point: Igobolo (Vega + Claussell), Seven Mile (Vega + Moodymann), Fake & Unholy '
  '(Floorplan + Honey Dijon), Black Magic Woman (Ron Trent + Claussell), Gypsy Woman '
  '(Karizma + a Crystal Waters writing credit), Let Us Shine (Josh Milan + Vega), C\'s Up '
  '(Honey Dijon + Mike Dunn).')
A('')

# ---------------------------------------------------------------- SA bonus
SA_PHASE = {
    'A': ('Disco, funky, soulful', 'pairs with Set one, phase I'),
    'B': ('Deep, introspective, acid', 'pairs with Set one, phase II'),
    'C': ('Fast and funky — the 4x4 pivot', 'pairs with Set one, phase III'),
    'D': ('Faster, harder, rave', 'pairs with Set two, the b2b'),
}
if os.path.exists('resolved_sa.json'):
    sa = [apply_ov(r) for r in json.load(open('resolved_sa.json'))['bonus_sa']]
    sa_ids = [r['yt'] for r in sa if r.get('yt')]
    A('---')
    A('')
    A('# Bonus — the South African line')
    A('')
    A('**A separate pool, not part of the 40.** Same four categories as the set above, two '
      'records each, drawn from South Africa rather than from your document.')
    A('')
    A('**Why it belongs next to this canon.** South African house is not an offshoot of the '
      'Chicago/New York story — it is a direct continuation of it. Imported house and garage '
      'records reached Johannesburg clubs in the late 1980s; local DJs slowed them, put African '
      'percussion and township slang through them, and the result became kwaito, then SA deep '
      'house, then Afro house. The parallels to your arc are almost uncomfortably neat: '
      '**3-step** is South Africa\'s UK garage — producers take a 4/4 and pull the third or '
      'fourth kick out, which is the same swing trick 2-step plays — and **gqom** is its bass '
      'music, dark and broken and built for weight. One record here is a literal handshake '
      'between the two documents: Robert Owens, off your list, sung over a remix by Enoo Napa '
      'of Durban.')
    A('')
    A('**Tempo warning, and it matters.** 3-step and amapiano run **110–120 BPM** — slower than '
      'they feel, because the syncopation does the work the tempo usually does. Dropping one '
      'straight after a 130 BPM record will read as a handbrake unless you plan the transition. '
      'Gqom sits around 124–130 but is broken rather than four-to-the-floor. The DJ Lag cut at '
      'the bottom is the exception at roughly 158.')
    A('')
    A(f'**▶ [All {len(sa_ids)} bonus tracks, no login]({wv(sa_ids)})** — kept out of the main '
      'playlist so it stays a clean 40.')
    A('')
    for ph in ('A', 'B', 'C', 'D'):
        rows = [r for r in sa if r['phase'] == ph]
        if not rows:
            continue
        title, pairs = SA_PHASE[ph]
        A(f'## {title}')
        A(f'*{pairs}*')
        A('')
        A(HEAD_N)
        for r in rows:
            A(row(r))
        A('')
    A('**A note on what is missing.** There is no real South African *acid* tradition to draw '
      'on — the 303 never took root there the way it did in Chicago or Rotterdam. The deep and '
      'introspective slot is therefore filled on mood rather than on hardware, which is why '
      'Thakzin and the Enoo Napa remix sit in it instead of something squelching. **Six of these '
      'eight are not on Discogs at all**, and two carry no label credit I could verify — most '
      'modern South African dance music is released digital-first and never pressed, so '
      'Bandcamp, SoundCloud and the artists\' own YouTube channels are the record. That is '
      'exactly the case your four-platform rule was written for.')
    A('')

open(OUT, 'w').write('\n'.join(L) + '\n')

items = {'schema': 'discogs-playlist/v1',
         'playlist': {'title': 'Friday Warm-Up — 20:30-22:30',
                      'description': 'Modern releases by the GOAT DJs & Producers list. '
                                     'Disco/soulful into deep/acid into heavy funky 4x4 and UKG.',
                      'privacy': 'private'},
         'items': [{'position': i, 'video_id': r['yt'], 'artist': r['artist'],
                    'track': r['track'], 'year': r['year'], 'label': r['label'],
                    'discogs': r.get('dc_url'), 'soundcloud': r.get('sc'),
                    'bandcamp': r.get('bc'), 'set': ('set1' if r in s1 else 'set2'),
                    'phase': r.get('phase'), 'yt_source': r.get('yt_src')}
                   for i, r in enumerate(s1 + s2) if r.get('yt')]}
json.dump(items, open('../playlist_items.json', 'w'), indent=1)

print(f'wrote {OUT}  ({len(s1)}+{len(s2)} tracks, {len(bench)} bench)')
print('platform coverage:')
for name, rows in (('set1', s1), ('set2', s2), ('bench', bench)):
    print(f"  {name}: YT {sum(1 for r in rows if r.get('yt'))}/{len(rows)}  "
          f"SC {sum(1 for r in rows if r.get('sc'))}/{len(rows)}  "
          f"BC {sum(1 for r in rows if r.get('bc'))}/{len(rows)}  "
          f"DC {sum(1 for r in rows if r.get('dc_url'))}/{len(rows)}")
print('anon playlist ids:', len(ids_all))
