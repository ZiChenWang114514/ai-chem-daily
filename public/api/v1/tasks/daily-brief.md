# 每日智能研究简报任务

每天北京时间 08:00，由 Windows 计划任务执行以下工作：

1. `ops/run_local_pipeline.ps1` 采集公开元数据并生成全部候选。
2. 本地 Codex CLI 读取每一篇候选，输出符合 schema 的结构化精选。
3. `backend/apply_curation.py` 导入中文概述、关注理由、分类、标签和分数。
4. 测试通过后提交到 `ZiChenWang114514/ai-chem-daily`，GitHub Pages 自动部署。
5. Pages 工作流创建当日日报 Issue，GitHub 根据账号通知设置发送邮件。

运行状态：https://zichenwang114514.github.io/ai-chem-daily/api/v1/status.json
