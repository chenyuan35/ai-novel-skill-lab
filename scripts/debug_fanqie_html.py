#!/usr/bin/env python3
"""Check SSR HTML for visible text patterns."""
import requests, re, sqlite3

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

c = sqlite3.connect("/root/novel-crawler/benchmark.db").cursor()
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='番茄' ORDER BY id")
rows = c.fetchall()

for nid, novel_id, name in rows[:5]:
    url = f"https://fanqienovel.com/page/{novel_id}"
    r = S.get(url, timeout=15)
    html = r.text
    print(f"\n=== id={nid} novel_id={novel_id} {name[:20]} (len={len(html)}) ===")

    wc_match = re.search(r'"wordNumber"\s*:\s*(\d+)', html)
    cs_match = re.search(r'"creationStatus"\s*:\s*(\d+)', html)
    cat_match = re.search(r'"completeCategory"\s*:\s*"([^"]+)', html)

    print(f"  wordNumber={wc_match.group(1) if wc_match else 'NOT FOUND'}")
    print(f"  creationStatus={cs_match.group(1) if cs_match else 'NOT FOUND'}")
    print(f"  completeCategory={cat_match.group(1) if cat_match else 'NOT FOUND'}")

    # Search for text patterns
    for pat in ["万字", "字", "连载", "完结", "作者", "分类"]:
        for m in re.finditer(pat, html):
            idx = html.find(m.group())
            ctx = html[max(0,idx-40):idx+40]
            print(f"  '{pat}' -> ...{ctx}...")
            break
        else:
            print(f"  '{pat}': NOT FOUND")

    for pat in ["bookId", "item_id", "novel_id"]:
        for m in re.finditer(pat, html):
            idx = html.find(m.group())
            ctx = html[max(0,idx-10):idx+60]
            print(f"  '{pat}' -> ...{ctx}...")
            break
        else:
            print(f"  '{pat}': NOT FOUND")
