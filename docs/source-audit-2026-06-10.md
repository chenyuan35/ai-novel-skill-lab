# 上游源码审计记录（2026-06-10）

> 上游项目：`ExplosiveCoderflome/AI-Novel-Writing-Assistant`  
> 本地只读研究目录：`C:\Users\59314\claudework\ai-novel-upstream-source`  
> 目标：仅为个人自用 MCP 化改造理解上游设计，不把上游软件宣称为自研项目。

## 1. 授权与归属

已阅读：

- `LICENSE`
- `NOTICE`
- `package.json`
- `server/package.json`

结论：

- 上游默认许可证是 `AGPL-3.0-only`。
- `NOTICE` 明确说明：service-style commercial use 需要上游维护者单独商业授权。
- 我们的定位必须是私人自用、私有仓库、本地改造实验室。
- 不得公开搬运上游代码后伪装成原创项目。
- 不得把密钥、数据库、小说正文、运行时产物推到远程。

## 2. 上游工程形态

已确认上游是 pnpm monorepo：

- `client/`：React + Vite 前端 GUI。
- `desktop/`：Electron 桌面壳。
- `server/`：Express + Prisma + LangChain/LangGraph 后端。
- `shared/`：前后端共享类型与协议。

根脚本显示它支持：

- Web / Server 开发运行。
- Desktop 打包。
- Prisma migrate / seed / studio。
- server tests：planner、tools、runtime、routes、book-analysis。

## 3. 上游真正精华

源码审计确认：它不是一个“AI 写一章”的 GUI，而是 AI Native 长篇小说生产系统。

### 3.1 Agent Runtime / 写作军团骨架

关键源码：

- `server/src/agents/catalog.ts`
- `server/src/agents/toolRegistry.ts`
- `server/src/agents/runtime/AgentRuntime.ts`

上游领域 Agent：

- `Coordinator`：创作总控。
- `NovelAgent`：小说中枢。
- `BookAnalysisAgent`：拆书分析官。
- `KnowledgeAgent`：知识档案官。
- `WorldAgent`：世界观编务。
- `FormulaAgent`：公式编修师。
- `CharacterAgent`：角色档案官。

核心机制：

- Planner 先把用户目标解析成结构化计划。
- Tool Registry 统一管理工具。
- Runtime 执行工具计划。
- Approval 节点处理高风险动作。
- Trace Store 保存运行步骤，可追踪/恢复/重放。

这正对应用户说的“写作军团”，不能降级成单个写手。

### 3.2 自动导演链路

关键源码：

- `server/src/services/novel/director/NovelDirectorService.ts`
- `server/src/services/novel/director/automation/*`
- `server/src/services/novel/director/runtime/*`
- `server/src/services/novel/director/projections/*`
- `server/src/agents/tools/directorRuntimeTools.ts`

上游自动导演包含：

- candidate stage / 方向候选。
- confirm runtime / 方案确认。
- pipeline runtime / 开书后连续推进。
- continue runtime / 中断后继续。
- takeover / 接管已有项目。
- checkpoint / recovery / circuit breaker。
- workspace analysis / artifact inventory。
- policy mode：suggest only、run next step、run until gate、auto safe scope。

MCP 化必须保留“运行态可见 + 可恢复 + 可解释下一步”，否则就丢了 GUI 的核心价值。

### 3.3 整本生产主链

关键源码：

- `server/src/agents/tools/novelProductionTools.ts`
- `server/src/services/novel/NovelProductionStatusService.ts`
- `server/src/services/novel/NovelPipelineRuntimeService.ts`
- `server/src/services/novel/runtime/chapterRuntimePipeline.ts`
- `server/src/services/novel/chapterWritingGraph.ts`

上游生产链包含：

- 生成本书世界。
- 生成核心角色。
- 生成小说圣经。
- 生成发展走向。
- 生成结构化大纲。
- 同步章节目录。
- 启动整本写作任务。
- 查询整本生产状态。
- 服务重启/心跳超时后的任务恢复。

章节运行时不是简单生成，而是：

- 组装上下文。
- writer draft。
- 非空保护。
- 开头相似度/连续性防复制。
- 目标长度补写。
- 审校。
- 修复。
- 状态提交。
- artifact sync。
- 失败归因。

