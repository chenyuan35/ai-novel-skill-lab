#!/usr/bin/env python3
import socket
for domain in ['www.qidian.cn', 'www.jjwxc.net', 'www.fanqienovel.com', 'www.zongheng.com', 'www.qqread.com', 'www.qimao.com']:
    try:
        ip = socket.gethostbyname(domain)
        print(f'{domain} -> {ip} OK')
    except socket.gaierror as e:
        print(f'{domain} -> FAILED: {e}')
