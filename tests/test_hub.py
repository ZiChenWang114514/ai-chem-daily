import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
API = PUBLIC / "api" / "v1"


class HubInterfaceTests(unittest.TestCase):
    def load(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_manifest_has_all_planned_channels(self):
        manifest = self.load(API / "manifest.json")
        ids = {channel["id"] for channel in manifest["channels"]}
        self.assertEqual(ids, {"aixchem", "aixbio", "aixmath", "aivoices", "engineering"})
        self.assertTrue(manifest["endpoints"]["daily_task"].startswith("https://"))

    def test_activity_exposes_calendar_metrics(self):
        activity = self.load(API / "activity.json")
        self.assertEqual(activity["metrics"], ["selected", "candidates", "fetched"])
        aixchem = [item for item in activity["items"] if item["channel"] == "aixchem"]
        self.assertTrue(aixchem)
        for item in aixchem:
            self.assertTrue({"date", "selected", "candidates", "fetched"}.issubset(item))

    def test_scheduled_task_has_read_and_write_interfaces(self):
        task = self.load(API / "tasks" / "daily-brief.json")
        self.assertEqual(task["write_interface"]["provider"], "local-codex-cli")
        self.assertEqual(task["write_interface"]["label"], "scheduled-intake")
        self.assertTrue(task["write_interface"]["schema"].startswith("https://"))

    def test_intake_schema_supports_current_and_future_channels(self):
        schema = self.load(API / "schemas" / "intake.json")
        channels = schema["properties"]["channel"]["enum"]
        self.assertIn("aixchem", channels)
        self.assertIn("aixmath", channels)
        self.assertIn("aivoices", channels)

    def test_raw_snapshots_are_not_public(self):
        self.assertFalse((PUBLIC / "raw").exists())


if __name__ == "__main__":
    unittest.main()
