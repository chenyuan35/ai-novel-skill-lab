#!/usr/bin/env python3
"""Debug Fanqie genre extraction."""
import requests, re, json

urls = [
    ("206", "https://fanqienovel.com/page/7296935453201244172"),
    ("207", "https://fanqienovel.com/page/7314905766182929958"),
    ("211", "https://fanqienovel.com/page/7369852758321103423"),
]

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

for nid, url in urls:
    r = S.get(url, timeout=15)
    html = r.text
    print(f"\n=== novel_id={nid} (len={len(html)}) ===")

    # Search for category-related JSON fields
    for pat in ["completeCategory", "category", "creationStatus", "wordNumber", "genre"]:
        for m in re.finditer(pat, html):
            idx = html.find(m.group())
            ctx = html[max(0,idx-20):idx+80]
            print(f"  '{pat}' -> ...{ctx}...")
            break
        else:
            print(f"  '{pat}': NOT FOUND")

    # Try to find the pageData/initData JSON
    for pat in ["pageData", "initData", "bookInfo", "props"]:
        for m in re.finditer(pat, html):
            idx = html.find(m.group())
            ctx = html[max(0,idx-20):idx+120]
            print(f"  '{pat}' -> ...{ctx}...")
            break
        else:
            print(f"  '{pat}': NOT FOUND")
