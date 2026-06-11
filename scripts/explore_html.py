#!/usr/bin/env python3
"""提取各平台关键HTML片段用于编写解析器"""
import requests, re, json

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# 1. 纵横 - 查看排行列表的HTML结构
print("=== 纵横月票榜HTML结构 ===")
r = SESSION.get("https://www.zongheng.com/rank?nav=monthly-ticket&rankType=1", timeout=15)
h = r.text
# Find book items
# Look for <li> or <div> containing book info
book_items = re.findall(r'<li[^>]*?class="[^"]*"[^>]*?>.*?</li>', h, re.S)
print(f"List items: {len(book_items)}")
# Find all <a> with rank-related text
for m in re.finditer(r'<a[^>]*href="(https?://book\.zongheng\.com[^"]+)"[^>]*>([^<]+)</a>', h):
    print(f"  Book: {m.group(2).strip():30s} -> {m.group(1)}")
# Show 2000 chars around first "book" reference
idx = h.find('book.zongheng.com')
if idx > 0:
    print(f"\nHTML context around first book link:")
    print(h[max(0,idx-300):idx+500])

# 2. 红袖 - check actual novel link patterns
print("\n\n=== 红袖排行小说项 ===")
r2 = SESSION.get("https://www.hongxiu.com/rank", timeout=15)
h2 = r2.text
# Find all links with numeric book IDs
for m in re.finditer(r'href="(/book/\d+)"[^>]*>([^<]{4,50})</a>', h2):
    print(f"  {m.group(2).strip():30s} -> {m.group(1)}")
# Show 2000 chars around first result
idx2 = h2.find('/book/')
if idx2 > 0:
    print(f"\nHTML around first /book/:")
    print(h2[max(0,idx2-200):idx2+600])

# 3. 番茄 - 提取window.__INITIAL_STATE__
print("\n\n=== 番茄__INITIAL_STATE__ ===")
r3 = SESSION.get("https://fanqienovel.com/", timeout=15)
h3 = r3.text
m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>', h3, re.S)
if m:
    data = json.loads(m.group(1))
    print(f"Keys: {list(data.keys())}")
    # Check novel-related data
    for k, v in data.items():
        if isinstance(v, dict):
            print(f"  {k}: {list(v.keys())[:5]}")
        else:
            print(f"  {k}: {type(v).__name__} = {str(v)[:100]}")

# 4. Search fanqie
print("\n\n=== 番茄搜索 ===")
r4 = SESSION.get("https://fanqienovel.com/search?keyword=重生", timeout=15)
h4 = r4.text
print(f"Search page: {len(h4)} bytes")
m4 = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>', h4, re.S)
if m4:
    data4 = json.loads(m4.group(1))
    print(f"Keys: {list(data4.keys())}")
    for k, v in data4.items():
        if isinstance(v, dict):
            print(f"  {k}: {list(v.keys())[:5]}")
            # Check for novel data
            for k2, v2 in v.items():
                if isinstance(v2, list):
                    print(f"    {k2}: list[{len(v2)}]")
                    if v2 and isinstance(v2[0], dict):
                        print(f"      sample keys: {list(v2[0].keys())[:10]}")
                elif isinstance(v2, dict):
                    print(f"    {k2}: dict keys={list(v2.keys())[:8]}")
        else:
            print(f"  {k}: {type(v).__name__} = {str(v)[:200]}")

# 5. Check zongheng category browse (not search)
print("\n\n=== 纵横分类浏览 ===")
for cat_id in ["5", "6", "7", "8"]:  # 不同分类
    r5 = SESSION.get(f"https://www.zongheng.com/store?categoryId={cat_id}&page=1", timeout=15)
    books = re.findall(r'href="(https?://book\.zongheng\.com/book/\d+\.html)"[^>]*>([^<]+)</a>', r5.text)
    print(f"  category={cat_id}: {len(books)} books, size={len(r5.text)}")
    for href, title in books[:3]:
        print(f"    {title.strip():25s} -> {href}")
