# AIxDaily

X 只走 Grok 检索，不走官方 X API。

## Codex

Codex 不执行 `ops/grok/daily_visit_prompt.md`，也不直接检索 X。Codex 只运行 `ops/run_local_pipeline.ps1`；该脚本负责写访问票、启动 Grok、读取完成缓存并继续五频道审阅与发布。

## Grok

仅当当前执行者是 Grok，且仓库里有 `work/grok-x/<date>.request.json`、对应缓存尚未就绪时，才执行 `ops/grok/daily_visit_prompt.md`。Grok 完成 X 采集后结束，不审阅频道、不修改 `public/`、不 commit 或 push。

完整合同见 `ops/grok/x_harvest_protocol.md`。五频道学术审阅仍由 Codex `gpt-5.6-terra` / `high` 完成。
