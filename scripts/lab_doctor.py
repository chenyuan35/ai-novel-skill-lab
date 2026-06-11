#!/usr/bin/env python3
"""Fast local health check for AI Novel Skill Lab.

The script is intentionally dependency-free so it can run before a writing
session or before pushing to GitHub.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DIRS = [
    "docs",
    "workflow",
    "mcp-bridge",
    "skills",
    "agents",
    "ops",
    "exports",
    "obsidian-vault",
]
BLOCKED_TRACKED_PATTERNS = [
    ".env",
    ".env.*",
    "*.db",
    "*.db-shm",
    "*.db-wal",
    "*.sqlite",
    "*.sqlite3",
    "*.log",
    "*.docx",
    "*.epub",
    "exports/drafts/*",
    "exports/private/*",
    ".ai_novel_bridge/logs/*",
    ".ai_novel_backup/*",
    "node_modules/*",
    "__pycache__/*",
]
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{20,}|"
    r"ghp_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_-]{30,}|"
    r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{24,})",
    re.IGNORECASE,
)
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}


def run_git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip()


def tracked_files() -> list[Path]:
    code, out = run_git("ls-files", "-z")
    if code != 0:
        return []
    return [ROOT / item for item in out.split("\0") if item]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def parse_mcp_tools() -> list[str]:
    bridge = ROOT / "mcp-bridge" / "ai_novel_mcp.py"
    try:
        tree = ast.parse(bridge.read_text(encoding="utf-8"))
    except OSError:
        return []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "TOOLS" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            return []
        return [
            key.value
            for key in node.value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        ]
    return []


def scan_secret_candidates(files: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in files:
        if not path.exists() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            if path.stat().st_size > 512_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if SECRET_RE.search(line):
                hits.append(f"{rel(path)}:{line_no}")
                break
    return hits


def count_vault() -> dict[str, object]:
    novels_dir = ROOT / "obsidian-vault" / "novels"
    categories: dict[str, int] = {}
    if novels_dir.exists():
        for item in sorted(novels_dir.iterdir()):
            if item.is_dir():
                categories[item.name] = len(list(item.glob("*.md")))
    return {
        "category_count": len(categories),
        "novel_file_count": sum(categories.values()),
        "categories": categories,
    }


def collect_report() -> dict[str, object]:
    code, branch = run_git("status", "--short", "--branch")
    status_lines = branch.splitlines() if code == 0 else [branch]
    tracked = tracked_files()
    tracked_rel = [rel(path) for path in tracked]
    blocked = [path for path in tracked_rel if matches_any(path, BLOCKED_TRACKED_PATTERNS)]
    tools = parse_mcp_tools()
    scripts_dir = ROOT / "scripts"
    scripts = sorted(path.name for path in scripts_dir.glob("*.py")) if scripts_dir.exists() else []
    debug_scripts = [
        name
        for name in scripts
        if name.startswith(("_", "debug_", "test_", "check_")) or "_debug" in name
    ]
    missing_dirs = [name for name in EXPECTED_DIRS if not (ROOT / name).is_dir()]
    secret_hits = scan_secret_candidates(tracked)
    return {
        "repo": str(ROOT),
        "git": {
            "status": status_lines,
            "clean": len(status_lines) <= 1,
        },
        "layout": {
            "missing_dirs": missing_dirs,
        },
        "mcp_bridge": {
            "tool_count": len(tools),
            "tools": tools,
        },
        "scripts": {
            "python_count": len(scripts),
            "debug_or_probe_count": len(debug_scripts),
            "debug_or_probe_examples": debug_scripts[:8],
        },
        "vault": count_vault(),
        "safety": {
            "blocked_tracked_files": blocked,
            "secret_candidate_locations": secret_hits,
            "ok": not blocked and not secret_hits,
        },
    }


def print_text(report: dict[str, object]) -> None:
    git = report["git"]
    layout = report["layout"]
    bridge = report["mcp_bridge"]
    scripts = report["scripts"]
    vault = report["vault"]
    safety = report["safety"]

    print("AI Novel Skill Lab Doctor")
    print(f"repo: {report['repo']}")
    print(f"git: {git['status'][0] if git['status'] else 'unknown'}")
    print(f"dirty: {'no' if git['clean'] else 'yes'}")
    print(f"layout missing: {', '.join(layout['missing_dirs']) or 'none'}")
    print(f"mcp tools: {bridge['tool_count']}")
    print(
        "scripts: "
        f"{scripts['python_count']} python files "
        f"({scripts['debug_or_probe_count']} debug/check/probe style)"
    )
    print(
        "vault: "
        f"{vault['category_count']} categories, "
        f"{vault['novel_file_count']} markdown files"
    )
    print(f"safety: {'ok' if safety['ok'] else 'needs attention'}")
    if safety["blocked_tracked_files"]:
        print("blocked tracked files:")
        for item in safety["blocked_tracked_files"]:
            print(f"  - {item}")
    if safety["secret_candidate_locations"]:
        print("secret-like text candidates:")
        for item in safety["secret_candidate_locations"]:
            print(f"  - {item}")
    print("")
    print("next:")
    print("  python mcp-bridge/ai_novel_mcp.py --help")
    print("  python mcp-bridge/ai_novel_mcp.py healthcheck")
    print("  python mcp-bridge/ai_novel_mcp.py bootstrap")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check local AI Novel Skill Lab usability and push safety.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when safety checks fail.")
    args = parser.parse_args(argv)

    report = collect_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)

    if args.strict and not report["safety"]["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
