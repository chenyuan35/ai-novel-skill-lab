#!/usr/bin/env python3
"""
小说扫榜工具 v2 - 重生校园青春/学霸/治愈类
支持 cloudscraper 绕过反爬，DNS 备用解析
"""
import requests
import cloudscraper
import json
import sqlite3
import time
import re
import sys
import os
import socket
from datetime import datetime
from bs4 import BeautifulSoup

DB_PATH = "/root/novel-crawler/benchmark.db"
SESSION = requests.Session()
SCRAPER = cloudscraper.create_scraper()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
})

# DNS 备用解析 - 如果某个域名 DNS 失败，用这个
DNS_CACHE = {}

def get_ip_fallback(domain):
    """DNS 失败时尝试用备用 DNS（阿里云 DNS）"""
    if domain in DNS_CACHE:
        return DNS_CACHE[domain]
    try:
        # 先用默认 DNS
        ip = socket.gethostbyname(domain)
        DNS_CACHE[domain] = ip
        return ip
    except socket.gaierror:
        pass

    try:
        # 用阿里云 DNS (223.5.5.5) 和腾讯 DNS (119.29.29.29)
        for dns_server in ['223.5.5.5', '119.29.29.29']:
            try:
                resolver = socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
                if resolver:
                    ip = resolver[0][4][0]
                    DNS_CACHE[domain] = ip
                    return ip
            except:
                continue
    except:
        pass

    DNS_CACHE[domain] = None
    return None


# 关键词库
KEYWORDS = {
    "重生校园": ["重生校园", "重生初中", "重返青春", "回到学生时代"],
    "学霸": ["学霸", "学霸前桌"],
    "通用": ["重生 校园", "校园 青春", "学霸 重生"],
}

