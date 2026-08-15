# Zeus raw-data layout

Raw snapshots are private and live under:

```text
/data3/zcwang/daily-intelligence-hub/raw/
  aixchem/YYYY/MM/YYYY-MM-DD.jsonl.gz
  aixchem/YYYY/MM/YYYY-MM-DD.manifest.json
  aixbio/YYYY/MM/...
  aixmath/YYYY/MM/...
  aivoices/YYYY/MM/...
  engineering/YYYY/MM/...
```

Each compressed JSON Lines file has a neighboring manifest with its channel, collection window, record count, source counts, and byte size. The primary collector is `aix-daily-raw.timer` on Zeus and runs every day at 08:25 Asia/Shanghai. Windows synchronization remains available for manual use.

GitHub Actions keeps raw artifacts for 14 days so a temporarily offline Windows or Zeus host can synchronize later. Raw snapshots are never published by GitHub Pages and are never committed to Git.
