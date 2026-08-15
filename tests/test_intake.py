import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from import_intake import extract_payload, publish_generic_digest  # noqa: E402


class ScheduledIntakeTests(unittest.TestCase):
    def test_extracts_json_from_issue_form_body(self):
        body = """### JSON 资料

```json
{"schema_version":"1.0","intake_type":"notes","channel":"aivoices","date":"2026-08-16"}
```
"""
        payload = extract_payload(body)
        self.assertEqual(payload["channel"], "aivoices")

    def test_generic_digest_creates_latest_and_archive(self):
        payload = {
            "schema_version": "1.0",
            "intake_type": "digest",
            "channel": "aixmath",
            "date": "2026-08-16",
            "title": "AI × Math 每日简报",
            "items": [
                {
                    "title": "Example",
                    "url": "https://example.com/paper",
                    "summary_zh": "示例资料。",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            site_root = Path(directory)
            publish_generic_digest(site_root, payload, {"number": "7", "url": "https://example.com/7"})
            latest = json.loads((site_root / "data" / "channels" / "aixmath" / "latest.json").read_text(encoding="utf-8"))
            index = json.loads((site_root / "data" / "channels" / "aixmath" / "archive" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["stats"]["selected"], 1)
            self.assertEqual(index["items"][0]["date"], "2026-08-16")


if __name__ == "__main__":
    unittest.main()
