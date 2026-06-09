# 远程仓库策略

## 当前状态

- 本地仓库已创建：`C:\Users\59314\claudework\ai-novel-skill-lab`
- 远程仓库已存在：`https://github.com/chenyuan35/ai-novel-skill-lab`
- GitHub 返回可见性：`PRIVATE`
- 当前分支：`main`
- 当前原则：只允许作为个人自用 MCP 改造实验室，不公开宣传为自研项目，不推送密钥、数据库、日志、正式正文或上游完整源码。

## 默认建议

- 保持仓库名：`ai-novel-skill-lab`
- 保持可见性：private
- 用途：个人自用 MCP 改造实验室，不作为上游正式分发版，也不对外宣称为自研项目。
- 远程内容：只同步技能规则、桥接代码、操作手册、配置模板和脱敏样例。

## 与上游关系

- 上游：`ExplosiveCoderflome/AI-Novel-Writing-Assistant`
- 上游默认 AGPLv3，且 NOTICE 说明服务型商用/SaaS/托管给第三方使用需要商业授权。
- 当前仓库不是公开 fork，不保存上游完整源码；只保存个人改造文档、MCP 桥接代码和脱敏规则副本。
- 若未来要公开发布或对外服务，必须重新审查 LICENSE/NOTICE，并保留上游归属和源码开放义务。

## 每次 push 前必须检查

1. `git status --short`
2. 检查 `.gitignore`
3. 搜索密钥和 token
4. 确认没有 SQLite、日志、正式正文、私密素材、node_modules、runtime exe
5. 确认没有把上游完整源码复制进仓库

## 建议执行顺序

1. 继续完善本地工作流文档和桥接代码。
2. 把当前小说项目旧污染清理完。
3. 复制或抽取技能/agent/MCP 文件的脱敏可审查版本。
4. 本地 commit。
5. push 到已有 private remote。

## 授权与安全

- 已在对话中出现过的 SSH 密码、ModelScope token、Mistral key 都应视为暴露，不得写入仓库，建议轮换。
- 小说正文和世界观资产默认属于私密资产，不进入公开仓库。
- 即使仓库是 private，也按“可能泄露”标准管理秘密。
