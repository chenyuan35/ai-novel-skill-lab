#!/usr/bin/env python3
"""Test Fanqie directory API with fanqie web book IDs vs snssdk book IDs."""
import requests, json, sqlite3, os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "novel-crawler", "benchmark.db"))
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

c = sqlite3.connect(DB_PATH)
c.row_factory = sqlite3.Row

# Grab 3 novels with both fanqie web ID (novel_id) and snssdk data
rows = c.execute("""
    SELECT id, novel_id, novel_name, raw_data FROM novels
    WHERE platform='番茄' AND source='home_list' AND id <= 5
""").fetchall()

for r in rows:
    fanqie_web_id = r['novel_id']  # from fanqie SSR
    print(f"\n--- id={r['id']} {r['novel_name']} ---")
    print(f"  Fanqie web bookId: {fanqie_web_id}")

    # Try directory API with fanqie web ID
    r1 = S.get(f"https://fanqienovel.com/api/reader/directory/detail?bookId={fanqie_web_id}", timeout=10)
    if r1.status_code == 200:
        data = r1.json()
        d = data.get("data", {})
        total = d.get("totalChapterNum", 0)
        chapters = d.get("chapterListWithVolume", [])
        print(f"  Directory (web ID): {total} chapters, {len(chapters)} volumes")
        if total > 0 and chapters and len(chapters[0]) > 0:
            first = chapters[0][0]
            item_id = first.get("itemId", "")
            print(f"  First chapter itemId: {item_id}")
            # Try content API
            r2 = S.get("https://novel.snssdk.com/api/novel/book/reader/full/v1/", params={
                "device_platform": "android", "parent_enterfrom": "novel_channel_search.tab.",
                "aid": "2329", "platform_id": "1967",
                "group_id": str(item_id), "item_id": str(item_id),
            }, timeout=10)
            if r2.status_code == 200:
                nd = r2.json().get("data", {}).get("novel_data", {})
                wc = nd.get("word_number")
                print(f"  Content API word_number: {wc}")
                if not wc:
                    print(f"  NovelData keys: {list(nd.keys()) if nd else 'None'}")
            else:
                print(f"  Content API: HTTP {r2.status_code}")
    else:
        print(f"  Directory (web ID): HTTP {r1.status_code}")

print("\n--- Done ---")
