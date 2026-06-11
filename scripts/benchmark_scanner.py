#!/usr/bin/env python3
"""Multi-platform novel benchmark scanner for 重生校园青春/学霸/治愈 genre.
Platforms: hongxiu (红袖), fanqie (番茄), jjwxc (晋江)
Crawl on server only — no local execution."""
import requests, sqlite3, json, time, re, sys
from datetime import datetime

DB_PATH = "/root/novel-crawler/benchmark.db"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

TROPE_KEYWORDS = ["重生", "校园", "青春", "学霸", "学生", "初三", "初中", "治愈", "成长", "穿书"]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS novels (
        id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, novel_id TEXT, novel_name TEXT,
        author TEXT, description TEXT, genre TEXT, tags TEXT, status TEXT,
        chapter_count INTEGER, word_count INTEGER, word_count_display TEXT,
        rating REAL, total_clicks INTEGER, total_hits INTEGER, total_recommend INTEGER,
        is_completed INTEGER DEFAULT 0, source TEXT, search_keyword TEXT,
        crawled_at TEXT, raw_data TEXT, UNIQUE(platform, novel_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS trope_stats (
        trope TEXT PRIMARY KEY, count INTEGER DEFAULT 0, novels TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS scan_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, method TEXT,
        keyword TEXT, novels_found INTEGER, scanned_at TEXT)""")
    conn.commit()
    conn.close()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def match_tropes(text):
    return [t for t in TROPE_KEYWORDS if t in text]

def save_novel(conn, n):
    c = conn.cursor()
    try:
        c.execute("""INSERT OR IGNORE INTO novels (platform, novel_id, novel_name, author,
            description, genre, tags, status, chapter_count, word_count, word_count_display,
            is_completed, source, search_keyword, crawled_at, raw_data)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            n["platform"], n["novel_id"], n["novel_name"], n.get("author", ""),
            n.get("description", ""), n.get("genre", ""),
            json.dumps(n.get("tags", []), ensure_ascii=False),
            n.get("status", ""), n.get("chapter_count", 0), n.get("word_count", 0),
            n.get("word_count_display", ""), n.get("is_completed", 0),
            n.get("source", ""), n.get("search_keyword", ""),
            datetime.now().isoformat(), n.get("raw_data", "")
        ))
        if c.rowcount > 0:
            for tag in n.get("tags", []):
                c.execute("INSERT INTO trope_stats (trope, count) VALUES (?,1) ON CONFLICT(trope) DO UPDATE SET count=count+1", (tag,))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False

def log_scan(conn, platform, method, keyword, found):
    c = conn.cursor()
    c.execute("INSERT INTO scan_log (platform,method,keyword,novels_found,scanned_at) VALUES (?,?,?,?,?)",
              (platform, method, keyword, found, datetime.now().isoformat()))
    conn.commit()

# ── 红袖 (Hongxiu) ────────────────────────────────────────────

HONGXIU_RANK_TABS = {
    "综合": "https://www.hongxiu.com/rank",
    "点击": "https://www.hongxiu.com/rank/click",
    "推荐": "https://www.hongxiu.com/rank/recomm",
    "收藏": "https://www.hongxiu.com/rank/collect",
    "新书": "https://www.hongxiu.com/rank/up",
    "完本": "https://www.hongxiu.com/rank/finish",
}

def scrape_hongxiu_rank():
    """Scrape hongxiu rank pages for book IDs and names."""
    results = []
    for label, url in HONGXIU_RANK_TABS.items():
        try:
            r = S.get(url, timeout=15)
            books = re.findall(r'href="(/book/\d+)"[^>]*>([^<]+)</a>', r.text)
            seen = set()
            for href, title in books:
                name = title.strip()
                if not name or name in seen or len(name) < 2:
                    continue
                seen.add(name)
                novel_id = href.replace("/book/", "")
                tags = match_tropes(name)
                results.append({
                    "platform": "红袖",
                    "novel_id": novel_id,
                    "novel_name": name,
                    "source": "rank",
                    "search_keyword": f"rank_{label}",
                    "tags": tags,
                    "raw_data": json.dumps({"url": url, "rank_type": label}, ensure_ascii=False),
                })
        except Exception as e:
            print(f"  [红袖] rank/{label} ERROR: {e}")
        time.sleep(0.5)
    return results

