#!/usr/bin/env python3
"""Quick enrichment status check."""
import sqlite3
c = sqlite3.connect("/root/novel-crawler/benchmark.db").cursor()

for p in ["晋江文学城", "番茄", "红袖"]:
    c.execute("SELECT COUNT(*), SUM(CASE WHEN word_count>0 THEN 1 ELSE 0 END), SUM(CASE WHEN genre!='' THEN 1 ELSE 0 END), SUM(CASE WHEN chapter_count>0 THEN 1 ELSE 0 END) FROM novels WHERE platform=?", (p,))
    total, wc, genre, cc = c.fetchone()
    print(f"{p}: total={total}, word_count={wc or 0}, genre={genre or 0}, chapter_count={cc or 0}")

print()
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='番茄' AND word_count=0")
print(f"番茄 missing word_count ({c.rowcount}):")
for r in c.fetchall():
    print(f"  id={r[0]} nid={r[1]} name={r[2][:30]}")

print()
c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='晋江文学城' AND word_count=0")
print(f"晋江 missing word_count ({c.rowcount}):")
for r in c.fetchall():
    print(f"  id={r[0]} nid={r[1]} name={r[2][:30]}")
