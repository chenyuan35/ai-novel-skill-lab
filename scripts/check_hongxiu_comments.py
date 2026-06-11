"""Check hongxiu HTML comment structure around word count and other data."""
import requests, re, sqlite3

DB_PATH = "/root/novel-crawler/benchmark.db"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT novel_id, novel_name FROM novels WHERE platform='红袖' AND novel_name != '书籍详情' LIMIT 3")
rows = c.fetchall()

for nid, name in rows:
    try:
        r = S.get(f"https://www.hongxiu.com/book/{nid}", timeout=15)
        h = r.text
        print(f"\n===== {name} (id={nid}) =====")

        # Extract ALL HTML comments
        for m in re.finditer(r'<!---->(.*?)<!---->', h, re.S):
            comment = m.group(1).strip()
            if comment and any(c in comment for c in "万字章"):
                print(f"  Comment: {comment}")

        # Also extract the full book-total section
        bt = re.search(r'<p\s+class="book-total[^"]*"[^>]*>(.*?)</p>', h, re.S)
        if bt:
            print(f"\n  book-total section:")
            print(f"  {bt.group(1)[:500]}")

        # Extract og:tags for comparison
        for m in re.finditer(r'<meta\s+property="([^"]+)"\s+content="([^"]*)"', h):
            print(f"  meta: {m.group(1)} = {m.group(2)[:60]}")

    except Exception as e:
        print(f"  ERROR: {e}")