### 3.4 知识库 / RAG / 拆书沉淀

关键源码：

- `server/src/services/knowledge/KnowledgeService.ts`
- `server/src/routes/knowledge.ts`
- `server/src/services/bookAnalysis/BookAnalysisService.ts`
- `server/src/routes/bookAnalysis.ts`
- `server/src/services/rag/*`

知识库能力：

- 文档创建、版本化、激活版本。
- 文档归档/恢复。
- RAG 索引任务。
- recall test。
- 与小说/世界绑定。

拆书能力：

- 创建分析。
- 重建、重试、取消。
- 分 section 生成/编辑/冻结。
- 导出 markdown/json。
- publish to novel knowledge。

这就是“把优质小说、参考作品、素材沉淀成以后可复用能力”的核心。

### 3.5 写法引擎 / 反 AI 规则

关键源码：

- `server/src/services/styleEngine/StyleProfileService.ts`
- `server/src/services/styleEngine/StyleCompiler.ts`
- `server/src/routes/styleEngine.ts`

写法引擎能力：

- style profile。
- 从模板创建。
- 从 brief 创建。
- 从文本提取。
- 从拆书分析生成。
- 提取 feature pool。
- narrative / character / language / rhythm rules。
- anti-AI rules。
- style binding：novel / chapter / task。
- detection / rewrite / test-write。

当前 MCP 版只读取了一部分 style context，还没有真正把写法引擎 MCP 化。

### 3.6 长篇记忆账本

关键源码：

- `server/src/services/novel/fact/NovelFactService.ts`
- `server/src/services/novel/NovelChapterSummaryService.ts`
- `server/src/prisma/schema.sqlite.prisma`

已确认 schema 中有：

- `NovelFactEntry`：事实账本。
- `PayoffLedgerItem`：伏笔/兑现账本。
- `CharacterResourceLedgerItem`：角色资源账本。
- `StoryTimelineEvent`、`TimelineHook`、`TimelineConstraint`、`TimelineCheckReport`：时间线约束层。
- `ChapterSummary`：章节摘要。
- `ConsistencyFact`：一致性事实。
- `DirectorArtifact`、`DirectorRun`、`DirectorStepRun`：导演运行与产物。

`NovelFactService` 明确写着：

- 写入方：章节接收/定稿后自动写入。
- 读取方：生成上下文组装时填充 completedMilestones。
- 目的：防止 LLM 重复写已发生事件或改写硬事实。

## 4. 当前 MCP 桥接层状态

已读当前桥接：`C:\Users\59314\Documents\NovelAutoPublish\scripts\ai_novel_mcp.py`

目前已暴露：

- healthcheck / status / start backend / stop backend。
- model config / provider create-update / route set / model test。
- list novels / list chapters / get chapter / get sample。
- style context（只读 active style profiles + characters）。
- update chapter brief。
- interactive choice。
- generate chapter。
- overnight runner。

当前明显缺口：

- 未暴露上游 Agent Runtime 的 run/detail/replay 能力。
- 未暴露自动导演 runtime projection / next action / recovery / policy mode。
- 未暴露整本生产 status / full pipeline dry-run / start_full_novel_pipeline。
- 未暴露知识库文档创建、版本、绑定、索引、recall test。
- 未暴露拆书分析 create/rebuild/publish/export。
- 未暴露写法资产创建、提取、绑定、anti-AI rule、detection、rewrite。
- 未暴露事实账本、伏笔账本、时间线检查、角色资源账本。
- 章节生成后只有 sample export，对 summary/fact/payoff/timeline/artifact sync 的状态可见性不足。

## 5. MCP 化原则

1. 不复制 GUI 体验本身，保留 GUI 的生产系统精华。
2. Claude 是用户代理和总导演；AI Novel 后端是写作军团。
3. 生产正文必须走 AI Novel，不允许 Claude 手写替代。
4. MCP 工具要暴露“状态、诊断、恢复、回灌”，不只是“生成”。
5. 每个高风险写入工具必须有 dry-run 或明确审批边界。
6. 私有仓库只保存桥接代码、技能规则、文档和脱敏样例。
