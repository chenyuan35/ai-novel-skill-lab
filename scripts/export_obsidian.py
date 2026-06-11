#!/usr/bin/env python3
"""Export benchmark.db novels to Obsidian-compatible Markdown vault."""
import sqlite3, os, json, textwrap

DB_PATH = os.path.join(os.environ["USERPROFILE"], "claudework", "ai-novel-skill-lab",
                        "novel-crawler", "benchmark.db")
OUTPUT = os.path.join(os.environ["USERPROFILE"], "claudework", "ai-novel-skill-lab",
                       "obsidian-vault")

# ── helpers ──────────────────────────────────────────────────────────────

def extract_category_and_tags(cat_val, genre_val):
    """Return (primary_category, tags_list) from the various data formats."""
    tags = []

    # Try parsing as JSON array (rank novel format)
    if cat_val and cat_val.startswith("["):
        try:
            objs = json.loads(cat_val)
            primary = ""
            for obj in objs:
                dim = obj.get("Dim")
                name = obj.get("Name", "")
                if dim == 1 and not primary:
                    primary = name  # top-level genre like "古代言情"
                if dim == 10 and name and name != primary:
                    tags.append(name)
                if dim == 2 and name:
                    tags.append(name)
                if dim == 3 and name:
                    tags.append(name)
            if not primary:
                # fallback: use MainCategory
                for obj in objs:
                    if obj.get("MainCategory"):
                        primary = obj.get("Name", "")
            if not primary and objs:
                primary = objs[0].get("Name", "未分类")
            return primary, tags
        except (json.JSONDecodeError, TypeError):
            pass

    # Simple text category (home_list format)
    primary = str(cat_val).strip() if cat_val else ""
    if not primary:
        # Map genre code if category is empty
        genre_code = str(genre_val or "")
        primary = {"0": "未分类", "4": "小说"}.get(genre_code, "未分类")
    return primary, tags

def word_count_str(wc):
    if wc >= 10000:
        return f"{wc/10000:.1f}万"
    return str(wc)

def clean_text(s):
    """Remove control chars that would break YAML or Markdown."""
    if not s:
        return ""
    # Replace null bytes and other control chars except newline/tab
    cleaned = "".join(c if c >= " " or c in "\n\t" else "" for c in s)
    return cleaned.strip()

# ── main ────────────────────────────────────────────────────────────────

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM novels WHERE platform='番茄' ORDER BY id").fetchall()
conn.close()

print(f"Exporting {len(rows)} novels to Obsidian vault at: {OUTPUT}")

# Track category → novels mapping for interlinking
category_map = {}
all_novels = []

for r in rows:
    novel = dict(r)
    all_novels.append(novel)

    cat, tags = extract_category_and_tags(novel["category"], novel["genre"])

    novel["_primary_cat"] = cat if cat else "未分类"
    novel["_sub_tags"] = tags

    # Track for index linking
    if novel["_primary_cat"] not in category_map:
        category_map[novel["_primary_cat"]] = []
    category_map[novel["_primary_cat"]].append(novel)

# ── Generate novel files ────────────────────────────────────────────────

