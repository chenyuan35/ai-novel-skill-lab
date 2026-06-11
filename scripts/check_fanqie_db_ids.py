#!/usr/bin/env python3
"""Check Fanqie novel_ids in DB and test page content."""
import sqlite3, requests, re

c = sqlite3.connect("/root/novel-crawler/benchmark.db").cursor()
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='番茄' ORDER BY id LIMIT 5")
print("First 5 novels:")
for r in c.fetchall():
    print(f"  id={r[0]} novel_id={r[1]} name={r[2][:30]}")
    # Test page
    url = f"https://fanqienovel.com/page/{r[1]}"
    resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    html = resp.text
    print(f"    page_len={len(html)}")
    wc = re.search(r'"wordNumber"\s*:\s*(\d+)', html)
    cs = re.search(r'"creationStatus"\s*:\s*(\d+)', html)
    cat = re.search(r'"completeCategory"\s*:\s*"([^"]+)', html)
    print(f"    wordNumber={wc.group(1) if wc else 'NOT FOUND'}")
    print(f"    creationStatus={cs.group(1) if cs else 'NOT FOUND'}")
    print(f"    completeCategory={cat.group(1) if cat else 'NOT FOUND'}")
