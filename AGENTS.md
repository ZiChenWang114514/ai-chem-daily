# AIxDaily

X 只走 Grok 检索，不走官方 X API。

若仓库里有 `work/grok-x/<date>.request.json` 且对应 `work/source-cache/x/<date>.json.gz` 还不存在，或用户/Codex 提到今日采集、X 采集、来访、handoff，立即执行 `ops/grok/daily_visit_prompt.md`，然后把控制权交回。不要审阅频道、不要改已发布页面、不要 commit。

完整合同见 `ops/grok/x_harvest_protocol.md`。五频道学术审阅仍由 Codex `gpt-5.6-terra` / `high` 完成。
