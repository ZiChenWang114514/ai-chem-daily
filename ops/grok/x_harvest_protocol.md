# X 采集协议（Grok 检索）

X 只走 Grok 检索。日报流水线不再调用官方 X API，也不再读取 Bearer Token。

## 顺序

1. Grok 按本协议检索公开帖，写入 `work/grok-x/<date>.json`。
2. `python backend/x_harvest.py ingest work/grok-x/<date>.json --date <date>` 规范化并写入 `work/source-cache/x/<date>.json.gz`。
3. `ops/run_local_pipeline.ps1` 采集 AI Voices 时只读该缓存；没有缓存则 X 记为失败，研究博客继续。

查询清单由 `python backend/x_harvest.py queries --date <date>` 根据 `config/watchlists.json` 生成。

## 窗口

与其他来源相同：周一向前 4 天，其余日期向前 3 天，结束日为运行日。Grok 检索的 `until:` 为结束日的次日（不含）。

## 工具

只使用 Grok 的 `x_keyword_search`、`x_semantic_search`、`x_thread_fetch`。

- `x_keyword_search`：执行 `queries` 列出的每一条，账号查询 `mode` 为 `Latest`，主题查询 `mode` 为 `Top`，`limit` 为 10。
- `x_semantic_search`：可选补漏，查询研究发布、形式化证明、AI×化学/生物，时间与窗口一致。
- `x_thread_fetch`：仅当关键词结果被截断、需要补全文时使用。
- 不要调用 `api.x.com`，不要使用 `X_BEARER_TOKEN`。

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

缓存不存在时，采集记录 `X: RuntimeError: 未找到 Grok X 检索缓存`。不要回退到官方 API。
