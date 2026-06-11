#!/usr/bin/env python3
"""Enrich hongxiu novels with detail page data: genre, word count, chapter count."""
import requests, sqlite3, json, time, re, sys

DB_PATH = "/root/novel-crawler/benchmark.db"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

TROPE_KEYWORDS = ["重生", "校园", "青春", "学霸", "学生", "初三", "初中", "治愈", "成长", "穿书"]

def match_tropes(text):
    return [t for t in TROPE_KEYWORDS if t in text]

# 1) Enrich hongxiu novels missing genre or word_count
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='红袖' AND (genre='' OR word_count=0) LIMIT 80")
rows = c.fetchall()
print(f"Hongxiu novels needing enrichment: {len(rows)}")

for i, (nid, novel_id, name) in enumerate(rows):
    try:
        r = S.get(f"https://www.hongxiu.com/book/{novel_id}", timeout=15)
        h = r.text
        genre = ""; wc = 0; wc_disp = ""; cc = 0; desc = ""; status_text = ""; author = ""

        # og: meta tags
        for m in re.finditer(r'<meta\s+property="([^"]+)"\s+content="([^"]*)"', h):
            p, val = m.group(1), m.group(2).strip()
            if p == "og:novel:category": genre = val
            elif p == "og:novel:author": author = val
            elif p == "og:novel:status": status_text = val

        # Word count from text like "累计字数: 12.3万字"
        wc_match = re.search(r'(\d+[\.\d]*万?)字', h[:50000])
        if wc_match:
            wc_raw = wc_match.group(1)
            wc_disp = wc_raw + "字"
            if "万" in wc_raw:
                wc = int(float(wc_raw.replace("万", "")) * 10000)
            else:
                wc = int(wc_raw)

        # Chapter count
        ch_match = re.search(r'(\d+)章', h[:50000])
        if ch_match:
            cc = int(ch_match.group(1))

        # Description
        desc_match = re.search(r'<meta\s+name="description"[^>]*content="([^"]*)"', h)
        if desc_match:
            desc = desc_match.group(1).strip()[:500]

        is_comp = 1 if ("完结" in status_text or "完成" in status_text) else 0
        tags = match_tropes(name + " " + genre)

        c.execute("""UPDATE novels SET genre=?, status=?, word_count=?, word_count_display=?,
            chapter_count=?, description=?, is_completed=?, author=?, tags=? WHERE id=?""",
            (genre, status_text, wc, wc_disp, cc, desc, is_comp, author, json.dumps(tags, ensure_ascii=False), nid))
        conn.commit()
        if wc or cc or genre:
            print(f"  OK id={nid} [{name:20s}] wc={wc_disp:10s} ch={cc:3d} genre={genre}")
    except Exception as e:
        print(f"  ERROR id={nid} {name}: {e}")
    time.sleep(0.3)

c.execute("SELECT COUNT(*) FROM novels WHERE platform='红袖' AND genre!=''")
done = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM novels WHERE platform='红袖' AND word_count>0")
wc_done = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM novels WHERE platform='红袖'")
total = c.fetchone()[0]
print(f"\nHongxiu enrichment done: {done}/{total} have genre, {wc_done}/{total} have word_count")

# 2) JJWXC chapter count fix
c.execute("SELECT id, novel_id, novel_name, raw_data FROM novels WHERE platform='晋江文学城' AND chapter_count=0 LIMIT 10")
jj_rows = c.fetchall()
if jj_rows:
    print(f"\nJJWXC chapter count fix: checking {len(jj_rows)} novels")
    for nid, novel_id, name, raw_json in jj_rows[:3]:
        try:
            url = f"https://www.jjwxc.net/onebook.php?novelid={novel_id}"
            r = S.get(url, timeout=15)
            r.encoding = "gb18030"
            h = r.text
            # Look for chapter count in various patterns
            for pat in [r'共(\d+)章', r'章节数[：:](\d+)', r'(\d+)章\s', r'<span[^>]*class="num">(\d+)</span>',
                        r'<a[^>]*id="[^"]*chapter[^"]*"[^>]*>(\d+)', r'<em[^>]*>(\d+)</em>.*章']:
                m = re.search(pat, h)
                if m:
                    print(f"  {name}: found '{pat[:40]}' -> {m.group(1)}")
                    break
            else:
                print(f"  {name}: no chapter count pattern found")
                # Show HTML around "章" for debugging
                for m2 in re.finditer(r'.{0,80}章.{0,80}', h[:30000]):
                    print(f"    context: ...{m2.group().strip()[:120]}...")
                break  # Just debug first one
        except Exception as e:
            print(f"  ERROR {name}: {e}")

conn.close()
