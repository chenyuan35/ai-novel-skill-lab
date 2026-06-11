#!/usr/bin/env python3
import urllib.parse
import requests
from bs4 import BeautifulSoup

r = requests.Session()
r.headers.update({"User-Agent": "Mozilla/5.0"})

kw = urllib.parse.quote('重生')
url = 'https://www.jjwxc.net/search.php?search_type=all&keywords=' + kw + '&page=1'
resp = r.get(url, timeout=10)
resp.encoding = 'gb18030'

soup = BeautifulSoup(resp.text, 'lxml')

# Find all tags with 'book' or 'onebook' or 'novel'
print("All tags with 'onebook':")
for a in soup.select('a[href*="onebook"]:first(20)'):
    print(f'  {a.get_text(strip=True)[:50]} (nid={a.get("href")[:60]})')

print("\nAll tags with 'book' in href:")
for a in soup.select('a[href*="book"][:20]'):
    print(f'  {a.get_text(strip=True)[:50]} href={a.get("href")[:80]}')

print("\nDivs with 'novel' in class:")
for d in soup.select('div[class*="novel"][:20]'):
    print(f'  class={d.get("class")} text={d.get_text(strip=True)[:50]}')

print("\nFirst 500 chars of soup:")
print(str(soup)[:500])

print("\nTitle tag:")
title = soup.find('title')
if title:
    print(f'  {title.get_text()[:200]}')
