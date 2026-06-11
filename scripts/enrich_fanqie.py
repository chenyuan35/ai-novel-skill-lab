#!/usr/bin/env python3
"""Enrich Fanqie (番茄) novels with word count, genre, status from detail pages."""
import requests, sqlite3, json, time, re

DB_PATH = "/root/novel-crawler/benchmark.db"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get all fanqie novels
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='番茄' ORDER BY id")
rows = c.fetchall()
print(f"Fanqie novels to enrich: {len(rows)}")

enriched = 0
error_count = 0
wc_found = 0
genre_found = 0

for i, (nid, novel_id, name) in enumerate(rows):
    try:
        url = f"https://fanqienovel.com/page/{novel_id}"
        r = S.get(url, timeout=15)
        html = r.text

        # Detect error page
        if len(html) < 1000 or "Page Not Found" in html or "页面不存在" in html:
            error_count += 1
            c.execute("UPDATE novels SET raw_data=? WHERE id=?",
                      (json.dumps({"error": "page_not_found"}), nid))
            conn.commit()
            print(f"  [{i+1}/{len(rows)}] id={nid} {name[:20]:20s} ERROR PAGE")
            time.sleep(0.5)
            continue

        wc = 0
        wc_disp = ""
        genre = ""
        status_text = ""
        desc = ""
        author = ""
        is_comp = 0

        # Word count: "wordNumber":2026794
        wc_match = re.search(r'"wordNumber"\s*:\s*(\d+)', html)
        if wc_match:
            wc = int(wc_match.group(1))
            # Fanqie uses character count (similar to word count)
            if wc >= 10000:
                wan = wc / 10000
                if wan >= 100:
                    wc_disp = f"{wan:.0f}万字"
                else:
                    wc_disp = f"{wan:.1f}万字"
            else:
                wc_disp = f"{wc}字"
            wc_found += 1

        # Genre: "completeCategory":"女生/古代言情/宫闱宅斗"
        genre_match = re.search(r'"completeCategory"\s*:\s*"([^"]+)', html)
        if not genre_match:
            genre_match = re.search(r'"category"\s*:\s*"([^"]+)', html)
        if genre_match:
            raw_genre = genre_match.group(1)
            genre = raw_genre.replace("\\u002F", "/").replace("\\/", "/")
            genre_found += 1

        # Status: "creationStatus":0
        status_match = re.search(r'"creationStatus"\s*:\s*(\d+)', html)
        if status_match:
            cs = int(status_match.group(1))
            status_text = "连载中" if cs == 0 else "已完结" if cs == 1 else str(cs)
            is_comp = 1 if cs == 1 else 0
        else:
            # Try text-based status
            s2 = re.search(r'"creationStatus"\s*:\s*"([^"]+)"', html)
            if s2:
                status_text = s2.group(1)
                is_comp = 1 if ("完结" in status_text or "finish" in status_text.lower()) else 0

        # Author: "author":"..."
        author_match = re.search(r'"author"\s*:\s*"([^"]+)', html)
        if author_match:
            author = author_match.group(1)

        # Description: "abstract":"..."
        desc_match = re.search(r'"abstract"\s*:\s*"([^"]+)', html)
        if desc_match:
            desc = desc_match.group(1)[:500]

        # Preserve existing tags
        c.execute("SELECT tags FROM novels WHERE id=?", (nid,))
        existing = c.fetchone()
        if existing and existing[0]:
            tags = json.loads(existing[0])
        else:
            tags = []
        tags_json = json.dumps(tags, ensure_ascii=False)

        c.execute("""UPDATE novels SET genre=?, status=?, word_count=?, word_count_display=?,
            is_completed=?, author=?, description=?, tags=?, raw_data=? WHERE id=?""",
            (genre, status_text, wc, wc_disp, is_comp, author, desc, tags_json,
             json.dumps({"enriched": True}, ensure_ascii=False), nid))
        conn.commit()
        enriched += 1

        print(f"  [{i+1}/{len(rows)}] id={nid} {name[:20]:20s} wc={wc_disp:12s} genre={genre[:20]:20s} status={status_text}")

    except Exception as e:
        print(f"  ERROR id={nid} {name}: {e}")
        error_count += 1

    time.sleep(0.5)

print(f"\n{'='*50}")
print(f"Done: {enriched} enriched, {error_count} errors")
print(f"  Word count found: {wc_found}/{len(rows)}")
print(f"  Genre found: {genre_found}/{len(rows)}")

c.execute("SELECT COUNT(*) FROM novels WHERE platform='番茄' AND word_count>0")
w = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM novels WHERE platform='番茄' AND genre!=''")
g = c.fetchone()[0]
print(f"  DB result: Word count: {w}, Genre: {g}")
conn.close()
