#!/usr/bin/env python3
"""Rewrite published JSON to the slim public contract and refresh hub pages."""

from __future__ import annotations

from pathlib import Path

from aix_pipeline import CHANNELS
from daily_digest import SITE_TITLE, load_json, slim_channel_payload, slim_daily_payload, write_json
from hub_publish import build_hub_interfaces
from publish_daily import SITE_URL, build as build_daily


def slim_tree(root: Path, *, include_abstract: bool, clip_release: bool) -> None:
    if not root.exists():
        return
    for path in root.glob("????-??-??.json"):
        payload = load_json(path, {})
        if payload:
            write_json(path, slim_channel_payload(payload, include_abstract=include_abstract, clip_release=clip_release))


def main() -> int:
    site = Path("public")
    for channel in CHANNELS:
        channel_root = site / "data" / "channels" / channel
        latest = load_json(channel_root / "latest.json", {})
        if latest:
            write_json(channel_root / "latest.json", slim_channel_payload(latest, include_abstract=True, clip_release=True))
        slim_tree(channel_root / "archive", include_abstract=True, clip_release=True)

    legacy_latest = load_json(site / "data" / "latest.json", {})
    if legacy_latest:
        write_json(site / "data" / "latest.json", slim_channel_payload(legacy_latest, include_abstract=True, clip_release=True))
    slim_tree(site / "data" / "archive", include_abstract=True, clip_release=True)

    build_daily(site, None, SITE_URL)

    latest_date = load_json(site / "data" / "daily" / "latest.json", {}).get("date")
    for path in (site / "data" / "daily" / "archive").glob("????-??-??.json"):
        if path.stem == latest_date:
            continue
        payload = load_json(path, {})
        if not payload:
            continue
        slimmed = slim_daily_payload(payload, include_abstract=True, clip_release=True)
        slimmed["title"] = SITE_TITLE
        write_json(path, slimmed)

    build_hub_interfaces(site, Path("config/channels.json"), SITE_URL)
    print("Rewrote published payloads and hub interfaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
