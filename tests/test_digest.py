import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "public" / "data" / "latest.json"
ARCHIVE_INDEX = ROOT / "public" / "data" / "archive" / "index.json"


class DigestOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(LATEST.read_text(encoding="utf-8"))

    def test_required_top_level_fields(self):
        for key in ("date", "generated_at", "stats", "items", "method", "method_note"):
            self.assertIn(key, self.payload)
        self.assertNotIn("papers", self.payload)

    def test_selected_count_matches_items(self):
        items = self.payload.get("items") or []
        self.assertEqual(self.payload["stats"]["selected"], len(items))
        self.assertLessEqual(len(items), 16)

    def test_items_have_reviewable_fields(self):
        required = ("title", "abstract_or_text", "url", "source", "published", "summary_zh", "why_it_matters_zh")
        for paper in self.payload.get("items") or []:
            for key in required:
                self.assertTrue(paper.get(key), f"missing {key} in {paper.get('id')}")
            self.assertNotIn("abstract", paper)
            self.assertTrue(paper["url"].startswith("https://"))
            self.assertIn(paper["source"], {"arXiv", "bioRxiv", "ChemRxiv"})

    def test_ranks_are_sequential(self):
        ranks = [paper["rank"] for paper in (self.payload.get("items") or [])]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))

    def test_archive_index_contains_latest(self):
        index = json.loads(ARCHIVE_INDEX.read_text(encoding="utf-8"))
        self.assertIn(self.payload["date"], [item["date"] for item in index["items"]])
        latest_item = next(item for item in index["items"] if item["date"] == self.payload["date"])
        self.assertEqual(latest_item["candidates"], self.payload["stats"]["candidates"])


if __name__ == "__main__":
    unittest.main()
