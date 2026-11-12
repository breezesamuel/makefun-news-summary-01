import json, os, re, sys
import xml.etree.ElementTree as ET
import email.utils as eut
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "raw")
T0, T1 = 1794355200, 1794441600
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def jload(name):
    try:
        return json.load(open(os.path.join(OUT, name), encoding="utf-8"))
    except Exception:
        return None

# ---- merge all HN stories ----
allh = []
for fn in sorted(os.listdir(OUT)):
    if fn.startswith("hn_bydate_p") and fn.endswith(".json"):
        j = jload(fn)
        if j:
            allh.extend(j.get("hits", []))
seen = {}
for h in allh:
    oid = h.get("objectID")
    if oid and oid not in seen:
        seen[oid] = h
stories = [h for h in seen.values() if T0 < h.get("created_at_i", 0) < T1]
stories.sort(key=lambda h: (h.get("points", 0), h.get("num_comments", 0)), reverse=True)
bystory = {h["objectID"]: h for h in stories}

def slim(h):
    return {
        "id": h["objectID"],
        "title": h.get("title"),
        "points": h.get("points"),
        "num_comments": h.get("num_comments"),
        "author": h.get("author"),
        "created_utc": datetime.fromtimestamp(h["created_at_i"], timezone.utc).isoformat(),
        "url": h.get("url") or ("https://news.ycombinator.com/item?id=" + h["objectID"]),
        "hn_url": "https://news.ycombinator.com/item?id=" + h["objectID"],
    }

CITED = ["50459321","50459703","50454937","50450488","50458900","50451102","50450955","50455898",
         "50454289","50456735","50455704","50454140","50454010","50451985","50454418","50452895",
         "50455907","50460744","50458234","50454106","50450055","50450601","50452139","50453301",
         "50455376","50456631","50456740","50456791","50458532","50459485","50452742","50453637",
         "50454625","50457230","50458166","50460154","50455633","50453171","50451903","50453555",
         "50459745","50453288","50457164","50456668","50453064","50451820","50457124",
         "50451588","50454606","50456534","50456753","50452455","50459151","50457669","50457083",
         "50451805","50453474","50455394"]

cited = [slim(bystory[i]) for i in CITED if i in bystory]
missing = [i for i in CITED if i not in bystory]

# ---- GitHub ----
gh = jload("gh_day.json")
gh_repos = []
if gh:
    for r in gh.get("items", []):
        gh_repos.append({
            "full_name": r.get("full_name"),
            "url": r.get("html_url"),
            "stars": r.get("stargazers_count"),
            "language": r.get("language"),
            "description": (r.get("description") or "")[:200],
            "created_at": r.get("created_at"),
        })

# ---- France24 ----
f24 = []
f24_meta = {}
p = os.path.join(OUT, "rss_france24.xml")
if os.path.exists(p):
    root = ET.parse(p).getroot()
    for it in root.findall(".//item"):
        t = (it.findtext("title") or "").strip()
        d = (it.findtext("pubDate") or "").strip()
        link = (it.findtext("link") or "").strip()
        try:
            dt = eut.parsedate_to_datetime(d).astimezone(timezone.utc)
        except Exception:
            continue
        if T0 <= dt.timestamp() < T1:
            f24.append({"time_utc": dt.isoformat(), "title": t, "url": link})
uniq_titles = []
for e in f24:
    key = e["title"].lower()
    if key not in uniq_titles:
        uniq_titles.append(key)
f24_meta = {"in_window_entries": len(f24), "unique_headlines": len(uniq_titles)}

# ---- arXiv ----
arxiv_status = {}
for fn in ["arxiv_csai.xml", "arxiv_cslg.xml"]:
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        txt = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"<lastBuildDate>([^<]+)</lastBuildDate>", txt)
        arxiv_status[fn] = {"items": txt.count("<item>"), "lastBuildDate": m.group(1) if m else None}
