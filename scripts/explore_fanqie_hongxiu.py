#!/usr/bin/env python3
"""Fix fanqie INITIAL_STATE extraction + hongxiu keyword deep dive"""
import requests, re, json

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# 1. 番茄 - 用更好的方法提取__INITIAL_STATE__
print("=== 番茄 SSR数据提取 ===")
r = S.get("https://fanqienovel.com/search?keyword=重生校园", timeout=15)
h = r.text

# Method 1: simpler regex
idx = h.find('window.__INITIAL_STATE__')
if idx > 0:
    # Find the { and match braces
    start = h.find('{', idx)
    depth = 0
    end = start
    for i in range(start, len(h)):
        if h[i] == '{': depth += 1
        elif h[i] == '}': depth -= 1
        if depth == 0:
            end = i + 1
            break
    raw = h[start:end]
    print(f"Found __INITIAL_STATE__ at index {idx}, JSON length: {len(raw)}")
    try:
        data = json.loads(raw)
        print(f"Root keys: {list(data.keys())}")
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"  {k}: type=dict, keys={list(v.keys())[:10]}")
                for k2, v2 in v.items():
                    if isinstance(v2, list) and len(v2) > 0:
                        print(f"    {k2}: list[{len(v2)}] type={type(v2[0]).__name__}")
                        if isinstance(v2[0], dict):
                            print(f"      sample keys: {list(v2[0].keys())[:15]}")
                            if any(x in str(v2[0]) for x in ['book', 'novel', 'title', 'name']):
                                print(f"      item: {json.dumps(v2[0], ensure_ascii=False)[:500]}")
            elif isinstance(v, list):
                print(f"  {k}: list[{len(v)}]")
            else:
                print(f"  {k}: {type(v).__name__} = {str(v)[:200]}")
    except Exception as e:
        print(f"  JSON parse error: {e}")
        print(f"  First 500 chars: {raw[:500]}")
        print(f"  Last 500 chars: {raw[-500:]}")

# Also check the main page
print("\n=== 番茄首页 SSR ===")
r2 = S.get("https://fanqienovel.com/", timeout=15)
h2 = r2.text
idx2 = h2.find('window.__INITIAL_STATE__')
if idx2 > 0:
    start2 = h2.find('{', idx2)
    depth = 0
    end2 = start2
    for i in range(start2, len(h2)):
        if h2[i] == '{': depth += 1
        elif h2[i] == '}': depth -= 1
        if depth == 0:
            end2 = i + 1
            break
    raw2 = h2[start2:end2]
    print(f"Found at index {idx2}, JSON length: {len(raw2)}")
    try:
        data2 = json.loads(raw2)
        print(f"Root keys: {list(data2.keys())}")
        # Look for book/category lists
        for k, v in data2.items():
            if isinstance(v, dict):
                subkeys = list(v.keys())[:8]
                print(f"  {k}: dict, keys={subkeys}")
                for k2 in subkeys:
                    vv = v.get(k2)
                    if isinstance(vv, list) and len(vv) > 0 and isinstance(vv[0], dict):
                        print(f"    -> {k2}: list[{len(vv)}] keys={list(vv[0].keys())[:10]}")
                        if 'book_name' in vv[0]:
                            print(f"    sample: {vv[0].get('book_name','')[:50]} {vv[0].get('author','')[:20]}")
    except Exception as e:
        print(f"  JSON parse error: {e}")

# 2. 红袖 - 更多关键词
print("\n=== 红袖更多关键词 ===")
keywords = ["青春", "初三", "初中", "治愈", "成长", "校园言情", "重生校园"]
for kw in keywords:
    try:
        r3 = S.get(f"https://www.hongxiu.com/so/{kw}", timeout=15)
        seen = set()
        books = []
        for m in re.finditer(r'href="(/book/\d+)"[^>]*>([^<]+)</a>', r3.text):
            title = m.group(2).strip()
            if title not in seen and '详情' not in title and len(title) > 1:
                seen.add(title)
                if len(books) < 10:
                    books.append((title, m.group(1)))
        print(f"  '/so/{kw}': {len(seen)} unique books")
        for t, h in books[:8]:
            print(f"    {t:25s} -> {h}")
    except Exception as e:
        print(f"  '/so/{kw}': ERROR {e}")

# 3. 尝试从红袖图书详情页获取更多信息
print("\n=== 红袖详情页信息 ===")
sample_book = "/book/13934054205556304"  # 青藤心事——中学时代 (校园题材)
r4 = S.get(f"https://www.hongxiu.com{sample_book}", timeout=15)
h4 = r4.text
print(f"Detail page: {len(h4)} bytes")
# Look for book info meta
for m in re.finditer(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', h4):
    print(f"  Description: {m.group(1)[:200]}")
# Look for word count, chapter count
for pattern in [r'(\d+[\.\d]*万?字)', r'(\d+章)', r'(\d+[\.\d]*万?)']:
    for m in re.finditer(pattern, h4[:50000]):
        print(f"  Found: {m.group(1)}")
# Show all meta tags
for m in re.finditer(r'<meta[^>]*>', h4):
    content = m.group(0)
    if 'book' in content.lower() or 'novel' in content.lower() or 'description' in content.lower():
        print(f"  Meta: {content[:200]}")

# 4. Also check what tags/categories the book has
print(f"\n  HTML 2000 chars around 'word' or 'count' or 'chapter':")
for keyword in ['word', 'chapter', '字数', '章节', '连载', '状态']:
    idx = h4.lower().find(keyword.lower())
    if idx > 0:
        print(f"  Found '{keyword}' at {idx}:")
        print(f"    {h4[max(0,idx-50):idx+150]}")
