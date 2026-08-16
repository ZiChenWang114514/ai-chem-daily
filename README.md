# AIX Daily · 每日智能研究集散中心

AIX Daily 在 Windows 本地完成每日采集与 Codex 审阅，使用 GitHub Pages 发布。AI × Chem、AI × Bio、AI × Math、AI Voices 与 Engineering 五个频道均已启用。

## 每日流程

1. 北京时间 01:00 至 05:00，Windows 计划任务依次处理五个频道，全程串行。
2. arXiv 与 bioRxiv 每天只采集一次，Chem、Bio、Math 共用本地 source cache；同一主机的请求保持间隔。
3. 本机 Codex CLI 每个频道都显式使用 `gpt-5.6-terra` 和 `high` 推理强度，按独立评分标准审阅完整候选集。
4. 06:15 检查五频道状态；07:15 只再次处理失败频道；07:45 生成综合日报、测试网站并发布。
5. GitHub Pages 部署完成后只创建一个五频道日报 Issue，并指派给 `ZiChenWang114514`。GitHub 根据账号通知设置发送邮件。

电脑在 01:00 关机时，Windows 会在下次开机并登录后执行当天任务。屏幕锁定不影响已经登录的计划任务。

## 公开接口

- `public/api/v1/manifest.json`：频道、版本与端点清单
- `public/api/v1/status.json`：当天更新状态
- `public/api/v1/activity.json`：日历热力图数据
- `public/api/v1/tasks/daily-brief.json`：网页版任务的完整读写说明
- `public/api/v1/schemas/intake.json`：资料提交格式
- `public/data/candidates/latest.json`：AI × Chem 当日候选
- `public/data/latest.json`：AI × Chem 最近一期
- `public/data/channels/<channel>/latest.json`：各频道最近一期
- `public/data/channels/<channel>/candidates/latest.json`：各频道候选集
- `public/data/channels/<channel>/archive/`：各频道日期归档
- `public/data/daily/latest.json`：五频道综合日报

任务连接页位于 `public/task/index.html`，线上地址是 <https://zichenwang114514.github.io/ai-chem-daily/task/>。

## 工程目录

```text
config/channels.json           频道登记与公开接口路径
config/watchlists.json         X、研究博客、OpenReview 与 GitHub 清单
backend/aix_pipeline.py        五频道采集、规范化、筛选与本地原始记录
backend/apply_channel_curation.py 导入单频道模型审阅结果
backend/publish_daily.py       生成综合日报与通知内容
backend/hub_publish.py         生成公开接口、任务说明和活动数据
backend/import_intake.py       导入人工提交的结构化资料
ops/run_local_pipeline.ps1     本地采集、Codex 复核、测试与发布
ops/install_local_task.ps1     安装 Windows 每日计划任务
ops/codex/                     学术复核 Prompt 与结构化输出 Schema
public/                        GitHub Pages 页面、接口与已发布数据
.github/workflows/intake.yml   人工资料导入
.github/workflows/deploy.yml   Pages 部署
```

## 本地运行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/run_local_pipeline.ps1 -RunNow -SkipPush -SkipPull
```

打开 `http://localhost:8000` 查看网站。手动执行完整流程时运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/run_local_pipeline.ps1 -RunNow
```

只测试内容、不提交 GitHub 时运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/run_local_pipeline.ps1 -RunNow -SkipPush -SkipPull
```

## Windows 定时运行

安装或更新每天 01:00 的本地任务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/install_local_task.ps1 -At 01:00
```

任务名称为 `AIX Daily Local Academic Pipeline`。运行记录、Codex 结构化结果、本地原始资料与共享缓存分别保存在 `work/local-pipeline/`、`work/raw/` 与 `work/source-cache/`，这些目录不会提交到 GitHub。

本地参数位于被 Git 忽略的 `config/local.settings.psd1`。X Bearer Token 与 OpenReview 账号位于 `config/local.secrets.psd1`。可提交的参考文件分别是 `config/local.settings.example.psd1` 与 `config/local.secrets.example.psd1`。

## 数据源

- AI × Chem：arXiv、bioRxiv、ChemRxiv
- AI × Bio：arXiv、bioRxiv、medRxiv、Europe PMC
- AI × Math：arXiv、OpenReview
- AI Voices：X Recent Search、官方研究博客
- Engineering：GitHub Releases 与项目官方发布信息

X Recent Search 需要开发者项目具备 API 额度；OpenReview 的受限查询需要账号。来源不可用时，日报会显示该来源的 HTTP 状态，其他来源继续处理。

## 邮件

本地程序推送日报后，Pages 工作流创建当天唯一的 `daily-digest` Issue 并指派给你的 GitHub 账号。仓库已经订阅；请在 GitHub 的通知设置中把该仓库的邮件发送地址设为 `wangzc@stu.pku.edu.cn`。HTML 和 Markdown 邮件内容仍会生成到 `public/email/`。

## 内容说明

日报以公开元数据和公开网页为依据。自动筛选与模型复核可能遗漏有价值的研究，预印本也未经同行评议，研究结论请以原文和后续正式版本为准。
