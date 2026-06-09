# P1 知识沉淀 MCP 工具验证记录

日期：2026-06-10

## 已新增工具

### 知识库

- `ai_novel_knowledge_list_documents`
- `ai_novel_knowledge_get_document`
- `ai_novel_knowledge_create_document`
- `ai_novel_knowledge_create_version`
- `ai_novel_knowledge_reindex_document`
- `ai_novel_knowledge_recall_test`

### 拆书分析

- `ai_novel_book_analysis_list`
- `ai_novel_book_analysis_get`
- `ai_novel_book_analysis_create`
- `ai_novel_book_analysis_publish`
- `ai_novel_book_analysis_export`

## 验证方式

1. 编译 `scripts/ai_novel_mcp.py`。
2. 导入脚本并检查 `TOOLS` 注册表。
3. 只调用离线只读列表工具：
   - `tool_knowledge_list_documents({ offline: true, limit: 5 })`
   - `tool_book_analysis_list({ offline: true, limit: 5 })`

未调用任何创建、发布、重建、召回测试或生成类工具。

## 验证结果

- Python 编译：通过。
- P1 工具注册：通过。
- 知识库列表只读调用：通过，返回 `source/items/count`。
- 拆书分析列表只读调用：通过，返回 `source/items/count`。

当前本地数据库中知识库文档和拆书分析数量可能为 0；这不是失败，说明后续还没有正式把对标作品/素材沉淀进知识库。

## 设计边界

- 列表/详情工具支持 offline SQLite 读取。
- 创建/版本/重索引/召回测试/拆书创建/发布/导出走后端 API，需要 backend 运行。
- 写入类工具只是注册能力，本次没有执行。
- 后续使用时，应由 Claude 作为用户代言人先确认要沉淀什么素材，再调用创建类工具。

## 下一步建议

1. 用 `ai_novel_knowledge_create_document` 沉淀经过用户确认的素材，而不是聊天临时灵感。
2. 用 `ai_novel_book_analysis_create` 对完整参考文本做拆书。
3. 用 `ai_novel_book_analysis_publish` 把拆书结果发布到目标小说知识资产。
4. 再补 P2 写法引擎工具：从文本/拆书生成 style profile，并绑定到 novel/chapter/task。
