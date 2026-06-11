#!/usr/bin/env python3
"""Fixed enrichment for hongxiu detail pages.
Key fix: word count is inside HTML comments, chapter count via J-catalogCount."""
import requests, sqlite3, json, time, re, sys

DB_PATH = "/root/novel-crawler/benchmark.db"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

TROPE_KEYWORDS = ["重生", "校园", "青春", "学霸", "学生", "初三", "初中", "治愈", "成长", "穿书"]

def match_tropes(text):
    return [t for t in TROPE_KEYWORDS if t in text]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get ALL hongxiu novels, not just ones missing data - to re-enrich with fixed patterns
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='红袖' ORDER BY id")
rows = c.fetchall()
print(f"Hongxiu novels to enrich: {len(rows)}")

enriched = 0
error_count = 0
wc_found = 0
cc_found = 0

for i, (nid, novel_id, name) in enumerate(rows):
    try:
        r = S.get(f"https://www.hongxiu.com/book/{novel_id}", timeout=15)
        h = r.text

        # Detect error page (~1887 bytes with "出错啦！")
        is_error = "出错啦" in h or len(h) < 5000
        if is_error:
            error_count += 1
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(rows)}] id={nid} {name[:20]:20s} ERROR PAGE")
            # Mark as error in raw_data
            c.execute("UPDATE novels SET raw_data=? WHERE id=?",
                     (json.dumps({"error": "page_not_found"}, ensure_ascii=False), nid))
            conn.commit()
            time.sleep(0.3)
            continue

        genre = ""; status_text = ""; author = ""; desc = ""
        wc = 0; wc_disp = ""; cc = 0

        # og: meta tags (already worked fine)
        for m in re.finditer(r'<meta\s+property="([^"]+)"\s+content="([^"]*)"', h):
            p, val = m.group(1), m.group(2).strip()
            if p == "og:novel:category": genre = val
            elif p == "og:novel:author": author = val
            elif p == "og:novel:status": status_text = val

        # Word count from HTML comment: <!-- <span>36</span><em>万字</em> -->
        wc_match = re.search(r'<!--.*?<span>([\d.]+)</span><em>(万字|千字)</em>', h)
        if wc_match:
            num_str = wc_match.group(1)
            unit = wc_match.group(2)
            try:
                if "万" in unit:
                    wc = int(float(num_str) * 10000)
                else:
                    wc = int(num_str)
                wc_disp = f"{num_str}{unit}"
            except ValueError:
                pass

        # Chapter count from catalog: <span id="J-catalogCount">(341章)</span>
        cc_match = re.search(r'J-catalogCount[^>]*>\((\d+)章\)', h)
        if cc_match:
            cc = int(cc_match.group(1))

        # Description from meta
        desc_match = re.search(r'<meta\s+name="description"[^>]*content="([^"]*)"', h)
        if desc_match:
            desc = desc_match.group(1).strip()[:500]

        is_comp = 1 if ("完结" in status_text or "完成" in status_text) else 0
        tags = match_tropes(name + " " + genre)
        tags_json = json.dumps(tags, ensure_ascii=False)

        c.execute("""UPDATE novels SET genre=?, status=?, word_count=?, word_count_display=?,
            chapter_count=?, description=?, is_completed=?, author=?, tags=?, raw_data=? WHERE id=?""",
            (genre, status_text, wc, wc_disp, cc, desc, is_comp, author, tags_json,
             json.dumps({"enriched": True}, ensure_ascii=False), nid))
        conn.commit()
        enriched += 1
        if wc: wc_found += 1
        if cc: cc_found += 1

        if (i + 1) % 10 == 0 or wc or cc:
            print(f"  [{i+1}/{len(rows)}] id={nid} {name[:20]:20s} genre={genre:8s} wc={wc_disp:10s} cc={cc:3d}")

    except Exception as e:
        print(f"  ERROR id={nid} {name}: {e}")

    time.sleep(0.3)

# Summary
print(f"\n{'='*50}")
print(f"Done: {enriched} enriched, {error_count} error pages")
print(f"  Word count found: {wc_found}/{len(rows)}")
print(f"  Chapter count found: {cc_found}/{len(rows)}")
print(f"  Error pages: {error_count}/{len(rows)}")

c.execute("SELECT COUNT(*) FROM novels WHERE platform='红袖' AND genre!=''")
g = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM novels WHERE platform='红袖' AND word_count>0")
w = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM novels WHERE platform='红袖' AND chapter_count>0")
ch = c.fetchone()[0]
print(f"  Genre: {g}, Word count: {w}, Chapter count: {ch}")
conn.close()
