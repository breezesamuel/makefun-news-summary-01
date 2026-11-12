import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone

BASE = r"F:\2026\第二次点子\hackathon-qday\entry\news-summary-01-dev"
OUT = os.path.join(BASE, "raw")
os.makedirs(OUT, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

T0, T1 = 1794355200, 1794441600
print("WINDOW UTC:", datetime.fromtimestamp(T0, timezone.utc), "->", datetime.fromtimestamp(T1, timezone.utc))

UA = {"User-Agent": "qday-news-digest/1.0 (research)"}
GH_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
log = []

def fetch(url, name, timeout=20, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)
        log.append({"name": name, "url": url, "status": "ok", "bytes": len(data)})
        print("OK", name, len(data))
        return True
    except Exception as e:
        log.append({"name": name, "url": url, "status": "error", "error": repr(e)[:200]})
        print("FAIL", name, repr(e)[:120])
        return False

def jload(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("PARSEFAIL", name, e)
        return None

def main():
    # 1) HN Algolia by-date pagination
    hits_total = 0
    for page in range(7):
        q = urllib.parse.urlencode({
            "tags": "story",
            "numericFilters": "created_at_i>%d,created_at_i<%d" % (T0, T1),
            "hitsPerPage": "100",
            "page": str(page),
        })
        ok = fetch("https://hn.algolia.com/api/v1/search_by_date?" + q, "hn_bydate_p%d.json" % page, timeout=25)
        if not ok:
            break
        j = jload("hn_bydate_p%d.json" % page)
        if not j or not j.get("hits"):
            print("page empty:", page)
            break
        hits_total += len(j["hits"])
        if len(j["hits"]) < 100:
            print("last page:", page, len(j["hits"]))
            break
    print("STORIES FETCHED:", hits_total)

    # 2) top 15 by points -> item details incl. comments
    allh = []
    for fn in os.listdir(OUT):
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
    print("UNIQUE STORIES IN WINDOW:", len(stories))
    for h in stories[:15]:
        fetch("https://hn.algolia.com/api/v1/items/" + h["objectID"], "hn_item_%s.json" % h["objectID"], timeout=25)
        time.sleep(0.15)

    # 3) GitHub breakout repos
    gh_headers = {"Accept": "application/vnd.github+json"}
    if GH_TOKEN:
        gh_headers["Authorization"] = "Bearer " + GH_TOKEN
        print("GITHUB: using token")
    else:
        print("GITHUB: unauthenticated")
    q1 = urllib.parse.urlencode({"q": "created:2026-11-11", "sort": "stars", "order": "desc", "per_page": "20"})
    fetch("https://api.github.com/search/repositories?" + q1, "gh_day.json", timeout=25, headers=gh_headers)
    time.sleep(3)
    q2 = urllib.parse.urlencode({"q": "created:2026-11-10..2026-11-11", "sort": "stars", "order": "desc", "per_page": "20"})
    fetch("https://api.github.com/search/repositories?" + q2, "gh_two_days.json", timeout=25, headers=gh_headers)

    # 4) arXiv RSS
    fetch("https://rss.arxiv.org/rss/cs.AI", "arxiv_csai.xml", timeout=30)
    fetch("https://rss.arxiv.org/rss/cs.LG", "arxiv_cslg.xml", timeout=30)

    # 5) international RSS probes
    for name, url in [
        ("rss_bbccouk_world.xml", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("rss_dw_world.xml", "https://rss.dw.com/rdf/rss-en-world"),
        ("rss_france24.xml", "https://www.france24.com/en/rss"),
    ]:
        fetch(url, name, timeout=10)

    # 6) Firebase cross-check
    fetch("https://hacker-news.firebaseio.com/v0/topstories.json", "hn_firebase_topstories.json", timeout=15)
    j = jload("hn_firebase_topstories.json")
    if j:
        for oid in j[:30]:
            fetch("https://hacker-news.firebaseio.com/v0/item/%s.json" % oid, "hn_firebase_item_%s.json" % oid, timeout=12)
            time.sleep(0.05)

    with open(os.path.join(OUT, "_fetch_log.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1)
    print("DONE. fetches:", len(log), "ok:", sum(1 for r in log if r["status"] == "ok"))

main()
