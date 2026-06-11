#!/usr/bin/env python3
"""Enrich JJWXC novels with word count, genre, status, chapter count."""
import requests, sqlite3, json, time, re

DB_PATH = "/root/novel-crawler/benchmark.db"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get all JJWXC novels
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='晋江文学城' ORDER BY id")
rows = c.fetchall()
print(f"JJWXC novels to enrich: {len(rows)}")

enriched = 0; error_count = 0; wc_found = 0; cc_found = 0; genre_found = 0

for i, (nid, novel_id, name) in enumerate(rows):
    try:
        url = f"https://www.jjwxc.net/onebook.php?novelid={novel_id}"
        r = S.get(url, timeout=15)
        r.encoding = "gb18030"
        h = r.text

        # Detect error/missing page (JJWXC returns 200 for non-existent too)
        if len(h) < 2000 or "该书不存在" in h or "没有找到" in h:
            error_count += 1
            c.execute("UPDATE novels SET raw_data=? WHERE id=?",
                      (json.dumps({"error": "page_not_found"}), nid))
            conn.commit()
            print(f"  [{i+1}/{len(rows)}] id={nid} {name[:20]:20s} ERROR PAGE")
            time.sleep(0.5)
            continue

        wc = 0; wc_disp = ""; cc = 0
        genre = ""; status_text = ""; author = ""

        # Word count: <span itemprop="wordCount">946030字</span>
        wc_match = re.search(r'itemprop="wordCount">(\d+)字', h)
        if wc_match:
            wc_val = int(wc_match.group(1))
            wc_disp = f"{wc_val}字"
            # Convert to wan for consistency
            if wc_val >= 10000:
                wan = wc_val / 10000
                wc = int(wan * 10000)  # Keep in character count
            else:
                wc = wc_val
            wc_found += 1

        # Genre: <span itemprop="genre">原创-纯爱-近代现代-爱情</span> (may span multiple lines)
        genre_match = re.search(r'itemprop="genre">\s*(.*?)\s*</span>', h, re.DOTALL)
        if genre_match:
            genre = genre_match.group(1).strip()
            genre_found += 1

        # Status: <span itemprop="updataStatus"><font color=red>完结</font></span>
        status_match = re.search(r'itemprop="updataStatus">.*?(完结|连载中|暂停)', h)
        if status_match:
            status_text = status_match.group(1)

        is_comp = 1 if "完结" in status_text else 0

        # Chapter count: count rows
        chapters = re.findall(r'<tr itemprop="chapter"', h)
        if chapters:
            cc = len(chapters)
            cc_found += 1

        # Author from og:meta if available
        author_match = re.search(r'<meta\s+property="og:novel:author"\s+content="([^"]*)"', h)
        if author_match:
            author = author_match.group(1)

        # Description from meta
        desc_match = re.search(r'<meta\s+name="description"[^>]*content="([^"]*)"', h)
        desc = desc_match.group(1).strip()[:500] if desc_match else ""

        # Trope matching from existing tags (preserve)
        c.execute("SELECT tags FROM novels WHERE id=?", (nid,))
        existing_tags_raw = c.fetchone()
        if existing_tags_raw and existing_tags_raw[0]:
            tags = json.loads(existing_tags_raw[0])
        else:
            tags = []

        tags_json = json.dumps(tags, ensure_ascii=False)

        c.execute("""UPDATE novels SET genre=?, status=?, word_count=?, word_count_display=?,
            chapter_count=?, is_completed=?, author=?, description=?, tags=?, raw_data=? WHERE id=?""",
            (genre, status_text, wc, wc_disp, cc, is_comp, author, desc, tags_json,
             json.dumps({"enriched": True, "wordCount_raw": wc_val if wc_match else 0}), nid))
        conn.commit()
        enriched += 1

        print(f"  [{i+1}/{len(rows)}] id={nid} {name[:20]:20s} wc={wc_disp:12s} cc={cc:3d} genre={genre[:16]:16s} status={status_text:4s}")

    except Exception as e:
        print(f"  ERROR id={nid} {name}: {e}")
        error_count += 1

    time.sleep(0.5)

print(f"\n{'='*50}")
print(f"Done: {enriched} enriched, {error_count} errors")
print(f"  Word count found: {wc_found}/{len(rows)}")
print(f"  Chapter count found: {cc_found}/{len(rows)}")
print(f"  Genre found: {genre_found}/{len(rows)}")

c.execute("SELECT COUNT(*) FROM novels WHERE platform='晋江文学城' AND word_count>0")
w = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM novels WHERE platform='晋江文学城' AND chapter_count>0")
ch = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM novels WHERE platform='晋江文学城' AND genre!=''")
g = c.fetchone()[0]
print(f"  DB result: Word count: {w}, Chapter count: {ch}, Genre: {g}")
conn.close()