def scrape_hongxiu_keyword(keyword):
    """Search hongxiu /so/{keyword} for books matching trope keywords."""
    results = []
    try:
        r = S.get(f"https://www.hongxiu.com/so/{keyword}", timeout=15)
        books = re.findall(r'href="(/book/\d+)"[^>]*>([^<]+)</a>', r.text)
        seen = set()
        for href, title in books:
            name = title.strip()
            if not name or name in seen or len(name) < 2:
                continue
            seen.add(name)
            novel_id = href.replace("/book/", "")
            tags = list(set(match_tropes(name) + [keyword]))
            results.append({
                "platform": "红袖",
                "novel_id": novel_id,
                "novel_name": name,
                "source": "keyword",
                "search_keyword": keyword,
                "tags": tags,
                "raw_data": json.dumps({"url": f"https://www.hongxiu.com/so/{keyword}"}, ensure_ascii=False),
            })
    except Exception as e:
        print(f"  [红袖] /so/{keyword} ERROR: {e}")
    return results

def enrich_hongxiu_detail(n):
    """Visit hongxiu detail page to fill in genre/status/word count from og: meta."""
    try:
        url = f"https://www.hongxiu.com/book/{n['novel_id']}"
        r = S.get(url, timeout=15)
        h = r.text
        # og: meta tags
        for og_key, field in [
            ("og:novel:book_name", "novel_name"),
            ("og:novel:author", "author"),
            ("og:novel:category", "genre"),
            ("og:novel:status", "status"),
            ("og:novel:latest_chapter_name", None),
        ]:
            m = re.search(rf'<meta\s+property=["\']{og_key}["\']\s+content=["\']([^"\']*)["\']', h)
            if m and field:
                n[field] = m.group(1).strip()
        # is_completed from status
        if "连载" in n.get("status", ""):
            n["is_completed"] = 0
        elif "完结" in n.get("status", "") or "完成" in n.get("status", ""):
            n["is_completed"] = 1
        # Word count from "累计字数"
        m = re.search(r'(\d+[\.\d]*万?)字', h[:50000])
        if m:
            wc_text = m.group(1)
            n["word_count_display"] = wc_text + "字"
            if "万" in wc_text:
                n["word_count"] = int(float(wc_text.replace("万", "")) * 10000)
            else:
                n["word_count"] = int(wc_text)
        # Chapter count from "xxx章"
        m = re.search(r'(\d+)章', h[:50000])
        if m:
            n["chapter_count"] = int(m.group(1))
        # Description from meta description
        m = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', h)
        if m:
            n["description"] = m.group(1).strip()[:500]
        # Recalculate trope matches with enriched name
        n["tags"] = match_tropes(n.get("novel_name", "") + " " + n.get("genre", ""))
        n["raw_data"] = json.dumps({"detail_fetched": True, "url": url}, ensure_ascii=False)
    except Exception as e:
        pass  # Non-fatal — keep partial data
    return n

# ── 番茄 (Fanqie) ─────────────────────────────────────────────

