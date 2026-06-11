#!/usr/bin/env python3
# coding: utf-8
import urllib.parse
import requests
import json
import sqlite3
import time
import re
import sys
import socket
from datetime import datetime
from bs4 import BeautifulSoup

DB = "/root/novel-crawler/benchmark.db"
SESS = requests.Session()
SESS.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

def init_db():
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
        r = SESS.get(url, timeout=10)
        r.encoding = enc
        return r.text
    except:
        return None

def tags_of(text):
    tags = []
    kw_map = {"重生": ["重生", "穿越回", "重返"], "校园": ["校园", "学校", "教室", "班主任", "同桌", "前后桌", "分班"], "青春": ["青春", "少年", "少女", "初三", "高中", "初中"], "学霸": ["学霸", "年级第一", "第一名"], "治愈": ["治愈", "温暖", "陪伴"], "学生": ["学生", "上课", "考试", "月考"]}
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

def scrape_qidian():
    results = []
    print("  [起点] ...")
    for kw in ["重生 校园", "校园 青春"]:
        try:
            url = "https://www.qidian.cn/search?kw=" + urllib.parse.quote(kw)
            html = fetch(url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                name = a.get_text(strip=True)
                if not name or len(name) < 3 or '广告' in name:
                    continue
                if 'book' in href.lower() or 'novel' in href.lower() or 'list' in href.lower():
                    t = tags_of(name)
                    if t:
                        results.append({"platform": "起点中文网", "novel_name": name, "author": "", "tags": t, "source": "search", "search_keyword": kw, "raw_data": json.dumps({"href": href[:200]}, ensure_ascii=False)})
        except:
            continue
        time.sleep(1)
    return results

def scrape_fanqie():
    results = []
    print("  [番茄] ...")
    for kw in ["重生 校园", "校园 青春"]:
        try:
            url = "https://www.fanqienovel.com/search?keyword=" + urllib.parse.quote(kw)
            html = fetch(url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            for a in soup.find_all('a', href=True):
                name = a.get_text(strip=True)
                if not name or len(name) < 3:
                    continue
                href = a.get('href', '')
                if 'book' in href.lower() or 'novel' in href.lower() or 'reader' in href.lower():
                    t = tags_of(name)
                    if t:
                        results.append({"platform": "番茄小说", "novel_name": name, "author": "", "tags": t, "source": "search", "search_keyword": kw, "raw_data": json.dumps({"href": href[:200]}, ensure_ascii=False)})
        except:
            continue
        time.sleep(1)
    return results

def scrape_jjwxc():
    results = []
    print("  [晋江] ...")
    for kw in ["重生 校园", "校园 青春"]:
        try:
            url = "https://www.jjwxc.net/search.php?search_type=all&keywords=" + urllib.parse.quote(kw) + "&page=1"
            html = fetch(url, enc='gb18030')
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            # Look for book links
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                name = a.get_text(strip=True)
                if not name or len(name) < 3 or 'onebook' not in href:
                    continue
                t = tags_of(name)
                if t:
                    nid_m = re.search(r'novelid=(\d+)', href)
                    nid = nid_m.group(1) if nid_m else ""
                    results.append({"platform": "晋江文学城", "novel_id": nid, "novel_name": name, "author": "", "tags": t, "source": "search", "search_keyword": kw, "raw_data": json.dumps({"href": href[:200]}, ensure_ascii=False)})
        except Exception as e:
            print(f"    [晋江] ERR: {e}")
            continue
        time.sleep(1)
    return results

def scrape_zongheng():
    results = []
    print("  [纵横] ...")
    for kw in ["重生", "校园"]:
        try:
            url = "https://so.zongheng.com/search?keyword=" + urllib.parse.quote(kw) + "&page=1"
            html = fetch(url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            for a in soup.find_all('a', href=True):
                name = a.get_text(strip=True)
                if not name or len(name) < 3:
                    continue
                href = a.get('href', '')
                if 'book' in href.lower() or 'zs' in href.lower():
                    t = tags_of(name)
                    if t:
                        results.append({"platform": "纵横中文网", "novel_name": name, "author": "", "tags": t, "source": "search", "search_keyword": kw, "raw_data": json.dumps({"href": href[:200]}, ensure_ascii=False)})
        except:
            continue
        time.sleep(1)
    return results

def scrape_qqread():
    results = []
    print("  [QQ阅读] ...")
    for kw in ["重生 校园"]:
        try:
            url = "https://www.qqread.com/s?q=" + urllib.parse.quote(kw)
            html = fetch(url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            for a in soup.find_all('a', href=True):
                name = a.get_text(strip=True)
                if not name or len(name) < 3:
                    continue
                href = a.get('href', '')
                if 'book' in href.lower() or 'novel' in href.lower():
                    t = tags_of(name)
                    if t:
                        results.append({"platform": "QQ阅读", "novel_name": name, "author": "", "tags": t, "source": "search", "search_keyword": kw, "raw_data": json.dumps({"href": href[:200]}, ensure_ascii=False)})
        except:
            continue
        time.sleep(1)
    return results

def scrape_qimao():
    results = []
    print("  [七猫] ...")
    for kw in ["重生 校园"]:
        try:
            url = "https://www.qimao.com/search?q=" + urllib.parse.quote(kw)
            html = fetch(url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            for a in soup.find_all('a', href=True):
                name = a.get_text(strip=True)
                if not name or len(name) < 3:
                    continue
                href = a.get('href', '')
                if 'book' in href.lower() or 'read' in href.lower() or 'novel' in href.lower():
                    t = tags_of(name)
                    if t:
                        results.append({"platform": "七猫小说", "novel_name": name, "author": "", "tags": t, "source": "search", "search_keyword": kw, "raw_data": json.dumps({"href": href[:200]}, ensure_ascii=False)})
        except:
            continue
        time.sleep(1)
    return results

def run():
    print("=" * 60)
    print("小说扫榜工具 - 重生校园青春/学霸/治愈类")
    print(f"Start: {datetime.now().isoformat()}")
    print("=" * 60)
    init_db()
    conn = db()
    c = conn.cursor()
    total = 0
    scanners = [
        ("起点", scrape_qidian),
        ("番茄", scrape_fanqie),
        ("晋江", scrape_jjwxc),
        ("纵横", scrape_zongheng),
        ("QQ阅读", scrape_qqread),
        ("七猫", scrape_qimao),
    ]
    for name, func in scanners:
        print(f"\n[{name}]")
        try:
            results = func()
            seen = set()
            unique = []
            for n in results:
                key = n.get("novel_name", "")
                if key and key not in seen:
                    seen.add(key)
                    unique.append(n)
            print(f"  Unique: {len(unique)}")
            for n in unique:
                if save(c, n):
                    total += 1
        except Exception as e:
            print(f"  ERR: {e}")
    print(f"\n{'='*60}")
    print(f"Done! Added {total} novels")
    c.execute("SELECT platform, COUNT(*) FROM novels GROUP BY platform ORDER BY COUNT(*) DESC")
    print("By platform:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    c.execute("SELECT trope, count FROM trope_stats ORDER BY count DESC LIMIT 20")
    print("\nTop tags:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    c.execute("INSERT INTO scan_log (platform, method, keyword, novels_found, scanned_at) VALUES (?, ?, ?, ?, ?)", ("all", "scan", "all", total, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print("=" * 60)

def stats():
    conn = db()
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("扫榜数据库统计")
    print("=" * 60)
    c.execute("SELECT COUNT(*) FROM novels")
    print(f"Total: {c.fetchone()[0]}")
    c.execute("SELECT platform, COUNT(*) FROM novels GROUP BY platform")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    c.execute("SELECT trope, count FROM trope_stats ORDER BY count DESC LIMIT 20")
    print("\nTop tags:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    conn.close()

def export_json():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM novels ORDER BY id")
    rows = c.fetchall()
    novels = [{"platform": r["platform"], "novel_id": r["novel_id"], "novel_name": r["novel_name"], "author": r["author"], "tags": json.loads(r["tags"]) if r["tags"] else [], "source": r["source"], "crawled_at": r["crawled_at"]} for r in rows]
    with open("/root/novel-crawler/benchmark_export.json", "w", encoding="utf-8") as f:
        json.dump(novels, f, ensure_ascii=False, indent=2)
    conn.close()
    print(f"Exported {len(novels)} novels")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 benchmark.py [scan|stats|export]")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "scan":
        run()
    elif cmd == "stats":
        stats()
    elif cmd == "export":
        export_json()
    else:
        print(f"Unknown: {cmd}")
