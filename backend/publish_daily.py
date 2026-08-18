#!/usr/bin/env python3
"""Build the five-channel home payload and one combined email message."""

from __future__ import annotations

import argparse
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aix_pipeline import CHANNELS, CHANNEL_META, natural_key
from daily_digest import SITE_NAME, SITE_TITLE, load_json, slim_public_item, write_json


SITE_URL = "https://zichenwang114514.github.io/ai-x-daily/"


def factual_overview(channels: list[dict[str, Any]], summary_overview: str) -> str:
    counts = "今日精选：" + "，".join(f"{channel['name']} {channel['stats']['selected']} 项" for channel in channels) + "。"
    text = (summary_overview or "").strip()
    if not text:
        return counts
    if text.startswith("今日精选"):
        return text
    return counts + text


def render_email(payload: dict[str, Any], site_url: str) -> tuple[str, str]:
    html_sections = []
    markdown_sections = []
    for channel in payload["channels"]:
        stats = channel["stats"]
        channel_url = f"{site_url.rstrip('/')}/channels/{channel['id']}/"
        rows = []
        lines = []
        for item in channel["items"][:3]:
            rows.append(f'<li style="margin:0 0 16px"><a href="{html.escape(item["url"])}" style="color:#17345b;font-weight:700;text-decoration:none">{html.escape(item["title"])}</a><div style="margin-top:5px;color:#46556d;line-height:1.65">{html.escape(item.get("summary_zh") or "请前往网站查看详情。")}</div></li>')
            lines.append(f'- [{item["title"]}]({item["url"]}) — {item.get("summary_zh") or "请前往网站查看详情。"}')
        if not rows:
            rows.append('<li style="color:#69768a">今日无足够高质量更新。</li>')
            lines.append("- 今日无足够高质量更新。")
        status = "；".join(channel.get("source_errors") or []) or "各来源已完成"
        html_sections.append(f'<section style="padding:22px 0;border-bottom:1px solid #e7eaf0"><h2 style="margin:0 0 8px;font-size:21px">{html.escape(channel["name"])}</h2><p style="margin:0 0 14px;color:#69768a">采集 {stats["fetched"]} · 候选 {stats["candidates"]} · 精选 {stats["selected"]} · {html.escape(status)}</p><ol style="padding-left:22px">{"".join(rows)}</ol><a href="{channel_url}" style="color:#087c78">查看频道专页</a></section>')
        markdown_sections.append(f'## {channel["name"]}\n\n采集 {stats["fetched"]}，候选 {stats["candidates"]}，精选 {stats["selected"]}。来源状态：{status}\n\n' + "\n".join(lines) + f'\n\n[查看频道专页]({channel_url})')
    overview = payload.get("overview_zh") or "五个频道已完成当日整理，以下列出各频道前三项。"
    email_html = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"></head><body style="margin:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;color:#17233b"><table role="presentation" width="100%"><tr><td align="center" style="padding:28px 12px"><table role="presentation" width="720" style="width:100%;max-width:720px;background:#fff;border-radius:18px;padding:34px"><tr><td><div style="font-size:12px;letter-spacing:2px;color:#087c78">{SITE_NAME}</div><h1 style="margin:8px 0">{SITE_NAME} · {payload["date"]}</h1><p style="color:#46556d;line-height:1.7">{html.escape(overview)}</p>{''.join(html_sections)}<p style="text-align:center;margin-top:28px"><a href="{site_url}" style="display:inline-block;padding:11px 24px;border-radius:999px;background:#087c78;color:#fff;text-decoration:none;font-weight:700">查看完整网站与历史归档</a></p></td></tr></table></td></tr></table></body></html>'''
    markdown = f'# {SITE_NAME} · {payload["date"]}\n\n{overview}\n\n' + "\n\n".join(markdown_sections) + f'\n\n[查看完整网站与历史归档]({site_url})\n'
    return email_html, markdown


def upsert_daily_archive(site_root: Path, payload: dict[str, Any]) -> None:
    day = payload["date"]
    archive_root = site_root / "data" / "daily" / "archive"
    write_json(archive_root / f"{day}.json", payload)
    index_path = archive_root / "index.json"
    index = load_json(index_path, {"schema_version": "2.0", "items": []})
    items = [item for item in index.get("items", []) if item.get("date") != day]
    selected = sum(int(channel.get("stats", {}).get("selected") or 0) for channel in payload.get("channels", []))
    items.append({
        "date": day,
        "href": f"data/daily/archive/{day}.json",
        "selected": selected,
        "kind": "json",
    })
    index["schema_version"] = index.get("schema_version") or "2.0"
    index["items"] = sorted(items, key=lambda item: item.get("date", ""), reverse=True)
    write_json(index_path, index)


def build(site_root: Path, summary_path: Path | None, site_url: str, *, write_payload: bool = True) -> dict[str, Any]:
    summary = load_json(summary_path, {}) if summary_path else {}
    latest_by_channel: dict[str, dict[str, Any]] = {}
    channel_dates: list[str] = []
    for channel_id in CHANNELS:
        latest = load_json(site_root / "data" / "channels" / channel_id / "latest.json", {})
        if not latest:
            raise RuntimeError(f"Missing latest data for {channel_id}")
        latest_by_channel[channel_id] = latest
        if latest.get("date"):
            channel_dates.append(str(latest["date"]))
    if not channel_dates:
        raise RuntimeError("No channel dates available")
    run_date = max(channel_dates)
    channels = []
    archive_channels = []
    seen: set[str] = set()
    for channel_id in CHANNELS:
        latest = latest_by_channel[channel_id]
        stale = str(latest.get("date") or "") != run_date
        items = []
        if not stale:
            for item in latest.get("items") or latest.get("papers") or []:
                key = natural_key(item)
                if key in seen:
                    continue
                seen.add(key)
                items.append(item)
        stats = dict(latest.get("stats") or {})
        stats["selected"] = len(items)
        name = CHANNEL_META[channel_id][0].replace(" 每日精选", "")
        errors = list(latest.get("source_errors") or [])
        if stale:
            errors.append("当日未更新，未纳入本期")
        entry = {
            "id": channel_id,
            "name": name,
            "stats": stats,
            "source_errors": errors,
        }
        home_items = [slim_public_item(item, include_abstract=False) for item in items]
        archive_items = [slim_public_item(item, include_abstract=True, clip_release=True) for item in items]
        channels.append({**entry, "items": home_items})
        archive_channels.append({**entry, "items": archive_items})
    existing = load_json(site_root / "data" / "daily" / "latest.json", {})
    overview = summary.get("overview_zh") or existing.get("overview_zh") or ""
    highlights = summary.get("channel_highlights") or existing.get("channel_highlights") or {}
    payload = {
        "schema_version": "2.0", "date": run_date,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": SITE_TITLE,
        "overview_zh": factual_overview(channels, overview),
        "channel_highlights": highlights,
        "channels": channels,
    }
    if write_payload:
        write_json(site_root / "data" / "daily" / "latest.json", payload)
        upsert_daily_archive(site_root, {**payload, "channels": archive_channels})
    email_html, email_markdown = render_email(payload, site_url)
    email_root = site_root / "email"
    email_root.mkdir(parents=True, exist_ok=True)
    (email_root / "latest.html").write_text(email_html, encoding="utf-8")
    (email_root / "latest.md").write_text(email_markdown, encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--site-url", default=SITE_URL)
    args = parser.parse_args()
    payload = build(args.site_root, args.summary, args.site_url)
    print(f"Combined daily ready: {payload['date']}; channels={len(payload['channels'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
