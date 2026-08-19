# 每日智能研究简报任务

每天北京时间 07:00，由 Codex 已安排任务在本机启动一次完整流程：

1. Codex 写下访问票并启动本机 Grok；Grok 检索 X 并写入 source-cache。
2. 依次收集 AI × Chem、AI × Bio、AI × Math、AI Voices 和 Engineering，共享 arXiv、bioRxiv 缓存，不并发采集频道。
3. 采集完成后，本地 Codex CLI 固定使用 `gpt-5.6-terra` 与 `high`，依次生成五频道结构化精选。
4. 失败频道立即再执行一次，随后生成综合日报、运行测试并发布网站。
5. GitHub Pages 部署后创建当天唯一的综合日报 Issue，由 GitHub 通知发送邮件。

运行状态：https://zichenwang114514.github.io/ai-x-daily/api/v1/status.json
