import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("aixchem", "aixbio", "aixmath", "aivoices", "engineering")


class FiveChannelConfigurationTests(unittest.TestCase):
    def test_all_channels_are_active_and_have_unified_paths(self):
        config = json.loads((ROOT / "config" / "channels.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in config["channels"]], list(CHANNELS))
        for item in config["channels"]:
            self.assertEqual(item["status"], "active")
            base = f"data/channels/{item['id']}"
            self.assertEqual(item["latest_path"], f"{base}/latest.json")
            self.assertEqual(item["candidate_path"], f"{base}/candidates/latest.json")
            self.assertEqual(item["archive_path"], f"{base}/archive/index.json")

    def test_scheduled_reviews_use_terra_high(self):
        settings = (ROOT / "config" / "local.settings.example.psd1").read_text(encoding="utf-8")
        runner = (ROOT / "ops" / "run_local_pipeline.ps1").read_text(encoding="utf-8")
        self.assertIn('Model = "gpt-5.6-terra"', settings)
        self.assertIn('ReasoningEffort = "high"', settings)
        self.assertIn('"--model", [string]$Settings.Model', runner)
        self.assertIn('model_reasoning_effort=', runner)
        self.assertNotIn("gpt-5.6-sol", runner)

    def test_unified_morning_run_is_configured(self):
        settings = (ROOT / "config" / "local.settings.example.psd1").read_text(encoding="utf-8")
        self.assertIn('ScheduleTime = "07:00"', settings)
        self.assertNotIn("RunSlots", settings)
        self.assertNotIn("RetryTime", settings)
        self.assertNotIn("PublishDeadline", settings)
        runner = (ROOT / "ops" / "run_local_pipeline.ps1").read_text(encoding="utf-8")
        self.assertNotIn("Start-Job", runner)
        self.assertNotIn("ForEach-Object -Parallel", runner)
        self.assertNotIn("Wait-ForSlot", runner)
        self.assertLess(runner.index("Invoke-Collection"), runner.index("Invoke-Curation"))

    def test_watchlists_are_editable_configuration(self):
        watchlists = json.loads((ROOT / "config" / "watchlists.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(watchlists["x_accounts"]), 30)
        self.assertGreaterEqual(len(watchlists["x_topic_queries"]), 2)
        self.assertGreaterEqual(len(watchlists["github_repositories"]), 20)
        self.assertGreaterEqual(len(watchlists["openreview_domains"]), 5)

    def test_private_paths_and_secrets_are_ignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for value in ("work/", "config/local.secrets.psd1"):
            self.assertIn(value, ignored)
        tracked_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts and path.name != "local.secrets.psd1")
        self.assertNotRegex(tracked_text, re.compile(r"AAAAAAAAAAAAAAAAAAAAA[A-Za-z0-9%]+"))

    def test_legacy_html_is_imported_into_chem_archive(self):
        archive = json.loads((ROOT / "public" / "data" / "channels" / "aixchem" / "archive" / "2026-07-17.json").read_text(encoding="utf-8"))
        self.assertEqual(archive["date"], "2026-07-17")
        self.assertGreaterEqual(len(archive.get("items") or archive.get("papers") or []), 16)
        daily = json.loads((ROOT / "public" / "data" / "daily" / "archive" / "2026-07-17.json").read_text(encoding="utf-8"))
        self.assertEqual(daily["date"], "2026-07-17")
        activity = json.loads((ROOT / "public" / "api" / "v1" / "activity.json").read_text(encoding="utf-8"))
        dates = {item["date"] for item in activity["items"] if item["channel"] == "aixchem"}
        self.assertIn("2026-07-17", dates)
        self.assertIn("2026-08-15", dates)

    def test_channel_pages_exist(self):
        for channel in CHANNELS:
            page = ROOT / "public" / "channels" / channel / "index.html"
            self.assertTrue(page.exists())
            text = page.read_text(encoding="utf-8")
            self.assertIn(f'data-channel="{channel}"', text)
            self.assertIn('data-root="../../"', text)


class UnifiedOutputTests(unittest.TestCase):
    def test_generated_outputs_when_present(self):
        required = {
            "id", "channel", "related_channels", "item_type", "source", "title", "url",
            "published_at", "updated_at", "creators", "language", "abstract_or_text",
            "summary_zh", "why_it_matters_zh", "quality_score", "tags", "evidence_flags",
            "publication_status", "rank",
        }
        seen = set()
        for channel in CHANNELS:
            path = ROOT / "public" / "data" / "channels" / channel / "latest.json"
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["channel"], channel)
            for item in payload.get("items", []):
                self.assertTrue(required.issubset(item))
                key = (item.get("metadata") or {}).get("doi") or item["url"].split("?", 1)[0].rstrip("/").lower()
                self.assertNotIn(key, seen)
                seen.add(key)


if __name__ == "__main__":
    unittest.main()
