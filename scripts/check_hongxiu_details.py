import requests, sqlite3, json, re

DB_PATH = "/root/novel-crawler/benchmark.db"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Find hongxiu novels with real names (not "书籍详情")
c.execute("SELECT novel_id, novel_name FROM novels WHERE platform='红袖' AND novel_name != '书籍详情' AND novel_name != '' AND novel_name NOT LIKE '%error%' LIMIT 5")
rows = c.fetchall()

for nid, name in rows:
    try:
        url = f"https://www.hongxiu.com/book/{nid}"
        r = S.get(url, timeout=15, allow_redirects=True)
        h = r.text

        # Check if it's an error page
        is_error = "出错啦" in h or "页面无法访问" in h

        print(f"\n===== {name} (id={nid}) len={len(h)} error={is_error} =====")

        if not is_error:
            # Look around "字" for word count
            idx = h.find("字")
            if idx > 0:
                ctx = h[max(0,idx-200):idx+50]
                print(f"  Context around '字':")
                print(f"  ...{ctx}...")

            # Look for og:meta
            for m in re.finditer(r'<meta[^>]*property="([^"]+)"[^>]*content="([^"]*)"', h):
                print(f"  meta: {m.group(1)} = {m.group(2)[:60]}")
        else:
            print(f"  Error page HTML snippet:")
            print(f"  {h[:500]}")
    except Exception as e:
        print(f"  ERROR: {e}")
