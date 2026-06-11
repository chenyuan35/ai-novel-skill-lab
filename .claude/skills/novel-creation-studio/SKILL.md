---
name: novel-creation-studio
description: Use this when running AI Novel Writing Assistant v2 through the MCP bridge for long-form novel planning, chapter generation, review, style repair, and knowledge recall.
---

# Novel Creation Studio

Claude/Codex is the director and operator. AI Novel is the production engine.

## Start

1. Run `python scripts/lab_doctor.py`.
2. Run `python mcp-bridge/ai_novel_mcp.py healthcheck`.
3. Start writing sessions with `ai_novel_bootstrap_session`.

## Before Generation

- Read `ai_novel_production_status`.
- Read `ai_novel_director_status`.
- Read `ai_novel_read_ledgers`.
- Read `ai_novel_style_context`.
- Update the chapter brief, task sheet, scene cards, must-avoid rules, and target word count.

## Generation Loop

1. Call `ai_novel_generate_chapter`.
2. Read with `ai_novel_read_chapter_full` or `ai_novel_get_chapter_sample`.
3. Ask the user to approve, reject, or redirect.
4. If rejected, name the concrete issue before retrying.
5. If approved, update chapter status and capture knowledge.

## Boundaries

- Do not hand-write production chapters.
- Do not commit secrets, databases, logs, private drafts, or upstream full source.
- Treat this GitHub repo as public unless the user has changed visibility.
