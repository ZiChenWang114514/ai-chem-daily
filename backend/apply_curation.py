#!/usr/bin/env python3
"""Apply a reviewed curation JSON to the latest digest and rebuild email assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aix_pipeline import LIMITS
from daily_digest import archive_index_entry, author_line, clean_text, load_json, looks_cjk, publish_tags, render_email, slim_public_item, upsert_archive_index, write_json


ALLOWED_CATEGORIES = {"方法与模型", "分子与药物发现", "结构与生物", "材料与催化"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("curation", type=Path, help="JSON file with a selected array")
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    parser.add_argument("--site-url", default="https://zichenwang114514.github.io/ai-x-daily/")
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

    candidate_records = candidates.get("papers") or candidates.get("items") or []
    by_id = {paper["id"]: paper for paper in candidate_records}
    selected = curation.get("selected") or []
    if not 6 <= len(selected) <= LIMITS["aixchem"]:
        raise ValueError(f"Curation must contain between 6 and {LIMITS['aixchem']} selected papers")

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
        source_abstract = clean_text(paper.get("abstract_or_text") or paper.get("abstract"))
        abstract_zh = clean_text(item.get("abstract_zh"))
        if looks_cjk(source_abstract) and not abstract_zh:
            abstract_zh = source_abstract
        if len(summary) < 25 or len(reason) < 18:
            raise ValueError(f"Curation text is too short for {paper_id}")
        if source_abstract and not abstract_zh:
            raise ValueError(f"Missing Chinese abstract for {paper_id}")
        paper["rank"] = rank
        paper["featured"] = rank <= 3
        paper["category"] = category
        paper["summary_zh"] = summary
        paper["why_it_matters_zh"] = reason
        paper["abstract_zh"] = abstract_zh
        paper["quality_score"] = max(0, min(100, float(item.get("quality_score", paper.get("quality_score", 0)))))
        reviewed_tags = [clean_text(value) for value in (item.get("tags") or []) if clean_text(value)]
        paper["tags"] = publish_tags(category, reviewed_tags)
        paper["evidence_flags"] = [clean_text(value) for value in (item.get("evidence_flags") or []) if clean_text(value)][:5]
        authors = paper.get("authors") or paper.get("creators") or []
        paper["author_line"] = author_line(authors)
        papers.append(paper)

    latest["items"] = [slim_public_item(paper, include_abstract=True, clip_release=True) for paper in papers]
    latest.pop("papers", None)
    latest["method"] = "公开元数据全量抓取 + ChatGPT 摘要复核"
    latest["method_note"] = "系统抓取公开元数据并完成规则初筛，随后依据题名和摘要复核相关性、方法信息与验证证据；预印本未经同行评议。"
    latest["stats"]["selected"] = len(papers)
    latest["stats"]["topics"] = {}
    for paper in papers:
        category = paper["category"]
        latest["stats"]["topics"][category] = latest["stats"]["topics"].get(category, 0) + 1

    write_json(latest_path, latest)
    write_json(args.site_root / "data" / "archive" / f"{latest['date']}.json", latest)
    chem_archive = args.site_root / "data" / "channels" / "aixchem" / "archive"
    write_json(chem_archive / f"{latest['date']}.json", latest)
    entry = archive_index_entry(
        latest["date"],
        selected=len(papers),
        candidates=latest["stats"].get("candidates", 0),
        fetched=latest["stats"].get("fetched", 0),
    )
    upsert_archive_index(args.site_root / "data" / "archive" / "index.json", entry)
    upsert_archive_index(chem_archive / "index.json", entry)

    email_html, email_markdown = render_email(latest, args.site_url)
    email_root = args.site_root / "email"
    email_root.mkdir(parents=True, exist_ok=True)
    (email_root / "latest.html").write_text(email_html, encoding="utf-8")
    (email_root / "latest.md").write_text(email_markdown, encoding="utf-8")
    print(f"Applied reviewed curation for {latest['date']}: {len(papers)} papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
