#!/usr/bin/env python3
"""Test snssdk search API with proper encoding and full response."""
import requests, json

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
})

# Test novels from existing DB (first 10 Fanqie)
novels = [
    ("7296935453201244172", "重生之都市仙尊"),
    ("7314905766182929958", "我在精神病院学斩神"),
    ("7369852758321103423", "整座大山都是我的猎场"),
    ("7421891571487973642", "从齐天大圣到大佬只用了三年"),
    ("7419599866977677863", "我不做人了"),
    ("7417272121971591433", "你们练武我种田"),
    ("7428701072452495626", "我的诡异能复活"),
    ("7447151763282828299", "这个游戏不简单"),
    ("7433986421027488056", "七味书屋"),
    ("7361919233818272263", "七味书屋"),
]

results = {}
for novel_id, name in novels:
    try:
        params = {"q": name, "aid": "1967"}
        r = S.get(
            "https://novel.snssdk.com/api/novel/channel/homepage/search/search/v1/",
            params=params,
            timeout=10,
        )
        data = r.json()
        ret_data = data.get('data', {}).get('ret_data', [])

        matches = []
        for item in ret_data[:3]:
            match = {
                "book_id": item.get("book_id"),
                "title": item.get("title", ""),
                "category": item.get("category", ""),
                "creation_status": item.get("creation_status"),
                "genre": item.get("genre", ""),
                "word_number": item.get("word_number"),
                "author": item.get("author", ""),
            }
            matches.append(match)

        results[f"{novel_id}|{name}"] = {
            "status": r.status_code,
            "total_results": len(ret_data),
            "matches": matches,
        }
    except Exception as e:
        results[f"{novel_id}|{name}"] = {"error": str(e)}

# Print results
print(json.dumps(results, ensure_ascii=False, indent=2))
