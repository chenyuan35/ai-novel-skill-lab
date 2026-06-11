#!/usr/bin/env python3
"""调试脚本 - 测试各平台抓取"""
import urllib.parse
import cloudscraper
import requests
from bs4 import BeautifulSoup

s = cloudscraper.create_scraper()
r = requests.Session()
r.headers.update({"User-Agent": "Mozilla/5.0"})

kw = urllib.parse.quote('重生 校园')

# 起点
print("=== 起点 (cloudscraper) ===")
try:
    url = 'https://www.qidian.cn/search?kw=' + kw
    resp = s.get(url, timeout=15, allow_redirects=True)
    print(f'Status: {resp.status_code} Len: {len(resp.text)}')
    soup = BeautifulSoup(resp.text, 'lxml')
    items = soup.select('.book-multiple-info, .book-info, h4, h5')
    print(f'Items found: {len(items)}')
    if items:
        print('First item:', items[0].get_text(strip=True)[:200])
except Exception as e:
    print(f'Error: {e}')

# 晋江
print("\n=== 晋江 ===")
try:
    url = 'https://www.jjwxc.net/search.php?search_type=all&keywords=' + kw + '&page=1'
    resp = r.get(url, timeout=10)
    resp.encoding = 'gb18030'
    print(f'Status: {resp.status_code} Len: {len(resp.text)}')
    soup = BeautifulSoup(resp.text, 'lxml')
    items = soup.select('table tr')
    print(f'Table rows: {len(items)}')
    for item in items[:3]:
        name_m = item.select_one('a[href*="onebook.php"]')
        if name_m:
            print(f'  Found: {name_m.get_text(strip=True)}')
except Exception as e:
    print(f'Error: {e}')

# 纵横
print("\n=== 纵横 ===")
try:
    url = 'https://so.zongheng.com/search?keyword=' + urllib.parse.quote('重生')
    resp = r.get(url, timeout=10)
    print(f'Status: {resp.status_code} Len: {len(resp.text)}')
    soup = BeautifulSoup(resp.text, 'lxml')
    items = soup.select('.book-item')
    print(f'Items: {len(items)}')
except Exception as e:
    print(f'Error: {e}')
