# 远程仓库策略

## 当前状态

- 本地仓库已创建：`C:\Users\59314\claudework\ai-novel-skill-lab`
- GitHub CLI 已登录，可创建远程仓库。
- 远程仓库尚未创建，因为这属于对外可见操作，必须先确认。

## 默认建议

- 仓库名：`ai-novel-skill-lab`
- 可见性：私有仓库
- 用途：个人自用 MCP 改造实验室，不作为上游正式分发版，也不对外宣称为自研项目。
- 远程内容：只同步技能规则、桥接代码、操作手册、配置模板和脱敏样例。

## 创建远程前必须确认

1. 仓库名
   - 默认：`ai-novel-skill-lab`
   - 可改成：`novel-legion-lab`、`ai-novel-mcp-lab`、`my-novel-skill`

2. 可见性
   - 默认：private
   - 不建议现在 public，因为存在上游 AGPLv3、个人小说资产和配置泄露风险。

3. 与上游关系
   - 私人实验室：适合当前阶段；不对外宣称为自研项目。
   - fork：适合未来要同步上游代码和提交 PR。
   - 公开派生版：需要完整许可证、NOTICE、源码开放和商业使用边界审查。

4. 首次 push 前检查
   - `git status --short`
   - 检查 `.gitignore`
   - 搜索密钥和 token
   - 确认没有 SQLite、日志、正式正文、私密素材、node_modules、runtime exe。

## 建议执行顺序

1. 继续完善本地工作流文档和桥接代码。
2. 把当前小说项目旧污染清理完。
3. 复制或抽取技能/agent/MCP 文件的脱敏可审查版本。
4. 做首次本地 commit。
5. 用户确认远程仓库名和 private/public。
6. 创建 GitHub remote 并 push。

## 授权与安全

- 上游默认 AGPLv3；如果公开发布或提供服务，需要保留许可证和 NOTICE，并评估是否需要商业授权。
- 已在对话中出现过的 SSH 密码、ModelScope token、Mistral key 都应视为暴露，不得写入仓库，建议轮换。
- 小说正文和世界观资产默认属于私密资产，不进入公开仓库。
