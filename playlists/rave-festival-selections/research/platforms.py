"""Keyless resolvers for YouTube / SoundCloud / Bandcamp / Discogs."""
import urllib.request, urllib.parse, json, re, os, time, hashlib

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(CACHE, exist_ok=True)

def _cache_path(kind, key):
    d = os.path.join(CACHE, kind); os.makedirs(d, exist_ok=True)
    return os.path.join(d, hashlib.sha1(key.encode()).hexdigest() + '.json')

def cached(kind, key, fn):
    p = _cache_path(kind, key)
    if os.path.exists(p):
        try: return json.load(open(p))
        except Exception: pass
    v = fn()
    json.dump(v, open(p, 'w'))
    return v

def get(url, headers=None, timeout=30):
    h = {'User-Agent': UA}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return f.read().decode('utf-8', 'replace')

def post_json(url, payload, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={'User-Agent': UA, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.loads(f.read().decode('utf-8', 'replace'))

# ---------------- SoundCloud ----------------
_CID = None
def sc_client_id():
    global _CID
    if _CID: return _CID
    p = os.path.join(CACHE, 'sc_client_id.txt')
    if os.path.exists(p):
        _CID = open(p).read().strip()
        if _sc_ok(_CID): return _CID
    html = get('https://soundcloud.com/discover')
    for src in reversed(re.findall(r'src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"', html)):
        try: js = get(src)
        except Exception: continue
        m = re.search(r'client_id[:=]"([A-Za-z0-9]{32})"', js)
        if m and _sc_ok(m.group(1)):
            _CID = m.group(1); open(p, 'w').write(_CID); return _CID
    raise RuntimeError('no soundcloud client_id')

def _sc_ok(cid):
    try:
        get(f'https://api-v2.soundcloud.com/search/tracks?q=test&client_id={cid}&limit=1'); return True
    except Exception: return False

def sc_search(q, limit=15):
    def fn():
        cid = sc_client_id()
        u = (f'https://api-v2.soundcloud.com/search/tracks?q={urllib.parse.quote(q)}'
             f'&client_id={cid}&limit={limit}')
        d = json.loads(get(u))
        out = []
        for t in d.get('collection', []):
            out.append({
                'title': t.get('title'), 'user': (t.get('user') or {}).get('username'),
                'url': t.get('permalink_url'), 'plays': t.get('playback_count') or 0,
                'likes': t.get('likes_count') or 0, 'created': (t.get('display_date') or '')[:10],
                'dur_s': round((t.get('duration') or 0) / 1000),
                'genre': t.get('genre'), 'label': (t.get('publisher_metadata') or {}).get('release_title'),
            })
        return out
    try: return cached('sc', q, fn)
    except Exception as e: return [{'error': str(e)}]

# ---------------- Bandcamp ----------------
def bc_search(q, kind='t'):
    def fn():
        d = post_json('https://bandcamp.com/api/bcsearch_public_api/1/autocomplete_elastic',
                      {'search_text': q, 'search_filter': kind, 'full_page': False, 'fan_id': None})
        out = []
        for r in (d.get('auto') or {}).get('results', []):
            out.append({'type': r.get('type'), 'name': r.get('name'), 'band': r.get('band_name'),
                        'album': r.get('album_name'), 'url': r.get('item_url_path')})
        return out
    try: return cached('bc' + kind, q, fn)
    except Exception as e: return [{'error': str(e)}]

# ---------------- YouTube ----------------
def yt_search(q, limit=8):
    def fn():
        html = get('https://www.youtube.com/results?search_query=' + urllib.parse.quote(q))
        m = re.search(r'var ytInitialData = (\{.*?\});</script>', html)
        if not m: return []
        data = json.loads(m.group(1))
        out, seen = [], set()
        def walk(o):
            if isinstance(o, dict):
                if 'videoRenderer' in o:
                    v = o['videoRenderer']; vid = v.get('videoId')
                    if vid and vid not in seen:
                        seen.add(vid)
                        title = ''.join(r.get('text', '') for r in (v.get('title', {}).get('runs') or []))
                        ch = ''
                        for k in ('ownerText', 'longBylineText'):
                            if v.get(k): ch = ''.join(r.get('text','') for r in v[k].get('runs', []))
                            if ch: break
                        out.append({'id': vid, 'title': title, 'channel': ch,
                                    'dur': (v.get('lengthText') or {}).get('simpleText'),
                                    'views': (v.get('viewCountText') or {}).get('simpleText'),
                                    'published': (v.get('publishedTimeText') or {}).get('simpleText')})
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(data)
        return out[:limit]
    try: return cached('yt', q, fn)
    except Exception as e: return [{'error': str(e)}]

def yt_alive(vid):
    def fn():
        try:
            get('https://www.youtube.com/oembed?format=json&url=' +
                urllib.parse.quote('https://www.youtube.com/watch?v=' + vid))
            return True
        except Exception: return False
    return cached('ytalive', vid, fn)

# ---------------- Discogs (anonymous release reads; search needs a token) ----------------
def dc_token():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.discogs_token')
    return open(p).read().strip() if os.path.exists(p) else None

def dc_search(q, **kw):
    tok = dc_token()
    if not tok: return [{'error': 'no token'}]
    def fn():
        params = {'q': q, 'per_page': 8, 'type': 'release'}; params.update(kw)
        u = 'https://api.discogs.com/database/search?' + urllib.parse.urlencode(params)
        d = json.loads(get(u, {'Authorization': f'Discogs token={tok}'}))
        return [{'id': r.get('id'), 'master_id': r.get('master_id'), 'title': r.get('title'),
                 'year': r.get('year'), 'label': (r.get('label') or [None])[0],
                 'uri': 'https://www.discogs.com' + (r.get('uri') or '')} for r in d.get('results', [])]
    try: return cached('dc', q + json.dumps(kw, sort_keys=True), fn)
    except Exception as e: return [{'error': str(e)}]

def dc_release(rid):
    def fn():
        time.sleep(2.5)
        return json.loads(get(f'https://api.discogs.com/releases/{rid}'))
    try: return cached('dcrel', str(rid), fn)
    except Exception as e: return {'error': str(e)}

if __name__ == '__main__':
    import sys
    fn = {'sc': sc_search, 'bc': bc_search, 'yt': yt_search, 'dc': dc_search}[sys.argv[1]]
    print(json.dumps(fn(' '.join(sys.argv[2:])), indent=1)[:4000])
