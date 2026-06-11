#!/usr/bin/env python3
import urllib.parse
import cloudscraper
import requests
from bs4 import BeautifulSoup

s = cloudscraper.create_scraper()
r = requests.Session()
r.headers.update({"User-Agent": "Mozilla/5.0"})

kw = urllib.parse.quote('重生 校园')

print("=== JJWXC ===")
try:
    url = 'https://www.jjwxc.net/search.php?search_type=all&keywords=' + kw + '&page=1'
    resp = r.get(url, timeout=10)
    resp.encoding = 'gb18030'
    print(f'Status: {resp.status_code} Len: {len(resp.text)}')
    soup = BeautifulSoup(resp.text, 'lxml')
    items = soup.select('table tr')
    print(f'Table rows: {len(items)}')
    found = 0
    for item in items[:10]:
        name_m = item.select_one('a[href*="onebook.php"]')
        if name_m:
            name = name_m.get_text(strip=True)
            print(f'  FOUND: {name}')
            found += 1
    print(f'Total found in first 10 rows: {found}')
except Exception as e:
    print(f'Error: {e}')
