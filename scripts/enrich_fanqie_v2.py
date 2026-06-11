#!/usr/bin/env python3
"""Enrich Fanqie novels: category, creation_status, genre (via snssdk search)
   + word_count (via snssdk content API with chapter_id from directory API).

   Run from Windows where DB is at novel-crawler/benchmark.db.
   Falls back gracefully when APIs don't return data.
"""
import requests, sqlite3, json, time, re, sys, os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "novel-crawler", "benchmark.db")
DB_PATH = os.path.abspath(DB_PATH)

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
})

# ── Ensure enrichment columns exist ──
def ensure_columns(conn):
    c = conn.cursor()
    existing = [col[1] for col in c.execute("PRAGMA table_info(novels)").fetchall()]
    for col, typ in [("category", "TEXT"), ("creation_status", "INTEGER"),
                     ("genre", "TEXT"), ("genre_display", "TEXT")]:
        if col not in existing:
            c.execute(f"ALTER TABLE novels ADD COLUMN {col} {typ}")
            print(f"  Added column: {col}")
    conn.commit()


# ── Tier 1: snssdk search → category, creation_status, genre ──
def snssdk_search(name):
    """Search by title, return list of candidate books with snssdk book_ids."""
    params = {"q": name, "aid": "1967"}
    r = S.get(
        "https://novel.snssdk.com/api/novel/channel/homepage/search/search/v1/",
        params=params, timeout=10,
    )
    if r.status_code != 200:
        return []
    data = r.json()
    ret_data = data.get("data", {}).get("ret_data", [])
    candidates = []
    for item in ret_data:
        candidates.append({
            "book_id": str(item.get("book_id", "")),
            "title": item.get("title", ""),
            "author": item.get("author", ""),
            "category": item.get("category", ""),
            "creation_status": item.get("creation_status"),
            "genre": item.get("genre", ""),
            "word_number": item.get("word_number"),
        })
    return candidates


# ── Tier 2: Fanqie reader directory API → chapter list ──
def fanqie_directory(book_id):
    """Get chapter list for a book on fanqienovel.com.
       NOTE: book_id here is the snssdk book_id, not the fanqie web ID.
    """
    params = {"bookId": book_id}
    r = S.get("https://fanqienovel.com/api/reader/directory/detail",
              params=params, timeout=10)
    if r.status_code != 200:
        return None
    try:
        data = r.json()
        return data.get("data", {})
    except:
        return None


# ── Tier 3: snssdk content API → NovelData with word_number ──
def snssdk_content(chapter_id):
    """Get chapter content + novel data (word_number, etc.) from snssdk."""
    params = {
        "device_platform": "android",
        "parent_enterfrom": "novel_channel_search.tab.",
        "aid": "2329",
        "platform_id": "1967",
        "group_id": str(chapter_id),
        "item_id": str(chapter_id),
    }
    r = S.get("https://novel.snssdk.com/api/novel/book/reader/full/v1/",
              params=params, timeout=10)
    if r.status_code != 200:
        return None
    try:
        data = r.json()
        novel_data = data.get("data", {}).get("novel_data", {})
        if novel_data:
            return {
                "word_number": novel_data.get("word_number"),
                "book_id": str(novel_data.get("book_id", "")),
                "book_name": novel_data.get("book_name", ""),
                "category": novel_data.get("category", ""),
                "creation_status": novel_data.get("creation_status"),
                "genre": novel_data.get("genre", ""),
            }
        return None
    except:
        return None


# ── Score candidates to find best match ──
def best_match(candidates, novel_name, novel_id):
    """Score candidates: exact title match is best, partial is ok.
       Returns the best candidate or None.
    """
    if not candidates:
        return None

    # First: exact title match
    for c in candidates:
        if c["title"].strip() == novel_name.strip():
            return c

    # Second: partial match where novel_name is in title or vice versa
    for c in candidates:
        if novel_name[:4] in c["title"] or c["title"][:4] in novel_name:
            return c

    # Last: first candidate
    return candidates[0]