NS = {"a": "http://www.w3.org/2005/Atom"}
adjacent = []
p = os.path.join(OUT, "arxiv_api2_csAI.xml")
if os.path.exists(p):
    root = ET.parse(p).getroot()
    for e in root.findall("a:entry", NS)[:8]:
        if (e.findtext("a:published", "", NS) or "").startswith("2026-11-10"):
            adjacent.append({
                "id": e.findtext("a:id", "", NS).replace("http://arxiv.org/abs/", ""),
                "published": e.findtext("a:published", "", NS),
                "title": (e.findtext("a:title", "", NS) or "").strip(),
            })

# ---- Firebase cross-check ----
cross = []
j = jload("hn_firebase_topstories.json")
if j:
    for rank, oid in enumerate(j[:30]):
        it = jload("hn_firebase_item_%s.json" % oid)
        if it:
            cross.append({
                "front_page_rank": rank + 1,
                "id": str(oid),
                "in_window": T0 < it.get("time", 0) < T1,
                "title": it.get("title"),
                "points": it.get("score"),
            })

# ---- fetch log ----
flog = jload("_fetch_log.json") or []

pts = sorted([h.get("points", 0) for h in stories], reverse=True)
n = len(pts)

src = jload("gh_day.json")

doc = {
    "entry": "make.fun competition news-summary-01 — 2026-11-11 world news digest",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "window": {
        "start_utc": "2026-11-11T00:00:00Z",
        "end_utc": "2026-11-12T00:00:00Z",
        "epoch_start": T0,
        "epoch_end": T1,
    },
    "stats": {
        "hn_stories_in_window": len(stories),
        "hn_points_max": pts[0],
        "hn_points_p99": pts[max(0, int(n * 0.01))],
        "hn_points_p90": pts[max(0, int(n * 0.1))],
        "hn_points_median": pts[n // 2],
        "france24_in_window_entries": f24_meta["in_window_entries"],
        "france24_unique_headlines": f24_meta["unique_headlines"],
        "github_repos_created_that_day_reported_by_api": (gh or {}).get("total_count"),
    },
    "sources_used": [
        {"kind": "hacker_news_algolia", "what": "all 1,000 stories in window (10 pages x 100, by date)", "status": "ok"},
        {"kind": "hacker_news_algolia_items", "what": "full comment threads for top 25 stories", "status": "ok"},
        {"kind": "hacker_news_firebase", "what": "front-page snapshot 2026-11-12 ~08:10 UTC as recency cross-check", "status": "ok"},
        {"kind": "github_search", "what": "repositories created 2026-11-11 sorted by stars", "status": "ok (1 query; second query rate-limited 403)"},
        {"kind": "arxiv_api", "what": "cs.AI/cs.LG submissions in-window (0 found) + newest adjacent batch", "status": "ok"},
        {"kind": "arxiv_rss", "what": "rss.arxiv.org cs.AI/cs.LG built 2026-11-12 05:00 UTC", "status": "ok but 0 items"},
        {"kind": "france24_rss", "what": "world wire", "status": "ok"},
        {"kind": "bbc_rss", "what": "feeds.bbci.co.uk/news/world/rss.xml", "status": "failed (SSL handshake timeout)"},
        {"kind": "dw_rss", "what": "rss.dw.com/rdf/rss-en-world", "status": "failed (connection reset)"},
    ],
    "hn_stories_cited_in_summary": cited,
    "hn_cited_ids_missing_from_merge": missing,
    "hn_top10_by_points": [slim(h) for h in stories[:10]],
    "github_breakout_repos_created_2026_11_11": gh_repos,
    "france24_in_window_items": f24,
    "arxiv_status": {
        "rss": arxiv_status,
        "api_newest_csAI_published": "2026-11-10T18:59:54Z",
        "in_window_announcements": 0,
        "adjacent_batch_sample": adjacent,
    },
    "firebase_front_page_cross_check": cross,
    "fetch_log": flog,
}

out_path = os.path.join(BASE, "sources.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)
print("sources.json written:", os.path.getsize(out_path), "bytes; cited:", len(cited), "missing:", missing)
