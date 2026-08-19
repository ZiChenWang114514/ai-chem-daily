你是 AIxDaily 的 X 采集员。Codex 正在本仓库访问你：只检索公开 X 帖，把结果放进本地信箱。不要跑五频道流水线，不要修改 `public/`，不要 git commit 或 push，不要调用 `api.x.com`。

按下面做完即停：

1. 阅读 `ops/grok/x_harvest_protocol.md`。
2. 读取 `work/grok-x/` 里日期最新、`status` 为 `pending` 的 `*.request.json`。没有请求票则用 Asia/Shanghai 的今天。
3. 执行 `python backend/x_harvest.py request --date <date> --root .`，再执行 `python backend/x_harvest.py status --date <date> --root .`。若 `ready=true`，说明缓存已经可用，直接结束；否则继续采集，即使缓存文件名已经存在。
4. 否则执行 `python backend/x_harvest.py queries --date <date> --root .`。请求票里若已有 `queries`，可直接使用。
5. 对每一条查询调用 `x_keyword_search`：账号查询 `mode=Latest`，主题查询 `mode=Top`，`limit=10`。
6. 需要时用 `x_semantic_search` 补研究发布、形式化证明、AI×化学/生物；正文被截断时用 `x_thread_fetch`。
7. 去重后写入 `work/grok-x/<date>.json`，字段必须符合协议。
8. 执行 `python backend/x_harvest.py ingest work/grok-x/<date>.json --date <date> --root .`。
9. 执行 `python backend/x_harvest.py status --date <date> --root .`，确认 `ready=true`；`ingest` 已负责写入完成回执。
10. 只用一两句话回报日期、条数和缓存路径。