# ── Enrich all Fanqie novels ──
def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ensure_columns(conn)

    # Get all Fanqie novels
    c.execute("SELECT id, novel_id, novel_name FROM novels WHERE platform='番茄' ORDER BY id")
    rows = c.fetchall()
    print(f"Fanqie novels to process: {len(rows)}")

    stats = {"found_category": 0, "found_status": 0, "found_genre": 0,
             "found_wordcount": 0, "errors": 0, "no_match": 0}

    for i, (nid, novel_id, novel_name) in enumerate(rows):
        print(f"\n[{i+1}/{len(rows)}] id={nid} novel_id={novel_id} {novel_name[:30]}")

        # ── Step 1: snssdk search ──
        candidates = snssdk_search(novel_name)
        match = best_match(candidates, novel_name, novel_id)

        category = None
        creation_status = None
        genre = None
        word_count = None
        snssdk_book_id = None

        if not match:
            # If title search fails, try first few chars
            print(f"  ⚠ No match for '{novel_name}', trying short title...")
            candidates = snssdk_search(novel_name[:6])
            match = best_match(candidates, novel_name, novel_id)

        if match:
            category = match["category"]
            creation_status = match["creation_status"]
            genre = match["genre"]
            snssdk_book_id = match["book_id"]
            print(f"  ✓ snssdk: book_id={snssdk_book_id} cat={category} cs={creation_status} genre={genre}")
            if category:
                stats["found_category"] += 1
            if creation_status is not None:
                stats["found_status"] += 1
            if genre:
                stats["found_genre"] += 1

            # ── Step 2: Try directory API → chapter_id → word_number ──
            # Use snssdk book_id for directory API
            dir_data = fanqie_directory(snssdk_book_id)
            if dir_data:
                chapters = dir_data.get("chapterListWithVolume", [])
                total_chapters = dir_data.get("totalChapterNum", 0)
                print(f"  ⓘ directory: {total_chapters} chapters, {len(chapters)} volumes")
                if total_chapters > 0:
                    # Also try getting first chapter_id from the volume list
                    if chapters and len(chapters[0]) > 0:
                        first_chapter = chapters[0][0]
                        chapter_id = first_chapter.get("itemId")
                        if chapter_id:
                            print(f"  → Getting content for chapter_id={chapter_id}")
                            novel_data = snssdk_content(chapter_id)
                            if novel_data and novel_data["word_number"]:
                                word_count = int(novel_data["word_number"])
                                print(f"  ✓ word_count={word_count} ({word_count/10000:.1f}万字)")
                                stats["found_wordcount"] += 1
                            else:
                                print(f"  ⚠ content API returned no word_number")
                    else:
                        print(f"  ⚠ no chapters in volume list")
            else:
                print(f"  ⚠ directory API returned empty")
        else:
            stats["no_match"] += 1
            print(f"  ✗ No match found on snssdk")

        # ── Step 3: Update DB ──
        update_fields = {}
        if category is not None:
            update_fields["category"] = category
        if creation_status is not None:
            update_fields["creation_status"] = int(creation_status)
        if genre is not None:
            update_fields["genre"] = genre
        if word_count is not None:
            update_fields["word_count"] = word_count

        if update_fields:
            set_clause = ", ".join(f"{k}=?" for k in update_fields)
            values = list(update_fields.values()) + [nid]
            c.execute(f"UPDATE novels SET {set_clause} WHERE id=?", values)
            conn.commit()
            print(f"  💾 Updated {len(update_fields)} fields")

        time.sleep(0.8)  # Polite delay

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total: {len(rows)}")
    print(f"  With category: {stats['found_category']}")
    print(f"  With creation_status: {stats['found_status']}")
    print(f"  With genre: {stats['found_genre']}")
    print(f"  With word_count: {stats['found_wordcount']}")
    print(f"  No match: {stats['no_match']}")
    print(f"  Errors: {stats['errors']}")
    conn.close()


if __name__ == "__main__":
    main()
