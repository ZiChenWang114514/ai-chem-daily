# AI × Chem 每日预印本精选

一个以 GitHub Pages 发布、由 GitHub Actions 每日更新的 AI 与化学交叉领域预印本日报。

## 工作方式

- 数据程序每天读取 arXiv、bioRxiv 与 ChemRxiv 的公开元数据。
- 全部新记录先经过 AI 与化学双重相关性筛选，并结合基准、数据、实验验证等信号计算候选分数。
- GitHub Actions 生成可独立发布的基础日报；ChatGPT 已安排任务读取候选摘要，进一步核查相关性、排序和中文说明。
- 结果写入 `public/data/latest.json` 和按日期保存的归档 JSON，随后部署到 GitHub Pages。
- 每期创建一条分配给仓库所有者的 GitHub Issue，作为免费邮件提醒。可另行配置 SMTP Secrets，发送完整 HTML 邮件。

## 目录

```text
backend/daily_digest.py       数据采集、评分、摘要整理、归档与邮件生成
backend/apply_curation.py     将复核后的选择与中文说明写入日报
public/                       GitHub Pages 静态前端与已发布数据
tests/test_digest.py          生成结果检查
.github/workflows/daily.yml   每日任务、部署与通知
```

## 本地运行

```powershell
python backend/daily_digest.py --site-root public --days 3 --limit 16
python -m unittest discover -s tests -v
python -m http.server 8000 --directory public
```

打开 `http://localhost:8000` 查看网站。

## 每日时间

GitHub Actions 计划在北京时间每天 08:12 运行。GitHub 的计划工作流可能出现几分钟延迟。周一会自动扩大日期范围，以包含周末记录。

ChatGPT 已安排任务随后读取 `public/data/candidates/latest.json`，完成摘要复核并通过 `backend/apply_curation.py` 更新当日内容；审核后的提交会触发独立部署工作流。

## 邮件

默认通知由 GitHub Issue 发送，需在 GitHub 通知设置中启用邮件。直接发送 HTML 邮件时，请在仓库 Actions Secrets 中配置：

- `SMTP_HOST`
- `SMTP_PORT`，常见值为 `465` 或 `587`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`，应使用邮箱服务生成的授权码
- `MAIL_FROM`

收件地址通过仓库变量 `MAIL_TO` 设置。任何密码或授权码都不应写入代码、Issue 或聊天消息。

## 方法说明

日报以公开元数据为依据，自动筛选与模型复核都可能遗漏有价值的研究。所有预印本均未经同行评议，研究结论应以原文与后续正式版本为准。
