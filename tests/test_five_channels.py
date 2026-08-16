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

    def test_serial_slots_and_retry_times_are_configured(self):
        settings = (ROOT / "config" / "local.settings.example.psd1").read_text(encoding="utf-8")
        for clock in ("01:00", "02:00", "03:00", "04:00", "05:00", "07:15", "07:45"):
            self.assertIn(clock, settings)
        runner = (ROOT / "ops" / "run_local_pipeline.ps1").read_text(encoding="utf-8")
        self.assertNotIn("Start-Job", runner)
        self.assertNotIn("ForEach-Object -Parallel", runner)

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
