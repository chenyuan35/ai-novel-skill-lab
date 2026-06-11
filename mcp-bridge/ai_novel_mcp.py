import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
BRIDGE_DIR = WORKSPACE / ".ai_novel_bridge"
DRAFTS_DIR = BRIDGE_DIR / "drafts"
BRIDGE_LOG_DIR = BRIDGE_DIR / "logs"
STATE_PATH = BRIDGE_DIR / "state.json"
APP_DATA_DIR = Path(os.environ.get(
    "AI_NOVEL_APP_DATA_DIR",
    str(Path.home() / "AppData" / "Local" / "AI-Novel-Writing-Assistant-v2"),
))
DB_PATH = Path(os.environ.get("AI_NOVEL_DB_PATH", str(APP_DATA_DIR / "data" / "dev.db")))
GLOBAL_CLAUDE_SKILL_DIR = Path.home() / ".claude" / "skills" / "novel-creation-studio"
BACKEND_BUNDLE_DIR = WORKSPACE / "_ai_novel_backend"
BACKEND_RUNTIME_EXE = BACKEND_BUNDLE_DIR / "runtime" / "ai-novel-node-runtime.exe"
BACKEND_SERVER_ENTRY = BACKEND_BUNDLE_DIR / "node_modules" / "@ai-novel" / "server" / "dist" / "app.js"
AUDIT_SERVER_ENTRY = WORKSPACE / "_electron_audit" / "app" / "node_modules" / "@ai-novel" / "server" / "dist" / "app.js"
DESKTOP_EXE = Path(os.environ.get(
    "AI_NOVEL_DESKTOP_EXE",
    str(BACKEND_RUNTIME_EXE if BACKEND_RUNTIME_EXE.exists() else Path(r"C:\Program Files\AI Novel Writing Assistant v2\AI Novel Writing Assistant v2.exe")),
))
EXTRACTED_SERVER_ENTRY = Path(os.environ.get(
    "AI_NOVEL_SERVER_ENTRY",
    str(BACKEND_SERVER_ENTRY if BACKEND_SERVER_ENTRY.exists() else AUDIT_SERVER_ENTRY),
))
LOG_PATH = Path(os.environ.get(
    "AI_NOVEL_LOG_PATH",
    str(APP_DATA_DIR / "logs" / "desktop-main.log"),
))
DEFAULT_NOVEL_ID = os.environ.get("AI_NOVEL_DEFAULT_NOVEL_ID", "cmq2gpstg002kdodh8fan9sod")
HEADLESS_ONLY = os.environ.get("AI_NOVEL_HEADLESS_ONLY", "1").strip().lower() in ("1", "true", "yes")
NOVEL_PANEL_VIEW_URI = "ui://novel-panel/view.html"
CHAPTER_READER_URI = "ui://chapter-reader/view.html"
_CHAPTER_READER_CACHE = {"html": "", "title": "", "order": 0}
NOVEL_PANEL_WATCHED_FILES = {
    "NOVEL_CONCEPT_BOARD.md": "概念卡",
    "OUTLINE.md": "大纲",
    "CHARACTER_RULES.md": "人物",
    "CANON.md": "世界观",
    "AUTHOR_STYLE.md": "作者风格",
    "DIRECTOR_NOTES.md": "导演笔记",
    "MATERIALS.md": "素材",
}

