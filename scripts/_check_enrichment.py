import sqlite3, os
db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "novel-crawler", "benchmark.db"))
c = sqlite3.connect(db)
c.row_factory = sqlite3.Row

# Check word_count from rank scrape
rows = c.execute("SELECT id, novel_name, word_count, source, category, creation_status, genre FROM novels WHERE platform='番茄' ORDER BY id").fetchall()
print(f"Total Fanqie novels: {len(rows)}")
print(f"With word_count > 0: {sum(1 for r in rows if r['word_count'] > 0)}")
print(f"With category: {sum(1 for r in rows if r['category'])}")
print(f"With creation_status: {sum(1 for r in rows if r['creation_status'] is not None)}")
print(f"With genre: {sum(1 for r in rows if r['genre'])}")
print()
print(f"{'id':>3} {'word_cnt':>8} {'cs':>3} {'cat':<16} {'genre':<6} {'source':<12} {'name':<30}")
print("-"*90)
for r in rows:
    cs = r['creation_status']
    cs_str = ('完结' if cs == 0 else '连载' if cs == 1 else str(cs))
    print(f"{r['id']:>3} {r['word_count']:>8} {cs_str:>3} {str(r['category'] or ''):<16} {str(r['genre'] or ''):<6} {(r['source'] or ''):<12} {(r['novel_name'] or ''):<30}")
print("\n--- Novels with word_count > 0 ---")
for r in rows:
    if r['word_count'] > 0:
        print(f"  id={r['id']} {r['novel_name']}: {r['word_count']}")
