#!/usr/bin/env python3
"""Import a structured ChatGPT scheduled-task submission from a GitHub Issue."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from daily_digest import load_json, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue_body", type=Path)
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    parser.add_argument("--issue-number", default=os.getenv("ISSUE_NUMBER", "unknown"))
    parser.add_argument("--issue-url", default=os.getenv("ISSUE_URL", ""))
    return parser.parse_args()


def extract_payload(text: str) -> dict[str, Any]:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = match.group(1) if match else text.strip()
    return json.loads(candidate)


def publish_generic_digest(site_root: Path, payload: dict[str, Any], issue: dict[str, str]) -> None:
    channel = payload["channel"]
    day = payload["date"]
    items = payload.get("items") or []
    digest = {
        "schema_version": 1,
        "date": day,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": payload.get("title") or f"{channel} 每日简报",
        "subtitle": payload.get("summary") or "由已安排任务整理的每日资料。",
        "method": "ChatGPT 已安排任务采集与整理",
        "method_note": "内容来自公开网页与公开资料，请通过原始链接核查。",
        "stats": {
            "fetched": int(payload.get("fetched") or len(items)),
            "candidates": int(payload.get("candidates") or len(items)),
            "selected": len(items),
            "sources": payload.get("sources") or {},
            "topics": payload.get("topics") or {},
        },
        "source_errors": payload.get("source_errors") or [],
        "papers": items,
        "intake": issue,
    }
    channel_root = site_root / "data" / "channels" / channel
    write_json(channel_root / "latest.json", digest)
    write_json(channel_root / "archive" / f"{day}.json", digest)
    index_path = channel_root / "archive" / "index.json"
    index = load_json(index_path, {"schema_version": 1, "items": []})
    entries = [item for item in index.get("items", []) if item.get("date") != day]
    entries.append(
        {
            "date": day,
            "href": f"data/channels/{channel}/archive/{day}.json",
            "selected": len(items),
            "candidates": digest["stats"]["candidates"],
            "fetched": digest["stats"]["fetched"],
            "kind": "json",
        }
    )
    index["items"] = sorted(entries, key=lambda item: item.get("date", ""), reverse=True)
    write_json(index_path, index)


def main() -> int:
    args = parse_args()
    payload = extract_payload(args.issue_body.read_text(encoding="utf-8"))
    inferred_curation = bool(payload.get("selected"))
    channel = str(payload.get("channel") or ("aixchem" if inferred_curation else "notes"))
    day = str(payload.get("date") or datetime.now(timezone.utc).date().isoformat())
    intake_type = str(payload.get("intake_type") or ("curation" if inferred_curation else "notes"))
    issue = {"number": str(args.issue_number), "url": args.issue_url}

    stored = {
        **payload,
        "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "issue": issue,
    }
    write_json(args.site_root / "data" / "intake" / channel / f"{day}-{args.issue_number}.json", stored)

    if channel == "aixchem" and intake_type == "curation":
        curation_path = Path("work") / f"issue-{args.issue_number}-curation.json"
        write_json(curation_path, {"date": day, "selected": payload.get("selected") or []})
        subprocess.run(
            [sys.executable, "backend/apply_curation.py", str(curation_path), "--site-root", str(args.site_root)],
            check=True,
        )
        result = "aixchem curation applied"
    elif intake_type == "digest":
        publish_generic_digest(args.site_root, payload, issue)
        result = f"{channel} digest published"
    else:
        result = f"{channel} notes stored"

    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as stream:
            stream.write(f"channel={channel}\n")
            stream.write(f"date={day}\n")
            stream.write(f"result={result}\n")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
