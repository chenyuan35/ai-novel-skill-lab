# P0 只读 MCP 工具验证记录

日期：2026-06-10

## 已新增工具

- `ai_novel_production_status`
- `ai_novel_director_status`
- `ai_novel_read_ledgers`

## 验证方式

使用 Python 直接导入 `scripts/ai_novel_mcp.py`，调用三个 handler。验证过程只读 SQLite，不调用生成接口，不更新数据库。

## 验证结果

### 1. `ai_novel_production_status`

结果：通过。

确认返回字段：

- `source`
- `novelId`
- `title`
- `targetChapterCount`
- `assetsReady`
- `pipelineReady`
- `currentStage`
- `assetStages`
- `chapterProgress`
- `memoryCounts`
- `facts`
- `latestGenerationJob`
- `latestWorkflowTask`
- `latestDirectorTask`
- `summary`

用途：判断项目是否具备整本生产条件，显示当前资产缺口、章节进度、记忆账本计数和后台任务状态。

### 2. `ai_novel_director_status`

结果：通过。

确认返回字段：

- `task`
- `runtime`
- `recentRuntimeEvents`
- `recentDirectorEvents`
- `recentSteps`
- `recentArtifacts`
- `requiresAttention`
- `blockingReason`
- `summary`

用途：恢复 GUI 中自动导演运行态/失败原因/最近事件的可见性。

### 3. `ai_novel_read_ledgers`

结果：通过。

确认返回字段：

- `novelFacts`
- `consistencyFacts`
- `payoffLedger`
- `characterResourceLedger`
- `timelineEvents`
- `timelineHooks`
- `activeTimelineConstraints`
- `chapterSummaries`
- `counts`

用途：读取长篇记忆层，确认事实、伏笔、角色资源、时间线和章节摘要是否沉淀。

## 重要发现

- 当前项目已有不少长篇记忆沉淀：章节摘要、一致性事实、伏笔账本、角色资源账本、时间线事件等。
- `NovelFactEntry` 当前可能为空，但旧链路使用了 `ConsistencyFact`；后续要决定是兼容两套事实来源，还是补迁移/桥接。
- 自动导演任务存在失败/阻塞历史，P0 工具能读出失败摘要，后续应做专门恢复/诊断工具。
- 终端直接打印时可能出现中文编码显示问题；以 UTF-8 文件或 MCP 返回给 Claude 时应正常。

## 安全结果

- 未提交测试输出 JSON，因为其中可能包含私密小说状态和账本片段。
- `.gitignore` 已增加 `mcp-bridge/*test-output*.json`、`*.local.json`、`*.private.json`。
