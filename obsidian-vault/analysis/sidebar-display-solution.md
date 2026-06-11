# Claude Desktop 章节 Sidebar 显示方案

## 最终验证方案（2026-06-11）

通过 Claude Desktop 的 **preview HTTP server** 机制在右侧 preview 面板显示章节正文。

### 流程

1. 章节 markdown 写入 `.ai_novel_bridge/drafts/ch{N}.md`
2. Python 转成 HTML（UTF-8）写入 `ch{N}.html`
3. `preview_start` 启动 HTTP server（端口 8765）
4. `preview_eval` 执行 `window.location.href = '/ch{N}.html'`
5. 用户在右侧 preview 面板读正文

### launch.json 配置

路径：`C:\Users\59314\claudework\.claude\launch.json`

```json
{
  "version": "0.0.1",
  "configurations": [{
    "name": "novel-reader",
    "runtimeExecutable": "C:\\Users\\59314\\AppData\\Local\\Programs\\Python\\Launcher\\py.exe",
    "runtimeArgs": ["-3", "-m", "http.server", "8765", "--directory", "C:\\Users\\59314\\Documents\\NovelAutoPublish\\.ai_novel_bridge\\drafts"],
    "port": 8765
  }]
}
```

### 踩过的坑

| 方案 | 结果 | 原因 |
|------|------|------|
| MCP Apps `ui://` + `text/html;profile=mcp-app` | ❌ 不渲染 | Claude Desktop 已知 bug，从不调用 `resources/read` ([#165](https://github.com/anthropics/claude-ai-mcp/issues/165)) |
| Read 工具 | ❌ 内容在对话里 | 不触发右侧 sidebar 预览 |
| Write 工具 | ❌ 不触发预览 | 同上 |
| http.server 直接 serve .md | ❌ 中文乱码 | 编码问题 |
| `python` 命令 | ❌ 找不到 | Windows 没有 `python`，要用 `py.exe` |
| **preview server + HTML** | ✅ 正常显示 | UTF-8 HTML + preview 面板 |

### 关键细节

- Windows 必须用 `C:\Users\59314\AppData\Local\Programs\Python\Launcher\py.exe`
- .md 必须转 .html（带 `<meta charset="utf-8">`）才能正确显示中文
- `preview_start` 会自动启动 server，不需要手动运行
- 每次生成新章节后，更新 HTML 文件并 `preview_eval` 导航到新文件
