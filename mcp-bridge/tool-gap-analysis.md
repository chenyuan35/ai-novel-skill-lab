# MCP 工具缺口与执行清单

> 基于 2026-06-10 上游源码审计。目标是把 AI Novel Writing Assistant v2 从 GUI 使用方式改造成私人自用 MCP 写作军团，而不是重写或冒充上游项目。

## P0：立刻补齐的可见性工具

这些工具优先级最高，因为不改变正文，只增强 Claude 对后端状态的判断能力。

### 1. `ai_novel_production_status`

对应上游：

- `GET /api/agent...` 可间接读 production tool；更直接可参考 `NovelProductionStatusService`。
- 源码：`server/src/services/novel/NovelProductionStatusService.ts`

能力：

- 返回资产阶段：世界、故事宏观、Book Contract、角色、小说圣经、卷规划、结构化大纲、章节任务单、正文、审校修复、状态提交、后台任务。
- 返回 `assetsReady`、`pipelineReady`、`currentStage`、`failureSummary`、`recoveryHint`。

用途：

- 用户问“能不能正常运行”“现在到哪了”时，不靠猜。
- 生成前判断缺什么。
- 失败时给恢复建议。

### 2. `ai_novel_director_status`

对应上游：

- `server/src/agents/tools/directorRuntimeTools.ts`
- `NovelDirectorService.getRuntimeProjection`

能力：

- 读取自动导演任务状态。
- 当前节点、当前阶段、是否需要用户动作、阻塞原因、推荐下一步、风险徽章、最近事件。

用途：

- 恢复 GUI 侧边栏/任务中心的“可见运行态”。

### 3. `ai_novel_read_ledgers`

对应上游 schema：

- `NovelFactEntry`
- `PayoffLedgerItem`
- `CharacterResourceLedgerItem`
- `StoryTimelineEvent`
- `TimelineConstraint`
- `TimelineCheckReport`

能力：

- 按小说读取事实、伏笔、角色资源、时间线约束摘要。
- 按章节读取前置事实和待兑现钩子。

用途：

- 修复“长篇写散、硬设定跨章漂移”。
- 让 Claude 能检查 AI Novel 有没有真的回灌。

## P1：知识沉淀和拆书工具

### 4. `ai_novel_knowledge_create_document`

对应上游：`POST /api/knowledge/documents`

能力：

- 把对标作品分析、素材、世界观规则、用户偏好写入知识库。
- 支持 title、fileName、content。

安全要求：

- 不自动上传私密正文到远程。
- 本地 DB 保存即可。

### 5. `ai_novel_knowledge_list_documents`

当前 Agent 工具有只读版本，但 MCP 桥接未暴露完整 REST。

能力：

- 列文档、状态、版本数、索引状态、最近错误。

### 6. `ai_novel_knowledge_recall_test`

对应上游：`POST /api/knowledge/documents/:id/recall-test`

能力：

- 用查询语句测试某文档能不能被召回。

用途：

- 验证“学习能力”不是嘴上说说。

### 7. `ai_novel_book_analysis_create`

对应上游：`POST /api/book-analysis`

能力：

- 对知识库里的参考作品做拆书。
- section 包括 overview、plot_structure、timeline、character_system、worldbuilding、themes、style_technique、market_highlights。

### 8. `ai_novel_book_analysis_publish_to_knowledge`

对应上游：`POST /api/book-analysis/:id/publish`

能力：

- 把拆书结果发布到某本小说知识中。

用途：

- 用户要求“参考成功作品，不要自己瞎造”时，形成长期资产。

## P2：写法引擎工具

### 9. `ai_novel_style_list_profiles`

比当前 `ai_novel_style_context` 更完整：列 profile、来源、规则、anti-AI 绑定。

### 10. `ai_novel_style_create_from_text`

对应上游 `StyleProfileService.createFromText` 或 route。

能力：

- 从用户给的样文/对标片段提取写法资产。

### 11. `ai_novel_style_create_from_book_analysis`

对应上游：`POST /api/style-engine/style-profiles/from-book-analysis`

能力：

- 把拆书分析转成可绑定的写法资产。

### 12. `ai_novel_style_bind`

对应上游 StyleBinding：targetType = novel/chapter/task。

能力：

- 把写法资产绑定到小说、章节或具体任务。

### 13. `ai_novel_style_detect` / `ai_novel_style_rewrite`

对应上游：style detection / rewrite route。

能力：

- 检测 AI 味、规则违背。
- 由 AI Novel 的 repair/rewrite 链路修，不让 Claude 手写替代。

## P3：整本生产和恢复工具

### 14. `ai_novel_start_full_pipeline`

对应上游：`start_full_novel_pipeline`

必须带：

- `dryRun` 默认 true 或先提供 preview 工具。
- startOrder / endOrder / maxRetries / targetChapterCount。

### 15. `ai_novel_pipeline_recover`

对应上游：

- `NovelPipelineRuntimeService.resumePendingPipelineJobs`
- `recoverStalePipelineJobs`

能力：

- 服务重启/心跳超时后恢复 pipeline。

### 16. `ai_novel_chapter_runtime_report`

能力：

- 读取某章的 runtime package / audit / repair / quality debt attribution / artifact sync 状态。

用途：

- 用户问“为什么这章不好/为什么失败”时能精准定位。

## P4：安全和版本管理工具

### 17. `ai_novel_backup_db`

能力：

- 清洗旧污染前自动备份 SQLite。
- 返回备份路径。

### 18. `ai_novel_secret_scan_project`

能力：

- 私有仓库 push 前扫描 token/key/db/log/draft。

### 19. `ai_novel_export_markdown_bundle`

能力：

- 只导出用户批准的章节/样稿。
- 默认不进 Git。

## 当前执行顺序

1. 先补 P0 只读状态工具。
2. 再补 P1 知识/拆书沉淀工具。
3. 再补 P2 写法引擎工具。
4. 最后再开放 P3 整本自动生产，且必须有 dry-run 和用户审批。

## 硬边界

- 不自动公开远程。
- 不提交上游完整源码。
- 不提交 SQLite、密钥、日志、正式正文。
- 不把 Claude 变成正文写手。