def extract_ssr(html):
    """Extract window.__INITIAL_STATE__ JSON via brace matching."""
    idx = html.find("window.__INITIAL_STATE__")
    if idx < 0:
        return None
    start = html.find("{", idx)
    if start < 0:
        return None
    depth = 0
    end = start
    for i in range(start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
        if depth == 0:
            end = i + 1
            break
    return json.loads(html[start:end])

def scrape_fanqie_home():
    """Scrape fanqie home page lists (girlList, boyList, weekList, editorList)."""
    results = []
    try:
        r = S.get("https://fanqienovel.com/", timeout=15)
        data = extract_ssr(r.text)
        if not data:
            print("  [番茄] 首页 SSR提取失败")
            return results
        home = data.get("home", {})
        for list_name in ["girlList", "boyList", "weekList", "editorList"]:
            items = home.get(list_name, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("bookName", "") or ""
                if not name or len(name) < 2:
                    continue
                novel_id = str(item.get("bookId", ""))
                if not novel_id:
                    continue
                tags = match_tropes(name)
                genre = item.get("category", "")
                tags = list(set(tags + match_tropes(genre)))
                results.append({
                    "platform": "番茄",
                    "novel_id": novel_id,
                    "novel_name": name,
                    "author": item.get("author", ""),
                    "description": item.get("abstract", "")[:500],
                    "genre": genre,
                    "source": "home_list",
                    "search_keyword": list_name,
                    "tags": tags,
                    "raw_data": json.dumps({"list": list_name}, ensure_ascii=False),
                })
    except Exception as e:
        print(f"  [番茄] 首页 ERROR: {e}")
    return results

def scrape_fanqie_rank():
    """Scrape fanqie rank page — has wordNumber, readCount, etc."""
    results = []
    try:
        r = S.get("https://fanqienovel.com/rank", timeout=15)
        data = extract_ssr(r.text)
        if not data:
            print("  [番茄] 排行页 SSR提取失败")
            return results
        rank = data.get("rank", {})
        for rk, rv in rank.items():
            if not isinstance(rv, list):
                continue
            for item in rv:
                if not isinstance(item, dict):
                    continue
                name = item.get("bookName", "") or ""
                if not name or len(name) < 2:
                    continue
                novel_id = str(item.get("bookId", ""))
                if not novel_id:
                    continue
                genre = item.get("category", "")
                tags = list(set(match_tropes(name) + match_tropes(genre)))
                word_count = 0
                wc_raw = item.get("wordNumber", 0) or 0
                try:
                    word_count = int(wc_raw)
                except (ValueError, TypeError):
                    pass
                results.append({
                    "platform": "番茄",
                    "novel_id": novel_id,
                    "novel_name": name,
                    "author": item.get("author", ""),
                    "description": item.get("abstract", "")[:500],
                    "genre": genre,
                    "word_count": word_count,
                    "word_count_display": f"{word_count:,}" if word_count else "",
                    "status": item.get("creationStatus", ""),
                    "chapter_count": item.get("lastChapterItemId", 0) or None,
                    "source": "rank",
                    "search_keyword": rk,
                    "tags": tags,
                    "is_completed": 1 if item.get("creationStatus") == "完结" else 0,
                    "raw_data": json.dumps({"rank_category": rk}, ensure_ascii=False),
                })
    except Exception as e:
        print(f"  [番茄] 排行页 ERROR: {e}")
    return results

# ── 晋江 (JJWXC) ───────────────────────────────────────────────

JJWXC_CATEGORIES = {
    "青春校园": 5,
    "游戏竞技": 8,
    "耽美": 14,
    "百合": 16,
}

def scrape_jjwxc_rank(cid=5, pages=5):
    """Scrape JJWXC monthly click rank for a category. cid=5 is 青春校园."""
    results = []
    for page in range(1, pages + 1):
        url = f"https://www.jjwxc.net/bookbase.php?orderstr=click_month&cid={cid}&page={page}"
        try:
            r = S.get(url, timeout=15)
            r.encoding = "gb18030"
            html = r.text
            for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
                nm = re.search(r'href="onebook\.php\?novelid=(\d+)"[^>]*>([^<]+)<', tr)
                if not nm:
                    continue
                nid, name = nm.group(1), nm.group(2).strip()
                if not name or len(name) < 2:
                    continue
                am = re.search(r'href="oneauthor\.php\?authorid=\d+"[^>]*>([^<]+)<', tr)
                author = am.group(1).strip() if am else ""
                tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
                # Columns: [0]=rank, [1]=novel (name+link), [2]=author, [3]=字数, [4]=收藏,
                #          [5]=积分, [6]=评论数, [7]=霸王票, [8]=文章类型
                if len(tds) < 5:
                    continue
                ch_count = 0
                # Chapter count may be in tds[3] or embedded in the name link
                # Also try to find in the novel name span
                m = re.search(r'<span[^>]*class=["\']?num["\']?[^>]*>(\d+)</span>', tr)
                if m:
                    ch_count = int(m.group(1))
                status = ""
                word_text = ""
                word_count = 0
                if len(tds) >= 5:
                    status = re.sub(r"<[^>]+>", "", tds[3]).strip() if len(tds) > 3 else ""
                    word_text = re.sub(r"<[^>]+>", "", tds[4]).strip() if len(tds) > 4 else ""
                    m = re.search(r"([\d,]+)", word_text)
                    if m:
                        word_count = int(m.group(1).replace(",", ""))
                tags = match_tropes(name + " " + author)
                if not tags:
                    continue
                results.append({
                    "platform": "晋江文学城",
                    "novel_id": nid,
                    "novel_name": name,
                    "author": author,
                    "status": status,
                    "chapter_count": ch_count,
                    "word_count": word_count,
                    "word_count_display": word_text,
                    "is_completed": 1 if "完结" in status else 0,
                    "tags": tags,
                    "source": "rank",
                    "search_keyword": f"rank_month_cid{cid}",
                    "raw_data": json.dumps({"url": url}, ensure_ascii=False),
                })
        except Exception as e:
            print(f"  [晋江] page {page} cid={cid} ERROR: {e}")
        time.sleep(1)
    return results

# ── 主流程 ─────────────────────────────────────────────────────

def run_scan(options=None):
    if options is None:
        options = {"hongxiu": True, "fanqie": True, "jjwxc": True, "detail_enrich": True}
    print("=" * 60)
    print(f"扫榜开始 {datetime.now().isoformat()}")
    print(f"选项: {json.dumps(options, ensure_ascii=False)}")
    print("=" * 60)
    init_db()
    conn = db()
    total = 0

    # ── 红袖 ──
    if options.get("hongxiu"):
        print("\n[1] 红袖排行...")
        hx_rank = scrape_hongxiu_rank()
        print(f"  排行: {len(hx_rank)} 本")
        for kw in TROPE_KEYWORDS:
            print(f"  /so/{kw}...", end=" ", flush=True)
            books = scrape_hongxiu_keyword(kw)
            hx_rank.extend(books)
            print(f"{len(books)} 本")
            time.sleep(0.5)
        print(f"  红袖总计: {len(hx_rank)} 本")
        if options.get("detail_enrich"):
            print("  补充详情页...")
            for i, n in enumerate(hx_rank):
                enrich_hongxiu_detail(n)
                if (i + 1) % 20 == 0:
                    print(f"    ...{i+1}/{len(hx_rank)} 完成")
                time.sleep(0.3)
        for n in hx_rank:
            if save_novel(conn, n):
                total += 1
        log_scan(conn, "红袖", "all", "rank+keyword", len(hx_rank))

    # ── 番茄 ──
    if options.get("fanqie"):
        print("\n[2] 番茄首页列表...")
        fq_home = scrape_fanqie_home()
        print(f"  首页: {len(fq_home)} 本")
        print("\n[3] 番茄排行...")
        fq_rank = scrape_fanqie_rank()
        print(f"  排行: {len(fq_rank)} 本")
        all_fq = fq_home + fq_rank
        for n in all_fq:
            if save_novel(conn, n):
                total += 1
        log_scan(conn, "番茄", "all", "home+rank", len(all_fq))

    # ── 晋江 ──
    if options.get("jjwxc"):
        print("\n[4] 晋江文学城排行...")
        jj = []
        for cat_name, cid in JJWXC_CATEGORIES.items():
            print(f"  {cat_name}(cid={cid})...")
            jj.extend(scrape_jjwxc_rank(cid=cid, pages=3))
        for n in jj:
            if save_novel(conn, n):
                total += 1
        log_scan(conn, "晋江文学城", "all", "rank_month", len(jj))

    # ── 统计 ──
    print("\n" + "=" * 60)
    print("扫榜完成 — 统计")
    print("=" * 60)
    print(f"本次新增: {total} 本")
    c = conn.cursor()
    c.execute("SELECT platform, COUNT(*) FROM novels GROUP BY platform ORDER BY COUNT(*) DESC")
    for r in c.fetchall():
        print(f"  {r[0]}: {r[1]}")
    c.execute("SELECT trope, count FROM trope_stats ORDER BY count DESC LIMIT 15")
    print("\n题材热度:")
    for r in c.fetchall():
        print(f"  {r[0]}: {r[1]}")
    conn.close()


if __name__ == "__main__":
    # CLI: --skip-detail to skip detail page enrichment
    opts = {"hongxiu": True, "fanqie": True, "jjwxc": True, "detail_enrich": "--skip-detail" not in sys.argv}
    run_scan(opts)
