#!/usr/bin/env python3
"""Populate local benchmark.db with Fanqie novels from fanqienovel.com.
Scrapes home + rank pages via SSR extraction, matches the actual DB schema.

Run from Windows: py.exe scripts/populate_fanqie_local.py
"""
import requests, sqlite3, json, time, re, os, sys

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "novel-crawler", "benchmark.db"))

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

TROPE_KEYWORDS = ["重生", "校园", "青春", "学霸", "学生", "初三", "初中", "治愈", "成长", "穿书"]

def match_tropes(text):
    return [t for t in TROPE_KEYWORDS if t in text]

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

def ensure_schema(conn):
    """Create novels/scan_log tables if missing; add enrichment columns."""
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS novels (
        id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, novel_id TEXT, novel_name TEXT,
        author TEXT, description TEXT, tags TEXT, status TEXT,
        chapter_count INTEGER, word_count INTEGER, rating REAL,
        source TEXT, search_keyword TEXT, crawled_at TEXT, raw_data TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS scan_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, method TEXT,
        keyword TEXT, novels_found INTEGER, scanned_at TEXT)""")
    existing = [col[1] for col in c.execute("PRAGMA table_info(novels)").fetchall()]
    for col, typ in [("category", "TEXT"), ("creation_status", "INTEGER"),
                     ("genre", "TEXT"), ("genre_display", "TEXT")]:
        if col not in existing:
            c.execute(f"ALTER TABLE novels ADD COLUMN {col} {typ}")
    conn.commit()

def save_novel(conn, n):
    c = conn.cursor()
    try:
        c.execute("""INSERT OR IGNORE INTO novels
            (platform, novel_id, novel_name, author, description, tags, status,
             chapter_count, word_count, rating, source, search_keyword, crawled_at, raw_data)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            n["platform"], n["novel_id"], n["novel_name"], n.get("author", ""),
            n.get("description", ""), json.dumps(n.get("tags", []), ensure_ascii=False),
            n.get("status", ""), n.get("chapter_count", 0), n.get("word_count", 0),
            n.get("rating", 0.0), n.get("source", ""), n.get("search_keyword", ""),
            n.get("crawled_at", ""), n.get("raw_data", "")
        ))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        print(f"    DB error: {e}")
        return False

def log_scan(conn, platform, method, keyword, found):
    c = conn.cursor()
    c.execute("INSERT INTO scan_log (platform, method, keyword, novels_found, scanned_at) VALUES (?,?,?,?,?)",
              (platform, method, keyword, found, time.strftime("%Y-%m-%dT%H:%M:%S")))
    conn.commit()

def scrape_home():
    """Home page lists: girlList, boyList, weekList, editorList."""
    results = []
    r = S.get("https://fanqienovel.com/", timeout=15)
    data = extract_ssr(r.text)
    if not data:
        print("  [home] SSR extraction failed")
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
                "platform": "番茄", "novel_id": novel_id, "novel_name": name,
                "author": item.get("author", ""), "description": (item.get("abstract", "") or "")[:500],
                "tags": tags, "status": "", "chapter_count": 0, "word_count": 0,
                "rating": 0.0, "source": "home_list", "search_keyword": list_name,
                "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "raw_data": json.dumps({"list": list_name}, ensure_ascii=False),
            })
        print(f"  [home] {list_name}: {len(items)} items")
    return results

def scrape_rank():
    """Rank page — has wordNumber, creationStatus, etc."""
    results = []
    r = S.get("https://fanqienovel.com/rank", timeout=15)
    data = extract_ssr(r.text)
    if not data:
        print("  [rank] SSR extraction failed")
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
                "platform": "番茄", "novel_id": novel_id, "novel_name": name,
                "author": item.get("author", ""), "description": (item.get("abstract", "") or "")[:500],
                "tags": tags, "status": item.get("creationStatus", ""),
                "chapter_count": item.get("lastChapterItemId", 0) or None,
                "word_count": word_count, "rating": 0.0,
                "source": "rank", "search_keyword": rk,
                "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "raw_data": json.dumps({"rank_category": rk}, ensure_ascii=False),
            })
        print(f"  [rank] {rk}: {len(rv)} items")
    return results

def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    print(f"DB: {DB_PATH}")
    print(f"Schema ready. Novels before: {conn.execute('SELECT COUNT(*) FROM novels').fetchone()[0]}")

    all_results = []
    all_results.extend(scrape_home())
    time.sleep(1)
    all_results.extend(scrape_rank())

    # Dedup by novel_id, keeping first occurrence
    seen = set()
    deduped = []
    for n in all_results:
        if n["novel_id"] not in seen:
            seen.add(n["novel_id"])
            deduped.append(n)

    saved = 0
    for n in deduped:
        if save_novel(conn, n):
            saved += 1

    log_scan(conn, "番茄", "local_populate", "home+rank", saved)
    total = conn.execute("SELECT COUNT(*) FROM novels").fetchone()[0]
    print(f"\nScraped: {len(all_results)} raw, {len(deduped)} unique")
    print(f"Saved: {saved} new, {total} total in DB")
    conn.close()

if __name__ == "__main__":
    main()
