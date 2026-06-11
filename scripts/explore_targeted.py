#!/usr/bin/env python3
"""Targeted extraction: fanqie SSR data, hongxiu /so/ pages, hetushu detail"""
import requests, re, json

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# 1. 番茄 - 搜索页的__INITIAL_STATE__
print("=== 番茄__INITIAL_STATE__ (首页) ===")
r = S.get("https://fanqienovel.com/", timeout=15)
m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>', r.text, re.S)
if m:
    data = json.loads(m.group(1))
    print(f"Root keys: {list(data.keys())}")
    for k, v in data.items():
        if isinstance(v, dict):
            print(f"  {k}: {list(v.keys())[:8]} counts={ {kk: type(vv).__name__ for kk, vv in v.items()} }")
        elif isinstance(v, list):
            print(f"  {k}: list[{len(v)}]")
        else:
            print(f"  {k}: {type(v).__name__} = {str(v)[:100]}")
    # Check for novel/category data
    for key in data:
        v = data[key]
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, list) and len(v2) > 0 and isinstance(v2[0], dict):
                    print(f"\n  {key}.{k2}[0] keys: {list(v2[0].keys())}")
                    if 'book_name' in v2[0] or 'novel_name' in v2[0] or 'title' in v2[0]:
                        print(f"  Sample item: {json.dumps(v2[0], ensure_ascii=False)[:300]}")

print("\n=== 番茄__INITIAL_STATE__ (搜索 page) ===")
r2 = S.get("https://fanqienovel.com/search?keyword=重生校园", timeout=15)
m2 = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>', r2.text, re.S)
if m2:
    data2 = json.loads(m2.group(1))
    print(f"Root keys: {list(data2.keys())}")
    for k, v in data2.items():
        if isinstance(v, dict):
            print(f"  {k}: {list(v.keys())[:8]}")
            for k2, v2 in v.items():
                if isinstance(v2, list) and len(v2) > 0 and isinstance(v2[0], dict):
                    print(f"    {k2}: list[{len(v2)}] sample keys: {list(v2[0].keys())[:15]}")
                    if any(x in str(v2[0]).lower() for x in ['book', 'novel', 'title', 'name']):
                        print(f"    Sample: {json.dumps(v2[0], ensure_ascii=False)[:400]}")
        elif isinstance(v, list):
            print(f"  {k}: list[{len(v)}]")
        else:
            print(f"  {k}: {type(v).__name__} = {str(v)[:200]}")

# 2. 红袖 /so/ 关键词页
print("\n=== 红袖 /so/ 关键词页 ===")
for kw in ["重生", "校园", "学霸"]:
    r3 = S.get(f"https://www.hongxiu.com/so/{kw}", timeout=15)
    h3 = r3.text
    books = re.findall(r'href="(/book/\d+)"[^>]*>([^<]+)</a>', h3)
    print(f"  '/so/{kw}': {len(books)} total links")
    # Show unique books
    seen = set()
    for href, title in books:
        if title.strip() not in seen:
            seen.add(title.strip())
            if len(seen) <= 10:
                print(f"    {title.strip():25s} -> {href}")
    print(f"    (unique: {len(seen)})")

# Also check if we can extract more info (author, stats) from the page
print("\n=== 红袖 /so/重生 - 详细HTML片段 ===")
r4 = S.get("https://www.hongxiu.com/so/重生", timeout=15)
# Look for book lists
for m in re.finditer(r'<div[^>]*class="book-info"[^>]*>(.*?)</div>', r4.text, re.S):
    content = m.group(1)[:500]
    print(f"  Book info block: {content[:300]}")
    break

# Save a sample section
idx_a = r4.text.find('class="book-list"')
if idx_a < 0: idx_a = r4.text.find('rank-list')
if idx_a < 0: idx_a = r4.text.find('list-wrap')
if idx_a < 0: idx_a = 1000
print(f"\n  HTML around list area:")
print(r4.text[max(0,idx_a-100):idx_a+2000])

# 3. Check total server disk
import os
st = os.statvfs('/')
free = st.f_bavail * st.f_frsize
total = st.f_blocks * st.f_frsize
print(f"\n=== 服务器磁盘 ===")
print(f"Free: {free/1024/1024:.0f}MB / {total/1024/1024:.0f}MB")
