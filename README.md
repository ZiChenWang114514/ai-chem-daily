# AIX Daily · 每日智能研究集散中心

AIX Daily 使用 GitHub Pages 发布，使用 GitHub Actions 采集、导入和部署。当前频道是 AI × Chem，数据结构已经预留 AI × Bio、AI × Math、研究者动态与工程更新。

## 每日流程

1. 北京时间 08:12，GitHub Actions 读取 arXiv、bioRxiv 与 ChemRxiv 的公开元数据，生成候选列表和基础日报。
2. 原始记录压缩为短期 Actions 工件。本地轻量任务在电脑可用时把新文件复制到 `zeus_ts:/data3/zcwang/daily-intelligence-hub/raw/`，完成后清理临时目录。
3. 北京时间 09:15，ChatGPT 网页版已安排任务读取公开任务接口和候选资料，完成摘要复核。
4. 网页版任务通过已连接的 GitHub 应用创建或更新 `scheduled-intake` Issue。导入工作流读取其中的 JSON，将资料写入频道归档并更新网站。
5. GitHub Pages 部署公开页面、版本化 JSON 接口和年度活动日历。GitHub Issue 与 ChatGPT 通知共同提供每日提醒。

网页版任务不需要访问 Windows 文件夹，也不需要保存 GitHub Token。ChatGPT 目前不提供 scheduled-task webhook，因此仓库 Issue 是资料写入方式。

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
backend/daily_digest.py        AI × Chem 采集、筛选、邮件与原始快照
backend/hub_publish.py         生成公开接口、任务说明和活动数据
backend/import_intake.py       导入网页版已安排任务提交的资料
backend/apply_curation.py      将 AI × Chem 复核结果写入日报
ops/sync_raw_to_zeus.ps1       把短期 Actions 原始资料复制到 Zeus
public/                        GitHub Pages 页面、接口与已发布数据
.github/workflows/daily.yml    每日采集
.github/workflows/intake.yml   已安排任务资料导入
.github/workflows/deploy.yml   Pages 部署
```

## 本地运行

```powershell
python backend/daily_digest.py --site-root public --raw-root work/raw --days 3 --limit 16
python backend/hub_publish.py --site-root public
python -m unittest discover -s tests -v
python -m http.server 8000 --directory public
```

打开 `http://localhost:8000` 查看网站。同步短期原始资料时运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ops/sync_raw_to_zeus.ps1
```

## 新增频道

在 `config/channels.json` 增加频道说明，并让采集器或网页版任务按照 intake schema 提交 `digest` 资料即可。通用导入程序会生成 `public/data/channels/<channel>/latest.json` 与日期归档，随后公开接口和活动日历自动纳入该频道。

## 邮件

GitHub Issue 可以通过 GitHub 通知免费发送邮件。若需要完整 HTML 邮件，可在仓库 Actions Secrets 中配置 SMTP 主机、端口、用户名、授权码与发件地址，并用仓库变量 `MAIL_TO` 设置收件地址。凭据不写入代码或 Issue。

## 内容说明

日报以公开元数据和公开网页为依据。自动筛选与模型复核可能遗漏有价值的研究，预印本也未经同行评议，研究结论请以原文和后续正式版本为准。
