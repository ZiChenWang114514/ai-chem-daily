#!/usr/bin/env python3
"""Import standalone legacy HTML digests into the channel and daily archives."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from daily_digest import archive_index_entry, load_json, upsert_archive_index, write_json
from hub_publish import build_hub_interfaces


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "public"
CHANNELS = ("aixchem", "aixbio", "aixmath", "aivoices", "engineering")
CHANNEL_NAMES = {
    "aixchem": "AI × Chem",
    "aixbio": "AI × Bio",
    "aixmath": "AI × Math",
    "aivoices": "AI Voices",
    "engineering": "Engineering",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def clean_category(value: str) -> str:
    text = clean_text(re.sub(r"^[^\w\u4e00-\u9fff]+", "", value))
    text = text.replace("·", "、")
    return text or "其他更新"


def source_from_url(url: str) -> str:
    if "arxiv.org" in url:
        return "arXiv"
    if "biorxiv.org" in url:
        return "bioRxiv"
    if "chemrxiv" in url:
        return "ChemRxiv"
    if "medrxiv.org" in url:
        return "medRxiv"
    return "其他"


def item_id(url: str, source: str) -> str:
    if "arxiv.org/abs/" in url:
        arxiv_id = url.rsplit("/abs/", 1)[-1].split("?", 1)[0].strip("/")
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        return "arxiv:" + arxiv_id
    doi = ""
    if "doi.org/" in url:
        doi = url.split("doi.org/", 1)[-1]
    elif "/content/" in url:
        doi = url.split("/content/", 1)[-1].strip("/")
    if doi:
        prefix = "chemrxiv" if source == "ChemRxiv" else source.lower().replace(" ", "")
        return f"{prefix}:{doi}"
    return f"{source.lower()}:{url}"


def parse_authors(meta: str) -> tuple[list[str], str, str]:
    head, _, tail = meta.partition(" · ")
    published = tail.strip()[:10]
    authors = [part.strip() for part in re.split(r",|、", re.sub(r"\s+等\s+\d+\s*人", "", head)) if part.strip()]
    return authors, published, clean_text(head)


def parse_legacy_html(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if not date_match:
        raise ValueError(f"No date found in {path}")
    day = date_match.group(1)
    fetched = int(re.search(r"<b>(\d+)</b><span>当日抓取", raw).group(1)) if re.search(r"<b>(\d+)</b><span>当日抓取", raw) else 0
    candidates = int(re.search(r"<b>(\d+)</b><span>相关候选", raw).group(1)) if re.search(r"<b>(\d+)</b><span>相关候选", raw) else 0
    selected_stat = int(re.search(r"<b>(\d+)</b><span>今日精选", raw).group(1)) if re.search(r"<b>(\d+)</b><span>今日精选", raw) else 0

    category = "今日精选"
    items: list[dict[str, Any]] = []
    token_re = re.compile(
        r'<h2 class="sec">(.*?)</h2>|'
        r'<span class="rank">(\d+)</span><h3 class="ptitle"><a href="([^"]+)"[^>]*>(.*?)</a></h3>\s*'
        r'<div class="meta">(.*?)</div>\s*<div>(.*?)</div>\s*'
        r'<div class="comment">(.*?)</div>\s*'
        r'<div class="abstract"><details><summary></summary><p>(.*?)</p></details></div>',
        re.S,
    )
    for match in token_re.finditer(raw):
        if match.group(1) is not None:
            category = clean_category(match.group(1))
            continue
        url = clean_text(match.group(3))
        title = clean_text(match.group(4))
        authors, published, author_line = parse_authors(clean_text(match.group(5)))
        badges = [clean_text(item) for item in re.findall(r"<span class=\"badge[^\"]*\">(.*?)</span>", match.group(6))]
        source = next((item for item in badges if item in {"arXiv", "bioRxiv", "ChemRxiv", "medRxiv"}), source_from_url(url))
        tags = [item for item in badges if item and item != source][:6]
        summary = clean_text(match.group(7))
        abstract = clean_text(match.group(8))
        rank = int(match.group(2))
        item = {
            "id": item_id(url, source),
            "channel": "aixchem",
            "related_channels": [],
            "item_type": "preprint",
            "source": source,
            "title": title,
            "url": url,
            "published_at": published,
            "updated_at": published,
            "creators": authors,
            "language": "en",
            "abstract_or_text": abstract,
            "summary_zh": summary,
            "why_it_matters_zh": summary,
            "quality_score": 80,
            "tags": tags or [category],
            "evidence_flags": [],
            "publication_status": "preprint",
            "rank": rank,
            "featured": rank <= 3,
            "category": category,
            "authors": authors,
            "abstract": abstract,
            "published": published,
            "author_line": author_line or "作者信息暂缺",
        }
        items.append(item)

    sources: dict[str, int] = {}
    topics: dict[str, int] = {}
    for item in items:
        sources[item["source"]] = sources.get(item["source"], 0) + 1
        topics[item["category"]] = topics.get(item["category"], 0) + 1

    payload = {
        "schema_version": "2.0",
        "date": day,
        "channel": "aixchem",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": "AI × Chem 每日预印本精选",
        "subtitle": "面向人工智能与化学交叉研究的每日文献观察",
        "window": {"start": day, "end": day},
        "method": "历史页面导入",
        "method_note": f"从 legacy/{path.name} 导入，保留原题名、摘要与编者说明。",
        "stats": {
            "fetched": fetched,
            "candidates": candidates,
            "selected": selected_stat or len(items),
            "sources": sources,
            "topics": topics,
        },
        "source_errors": [],
        "items": items,
        "papers": items,
    }
    return payload


def write_chem_archive(payload: dict[str, Any]) -> None:
    day = payload["date"]
    chem_root = SITE / "data" / "channels" / "aixchem"
    write_json(chem_root / "archive" / f"{day}.json", payload)
    write_json(SITE / "data" / "archive" / f"{day}.json", payload)
    entry = archive_index_entry(
        day,
        selected=payload["stats"]["selected"],
        candidates=payload["stats"]["candidates"],
        fetched=payload["stats"]["fetched"],
    )
    upsert_archive_index(chem_root / "archive" / "index.json", entry)
    upsert_archive_index(SITE / "data" / "archive" / "index.json", entry)


def compose_daily(day: str) -> dict[str, Any]:
    latest = load_json(SITE / "data" / "daily" / "latest.json", {})
    channels = []
    total = 0
    for channel_id in CHANNELS:
        archive = load_json(SITE / "data" / "channels" / channel_id / "archive" / f"{day}.json", {})
        items = archive.get("items") or archive.get("papers") or []
        stats = archive.get("stats") or {"fetched": 0, "candidates": 0, "selected": len(items)}
        if not archive and not items:
            continue
        channels.append({
            "id": channel_id,
            "name": CHANNEL_NAMES[channel_id],
            "stats": stats,
            "source_errors": archive.get("source_errors", []),
            "items": items,
        })
        total += int(stats.get("selected") or len(items) or 0)
    if not channels:
        raise FileNotFoundError(f"No channel archive for {day}")
    existing = load_json(SITE / "data" / "daily" / "archive" / f"{day}.json", {})
    generic_overview = f"{day.replace('-', '年', 1).replace('-', '月', 1)}日的历史日报，共 {total} 项精选。"
    if day == "2026-07-17":
        generic_overview = "2026 年 7 月 17 日的 AI × Chem 历史日报，收录 16 项精选。"
    overview = existing.get("overview_zh") or (latest.get("overview_zh") if latest.get("date") == day else generic_overview)
    highlights = existing.get("channel_highlights") or (
        latest.get("channel_highlights") if latest.get("date") == day else {
            channel["id"]: f"{channel['name']} {channel['stats'].get('selected', 0)} 项" for channel in channels
        }
    )
    return {
        "schema_version": "2.0",
        "date": day,
        "generated_at": existing.get("generated_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": "AIX每日精读",
        "overview_zh": overview,
        "channel_highlights": highlights,
        "channels": channels,
    }


def rebuild_daily_archives() -> list[str]:
    dates: set[str] = set()
    for channel_id in CHANNELS:
        index = load_json(SITE / "data" / "channels" / channel_id / "archive" / "index.json", {})
        for item in index.get("items", []):
            if item.get("date"):
                dates.add(item["date"])
    written = []
    daily_entries = []
    for day in sorted(dates, reverse=True):
        payload = compose_daily(day)
        write_json(SITE / "data" / "daily" / "archive" / f"{day}.json", payload)
        selected = sum(int(channel["stats"].get("selected") or 0) for channel in payload["channels"])
        daily_entries.append({
            "date": day,
            "href": f"data/daily/archive/{day}.json",
            "selected": selected,
            "kind": "json",
        })
        written.append(day)
    write_json(SITE / "data" / "daily" / "archive" / "index.json", {"schema_version": "2.0", "items": daily_entries})
    return written


def main() -> int:
    imported = []
    for path in sorted((SITE / "legacy").glob("????-??-??.html")):
        payload = parse_legacy_html(path)
        write_chem_archive(payload)
        imported.append(f"{payload['date']}:{len(payload['items'])}")
    days = rebuild_daily_archives()
    build_hub_interfaces(SITE, ROOT / "config" / "channels.json", "https://zichenwang114514.github.io/ai-x-daily/")
    print("imported " + ", ".join(imported) if imported else "no legacy html")
    print("daily archives " + ", ".join(days))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
