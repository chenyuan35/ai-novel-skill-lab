#!/usr/bin/env python3
"""探索各小说平台的排行/搜索页面结构"""
import requests, re, sys

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

targets = [
    ("纵横排行", "https://www.zongheng.com/rank.html"),
    ("七猫排行", "https://www.qimao.com/rank/"),
    ("红袖排行", "https://www.hongxiu.com/rank"),
    ("掌阅排行", "https://www.zhangyue.com/rank"),
    ("和图书", "https://www.hetushu.com/"),
    ("刺猬猫排行", "https://www.ciweimao.com/rank"),
]

for name, url in targets:
    print(f"\n=== {name} ===")
    print(f"URL: {url}")
    try:
        r = SESSION.get(url, timeout=15)
        print(f"Status: {r.status_code}, Size: {len(r.text)} bytes, Encoding: {r.encoding}")
        html = r.text

        # Look for novel links
        links = re.findall(r'href=["\']([^"\']*?)["\'][^>]*?>([^<]{4,30})</a>', html)
        novel_links = [l for l in links if 'book' in l[0].lower() or 'novel' in l[0].lower() or 'chapter' in l[0].lower()]
        print(f"  Novel-like links: {len(novel_links)}")
        if novel_links:
            for href, text in novel_links[:8]:
                print(f"    {text.strip():25s} -> {href}")

        # Check for search params / form
        search_forms = re.findall(r'<input[^>]*?name=["\'](?:keyword|search|q|wd)["\'][^>]*>', html)
        print(f"  Search inputs found: {len(search_forms)}")

        # Check category / genre tags
        cats = re.findall(r'category|genre|type|分类', html[:5000], re.I)
        print(f"  Category mentions: {len(cats)}")

    except Exception as e:
        print(f"  ERROR: {e}")

# Check zongheng search
print("\n\n=== 纵横搜索测试 ===")
try:
    r = SESSION.get("https://www.zongheng.com/search?keyword=重生校园", timeout=15)
    print(f"Search Status: {r.status_code}, Size: {len(r.text)}")
    # Extract novel items
    items = re.findall(r'<div[^>]*?class=["\'][^"\']*?book[^"\']*?["\'][^>]*?>.*?</div>', r.text, re.S)[:3]
    print(f"Book divs found: {len(items)}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 七猫搜索测试 ===")
try:
    r = SESSION.get("https://www.qimao.com/search/all/?key=重生校园", timeout=15)
    print(f"Search Status: {r.status_code}, Size: {len(r.text)}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 番茄搜索测试 ===")
try:
    r = SESSION.get("https://fanqienovel.com/api/novel/search?keyword=重生校园", timeout=15)
    print(f"Search API Status: {r.status_code}, Size: {len(r.text)}, JSON: {r.headers.get('content-type','')}")
    if 'json' in r.headers.get('content-type',''):
        data = r.json()
        print(f"  Data keys: {list(data.keys())}")
except Exception as e:
    print(f"ERROR: {e}")
