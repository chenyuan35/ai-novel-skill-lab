#!/usr/bin/env python3
"""Check Fanqie API endpoints for novel details."""
import requests, json

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# Try multiple Fanqie APIs
apis = [
    "https://novel.snssdk.com/api/novel/book/detail/v2?book_id={}",
    "https://api5-normal-sinfonlineb.fqnovel.com/reading/bookapi/detail/v1/?book_id={}",
    "https://api.fanqienovel.com/api/novel/detail/v1?novel_id={}",
]

novel_ids = ["7296935453201244172", "7314905766182929958", "7369852758321103423"]

for nid in novel_ids:
    print(f"\n=== novel_id={nid} ===")
    for api_tpl in apis:
        url = api_tpl.format(nid)
        try:
            r = S.get(url, timeout=10)
            data = r.json()
            # Check for wordNumber, category, creationStatus
            has_data = False
            for key in ["wordNumber", "category", "completeCategory", "creationStatus", "word_count", "data"]:
                path = ["data", key]
                val = data
                try:
                    for k in path:
                        val = val[k]
                except (KeyError, TypeError):
                    continue
                has_data = True
            if has_data:
                print(f"  API: {url[:60]}...")
                print(f"    {json.dumps(data, ensure_ascii=False)[:300]}")
        except Exception as e:
            print(f"  ERR {api_tpl[:50]}: {e}")

    # Also search HTML for any JSON-like data
    r = S.get(f"https://fanqienovel.com/page/{nid}", timeout=15)
    html = r.text
    # Try to find any script tags with data
    import re
    scripts = re.findall(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if scripts:
        print(f"  __NEXT_DATA__ found in SSR (len={len(scripts[0])})")
        try:
            parsed = json.loads(scripts[0])
            print(f"    props: {json.dumps(parsed, ensure_ascii=False)[:300]}")
        except:
            print(f"    (not valid JSON)")
    else:
        print(f"  __NEXT_DATA__: NOT FOUND in SSR")

    # Search for any JSON block
    for m in re.finditer(r'window\.__NUXT__\s*=\s*({.*?});', html, re.DOTALL):
        print(f"  __NUXT__ found (len={len(m.group(1))})")
