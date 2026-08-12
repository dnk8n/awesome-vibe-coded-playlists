"""Print Discogs tracklists (+ page videos) for candidate releases."""
import json, sys, time, urllib.parse
from platforms import get, dc_token, cached

HDR = {'Authorization': f'Discogs token={dc_token()}'}


def api(path, **params):
    def fn():
        time.sleep(1.1)
        u = 'https://api.discogs.com' + path
        if params:
            u += '?' + urllib.parse.urlencode(params)
        return json.loads(get(u, HDR))
    return cached('dcapi', path + json.dumps(params, sort_keys=True), fn)


def credit(artists):
    out = ''
    for a in artists or []:
        nm = a.get('anv') or a.get('name') or ''
        nm = __import__('re').sub(r'\s\(\d+\)$', '', nm)
        out += nm + (' ' + a['join'] + ' ' if a.get('join', '').strip() else
                     (' ' if a.get('join') == '' else ''))
    return out.strip().rstrip(',')


def show(rid):
    r = api(f'/releases/{rid}')
    if 'id' not in r:
        print(f'#{rid}: {r}'); return
    print(f"\n=== #{rid} {credit(r.get('artists'))} - {r.get('title')} "
          f"[{', '.join(l['name'] for l in r.get('labels', []))}] "
          f"{r.get('released') or r.get('year')} master={r.get('master_id')}")
    for t in r.get('tracklist', []):
        if t.get('type_') != 'track':
            continue
        ta = credit(t.get('artists')) if t.get('artists') else ''
        ex = ''
        for e in t.get('extraartists', []) or []:
            ex += f" [{e.get('role')}: {credit([e])}]"
        print(f"   {t.get('position','') :<5} {ta + ' - ' if ta else ''}{t.get('title')} "
              f"({t.get('duration') or '?'}){ex}")
    for v in r.get('videos', []) or []:
        vid = v.get('uri', '').split('v=')[-1][:11]
        print(f"   > YT {vid}  {v.get('title','')[:70]}")


if __name__ == '__main__':
    for rid in sys.argv[1:]:
        try:
            show(rid)
        except Exception as e:
            print(f'#{rid} ERROR {e}')
