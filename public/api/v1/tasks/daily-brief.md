# 每日智能研究简报任务

每天北京时间 01:00，由 Windows 计划任务串行执行以下工作：

1. 01:00 至 05:00 依次处理 AI × Chem、AI × Bio、AI × Math、AI Voices 和 Engineering。
2. 共享 arXiv、bioRxiv 缓存，各频道之间不并发。
3. 本地 Codex CLI 固定使用 `gpt-5.6-terra` 与 `high`，输出符合 schema 的结构化精选。
4. 07:15 只再次处理失败频道；07:45 生成综合日报并完成最终发布。
5. GitHub Pages 部署后创建一个综合日报 Issue，由 GitHub 通知发送邮件。

运行状态：https://zichenwang114514.github.io/ai-chem-daily/api/v1/status.json
