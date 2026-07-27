#!/usr/bin/env python3
"""Splice article.md + contents + ONE big table (rows/*.json) -> ../bump.md."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "bump.md"
MARKER = "<!-- INSERT_TABLES_HERE -->"

STATUS_DG = {True: "✅", False: "❌"}
STATUS_YT = {"exact": "🎯", "fallback": "▶", "none": "∅"}

HEADER = ("| ID | Series | Artist | Track | Genre | Style | Released | SA "
          "| Discogs | YouTube | Notes | Status |")
ALIGN = "|---|---|---|---|---|---|---|---|---|---|---|---|"


def watch_urls(rows):
    """Anonymous playlist URL(s), sleeve order, <=50 ids each (URL cap)."""
    ids = [r["yt_id"] for r in rows if r["yt_id"]]
    return ["https://www.youtube.com/watch_videos?video_ids=" + ",".join(chunk)
            for chunk in (ids[i:i + 50] for i in range(0, len(ids), 50)) if chunk]


def esc(s):
    return (s or "").replace("|", "\\|")


def contents_line(doc):
    urls = watch_urls(doc["rows"])
    got = sum(1 for r in doc["rows"] if r["yt_id"])
    if len(urls) == 1:
        play = f"[▶ Play all {got}]({urls[0]})"
    elif urls:
        play = " · ".join(f"[▶ Part {i} of {len(urls)}]({u})"
                          for i, u in enumerate(urls, 1))
    else:
        play = "—"
    return (f"| {doc['bump_n']} | [{esc(doc['title'])}]({doc['url']}) "
            f"| {doc['year']} | {esc(doc['label'])} | {play} |")


def row_line(r):
    if r["dg_url"]:
        dg = f"[{r['dg_kind']} · {r['dg_year']}]({r['dg_url']})"
    else:
        dg = "—"
    yt = f"[▶ Watch](https://youtu.be/{r['yt_id']})" if r["yt_id"] else "—"
    status = STATUS_DG[bool(r["dg_url"])] + " " + STATUS_YT[r["yt_match"]]
    return "| " + " | ".join([
        r["id"], str(r["series"]), esc(r["artist"]), esc(r["track"]),
        esc(r["genre"]) or "—", esc(r["style"]) or "—",
        esc(r.get("released")) or "—", "✓" if r.get("sa") else "",
        dg, yt, esc("; ".join(r["notes"])), status]) + " |"


def main():
    docs = [json.loads(p.read_text()) for p in sorted((HERE / "rows").glob("bump_*.json"))]
    docs.sort(key=lambda d: d["bump_n"])

    lines = ["## Contents", "",
             "| # | Bump release | Year | Label | Anonymous playlist |",
             "|---|---|---|---|---|"]
    lines += [contents_line(d) for d in docs]
    lines += ["", "## All tracks", "", HEADER, ALIGN]
    for d in docs:
        lines += [row_line(r) for r in d["rows"]]
    lines.append("")

    article = (HERE / "article.md").read_text()
    OUT.write_text(article.replace(MARKER, "\n".join(lines)))
    total = sum(len(d["rows"]) for d in docs)
    print(f"{OUT.name}: {len(docs)} volumes, {total} rows")


if __name__ == "__main__":
    main()
