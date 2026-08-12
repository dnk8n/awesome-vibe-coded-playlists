"""Resolve every pick across YouTube / SoundCloud / Bandcamp / Discogs.

YouTube ids come from the Discogs release pages (community-curated) and are
liveness-checked via oEmbed. SoundCloud and Bandcamp are matched by token
overlap against the credited artist + track, with a threshold so a near-miss
is reported as "not found" rather than a wrong link.
"""
import json, re, sys
from platforms import sc_search, bc_search, yt_alive, yt_search

STOP = {'the', 'a', 'an', 'of', 'and', 'feat', 'featuring', 'ft', 'vs', 'presents',
        'pres', 'x', 'w'}

# Words that name a *version*. Getting these wrong means linking a different record,
# so they are scored separately and some of them are hard blockers.
VERSION = {'mix', 'remix', 'version', 'edit', 'edits', 'extended', 'original', 'main',
           'club', 'dub', 'vocal', 'instrumental', 'radio', 'vip', 'refix', 'acapella',
           'snippet', 'live', 'demo', 'rework', 'bootleg', 'preview'}
# If the candidate claims one of these and the target does not, it is a different cut.
BLOCK = {'remix', 'vip', 'refix', 'instrumental', 'acapella', 'snippet', 'radio',
         'live', 'demo', 'bootleg', 'preview', 'rework'}


def toks(s, keep_parens=True):
    s = s or ''
    if not keep_parens:
        s = re.sub(r'\(.*?\)|\[.*?\]', ' ', s)
    return {t for t in re.findall(r'[a-z0-9]+', s.lower()) if t not in STOP and len(t) > 1}


def score(cand, want_a, want_t):
    """Core title tokens must nearly all be present; version words must not conflict."""
    c = toks(cand)
    ta = toks(want_a)
    tt = toks(want_t)
    core_t, ver_t = tt - VERSION, tt & VERSION
    core_c, ver_c = c - VERSION, c & VERSION
    if not core_t:
        return 0.0
    # hard block: candidate advertises a version the target never asked for
    if (ver_c & BLOCK) - ver_t:
        # tolerated when the target itself names that word inside a remixer credit
        if not ((ver_c & BLOCK) - ver_t) & ver_t:
            return 0.0
    core_hit = len(core_t & core_c) / len(core_t)
    if core_hit < 0.8:
        return 0.0
    a_hit = len(ta & c) / len(ta) if ta else 1.0
    ver_hit = len(ver_t & ver_c) / len(ver_t) if ver_t else 1.0
    return 0.45 * core_hit + 0.3 * a_hit + 0.25 * ver_hit


def best(cands, want_a, want_t, get_text, floor=0.75):
    ranked = sorted(((score(get_text(c), want_a, want_t), c) for c in cands),
                    key=lambda x: -x[0])
    if ranked and ranked[0][0] >= floor:
        return ranked[0][1], round(ranked[0][0], 2)
    return None, (round(ranked[0][0], 2) if ranked else 0)


def discogs_url(dc):
    if not dc:
        return None
    if dc.get('master'):
        return f"https://www.discogs.com/master/{dc['master']}"
    if dc.get('release'):
        return f"https://www.discogs.com/release/{dc['release']}"
    return None


def resolve(p):
    a, t = p['artist'], p['track']
    q = f'{a} {t}'
    out = dict(p)

    # --- YouTube: page-sourced id, liveness-checked; fall back to search ---
    vid, src = p.get('yt'), 'discogs page'
    if vid and not yt_alive(vid):
        vid, src = None, 'dead page embed'
    if not vid:
        cands = [c for c in yt_search(q, limit=8) if 'error' not in c]
        c, sc = best(cands, a, t, lambda c: f"{c.get('title','')} {c.get('channel','')}")
        if c and yt_alive(c['id']):
            vid, src = c['id'], f'youtube search ({sc})'
        else:
            src = 'not found'
    out['yt'] = vid
    out['yt_src'] = src

    # --- SoundCloud ---
    cands = [c for c in sc_search(q, limit=12) if 'error' not in c and 120 <= c['dur_s'] <= 1200]
    c, sc = best(cands, a, t, lambda c: f"{c.get('title','')} {c.get('user','')}")
    out['sc'] = c['url'] if c else None
    out['sc_score'] = sc

    # --- Bandcamp (tracks, then albums) ---
    bc = None
    for kind in ('t', 'a'):
        cands = [c for c in bc_search(q, kind) if 'error' not in c and c.get('url')]
        c, s = best(cands, a, t, lambda c: f"{c.get('name','')} {c.get('band','')} {c.get('album','')}",
                    floor=0.78 if kind == "t" else 0.85)
        if c:
            bc = c['url']; out['bc_score'] = s; out['bc_kind'] = kind
            break
    out['bc'] = bc

    out['dc_url'] = discogs_url(p.get('dc'))
    return out


if __name__ == '__main__':
    data = json.load(open('picks.json'))
    res = {}
    for key in ('set1', 'set2', 'bench'):
        res[key] = []
        for p in data[key]:
            r = resolve(p)
            res[key].append(r)
            plats = ''.join(x for x, v in (('Y', r['yt']), ('S', r['sc']), ('B', r['bc']),
                                           ('D', r['dc_url'])) if v)
            print(f"{r.get('n','  '):>3} {plats:<4} {r['artist'][:28]:<28} {r['track'][:40]:<40} "
                  f"yt={r['yt_src']}", flush=True)
    json.dump(res, open('resolved.json', 'w'), indent=1)
    for k in res:
        n = len(res[k])
        print(f"{k}: {n} | YT {sum(1 for r in res[k] if r['yt'])} "
              f"SC {sum(1 for r in res[k] if r['sc'])} "
              f"BC {sum(1 for r in res[k] if r['bc'])} "
              f"DC {sum(1 for r in res[k] if r['dc_url'])}")
