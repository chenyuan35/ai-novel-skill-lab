---
name: novel-creation-studio
description: Use this when helping the user run AI Novel Writing Assistant v2 through the MCP bridge for long-form novel planning, chapter generation, review, style repair, knowledge recall, and safe local publishing.
---

# Novel Creation Studio

目标：让 Claude/Codex 做导演、诊断和用户代言，正文生产、修复、知识回灌优先走 AI Novel MCP 工具。

## 开场检查

1. 先运行本仓库体检：

   ```bash
   python scripts/lab_doctor.py
   ```

2. 再检查 AI Novel 后端：

   ```bash
   python mcp-bridge/ai_novel_mcp.py healthcheck
   ```

3. 写作会话开始时优先调用 `ai_novel_bootstrap_session`。需要只读判断时先调用：

   - `ai_novel_production_status`
   - `ai_novel_director_status`
   - `ai_novel_read_ledgers`
   - `ai_novel_style_context`

## 硬边界

- 不把 Claude/Codex 当生产正文写手。
- 生成、修复、风格改写优先使用 AI Novel 工具。
- 不提交密钥、数据库、日志、正式正文、私密素材或上游完整源码。
- 公开发布或商业使用前，重新审查上游 AGPLv3 和 NOTICE。

## 日常流程

1. 概念阶段：把用户一句灵感压成 2-4 条路线，让用户选。
2. 设定阶段：沉淀概念卡、人物、世界观、作者风格、导演笔记。
3. 生成前：更新 chapter brief、task sheet、scene cards、must avoid。
4. 生成时：调用 `ai_novel_generate_chapter`，不要手写替代。
5. 审稿时：用 `ai_novel_read_chapter_full` 或 `ai_novel_get_chapter_sample`，让用户选择通过/不通过/其他。
6. 不通过时：先记录问题，再走 `ai_novel_style_detect` / `ai_novel_style_rewrite` 或重新生成。
7. 通过后：更新章节状态，并把事实、伏笔、风格和反馈沉淀到知识库。

## 失败诊断顺序

1. `ai_novel_healthcheck`
2. `ai_novel_status`
3. `ai_novel_model_config`
4. `ai_novel_test_model`
5. `ai_novel_production_status`
6. `ai_novel_director_status`
7. 读取本地日志和 SQLite 状态，只做必要摘要，不外泄私密正文。

## Push 前

运行：

```bash
python scripts/lab_doctor.py --strict
git status --short
```

若 doctor 报告 `blocked tracked files` 或 `secret-like text candidates`，先清理再 push。
