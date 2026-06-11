#!/usr/bin/env python3
"""Enrich word_count for Fanqie novels from book detail page SSR data."""
import requests, sqlite3, json, time, os, sys

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "novel-crawler", "benchmark.db"))
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

def extract_ssr(html):
    idx = html.find("window.__INITIAL_STATE__")
    if idx < 0: return None
    start = html.find("{", idx)
    if start < 0: return None
    depth, i = 0, start
    while i < len(html):
        if html[i] == "{": depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0: break
        i += 1
    return json.loads(html[start:i+1])

conn = sqlite3.connect(DB_PATH)
rows = conn.execute(
    "SELECT id, novel_id, novel_name FROM novels WHERE platform='番茄' AND (word_count IS NULL OR word_count = 0) ORDER BY id"
).fetchall()

print(f"Novels needing word_count: {len(rows)}")
updated = 0
failed = 0

for r in rows:
    nid, novel_id, name = r
    url = f"https://fanqienovel.com/page/{novel_id}"
    try:
        resp = S.get(url, timeout=15)
        data = extract_ssr(resp.text)
        if not data:
            print(f"  [FAIL] id={nid} {name}: SSR extraction failed")
            failed += 1
            continue
        wc = data.get("page", {}).get("wordNumber", 0)
        if wc and int(wc) > 0:
            conn.execute("UPDATE novels SET word_count=? WHERE id=?", (int(wc), nid))
            conn.commit()
            updated += 1
            print(f"  [OK] id={nid} {name}: {wc}")
        else:
            print(f"  [FAIL] id={nid} {name}: wordNumber={wc}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] id={nid} {name}: {e}")
        failed += 1
    time.sleep(0.5)

print(f"\nDone: {updated} updated, {failed} failed")
conn.close()
