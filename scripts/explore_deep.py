#!/usr/bin/env python3
"""深入分析各平台页面结构"""
import requests, re, json, sys

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# 1. 纵横 - check rank page structure in detail
print("=== 纵横-查看排行页核心内容 ===")
r = SESSION.get("https://www.zongheng.com/rank.html", timeout=15)
html = r.text
# Find all links
all_links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', html)
print(f"Total links: {len(all_links)}")
# Show rank-related links
for href, text in all_links:
    if 'rank' in href.lower() or '排行' in text:
        print(f"  {text.strip():20s} -> {href}")
# Show search
search = re.findall(r'<form[^>]*>(.*?)</form>', html, re.S)
print(f"Forms: {len(search)}")
for i, f in enumerate(search[:5]):
    inputs = re.findall(r'<input[^>]*>', f)
    print(f"  Form {i}: {inputs}")

# Check what the actual novel list looks like
book_sections = re.findall(r'<div[^>]*?class=["\'][^"\']*?book[^"\']*?["\'][^>]*?>', html, re.I)
print(f"Book divs: {len(book_sections)}")
# Look for data attributes
data_attrs = re.findall(r'data-[\w-]+=["\'][^"\']*["\']', html)
print(f"Data attributes: {len(data_attrs)}")

# 2. Check zongheng search more carefully
print("\n=== 纵横搜索(HTML) ===")
for kw in ["重生", "校园"]:
    r2 = SESSION.get(f"https://www.zongheng.com/search?keyword={kw}", timeout=15)
    print(f"  Search '{kw}': status={r2.status_code}, size={len(r2.text)}")
    # Look for search result items
    items = re.findall(r'<li[^>]*>(.*?)</li>', r2.text, re.S)
    links = re.findall(r'href=["\']([^"\']*book[^"\']*)["\'][^>]*>([^<]+)<', r2.text)
    print(f"  Book links found: {len(links)}")
    for href, text in links[:5]:
        print(f"    {text.strip():25s} -> {href}")
    if not links:
        # Show text content around keyword
        idx = r2.text.find(kw)
        if idx > 0:
            print(f"  Context around '{kw}': ...{r2.text[max(0,idx-100):idx+100]}...")

# 3. Hongxiu - check category pages
print("\n=== 红袖分类/搜索 ===")
r3 = SESSION.get("https://www.hongxiu.com/rank", timeout=15)
# Look for category filters
cats = re.findall(r'<a[^>]*href=["\']([^"\']*category[^"\']*|[^"\']*cat[^"\']*)["\'][^>]*>([^<]+)<', r3.text)
print(f"Category links: {cats[:10]}")
# Check search
r4 = SESSION.get("https://www.hongxiu.com/search?keyword=重生校园", timeout=15)
print(f"Search: status={r4.status_code}, size={len(r4.text)}")
links4 = re.findall(r'href=["\']([^"\']*book[^"\']*)["\'][^>]*>([^<]+)<', r4.text)
print(f"Book links: {len(links4)}")
for href, text in links4[:5]:
    print(f"  {text.strip():25s} -> {href}")

# 4. Qimao - try different search URL patterns
print("\n=== 七猫搜索测试 ===")
patterns = [
    "https://www.qimao.com/search/all/?key=重生校园",
    "https://www.qimao.com/search?keyword=重生校园",
    "https://www.qimao.com/shuku/search/?keyword=重生校园",
]
for url in patterns:
    try:
        r5 = SESSION.get(url, timeout=15, allow_redirects=True)
        links5 = re.findall(r'href=["\']([^"\']*(?:book|novel|shu)[^"\']*)["\'][^>]*>([^<]+)<', r5.text)
        print(f"  {url}: status={r5.status_code}, size={len(r5.text)}, books={len(links5)}")
        for href, text in links5[:5]:
            print(f"    {text.strip():25s} -> {href}")
    except Exception as e:
        print(f"  {url}: ERROR {e}")

# 5. Fanqie - check the main page and API
print("\n=== 番茄小说 API 探索 ===")
r6 = SESSION.get("https://fanqienovel.com/", timeout=15)
print(f"Main page: status={r6.status_code}, size={len(r6.text)}")
# Look for API endpoints
apis = re.findall(r'/api/[^"\']+', r6.text)
print(f"API endpoints found: {len(apis)}")
for a in apis[:15]:
    print(f"  {a}")
# Check for SSR data
ssr = re.findall(r'window\.__NUXT__|window\.__INITIAL_STATE__|window\.__DATA__', r6.text)
print(f"SSR state: {ssr}")

# 6. Hetushu - check search
print("\n=== 和图书搜索 ===")
r7 = SESSION.get("https://www.hetushu.com/search?keyword=重生校园", timeout=15)
print(f"Search: status={r7.status_code}, size={len(r7.text)}")
links7 = re.findall(r'href=["\']([^"\']*/book/[^"\']*)["\'][^>]*>([^<]+)<', r7.text)
print(f"Book links: {len(links7)}")
for href, text in links7[:5]:
    print(f"  {text.strip():25s} -> {href}")