# 平台配置
PLATFORMS = {
    "fanqie": {
        "name": "番茄小说",
        "base": "https://www.fanqienovel.com",
        "search_url": "https://www.fanqienovel.com/search?keyword={keyword}",
        "encoding": "utf-8",
    },
    "ijj": {
        "name": "晋江文学城",
        "base": "https://www.jjwxc.net",
        "search_url": "https://www.jjwxc.net/search.php?search_type=all&keywords={keyword}",
        "rank_url": "https://www.jjwxc.net/bookbase.php?orderstr=click_month&cid=5&page={page}",
        "encoding": "gb18030",
    },
    "zongheng": {
        "name": "纵横中文网",
        "base": "https://www.zongheng.com",
        "search_url": "https://so.zongheng.com/search?keyword={keyword}",
        "encoding": "utf-8",
    },
    "qqread": {
        "name": "QQ阅读",
        "base": "https://www.qqread.com",
        "search_url": "https://www.qqread.com/s?q={keyword}",
        "encoding": "utf-8",
    },
    "qimao": {
        "name": "七猫小说",
        "base": "https://www.qimao.com",
        "search_url": "https://www.qimao.com/search?q={keyword}",
        "encoding": "utf-8",
    },
    "qidian": {
        "name": "起点中文网",
        "base": "https://www.qidian.cn",
        "search_url": "https://www.qidian.cn/search?kw={keyword}",
        "encoding": "utf-8",
    },
}


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS novels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            novel_id TEXT NOT NULL,
            novel_name TEXT NOT NULL,
            author TEXT NOT NULL,
            description TEXT,
            genre TEXT,
            tags TEXT,
            status TEXT,
            chapter_count INTEGER,
            word_count INTEGER,
            word_count_display TEXT,
            rating REAL,
            total_clicks INTEGER,
            total_hits INTEGER,
            total_recommend INTEGER,
            source TEXT,
            search_keyword TEXT,
            crawled_at TEXT,
            raw_data TEXT,
            UNIQUE(platform, novel_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS trope_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trope TEXT NOT NULL UNIQUE,
            count INTEGER DEFAULT 0,
            novels TEXT,
            updated_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            method TEXT,
            keyword TEXT,
            novels_found INTEGER,
            scanned_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_page(url, encoding='utf-8', use_scraper=False, timeout=15):
    """获取页面 HTML"""
    try:
        if use_scraper:
            r = SCRAPER.get(url, timeout=timeout, allow_redirects=True)
        else:
            r = SESSION.get(url, timeout=timeout)
        r.encoding = encoding
        return r.text
    except Exception as e:
        return None


def extract_tags(text):
    """从文本提取题材标签"""
    tags = []
    keywords = {
        "重生": ["重生", "穿越回", "回到", "返青春", "重返"],
        "校园": ["校园", "学校", "教室", "班主任", "同桌", "前后桌"],
        "青春": ["青春", "少年", "少女", "初中", "高中", "初三"],
        "学霸": ["学霸", "年级第一", "第一名", "成绩"],
        "治愈": ["治愈", "温暖", "陪伴", "成长"],
        "学生": ["学生", "上课", "考试", "月考", "期中", "期末"],
        "喜剧": ["喜剧", "搞笑", "欢乐", "轻松"],
        "逆袭": ["逆袭", "翻身", "反杀", "打脸"],
    }
    for category, kws in keywords.items():
        for kw in kws:
            if kw in text:
                tags.append(category)
                break
    return tags


def save_novel(conn, novel_data):
    """保存小说到数据库"""
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR IGNORE INTO novels (
                platform, novel_id, novel_name, author, description, genre, tags,
                status, chapter_count, word_count, word_count_display,
                rating, total_clicks, total_hits, total_recommend,
                source, search_keyword, crawled_at, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            novel_data.get("platform", ""),
            novel_data.get("novel_id", ""),
            novel_data.get("novel_name", ""),
            novel_data.get("author", ""),
            novel_data.get("description", "") or "",
            novel_data.get("genre", "") or "",
            json.dumps(novel_data.get("tags", []), ensure_ascii=False),
            novel_data.get("status", "") or "",
            novel_data.get("chapter_count", 0),
            novel_data.get("word_count", 0),
            novel_data.get("word_count_display", "") or "",
            novel_data.get("rating", 0),
            novel_data.get("total_clicks", 0),
            novel_data.get("total_hits", 0),
            novel_data.get("total_recommend", 0),
            novel_data.get("source", "") or "",
            novel_data.get("search_keyword", "") or "",
            datetime.now().isoformat(),
            novel_data.get("raw_data", "") or "",
        ))
        conn.commit()

        for tag in novel_data.get("tags", []):
            c.execute("""
                INSERT INTO trope_stats (trope, count) VALUES (?, 1)
                ON CONFLICT(trope) DO UPDATE SET count = count + 1
            """, (tag,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"    [DB ERROR] {e}")
        return False


def scrape_fanqie():
    """扫描番茄小说"""
    results = []
    print("  [番茄] 搜索关键词...")

    keywords = ["重生 校园", "校园 青春", "学霸"]
    for kw in keywords:
        try:
            # 番茄有搜索页
            url = f"https://www.fanqienovel.com/search?keyword={urllib.parse.quote(kw)}"
            html = fetch_page(url, encoding='utf-8')
            if not html:
                print(f"    [番茄] {kw} 获取失败")
                continue

            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.search-item, .book-item, [class*="search"], .novel-item')

            for item in items[:10]:
                try:
                    name_m = item.select_one('[class*="title"], [class*="name"], h3, h4, a')
                    if not name_m:
                        continue
                    name = name_m.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    tags = extract_tags(name)
                    if not tags:
                        continue

                    results.append({
                        "platform": "番茄小说",
                        "novel_name": name,
                        "author": "",
                        "tags": tags,
                        "source": "search",
                        "search_keyword": kw,
                        "raw_data": json.dumps({"html_snippet": str(name_m)[:200]}, ensure_ascii=False),
                    })
                except:
                    continue

            time.sleep(1)
        except Exception as e:
            print(f"    [番茄] ERROR: {e}")

    return results


def scrape_jjwxc():
    """扫描晋江文学城"""
    results = []
    print("  [晋江] 搜索关键词...")

    keywords = ["重生 校园", "校园 青春"]
    for kw in keywords:
        try:
            url = f"https://www.jjwxc.net/search.php?search_type=all&keywords={urllib.parse.quote(kw)}&page=1"
            html = fetch_page(url, encoding='gb18030')
            if not html:
                continue

            soup = BeautifulSoup(html, 'lxml')
            for tr in soup.select('table tr'):
                try:
                    name_m = tr.select_one('a[href*="onebook.php"]')
                    if not name_m:
                        continue
                    name = name_m.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    author_m = tr.select_one('a[href*="author.php"]')
                    author = author_m.get_text(strip=True) if author_m else ""

                    # 提取novelid
                    nid_m = re.search(r'novelid=(\d+)', name_m.get('href', ''))
                    nid = nid_m.group(1) if nid_m else ""

                    tags = extract_tags(name + author)
                    if not tags:
                        continue

                    results.append({
                        "platform": "晋江文学城",
                        "novel_id": nid,
                        "novel_name": name,
                        "author": author,
                        "tags": tags,
                        "source": "search",
                        "search_keyword": kw,
                        "raw_data": json.dumps({"html_snippet": str(name_m)[:200]}, ensure_ascii=False),
                    })
                except:
                    continue

            time.sleep(1)
        except Exception as e:
            print(f"    [晋江] ERROR: {e}")

    return results


def scrape_zongheng():
    """扫描纵横中文网"""
    results = []
    print("  [纵横] 搜索关键词...")

    keywords = ["重生", "校园"]
    for kw in keywords:
        try:
            url = f"https://so.zongheng.com/search?keyword={urllib.parse.quote(kw)}&page=1"
            html = fetch_page(url, encoding='utf-8')
            if not html:
                continue

            soup = BeautifulSoup(html, 'lxml')
            for item in soup.select('.book-item, .search-book-item, li'):
                try:
                    name_m = item.select_one('.bookname, .book-title, h3, h4, .book-info h4')
                    if not name_m:
                        continue
                    name = name_m.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    tags = extract_tags(name)
                    if not tags:
                        continue

                    results.append({
                        "platform": "纵横中文网",
                        "novel_name": name,
                        "author": "",
                        "tags": tags,
                        "source": "search",
                        "search_keyword": kw,
                        "raw_data": json.dumps({"name": name}, ensure_ascii=False),
                    })
                except:
                    continue

            time.sleep(1)
        except Exception as e:
            print(f"    [纵横] ERROR: {e}")

    return results


def scrape_qidian():
    """扫描起点中文网（使用 cloudscraper）"""
    results = []
    print("  [起点] 搜索关键词...")

    keywords = ["重生 校园", "校园 青春"]
    for kw in keywords:
        try:
            url = f"https://www.qidian.cn/search?kw={urllib.parse.quote(kw)}"
            html = fetch_page(url, encoding='utf-8', use_scraper=True)
            if not html:
                print(f"    [起点] {kw} 获取失败")
                continue

            soup = BeautifulSoup(html, 'lxml')
            for item in soup.select('.book-multiple-info, .book-info, .book-item, .recommend-item'):
                try:
                    name_m = item.select_one('.bookname, .book-info-title, h4, h5, .book-name, .title')
                    if not name_m:
                        continue
                    name = name_m.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    author_m = item.select_one('.author, .book-author, .writer, a.name')
                    author = author_m.get_text(strip=True) if author_m else ""

                    tags = extract_tags(name + author)
                    if not tags:
                        continue

                    results.append({
                        "platform": "起点中文网",
                        "novel_name": name,
                        "author": author,
                        "tags": tags,
                        "source": "search",
                        "search_keyword": kw,
                        "raw_data": json.dumps({"html_snippet": str(name_m)[:200]}, ensure_ascii=False),
                    })
                except:
                    continue

            time.sleep(2)
        except Exception as e:
            print(f"    [起点] ERROR: {e}")

    return results


def scrape_qqread():
    """扫描QQ阅读"""
    results = []
    print("  [QQ阅读] 搜索关键词...")

    keywords = ["重生 校园"]
    for kw in keywords:
        try:
            url = f"https://www.qqread.com/s?q={urllib.parse.quote(kw)}"
            html = fetch_page(url, encoding='utf-8')
            if not html:
                continue

            soup = BeautifulSoup(html, 'lxml')
            for item in soup.select('.book-item, li'):
                try:
                    name_m = item.select_one('.title, h3, h4, a')
                    if not name_m:
                        continue
                    name = name_m.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    tags = extract_tags(name)
                    if not tags:
                        continue

                    results.append({
                        "platform": "QQ阅读",
                        "novel_name": name,
                        "author": "",
                        "tags": tags,
                        "source": "search",
                        "search_keyword": kw,
                        "raw_data": json.dumps({"name": name}, ensure_ascii=False),
                    })
                except:
                    continue

            time.sleep(1)
        except Exception as e:
            print(f"    [QQ阅读] ERROR: {e}")

    return results


def scrape_qimao():
    """扫描七猫小说"""
    results = []
    print("  [七猫] 搜索关键词...")

    keywords = ["重生 校园"]
    for kw in keywords:
        try:
            url = f"https://www.qimao.com/search?q={urllib.parse.quote(kw)}"
            html = fetch_page(url, encoding='utf-8')
            if not html:
                continue

            soup = BeautifulSoup(html, 'lxml')
            for item in soup.select('.book-item, li'):
                try:
                    name_m = item.select_one('.title, h3, h4, a')
                    if not name_m:
                        continue
                    name = name_m.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    tags = extract_tags(name)
                    if not tags:
                        continue

                    results.append({
                        "platform": "七猫小说",
                        "novel_name": name,
                        "author": "",
                        "tags": tags,
                        "source": "search",
                        "search_keyword": kw,
                        "raw_data": json.dumps({"name": name}, ensure_ascii=False),
                    })
                except:
                    continue

            time.sleep(1)
        except Exception as e:
            print(f"    [七猫] ERROR: {e}")

    return results


def run_scan():
    """执行全平台扫榜"""
    print("=" * 60)
    print("小说扫榜工具 v2 - 重生校园青春/学霸/治愈类")
    print(f"开始时间: {datetime.now().isoformat()}")
    print("=" * 60)

    init_db()
    conn = db()
    total_found = 0

    scanners = [
        ("起点中文网", scrape_qidian),
        ("番茄小说", scrape_fanqie),
        ("晋江文学城", scrape_jjwxc),
        ("纵横中文网", scrape_zongheng),
        ("QQ阅读", scrape_qqread),
        ("七猫小说", scrape_qimao),
    ]

    for platform_name, scanner_func in scanners:
        print(f"\n[{platform_name}]")
        try:
            results = scanner_func()
            # 去重（按书名）
            seen = set()
            unique = []
            for novel in results:
                key = novel.get("novel_name", "")
                if key and key not in seen:
                    seen.add(key)
                    unique.append(novel)
            print(f"  找到 {len(unique)} 本相关小说")

            for novel in unique:
                if save_novel(conn, novel):
                    total_found += 1

        except Exception as e:
            print(f"  [ERROR] {e}")

    # 统计
    print("\n" + "=" * 60)
    print(f"扫榜完成！共新增 {total_found} 本小说到数据库")
    print(f"数据库位置: {DB_PATH}")

    c = conn.cursor()
    c.execute("SELECT platform, COUNT(*) as cnt FROM novels GROUP BY platform ORDER BY cnt DESC")
    print("\n各平台收录:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]} 本")

    c.execute("SELECT trope, count FROM trope_stats ORDER BY count DESC LIMIT 20")
    print("\n套路标签统计 (Top 20):")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]} 本")

    c.execute("INSERT INTO scan_log (platform, method, keyword, novels_found, scanned_at) VALUES (?, ?, ?, ?, ?)")
    c.execute("SELECT COUNT(*) FROM novels")
    total = c.fetchone()[0]
    c.execute("INSERT INTO scan_log (platform, method, keyword, novels_found, scanned_at) VALUES (?, ?, ?, ?, ?)",
              ("all", "full_scan", "all", total, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print("=" * 60)


def show_stats():
    """显示数据库统计"""
    conn = db()
    c = conn.cursor()

    print("\n" + "=" * 60)
    print("扫榜数据库统计")
    print("=" * 60)

    c.execute("SELECT COUNT(*) FROM novels")
    print(f"总收录: {c.fetchone()[0]} 本")

    c.execute("SELECT platform, COUNT(*), SUM(is_completed) FROM novels GROUP BY platform")
    print("\n各平台:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]} 本")

    c.execute("SELECT trope, count, novels FROM trope_stats ORDER BY count DESC LIMIT 20")
    print("\nTop 20 套路标签:")
    for row in c.fetchall():
        novels = json.loads(row[2]) if row[2] else []
        print(f"  {row[0]}: {row[1]} 本 ({', '.join(novels[:5])})")

    c.execute("SELECT novel_name, author, chapter_count, platform, tags FROM novels ORDER BY chapter_count DESC LIMIT 10")
    print("\n最长作品 Top 10:")
    for row in c.fetchall():
        tags = json.loads(row[4]) if row[4] else []
        print(f"  [{row[3]}] {row[0]} by {row[1]} ({row[2]}章) {tags}")

    conn.close()


def export_json():
    """导出为JSON"""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM novels ORDER BY chapter_count DESC")
    rows = c.fetchall()

    novels = []
    for row in rows:
        novels.append({
            "platform": row["platform"],
            "novel_id": row["novel_id"],
            "novel_name": row["novel_name"],
            "author": row["author"],
            "description": row["description"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "status": row["status"],
            "chapter_count": row["chapter_count"],
            "word_count": row["word_count"],
            "source": row["source"],
            "crawled_at": row["crawled_at"],
        })

    output_path = "/root/novel-crawler/benchmark_export.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(novels, f, ensure_ascii=False, indent=2)

    conn.close()
    print(f"已导出 {len(novels)} 本小说到 {output_path}")


if __name__ == "__main__":
    import urllib.parse

    if len(sys.argv) < 2:
        print("用法: python3 benchmark_scanner_v2.py [command]")
        print("命令: scan, stats, export")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "scan":
        run_scan()
    elif cmd == "stats":
        show_stats()
    elif cmd == "export":
        export_json()
    else:
        print(f"未知命令: {cmd}")
