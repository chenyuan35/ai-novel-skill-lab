#!/usr/bin/env python3
"""Probe snssdk API endpoints for word_count data."""
import requests, json

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# Known working book from search: 萤火之城 book_id = 7218822722090961958
book_id = "7218822722090961958"

endpoints = [
    # Book detail
    ("book/detail/v1", {"book_id": book_id, "aid": "1967"}),
    ("book/info/v1", {"book_id": book_id, "aid": "1967"}),
    ("book/full/v1", {"book_id": book_id, "aid": "1967"}),
    # Try with item_id/group_id as book_id
    ("book/reader/full/v1", {"group_id": book_id, "item_id": book_id, "aid": "2329", "platform_id": "1967"}),
    # Different params
    ("book/reader/full/v1", {"group_id": book_id, "item_id": book_id, "aid": "1967"}),
    # Try the search with different params
    ("channel/homepage/search/search/v1", {"q": "萤火之城", "aid": "1967", "offset": "0", "count": "10"}),
]

for name, params in endpoints:
    url = f"https://novel.snssdk.com/api/novel/{name}/"
    try:
        r = S.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            # Check for word_number or word_count at any depth
            def find_keys(obj, target_keys, path=""):
                results = []
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in target_keys:
                            results.append((f"{path}.{k}", v))
                        results.extend(find_keys(v, target_keys, f"{path}.{k}"))
                return results
            matches = find_keys(data, {"word_number", "word_count", "total_word_number", "total_word_count", "wordNumber"})
            if matches:
                print(f"✓ {name}: found word keys: {matches}")
            else:
                # Check top-level keys
                ret_data = data.get("data", {})
                top_keys = list(ret_data.keys()) if ret_data else []
                print(f"  {name}: HTTP 200, top keys: {top_keys[:8]}")
        else:
            print(f"  {name}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  {name}: ERROR {e}")

# Try fanqie novel API
other_apis = [
    ("https://novel.snssdk.com/api/novel/book/detail/v1/", {"book_id": book_id}),
    ("https://novel.snssdk.com/api/novel/book/category/detail/v1/", {"book_id": book_id}),
    ("https://api.fanqienovel.com/api/reader/novel/detail/v1/", {"bookId": book_id}),
    ("https://api.fanqienovel.com/api/reader/novel/info/v1/", {"bookId": book_id}),
]
print()
for url, params in other_apis:
    try:
        r = S.get(url, params=params, timeout=10)
        print(f"  {url.split('/')[-2]}/{url.split('/')[-1]}: HTTP {r.status_code}, keys: {list(r.json().get('data',{}).keys())[:8] if r.status_code==200 else ''}")
    except Exception as e:
        print(f"  {url}: ERROR {e}")
