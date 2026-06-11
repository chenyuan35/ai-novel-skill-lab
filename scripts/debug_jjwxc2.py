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

print("All tags with 'onebook':")
found = []
for a in soup.find_all('a', href=True):
    if 'onebook' in a.get('href', ''):
        found.append(a)
        print(f'  {a.get_text(strip=True)[:50]} href={a.get("href")[:80]}')
print(f'Total: {len(found)}')

print("\n\nTable analysis:")
for table in soup.find_all('table'):
    rows = table.find_all('tr')
    print(f'  Table has {len(rows)} rows')
    if rows:
        # Print first row's structure
        for td in rows[0].find_all(['td', 'th']):
            txt = td.get_text(strip=True)[:80]
            if txt:
                print(f'    TD: {txt}')

# Save raw HTML for analysis
with open('/tmp/jjwxc_debug.html', 'w', encoding='gb18030') as f:
    f.write(resp.text)
print(f"\nSaved raw HTML to /tmp/jjwxc_debug.html ({len(resp.text)} chars)")
