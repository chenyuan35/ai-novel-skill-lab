#!/bin/bash
# 检查服务器网络和代理
echo "=== PROXY ==="
env | grep -i proxy || echo "NO_PROXY_SET"
echo "=== DNS ==="
nslookup www.qidian.cn 2>&1 || echo "DNS_FAIL"
echo "=== CLOUDSCRAPER TEST ==="
python3 -c "
import cloudscraper
s = cloudscraper.create_scraper()
try:
    r = s.get('https://www.qidian.cn', timeout=15)
    print(f'qidian: status={r.status_code} len={len(r.text)}')
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1
