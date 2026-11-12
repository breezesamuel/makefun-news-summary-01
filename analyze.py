import json, os, re, sys, html
import xml.etree.ElementTree as ET
import email.utils as eut
from datetime import datetime, timezone

BASE = r"F:\2026\第二次点子\hackathon-qday\entry\news-summary-01-dev"
OUT = os.path.join(BASE, "raw")
T0, T1 = 1794355200, 1794441600
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def jload(name):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

lines = []
def out(s=""):
    lines.append(str(s))

# ---------- HN merge ----------
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

out("=== UNIQUE STORIES IN WINDOW: %d (from %d raw hits) ===" % (len(stories), len(allh)))
pts = sorted([h.get("points", 0) for h in stories], reverse=True)
n = len(pts)
out("points max/p99/p90/p50/min: %s / %s / %s / %s / %s" % (
    pts[0], pts[max(0, int(n * 0.01))], pts[max(0, int(n * 0.1))], pts[n // 2], pts[-1]))

out("")
out("=== TOP 40 BY POINTS ===")
for i, h in enumerate(stories[:40]):
    url = h.get("url") or ("https://news.ycombinator.com/item?id=" + h["objectID"])
    out("%02d | id=%s | pts=%s | cmt=%s | by=%s | %s | %s" % (
        i + 1, h["objectID"], h.get("points"), h.get("num_comments"), h.get("author"),
        datetime.fromtimestamp(h["created_at_i"], timezone.utc).strftime("%d %H:%M"), h.get("title", "")))
    out("      %s" % url)

# ---------- keyword triage ----------
KW_WORLD = ["russia", "ukrain", "israel", "gaza", "iran", "china", "chinese", "beijing", "eu ", "europe",
            "brussels", "trump", "white house", "senate", "congress", "president", "election", "vote",
            "law", "court", "sue", "sued", "sues", "lawsuit", "ban", "bans", "banned", "regulat",
            "sanction", "war", "military", "nato", "government", "state department", "immigration",
            "privacy", "police", "supreme court", "tariff", "politics", "ministry", "parliament",
            "korea", "japan", "india", "africa", "mexico", "brazil", "un ", "united nations", "treaty",
            "speech", "protest", "attack", "prison", "censor", "surveillance", "civil"]
KW_ECON = ["ipo", "stock", "market", "inflation", "fed ", "federal reserve", "interest rate", "economy",
           "layoff", "layoff", "acquisition", "acquire", "billion", "funding", "raises", "raised",
           "valued", "valuation", "price", "oil", "energy", "profit", "revenue", "euro", "dollar",
           "openai", "nvidia", "a16z", "venture", "startup raises", "budget", "debt", "ipo", "merger"]
KW_SCI = ["quantum", "physic", "cancer", "brain", "dna", "gene", "space", "nasa", "mars", "moon",
          "fusion", "climate", "carbon", "vaccine", "protein", "telescope", "asteroid", "solar",
          "medicine", "clinical", "trial", "fossil", "dinosaur", "particle"]

def triage(title_tag, kws):
    out("")
    out("=== KEYWORD TRIAGE: %s ===" % title_tag)
    for h in stories:
        t = (h.get("title") or "").lower()
        hits = [k for k in kws if k in t]
        if hits:
            out("id=%s pts=%s cmt=%s | %s | kw=%s" % (h["objectID"], h.get("points"), h.get("num_comments"),
                                                      h.get("title"), ",".join(hits[:5])))
triage("WORLD/POLICY", KW_WORLD)
triage("ECON/MARKETS", KW_ECON)
triage("SCIENCE", KW_SCI)

out("")
out("=== SHOW HN IN WINDOW (pts>=30) ===")
for h in stories:
    t = h.get("title") or ""
    if t.lower().startswith("show hn") and h.get("points", 0) >= 30:
        out("id=%s pts=%s cmt=%s | %s" % (h["objectID"], h.get("points"), h.get("num_comments"), t))

out("")
out("=== ASK HN IN WINDOW (pts>=30) ===")
for h in stories:
    t = h.get("title") or ""
    if t.lower().startswith("ask hn") and h.get("points", 0) >= 30:
        out("id=%s pts=%s cmt=%s | %s" % (h["objectID"], h.get("points"), h.get("num_comments"), t))

# ---------- top stories detail ----------
def striphtml(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

out("")
out("=== TOP 15 STORY DETAILS (story text + top comments) ===")
for i, h in enumerate(stories[:15]):
    oid = h["objectID"]
    it = jload("hn_item_%s.json" % oid)
    out("")
    out("--- #%d id=%s pts=%s cmt=%s | %s" % (i + 1, oid, h.get("points"), h.get("num_comments"), h.get("title")))
    if h.get("url"):
        out("    url: %s" % h["url"])
    if it:
        st = striphtml(it.get("text", "") or "")
        if st:
            out("    STORYTEXT: %s" % st[:800])
        for ci, c in enumerate((it.get("children") or [])[:6]):
            ct = striphtml(c.get("text", "") or "")
            if ct:
                out("    C%d [%s] (replies=%s): %s" % (ci + 1, c.get("author"), len(c.get("children") or []), ct[:650]))

# ---------- GitHub ----------
out("")
out("=== GITHUB BREAKOUT REPOS (created 2026-11-11, by stars) ===")
j = jload("gh_day.json")
if j:
    out("total_count=%s" % j.get("total_count"))
    for r in j.get("items", [])[:20]:
        out("stars=%s | %s | lang=%s | %s" % (r.get("stargazers_count"), r.get("full_name"),
                                              r.get("language"), (r.get("description") or "")[:170]))
        out("    %s" % r.get("html_url"))
else:
    out("NO DATA")

# ---------- France24 ----------
out("")
out("=== FRANCE24 RSS ===")
p = os.path.join(OUT, "rss_france24.xml")
if os.path.exists(p):
    try:
        root = ET.parse(p).getroot()
        items = root.findall(".//item")
        out("items=%d" % len(items))
        inwin = []
        latest = []
        for it in items:
            t = (it.findtext("title") or "").strip()
            d = (it.findtext("pubDate") or "").strip()
            link = (it.findtext("link") or "").strip()
            try:
                dt = eut.parsedate_to_datetime(d).astimezone(timezone.utc)
            except Exception:
                dt = None
            if dt:
                latest.append(dt)
                if T0 <= dt.timestamp() < T1:
                    inwin.append((dt, t, link))
        if latest:
            out("newest item: %s | oldest item: %s" % (max(latest).isoformat(), min(latest).isoformat()))
        out("IN-WINDOW items=%d" % len(inwin))
        for dt, t, link in inwin[:40]:
            out("  %s | %s | %s" % (dt.strftime("%H:%M"), t, link))
        if not inwin:
            out("(most recent 10 titles, for freshness reference)")
            for it in items[:10]:
                out("  %s | %s" % ((it.findtext("pubDate") or "").strip(), (it.findtext("title") or "").strip()))
    except Exception as e:
        out("PARSE ERROR %s" % e)

# ---------- Firebase cross-check ----------
out("")
out("=== FIREBASE TOP STORIES CROSS-CHECK (snapshot 2026-11-12 ~08:10 UTC) ===")
j = jload("hn_firebase_topstories.json")
if j:
    for rank, oid in enumerate(j[:30]):
        it = jload("hn_firebase_item_%s.json" % oid)
        if it:
            inwin = T0 < it.get("time", 0) < T1
            out("%02d id=%s in_window=%s pts=%s cmt=%s | %s" % (
                rank + 1, oid, inwin, it.get("score"), it.get("descendants"), it.get("title")))

# ---------- arXiv note ----------
out("")
out("=== ARXIV STATUS ===")
for fn in ["arxiv_csai.xml", "arxiv_cslg.xml"]:
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        txt = open(p, encoding="utf-8", errors="replace").read()
        n_items = txt.count("<item>")
        m = re.search(r"<lastBuildDate>([^<]+)</lastBuildDate>", txt)
        out("%s items=%d lastBuild=%s" % (fn, n_items, m.group(1) if m else "?"))
NS = {"a": "http://www.w3.org/2005/Atom"}
for tag in ["csAI", "csLG"]:
    p = os.path.join(OUT, "arxiv_api2_%s.xml" % tag)
    if os.path.exists(p):
        root = ET.parse(p).getroot()
        entries = root.findall("a:entry", NS)
        out("%s: 100 most-recent-updated entries; newest published=%s count with published 2026-11-11 = %d" % (
            tag, entries[0].findtext("a:published", "", NS) if entries else "?",
            sum(1 for e in entries if (e.findtext("a:published", "", NS) or "").startswith("2026-11-11"))))
        out("--- newest %s entries (adjacent batch, 2026-11-10 19:00 UTC) ---" % tag)
        for e in entries[:12]:
            if (e.findtext("a:published", "", NS) or "").startswith("2026-11-10"):
                eid = e.findtext("a:id", "", NS).replace("http://arxiv.org/abs/", "")
                ttl = (e.findtext("a:title", "", NS) or "").strip().replace("\n", " ")
                smry = (e.findtext("a:summary", "", NS) or "").strip().replace("\n", " ")
                out("  %s | %s | %s" % (eid, ttl[:120], smry[:200]))

txt = "\n".join(lines)
with open(os.path.join(OUT, "analysis_digest.txt"), "w", encoding="utf-8") as f:
    f.write(txt)
print("digest written, chars:", len(txt), "lines:", len(lines))
