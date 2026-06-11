#!/usr/bin/env python3
"""深入检查各平台可爬取内容的HTML结构和URL模式"""
import requests, re, json

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# 1. 红袖 - 详细的排行+搜索HTML分析
print("=== 红袖排行页详细分析 ===")
r = S.get("https://www.hongxiu.com/rank", timeout=15)
# 看排行tab/分类筛选
for m in re.finditer(r'<a[^>]*href=["\']([^"\']*rank[^"\']*)["\'][^>]*>([^<]+)</a>', r.text):
    print(f"  Rank tab: {m.group(2).strip():20s} -> {m.group(1)}")

# 看排行列表里实际的小说信息
for m in re.finditer(r'<li>\s*<span[^>]*class="num\d"[^>]*>(\d+)</span>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', r.text):
    print(f"  Rank #{m.group(1):2s}: {m.group(3).strip():25s} -> {m.group(2)}")

# 红袖 - 查看小说详情页结构（看有没有需要的信息）
print("\n=== 红袖搜索页详细分析 ===")
r2 = S.get("https://www.hongxiu.com/search?keyword=重生校园", timeout=15)
h2 = r2.text
print(f"Size: {len(h2)} bytes")
# 保存10KB片段看看格式
idx = h2.find('search')
if idx < 0: idx = 500
# 找所有链接
links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', h2)
print(f"Total links: {len(links)}")
for href, text in links[:30]:
    print(f"  {text.strip():30s} -> {href}")

# 2. 番茄 - 更仔细地找__INITIAL_STATE__
print("\n=== 番茄详细HTML分析 ===")
for url, label in [
    ("https://fanqienovel.com/", "首页"),
    ("https://fanqienovel.com/search?keyword=重生校园", "搜索"),
    ("https://fanqienovel.com/search?keyword=校园", "搜索2"),
]:
    r3 = S.get(url, timeout=15)
    h3 = r3.text
    print(f"\n{label}: {len(h3)} bytes")
    # 看看有没有window.变量
    for m in re.finditer(r'window\.(\w+)\s*=', h3):
        print(f"  window.{m.group(1)}")
    # 找script里的JSON
    for m in re.finditer(r'<script[^>]*id=["\']__NEXT_DATA__["\'](.*?)</script>', h3, re.S):
        print(f"  __NEXT_DATA__ found: {m.group(0)[:200]}")
    for m in re.finditer(r'<script[^>]*>(.*?)</script>', h3, re.S):
        content = m.group(1)[:300]
        if '__INITIAL__' in content or '__NUXT' in content:
            print(f"  SSR data: {content[:500]}")
        if 'novel' in content.lower() or 'book' in content.lower():
            if 'api' not in content.lower():
                pass  # skip normal scripts

# 3. 番茄API尝试
print("\n=== 番茄API尝试 ===")
for api_url in [
    "https://fanqienovel.com/api/novel/search?keyword=重生校园",
    "https://api.fanqienovel.com/api/novel/search?keyword=重生校园",
    "https://novel.snssdk.com/api/novel/search?keyword=重生校园",
]:
    try:
        r4 = S.get(api_url, timeout=10)
        ct = r4.headers.get('content-type','')
        print(f"{api_url}: status={r4.status_code}, size={len(r4.text)}, type={ct[:50]}")
        if 'json' in ct or r4.text.startswith('{'):
            data = r4.json()
            print(f"  Keys: {list(data.keys())}")
    except Exception as e:
        print(f"{api_url}: ERROR {e}")

# 4. 和图书搜索详情
print("\n=== 和图书搜索详情 ===")
for kw in ["重生校园", "学霸青春", "治愈成长"]:
    r5 = S.get(f"https://www.hetushu.com/search?keyword={kw}", timeout=15)
    h5 = r5.text
    books = re.findall(r'href=["\']([^"\']*/book/\d+[^"\']*)["\'][^>]*>([^<]{2,40})</a>', h5)
    print(f"  '{kw}': {len(books)} books")
    for href, title in books[:5]:
        print(f"    {title.strip():25s} -> {href}")
    # Show HTML around first book result
    if books:
        idx = h5.find(f'>{books[0][1].strip()}<')
        if idx > 0:
            print(f"  HTML context: ...{h5[max(0,idx-200):idx+len(books[0][1])+200]}...")

# 5. 红袖排行的不同榜单
print("\n=== 红袖不同榜单 ===")
for rank_url in [
    "https://www.hongxiu.com/rank/click",  # 点击榜
    "https://www.hongxiu.com/rank/recomm",  # 推荐榜
    "https://www.hongxiu.com/rank/collect",  # 收藏榜
    "https://www.hongxiu.com/rank/up",  # 新书榜
    "https://www.hongxiu.com/rank/finish",  # 完本榜
]:
    try:
        r6 = S.get(rank_url, timeout=15)
        books = re.findall(r'<a[^>]*href="(/book/\d+)"[^>]*>([^<]+)</a>', r6.text)
        print(f"  {rank_url.split('/')[-1]}: {len(books)} books")
        for href, title in books[:3]:
            print(f"    {title.strip():25s} -> {href}")
    except Exception as e:
        print(f"  {rank_url}: ERROR {e}")
