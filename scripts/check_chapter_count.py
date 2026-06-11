"""Find chapter count on hongxiu detail pages and verify comment extraction."""
import requests, re

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

# Test with a book that has chapters
nid = "10055726104646703"
r = S.get(f"https://www.hongxiu.com/book/{nid}", timeout=15)
h = r.text

print(f"Page size: {len(h)} bytes")

# 1. Extract from comments: word count
wc = re.search(r'<!--.*?<span>([\d.]+)</span><em>(万字|千字)</em>.*?-->', h)
if wc:
    num = wc.group(1)
    unit = wc.group(2)
    print(f"\nWord count from comment: {num}{unit}")
    if "万" in unit:
        wc_val = int(float(num) * 10000)
    else:
        wc_val = int(num)
    print(f"  = {wc_val} words")

# 2. Search for chapter-related text everywhere
for pat in [r'(\d+)章', r'章节.*?(\d+)', r'共(\d+)', r'<span[^>]*class="[^"]*chapter[^"]*"[^>]*>(\d+)']:
    for m in re.finditer(pat, h):
        idx = h.find(m.group(0))
        ctx = h[max(0,idx-80):idx+80]
        print(f"\n  '{pat[:30]}' matched: {m.group(0)} at byte {idx}")
        print(f"    context: ...{ctx}...")

# 3. Check if there's a chapter list section
idx = h.find("章节目录")
if idx > 0:
    print(f"\n\n章节目录 found at byte {idx}, context:")
    print(h[idx:idx+500])

idx = h.find("chapter")
if idx > 0:
    print(f"\n\n'chapter' found at byte {idx}, context:")
    print(h[max(0,idx-100):idx+200])

# 4. Check for chapter list links
for m in re.finditer(r'href="(/chapter/\d+/\d+)"[^>]*>([^<]+)<', h):
    print(f"\n  Chapter link: {m.group(2)} -> {m.group(1)}")

# 5. Count chapter list URLs
chapters = re.findall(r'/chapter/\d+/\d+', h)
print(f"\n\nTotal chapter links found: {len(chapters)}")
