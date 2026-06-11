#!/usr/bin/env python3
"""Fix garbled novel names & enrich metadata from fanqie book detail page SSR."""
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
# Only fix garbled-name novels (from rank page — IDs 28-37)
rows = conn.execute(
    "SELECT id, novel_id, novel_name, source FROM novels WHERE platform='番茄' AND source='rank' ORDER BY id"
).fetchall()

print(f"Total Fanqie novels: {len(rows)}")
updated_names = 0
fail = 0

for r in rows:
    nid, novel_id, old_name, src = r
    url = f"https://fanqienovel.com/page/{novel_id}"
    try:
        resp = S.get(url, timeout=15)
        data = extract_ssr(resp.text)
        if not data:
            print(f"  [SKIP] id={nid}: SSR extraction failed")
            fail += 1
            continue
        page = data.get("page", {})
        correct_name = page.get("bookName", "")
        if not correct_name:
            print(f"  [SKIP] id={nid}: empty bookName")
            fail += 1
            continue

        # Update name + metadata from page
        conn.execute("""UPDATE novels SET
            novel_name=?, author=?, description=?,
            category=?, creation_status=?, genre=?,
            word_count=?
            WHERE id=?""", (
            correct_name,
            page.get("author", ""),
            (page.get("description", "") or "")[:500],
            page.get("categoryV2", ""),
            page.get("creationStatus"),
            page.get("category", ""),
            int(page.get("wordNumber", 0)),
            nid
        ))
        conn.commit()
        if correct_name != old_name:
            print(f"  [NAME FIX] id={nid}: '{old_name}' -> '{correct_name}'")
            updated_names += 1
        else:
            print(f"  [OK] id={nid}: {correct_name}")
    except Exception as e:
        print(f"  [FAIL] id={nid}: {e}")
        fail += 1
    time.sleep(0.5)

print(f"\nDone: {updated_names} names fixed, {fail} failed")
conn.close()
