import json, glob, re, collections

stories = {}
for f in glob.glob("raw/hn_bydate_p*.json"):
    d = json.load(open(f, encoding="utf-8"))
    for h in d.get("hits", []):
        stories[h["objectID"]] = h

ss = [s for s in stories.values() if s.get("created_at_i")]
print("stories:", len(ss))

def t(s): return (s.get("title") or "")

# 1. Nvidia / Huang cluster
nv = [s for s in ss if re.search(r"nvidia|huang|nvda", t(s), re.I)]
print("nvidia/huang titles:", len(nv), "| total points:", sum(s['points'] or 0 for s in nv))
for s in sorted(nv, key=lambda x: -(x['points'] or 0))[:22]:
    print("   ", s['objectID'], s['points'], s.get('num_comments'), s['created_at'][11:16], t(s)[:90])

# 2. ouster dupes
ou = [s for s in ss if re.search(r"oust|fire ceo|fire jensen", t(s), re.I)]
print("\nouster-title dupes:", len(ou), [ (s['objectID'], s['points'], s['created_at'][11:16]) for s in ou])

# 3. hourly distribution
hours = collections.Counter(s['created_at'][11:13] for s in ss)
print("\nhourly:", sorted(hours.items()))
late = sum(v for k, v in hours.items() if k >= "18")
print("after 18:00 UTC:", late, f"({late/len(ss)*100:.1f}%)")

# 4. AI vocabulary
pat = re.compile(r"\bai\b|agent|llm|gpt|claude|gemini|openai|anthropic|model|inference|prompt", re.I)
ai = [s for s in ss if pat.search(t(s))]
print("\nAI-ish titles:", len(ai), f"({len(ai)/len(ss)*100:.1f}%)")

# 5. containment vs capability verbs
contain = re.compile(r"\bban|bans|banned|block|blocks|restrict|outlaw|lawsuit|sues|crackdown|probe|investigat", re.I)
capab = re.compile(r"\blaunch|releases|introduc|announc|unveil|ships|open[- ]sourc|show hn", re.I)
c1 = [s for s in ss if contain.search(t(s))]
c2 = [s for s in ss if capab.search(t(s))]
print("containment-verb titles:", len(c1), "| capability-verb titles:", len(c2))

# 6. points buckets
b = collections.Counter()
for s in ss:
    p = s['points'] or 0
    b["0-4" if p < 5 else "5-19" if p < 20 else "20-49" if p < 50 else "50-199" if p < 200 else "200+"] += 1
print("\nbuckets:", dict(b))

# 7. domains in top 100
top = sorted(ss, key=lambda s: -(s['points'] or 0))[:100]
dom = collections.Counter()
for s in top:
    u = s.get("url") or ""
    m = re.match(r"https?://([^/]+)", u)
    dom[m.group(1).replace("www.", "") if m else "news.ycombinator.com"] += 1
print("\ntop100 domains:", dom.most_common(12))
print("github.com share of top100:", dom.get("github.com", 0))

# 8. self posts
print("\nAsk HN:", sum(1 for s in ss if t(s).startswith("Ask HN")),
      "| Show HN:", sum(1 for s in ss if t(s).startswith("Show HN")))

# 9. comment concentration
cm = sum(s.get('num_comments') or 0 for s in ss)
top10c = sum(s.get('num_comments') or 0 for s in sorted(ss, key=lambda s: -(s.get('num_comments') or 0))[:10])
print("total comments:", cm, "| top10 share:", f"{top10c/cm*100:.1f}%")

# 10. dead/flagged?
print("stories with 0 comments:", sum(1 for s in ss if not (s.get('num_comments') or 0)))
