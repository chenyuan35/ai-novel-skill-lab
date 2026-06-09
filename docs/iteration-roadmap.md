# 迭代路线

## 第一阶段：安全建仓

- 建立本地 Git 仓库。
- 加入 `.gitignore`，排除密钥、数据库、日志、生成稿和大体积运行时。
- 记录上游精华和 MCP 写作军团原则。

## 第二阶段：本地资产梳理

- 对比当前技能、agents、MCP bridge 与上游核心能力。
- 标记缺失能力：知识库批量导入、去重、RAG 回灌、质量恢复、任务中心可见性。
- 清理当前小说项目中的旧路线污染。

## 第三阶段：桥接层产品化

- 把 AI Novel backend 的 healthcheck、model config、route test、chapter brief、generation、sample export 串成稳定流程。
- 给失败路径建立诊断顺序：backend → provider → route → structured output → logs → DB 状态。
- 增加可复用的导出和备份操作。

## 第四阶段：学习能力增强

- 把对标作品、优质片段、风格规则、读者反馈和失败修复沉淀成可检索材料。
- 保持每本小说独立的世界、角色、事实、伏笔和时间线。
- 让新项目能复用经过验证的类型套路和写法资产。

## 第五阶段：远程同步

- 用户确认仓库名和可见性后再创建远程。
- 默认建议私有仓库。
- 首次 push 前运行秘密扫描和 Git 状态检查。
- 若未来公开发布，先做 AGPLv3/NOTICE/商业授权审查。