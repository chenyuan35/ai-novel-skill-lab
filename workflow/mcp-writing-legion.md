# MCP 写作军团工作流

## 角色分工

- Claude：导演、用户代言人、创意碰撞对象、工作流调度者。
- AI Novel：写作军团，包括 planner、writer、review、repair、summary、fact extraction、style profile、character memory。
- 状态面板：展示阶段、概念卡、文件状态和生成结果入口。
- SQLite + Markdown：保存可复用创作资产。

## 标准链路

1. 方向讨论
   - 和用户讨论题材、爽点、情绪、市场对标和禁区。
   - 不调用正文生成。

2. 概念锁定
   - 写入 concept board、character rules、outline、materials、director notes。
   - 刷新状态面板。

3. 章节准备
   - 更新 AI Novel chapter brief、task sheet、scene cards、must avoid、target word count。
   - 确认旧污染已清理，角色与风格上下文正确。

4. 生成执行
   - 用户明确批准后调用 AI Novel 生成章节。
   - 根据 task type 使用 writer/planner/review/repair 等模型路由。

5. 产物审阅
   - 读取 chapter sample。
   - 判断是否符合钩子、人物、节奏、商业阅读和连续性。
   - 需要修复时更新 brief，再走 repair/re-generate，不由 Claude 直接手写替代。

6. 回灌沉淀
   - 更新摘要、事实、伏笔账本、角色变化、风格偏好和素材库。
   - 保持 Markdown 导出供未来排版、发布和迁移。

## 硬规则

- 不把 AI Novel 降级成“单个写手”。
- 不让用户反复提醒才使用插件。
- 不把聊天中的临时灵感当作已沉淀资产。
- 不在模型失败时静默改成 Claude 手写正文。
- 不把私密正文、密钥、数据库提交到 Git。