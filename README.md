# AIX Daily · 每日智能研究集散中心

AIX Daily 在 Windows 本地完成每日采集与 Codex 学术复核，使用 GitHub Pages 发布。当前频道是 AI × Chem，数据结构已经预留 AI × Bio、AI × Math、研究者动态与工程更新。

## 每日流程

1. 北京时间 08:00，Windows 计划任务运行 `ops/run_local_pipeline.ps1`。
2. Python 读取 arXiv、bioRxiv 与 ChemRxiv 公开元数据，在本地保存压缩原始记录，生成当天全部候选。
3. 本机 Codex CLI 使用 `gpt-5.6-sol` 和高推理强度逐篇复核候选，输出 10 至 16 篇中文精选。
4. 固定程序导入精选结果、重建网站与邮件内容、运行测试，并把生成的数据提交到 GitHub。
5. GitHub Pages 部署完成后创建当日日报 Issue 并指派给 `ZiChenWang114514`。GitHub 根据账号通知设置发送邮件。

电脑在 08:00 关机时，Windows 会在下次开机并登录后补做任务。屏幕锁定不影响已经登录的计划任务。

## 公开接口

- `public/api/v1/manifest.json`：频道、版本与端点清单
- `public/api/v1/status.json`：当天更新状态
- `public/api/v1/activity.json`：日历热力图数据
- `public/api/v1/tasks/daily-brief.json`：网页版任务的完整读写说明
- `public/api/v1/schemas/intake.json`：资料提交格式
- `public/data/candidates/latest.json`：AI × Chem 当日候选
- `public/data/latest.json`：AI × Chem 最近一期

任务连接页位于 `public/task/index.html`，线上地址是 <https://zichenwang114514.github.io/ai-chem-daily/task/>。

## 工程目录

```text
config/channels.json           频道登记与数据源规划
backend/daily_digest.py        AI × Chem 采集、筛选、通知内容与原始快照
backend/hub_publish.py         生成公开接口、任务说明和活动数据
backend/import_intake.py       导入人工提交的结构化资料
backend/apply_curation.py      将 AI × Chem 复核结果写入日报
ops/run_local_pipeline.ps1     本地采集、Codex 复核、测试与发布
ops/install_local_task.ps1     安装 Windows 每日计划任务
ops/codex/                     学术复核 Prompt 与结构化输出 Schema
public/                        GitHub Pages 页面、接口与已发布数据
.github/workflows/intake.yml   人工资料导入
.github/workflows/deploy.yml   Pages 部署
```

## 本地运行

```powershell
python backend/daily_digest.py --site-root public --raw-root work/raw --days 3 --limit 16
python backend/hub_publish.py --site-root public
python -m unittest discover -s tests -v
python -m http.server 8000 --directory public
```

打开 `http://localhost:8000` 查看网站。手动执行完整流程时运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/run_local_pipeline.ps1
```

只测试内容、不提交 GitHub 时运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/run_local_pipeline.ps1 -SkipPush -SkipPull
```

## Windows 定时运行

安装或更新每天 08:00 的本地任务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/install_local_task.ps1 -At 08:00
```

任务名称为 `AIX Daily Local Academic Pipeline`。运行记录、Codex 结构化结果和本地原始资料分别保存在 `work/local-pipeline/` 与 `work/raw/`，这些目录不会提交到 GitHub。

本地参数位于被 Git 忽略的 `config/local.settings.psd1`。可提交的参考文件是 `config/local.settings.example.psd1`。

## 新增频道

在 `config/channels.json` 增加频道说明，并为新频道增加本地采集器与 Codex Prompt。通用数据结构会生成 `public/data/channels/<channel>/latest.json` 与日期归档，随后公开接口和活动日历自动纳入该频道。

## 邮件

本地程序推送日报后，Pages 工作流创建当天唯一的 `daily-digest` Issue 并指派给你的 GitHub 账号。仓库已经订阅；请在 GitHub 的通知设置中把该仓库的邮件发送地址设为 `wangzc@stu.pku.edu.cn`。HTML 和 Markdown 邮件内容仍会生成到 `public/email/`。

## 内容说明

日报以公开元数据和公开网页为依据。自动筛选与模型复核可能遗漏有价值的研究，预印本也未经同行评议，研究结论请以原文和后续正式版本为准。
