"""Enumerate every 2020+ Discogs release credited to each allowed-list artist
(Main, Remix, Appearance — the brief allows any credit)."""
import json, time, urllib.parse, sys
from platforms import get, dc_token, cached

TOK = dc_token()
HDR = {'Authorization': f'Discogs token={TOK}'}
NAMES = json.load(open('artists.json'))

# Hand-pinned Discogs artist ids where plain search picks the wrong person.
PINS = json.load(open('artist_pins.json')) if __import__('os').path.exists('artist_pins.json') else {}


def api(path, **params):
    def fn():
        time.sleep(1.1)
        u = 'https://api.discogs.com' + path
        if params:
            u += '?' + urllib.parse.urlencode(params)
        return json.loads(get(u, HDR))
    return cached('dcapi', path + json.dumps(params, sort_keys=True), fn)


def resolve(name):
    if name in PINS:
        return PINS[name]
    r = api('/database/search', q=name, type='artist', per_page=5)
    res = r.get('results', [])
    if not res:
        return None
    norm = lambda s: ''.join(c for c in s.lower() if c.isalnum())
    for x in res:                       # prefer an exact-ish name match
        if norm(x['title']) == norm(name):
            return x['id']
    return res[0]['id']


def releases(aid, pages=3):
    out = []
    for p in range(1, pages + 1):
        try:
            r = api(f'/artists/{aid}/releases', sort='year', sort_order='desc',
                    per_page=100, page=p)
        except Exception as e:
            print('  ! ', e); break
        items = r.get('releases', [])
        out += items
        if p >= (r.get('pagination', {}).get('pages') or 1):
            break
        if items and all((it.get('year') or 0) < 2020 for it in items):
            break                       # sorted desc: nothing newer below
    return out


if __name__ == '__main__':
    result = {}
    for name in NAMES:
        try:
            aid = resolve(name)
        except Exception as e:
            print(f'{name}: resolve failed {e}'); continue
        if not aid:
            print(f'{name}: no artist id'); continue
        rels = [r for r in releases(aid) if (r.get('year') or 0) >= 2020]
        result[name] = {'artist_id': aid, 'releases': [
            {'id': r.get('id'), 'type': r.get('type'), 'role': r.get('role'),
             'year': r.get('year'), 'title': r.get('title'), 'artist': r.get('artist'),
             'label': r.get('label'), 'main_release': r.get('main_release'),
             'stats': (r.get('stats') or {}).get('community', {})}
            for r in rels]}
        print(f'{name} [{aid}]: {len(rels)} releases 2020+', flush=True)
    json.dump(result, open('dc_sweep.json', 'w'), indent=1)
