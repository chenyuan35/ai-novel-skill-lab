# AI Novel Skill Lab Session Rules

Use this repository as a personal AI Novel Writing Assistant v2 MCP workspace.

## Start

1. Run `python scripts/lab_doctor.py`.
2. Run `python mcp-bridge/ai_novel_mcp.py healthcheck`.
3. For writing sessions, call `ai_novel_bootstrap_session` before planning or generating.

## Rules

- Claude/Codex acts as director, reviewer, and workflow operator.
- Production prose generation, repair, style detection, and style rewrite should go through AI Novel MCP tools.
- Do not commit secrets, SQLite databases, logs, private drafts, private materials, or upstream full source.
- Current remote is public; treat every committed file as publicly readable.

## Debug Order

1. `ai_novel_healthcheck`
2. `ai_novel_status`
3. `ai_novel_model_config`
4. `ai_novel_test_model`
5. `ai_novel_production_status`
6. `ai_novel_director_status`
7. Local logs and database summaries only when needed.
