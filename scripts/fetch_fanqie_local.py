#!/usr/bin/env python3
"""Fetch Fanqie novel data from local machine where DNS resolves."""
import requests, re, json, sqlite3, time, sys

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

# Get Fanqie novels from SQlite via SSH tunnel or local copy
# For now, test a few directly via HTTP

test_ids = [
    "7296935453201244172",
    "7314905766182929958",
    "7369852758321103423",
    "7421891571487973642",
    "7419599866977677863",
]

print("Testing Fanqie pages from local machine...\n")
for nid in test_ids:
    url = f"https://fanqienovel.com/page/{nid}"
    try:
        r = S.get(url, timeout=15)
        html = r.text
        print(f"novel_id={nid} (len={len(html)})")

        wc = re.search(r'"wordNumber"\s*:\s*(\d+)', html)
        cs = re.search(r'"creationStatus"\s*:\s*(\d+)', html)
        cat = re.search(r'"completeCategory"\s*:\s*"([^"]+)', html)

        print(f"  wordNumber={wc.group(1) if wc else 'NOT FOUND'}")
        print(f"  creationStatus={cs.group(1) if cs else 'NOT FOUND'}")
        print(f"  completeCategory={cat.group(1) if cat else 'NOT FOUND'}")

        # Also search visible text
        for pat in ["万字", "字", "连载", "完结", "分类", "玄幻", "言情", "都市", "穿越", "悬疑"]:
            for m in re.finditer(pat, html):
                idx = html.find(m.group())
                ctx = html[max(0,idx-50):idx+50]
                print(f"  '{pat}' -> ...{ctx}...")
                break
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
    time.sleep(1)

# Try the API from local
print("\n\nTesting Fanqie API from local machine...\n")
api_urls = [
    "https://api.fanqienovel.com/api/novel/detail/v1?novel_id={}",
    "https://novel.snssdk.com/api/novel/book/detail/v2?book_id={}",
]
for nid in test_ids[:2]:
    for api_tpl in api_urls:
        url = api_tpl.format(nid)
        try:
            r = S.get(url, timeout=10)
            print(f"API: {url[:60]}... status={r.status_code}")
            try:
                data = r.json()
                print(f"  {json.dumps(data, ensure_ascii=False)[:400]}")
            except:
                print(f"  (not JSON: {r.text[:200]})")
        except Exception as e:
            print(f"  ERR: {e}")
    print()
