# X 采集协议（Codex 访问 Grok）

X 只走 Grok 检索。日报流水线不调用官方 X API，不读取 Bearer Token。

方法：Codex 不会搜 X。它每天先在仓库里放下访问票，再启动本机 `grok.exe`。Grok 读票、检索、把规范化结果放回 `work/source-cache/x/`。Codex 回来只读这份缓存，继续五频道审阅和发布。

也可以在本仓库打开 Grok TUI，直接说「今日 X」或「Codex 来访」；效果相同。

## 每日顺序

1. Codex 运行 `ops/run_local_pipeline.ps1`。
2. 脚本执行 `python backend/x_harvest.py request --date <date>`，写下 `work/grok-x/<date>.request.json`。
3. 若当日缓存已在，跳过拜访。
4. 否则启动：

```powershell
grok.exe --cwd <repo> --prompt-file ops/grok/daily_visit_prompt.md --always-approve --permission-mode bypassPermissions --max-turns 48
```

5. Grok 按 `ops/grok/daily_visit_prompt.md` 检索，写入 `work/grok-x/<date>.json`，再 ingest 到 `work/source-cache/x/<date>.json.gz`，最后写 `work/grok-x/<date>.done.json`。
6. Codex 采集 AI Voices 时只读该缓存；没有缓存则 X 记失败，研究博客继续。
7. Codex 完成五套审阅、综合日报、测试与推送。Grok 不审阅、不改 `public/`、不 commit、不 push。

## 窗口

与其他来源相同：周一向前 4 天，其余日期向前 3 天，结束日为运行日。Grok 检索的 `until:` 为结束日的次日（不含）。日期以 Asia/Shanghai 为准。

## 工具

只使用 Grok 的 `x_keyword_search`、`x_semantic_search`、`x_thread_fetch`。

- `x_keyword_search`：执行请求票或 `queries` 列出的每一条。账号查询 `mode` 为 `Latest`，主题查询 `mode` 为 `Top`，`limit` 为 10。
- `x_semantic_search`：可选补漏，查询研究发布、形式化证明、AI×化学/生物，时间与窗口一致。
- `x_thread_fetch`：仅当关键词结果被截断、需要补全文时使用。
- 不要调用 `api.x.com`，不要使用 `X_BEARER_TOKEN`。

查询清单也可由 `python backend/x_harvest.py queries --date <date>` 生成。

## 写入

`work/grok-x/<date>.json` 至少包含：

```json
{
  "schema_version": "1.0",
  "source": "grok.x.search",
  "date": "YYYY-MM-DD",
  "window": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "items": [
    {
      "id": "帖子数字 ID",
      "username": "handle",
      "name": "显示名",
      "text": "原文",
      "created_at": "ISO 时间",
      "lang": "en",
      "url": "https://x.com/handle/status/ID",
      "query_kind": "accounts",
      "metrics": {"like_count": 0, "repost_count": 0, "reply_count": 0, "quote_count": 0}
    }
  ]
}
```

同一帖子只保留一条。转发、空文本、窗口外帖子在 ingest 时丢弃。

## 失败

缓存不存在时，采集记录 `X: RuntimeError: 未找到 Grok X 检索缓存`。不要回退到官方 API。本机没有 `grok.exe` 时，把访问票留在 `work/grok-x/`，改在 Grok TUI 里执行同一份 visit prompt。