NOVEL_PANEL_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>小说创作状态</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: #0e0e10; color: #e8e6e3; padding: 14px;
  font-size: 13px; line-height: 1.5;
}
.title { font-size: 13px; color: #ff8c42; font-weight: 600; }
.subtitle { color: #888; font-size: 11px; margin-bottom: 12px; }
.stage {
  background: linear-gradient(135deg, #ff8c42 0%, #e74c3c 100%);
  color: #fff; padding: 11px 13px; border-radius: 7px; margin-bottom: 14px;
}
.stage-name { font-size: 14px; font-weight: 600; margin-bottom: 3px; }
.stage-hint { font-size: 12px; opacity: 0.92; }
.section {
  font-size: 10px; color: #888; text-transform: uppercase;
  letter-spacing: 1px; margin: 12px 0 6px;
}
.concept-box {
  background: #1a1a1d; border: 1px solid #2a2a2e;
  border-radius: 6px; padding: 9px 11px;
}
.kv { display: flex; padding: 3px 0; border-bottom: 1px solid #222; font-size: 12px; }
.kv:last-child { border-bottom: none; }
.k { color: #888; min-width: 72px; }
.v { color: #e8e6e3; flex: 1; }
.hint { color: #666; font-style: italic; padding: 8px; font-size: 12px; }
.files { display: flex; flex-direction: column; gap: 5px; }
.file {
  background: #1a1a1d; border: 1px solid #2a2a2e; border-left: 3px solid #444;
  padding: 7px 10px; border-radius: 4px;
  display: flex; justify-content: space-between; align-items: center;
}
.file.filled { border-left-color: #4caf50; }
.file.empty { opacity: 0.55; }
.file-label { font-weight: 600; font-size: 12px; }
.file-name { color: #666; font-size: 10px; font-family: monospace; }
.file-meta { color: #888; font-size: 11px; }
.refresh {
  margin-top: 12px; padding-top: 10px; border-top: 1px solid #222;
  display: flex; justify-content: space-between; align-items: center;
}
.btn {
  background: #2a2a2e; color: #e8e6e3; border: 1px solid #3a3a3e;
  padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 11px;
}
.btn:hover { background: #3a3a3e; }
.ts { color: #555; font-size: 10px; }
</style>
</head>
<body>
<div class="title">\U0001f4d6 小说创作状态</div>
<div class="subtitle" id="proj">—</div>

<div class="stage">
  <div class="stage-name" id="stage-name">—</div>
  <div class="stage-hint" id="stage-hint">—</div>
</div>

<div class="section">概念卡</div>
<div id="concept"></div>

<div class="section">材料库</div>
<div class="files" id="files"></div>

<div class="refresh">
  <button class="btn" onclick="requestRefresh()">\U0001f504 刷新</button>
  <span class="ts" id="ts">—</span>
</div>

<script>
function renderConcept(c) {
  const box = document.getElementById('concept');
  const entries = Object.entries(c || {});
  if (entries.length === 0) {
    box.innerHTML = '<div class="hint">概念还没锁，先在对话里聊路线</div>';
    return;
  }
  box.innerHTML = '<div class="concept-box">' +
    entries.slice(0, 10).map(([k, v]) =>
      `<div class="kv"><span class="k">${escapeHtml(k)}</span><span class="v">${escapeHtml(v)}</span></div>`
    ).join('') + '</div>';
}

function renderFiles(files) {
  document.getElementById('files').innerHTML = (files || []).map(f =>
    `<div class="file ${f.status}">
       <div>
         <div class="file-label">${escapeHtml(f.label)}</div>
         <div class="file-name">${escapeHtml(f.name)}</div>
       </div>
       <div class="file-meta">${f.status === 'empty' ? '未创建' : f.lines + ' 行'}</div>
     </div>`
  ).join('');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

function applyState(state) {
  if (!state) return;
  document.getElementById('proj').textContent = state.project || '';
  document.getElementById('stage-name').textContent = state.stage_name || '';
  document.getElementById('stage-hint').textContent = state.stage_hint || '';
  renderConcept(state.concept);
  renderFiles(state.files);
  document.getElementById('ts').textContent = new Date().toLocaleTimeString();
}

function requestRefresh() {
  window.parent.postMessage({
    jsonrpc: "2.0", id: Date.now(),
    method: "tools/call",
    params: { name: "show_novel_panel", arguments: {} }
  }, '*');
}

window.addEventListener('message', (e) => {
  const msg = e.data;
  if (!msg) return;
  if (msg.method === 'ui/notifications/tool-result' || msg.method === 'ui/notifications/tool-input') {
    const result = msg.params?.result || msg.params;
    const content = result?.structuredContent || result;
    if (content && content.stage_name) applyState(content);
  }
});

window.parent.postMessage({
  jsonrpc: "2.0", id: 1,
  method: "ui/initialize",
  params: { protocolVersion: "2025-06-18", appCapabilities: {} }
}, '*');
window.parent.postMessage({
  jsonrpc: "2.0",
  method: "ui/notifications/initialized"
}, '*');
</script>
</body>
</html>
"""


def _read_md(name):
    path = WORKSPACE / name
    try:
        data = path.read_text(encoding="utf-8").strip()
        return data if data else None
    except (FileNotFoundError, OSError):
        return None
    except Exception as exc:
        return f"[读取错误: {exc}]"


def _parse_concept(text):
    if not text:
        return {}
    fields = {}
    for line in text.split("\n"):
        m = re.match(r"^[-*]?\s*([一-鿿\w]+)[：:]?\s*(.+)", line.strip())
        if m:
            k = m.group(1).strip()
            v = m.group(2).strip()
            if v and v not in ("", "—", "-"):
                fields[k] = v
    return fields


def _detect_stage():
    concept = _read_md("NOVEL_CONCEPT_BOARD.md")
    outline = _read_md("OUTLINE.md")
    characters = _read_md("CHARACTER_RULES.md")
    if not concept:
        return "脑洞阶段", "还没锁定概念，先聊路线"
    if not characters:
        return "概念已锁", "下一步：建人物"
    if not outline:
        return "人物已建", "下一步：搭大纲"
    return "大纲已搭", "可以进入章节生成"


def _novel_panel_snapshot():
    stage_name, stage_hint = _detect_stage()
    concept_text = _read_md("NOVEL_CONCEPT_BOARD.md")
    concept_fields = _parse_concept(concept_text)
    files = []
    for fname, label in NOVEL_PANEL_WATCHED_FILES.items():
        content = _read_md(fname)
        if content is None:
            files.append({"label": label, "name": fname, "status": "empty", "lines": 0})
        else:
            files.append({
                "label": label,
                "name": fname,
                "status": "filled",
                "lines": len(content.split("\n")),
            })
    return {
        "project": os.path.basename(WORKSPACE),
        "stage_name": stage_name,
        "stage_hint": stage_hint,
        "concept": concept_fields,
        "files": files,
    }


def tool_show_novel_panel(args):
    return _novel_panel_snapshot()


def _write(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _result(request_id, result):
    _write({"jsonrpc": "2.0", "id": request_id, "result": result})


def _error(request_id, code, message):
    _write({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def _text_result(text):
    return {"content": [{"type": "text", "text": text}]}


def _json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def _clip(text, limit=1800):
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


# === Red-line guard (管线侧代码守卫，不是 prompt 软判断) ===
# 确定性规则：生成后扫正文，命中即违规。这一层属于"管线编排层"，用代码 if-else，
# 不要塞进 prompt 让模型自觉。见记忆 feedback-ifelse-vs-prompt。
#
# 全局故事红线：整本书都不该出现的说明性/越界内容。
# 每条是 (规则名, 正则模式列表, 命中提示)。
GLOBAL_REDLINES = [
    (
        "重生说明性词汇",
        [r"重生", r"穿越", r"上一世", r"前世", r"这一世", r"重活", r"回到了?过去"],
        "禁止直接说明重生机制；用世界偏差细节暗示，不要点破。",
    ),
    (
        "前世婚姻/成年纠葛泄漏",
        [r"离婚", r"结婚", r"前妻", r"前夫", r"投行", r"同学聚会", r"中年", r"三十岁", r"三十年", r"工作多年"],
        "禁止把成年/前世的婚姻、职场、年龄写进初三场景，主角心理年龄只能用极少量错位暗示。",
    ),
    (
        "金手指/系统",
        [r"系统", r"面板", r"金手指", r"光脑", r"签到", r"开挂", r"作弊器"],
        "禁止系统/面板/金手指设定，主角只能靠笨办法自救。",
    ),
]


def _derive_chapter_redlines(must_avoid, task_sheet):
    """从本章 mustAvoid / taskSheet 的'严禁/禁止/不要X'里派生确定性禁词。

    只抽取能被关键词命中的硬约束，软性创作要求（笔触/节奏）不在此列。
    """
    rules = []
    text = " ".join(filter(None, [must_avoid or "", task_sheet or ""]))
    if not text:
        return rules
    # 角色出场限制：苏念仅限背影/发绳/翻书 → 正脸/对视/眼睛即违规
    if re.search(r"苏念.{0,12}(仅限|只(能|限)|背影)", text) or re.search(r"(禁止|严禁|不要).{0,20}苏念.{0,12}(正脸|对视|眼神)", text):
        rules.append((
            "苏念出场越界(正脸/对视)",
            [r"苏念.{0,8}(正脸|侧脸|对视|眼神|眼睛|瞳孔|看着我的眼)", r"对上.{0,4}(苏念|她).{0,4}(目光|眼)", r"她的眼(睛|神).{0,6}(看|望|盯)"],
            "苏念本章只能背影/发绳/翻书动作，不得写正脸、眼神、对视。",
        ))
    # 暗恋追回线作废
    if re.search(r"(暗恋|追回|追妻|甜宠).{0,6}(线)?.{0,6}(作废|禁止|不要|删)", text):
        rules.append((
            "暗恋追回线残留",
            [r"追(回|她)", r"挽回", r"她送(给)?我", r"我们(以前|曾经|分手)", r"复合"],
            "暗恋/追回/追妻线已作废，本章不得出现旧情追回暗示。",
        ))
    return rules


def _scan_redlines(content, must_avoid=None, task_sheet=None, old_soul_limit=2):
    """扫描正文红线，返回违规清单。纯确定性，无模型调用。"""
    if not content:
        return {"violations": [], "oldSoulHits": 0, "clean": True}
    violations = []
    rules = list(GLOBAL_REDLINES) + _derive_chapter_redlines(must_avoid, task_sheet)
    for name, patterns, hint in rules:
        hits = []
        for pat in patterns:
            for m in re.finditer(pat, content):
                s = max(0, m.start() - 12)
                e = min(len(content), m.end() + 12)
                hits.append(content[s:e].replace("\n", " "))
        if hits:
            violations.append({
                "rule": name,
                "count": len(hits),
                "samples": hits[:5],
                "hint": hint,
            })
    # 老灵魂细节密度：统计"前世/记忆里/这不对劲/和记忆不一样"类对照次数
    old_soul_pat = r"(记忆(里|中)|和记忆|不该|不对劲|本该|原本的记忆|印象(里|中))"
    old_soul_hits = len(re.findall(old_soul_pat, content))
    if old_soul_hits > old_soul_limit:
        violations.append({
            "rule": f"老灵魂对照过密(>{old_soul_limit})",
            "count": old_soul_hits,
            "samples": [m.group(0) for m in list(re.finditer(old_soul_pat, content))[:5]],
            "hint": f"世界偏差/老灵魂对照一章最多 {old_soul_limit} 处，当前 {old_soul_hits} 处，需大幅删减。",
        })
    return {
        "violations": violations,
        "oldSoulHits": old_soul_hits,
        "clean": len(violations) == 0,
    }


def _ensure_bridge_dirs():
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _read_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(state):
    _ensure_bridge_dirs()
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_pid_running(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return f'"{pid}"' in result.stdout or f",{pid}," in result.stdout


def _clear_stale_headless_state():
    state = _read_state()
    pid = state.get("headlessPid")
    if isinstance(pid, int) and not _is_pid_running(pid):
        for key in ("headlessPid", "headlessPort", "headlessBaseUrl"):
            state.pop(key, None)
        state["lastStalePid"] = pid
        state["lastStaleClearedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _write_state(state)
    return state


def _free_loopback_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _node_path():
    configured = os.environ.get("AI_NOVEL_NODE_PATH", "").strip()
    if configured:
        return configured
    return shutil.which("node") or shutil.which("node.exe")


def _server_node_command():
    if DESKTOP_EXE.exists():
        return [str(DESKTOP_EXE)], {"ELECTRON_RUN_AS_NODE": "1"}, "electron-as-node"
    node = _node_path()
    if node:
        return [node], {}, "system-node"
    return None, {}, "missing"


def _backend_base_url_from_state():
    state = _clear_stale_headless_state()
    port = state.get("headlessPort")
    if isinstance(port, int):
        return f"http://127.0.0.1:{port}"
    return None


def _db_connect(read_only=True):
    if not DB_PATH.exists():
        raise RuntimeError(f"找不到 AI Novel 数据库: {DB_PATH}")
    if read_only:
        uri = "file:" + urllib.parse.quote(str(DB_PATH).replace("\\", "/"), safe="/:") + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10)
    else:
        conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def _row_dict(row):
    return {key: row[key] for key in row.keys()}


def _db_list_novels(limit=12):
    with _db_connect(read_only=True) as conn:
        rows = conn.execute(
            """
            select id, title, description, status, projectStatus, defaultChapterLength,
                   estimatedChapterCount, updatedAt
            from Novel
            order by updatedAt desc
            limit ?
            """,
            (int(limit),),
        ).fetchall()
    return [_row_dict(row) for row in rows]


def _db_list_chapters(novel_id):
    with _db_connect(read_only=True) as conn:
        rows = conn.execute(
            """
            select id, "order", title, chapterStatus, generationState, targetWordCount,
                   length(coalesce(content, '')) as contentLength, expectation, updatedAt
            from Chapter
            where novelId = ?
            order by "order" asc
            """,
            (novel_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "order": row["order"],
            "title": row["title"],
            "status": row["chapterStatus"],
            "generationState": row["generationState"],
            "targetWordCount": row["targetWordCount"],
            "contentLength": row["contentLength"],
            "expectation": _clip(row["expectation"], 280),
            "updatedAt": row["updatedAt"],
        }
        for row in rows
    ]


def _db_find_chapter(novel_id, chapter_id=None, order=None):
    with _db_connect(read_only=True) as conn:
        if chapter_id:
            row = conn.execute(
                'select * from Chapter where novelId = ? and id = ? limit 1',
                (novel_id, chapter_id),
            ).fetchone()
        else:
            row = conn.execute(
                'select * from Chapter where novelId = ? and "order" = ? limit 1',
                (novel_id, int(order)),
            ).fetchone()
    if not row:
        raise RuntimeError("找不到指定章节。")
    return _row_dict(row)


def _db_recent_style_context(limit=5):
    with _db_connect(read_only=True) as conn:
        rows = conn.execute(
            """
            select id, name, category, description, analysisMarkdown, narrativeRulesJson,
                   characterRulesJson, languageRulesJson, rhythmRulesJson, status, updatedAt
            from StyleProfile
            where status = 'active'
            order by updatedAt desc
            limit ?
            """,
            (int(limit),),
        ).fetchall()
    return [_row_dict(row) for row in rows]


def _db_character_brief(novel_id, limit=12):
    with _db_connect(read_only=True) as conn:
        rows = conn.execute(
            """
            select id, name, role, personality, currentState, currentGoal,
                   relationToProtagonist, speechHabit, updatedAt
            from (
              select id, name, role, personality, currentState, currentGoal,
                     relationToProtagonist, voiceTexture as speechHabit, updatedAt
              from Character
              where novelId = ?
              order by updatedAt desc
              limit ?
            )
            """,
            (novel_id, int(limit)),
        ).fetchall()
    return [_row_dict(row) for row in rows]


def _json_or_none(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return text


def _db_table_exists(conn, table_name):
    row = conn.execute(
        "select name from sqlite_master where type = 'table' and name = ? limit 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _db_table_columns(conn, table_name):
    if not _db_table_exists(conn, table_name):
        return set()
    rows = conn.execute(f'pragma table_info("{table_name}")').fetchall()
    return {row["name"] for row in rows}


def _db_count(conn, table_name, where="", params=()):
    if not _db_table_exists(conn, table_name):
        return 0
    sql = f'select count(*) as c from "{table_name}"'
    if where:
        sql += f" where {where}"
    row = conn.execute(sql, params).fetchone()
    return int(row["c"] if row else 0)


def _pick(row, key, default=None):
    if not row:
        return default
    return row[key] if key in row.keys() else default


def _truthy_text(value):
    return bool(str(value or "").strip())


def _db_fetch_limited(conn, table_name, columns, where="", params=(), order_by=None, limit=20):
    if not _db_table_exists(conn, table_name):
        return []
    existing = _db_table_columns(conn, table_name)
    selected = [column for column in columns if column in existing]
    if not selected:
        return []
    quoted = ", ".join(f'"{column}"' for column in selected)
    sql = f'select {quoted} from "{table_name}"'
    if where:
        sql += f" where {where}"
    if order_by:
        sql += f" order by {order_by}"
    sql += " limit ?"
    rows = conn.execute(sql, tuple(params) + (int(limit),)).fetchall()
    result = []
    for row in rows:
        item = _row_dict(row)
        for key, value in list(item.items()):
            if key.endswith("Json") or key in ("payload", "metadataJson", "policyJson", "lastWorkspaceAnalysisJson"):
                item[key] = _json_or_none(value)
            elif isinstance(value, str) and len(value) > 1200:
                item[key] = _clip(value, 1200)
        result.append(item)
    return result


def _structured_outline_chapter_count(text):
    text = str(text or "")
    if not text.strip():
        return 0
    patterns = [
        r'第\s*\d+\s*章',
        r'chapter\s*\d+',
        r'"order"\s*:',
        r'"chapterOrder"\s*:',
    ]
    counts = [len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns]
    return max(counts) if counts else 0


def _latest_generation_job(conn, novel_id):
    if not _db_table_exists(conn, "GenerationJob"):
        return None
    row = conn.execute(
        """
        select id, status, progress, completedCount, totalCount, retryCount, maxRetries,
               pendingManualRecovery, heartbeatAt, currentStage, currentItemKey,
               currentItemLabel, error, lastErrorType, startedAt, finishedAt, updatedAt
        from GenerationJob
        where novelId = ?
        order by updatedAt desc
        limit 1
        """,
        (novel_id,),
    ).fetchone()
    return _row_dict(row) if row else None


def _latest_workflow_task(conn, novel_id, lane=None):
    if not _db_table_exists(conn, "NovelWorkflowTask"):
        return None
    if lane:
        row = conn.execute(
            """
            select id, novelId, lane, title, status, progress, currentStage, currentItemKey,
                   currentItemLabel, checkpointType, checkpointSummary, pendingManualRecovery,
                   heartbeatAt, startedAt, finishedAt, lastError, updatedAt
            from NovelWorkflowTask
            where novelId = ? and lane = ?
            order by updatedAt desc
            limit 1
            """,
            (novel_id, lane),
        ).fetchone()
    else:
        row = conn.execute(
            """
            select id, novelId, lane, title, status, progress, currentStage, currentItemKey,
                   currentItemLabel, checkpointType, checkpointSummary, pendingManualRecovery,
                   heartbeatAt, startedAt, finishedAt, lastError, updatedAt
            from NovelWorkflowTask
            where novelId = ?
            order by updatedAt desc
            limit 1
            """,
            (novel_id,),
        ).fetchone()
    return _row_dict(row) if row else None


def _chapter_progress_summary(chapters):
    total = len(chapters)
    drafted = 0
    reviewed = 0
    approved = 0
    needs_repair = 0
    with_task_sheet = 0
    current_order = None
    for chapter in chapters:
        content_length = len(chapter.get("content") or "")
        generation_state = str(chapter.get("generationState") or "").lower()
        chapter_status = str(chapter.get("chapterStatus") or "").lower()
        if content_length > 0:
            drafted += 1
        if generation_state in ("reviewed", "approved"):
            reviewed += 1
        if generation_state == "approved":
            approved += 1
        if "repair" in generation_state or "repair" in chapter_status:
            needs_repair += 1
        if _truthy_text(chapter.get("taskSheet")) or _truthy_text(chapter.get("expectation")):
            with_task_sheet += 1
        if current_order is None and content_length == 0:
            current_order = chapter.get("order")
    return {
        "chapterCount": total,
        "draftedChapterCount": drafted,
        "reviewedChapterCount": reviewed,
        "approvedChapterCount": approved,
        "needsRepairChapters": needs_repair,
        "chaptersWithTaskSheets": with_task_sheet,
        "currentChapterOrder": current_order,
    }


def _save_sample_file(novel_id, chapter):
    _ensure_bridge_dirs()
    order = chapter.get("order") or "unknown"
    title = re.sub(r'[<>:"/\\|?*]+', "_", chapter.get("title") or "untitled")
    path = DRAFTS_DIR / f"{novel_id}_chapter_{order}_{title}.md"
    content = chapter.get("content") or ""
    body = (
        f"# 第{order}章 {chapter.get('title') or ''}\n\n"
        f"- chapterId: {chapter.get('id')}\n"
        f"- status: {chapter.get('chapterStatus')}\n"
        f"- updatedAt: {chapter.get('updatedAt')}\n\n"
        f"{content.strip()}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def _healthy(base_url, timeout=0.25):
    try:
        data = _request("GET", f"{base_url}/api/health", timeout=timeout)
        return isinstance(data, dict) and data.get("success") is not False
    except Exception:
        return False


def _candidate_ports_from_log():
    if not LOG_PATH.exists():
        return []
    text = LOG_PATH.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"127\.0\.0\.1:(\d+)|localhost:(\d+)", text)
    ports = []
    for left, right in matches:
        port = int(left or right)
        if port not in ports:
            ports.append(port)
    return list(reversed(ports))


def find_base_url():
    env_url = os.environ.get("AI_NOVEL_BASE_URL", "").strip().rstrip("/")
    if env_url and _healthy(env_url):
        return env_url

    state_url = _backend_base_url_from_state()
    if state_url and _healthy(state_url):
        return state_url

    if HEADLESS_ONLY:
        return None

    for port in _candidate_ports_from_log()[:8]:
        base = f"http://127.0.0.1:{port}"
        if _healthy(base):
            return base
    return None


def _request(method, url, body=None, timeout=15):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            return _parse_sse(raw.decode("utf-8", errors="replace"))
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def _api(method, path, body=None, timeout=20):
    base = find_base_url()
    if not base:
        raise RuntimeError("AI Novel Writing Assistant v2 后台后端没有运行。请先调用 ai_novel_start_backend 或运行 start headless。")
    return _request(method, base + path, body=body, timeout=timeout)


def _ensure_backend_for_write(args):
    if find_base_url():
        return
    if args.get("autoStart", True):
        started = _start_headless_backend(timeout_seconds=int(args.get("startupTimeoutSeconds", 45)))
        if started.get("running"):
            return
    raise RuntimeError("AI Novel 纯后台未运行，写入/生成需要先让 Claude 调用 ai_novel_bootstrap_session 或自动启动写入工具。")


def _wait_for_backend(base_url, timeout_seconds=45):
    deadline = time.time() + float(timeout_seconds)
    while time.time() < deadline:
        if _healthy(base_url, timeout=1):
            return True
        time.sleep(0.5)
    return False


def _start_headless_backend(timeout_seconds=45, port=None):
    existing = find_base_url()
    if existing:
        return {"started": False, "running": True, "baseUrl": existing, "message": "本地后端已经在运行。"}

    node_command, node_extra_env, runtime_kind = _server_node_command()
    if not node_command:
        raise RuntimeError("找不到可用的 Node/Electron runtime，无法启动 AI Novel 后端。")
    if not EXTRACTED_SERVER_ENTRY.exists():
        raise RuntimeError(f"找不到提取出的 AI Novel 后端入口: {EXTRACTED_SERVER_ENTRY}")

    selected_port = int(port or os.environ.get("AI_NOVEL_HEADLESS_PORT") or _free_loopback_port())
    base_url = f"http://127.0.0.1:{selected_port}"
    _ensure_bridge_dirs()
    log_path = BRIDGE_LOG_DIR / f"headless-server-{selected_port}.log"
    log_file = log_path.open("a", encoding="utf-8", buffering=1)
    env = dict(os.environ)
    env.update({
        **node_extra_env,
        "NODE_ENV": "production",
        "AI_NOVEL_RUNTIME": "desktop",
        "AI_NOVEL_APP_DATA_DIR": str(APP_DATA_DIR),
        "AI_NOVEL_DATABASE_MODE": "sqlite",
        "DATABASE_URL": "file:./dev.db",
        "PORT": str(selected_port),
        "HOST": "127.0.0.1",
        "ALLOW_LAN": "false",
        "RAG_ENABLED": env.get("RAG_ENABLED", "false"),
        "DIRECTOR_WORKER_EXECUTION_SLOTS": env.get("DIRECTOR_WORKER_EXECUTION_SLOTS", "1"),
        "DIRECTOR_WORKER_POLL_MS": env.get("DIRECTOR_WORKER_POLL_MS", "10000"),
        "NOVEL_SIDE_EFFECT_WORKER_POLL_MS": env.get("NOVEL_SIDE_EFFECT_WORKER_POLL_MS", "10000"),
        "BOOK_ANALYSIS_MAX_CONCURRENT_TASKS": env.get("BOOK_ANALYSIS_MAX_CONCURRENT_TASKS", "1"),
        "BOOK_ANALYSIS_NOTES_CONCURRENCY": env.get("BOOK_ANALYSIS_NOTES_CONCURRENCY", "1"),
        "BOOK_ANALYSIS_SECTION_CONCURRENCY": env.get("BOOK_ANALYSIS_SECTION_CONCURRENCY", "1"),
    })
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    process = subprocess.Popen(
        [*node_command, str(EXTRACTED_SERVER_ENTRY)],
        cwd=str(EXTRACTED_SERVER_ENTRY.parents[1]),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _write_state({
        **_read_state(),
        "headlessPid": process.pid,
        "headlessPort": selected_port,
        "headlessBaseUrl": base_url,
        "headlessLogPath": str(log_path),
        "runtimeKind": runtime_kind,
        "startedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    if not _wait_for_backend(base_url, timeout_seconds=timeout_seconds):
        return {
            "started": True,
            "running": False,
            "pid": process.pid,
            "baseUrl": base_url,
            "logPath": str(log_path),
            "runtimeKind": runtime_kind,
            "message": "已尝试启动后端，但健康检查超时。可以稍后再调用 ai_novel_status 查看。",
        }
    return {
        "started": True,
        "running": True,
        "pid": process.pid,
        "baseUrl": base_url,
        "logPath": str(log_path),
        "runtimeKind": runtime_kind,
        "message": "AI Novel 后端已用无 UI 模式启动。",
    }


def _start_desktop_app():
    if HEADLESS_ONLY:
        raise RuntimeError("当前启用了 AI_NOVEL_HEADLESS_ONLY，不允许启动桌面 GUI。")
    if find_base_url():
        return {"started": False, "running": True, "message": "本地后端已经在运行。"}
    if not DESKTOP_EXE.exists():
        raise RuntimeError(f"找不到 AI Novel 桌面程序: {DESKTOP_EXE}")
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(
        [str(DESKTOP_EXE)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _write_state({**_read_state(), "desktopPid": process.pid, "desktopStartedAt": time.strftime("%Y-%m-%d %H:%M:%S")})
    return {"started": True, "pid": process.pid, "message": "已启动桌面端；等本地服务健康后 MCP 就能调用。"}


def _stop_headless_backend():
    state = _read_state()
    pid = state.get("headlessPid")
    if not isinstance(pid, int):
        return {"stopped": False, "message": "没有记录中的无 UI 后端进程。"}
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
    for key in ("headlessPid", "headlessPort", "headlessBaseUrl"):
        state.pop(key, None)
    state["stoppedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write_state(state)
    return {"stopped": True, "pid": pid}


def _parse_sse(text):
    events = []
    current = []
    for line in text.splitlines():
        if not line.strip():
            if current:
                events.append("\n".join(current))
                current = []
            continue
        if line.startswith("data:"):
            current.append(line[5:].strip())
    if current:
        events.append("\n".join(current))

    parsed = []
    final_text = []
    for event in events:
        if not event or event == "[DONE]":
            continue
        try:
            item = json.loads(event)
            parsed.append(item)
            for key in ("text", "content", "delta", "message"):
                value = item.get(key) if isinstance(item, dict) else None
                if isinstance(value, str):
                    final_text.append(value)
        except Exception:
            final_text.append(event)
    return {"events": parsed[-20:], "text": "".join(final_text).strip(), "rawEventCount": len(events)}


def _unwrap(response):
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def _redact_config(value):
    if isinstance(value, list):
        return [_redact_config(item) for item in value]
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key.lower() in ("key", "apikey", "api_key", "token", "secret"):
                redacted[key] = "***" if item else None
            else:
                redacted[key] = _redact_config(item)
        return redacted
    return value


def tool_status(args):
    if args.get("autoStart"):
        _start_headless_backend(timeout_seconds=int(args.get("timeoutSeconds", 45)))
    base = find_base_url()
    state = _clear_stale_headless_state()
    if not base:
        return {
            "running": False,
            "message": "AI Novel Writing Assistant v2 纯后台后端未运行。Claude 可调用 ai_novel_bootstrap_session 自动拉起。",
            "headlessOnly": HEADLESS_ONLY,
            "logPath": str(LOG_PATH),
            "dbPath": str(DB_PATH),
            "dbExists": DB_PATH.exists(),
            "headlessState": state,
            "recentPorts": _candidate_ports_from_log()[:8],
        }
    health = _request("GET", f"{base}/api/health", timeout=2)
    return {"running": True, "baseUrl": base, "health": health, "headlessOnly": HEADLESS_ONLY, "dbPath": str(DB_PATH), "headlessState": state}


def tool_start_backend(args):
    mode = (args.get("mode") or "headless").strip().lower()
    if mode == "desktop":
        return _start_desktop_app()
    if mode != "headless":
        raise RuntimeError("mode 只能是 headless 或 desktop。")
    return _start_headless_backend(
        timeout_seconds=int(args.get("timeoutSeconds", 45)),
        port=args.get("port"),
    )


def tool_stop_backend(args):
    return _stop_headless_backend()


def tool_model_config(args):
    _ensure_backend_for_write({"autoStart": args.get("autoStart", True)})
    providers = _unwrap(_api("GET", "/api/settings/api-keys", timeout=12))
    selection = _unwrap(_api("GET", "/api/settings/llm-selection", timeout=8))
    routes = _unwrap(_api("GET", "/api/llm/model-routes", timeout=12))
    structured_fallback = _unwrap(_api("GET", "/api/llm/structured-fallback", timeout=8))
    return _redact_config({
        "providers": providers,
        "currentSelection": selection,
        "modelRoutes": routes,
        "structuredFallback": structured_fallback,
    })


def tool_create_custom_provider(args):
    _ensure_backend_for_write({"autoStart": args.get("autoStart", True)})
    body = {
        "name": args.get("name"),
        "baseURL": args.get("baseURL"),
        "key": args.get("key", ""),
        "model": args.get("model", ""),
        "isActive": args.get("isActive", True),
        "reasoningEnabled": args.get("reasoningEnabled", True),
        "concurrencyLimit": int(args.get("concurrencyLimit", 1)),
        "requestIntervalMs": int(args.get("requestIntervalMs", 0)),
    }
    if args.get("imageModel") is not None:
        body["imageModel"] = args.get("imageModel")
    data = _unwrap(_api("POST", "/api/settings/custom-providers", body, timeout=int(args.get("timeoutSeconds", 45))))
    return _redact_config({"created": True, "provider": data})


def tool_update_provider_config(args):
    _ensure_backend_for_write({"autoStart": args.get("autoStart", True)})
    provider = args.get("provider", "").strip()
    if not provider:
        raise RuntimeError("provider 不能为空。")
    body = {}
    for key in ("displayName", "key", "model", "imageModel", "baseURL", "isActive", "reasoningEnabled", "concurrencyLimit", "requestIntervalMs"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    if not body:
        raise RuntimeError("没有提供要更新的模型配置字段。")
    data = _unwrap(_api("PUT", f"/api/settings/api-keys/{urllib.parse.quote(provider)}", body, timeout=int(args.get("timeoutSeconds", 45))))
    return _redact_config({"updated": True, "provider": data})


def tool_set_current_model(args):
    _ensure_backend_for_write({"autoStart": args.get("autoStart", True)})
    body = {
        "provider": args.get("provider"),
        "model": args.get("model"),
        "temperature": float(args.get("temperature", 0.7)),
    }
    if args.get("maxTokens") is not None:
        body["maxTokens"] = int(args.get("maxTokens"))
    data = _unwrap(_api("PUT", "/api/settings/llm-selection", body, timeout=12))
    return {"updated": True, "currentSelection": data}


def tool_set_model_route(args):
    _ensure_backend_for_write({"autoStart": args.get("autoStart", True)})
    body = {
        "taskType": args.get("taskType"),
        "provider": args.get("provider"),
        "model": args.get("model"),
    }
    for key in ("temperature", "maxTokens", "requestProtocol", "structuredResponseFormat"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    data = _api("PUT", "/api/llm/model-routes", body, timeout=12)
    return {"updated": True, "route": body, "response": data}


def tool_test_model(args):
    _ensure_backend_for_write({"autoStart": args.get("autoStart", True)})
    body = {
        "provider": args.get("provider"),
        "model": args.get("model"),
        "probeMode": args.get("probeMode", "both"),
    }
    if args.get("key"):
        body["apiKey"] = args.get("key")
    if args.get("baseURL"):
        body["baseURL"] = args.get("baseURL")
    data = _unwrap(_api("POST", "/api/llm/test", body, timeout=int(args.get("timeoutSeconds", 90))))
    return _redact_config({"tested": True, "result": data})


def tool_list_novels(args):
    page = int(args.get("page", 1))
    limit = int(args.get("limit", 12))
    if args.get("offline") or not find_base_url():
        return {"source": "sqlite", "items": _db_list_novels(limit=limit)}
    data = _unwrap(_api("GET", f"/api/novels?{urllib.parse.urlencode({'page': page, 'limit': limit})}", timeout=8))
    return data


def _novel_id(args):
    return args.get("novelId") or DEFAULT_NOVEL_ID


def tool_list_chapters(args):
    novel_id = _novel_id(args)
    if args.get("offline") or not find_base_url():
        return {"source": "sqlite", "items": _db_list_chapters(novel_id)}
    chapters = _unwrap(_api("GET", f"/api/novels/{urllib.parse.quote(novel_id)}/chapters", timeout=12))
    if isinstance(chapters, list):
        return [
            {
                "id": c.get("id"),
                "order": c.get("order"),
                "title": c.get("title"),
                "status": c.get("chapterStatus"),
                "targetWordCount": c.get("targetWordCount"),
                "contentLength": len(c.get("content") or ""),
                "expectation": _clip(c.get("expectation"), 280),
            }
            for c in chapters
        ]
    return chapters


def _find_chapter(novel_id, chapter_id=None, order=None):
    if not find_base_url():
        return _db_find_chapter(novel_id, chapter_id, order)
    chapters = _unwrap(_api("GET", f"/api/novels/{urllib.parse.quote(novel_id)}/chapters", timeout=12))
    if not isinstance(chapters, list):
        raise RuntimeError("章节列表返回格式异常。")
    for chapter in chapters:
        if chapter_id and chapter.get("id") == chapter_id:
            return chapter
        if order is not None and chapter.get("order") == int(order):
            return chapter
    raise RuntimeError("找不到指定章节。")


def tool_get_chapter(args):
    novel_id = _novel_id(args)
    chapter = _db_find_chapter(novel_id, args.get("chapterId"), args.get("order")) if args.get("offline") else _find_chapter(novel_id, args.get("chapterId"), args.get("order"))
    preview_chars = int(args.get("previewChars", 2200))
    return {
        "source": "sqlite" if args.get("offline") or not find_base_url() else "api",
        "id": chapter.get("id"),
        "order": chapter.get("order"),
        "title": chapter.get("title"),
        "status": chapter.get("chapterStatus"),
        "targetWordCount": chapter.get("targetWordCount"),
        "expectation": chapter.get("expectation"),
        "taskSheet": chapter.get("taskSheet"),
        "sceneCards": chapter.get("sceneCards"),
        "mustAvoid": chapter.get("mustAvoid"),
        "contentLength": len(chapter.get("content") or ""),
        "contentPreview": _clip(chapter.get("content"), preview_chars),
    }


def tool_read_chapter_full(args):
    """返回整章完整正文，同时自动生成 HTML 预览文件供 preview 面板显示。

    Claude 收到结果后必须：
    1. 用 preview_start 启动 novel-reader 服务器
    2. 用 preview_eval 导航到 previewUrl
    3. 用 AskUserQuestion 弹出「通过 / 不通过 / 其他」选择框
    4. 根据用户选择标记章节状态
    """
    novel_id = _novel_id(args)
    chapter = _find_chapter(novel_id, args.get("chapterId"), args.get("order"))
    content = chapter.get("content") or ""
    if not content:
        raise RuntimeError("该章节没有正文内容。")
    order = int(chapter.get("order") or 0)
    title = str(chapter.get("title") or f"第{order}章")
    status = str(chapter.get("chapterStatus") or "")
    target = chapter.get("targetWordCount") or 0

    # 自动生成 HTML 预览文件（UTF-8，中文不乱码）
    import html as _html
    html_content = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<title>{_html.escape(title)}</title>'
        '<style>body{font-family:"Microsoft YaHei",sans-serif;padding:20px;'
        'line-height:1.8;font-size:15px;white-space:pre-wrap;max-width:700px;margin:0 auto}'
        'h1{font-size:18px;border-bottom:1px solid #ccc;padding-bottom:8px}'
        '.meta{color:#888;font-size:13px;margin-bottom:16px}'
        '</style></head><body>'
        f'<h1>第{order}章 {_html.escape(title)}</h1>'
        f'<div class="meta">状态: {_html.escape(status)} | 目标: {target}字 | 实际: {len(content)}字</div>'
        f'{_html.escape(content)}'
        '</body></html>'
    )
    drafts_dir = DRAFTS_DIR
    drafts_dir.mkdir(parents=True, exist_ok=True)
    html_path = drafts_dir / f"ch{order}.html"
    html_path.write_text(html_content, encoding="utf-8")
    preview_url = f"http://localhost:8765/ch{order}.html"

    # 渲染指令：告诉 Claude 必须执行的完整流程
    rendered = (
        f"【交互式章节审阅流程 — 必须严格执行】\n\n"
        f"第{order}章「{title}」已生成（{len(content)}字，状态: {status}）\n\n"
        f"执行步骤：\n"
        f"1. 调用 preview_start(name='novel-reader') 启动预览服务器\n"
        f"2. 调用 preview_eval 执行 window.location.href = '/ch{order}.html'\n"
        f"3. 用户在右侧 preview 面板读正文\n"
        f"4. 调用 AskUserQuestion 弹出选择框，选项：通过 / 不通过 / 其他\n"
        f"5. 用户选择「通过」→ 调用 update_chapter_brief 设置 chapterStatus='completed'\n"
        f"   用户选择「不通过」→ 记录修改意见，重新生成\n"
        f"   用户选择「其他」→ 按用户指示处理\n\n"
        f"Preview URL: {preview_url}\n"
        f"HTML 文件: {html_path}\n"
    )
    return {
        "renderMarkdown": rendered,
        "previewUrl": preview_url,
        "htmlPath": str(html_path),
        "meta": {
            "id": chapter.get("id"),
            "order": order,
            "title": title,
            "status": status,
            "targetWordCount": target,
            "contentLength": len(content),
        },
    }


def tool_get_chapter_sample(args):
    novel_id = _novel_id(args)
    chapter = _db_find_chapter(novel_id, args.get("chapterId"), args.get("order"))
    sample_chars = int(args.get("sampleChars", 6000))
    path = _save_sample_file(novel_id, chapter)
    content = chapter.get("content") or ""
    order = int(chapter.get("order") or 0)
    title = str(chapter.get("title") or "")
    status = str(chapter.get("chapterStatus") or "")
    # Rendering instruction for Claude Desktop artifact
    payload = (
        f"【渲染指令】请将下面 --- 分隔线之间的全部正文,作为一个标题为「第{order}章 {title}」的 "
        f"Markdown 文档 artifact 完整输出,保持原文不变。对话里只需说'第{order}章已在右侧画布打开'。\n\n---\n\n"
        f"# 第{order}章 {title}\n\n{content}\n\n---"
    )
    return {
        "chapterId": chapter.get("id"),
        "order": order,
        "title": title,
        "status": status,
        "contentLength": len(content),
        "samplePath": str(path),
        "sample": _clip(content, sample_chars),
        "artifact_markdown": payload,
    }


def tool_style_context(args):
    novel_id = _novel_id(args)
    return {
        "styleProfiles": _db_recent_style_context(limit=int(args.get("styleLimit", 5))),
        "characters": _db_character_brief(novel_id, limit=int(args.get("characterLimit", 12))),
    }


def tool_production_status(args):
    novel_id = _novel_id(args)
    with _db_connect(read_only=True) as conn:
        novel = conn.execute(
            """
            select id, title, description, status, projectStatus, storylineStatus, outlineStatus,
                   defaultChapterLength, estimatedChapterCount, outline, structuredOutline,
                   storyWorldSliceJson, worldId, updatedAt
            from Novel
            where id = ?
            limit 1
            """,
            (novel_id,),
        ).fetchone()
        if not novel:
            raise RuntimeError("未找到当前小说。")
        novel = _row_dict(novel)
        chapters = []
        if _db_table_exists(conn, "Chapter"):
            chapters = [_row_dict(row) for row in conn.execute(
                """
                select id, "order", title, content, generationState, chapterStatus,
                       targetWordCount, expectation, taskSheet, sceneCards, mustAvoid, updatedAt
                from Chapter
                where novelId = ?
                order by "order" asc
                """,
                (novel_id,),
            ).fetchall()]
        latest_job = _latest_generation_job(conn, novel_id)
        latest_task = _latest_workflow_task(conn, novel_id)
        latest_director_task = _latest_workflow_task(conn, novel_id, "auto_director")
        chapter_progress = _chapter_progress_summary(chapters)
        structured_count = _structured_outline_chapter_count(novel.get("structuredOutline"))
        target_chapter_count = int(args.get("targetChapterCount") or novel.get("estimatedChapterCount") or structured_count or len(chapters) or 20)
        counts = {
            "characters": _db_count(conn, "Character", "novelId = ?", (novel_id,)),
            "chapterSummaries": _db_count(conn, "ChapterSummary", "novelId = ?", (novel_id,)),
            "consistencyFacts": _db_count(conn, "ConsistencyFact", "novelId = ?", (novel_id,)),
            "novelFactEntries": _db_count(conn, "NovelFactEntry", "novelId = ?", (novel_id,)),
            "payoffLedgerItems": _db_count(conn, "PayoffLedgerItem", "novelId = ?", (novel_id,)),
            "characterResourceLedgerItems": _db_count(conn, "CharacterResourceLedgerItem", "novelId = ?", (novel_id,)),
            "timelineEvents": _db_count(conn, "StoryTimelineEvent", "novelId = ?", (novel_id,)),
            "timelineHooksOpen": _db_count(conn, "TimelineHook", "novelId = ? and status != ?", (novel_id, "resolved")),
            "knowledgeBindings": _db_count(conn, "KnowledgeBinding", "targetType = ? and targetId = ?", ("novel", novel_id)),
            "styleBindings": _db_count(conn, "StyleBinding", "targetType = ? and targetId = ? and enabled = 1", ("novel", novel_id)),
            "generationJobs": _db_count(conn, "GenerationJob", "novelId = ?", (novel_id,)),
            "workflowTasks": _db_count(conn, "NovelWorkflowTask", "novelId = ?", (novel_id,)),
        }
        facts = {
            "hasWorld": bool(novel.get("worldId")) or _db_count(conn, "NovelWorld", "novelId = ?", (novel_id,)) > 0,
            "hasStoryMacro": _db_count(conn, "StoryMacroPlan", "novelId = ?", (novel_id,)) > 0,
            "hasBookContract": _db_count(conn, "BookContract", "novelId = ?", (novel_id,)) > 0,
            "hasStoryBible": _db_count(conn, "NovelBible", "novelId = ?", (novel_id,)) > 0,
            "hasCharacters": counts["characters"] > 0,
            "hasVolumeStrategy": _db_count(conn, "VolumePlan", "novelId = ?", (novel_id,)) > 0 or _db_count(conn, "VolumePlanVersion", "novelId = ?", (novel_id,)) > 0,
            "hasOutline": _truthy_text(novel.get("outline")) or _truthy_text(novel.get("structuredOutline")),
            "hasStructuredOutline": structured_count > 0,
            "hasChapterTaskSheets": chapter_progress["chaptersWithTaskSheets"] > 0,
        }
        asset_stages = [
            {"key": "novel_workspace", "label": "小说工作区", "status": "completed", "detail": novel.get("title")},
            {"key": "world", "label": "本书世界", "status": "completed" if facts["hasWorld"] else "pending", "detail": novel.get("worldId")},
            {"key": "story_macro", "label": "故事宏观规划", "status": "completed" if facts["hasStoryMacro"] else "pending", "detail": None},
            {"key": "book_contract", "label": "Book Contract", "status": "completed" if facts["hasBookContract"] else "pending", "detail": None},
            {"key": "characters", "label": "核心角色", "status": "completed" if facts["hasCharacters"] else "pending", "detail": f'{counts["characters"]} 个角色'},
            {"key": "story_bible", "label": "小说圣经", "status": "completed" if facts["hasStoryBible"] else "pending", "detail": None},
            {"key": "volume_strategy", "label": "卷规划", "status": "completed" if facts["hasVolumeStrategy"] else "pending", "detail": None},
            {"key": "structured_outline", "label": "结构化大纲", "status": "completed" if facts["hasStructuredOutline"] else "pending", "detail": f"{structured_count} 个章节信号" if structured_count else None},
            {"key": "chapters", "label": "章节任务单", "status": "completed" if facts["hasChapterTaskSheets"] else "pending", "detail": f'{chapter_progress["chaptersWithTaskSheets"]}/{len(chapters)} 章'},
            {"key": "chapter_drafts", "label": "章节正文", "status": "completed" if chapter_progress["draftedChapterCount"] >= target_chapter_count and target_chapter_count > 0 else ("running" if chapter_progress["draftedChapterCount"] else "pending"), "detail": f'{chapter_progress["draftedChapterCount"]}/{target_chapter_count} 章'},
            {"key": "quality_repair", "label": "审校与修复", "status": "blocked" if chapter_progress["needsRepairChapters"] else ("running" if chapter_progress["reviewedChapterCount"] else "pending"), "detail": f'{chapter_progress["needsRepairChapters"]} 章待修复' if chapter_progress["needsRepairChapters"] else None},
            {"key": "pipeline", "label": "后台任务", "status": (latest_job or {}).get("status") or "idle", "detail": (latest_job or {}).get("error")},
        ]
        planning_keys = {"novel_workspace", "world", "story_macro", "book_contract", "characters", "story_bible", "volume_strategy", "structured_outline", "chapters"}
        assets_ready = all(stage["status"] == "completed" for stage in asset_stages if stage["key"] in planning_keys)
        pipeline_ready = assets_ready and facts["hasChapterTaskSheets"]
        active_stage = next((stage for stage in asset_stages if stage["status"] in ("pending", "running", "blocked", "queued", "failed")), asset_stages[-1])
    return {
        "source": "sqlite_readonly",
        "novelId": novel_id,
        "title": novel.get("title"),
        "targetChapterCount": target_chapter_count,
        "assetsReady": assets_ready,
        "pipelineReady": pipeline_ready,
        "currentStage": active_stage["key"],
        "currentStageLabel": active_stage["label"],
        "assetStages": asset_stages,
        "chapterProgress": chapter_progress,
        "memoryCounts": counts,
        "facts": facts,
        "latestGenerationJob": latest_job,
        "latestWorkflowTask": latest_task,
        "latestDirectorTask": latest_director_task,
        "summary": f"《{novel.get('title')}》当前阶段：{active_stage['label']}；正文 {chapter_progress['draftedChapterCount']}/{target_chapter_count} 章；事实账本 {counts['novelFactEntries']} 条，伏笔账本 {counts['payoffLedgerItems']} 条。",
    }


def tool_director_status(args):
    novel_id = _novel_id(args)
    limit = int(args.get("limit", 12))
    with _db_connect(read_only=True) as conn:
        task = _latest_workflow_task(conn, novel_id, "auto_director")
        runtime = None
        if _db_table_exists(conn, "DirectorRuntimeInstance"):
            row = conn.execute(
                """
                select id, novelId, workflowTaskId, runId, runMode, status, currentStep,
                       currentChapterId, checkpointVersion, cancelRequestedAt, lastHeartbeatAt,
                       lastErrorClass, lastErrorMessage, workerMessage, metadataJson, updatedAt
                from DirectorRuntimeInstance
                where novelId = ?
                order by updatedAt desc
                limit 1
                """,
                (novel_id,),
            ).fetchone()
            runtime = _row_dict(row) if row else None
            if runtime:
                runtime["metadataJson"] = _json_or_none(runtime.get("metadataJson"))
        events = []
        if _db_table_exists(conn, "DirectorRuntimeEvent"):
            events = _db_fetch_limited(
                conn,
                "DirectorRuntimeEvent",
                ["id", "runtimeId", "workflowTaskId", "novelId", "type", "summary", "severity", "metadataJson", "occurredAt"],
                "novelId = ?",
                (novel_id,),
                "occurredAt desc",
                limit,
            )
        legacy_events = []
        if _db_table_exists(conn, "DirectorEvent"):
            legacy_events = _db_fetch_limited(
                conn,
                "DirectorEvent",
                ["id", "runId", "taskId", "novelId", "type", "nodeKey", "artifactType", "summary", "affectedScope", "severity", "metadataJson", "occurredAt"],
                "novelId = ?",
                (novel_id,),
                "occurredAt desc",
                limit,
            )
        steps = []
        if _db_table_exists(conn, "DirectorStepRun"):
            steps = _db_fetch_limited(
                conn,
                "DirectorStepRun",
                ["id", "runId", "taskId", "novelId", "nodeKey", "label", "status", "targetType", "targetId", "startedAt", "finishedAt", "error", "producedArtifactsJson", "policyDecisionJson", "updatedAt"],
                "novelId = ?",
                (novel_id,),
                "updatedAt desc",
                limit,
            )
        artifacts = []
        if _db_table_exists(conn, "DirectorArtifact"):
            artifacts = _db_fetch_limited(
                conn,
                "DirectorArtifact",
                ["id", "runId", "novelId", "taskId", "artifactType", "targetType", "targetId", "version", "status", "source", "contentTable", "contentId", "protectedUserContent", "artifactUpdatedAt", "updatedAt"],
                "novelId = ?",
                (novel_id,),
                "updatedAt desc",
                limit,
            )
    blocking_reason = None
    if runtime and runtime.get("lastErrorMessage"):
        blocking_reason = runtime.get("lastErrorMessage")
    elif task and task.get("lastError"):
        blocking_reason = task.get("lastError")
    return {
        "source": "sqlite_readonly",
        "novelId": novel_id,
        "task": task,
        "runtime": runtime,
        "recentRuntimeEvents": events,
        "recentDirectorEvents": legacy_events,
        "recentSteps": steps,
        "recentArtifacts": artifacts,
        "requiresAttention": bool(blocking_reason or (task and task.get("pendingManualRecovery")) or (runtime and runtime.get("status") in ("failed", "blocked"))),
        "blockingReason": blocking_reason,
        "summary": blocking_reason or (task.get("checkpointSummary") if task else None) or (runtime.get("workerMessage") if runtime else None) or "未发现自动导演阻塞信息。",
    }


def tool_read_ledgers(args):
    novel_id = _novel_id(args)
    limit = int(args.get("limit", 30))
    before_order = args.get("beforeChapterOrder")
    before_clause = ""
    before_params = []
    if before_order is not None:
        before_clause = " and chapterOrder < ?"
        before_params.append(int(before_order))
    with _db_connect(read_only=True) as conn:
        facts = _db_fetch_limited(
            conn,
            "NovelFactEntry",
            ["id", "novelId", "chapterOrder", "text", "category", "source", "createdAt"],
            "novelId = ?" + before_clause,
            (novel_id, *before_params),
            "chapterOrder desc, createdAt desc",
            limit,
        )
        consistency_facts = _db_fetch_limited(
            conn,
            "ConsistencyFact",
            ["id", "novelId", "chapterId", "category", "content", "source", "createdAt", "updatedAt"],
            "novelId = ?",
            (novel_id,),
            "updatedAt desc",
            limit,
        )
        payoffs = _db_fetch_limited(
            conn,
            "PayoffLedgerItem",
            ["id", "novelId", "ledgerKey", "title", "summary", "scopeType", "currentStatus", "targetStartChapterOrder", "targetEndChapterOrder", "firstSeenChapterOrder", "lastTouchedChapterOrder", "statusReason", "confidence", "updatedAt"],
            "novelId = ?",
            (novel_id,),
            "updatedAt desc",
            limit,
        )
        resources = _db_fetch_limited(
            conn,
            "CharacterResourceLedgerItem",
            ["id", "novelId", "resourceKey", "name", "summary", "resourceType", "narrativeFunction", "ownerType", "ownerName", "holderCharacterName", "status", "readerKnows", "holderKnows", "introducedChapterOrder", "lastTouchedChapterOrder", "expectedUseStartChapterOrder", "expectedUseEndChapterOrder", "confidence", "updatedAt"],
            "novelId = ?",
            (novel_id,),
            "updatedAt desc",
            limit,
        )
        timeline_events = _db_fetch_limited(
            conn,
            "StoryTimelineEvent",
            ["id", "novelId", "chapterId", "chapterIndex", "eventOrder", "storyDayIndex", "storyTimeLabel", "title", "summary", "type", "status", "visibility", "source", "participantIdsJson", "locationId", "confidence", "updatedAt"],
            "novelId = ?",
            (novel_id,),
            "eventOrder desc, updatedAt desc",
            limit,
        )
        hooks = _db_fetch_limited(
            conn,
            "TimelineHook",
            ["id", "novelId", "createdInChapterIndex", "expectedResolveByChapterIndex", "resolveMode", "blocking", "resolvedInChapterIndex", "title", "description", "status", "priority", "updatedAt"],
            "novelId = ?",
            (novel_id,),
            "updatedAt desc",
            limit,
        )
        constraints = _db_fetch_limited(
            conn,
            "TimelineConstraint",
            ["id", "novelId", "chapterId", "chapterIndex", "type", "severity", "description", "active", "updatedAt"],
            "novelId = ? and active = 1",
            (novel_id,),
            "updatedAt desc",
            limit,
        )
        summaries = _db_fetch_limited(
            conn,
            "ChapterSummary",
            ["id", "novelId", "chapterId", "summary", "keyEvents", "characterStates", "hook", "updatedAt"],
            "novelId = ?",
            (novel_id,),
            "updatedAt desc",
            limit,
        )
    return {
        "source": "sqlite_readonly",
        "novelId": novel_id,
        "filters": {"beforeChapterOrder": before_order, "limit": limit},
        "counts": {
            "novelFacts": len(facts),
            "consistencyFacts": len(consistency_facts),
            "payoffs": len(payoffs),
            "characterResources": len(resources),
            "timelineEvents": len(timeline_events),
            "timelineHooks": len(hooks),
            "activeTimelineConstraints": len(constraints),
            "chapterSummaries": len(summaries),
        },
        "novelFacts": facts,
        "consistencyFacts": consistency_facts,
        "payoffLedger": payoffs,
        "characterResourceLedger": resources,
        "timelineEvents": timeline_events,
        "timelineHooks": hooks,
        "activeTimelineConstraints": constraints,
        "chapterSummaries": summaries,
    }


def tool_knowledge_list_documents(args):
    limit = int(args.get("limit", 20))
    status = args.get("status")
    keyword = (args.get("keyword") or "").strip()
    if not args.get("offline") and find_base_url():
        query = {}
        if status:
            query["status"] = status
        if keyword:
            query["keyword"] = keyword
        path = "/api/knowledge/documents"
        if query:
            path += "?" + urllib.parse.urlencode(query)
        data = _unwrap(_api("GET", path, timeout=12))
        if isinstance(data, list):
            return {"source": "api", "items": data[:limit], "count": len(data)}
        return {"source": "api", "data": data}
    with _db_connect(read_only=True) as conn:
        where = []
        params = []
        if status:
            where.append("status = ?")
            params.append(status)
        else:
            where.append("status != ?")
            params.append("archived")
        if keyword:
            where.append("(title like ? or fileName like ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        rows = _db_fetch_limited(
            conn,
            "KnowledgeDocument",
            ["id", "title", "fileName", "status", "activeVersionId", "activeVersionNumber", "latestIndexStatus", "lastIndexedAt", "createdAt", "updatedAt"],
            " and ".join(where),
            tuple(params),
            "updatedAt desc",
            limit,
        )
        for row in rows:
            row["versionCount"] = _db_count(conn, "KnowledgeDocumentVersion", "documentId = ?", (row["id"],))
            row["bookAnalysisCount"] = _db_count(conn, "BookAnalysis", "documentId = ?", (row["id"],))
            row["bindingCount"] = _db_count(conn, "KnowledgeBinding", "documentId = ?", (row["id"],))
    return {"source": "sqlite_readonly", "items": rows, "count": len(rows)}


def tool_knowledge_get_document(args):
    document_id = (args.get("documentId") or "").strip()
    if not document_id:
        raise RuntimeError("documentId 不能为空。")
    if not args.get("offline") and find_base_url():
        data = _unwrap(_api("GET", f"/api/knowledge/documents/{urllib.parse.quote(document_id)}", timeout=12))
        return {"source": "api", "document": data}
    with _db_connect(read_only=True) as conn:
        row = _db_fetch_limited(
            conn,
            "KnowledgeDocument",
            ["id", "title", "fileName", "status", "activeVersionId", "activeVersionNumber", "latestIndexStatus", "lastIndexedAt", "createdAt", "updatedAt"],
            "id = ?",
            (document_id,),
            None,
            1,
        )
        if not row:
            raise RuntimeError("Knowledge document not found.")
        document = row[0]
        version_limit = int(args.get("versionLimit", 5))
        versions = _db_fetch_limited(
            conn,
            "KnowledgeDocumentVersion",
            ["id", "documentId", "versionNumber", "content", "contentHash", "charCount", "createdAt"],
            "documentId = ?",
            (document_id,),
            "versionNumber desc, createdAt desc",
            version_limit,
        )
        preview_chars = int(args.get("previewChars", 1200))
        for version in versions:
            if "content" in version:
                version["contentPreview"] = _clip(version.pop("content"), preview_chars)
        bindings = _db_fetch_limited(
            conn,
            "KnowledgeBinding",
            ["id", "targetType", "targetId", "documentId", "createdAt"],
            "documentId = ?",
            (document_id,),
            "createdAt desc",
            20,
        )
    return {"source": "sqlite_readonly", "document": document, "versions": versions, "bindings": bindings}


def tool_knowledge_create_document(args):
    _ensure_backend_for_write(args)
    title = (args.get("title") or "").strip() or None
    file_name = (args.get("fileName") or "").strip()
    content = args.get("content") or ""
    if not file_name:
        raise RuntimeError("fileName 不能为空。")
    if not str(content).strip():
        raise RuntimeError("content 不能为空。")
    body = {"fileName": file_name, "content": str(content)}
    if title:
        body["title"] = title
    data = _unwrap(_api("POST", "/api/knowledge/documents", body, timeout=int(args.get("timeoutSeconds", 45))))
    return {"created": True, "document": data}


def tool_knowledge_create_version(args):
    _ensure_backend_for_write(args)
    document_id = (args.get("documentId") or "").strip()
    content = args.get("content") or ""
    if not document_id:
        raise RuntimeError("documentId 不能为空。")
    if not str(content).strip():
        raise RuntimeError("content 不能为空。")
    body = {"content": str(content)}
    if args.get("fileName"):
        body["fileName"] = args.get("fileName")
    data = _unwrap(_api("POST", f"/api/knowledge/documents/{urllib.parse.quote(document_id)}/versions", body, timeout=int(args.get("timeoutSeconds", 45))))
    return {"createdVersion": True, "document": data}


def tool_knowledge_reindex_document(args):
    _ensure_backend_for_write(args)
    document_id = (args.get("documentId") or "").strip()
    if not document_id:
        raise RuntimeError("documentId 不能为空。")
    data = _unwrap(_api("POST", f"/api/knowledge/documents/{urllib.parse.quote(document_id)}/reindex", timeout=int(args.get("timeoutSeconds", 45))))
    return {"queued": True, "document": data}


def tool_knowledge_recall_test(args):
    _ensure_backend_for_write(args)
    document_id = (args.get("documentId") or "").strip()
    query = (args.get("query") or "").strip()
    if not document_id:
        raise RuntimeError("documentId 不能为空。")
    if not query:
        raise RuntimeError("query 不能为空。")
    body = {"query": query, "limit": int(args.get("limit", 5))}
    data = _unwrap(_api("POST", f"/api/knowledge/documents/{urllib.parse.quote(document_id)}/recall-test", body, timeout=int(args.get("timeoutSeconds", 45))))
    return {"tested": True, "result": data}


def tool_book_analysis_list(args):
    limit = int(args.get("limit", 20))
    status = args.get("status")
    document_id = args.get("documentId")
    keyword = (args.get("keyword") or "").strip()
    if not args.get("offline") and find_base_url():
        query = {}
        if status:
            query["status"] = status
        if document_id:
            query["documentId"] = document_id
        if keyword:
            query["keyword"] = keyword
        path = "/api/book-analysis"
        if query:
            path += "?" + urllib.parse.urlencode(query)
        data = _unwrap(_api("GET", path, timeout=12))
        if isinstance(data, list):
            return {"source": "api", "items": data[:limit], "count": len(data)}
        return {"source": "api", "data": data}
    with _db_connect(read_only=True) as conn:
        where = []
        params = []
        if status:
            where.append("status = ?")
            params.append(status)
        if document_id:
            where.append("documentId = ?")
            params.append(document_id)
        if keyword:
            where.append("title like ?")
            params.append(f"%{keyword}%")
        rows = _db_fetch_limited(
            conn,
            "BookAnalysis",
            ["id", "documentId", "documentVersionId", "title", "status", "summary", "provider", "model", "temperature", "maxTokens", "progress", "pendingManualRecovery", "heartbeatAt", "currentStage", "currentItemKey", "currentItemLabel", "attemptCount", "maxAttempts", "lastError", "lastRunAt", "publishedDocumentId", "createdAt", "updatedAt"],
            " and ".join(where),
            tuple(params),
            "updatedAt desc",
            limit,
        )
        for row in rows:
            row["sectionCount"] = _db_count(conn, "BookAnalysisSection", "analysisId = ?", (row["id"],))
    return {"source": "sqlite_readonly", "items": rows, "count": len(rows)}


def tool_book_analysis_get(args):
    analysis_id = (args.get("analysisId") or "").strip()
    if not analysis_id:
        raise RuntimeError("analysisId 不能为空。")
    if not args.get("offline") and find_base_url():
        data = _unwrap(_api("GET", f"/api/book-analysis/{urllib.parse.quote(analysis_id)}", timeout=12))
        return {"source": "api", "analysis": data}
    preview_chars = int(args.get("previewChars", 1200))
    with _db_connect(read_only=True) as conn:
        rows = _db_fetch_limited(
            conn,
            "BookAnalysis",
            ["id", "documentId", "documentVersionId", "title", "status", "summary", "provider", "model", "temperature", "maxTokens", "progress", "pendingManualRecovery", "heartbeatAt", "currentStage", "currentItemKey", "currentItemLabel", "attemptCount", "maxAttempts", "lastError", "lastRunAt", "publishedDocumentId", "createdAt", "updatedAt"],
            "id = ?",
            (analysis_id,),
            None,
            1,
        )
        if not rows:
            raise RuntimeError("Book analysis not found.")
        sections = _db_fetch_limited(
            conn,
            "BookAnalysisSection",
            ["id", "analysisId", "sectionKey", "title", "status", "aiContent", "editedContent", "notes", "structuredDataJson", "evidenceJson", "frozen", "sortOrder", "updatedAt"],
            "analysisId = ?",
            (analysis_id,),
            "sortOrder asc",
            20,
        )
        for section in sections:
            for key in ("aiContent", "editedContent", "notes"):
                if key in section and section[key] is not None:
                    section[key + "Preview"] = _clip(section.pop(key), preview_chars)
    return {"source": "sqlite_readonly", "analysis": rows[0], "sections": sections}


def tool_book_analysis_create(args):
    _ensure_backend_for_write(args)
    document_id = (args.get("documentId") or "").strip()
    if not document_id:
        raise RuntimeError("documentId 不能为空。")
    body = {"documentId": document_id}
    for key in ("versionId", "provider", "model", "temperature", "maxTokens", "includeTimeline", "enabledSectionKeys"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    data = _unwrap(_api("POST", "/api/book-analysis", body, timeout=int(args.get("timeoutSeconds", 90))))
    return {"created": True, "analysis": data}


def tool_book_analysis_publish(args):
    _ensure_backend_for_write(args)
    analysis_id = (args.get("analysisId") or "").strip()
    novel_id = _novel_id(args)
    if not analysis_id:
        raise RuntimeError("analysisId 不能为空。")
    data = _unwrap(_api("POST", f"/api/book-analysis/{urllib.parse.quote(analysis_id)}/publish", {"novelId": novel_id}, timeout=int(args.get("timeoutSeconds", 45))))
    return {"published": True, "result": data}


def tool_book_analysis_export(args):
    _ensure_backend_for_write(args)
    analysis_id = (args.get("analysisId") or "").strip()
    fmt = args.get("format") or "markdown"
    if not analysis_id:
        raise RuntimeError("analysisId 不能为空。")
    base = find_base_url()
    if not base:
        raise RuntimeError("AI Novel 后端未运行。")
    url = f"{base}/api/book-analysis/{urllib.parse.quote(analysis_id)}/export?{urllib.parse.urlencode({'format': fmt})}"
    req = urllib.request.Request(url, method="GET", headers={"Accept": "text/markdown, application/json, text/plain"})
    with urllib.request.urlopen(req, timeout=int(args.get("timeoutSeconds", 45))) as response:
        raw = response.read().decode("utf-8", errors="replace")
        content_type = response.headers.get("Content-Type", "")
    return {"analysisId": analysis_id, "format": fmt, "contentType": content_type, "content": _clip(raw, int(args.get("previewChars", 6000)))}


def tool_style_list_profiles(args):
    limit = int(args.get("limit", 20))
    status = args.get("status") or "active"
    if not args.get("offline") and find_base_url():
        data = _unwrap(_api("GET", "/api/style-profiles", timeout=12))
        if isinstance(data, list):
            items = data[:limit]
            if status:
                items = [item for item in items if str(item.get("status", "active")) == status]
            return {"source": "api", "items": items, "count": len(items)}
        return {"source": "api", "data": data}
    with _db_connect(read_only=True) as conn:
        where = ""
        params = ()
        if status:
            where = "status = ?"
            params = (status,)
        rows = _db_fetch_limited(
            conn,
            "StyleProfile",
            ["id", "name", "description", "category", "tagsJson", "applicableGenresJson", "sourceType", "sourceRefId", "extractedFeaturesJson", "selectedExtractionPresetKey", "analysisMarkdown", "status", "updatedAt"],
            where,
            params,
            "updatedAt desc",
            limit,
        )
        for row in rows:
            row["bindingCount"] = _db_count(conn, "StyleBinding", "styleProfileId = ? and enabled = 1", (row["id"],))
            row["antiAiRuleCount"] = _db_count(conn, "StyleProfileAntiAiRule", "styleProfileId = ? and enabled = 1", (row["id"],))
            if "analysisMarkdown" in row:
                row["analysisMarkdownPreview"] = _clip(row.pop("analysisMarkdown"), int(args.get("previewChars", 800)))
    return {"source": "sqlite_readonly", "items": rows, "count": len(rows)}


def tool_style_get_profile(args):
    profile_id = (args.get("styleProfileId") or "").strip()
    if not profile_id:
        raise RuntimeError("styleProfileId 不能为空。")
    if not args.get("offline") and find_base_url():
        data = _unwrap(_api("GET", f"/api/style-profiles/{urllib.parse.quote(profile_id)}", timeout=12))
        return {"source": "api", "styleProfile": data}
    with _db_connect(read_only=True) as conn:
        rows = _db_fetch_limited(
            conn,
            "StyleProfile",
            ["id", "name", "description", "category", "tagsJson", "applicableGenresJson", "sourceType", "sourceRefId", "sourceContent", "extractedFeaturesJson", "extractionPresetsJson", "extractionAntiAiRuleKeysJson", "selectedExtractionPresetKey", "analysisMarkdown", "narrativeRulesJson", "characterRulesJson", "languageRulesJson", "rhythmRulesJson", "status", "createdAt", "updatedAt"],
            "id = ?",
            (profile_id,),
            None,
            1,
        )
        if not rows:
            raise RuntimeError("Style profile not found.")
        profile = rows[0]
        preview_chars = int(args.get("previewChars", 1200))
        for key in ("sourceContent", "analysisMarkdown"):
            if key in profile and profile[key] is not None:
                profile[key + "Preview"] = _clip(profile.pop(key), preview_chars)
        bindings = _db_fetch_limited(
            conn,
            "StyleBinding",
            ["id", "styleProfileId", "targetType", "targetId", "priority", "weight", "enabled", "createdAt", "updatedAt"],
            "styleProfileId = ?",
            (profile_id,),
            "updatedAt desc",
            20,
        )
        anti_bindings = _db_fetch_limited(
            conn,
            "StyleProfileAntiAiRule",
            ["id", "styleProfileId", "antiAiRuleId", "enabled", "weight", "createdAt", "updatedAt"],
            "styleProfileId = ?",
            (profile_id,),
            "updatedAt desc",
            20,
        )
    return {"source": "sqlite_readonly", "styleProfile": profile, "bindings": bindings, "antiAiBindings": anti_bindings}


def tool_style_list_bindings(args):
    limit = int(args.get("limit", 30))
    if not args.get("offline") and find_base_url():
        query = {}
        for key in ("targetType", "targetId", "styleProfileId"):
            if args.get(key):
                query[key] = args.get(key)
        path = "/api/style-bindings"
        if query:
            path += "?" + urllib.parse.urlencode(query)
        data = _unwrap(_api("GET", path, timeout=12))
        if isinstance(data, list):
            return {"source": "api", "items": data[:limit], "count": len(data)}
        return {"source": "api", "data": data}
    where = []
    params = []
    for key, column in (("targetType", "targetType"), ("targetId", "targetId"), ("styleProfileId", "styleProfileId")):
        if args.get(key):
            where.append(f"{column} = ?")
            params.append(args.get(key))
    with _db_connect(read_only=True) as conn:
        rows = _db_fetch_limited(
            conn,
            "StyleBinding",
            ["id", "styleProfileId", "targetType", "targetId", "priority", "weight", "enabled", "createdAt", "updatedAt"],
            " and ".join(where),
            tuple(params),
            "updatedAt desc",
            limit,
        )
    return {"source": "sqlite_readonly", "items": rows, "count": len(rows)}


def tool_style_bind(args):
    _ensure_backend_for_write(args)
    body = {
        "styleProfileId": args.get("styleProfileId"),
        "targetType": args.get("targetType"),
        "targetId": args.get("targetId"),
        "priority": int(args.get("priority", 1)),
        "weight": float(args.get("weight", 1)),
        "enabled": bool(args.get("enabled", True)),
    }
    if not body["styleProfileId"] or not body["targetType"] or not body["targetId"]:
        raise RuntimeError("styleProfileId、targetType、targetId 不能为空。")
    data = _unwrap(_api("POST", "/api/style-bindings", body, timeout=int(args.get("timeoutSeconds", 45))))
    return {"created": True, "binding": data}


def tool_style_create_from_text(args):
    _ensure_backend_for_write(args)
    body = {"name": args.get("name"), "sourceText": args.get("sourceText")}
    if args.get("category"):
        body["category"] = args.get("category")
    for key in ("provider", "model", "temperature"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    if not body.get("name") or not str(body.get("sourceText") or "").strip():
        raise RuntimeError("name 和 sourceText 不能为空。")
    data = _unwrap(_api("POST", "/api/style-profiles/from-text", body, timeout=int(args.get("timeoutSeconds", 120))))
    return {"created": True, "styleProfile": data}


def tool_style_create_from_brief(args):
    _ensure_backend_for_write(args)
    body = {"brief": args.get("brief")}
    for key in ("name", "category", "provider", "model", "temperature"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    if not str(body.get("brief") or "").strip():
        raise RuntimeError("brief 不能为空。")
    data = _unwrap(_api("POST", "/api/style-profiles/from-brief", body, timeout=int(args.get("timeoutSeconds", 90))))
    return {"created": True, "styleProfile": data}


def tool_style_create_from_book_analysis(args):
    _ensure_backend_for_write(args)
    body = {"bookAnalysisId": args.get("analysisId") or args.get("bookAnalysisId"), "name": args.get("name")}
    for key in ("provider", "model", "temperature"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    if not body.get("bookAnalysisId") or not body.get("name"):
        raise RuntimeError("analysisId/bookAnalysisId 和 name 不能为空。")
    data = _unwrap(_api("POST", "/api/style-profiles/from-book-analysis", body, timeout=int(args.get("timeoutSeconds", 120))))
    return {"created": True, "styleProfile": data}


def tool_anti_ai_rules(args):
    limit = int(args.get("limit", 80))
    if not args.get("offline") and find_base_url():
        data = _unwrap(_api("GET", "/api/anti-ai-rules", timeout=12))
        if isinstance(data, list):
            return {"source": "api", "items": data[:limit], "count": len(data)}
        return {"source": "api", "data": data}
    with _db_connect(read_only=True) as conn:
        rows = _db_fetch_limited(
            conn,
            "AntiAiRule",
            ["id", "key", "name", "type", "severity", "description", "detectPatternsJson", "rewriteSuggestion", "promptInstruction", "autoRewrite", "enabled", "globalBaselineEnabled", "updatedAt"],
            "",
            (),
            "updatedAt desc",
            limit,
        )
    return {"source": "sqlite_readonly", "items": rows, "count": len(rows)}


def tool_style_detect(args):
    _ensure_backend_for_write(args)
    content = args.get("content") or ""
    if not str(content).strip():
        raise RuntimeError("content 不能为空。")
    body = {"content": str(content)}
    for key in ("styleProfileId", "novelId", "chapterId", "taskStyleProfileId", "previewAntiAiRuleIds", "provider", "model", "temperature"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    data = _unwrap(_api("POST", "/api/style-detection/check", body, timeout=int(args.get("timeoutSeconds", 90))))
    return {"checked": True, "result": data}


def tool_style_rewrite(args):
    _ensure_backend_for_write(args)
    content = args.get("content") or ""
    issues = args.get("issues") or []
    if not str(content).strip():
        raise RuntimeError("content 不能为空。")
    if not issues:
        raise RuntimeError("issues 不能为空。")
    body = {"content": str(content), "issues": issues}
    for key in ("styleProfileId", "novelId", "chapterId", "taskStyleProfileId", "previewAntiAiRuleIds", "provider", "model", "temperature"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    data = _unwrap(_api("POST", "/api/style-detection/rewrite", body, timeout=int(args.get("timeoutSeconds", 120))))
    return {"rewritten": True, "result": data}


def tool_update_chapter_brief(args):
    _ensure_backend_for_write(args)
    novel_id = _novel_id(args)
    chapter = _find_chapter(novel_id, args.get("chapterId"), args.get("order"))
    chapter_id = chapter["id"]
    body = {}
    for key in ("title", "expectation", "taskSheet", "sceneCards", "mustAvoid", "targetWordCount", "chapterStatus"):
        if key in args and args[key] is not None:
            body[key] = args[key]
    if not body:
        raise RuntimeError("没有提供要更新的字段。")
    data = _unwrap(_api("PUT", f"/api/novels/{urllib.parse.quote(novel_id)}/chapters/{urllib.parse.quote(chapter_id)}", body, timeout=12))
    return {"updated": True, "chapterId": chapter_id, "fields": sorted(body.keys()), "chapter": data}


def tool_interactive_choice(args):
    _ensure_backend_for_write(args)
    novel_id = _novel_id(args)
    chapter = _find_chapter(novel_id, args.get("chapterId"), args.get("order"))
    chapter_id = chapter["id"]
    user_choice = args.get("userChoice", "").strip()
    host_note = args.get("hostNote", "").strip()
    if not user_choice:
        raise RuntimeError("userChoice 不能为空。")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"\n\n[Claude互动创作记录 {stamp}]\n"
        f"玩家选择/作者意见：{user_choice}\n"
        f"主持人整理：{host_note or '按作者选择推进，不擅自改人设和主线。'}\n"
    )
    existing = chapter.get("taskSheet") or chapter.get("expectation") or ""
    body = {
        "taskSheet": (existing + block).strip(),
        "chapterStatus": "pending_generation",
    }
    data = _unwrap(_api("PUT", f"/api/novels/{urllib.parse.quote(novel_id)}/chapters/{urllib.parse.quote(chapter_id)}", body, timeout=12))
    return {"recorded": True, "chapterId": chapter_id, "added": block.strip(), "chapter": data}


def tool_generate_chapter(args):
    _ensure_backend_for_write(args)
    novel_id = _novel_id(args)
    chapter = _find_chapter(novel_id, args.get("chapterId"), args.get("order"))
    chapter_id = chapter["id"]
    chapter_order = int(chapter.get("order") or args.get("order") or 0)

    # ---- Per-chapter approval gate ----
    # Workflow: generate → sidebar → user approval → next chapter.
    # If the previous chapter exists and is not approved, refuse.
    if chapter_order > 1 and not args.get("force"):
        prev = _db_find_chapter(novel_id, order=chapter_order - 1)
        if prev:
            prev_status = (prev.get("chapterStatus") or "").lower()
            if prev_status not in ("completed", "approved"):
                raise RuntimeError(
                    "Chapter %d is not approved (status: %s). "
                    "Read the sample to sidebar, get user approval, then generate chapter %d."
                    % (chapter_order - 1, prev_status or "unknown", chapter_order)
                )
    # ---- End approval gate ----

    guidance = args.get("guidance", "").strip()
    if guidance:
        existing = chapter.get("taskSheet") or chapter.get("expectation") or ""
        body = {
            "taskSheet": (existing + "\n\n[本次生成指令]\n" + guidance).strip(),
            "chapterStatus": "pending_generation",
        }
        _api("PUT", f"/api/novels/{urllib.parse.quote(novel_id)}/chapters/{urllib.parse.quote(chapter_id)}", body, timeout=12)

    runtime_body = {
        "artifactSyncMode": "deferred",
        "controlPolicy": {
            "kickoffMode": "manual_start",
            "advanceMode": "manual",
            "reviewCheckpoints": [],
            "autoExecutionRange": None,
        },
    }
    for key in ("provider", "model", "temperature", "previousChaptersSummary"):
        if key in args and args[key] is not None:
            runtime_body[key] = args[key]
    before = _db_find_chapter(novel_id, chapter_id=chapter_id)
    before_length = len(before.get("content") or "")
    result = _api(
        "POST",
        f"/api/novels/{urllib.parse.quote(novel_id)}/chapters/{urllib.parse.quote(chapter_id)}/generate",
        runtime_body,
        timeout=int(args.get("timeoutSeconds", 240)),
    )
    after = _db_find_chapter(novel_id, chapter_id=chapter_id)
    sample_path = _save_sample_file(novel_id, after)
    content = after.get("content") or ""
    return {
        "chapterId": chapter_id,
        "generation": result,
        "beforeLength": before_length,
        "afterLength": len(content),
        "samplePath": str(sample_path),
        "sample": _clip(content, int(args.get("sampleChars", 4500))),
    }


def _read_style_files():
    parts = []
    for name in ("AUTHOR_STYLE.md", "DIRECTOR_NOTES.md", "CHARACTER_RULES.md", "CANON.md", "CHAPTER_REVIEW_TEMPLATE.md"):
        path = WORKSPACE / name
        if path.exists():
            parts.append(f"## {name}\n{_clip(path.read_text(encoding='utf-8', errors='ignore'), 2200)}")
    return "\n\n".join(parts)


def _overnight_guidance(base_guidance):
    style_context = _read_style_files()
    return (
        "按作者长期风格和评审习惯创作。本轮是本地后台长跑任务，保持手动挡积累的角色规则，"
        "不要擅自大改主线、人物底色、关系方向和结局钩子。\n\n"
        f"[本轮额外指令]\n{base_guidance or '延续上一章，稳步推进关系、爽点和章节钩子。'}\n\n"
        f"[作者风格/评审资料]\n{_clip(style_context, 7000)}"
    ).strip()


def run_overnight_job(config, progress=None):
    novel_id = config.get("novelId") or DEFAULT_NOVEL_ID
    start_order = int(config.get("startOrder") or config.get("order") or 1)
    end_order = int(config.get("endOrder") or start_order)
    max_chapters = int(config.get("maxChapters") or max(1, end_order - start_order + 1))
    delay_seconds = float(config.get("delaySeconds") or 0)
    stop_on_error = bool(config.get("stopOnError", True))
    sample_chars = int(config.get("sampleChars") or 3500)
    guidance = _overnight_guidance(config.get("guidance", ""))
    _ensure_backend_for_write({"autoStart": True, "startupTimeoutSeconds": config.get("startupTimeoutSeconds", 60)})

    completed = []
    errors = []
    count = 0
    for order in range(start_order, end_order + 1):
        if count >= max_chapters:
            break
        event = {"event": "chapter_started", "order": order, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        if progress:
            progress(event)
        try:
            result = tool_generate_chapter({
                "novelId": novel_id,
                "order": order,
                "guidance": guidance,
                "timeoutSeconds": int(config.get("timeoutSeconds", 600)),
                "sampleChars": sample_chars,
                "autoStart": False,
            })
            completed.append({
                "order": order,
                "chapterId": result.get("chapterId"),
                "afterLength": result.get("afterLength"),
                "samplePath": result.get("samplePath"),
                "redlineClean": result.get("redlineClean", True),
                "redlineViolations": [v["rule"] for v in (result.get("redline") or {}).get("violations", [])],
            })
            if progress:
                progress({"event": "chapter_done", "order": order, "result": completed[-1], "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        except Exception as exc:
            item = {"order": order, "error": str(exc), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            errors.append(item)
            if progress:
                progress({"event": "chapter_error", **item})
            if stop_on_error:
                break
        count += 1
        if delay_seconds > 0:
            time.sleep(delay_seconds)
    return {"completed": completed, "errors": errors, "novelId": novel_id}


def tool_start_overnight_runner(args):
    _ensure_bridge_dirs()
    run_id = time.strftime("overnight-%Y%m%d-%H%M%S")
    config_path = BRIDGE_DIR / f"{run_id}.json"
    log_path = BRIDGE_LOG_DIR / f"{run_id}.jsonl"
    config = dict(args)
    config["runId"] = run_id
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    log_file = log_path.open("a", encoding="utf-8", buffering=1)
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "overnight-run", str(config_path)],
        cwd=str(WORKSPACE),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    state = _read_state()
    state["overnightRunner"] = {
        "runId": run_id,
        "pid": process.pid,
        "configPath": str(config_path),
        "logPath": str(log_path),
        "startedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_state(state)
    return {"started": True, "runId": run_id, "pid": process.pid, "configPath": str(config_path), "logPath": str(log_path)}


def tool_overnight_status(args):
    state = _read_state().get("overnightRunner") or {}
    log_path = Path(args.get("logPath") or state.get("logPath") or "")
    lines = []
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()[-int(args.get("tail", 20)):]
    return {"runner": state, "logTail": lines}


def _compact_model_config(config):
    providers = config.get("providers")
    provider_items = []
    if isinstance(providers, dict):
        iterable = providers.items()
    elif isinstance(providers, list):
        iterable = [(item.get("provider") or item.get("name") or item.get("id"), item) for item in providers if isinstance(item, dict)]
    else:
        iterable = []

    for provider_id, provider in iterable:
        if not isinstance(provider, dict):
            continue
        provider_items.append({
            "provider": provider_id,
            "displayName": provider.get("displayName") or provider.get("name"),
            "model": provider.get("model"),
            "baseURL": provider.get("baseURL") or provider.get("baseUrl"),
            "isActive": provider.get("isActive"),
            "concurrencyLimit": provider.get("concurrencyLimit"),
        })

    return {
        "currentSelection": config.get("currentSelection"),
        "configuredProviders": provider_items[:12],
        "modelRoutes": config.get("modelRoutes"),
        "structuredFallback": config.get("structuredFallback"),
    }


def _health_check_item(name, ok, detail=None, severity="error"):
    return {
        "name": name,
        "ok": bool(ok),
        "severity": severity,
        "detail": detail,
    }


def tool_healthcheck(args):
    if args.get("autoStart"):
        _start_headless_backend(timeout_seconds=int(args.get("timeoutSeconds", 45)))

    base = find_base_url()
    checks = []
    checks.append(_health_check_item("workspace_exists", WORKSPACE.exists(), str(WORKSPACE)))
    checks.append(_health_check_item("mcp_config_exists", (WORKSPACE / ".mcp.json").exists(), str(WORKSPACE / ".mcp.json")))
    checks.append(_health_check_item("backend_runtime_exists", DESKTOP_EXE.exists(), str(DESKTOP_EXE)))
    checks.append(_health_check_item("server_entry_exists", EXTRACTED_SERVER_ENTRY.exists(), str(EXTRACTED_SERVER_ENTRY)))
    checks.append(_health_check_item("database_exists", DB_PATH.exists(), str(DB_PATH)))
    checks.append(_health_check_item("headless_only_default", HEADLESS_ONLY, f"HEADLESS_ONLY={HEADLESS_ONLY}"))
    checks.append(_health_check_item("backend_running", bool(base), base, severity="warning"))

    client_package = BACKEND_BUNDLE_DIR / "node_modules" / "@ai-novel" / "client"
    checks.append(_health_check_item("backend_bundle_has_no_client_ui", not client_package.exists(), str(client_package), severity="warning"))

    required_files = [
        "CLAUDE.md",
        "NOVEL_CREATION_WORKFLOW.md",
        "NOVEL_CONCEPT_BOARD.md",
        "OUTLINE.md",
        "MATERIALS.md",
        "AUTHOR_STYLE.md",
        "DIRECTOR_NOTES.md",
        "CHARACTER_RULES.md",
        "CANON.md",
        ".claude/skills/novel-creation-studio/SKILL.md",
        ".claude/skills/novel-creation-studio/references/workflow.md",
        ".claude/agents/novel-creation-studio.md",
        ".claude/agents/interactive-story-host.md",
    ]
    missing_files = [name for name in required_files if not (WORKSPACE / name).exists()]
    checks.append(_health_check_item("creation_studio_files_exist", not missing_files, {"missing": missing_files}))

    global_skill_files = [
        GLOBAL_CLAUDE_SKILL_DIR / "SKILL.md",
        GLOBAL_CLAUDE_SKILL_DIR / "references" / "workflow.md",
        GLOBAL_CLAUDE_SKILL_DIR / "agents" / "openai.yaml",
    ]
    missing_global_skill = [str(path) for path in global_skill_files if not path.exists()]
    checks.append(_health_check_item(
        "global_claude_skill_exists",
        not missing_global_skill,
        {"skillDir": str(GLOBAL_CLAUDE_SKILL_DIR), "missing": missing_global_skill},
    ))

    novel_ok = False
    novel_detail = None
    if DB_PATH.exists():
        try:
            novels = _db_list_novels(limit=20)
            current = next((item for item in novels if item.get("id") == DEFAULT_NOVEL_ID), None)
            novel_ok = bool(current)
            novel_detail = current or {"defaultNovelId": DEFAULT_NOVEL_ID, "availableCount": len(novels)}
        except Exception as exc:
            novel_detail = str(exc)
    checks.append(_health_check_item("default_novel_available", novel_ok, novel_detail, severity="warning"))

    health = None
    if base:
        try:
            health = _request("GET", f"{base}/api/health", timeout=2)
            checks.append(_health_check_item("backend_health_endpoint", True, health))
        except Exception as exc:
            checks.append(_health_check_item("backend_health_endpoint", False, str(exc)))

    failed = [item for item in checks if not item["ok"] and item["severity"] == "error"]
    warnings = [item for item in checks if not item["ok"] and item["severity"] == "warning"]
    return {
        "ok": not failed,
        "warningCount": len(warnings),
        "failedCount": len(failed),
        "checks": checks,
        "recommendedAction": "可以开始自然创作会话。" if not failed else "先修复 failed checks，再进行生成或通宵任务。",
    }


def tool_bootstrap_session(args):
    timeout = int(args.get("timeoutSeconds", 45))
    backend = tool_start_backend({"mode": "headless", "timeoutSeconds": timeout})
    status = tool_status({})
    model_config = _compact_model_config(tool_model_config({"autoStart": False}))

    novel_id = _novel_id(args)
    novels = _db_list_novels(limit=int(args.get("novelLimit", 8)))
    current_novel = next((novel for novel in novels if novel.get("id") == novel_id), None)
    if not current_novel and novels:
        current_novel = novels[0]
        novel_id = current_novel.get("id") or novel_id

    chapters = _db_list_chapters(novel_id) if novel_id else []
    chapter_limit = int(args.get("chapterLimit", 12))
    response = {
        "ready": bool(status.get("running")),
        "mode": "pure_headless_mcp",
        "backend": backend,
        "status": status,
        "model": model_config,
        "currentNovel": current_novel,
        "chapters": chapters[:chapter_limit],
        "chapterCount": len(chapters),
        "workspace": str(WORKSPACE),
        "backendBundle": str(BACKEND_BUNDLE_DIR),
        "guiRequired": False,
        "nextClaudeAction": "继续自然对话：确认用户要读样稿、推进现有章节、沉淀设定/大纲，或在用户明确同意后生成正文。",
    }

    if args.get("includeStyleContext"):
        response["styleContext"] = tool_style_context({"novelId": novel_id})

    if args.get("sampleOrder") is not None:
        response["sample"] = tool_get_chapter_sample({
            "novelId": novel_id,
            "order": int(args.get("sampleOrder")),
            "sampleChars": int(args.get("sampleChars", 3500)),
        })

    return response


TOOLS = {
    "ai_novel_healthcheck": {
        "description": "Run a preflight check for the one-window novel workflow: MCP paths, headless backend bundle, database, creation-studio files, default novel, and optional backend health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "autoStart": {"type": "boolean", "default": False},
                "timeoutSeconds": {"type": "integer", "default": 45},
            },
        },
        "handler": tool_healthcheck,
    },
    "ai_novel_bootstrap_session": {
        "description": "Auto-start the pure headless AI Novel backend and return the current writing workspace, model config, novel, chapters, and optional sample for a Claude writing session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "novelLimit": {"type": "integer", "default": 8},
                "chapterLimit": {"type": "integer", "default": 12},
                "includeStyleContext": {"type": "boolean", "default": False},
                "sampleOrder": {"type": "integer"},
                "sampleChars": {"type": "integer", "default": 3500},
            },
        },
        "handler": tool_bootstrap_session,
    },
    "ai_novel_status": {
        "description": "Check whether local AI Novel Writing Assistant v2 backend is running and discover its current port.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "autoStart": {"type": "boolean", "default": False},
                "timeoutSeconds": {"type": "integer", "default": 45},
            },
        },
        "handler": tool_status,
    },
    "ai_novel_start_backend": {
        "description": "Start AI Novel Writing Assistant v2 local backend. Use headless mode to avoid opening the Electron UI when possible.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["headless", "desktop"], "default": "headless"},
                "port": {"type": "integer"},
                "timeoutSeconds": {"type": "integer", "default": 45},
            },
        },
        "handler": tool_start_backend,
    },
    "ai_novel_stop_backend": {
        "description": "Stop the headless AI Novel backend process started by this bridge.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": tool_stop_backend,
    },
    "ai_novel_model_config": {
        "description": "Show sanitized AI Novel model/provider config, current model selection, model routes, and structured fallback settings.",
        "inputSchema": {
            "type": "object",
            "properties": {"autoStart": {"type": "boolean", "default": True}},
        },
        "handler": tool_model_config,
    },
    "ai_novel_create_custom_provider": {
        "description": "Create an OpenAI-compatible custom model provider in AI Novel. API keys are accepted but never returned.",
        "inputSchema": {
            "type": "object",
            "required": ["name", "baseURL"],
            "properties": {
                "name": {"type": "string"},
                "baseURL": {"type": "string"},
                "key": {"type": "string"},
                "model": {"type": "string"},
                "imageModel": {"type": "string"},
                "isActive": {"type": "boolean", "default": True},
                "reasoningEnabled": {"type": "boolean", "default": True},
                "concurrencyLimit": {"type": "integer", "default": 1},
                "requestIntervalMs": {"type": "integer", "default": 0},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_create_custom_provider,
    },
    "ai_novel_update_provider_config": {
        "description": "Update a built-in or existing custom model provider config in AI Novel. API keys are accepted but never returned.",
        "inputSchema": {
            "type": "object",
            "required": ["provider"],
            "properties": {
                "provider": {"type": "string"},
                "displayName": {"type": "string"},
                "key": {"type": "string"},
                "model": {"type": "string"},
                "imageModel": {"type": "string"},
                "baseURL": {"type": "string"},
                "isActive": {"type": "boolean"},
                "reasoningEnabled": {"type": "boolean"},
                "concurrencyLimit": {"type": "integer"},
                "requestIntervalMs": {"type": "integer"},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_update_provider_config,
    },
    "ai_novel_set_current_model": {
        "description": "Set AI Novel's current default LLM provider/model for backend generation.",
        "inputSchema": {
            "type": "object",
            "required": ["provider", "model"],
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number", "default": 0.7},
                "maxTokens": {"type": "integer"},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_set_current_model,
    },
    "ai_novel_set_model_route": {
        "description": "Set an AI Novel model route for a task type such as writer/planner/repair.",
        "inputSchema": {
            "type": "object",
            "required": ["taskType", "provider", "model"],
            "properties": {
                "taskType": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "maxTokens": {"type": "integer"},
                "requestProtocol": {"type": "string", "enum": ["auto", "openai_compatible", "anthropic"]},
                "structuredResponseFormat": {"type": "string", "enum": ["auto", "json_schema", "json_object", "prompt_json"]},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_set_model_route,
    },
    "ai_novel_test_model": {
        "description": "Test AI Novel model connectivity and structured-output compatibility. API keys are accepted but never returned.",
        "inputSchema": {
            "type": "object",
            "required": ["provider"],
            "properties": {
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "key": {"type": "string"},
                "baseURL": {"type": "string"},
                "probeMode": {"type": "string", "enum": ["plain", "structured", "both"], "default": "both"},
                "timeoutSeconds": {"type": "integer", "default": 90},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_test_model,
    },
    "ai_novel_list_novels": {
        "description": "List novels from AI Novel Writing Assistant v2.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {"type": "integer", "default": 1},
                "limit": {"type": "integer", "default": 12},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_list_novels,
    },
    "ai_novel_list_chapters": {
        "description": "List chapters for a novel with lightweight metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {"novelId": {"type": "string"}, "offline": {"type": "boolean", "default": False}},
        },
        "handler": tool_list_chapters,
    },
    "ai_novel_get_chapter": {
        "description": "Get a lightweight chapter brief and content preview.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "order": {"type": "integer"},
                "previewChars": {"type": "integer", "default": 2200},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_get_chapter,
    },
    "ai_novel_get_chapter_sample": {
        "description": (
            "读取指定章节正文，生成 HTML 预览文件，在右侧 preview 面板显示，并弹出交互式审批选择框。\n\n"
            "【必须严格执行的交互式审阅流程】\n"
            "1. 调用 preview_start(name='novel-reader') 启动预览服务器\n"
            "2. 调用 preview_eval 执行 window.location.href = '/ch{N}.html' 在右侧显示\n"
            "3. 调用 AskUserQuestion 弹出选择框，选项：通过 / 不通过 / 其他\n"
            "4. 用户选择「通过」→ 调用 ai_novel_update_chapter_brief 设置 chapterStatus='completed'\n"
            "   用户选择「不通过」→ 记录修改意见，重新生成\n"
            "   用户选择「其他」→ 按用户指示处理\n\n"
            "禁止：跳过 AskUserQuestion；在对话里打印正文；跳过 preview 面板。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "order": {"type": "integer"},
                "sampleChars": {"type": "integer", "default": 6000},
            },
        },
        "handler": tool_get_chapter_sample,
    },
    "ai_novel_read_chapter_full": {
        "description": (
            "读取指定章节的完整正文，在右侧 preview 面板显示，并弹出交互式审批选择框。\n\n"
            "【必须严格执行的交互式审阅流程】\n"
            "1. 调用 preview_start(name='novel-reader') 启动预览服务器\n"
            "2. 调用 preview_eval 执行 window.location.href = '/ch{N}.html' 在右侧显示\n"
            "3. 调用 AskUserQuestion 弹出选择框，选项：通过 / 不通过 / 其他\n"
            "4. 用户选择「通过」→ 调用 ai_novel_update_chapter_brief 设置 chapterStatus='completed'\n"
            "   用户选择「不通过」→ 记录修改意见，重新生成\n"
            "   用户选择「其他」→ 按用户指示处理\n\n"
            "禁止：跳过 AskUserQuestion；在对话里打印正文；跳过 preview 面板。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "order": {"type": "integer"},
            },
        },
        "handler": tool_read_chapter_full,
    },
    "ai_novel_style_context": {
        "description": "Read active style profiles and character briefs from the local AI Novel database for style-aware writing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "styleLimit": {"type": "integer", "default": 5},
                "characterLimit": {"type": "integer", "default": 12},
            },
        },
        "handler": tool_style_context,
    },
    "ai_novel_production_status": {
        "description": "Read a read-only production status snapshot from AI Novel SQLite: asset stages, chapter progress, memory ledger counts, latest generation job, and workflow task state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "targetChapterCount": {"type": "integer"},
            },
        },
        "handler": tool_production_status,
    },
    "ai_novel_director_status": {
        "description": "Read a read-only auto-director runtime snapshot: latest auto-director task, runtime instance, recent events, steps, artifacts, and blocking reason.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "limit": {"type": "integer", "default": 12},
            },
        },
        "handler": tool_director_status,
    },
    "ai_novel_read_ledgers": {
        "description": "Read long-form memory ledgers from AI Novel SQLite: facts, consistency facts, payoff ledger, character resource ledger, timeline events/hooks/constraints, and chapter summaries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "beforeChapterOrder": {"type": "integer"},
                "limit": {"type": "integer", "default": 30},
            },
        },
        "handler": tool_read_ledgers,
    },
    "ai_novel_knowledge_list_documents": {
        "description": "List AI Novel knowledge documents with version, binding, book-analysis, and index status; read-only by default and works offline from SQLite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "status": {"type": "string", "enum": ["enabled", "disabled", "archived"]},
                "limit": {"type": "integer", "default": 20},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_knowledge_list_documents,
    },
    "ai_novel_knowledge_get_document": {
        "description": "Read an AI Novel knowledge document detail, versions, previews, and bindings.",
        "inputSchema": {
            "type": "object",
            "required": ["documentId"],
            "properties": {
                "documentId": {"type": "string"},
                "versionLimit": {"type": "integer", "default": 5},
                "previewChars": {"type": "integer", "default": 1200},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_knowledge_get_document,
    },
    "ai_novel_knowledge_create_document": {
        "description": "Create a local AI Novel knowledge document for private writing assets; queues indexing when RAG is enabled.",
        "inputSchema": {
            "type": "object",
            "required": ["fileName", "content"],
            "properties": {
                "title": {"type": "string"},
                "fileName": {"type": "string"},
                "content": {"type": "string"},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_knowledge_create_document,
    },
    "ai_novel_knowledge_create_version": {
        "description": "Append a new version to an existing AI Novel knowledge document.",
        "inputSchema": {
            "type": "object",
            "required": ["documentId", "content"],
            "properties": {
                "documentId": {"type": "string"},
                "fileName": {"type": "string"},
                "content": {"type": "string"},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_knowledge_create_version,
    },
    "ai_novel_knowledge_reindex_document": {
        "description": "Queue a rebuild of one AI Novel knowledge document's RAG index.",
        "inputSchema": {
            "type": "object",
            "required": ["documentId"],
            "properties": {
                "documentId": {"type": "string"},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_knowledge_reindex_document,
    },
    "ai_novel_knowledge_recall_test": {
        "description": "Test whether a knowledge document can recall relevant chunks for a query.",
        "inputSchema": {
            "type": "object",
            "required": ["documentId", "query"],
            "properties": {
                "documentId": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_knowledge_recall_test,
    },
    "ai_novel_book_analysis_list": {
        "description": "List book-analysis jobs/results used for studying reference novels and publishing insights back to knowledge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "status": {"type": "string", "enum": ["draft", "queued", "running", "succeeded", "failed", "cancelled", "archived"]},
                "documentId": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_book_analysis_list,
    },
    "ai_novel_book_analysis_get": {
        "description": "Read a book-analysis detail and section previews.",
        "inputSchema": {
            "type": "object",
            "required": ["analysisId"],
            "properties": {
                "analysisId": {"type": "string"},
                "previewChars": {"type": "integer", "default": 1200},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_book_analysis_get,
    },
    "ai_novel_book_analysis_create": {
        "description": "Create a book-analysis job from a knowledge document. Use for private competitor/reference study before publishing insights into a novel knowledge base.",
        "inputSchema": {
            "type": "object",
            "required": ["documentId"],
            "properties": {
                "documentId": {"type": "string"},
                "versionId": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "maxTokens": {"type": "integer"},
                "includeTimeline": {"type": "boolean", "default": False},
                "enabledSectionKeys": {"type": "array", "items": {"type": "string"}},
                "timeoutSeconds": {"type": "integer", "default": 90},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_book_analysis_create,
    },
    "ai_novel_book_analysis_publish": {
        "description": "Publish a completed book-analysis into the current novel's knowledge assets.",
        "inputSchema": {
            "type": "object",
            "required": ["analysisId"],
            "properties": {
                "analysisId": {"type": "string"},
                "novelId": {"type": "string"},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_book_analysis_publish,
    },
    "ai_novel_book_analysis_export": {
        "description": "Export a book-analysis as markdown or JSON preview.",
        "inputSchema": {
            "type": "object",
            "required": ["analysisId"],
            "properties": {
                "analysisId": {"type": "string"},
                "format": {"type": "string", "enum": ["markdown", "json"], "default": "markdown"},
                "previewChars": {"type": "integer", "default": 6000},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_book_analysis_export,
    },
    "ai_novel_style_list_profiles": {
        "description": "List style profiles with source, extraction, binding, and anti-AI counts; read-only and offline-capable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": "active"},
                "limit": {"type": "integer", "default": 20},
                "previewChars": {"type": "integer", "default": 800},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_style_list_profiles,
    },
    "ai_novel_style_get_profile": {
        "description": "Read style profile detail, rules, feature metadata, bindings, and anti-AI bindings.",
        "inputSchema": {
            "type": "object",
            "required": ["styleProfileId"],
            "properties": {
                "styleProfileId": {"type": "string"},
                "previewChars": {"type": "integer", "default": 1200},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_style_get_profile,
    },
    "ai_novel_style_list_bindings": {
        "description": "List style bindings for novel/chapter/task targets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "styleProfileId": {"type": "string"},
                "targetType": {"type": "string", "enum": ["novel", "chapter", "task"]},
                "targetId": {"type": "string"},
                "limit": {"type": "integer", "default": 30},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_style_list_bindings,
    },
    "ai_novel_style_bind": {
        "description": "Bind a style profile to a novel, chapter, or task target.",
        "inputSchema": {
            "type": "object",
            "required": ["styleProfileId", "targetType", "targetId"],
            "properties": {
                "styleProfileId": {"type": "string"},
                "targetType": {"type": "string", "enum": ["novel", "chapter", "task"]},
                "targetId": {"type": "string"},
                "priority": {"type": "integer", "default": 1},
                "weight": {"type": "number", "default": 1},
                "enabled": {"type": "boolean", "default": True},
                "timeoutSeconds": {"type": "integer", "default": 45},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_style_bind,
    },
    "ai_novel_style_create_from_text": {
        "description": "Create a style profile from sample text using AI Novel Style Engine.",
        "inputSchema": {
            "type": "object",
            "required": ["name", "sourceText"],
            "properties": {
                "name": {"type": "string"},
                "sourceText": {"type": "string"},
                "category": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "timeoutSeconds": {"type": "integer", "default": 120},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_style_create_from_text,
    },
    "ai_novel_style_create_from_brief": {
        "description": "Create a style profile from a natural-language style brief.",
        "inputSchema": {
            "type": "object",
            "required": ["brief"],
            "properties": {
                "brief": {"type": "string"},
                "name": {"type": "string"},
                "category": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "timeoutSeconds": {"type": "integer", "default": 90},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_style_create_from_brief,
    },
    "ai_novel_style_create_from_book_analysis": {
        "description": "Create a style profile from a completed book-analysis result.",
        "inputSchema": {
            "type": "object",
            "required": ["analysisId", "name"],
            "properties": {
                "analysisId": {"type": "string"},
                "bookAnalysisId": {"type": "string"},
                "name": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "timeoutSeconds": {"type": "integer", "default": 120},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_style_create_from_book_analysis,
    },
    "ai_novel_anti_ai_rules": {
        "description": "List anti-AI style rules and global baseline flags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 80},
                "offline": {"type": "boolean", "default": False},
            },
        },
        "handler": tool_anti_ai_rules,
    },
    "ai_novel_style_detect": {
        "description": "Check content against style profile and anti-AI rules.",
        "inputSchema": {
            "type": "object",
            "required": ["content"],
            "properties": {
                "content": {"type": "string"},
                "styleProfileId": {"type": "string"},
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "taskStyleProfileId": {"type": "string"},
                "previewAntiAiRuleIds": {"type": "array", "items": {"type": "string"}},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "timeoutSeconds": {"type": "integer", "default": 90},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_style_detect,
    },
    "ai_novel_style_rewrite": {
        "description": "Rewrite content through AI Novel Style Engine based on supplied style issues; use for repair, not Claude hand-writing.",
        "inputSchema": {
            "type": "object",
            "required": ["content", "issues"],
            "properties": {
                "content": {"type": "string"},
                "issues": {"type": "array", "items": {"type": "object"}},
                "styleProfileId": {"type": "string"},
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "taskStyleProfileId": {"type": "string"},
                "previewAntiAiRuleIds": {"type": "array", "items": {"type": "string"}},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "timeoutSeconds": {"type": "integer", "default": 120},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_style_rewrite,
    },
    "ai_novel_update_chapter_brief": {
        "description": "Update chapter planning fields such as expectation, taskSheet, sceneCards, mustAvoid, targetWordCount.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "order": {"type": "integer"},
                "title": {"type": "string"},
                "expectation": {"type": "string"},
                "taskSheet": {"type": "string"},
                "sceneCards": {"type": "string"},
                "mustAvoid": {"type": "string"},
                "targetWordCount": {"type": "integer"},
                "chapterStatus": {"type": "string"},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_update_chapter_brief,
    },
    "ai_novel_interactive_choice": {
        "description": "Record the user's game-like interactive choice into the chapter task sheet before generation.",
        "inputSchema": {
            "type": "object",
            "required": ["userChoice"],
            "properties": {
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "order": {"type": "integer"},
                "userChoice": {"type": "string"},
                "hostNote": {"type": "string"},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_interactive_choice,
    },
    "ai_novel_generate_chapter": {
        "description": "Generate one chapter through AI Novel Writing Assistant v2 in manual mode. Optionally append guidance first.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "chapterId": {"type": "string"},
                "order": {"type": "integer"},
                "guidance": {"type": "string"},
                "provider": {"type": "string"},
                "model": {"type": "string"},
                "temperature": {"type": "number"},
                "previousChaptersSummary": {"type": "array", "items": {"type": "string"}},
                "timeoutSeconds": {"type": "integer", "default": 240},
                "sampleChars": {"type": "integer", "default": 4500},
                "autoStart": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_generate_chapter,
    },
    "ai_novel_start_overnight_runner": {
        "description": "Start a background chapter-generation runner so writing can continue while the user is away.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "novelId": {"type": "string"},
                "startOrder": {"type": "integer"},
                "endOrder": {"type": "integer"},
                "maxChapters": {"type": "integer", "default": 1},
                "guidance": {"type": "string"},
                "delaySeconds": {"type": "number", "default": 0},
                "timeoutSeconds": {"type": "integer", "default": 600},
                "sampleChars": {"type": "integer", "default": 3500},
                "stopOnError": {"type": "boolean", "default": True},
            },
        },
        "handler": tool_start_overnight_runner,
    },
    "ai_novel_overnight_status": {
        "description": "Read the latest background overnight runner status and log tail.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "logPath": {"type": "string"},
                "tail": {"type": "integer", "default": 20},
            },
        },
        "handler": tool_overnight_status,
    },
    "show_novel_panel": {
        "description": (
            "在对话流里渲染小说创作状态面板，显示当前阶段、概念卡、材料库进度。\n\n"
            "【交互式小说创作工作流 — 全程纯自然语言，不用斜杠命令】\n"
            "每个节点都要：sidebar 展示内容 + AskUserQuestion 弹选择框\n\n"
            "1. 脑洞/路线：给出 2-4 条路线，AskUserQuestion 让用户选\n"
            "2. 角色设定：preview 面板显示人设卡，AskUserQuestion 确认/修改\n"
            "3. 大纲：preview 面板显示大纲，AskUserQuestion 逐卷确认\n"
            "4. 章节生成：ai_novel_read_chapter_full 生成 HTML → preview 显示 → AskUserQuestion 通过/不通过/其他\n"
            "5. 修改：用户选不通过时，讨论修改方向，再弹选择框确认\n\n"
            "技术：sidebar 用 preview_start + preview_eval；选择框用 AskUserQuestion。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "meta": {"ui": {"resourceUri": NOVEL_PANEL_VIEW_URI}},
        "handler": tool_show_novel_panel,
    },
}


CLI_USAGE = """Usage:
  python mcp-bridge/ai_novel_mcp.py --help
  python mcp-bridge/ai_novel_mcp.py list-tools [--json]
  python mcp-bridge/ai_novel_mcp.py healthcheck [--start]
  python mcp-bridge/ai_novel_mcp.py bootstrap [sampleOrder]
  python mcp-bridge/ai_novel_mcp.py status
  python mcp-bridge/ai_novel_mcp.py start [headless|desktop]
  python mcp-bridge/ai_novel_mcp.py stop
  python mcp-bridge/ai_novel_mcp.py sample <order>
  python mcp-bridge/ai_novel_mcp.py model-config
  python mcp-bridge/ai_novel_mcp.py set-current-model <provider> <model>
  python mcp-bridge/ai_novel_mcp.py overnight-start [json_file]
  python mcp-bridge/ai_novel_mcp.py overnight-status
  python mcp-bridge/ai_novel_mcp.py overnight-run <config_json>
  python mcp-bridge/ai_novel_mcp.py run-request [json_file]

No command starts the MCP stdio server for Claude/Codex hosts.
"""


def _list_cli_tools(as_json=False):
    rows = [
        {
            "name": name,
            "description": spec["description"].splitlines()[0],
        }
        for name, spec in TOOLS.items()
    ]
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    print(f"{len(rows)} MCP tools:")
    for row in rows:
        print(f"- {row['name']}: {row['description']}")


def handle(request):
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        return _result(request_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": "ai-novel-writing-assistant-v2", "version": "0.1.0"},
        })
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        tools = [
            {
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
            for name, spec in TOOLS.items()
        ]
        return _result(request_id, {"tools": tools})
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in TOOLS:
            return _error(request_id, -32602, f"Unknown tool: {name}")
        try:
            value = TOOLS[name]["handler"](args)
            # If tool returns renderMarkdown, send it as plain text (not JSON)
            # so Claude can render it as an artifact in the sidebar/canvas.
            if isinstance(value, dict) and "renderMarkdown" in value:
                return _result(request_id, _text_result(value["renderMarkdown"]))
            if isinstance(value, dict) and "artifact_markdown" in value:
                return _result(request_id, _text_result(value["artifact_markdown"]))
            return _result(request_id, _text_result(_json_text(value)))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return _result(request_id, _text_result(f"HTTP {exc.code}: {_clip(detail, 3000)}"))
        except Exception as exc:
            return _result(request_id, _text_result(f"ERROR: {exc}"))
    if method == "resources/list":
        return _result(request_id, {
            "resources": [
                {
                    "uri": NOVEL_PANEL_VIEW_URI,
                    "name": "小说创作状态面板",
                    "description": "展示当前项目阶段、概念卡和材料库进度。",
                    "mimeType": "text/html;profile=mcp-app",
                },
                {
                    "uri": CHAPTER_READER_URI,
                    "name": "章节阅读器",
                    "description": "在 sidebar 显示当前章节正文，供用户阅读审校。",
                    "mimeType": "text/html;profile=mcp-app",
                },
            ]
        })
    if method == "resources/read":
        params = request.get("params") or {}
        uri = params.get("uri", "")
        if uri == NOVEL_PANEL_VIEW_URI:
            return _result(request_id, {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/html;profile=mcp-app",
                        "text": NOVEL_PANEL_HTML,
                    }
                ]
            })
        if uri == CHAPTER_READER_URI:
            html = _CHAPTER_READER_CACHE.get("html") or "<html><body style='background:#0e0e10;color:#e8e6e3;font-family:sans-serif;padding:20px'><p>还没有章节内容。请先调用 get_chapter_sample。</p></body></html>"
            return _result(request_id, {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "text/html;profile=mcp-app",
                        "text": html,
                    }
                ]
            })
        return _error(request_id, -32602, f"Unknown resource: {uri}")
    return _error(request_id, -32601, f"Method not found: {method}")


def main():
    if len(sys.argv) > 1:
        run_cli(sys.argv[1:])
        return
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except Exception as exc:
            _write({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}})


def run_cli(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(CLI_USAGE)
        return
    command = argv[0]
    if command == "list-tools":
        _list_cli_tools(as_json="--json" in argv)
        return
    if command == "healthcheck":
        print(_json_text(tool_healthcheck({"autoStart": "--start" in argv})))
        return
    if command == "bootstrap":
        args = {}
        if len(argv) > 1:
            args["sampleOrder"] = int(argv[1])
        print(_json_text(tool_bootstrap_session(args)))
        return
    if command == "status":
        print(_json_text(tool_status({})))
        return
    if command == "start":
        args = {"mode": argv[1] if len(argv) > 1 else "headless"}
        print(_json_text(tool_start_backend(args)))
        return
    if command == "stop":
        print(_json_text(tool_stop_backend({})))
        return
    if command == "sample":
        if len(argv) < 2:
            raise RuntimeError("Usage: ai_novel_mcp.py sample <chapterOrder>")
        print(_json_text(tool_get_chapter_sample({"order": int(argv[1])})))
        return
    if command == "model-config":
        print(_json_text(tool_model_config({})))
        return
    if command == "set-current-model":
        if len(argv) < 3:
            raise RuntimeError("Usage: ai_novel_mcp.py set-current-model <provider> <model>")
        print(_json_text(tool_set_current_model({"provider": argv[1], "model": argv[2]})))
        return
    if command == "overnight-start":
        if len(argv) > 1:
            config = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        else:
            config = json.loads(sys.stdin.read())
        print(_json_text(tool_start_overnight_runner(config)))
        return
    if command == "overnight-status":
        print(_json_text(tool_overnight_status({})))
        return
    if command == "overnight-run":
        if len(argv) < 2:
            raise RuntimeError("Usage: ai_novel_mcp.py overnight-run <config_json>")
        config = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        def progress(event):
            print(json.dumps(event, ensure_ascii=False), flush=True)
        result = run_overnight_job(config, progress=progress)
        print(json.dumps({"event": "overnight_finished", "result": result}, ensure_ascii=False), flush=True)
        return
    if command == "run-request":
        if len(argv) > 1:
            text = Path(argv[1]).read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        request = _extract_bridge_request(text)
        action = request.get("action")
        if action == "interactive_choice":
            result = tool_interactive_choice(request)
        elif action == "update_chapter_brief":
            args = dict(request)
            args.update(request.get("fields") or {})
            result = tool_update_chapter_brief(args)
        elif action == "generate_chapter":
            result = tool_generate_chapter(request)
        elif action == "start_overnight_runner":
            result = tool_start_overnight_runner(request)
        else:
            raise RuntimeError(f"Unsupported bridge request action: {action}")
        print(_json_text(result))
        return
    raise RuntimeError(CLI_USAGE)


def _extract_bridge_request(text):
    text = text.strip()
    if not text:
        raise RuntimeError("Empty bridge request.")
    if "AI_NOVEL_BRIDGE_REQUEST" in text:
        match = re.search(r"\{[\s\S]*?\"type\"\s*:\s*\"AI_NOVEL_BRIDGE_REQUEST\"[\s\S]*?\}", text)
        if not match:
            raise RuntimeError("Found marker but could not parse JSON object.")
        text = match.group(0)
    data = json.loads(text)
    if data.get("type") != "AI_NOVEL_BRIDGE_REQUEST":
        raise RuntimeError("Bridge request type must be AI_NOVEL_BRIDGE_REQUEST.")
    return data


if __name__ == "__main__":
    main()
