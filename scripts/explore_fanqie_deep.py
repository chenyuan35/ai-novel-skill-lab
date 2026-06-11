#!/usr/bin/env python3
"""Check fanqie search data structure and hongxiu detail page meta"""
import requests, re, json

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# 1. 番茄搜索页 - 检查searchBookList结构
print("=== 番茄搜索page SSR ===")
r = S.get("https://fanqienovel.com/search?keyword=校园", timeout=15)
h = r.text
idx = h.find('window.__INITIAL_STATE__')
if idx > 0:
    start = h.find('{', idx)
    depth = 0
    end = start
    for i in range(start, len(h)):
        if h[i] == '{': depth += 1
        elif h[i] == '}': depth -= 1
        if depth == 0:
            end = i + 1
            break
    data = json.loads(h[start:end])
    # Focus on search data
    sr = data.get('search', {})
    print(f"search keys: {list(sr.keys())}")
    total = sr.get('total')
    print(f"search total: {total}")
    book_list = sr.get('searchBookList')
    if book_list and isinstance(book_list, list):
        print(f"searchBookList: {len(book_list)} items")
        for i, book in enumerate(book_list[:10]):
            if isinstance(book, dict):
                print(f"  [{i}] keys: {list(book.keys())}")
                # Print core fields
                for k in ['bookName', 'bookId', 'author', 'abstract', 'category', 'wordNumber', 'chapterCount', 'thumbUri', 'subCategory', 'createTime', 'completeTime', 'status', 'score', 'readCount']:
                    if k in book:
                        v = book[k]
                        if isinstance(v, str) and len(v) > 100:
                            v = v[:100]
                        print(f"      {k}: {v}")
            print()
    # Also check if there's a rank section
    rank = data.get('rank', {})
    if rank and isinstance(rank, dict):
        for rk, rv in rank.items():
            if isinstance(rv, list) and len(rv) > 0 and isinstance(rv[0], dict):
                print(f"\nrank.{rk}: list[{len(rv)}], keys={list(rv[0].keys())}")
                for item in rv[:3]:
                    book_name = item.get('bookName', '') or item.get('book_name', '')
                    author = item.get('author', '')
                    print(f"  {book_name} by {author}")

# 2. 番茄首页 - 看分类列表结构
print("\n\n=== 番茄首页 girlList/boyList ===")
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
    data2 = json.loads(h2[start2:end2])
    home = data2.get('home', {})
    for lst_name in ['girlList', 'boyList', 'weekList', 'editorList', 'subscribeList', 'workhardList', 'writerList']:
        lst = home.get(lst_name)
        if lst and isinstance(lst, list) and len(lst) > 0 and isinstance(lst[0], dict):
            print(f"\n{lst_name}: {len(lst)} items")
            print(f"  sample keys: {list(lst[0].keys())}")
            for item in lst[:5]:
                bn = item.get('bookName', '') or item.get('name', '')
                au = item.get('author', '')
                cat = item.get('category', '') or item.get('abstract','')[:60]
                print(f"  {bn:25s} by {au:15s} cat={cat}")

# 3. Also try fanqie rank page
print("\n\n=== 番茄排行页 ===")
r3 = S.get("https://fanqienovel.com/rank", timeout=15)
h3 = r3.text
idx3 = h3.find('window.__INITIAL_STATE__')
if idx3 > 0:
    start3 = h3.find('{', idx3)
    depth = 0
    end3 = start3
    for i in range(start3, len(h3)):
        if h3[i] == '{': depth += 1
        elif h3[i] == '}': depth -= 1
        if depth == 0:
            end3 = i + 1
            break
    data3 = json.loads(h3[start3:end3])
    rank = data3.get('rank', {})
    for rk, rv in rank.items():
        if isinstance(rv, list) and len(rv) > 0 and isinstance(rv[0], dict):
            keys = list(rv[0].keys())
            print(f"rank.{rk}: list[{len(rv)}], keys={keys}")
            for item in rv[:3]:
                bn = item.get('bookName', '') or item.get('book_name', '') or str(item)[:80]
                print(f"  {bn}")
        elif isinstance(rv, list):
            print(f"rank.{rk}: list[{len(rv)}]")
