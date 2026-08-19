# AIxDaily

AIxDaily 在 Windows 本地完成每日采集与 Codex 审阅，使用 GitHub Pages 发布。AI × Chem、AI × Bio、AI × Math、AI Voices 与 Engineering 五个频道均已启用。

## 每日流程

1. Codex 已安排任务每天北京时间 07:00 启动一次完整流程。
2. 采集前 Codex 先写下 Grok 访问票，再启动本机 `grok.exe`。Grok 按 `ops/grok/x_harvest_protocol.md` 检索 X，把结果放进 `work/source-cache/x/`。没有缓存时，AI Voices 跳过 X，研究博客照常采集。
3. 然后依次收集五个频道的当日内容。arXiv 与 bioRxiv 每天只采集一次，Chem、Bio、Math 共用本地 source cache；同一主机的请求保持间隔。
4. 收集完成后，依次进行五套独立的 `gpt-5.6-terra` / `high` 审阅，并更新各频道日报。
5. 对失败频道立即再执行一次采集与审阅，随后生成综合日报、运行测试并发布 GitHub Pages。
6. Pages 部署完成后只创建一个五频道日报 Issue，并指派给 `ZiChenWang114514`。GitHub 根据账号通知设置发送邮件。

本地文件型已安排任务需要电脑保持开机，并保持 ChatGPT/Codex 桌面应用运行。

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
- `public/library/`：本机收藏。按频道归位，支持笔记、导出导入；不经过服务器

审阅入选条目时会同时写入 `abstract_zh`。页面上的「查看摘要」可在中文译文和原文之间切换。

任务连接页位于 `public/task/index.html`，线上地址是 <https://zichenwang114514.github.io/ai-x-daily/task/>。

## 工程目录

```text
config/channels.json           频道登记与公开接口路径
config/watchlists.json         X、研究博客、OpenReview 与 GitHub 清单
backend/aix_pipeline.py        五频道采集、规范化、筛选与本地原始记录
backend/x_harvest.py           生成 Grok X 查询并写入 source-cache
backend/apply_channel_curation.py 导入单频道模型审阅结果
backend/publish_daily.py       生成综合日报与通知内容
backend/hub_publish.py         生成公开接口、任务说明和活动数据
backend/import_intake.py       导入人工提交的结构化资料
backend/fill_abstract_zh.py    把已准备好的中文摘要写回已发布 JSON
ops/run_local_pipeline.ps1     本地采集、先拜访 Grok、再 Codex 复核与发布
ops/grok/                      Codex 访问 Grok 的 X 检索协议与 visit prompt
ops/codex/                     学术复核 Prompt 与结构化输出 Schema
AGENTS.md                      Grok 在本仓库被访问时的执行合同
public/library/                本机收藏页，按频道归位，笔记保存在浏览器
public/assets/collection.js    收藏、笔记与摘要语言偏好
public/                        GitHub Pages 页面、接口与已发布数据
.github/workflows/intake.yml   人工资料导入
.github/workflows/deploy.yml   Pages 部署
```

## 本地运行

```powershell
pwsh -NoProfile -File ops/run_local_pipeline.ps1 -SkipPush -SkipPull
```

打开 `http://localhost:8000` 查看网站。手动执行完整流程时运行：

```powershell
pwsh -NoProfile -File ops/run_local_pipeline.ps1
```

只测试内容、不提交 GitHub 时运行：

```powershell
pwsh -NoProfile -File ops/run_local_pipeline.ps1 -SkipPush -SkipPull
```

## Codex 已安排任务

任务名称为 `AIX每日精读`，每天北京时间 07:00 运行一次。它先拜访本机 Grok 检索 X，再完成五频道采集、五套审阅和统一发布。运行记录、Codex 结构化结果、本地原始资料与共享缓存分别保存在 `work/local-pipeline/`、`work/raw/` 与 `work/source-cache/`，这些目录不会提交到 GitHub。电脑需保持开机，并同时能运行 Codex 与 `grok.exe`。

本地参数位于被 Git 忽略的 `config/local.settings.psd1`。OpenReview 账号位于 `config/local.secrets.psd1`。可提交的参考文件分别是 `config/local.settings.example.psd1` 与 `config/local.secrets.example.psd1`。

## 数据源

- AI × Chem：arXiv、bioRxiv、ChemRxiv
- AI × Bio：arXiv、bioRxiv、medRxiv、Europe PMC
- AI × Math：arXiv、OpenReview
- AI Voices：Grok X 检索、官方研究博客
- Engineering：GitHub Releases 与项目官方发布信息

X 由 Codex 每天访问 Grok 完成：先写 `work/grok-x/<date>.request.json`，再由 Grok 检索并写入本地缓存。不再使用官方 X API 或 Bearer Token。OpenReview 的受限查询需要账号。来源不可用时，日报会显示该来源的错误，其他来源继续处理。

## 邮件

本地程序推送日报后，Pages 工作流创建当天唯一的 `daily-digest` Issue 并指派给你的 GitHub 账号。仓库已经订阅；请在 GitHub 的通知设置中把该仓库的邮件发送地址设为 `wangzc@stu.pku.edu.cn`。HTML 和 Markdown 邮件内容仍会生成到 `public/email/`。

## 内容说明

日报以公开元数据和公开网页为依据。自动筛选与模型复核可能遗漏有价值的研究，预印本也未经同行评议，研究结论请以原文和后续正式版本为准。
