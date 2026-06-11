#!/usr/bin/env python3
"""Debug JJWXC genre extraction."""
import requests, re

r = requests.get("https://www.jjwxc.net/onebook.php?novelid=1", timeout=15)
r.encoding = "gb18030"
h = r.text

# Check genre-related patterns around "genre"
for pat in ["genre", "类型", "分类", "原创", "纯爱", "言情", "奇幻"]:
    for m in re.finditer(pat, h):
        idx = h.find(m.group())
        ctx = h[max(0,idx-60):idx+120]
        print(f"'{pat}' -> ...{ctx}...")
        break
    else:
        print(f"'{pat}': NOT FOUND")

print()
print("--- wordCount context ---")
idx = h.find("wordCount")
if idx >= 0:
    print(h[max(0,idx-40):idx+80])
