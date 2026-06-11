import sqlite3
c = sqlite3.connect(r'C:\Users\59314\claudework\ai-novel-skill-lab\novel-crawler\benchmark.db')
c.row_factory = sqlite3.Row
platforms = c.execute('SELECT DISTINCT platform, COUNT(*) as cnt FROM novels GROUP BY platform').fetchall()
for p in platforms:
    plat = p['platform']
    print(repr(plat), p['cnt'])

rows = c.execute('SELECT id, platform, novel_name FROM novels LIMIT 5').fetchall()
for r in rows:
    print(r['id'], repr(r['platform']), repr(r['novel_name']))
