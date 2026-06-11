# coding: utf-8
"""
小说扫榜工具 - 本地 Windows 版
扫描目标：重生校园青春/学霸/治愈类
输出：SQLite 数据库 + JSON 导出
"""
import urllib.parse
import requests
import json
import sqlite3
import time
import re
import os
from datetime import datetime
from bs4 import BeautifulSoup

DB = os.path.join(os.path.dirname(__file__), "..", "novel-crawler", "benchmark.db")
SESS = requests.Session()
SESS.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS novels (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, novel_id TEXT, novel_name TEXT, author TEXT, description TEXT, tags TEXT, status TEXT, chapter_count INTEGER, word_count INTEGER, rating REAL, source TEXT, search_keyword TEXT, crawled_at TEXT, raw_data TEXT, UNIQUE(platform, novel_id))")
    c.execute("CREATE TABLE IF NOT EXISTS trope_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, trope TEXT UNIQUE, count INTEGER, novels TEXT, updated_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS scan_log (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, method TEXT, keyword TEXT, novels_found INTEGER, scanned_at TEXT)")
    conn.commit()
    conn.close()

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def fetch(url, enc='utf-8'):
    try:
        r = SESS.get(url, timeout=15, allow_redirects=True)
        r.encoding = enc
        return r.text
    except Exception as e:
        print(f"    [FETCH ERR] {url[:80]}: {e}")
        return None

def tags_of(text):
    tags = []
    kw_map = {
        "重生": ["重生", "穿越回", "重返", "回到"],
        "校园": ["校园", "学校", "教室", "班主任", "同桌", "前后桌", "分班"],
        "青春": ["青春", "少年", "少女", "初三", "高中", "初中"],
        "学霸": ["学霸", "年级第一", "第一名"],
        "治愈": ["治愈", "温暖", "陪伴"],
        "学生": ["学生", "上课", "考试", "月考"],
    }
    for cat, kws in kw_map.items():
        for kw in kws:
            if kw in text:
                tags.append(cat)
                break
    return tags

def save(c, nd):
    try:
        c.execute("INSERT OR IGNORE INTO novels (platform,novel_id,novel_name,author,description,tags,status,chapter_count,word_count,rating,source,search_keyword,crawled_at,raw_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (nd.get("platform",""), nd.get("novel_id",""), nd.get("novel_name",""), nd.get("author",""),
             nd.get("description","") or "", json.dumps(nd.get("tags",[]), ensure_ascii=False),
             nd.get("status","") or "", nd.get("chapter_count",0), nd.get("word_count",0),
             nd.get("rating",0), nd.get("source","") or "", nd.get("search_keyword","") or "",
             datetime.now().isoformat(), nd.get("raw_data","") or ""))
        conn.commit()
        for t in nd.get("tags",[]):
            c.execute("INSERT INTO trope_stats (trope, count) VALUES (?,1) ON CONFLICT(trope) DO UPDATE SET count=count+1", (t,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False

def scrape_platform(platform_name, search_url_template, enc='utf-8', href_filter=None):
    """通用扫描函数"""
    results = []
    keywords = ["重生 校园", "校园 青春", "学霸 重生"]
    for kw in keywords:
        url = search_url_template.format(keyword=urllib.parse.quote(kw))
        print(f"  [{platform_name}] 搜索: {kw}")
        html = fetch(url, enc=enc)
        if not html:
            continue
        soup = BeautifulSoup(html, 'lxml')
        count = 0
        for a in soup.find_all('a', href=True):
            name = a.get_text(strip=True)
            if not name or len(name) < 3:
                continue
            if '广告' in name or '推广' in name:
                continue
            href = a.get('href', '')
            if href_filter and not href_filter(href, name):
                continue
            t = tags_of(name)
            if t:
                count += 1
                results.append({
                    "platform": platform_name,
                    "novel_name": name,
                    "author": "",
                    "tags": t,
                    "source": "search",
                    "search_keyword": kw,
                    "raw_data": json.dumps({"url": url[:200], "href": href[:200]}, ensure_ascii=False),
                })
        if count:
            print(f"    找到 {count} 本")
        time.sleep(1)
    return results

def run():
    print("=" * 60)
    print("小说扫榜工具 v2 - 本地 Windows 版")
    print("题材：重生校园青春/学霸/治愈")
    print(f"开始: {datetime.now().isoformat()}")
    print("=" * 60)
    init_db()
    conn = db()
    c = conn.cursor()
    total = 0

    platforms = [
        ("起点中文网", "https://www.qidian.cn/search?kw={keyword}", 'utf-8',
         lambda href, name: 'book' in href.lower() or 'novel' in href.lower() or 'list' in href.lower()),
        ("番茄小说", "https://www.fanqienovel.com/search?keyword={keyword}", 'utf-8',
         lambda href, name: 'book' in href.lower() or 'novel' in href.lower() or 'reader' in href.lower()),
        ("晋江文学城", "https://www.jjwxc.net/search.php?search_type=all&keywords={keyword}&page=1", 'gb18030',
         lambda href, name: 'onebook' in href.lower()),
        ("纵横中文网", "https://so.zongheng.com/search?keyword={keyword}&page=1", 'utf-8',
         lambda href, name: 'book' in href.lower() or 'zs' in href.lower()),
        ("QQ阅读", "https://www.qqread.com/s?q={keyword}", 'utf-8',
         lambda href, name: 'book' in href.lower() or 'novel' in href.lower()),
        ("七猫小说", "https://www.qimao.com/search?q={keyword}", 'utf-8',
         lambda href, name: 'book' in href.lower() or 'read' in href.lower() or 'novel' in href.lower()),
    ]

    for name, url_tmpl, enc, pred in platforms:
        print(f"\n[{name}]")
        results = scrape_platform(name, url_tmpl, enc, pred)
        # 去重
        seen = set()
        unique = []
        for n in results:
            key = n.get("novel_name", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(n)
        print(f"  去重后: {len(unique)} 本")
        for n in unique:
            if save(c, n):
                total += 1

    print(f"\n{'='*60}")
    print(f"完成! 新增 {total} 本小说")
    print(f"数据库: {DB}")
    c.execute("SELECT platform, COUNT(*) FROM novels GROUP BY platform ORDER BY COUNT(*) DESC")
    print("各平台收录:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    c.execute("SELECT trope, count FROM trope_stats ORDER BY count DESC LIMIT 20")
    print("\nTop 套路标签:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    c.execute("INSERT INTO scan_log (platform, method, keyword, novels_found, scanned_at) VALUES (?, ?, ?, ?, ?)",
              ("all", "local_scan", "all", total, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print("=" * 60)

if __name__ == "__main__":
    run()
