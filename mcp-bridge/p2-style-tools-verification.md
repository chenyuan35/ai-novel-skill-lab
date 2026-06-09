# P2 写法引擎 MCP 工具验证记录

日期：2026-06-10

## 已新增工具

### 写法资产

- `ai_novel_style_list_profiles`
- `ai_novel_style_get_profile`
- `ai_novel_style_create_from_text`
- `ai_novel_style_create_from_brief`
- `ai_novel_style_create_from_book_analysis`

### 写法绑定

- `ai_novel_style_list_bindings`
- `ai_novel_style_bind`

### 反 AI / 检测 / 修复

- `ai_novel_anti_ai_rules`
- `ai_novel_style_detect`
- `ai_novel_style_rewrite`

## 验证方式

1. 编译 `scripts/ai_novel_mcp.py`。
2. 导入脚本并检查 `TOOLS` 注册表。
3. 只调用离线只读列表工具：
   - `tool_style_list_profiles({ offline: true, limit: 5 })`
   - `tool_style_list_bindings({ offline: true, limit: 5 })`
   - `tool_anti_ai_rules({ offline: true, limit: 5 })`

未调用创建写法、绑定写法、检测正文、改写正文等写入/生成类工具。

## 验证结果

- Python 编译：通过。
- P2 工具注册：通过。
- 写法资产列表只读调用：通过。
- 写法绑定列表只读调用：通过。
- 反 AI 规则列表只读调用：通过。

## 设计边界

- 列表/详情工具支持 offline SQLite 读取。
- 创建写法、绑定、检测、改写走后端 API。
- 写法改写必须通过 AI Novel Style Engine，不允许 Claude 直接手写替代生产正文。
- 后续使用时，应先由用户确认样文、拆书分析或风格 brief，再创建 style profile。

## 下一步建议

1. 把用户认可的样文章节或对标文本沉淀为 style profile。
2. 将 style profile 绑定到当前小说或具体章节任务。
3. 章节生成后用 `ai_novel_style_detect` 检查 AI 味和风格偏移。
4. 对发现的问题用 `ai_novel_style_rewrite` 或后端 repair 链路修复，而不是 Claude 直接改正文。