for novel in all_novels:
    nid = novel["id"]
    name = clean_text(novel["novel_name"])
    author = clean_text(novel["author"])
    desc = clean_text(novel.get("description", "") or "")
    primary_cat = novel["_primary_cat"]
    sub_tags = novel["_sub_tags"]
    wc = novel["word_count"] or 0
    cs = novel["creation_status"]
    status_str = "完结" if cs == 0 else "连载" if cs == 1 else "未知"
    source_tag = {"home_list": "番茄首页推荐", "rank": "番茄排行榜"}.get(
        novel.get("source", ""), novel.get("source", ""))

    # Build tag list
    tag_list = ["番茄小说", source_tag, primary_cat] + sub_tags
    tag_list = list(dict.fromkeys(tag_list))  # dedup, preserve order

    # Fanqie URL
    novel_id = novel["novel_id"]
    fanqie_url = f"https://fanqienovel.com/page/{novel_id}"

    # Build frontmatter
    lines = ["---"]
    lines.append(f'title: "{name}"')
    lines.append(f"author: \"{author}\"" if author else "author: \"\"")
    lines.append(f"word_count: {wc}")
    lines.append(f"word_count_display: \"{word_count_str(wc)}\"")
    lines.append(f"status: \"{status_str}\"")
    lines.append(f'category: "{primary_cat}"')
    lines.append(f'tags: [{", ".join(tag_list)}]')
    lines.append(f"platform: 番茄小说")
    lines.append(f"book_id: {novel_id}")
    lines.append(f"url: \"{fanqie_url}\"")

    # Sub-categories (raw JSON tags)
    if sub_tags:
        lines.append(f'sub_tags: [{", ".join(sub_tags)}]')

    lines.append("---")
    lines.append("")

    # Body
    lines.append(f"# {name}")
    lines.append("")

    if author:
        lines.append(f"> **作者**：{author}")
    lines.append(f"> **字数**：{word_count_str(wc)}  ({wc})")
    lines.append(f"> **状态**：{status_str}")
    lines.append(f"> **分类**：{primary_cat}")
    if sub_tags:
        lines.append(f"> **标签**：{' · '.join(sub_tags)}")
    lines.append(f"> **链接**：[fanqienovel.com]({fanqie_url})")
    lines.append("")

    if desc:
        lines.append("## 简介")
        lines.append("")
        lines.append(desc)
        lines.append("")

    # Related novels in same category
    siblings = [n for n in category_map[primary_cat] if n["id"] != nid]
    if siblings:
        lines.append("## 同类型作品")
        lines.append("")
        for sib in siblings:
            sib_name = clean_text(sib["novel_name"])
            sib_wc = word_count_str(sib["word_count"] or 0)
            sib_cs = "完结" if sib.get("creation_status") == 0 else "连载" if sib.get("creation_status") == 1 else ""
            sib_info = f"（{sib_wc}字·{sib_cs}）" if sib_cs else f"（{sib_wc}字）"
            lines.append(f"- [[{sib_name}]]{sib_info}")
        lines.append("")

    content = "\n".join(lines)

    # Category folder
    cat_dir = os.path.join(OUTPUT, "novels", primary_cat)
    os.makedirs(cat_dir, exist_ok=True)

    # Sanitize filename
    safe_name = name.replace("/", "／").replace("\\", "＼").replace(":", "：").replace("*", "＊")
    fpath = os.path.join(cat_dir, f"{safe_name}.md")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ {primary_cat}/{safe_name}.md")

# ── Category index files ────────────────────────────────────────────────

for cat, novels_in_cat in sorted(category_map.items()):
    index_lines = [f"# {cat}", "", f"共 {len(novels_in_cat)} 部作品", ""]

    # Table
    index_lines.append("| 书名 | 作者 | 字数 | 状态 |")
    index_lines.append("|------|------|------|------|")
    for n in sorted(novels_in_cat, key=lambda x: x["word_count"] or 0, reverse=True):
        n_name = clean_text(n["novel_name"])
        n_author = clean_text(n["author"])
        n_wc = word_count_str(n["word_count"] or 0)
        n_cs = "完结" if n.get("creation_status") == 0 else "连载" if n.get("creation_status") == 1 else ""
        index_lines.append(f"| [[{n_name}]] | {n_author} | {n_wc} | {n_cs} |")
    index_lines.append("")

    cat_dir = os.path.join(OUTPUT, "novels", cat)
    os.makedirs(cat_dir, exist_ok=True)
    idx_path = os.path.join(cat_dir, "README.md")
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))
    print(f"  ✓ {cat}/README.md")

# ── Vault root index ────────────────────────────────────────────────────

root_lines = [
    "# 番茄小说知识库",
    "",
    f"> 从 fanqienovel.com 采集的 {len(all_novels)} 部小说数据",
    f"> 生成时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "",
    "## 按分类浏览",
    "",
]

for cat, novels_in_cat in sorted(category_map.items()):
    n = len(novels_in_cat)
    total_wc = sum(n["word_count"] or 0 for n in novels_in_cat)
    root_lines.append(f"- **[{cat}](novels/{cat}/README.md)** — {n} 部作品，共 {word_count_str(total_wc)} 字")
root_lines.append("")

root_lines.append("---")
root_lines.append("")
root_lines.append("## 全部作品")
root_lines.append("")
root_lines.append("| 书名 | 分类 | 作者 | 字数 | 状态 |")
root_lines.append("|------|------|------|------|------|")
for n in sorted(all_novels, key=lambda x: x["id"]):
    n_name = clean_text(n["novel_name"])
    n_author = clean_text(n["author"])
    n_cat = n["_primary_cat"]
    n_wc = word_count_str(n["word_count"] or 0)
    n_cs = "完结" if n.get("creation_status") == 0 else "连载" if n.get("creation_status") == 1 else ""
    root_lines.append(f"| [[{n_name}]] | {n_cat} | {n_author} | {n_wc} | {n_cs} |")
root_lines.append("")

idx_path = os.path.join(OUTPUT, "index.md")
with open(idx_path, "w", encoding="utf-8") as f:
    f.write("\n".join(root_lines))
print(f"  ✓ index.md")

print(f"\nDone! Vault at: {OUTPUT}")
