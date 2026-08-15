#!/usr/bin/env python3
"""Apply a reviewed curation JSON to the latest digest and rebuild email assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from daily_digest import clean_text, load_json, render_email, write_json


ALLOWED_CATEGORIES = {"方法与模型", "分子与药物发现", "结构与生物", "材料与催化"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curation", type=Path, help="JSON file with a selected array")
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    parser.add_argument("--site-url", default="https://zichenwang114514.github.io/ai-chem-daily/")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    latest_path = args.site_root / "data" / "latest.json"
    candidates_path = args.site_root / "data" / "candidates" / "latest.json"
    latest = load_json(latest_path, {})
    candidates = load_json(candidates_path, {})
    curation = load_json(args.curation, {})
    if not latest or not candidates:
        raise RuntimeError("Run daily_digest.py before applying curation")
    if curation.get("date") != latest.get("date"):
        raise ValueError("Curation date does not match the latest digest")

    by_id = {paper["id"]: paper for paper in candidates.get("papers", [])}
    selected = curation.get("selected") or []
    if not 6 <= len(selected) <= 20:
        raise ValueError("Curation must contain between 6 and 20 selected papers")

    papers = []
    seen = set()
    for rank, item in enumerate(selected, 1):
        paper_id = str(item.get("id", ""))
        if not paper_id or paper_id in seen or paper_id not in by_id:
            raise ValueError(f"Unknown or duplicate paper id: {paper_id}")
        seen.add(paper_id)
        paper = dict(by_id[paper_id])
        category = clean_text(item.get("category"))
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Unsupported category for {paper_id}: {category}")
        summary = clean_text(item.get("summary_zh"))
        reason = clean_text(item.get("why_it_matters_zh"))
        if len(summary) < 25 or len(reason) < 18:
            raise ValueError(f"Curation text is too short for {paper_id}")
        paper["rank"] = rank
        paper["featured"] = rank <= 3
        paper["category"] = category
        paper["summary_zh"] = summary
        paper["why_it_matters_zh"] = reason
        paper["quality_score"] = max(0, min(100, float(item.get("quality_score", paper.get("quality_score", 0)))))
        reviewed_tags = [clean_text(value) for value in (item.get("tags") or []) if clean_text(value)]
        paper["tags"] = list(dict.fromkeys([category, *reviewed_tags, *(paper.get("tags") or [])]))[:6]
        paper["evidence_flags"] = [clean_text(value) for value in (item.get("evidence_flags") or []) if clean_text(value)][:5]
        authors = paper.get("authors") or []
        if not authors:
            paper["author_line"] = "作者信息暂缺"
        elif len(authors) <= 3:
            paper["author_line"] = ", ".join(authors)
        else:
            paper["author_line"] = f"{', '.join(authors[:3])} 等 {len(authors)} 人"
        papers.append(paper)

    latest["papers"] = papers
    latest["method"] = "公开元数据全量抓取 + ChatGPT 摘要复核"
    latest["method_note"] = "系统抓取公开元数据并完成规则初筛，随后依据题名和摘要复核相关性、方法信息与验证证据；预印本未经同行评议。"
    latest["stats"]["selected"] = len(papers)
    latest["stats"]["topics"] = {}
    for paper in papers:
        category = paper["category"]
        latest["stats"]["topics"][category] = latest["stats"]["topics"].get(category, 0) + 1

    write_json(latest_path, latest)
    write_json(args.site_root / "data" / "archive" / f"{latest['date']}.json", latest)
    archive_index_path = args.site_root / "data" / "archive" / "index.json"
    archive_index = load_json(archive_index_path, {"schema_version": 1, "items": []})
    for item in archive_index.get("items", []):
        if item.get("date") == latest["date"]:
            item["selected"] = len(papers)
    write_json(archive_index_path, archive_index)

    email_html, email_markdown = render_email(latest, args.site_url)
    email_root = args.site_root / "email"
    email_root.mkdir(parents=True, exist_ok=True)
    (email_root / "latest.html").write_text(email_html, encoding="utf-8")
    (email_root / "latest.md").write_text(email_markdown, encoding="utf-8")
    print(f"Applied reviewed curation for {latest['date']}: {len(papers)} papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
