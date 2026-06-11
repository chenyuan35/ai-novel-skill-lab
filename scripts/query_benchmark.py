#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/root/novel-crawler/benchmark.db')
c = conn.cursor()
c.execute('SELECT novel_name, author, chapter_count, word_count, status, tags FROM novels ORDER BY word_count DESC')
print(f"{'小说名':25s} {'作者':12s} {'章节':6s} {'字数':10s} {'状态':10s} {'标签'}")
print("-"*90)
for r in c.fetchall():
    print(f'{r[0]:25s} | {r[1]:12s} | {str(r[2])+"章":6s} | {str(r[3]):>8s}字 | {r[4]:10s} | {r[5]}')
c.execute('SELECT trope, count FROM trope_stats ORDER BY count DESC')
print("\n=== 标签统计 ===")
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')
