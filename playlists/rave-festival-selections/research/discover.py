import json, sys, re
from platforms import sc_search, bc_search

artists = json.load(open('artists.json'))
out = {}
for a in artists:
    rows = []
    for q in (a, a + ' remix'):
        for t in sc_search(q, limit=30):
            if 'error' in t: continue
            yr = int((t['created'] or '0')[:4] or 0)
            if yr < 2020: continue
            if not (100 <= t['dur_s'] <= 960): continue   # drop DJ mixes / radio shows
            title = (t['title'] or '')
            low = (title + ' ' + (t['user'] or '')).lower()
            if any(k in low for k in ('podcast','radio show','episode','live at','liveset','dj set','mix show','@ ','boiler room','tracklist')): continue
            rows.append(t)
    seen, ded = set(), []
    for t in sorted(rows, key=lambda x: -x['plays']):
        k = re.sub(r'[^a-z0-9]', '', (t['title'] or '').lower())[:40]
        if k in seen: continue
        seen.add(k); ded.append(t)
    out[a] = ded[:12]
    print(f"{a}: {len(ded)}", flush=True)
json.dump(out, open('sc_sweep.json','w'), indent=1)
