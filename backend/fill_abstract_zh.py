#!/usr/bin/env python3
"""Apply prepared Chinese abstracts onto published JSON payloads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from daily_digest import clean_text, looks_cjk, slim_channel_payload, slim_daily_payload, write_json


def load_map(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        items = raw.get("items") or raw
        if isinstance(items, dict):
            return {str(key): clean_text(value) for key, value in items.items() if clean_text(value)}
        raw = items
    mapping: dict[str, str] = {}
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            item_id = clean_text(row.get("id"))
            text = clean_text(row.get("abstract_zh") or row.get("zh") or row.get("text"))
            if item_id and text:
                mapping[item_id] = text
    return mapping


def attach(item: dict[str, Any], mapping: dict[str, str]) -> bool:
    item_id = clean_text(item.get("id"))
    source = clean_text(item.get("abstract_or_text") or item.get("abstract"))
    current = clean_text(item.get("abstract_zh"))
    translated = mapping.get(item_id, "")
    if looks_cjk(source) and not translated:
        translated = source
    if not translated or translated == current:
        if looks_cjk(source) and current != source:
            item["abstract_zh"] = source
            return True
        return False
    item["abstract_zh"] = translated
    return True


def walk_items(payload: dict[str, Any], mapping: dict[str, str]) -> int:
    changed = 0
    for item in payload.get("items") or payload.get("papers") or []:
        if isinstance(item, dict) and attach(item, mapping):
            changed += 1
    for channel in payload.get("channels") or []:
        for item in channel.get("items") or channel.get("papers") or []:
            if isinstance(item, dict) and attach(item, mapping):
                changed += 1
    return changed


def rewrite_channel_like(path: Path, mapping: dict[str, str], *, clip_release: bool) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return 0
    changed = walk_items(payload, mapping)
    if not changed:
        return 0
    if payload.get("channels"):
        write_json(path, slim_daily_payload(payload, include_abstract=True, clip_release=clip_release))
    else:
        write_json(path, slim_channel_payload(payload, include_abstract=True, clip_release=clip_release))
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    args = parser.parse_args()
    mapping = load_map(args.mapping)
    if not mapping:
        raise SystemExit("translation map is empty")
    site = args.site_root / "data"
    updated = 0
    targets = [
        site / "latest.json",
        *sorted((site / "archive").glob("????-??-??.json")),
        *sorted((site / "daily" / "archive").glob("????-??-??.json")),
    ]
    for channel_root in sorted((site / "channels").glob("*")):
        targets.append(channel_root / "latest.json")
        targets.extend(sorted((channel_root / "archive").glob("????-??-??.json")))
    for path in targets:
        if path.exists():
            updated += rewrite_channel_like(path, mapping, clip_release=True)
    print(f"Applied Chinese abstracts to {updated} item copies; map={len(mapping)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
