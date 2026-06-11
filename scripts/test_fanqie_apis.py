#!/usr/bin/env python3
"""Test Fanqie API endpoints found in techoc/fanqie-novel-api."""
import requests, json, re, time

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
})

novel_ids = {
    "7296935453201244172": "重生之都市仙尊",
    "7314905766182929958": "我在精神病院学斩神",
    "7369852758321103423": "整座大山都是我的猎场",
}

# 1. Search API (snssdk)
print("=" * 60)
print("1. snssdk Search API")
print("=" * 60)
for name in list(novel_ids.values())[:1]:
    params = {"q": name, "aid": "1967"}
    r = S.get("https://novel.snssdk.com/api/novel/channel/homepage/search/search/v1/", params=params, timeout=10)
    print(f"Search '{name}': status={r.status_code}, len={len(r.text)}")
    try:
        data = r.json()
        print(f"  code={data.get('code')}, msg={data.get('message')[:100]}")
        ret_data = data.get('data', {}).get('ret_data', [])
        if ret_data:
            print(f"  results: {len(ret_data)}")
            for item in ret_data[:2]:
                print(f"    book_id={item.get('book_id')} title={item.get('title')} category={item.get('category')} creation_status={item.get('creation_status')} genre={item.get('genre')}")
    except:
        print(f"  (not JSON: {r.text[:200]})")
print()

# 2. Search book API (fanqienovel.com)
print("=" * 60)
print("2. fanqienovel.com search book API")
print("=" * 60)
for name in list(novel_ids.values())[:1]:
    params = {"filter": "127,127,127,127", "page_count": "10", "page_index": "0", "query_type": "0", "query_word": name}
    r = S.get("https://fanqienovel.com/api/author/search/search_book/v1", params=params, timeout=10)
    print(f"Search '{name}': status={r.status_code}, len={len(r.text)}")
    try:
        data = r.json()
        print(f"  code={data.get('code')}, msg={data.get('message','')[:100]}")
        book_list = data.get('data', {}).get('search_book_data_list', [])
        if book_list:
            print(f"  results: {len(book_list)}")
            for item in book_list[:2]:
                print(f"    book_id={item.get('book_id')} name={item.get('book_name')} author={item.get('author')}")
                print(f"      word_count={item.get('word_count')} category={item.get('category')} creation_status={item.get('creation_status')}")
        else:
            print(f"  data keys: {list(data.get('data', {}).keys()) if data.get('data') else 'N/A'}")
    except:
        print(f"  (not JSON: {r.text[:200]})")
print()

# 3. Directory API (fanqienovel.com)
print("=" * 60)
print("3. fanqienovel.com directory API")
print("=" * 60)
for nid in list(novel_ids.keys())[:1]:
    params = {"bookId": nid}
    r = S.get("https://fanqienovel.com/api/reader/directory/detail", params=params, timeout=10)
    print(f"bookId={nid}: status={r.status_code}, len={len(r.text)}")
    try:
        data = r.json()
        print(f"  code={data.get('code')}, msg={data.get('message','')[:100]}")
        chapters = data.get('data', {}).get('chapterListWithVolume', [])
        print(f"  chapters: {len(chapters)} volumes, first={len(chapters[0]) if chapters else 0} chapters")
        if chapters and len(chapters[0]) > 0:
            print(f"  first chapter: id={chapters[0][0].get('itemId')} title={chapters[0][0].get('title')}")
    except:
        print(f"  (not JSON: {r.text[:200]})")
print()

# 4. Try reading content API (snssdk) for novel_data
print("=" * 60)
print("4. snssdk content API (novel_data)")
print("=" * 60)
# First get a chapter ID from directory API
params = {"bookId": "7296935453201244172"}
r = S.get("https://fanqienovel.com/api/reader/directory/detail", params=params, timeout=10)
try:
    data = r.json()
    chapters = data.get('data', {}).get('chapterListWithVolume', [])
    if chapters and len(chapters[0]) > 0:
        first_chapter_id = chapters[0][0].get('itemId')
        print(f"First chapter ID: {first_chapter_id}")

        params = {
            "device_platform": "android",
            "parent_enterfrom": "novel_channel_search.tab.",
            "aid": "2329",
            "platform_id": "1967",
            "group_id": str(first_chapter_id),
            "item_id": str(first_chapter_id),
        }
        r2 = S.get("https://novel.snssdk.com/api/novel/book/reader/full/v1/", params=params, timeout=10)
        print(f"Content API: status={r2.status_code}, len={len(r2.text)}")
        try:
            data2 = r2.json()
            novel_data = data2.get('data', {}).get('novel_data', {})
            if novel_data:
                print(f"  book_name={novel_data.get('book_name')}")
                print(f"  category={novel_data.get('category')}")
                print(f"  category_id={novel_data.get('category_id')}")
                print(f"  creation_status={novel_data.get('creation_status')}")
                print(f"  word_number={novel_data.get('word_number')}")
                print(f"  genre={novel_data.get('genre')}")
                print(f"  sub_genre={novel_data.get('sub_genre')}")
            else:
                print(f"  data keys: {list(data2.get('data', {}).keys()) if data2.get('data') else 'N/A'}")
        except:
            print(f"  (not JSON: {r2.text[:200]})")
except:
    print(f"  directory API failed")
print()

# 5. Try all search API variants
print("=" * 60)
print("5. Additional API tests")
print("=" * 60)
more_apis = [
    ("search title", "GET", "https://novel.snssdk.com/api/novel/channel/homepage/search/search/v1/", {"q": "重生", "aid": "1967"}),
    ("detail v2", "GET", "https://novel.snssdk.com/api/novel/book/detail/v2/", {"book_id": "7296935453201244172", "aid": "1967"}),
    ("detail v1", "GET", "https://novel.snssdk.com/api/novel/detail/v1/", {"novel_id": "7296935453201244172", "aid": "1967"}),
    ("homepage", "GET", "https://novel.snssdk.com/api/novel/channel/homepage/v3/", {"aid": "1967", "offset": "0"}),
]
for label, method, url, params in more_apis:
    try:
        if method == "GET":
            r = S.get(url, params=params, timeout=10)
            print(f"{label}: status={r.status_code}")
            try:
                data = r.json()
                snippet = json.dumps(data, ensure_ascii=False)[:200]
                print(f"  {snippet}")
            except:
                print(f"  (not JSON: {r.text[:150]})")
    except Exception as e:
        print(f"  {label}: ERROR {e}")
