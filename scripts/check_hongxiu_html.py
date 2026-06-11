import requests, re, json

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

nid = "14098206746138304"  # 青藤心事——中学时代
r = S.get(f"https://www.hongxiu.com/book/{nid}", timeout=15)
h = r.text

print(f"Page size: {len(h)} bytes")

# Search for word count related patterns
for kw in ["字数", "累计", "章节", "chapter"]:
    idx = h.lower().find(kw.lower())
    if idx > 0:
        ctx = h[max(0,idx-100):idx+150]
        print(f"\n===== '{kw}' at byte {idx} =====")
        print(ctx)

# Also look at meta tags more carefully
print("\n===== All meta tags =====")
for m in re.finditer(r'<meta[^>]*property="([^"]+)"[^>]*>', h):
    print(f"  {m.group(0)[:200]}")

# Look at what's in the HTML head
print(f"\n===== Head section (first 8000 chars) =====")
print(h[:8000])
