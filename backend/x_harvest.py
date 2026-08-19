#!/usr/bin/env python3
"""Build Grok X search queries and ingest harvest files into the source cache."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from aix_pipeline import build_x_queries, collection_window, item_id, within_window
from daily_digest import clean_text, load_json, write_json


POST_ID_RE = re.compile(r"(?:status|statuses)/(\d+)")


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def query_plan(watchlists: dict[str, Any], run_date: date) -> dict[str, Any]:
    start, end = collection_window(run_date)
    queries = [
        {
            "kind": kind,
            "query": query,
            "mode": "Latest" if kind == "accounts" else "Top",
            "limit": 10,
        }
        for kind, query in build_x_queries(watchlists, start, end)
    ]
    return {
        "schema_version": "1.0",
        "source": "grok.x.search",
        "date": run_date.isoformat(),
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "queries": queries,
    }


def first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, dict):
            nested = first_text(value.get("username"), value.get("screen_name"), value.get("handle"), value.get("name"), value.get("text"))
            if nested:
                return nested
        text = clean_text(value)
        if text:
            return text
    return ""


def first_int(value: Any, *names: str) -> int:
    if isinstance(value, dict):
        for name in names:
            raw = value.get(name)
            if raw in (None, ""):
                continue
            try:
                return int(raw)
            except (TypeError, ValueError):
                continue
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def extract_post_id(item: dict[str, Any]) -> str:
    for value in (item.get("id"), item.get("post_id"), item.get("tweet_id"), item.get("status_id")):
        text = clean_text(value)
        if text.isdigit():
            return text
        match = POST_ID_RE.search(text)
        if match:
            return match.group(1)
    match = POST_ID_RE.search(first_text(item.get("url"), item.get("tweet_url"), item.get("permalink")))
    return match.group(1) if match else ""


def extract_metrics(item: dict[str, Any]) -> dict[str, int]:
    raw = item.get("metrics") or item.get("public_metrics") or item
    return {
        "like_count": first_int(raw, "like_count", "favorite_count", "likes", "favoriteCount"),
        "repost_count": first_int(raw, "repost_count", "retweet_count", "reposts", "retweetCount"),
        "reply_count": first_int(raw, "reply_count", "replies", "replyCount"),
        "quote_count": first_int(raw, "quote_count", "quotes", "quoteCount"),
    }


def is_retweet(item: dict[str, Any], text: str) -> bool:
    if item.get("is_retweet") or item.get("retweeted"):
        return True
    return text.startswith("RT @")


def already_normalized(item: dict[str, Any]) -> bool:
    return str(item.get("source") or "") == "X" and str(item.get("id") or "").startswith("x:") and item.get("abstract_or_text")


def normalize_grok_post(item: dict[str, Any], query_kind: str = "accounts") -> dict[str, Any] | None:
    if already_normalized(item):
        return item
    text = first_text(item.get("text"), item.get("full_text"), item.get("content"), item.get("abstract_or_text"))
    post_id = extract_post_id(item)
    if not text or not post_id or is_retweet(item, text):
        return None
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    author = item.get("author") if isinstance(item.get("author"), dict) else {}
    username = first_text(
        item.get("username"), item.get("handle"), item.get("screen_name"),
        user.get("username"), user.get("screen_name"), author.get("username"),
        item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
    )
    if not username:
        username = first_text(user.get("name"), author.get("name"))
    name = first_text(item.get("name"), user.get("name"), author.get("name"), item.get("author_name"), username)
    created = first_text(item.get("created_at"), item.get("published_at"), item.get("date"), item.get("time"))
    url = first_text(item.get("url"), item.get("tweet_url"), item.get("permalink")) or (f"https://x.com/{username}/status/{post_id}" if username else f"https://x.com/i/status/{post_id}")
    kind = first_text(item.get("query_kind"), (item.get("metadata") or {}).get("query_kind") if isinstance(item.get("metadata"), dict) else "", query_kind) or "accounts"
    language = first_text(item.get("lang"), item.get("language")) or "en"
    return {
        "id": item_id("x", post_id),
        "channel": "aivoices",
        "related_channels": [],
        "item_type": "social_post",
        "source": "X",
        "title": f"@{username}：{text[:120]}" if username else text[:140],
        "url": url,
        "published_at": created,
        "updated_at": created,
        "creators": [name or username],
        "language": language,
        "abstract_or_text": text,
        "summary_zh": "",
        "why_it_matters_zh": "",
        "quality_score": 0,
        "tags": [kind],
        "evidence_flags": [],
        "publication_status": "public_post",
        "rank": 0,
        "featured": False,
        "category": "研究发布",
        "metrics": extract_metrics(item),
        "metadata": {"post_id": post_id, "username": username, "query_kind": kind, "harvest": "grok.x.search"},
    }


def unwrap_items(payload: Any) -> list[tuple[dict[str, Any], str]]:
    if isinstance(payload, list):
        return [(item, "accounts") for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    rows: list[tuple[dict[str, Any], str]] = []
    for key in ("items", "posts", "data", "results"):
        values = payload.get(key)
        if not isinstance(values, list):
            continue
        default_kind = clean_text(payload.get("query_kind")) or "accounts"
        for item in values:
            if isinstance(item, dict):
                rows.append((item, default_kind))
        if rows:
            return rows
    if payload.get("text") or payload.get("id"):
        return [(payload, clean_text(payload.get("query_kind")) or "accounts")]
    return []


def ingest_harvest(payload: Any, run_date: date) -> list[dict[str, Any]]:
    start, end = collection_window(run_date)
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for item, kind in unwrap_items(payload):
        normalized = normalize_grok_post(item, kind)
        if not normalized or normalized["id"] in seen:
            continue
        if normalized.get("published_at") and not within_window(str(normalized["published_at"]), start, end):
            continue
        seen.add(normalized["id"])
        results.append(normalized)
    return results


def write_cache(root: Path, run_date: date, items: list[dict[str, Any]]) -> Path:
    path = root / "work" / "source-cache" / "x" / f"{run_date.isoformat()}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(items, stream, ensure_ascii=False)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or ingest Grok X harvests")
    parser.add_argument("command", choices=("queries", "ingest"))
    parser.add_argument("harvest", nargs="?", help="Grok harvest JSON for ingest")
    parser.add_argument("--date", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    run_date = parse_iso_date(args.date)
    watchlists = load_json(root / "config" / "watchlists.json", {})
    if args.command == "queries":
        plan = query_plan(watchlists, run_date)
        out = root / "work" / "grok-x" / f"{run_date.isoformat()}-queries.json"
        write_json(out, plan)
        json.dump(plan, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if not args.harvest:
        raise SystemExit("ingest 需要 harvest JSON 路径")
    payload = json.loads(Path(args.harvest).read_text(encoding="utf-8"))
    items = ingest_harvest(payload, run_date)
    path = write_cache(root, run_date, items)
    print(f"wrote {len(items)} X posts to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
