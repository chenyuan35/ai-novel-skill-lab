# AI Novel Skill Lab

这是个人本地私有迭代仓库，用来基于第三方上游软件 AI Novel Writing Assistant v2 做自用 MCP 化改造。

## 30 秒入口

```bash
python scripts/lab_doctor.py
python mcp-bridge/ai_novel_mcp.py --help
python mcp-bridge/ai_novel_mcp.py healthcheck
```

日常写作会话建议从：

```bash
python mcp-bridge/ai_novel_mcp.py bootstrap
```

开始。它会返回当前后端、模型配置、小说、章节和下一步动作。

## 定位

- Claude 负责导演、用户代言、创意碰撞和工作流调度。
- AI Novel Writing Assistant v2 负责生产级小说内容、规划链、审校、修复、摘要、事实抽取和知识回灌。
- 本仓库只保存可迭代的技能、流程、桥接代码、配置模板和设计记录。
- 不保存 API 密钥、SQLite 数据库、日志、私密生成稿或大体积运行时产物。

## 目录

- `docs/`：原仓库研究、授权合规、产品原则。
- `workflow/`：导演链路、章节生产链、质量闸门、回灌规则。
- `mcp-bridge/`：MCP 桥接层改造记录和源码草案。
- `skills/`：Claude Code 小说技能相关文件的可审查副本。
- `agents/`：导演、审稿、风格、互动主持等 agent 规则副本。
- `ops/`：本地运行、模型路由、备份、发布导出操作手册。
- `exports/`：只放脱敏样例或模板，不放正式正文。

## 现在可用的顺手工具

- `scripts/lab_doctor.py`：快速看仓库状态、MCP 工具数量、素材库规模、push 安全风险。
- `mcp-bridge/ai_novel_mcp.py --help`：查看桥接脚本 CLI。
- `mcp-bridge/ai_novel_mcp.py list-tools`：列出当前暴露给 MCP host 的工具。
- `skills/novel-creation-studio/SKILL.md`：写作会话规则，约束 Claude/Codex 不手写生产正文，优先调用 AI Novel。

## 常用命令

```bash
# 本仓库体检，push 前建议加 --strict
python scripts/lab_doctor.py --strict

# AI Novel 后端预检
python mcp-bridge/ai_novel_mcp.py healthcheck

# 自动启动/读取当前写作会话
python mcp-bridge/ai_novel_mcp.py bootstrap

# 查看模型配置，输出会脱敏
python mcp-bridge/ai_novel_mcp.py model-config

# 查看第 N 章样稿
python mcp-bridge/ai_novel_mcp.py sample 1
```

## 日常写作顺序

1. 先用 `lab_doctor` 确认仓库没有明显风险。
2. 用 `healthcheck` 查后端、数据库、技能目录和默认小说。
3. 用 `bootstrap` 进入写作状态，不清楚时先读 production/director/ledger 状态。
4. 生成前更新 chapter brief / task sheet / scene cards / must avoid。
5. 正文生成、修复和风格改写走 AI Novel MCP 工具，不让 Claude/Codex 直接替写生产稿。
6. 通过审稿后，把事实、伏笔、风格和反馈回灌知识库。

## 远程仓库原则

当前 GitHub 远端是公开仓库，所有 push 都按“可能被公开读取”的标准检查。默认不提交密钥、SQLite、日志、正式正文、私密素材、大体积运行时和上游完整源码。
