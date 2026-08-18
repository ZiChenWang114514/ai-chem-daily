#!/usr/bin/env python3
"""Validate a channel review and publish its latest and archive JSON."""

from __future__ import annotations

import argparse
from pathlib import Path

from aix_pipeline import CHANNELS, LIMITS, THRESHOLDS, natural_key
from daily_digest import archive_index_entry, clean_text, load_json, looks_cjk, publish_tags, slim_public_item, write_json
from publish_daily import SITE_URL, build as build_daily


def earlier_channel_keys(site_root: Path, channel: str, day: str) -> set[str]:
    claimed: set[str] = set()
    for other in CHANNELS:
        if other == channel:
            break
        payload = load_json(site_root / "data" / "channels" / other / "latest.json", {})
        if payload.get("date") != day:
            continue
        for item in payload.get("items") or payload.get("papers") or []:
            key = natural_key(item)
            if key:
                claimed.add(key)
    return claimed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel", choices=CHANNELS)
    parser.add_argument("curation", type=Path)
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    parser.add_argument("--site-url", default=SITE_URL)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.site_root / "data" / "channels" / args.channel
    latest = load_json(root / "latest.json", {})
    candidates = load_json(root / "candidates" / "latest.json", {})
    curation = load_json(args.curation, {})
    if not latest or not candidates:
        raise RuntimeError(f"Missing collection output for {args.channel}")
    if curation.get("date") != latest.get("date") or curation.get("channel") != args.channel:
        raise ValueError("Curation date or channel does not match the collection")
    selected = curation.get("selected") or []
    if len(selected) > LIMITS[args.channel]:
        raise ValueError(f"Too many selected items for {args.channel}")
    by_id = {item["id"]: item for item in candidates.get("items", [])}
    claimed = earlier_channel_keys(args.site_root, args.channel, str(latest.get("date") or ""))
    output = []
    seen_ids: set[str] = set()
    seen_natural: set[str] = set()
    skipped = 0
    for review in selected:
        current_id = str(review.get("id") or "")
        if not current_id or current_id in seen_ids or current_id not in by_id:
            raise ValueError(f"Unknown or duplicate item id: {current_id}")
        item = dict(by_id[current_id])
        key = natural_key(item)
        if key in seen_natural:
            raise ValueError(f"Duplicate natural identifier: {current_id}")
        if key in claimed:
            skipped += 1
            continue
        seen_ids.add(current_id)
        seen_natural.add(key)
        score = float(review.get("quality_score", item.get("quality_score", 0)))
        if score < THRESHOLDS[args.channel]:
            raise ValueError(f"Selected item score is below threshold: {current_id}")
        summary = clean_text(review.get("summary_zh"))
        reason = clean_text(review.get("why_it_matters_zh"))
        source_abstract = clean_text(item.get("abstract_or_text") or item.get("abstract"))
        abstract_zh = clean_text(review.get("abstract_zh"))
        if looks_cjk(source_abstract) and not abstract_zh:
            abstract_zh = source_abstract
        if len(summary) < 20 or len(reason) < 16:
            raise ValueError(f"Review text is too short: {current_id}")
        if source_abstract and not abstract_zh:
            raise ValueError(f"Missing Chinese abstract: {current_id}")
        rank = len(output) + 1
        item.update({
            "summary_zh": summary,
            "why_it_matters_zh": reason,
            "abstract_zh": abstract_zh,
            "quality_score": min(100, score),
            "category": clean_text(review.get("category")) or item.get("category"),
            "tags": publish_tags(clean_text(review.get("category")) or item.get("category"), review.get("tags", [])),
            "evidence_flags": list(dict.fromkeys([clean_text(flag) for flag in review.get("evidence_flags", []) if clean_text(flag)] + list(item.get("evidence_flags") or [])))[:6],
            "related_channels": [value for value in review.get("related_channels", item.get("related_channels", [])) if value in CHANNELS and value != args.channel],
            "rank": rank,
            "featured": rank <= 3,
        })
        item["published"] = str(item.get("published_at", ""))[:10]
        creators = item.get("creators") or []
        item["author_line"] = ", ".join(creators[:3]) + (f" 等 {len(creators)} 人" if len(creators) > 3 else "") if creators else "作者信息暂缺"
        output.append(slim_public_item(item, include_abstract=True, clip_release=True))

    latest["items"] = output
    latest.pop("papers", None)
    latest["stats"]["selected"] = len(output)
    latest["review"] = {
        "model": "gpt-5.6-terra",
        "reasoning_effort": "high",
        "note": clean_text(curation.get("editor_note")),
    }
    write_json(root / "latest.json", latest)
    archive_root = root / "archive"
    write_json(archive_root / f"{latest['date']}.json", latest)
    index_path = archive_root / "index.json"
    index = load_json(index_path, {"schema_version": "2.0", "items": []})
    items = [item for item in index.get("items", []) if item.get("date") != latest["date"]]
    items.append(archive_index_entry(
        latest["date"],
        selected=len(output),
        candidates=latest["stats"].get("candidates", 0),
        fetched=latest["stats"].get("fetched", 0),
        href=f"data/channels/{args.channel}/archive/{latest['date']}.json",
    ))
    if args.channel == "aixchem":
        legacy_root = args.site_root / "data" / "archive"
        known_dates = {item["date"] for item in items}
        for legacy_path in legacy_root.glob("????-??-??.json"):
            legacy = load_json(legacy_path, {})
            legacy_date = legacy.get("date")
            if not legacy_date or legacy_date in known_dates:
                continue
            write_json(archive_root / legacy_path.name, legacy)
            legacy_stats = legacy.get("stats", {})
            items.append(archive_index_entry(
                legacy_date,
                selected=legacy_stats.get("selected", len(legacy.get("papers", []))),
                candidates=legacy_stats.get("candidates", 0),
                fetched=legacy_stats.get("fetched", 0),
            ))
            known_dates.add(legacy_date)
    index["schema_version"] = "2.0"
    index["items"] = sorted(items, key=lambda value: value["date"], reverse=True)
    write_json(index_path, index)
    if args.channel == "aixchem":
        write_json(args.site_root / "data" / "latest.json", latest)
        write_json(args.site_root / "data" / "archive" / f"{latest['date']}.json", latest)
        write_json(args.site_root / "data" / "archive" / "index.json", index)
        legacy_candidates = dict(candidates)
        records = list(legacy_candidates.get("items") or legacy_candidates.get("papers") or [])
        legacy_candidates["items"] = records
        legacy_candidates.pop("papers", None)
        write_json(args.site_root / "data" / "candidates" / "latest.json", legacy_candidates)
    try:
        build_daily(args.site_root, None, args.site_url, write_payload=False)
    except RuntimeError:
        pass
    skipped_note = f", skipped {skipped} claimed by earlier channels" if skipped else ""
    print(f"Published {args.channel}: {len(output)} selected{skipped_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
