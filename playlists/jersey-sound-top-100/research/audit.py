import json, re, unicodedata
V = json.load(open("verified.json"))
def norm(s): return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode().lower()).strip()
def toks(s): return set(w for w in norm(s).split() if w)
def yh(s):
    m=re.search(r"(19|20)\d\d",s or ""); return int(m.group()) if m else None
STOP={"the","a","and","feat","featuring","ft","presents","pres"}
flags=[]
for r in sorted(V,key=lambda x:x["rank"]):
    rank=r["rank"]; st=r.get("status")
    if st!="verified":
        flags.append(f"#{rank:>3} [{st}] {r['artist_listed']} – {r['track_listed']}"); continue
    al=r["artist_listed"]; credit=r.get("credit","")
    at=toks(al)-STOP; ct=toks(credit)-STOP
    yhint=yh(r.get("year_hint","")); ry=r.get("rel_year")
    prob=[]
    # artist overlap (skip known multi-artist/comp cases)
    if at and ct and not (at & ct) and al not in("Various",):
        prob.append(f"ARTIST listed='{al}' vs credit='{credit}'")
    # year drift
    if yhint and ry and abs(ry-yhint)>2:
        prob.append(f"YEAR hint={yhint} rel={ry}")
    # track present in tracklist?
    tl=[t["title"] for t in r.get("tracklist",[])]
    tqt=toks(r["track_listed"])-STOP
    if tl and tqt and not any(tqt & (toks(t)-STOP) for t in tl):
        prob.append(f"TRACK '{r['track_listed']}' not in tracklist {tl[:4]}")
    # resolved by search with weak top score
    if r.get("resolved_by")=="search":
        cs=r.get("candidates",[])
        if cs and cs[0].get("score",0)<80:
            prob.append(f"WEAK score={cs[0]['score']}")
    if prob:
        flags.append(f"#{rank:>3} {al} – {r['track_listed']}\n       {r.get('credit')} – {r.get('title')} | rel={r.get('released')} | {'; '.join(r.get('labels',[])[:1])} | by={r.get('resolved_by')} | {r['url']}\n       ⚠ "+" | ".join(prob))
print(f"verified: {sum(1 for r in V if r.get('status')=='verified')}/{len(V)}  |  flagged for review: {len(flags)}")
print("\n".join(flags))
