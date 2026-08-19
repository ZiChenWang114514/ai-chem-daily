import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from aix_pipeline import (  # noqa: E402
    Runtime,
    build_x_queries,
    collection_window,
    http_error_message,
    openreview_invitation,
    publication_date,
    within_window,
)
from daily_digest import ARXIV_CATEGORIES, arxiv_category_query, fetch_arxiv, load_json  # noqa: E402
from publish_daily import factual_overview  # noqa: E402


class SourceWindowTests(unittest.TestCase):
    def test_github_utc_evening_counts_as_shanghai_next_day(self):
        self.assertEqual(publication_date("2026-08-16T20:00:00Z"), date(2026, 8, 17))
        self.assertTrue(within_window("2026-08-16T20:00:00Z", date(2026, 8, 17), date(2026, 8, 17)))
        self.assertFalse(within_window("2026-08-16T07:24:37Z", date(2026, 8, 17), date(2026, 8, 17)))
        self.assertTrue(within_window("2026-08-16T07:24:37Z", date(2026, 8, 15), date(2026, 8, 17)))

    def test_monday_window_includes_friday_arxiv(self):
        start, end = collection_window(date(2026, 8, 17))
        self.assertEqual(end, date(2026, 8, 17))
        self.assertLessEqual(start, date(2026, 8, 14))
        start_tue, _ = collection_window(date(2026, 8, 18))
        self.assertEqual(start_tue, date(2026, 8, 15))

    def test_arxiv_query_uses_categories_not_submitted_date_only(self):
        query = arxiv_category_query(ARXIV_CATEGORIES)
        self.assertIn("cat:cs.LG", query)
        self.assertIn("cat:cs.LO", query)
        self.assertIn("cat:math.LO", query)
        self.assertNotIn("submittedDate", query)

    def test_openreview_invitation_defaults(self):
        self.assertEqual(openreview_invitation("TMLR"), "TMLR/-/Submission")
        self.assertEqual(openreview_invitation("ICLR.cc/2026/Conference"), "ICLR.cc/2026/Conference/-/Submission")
        self.assertEqual(openreview_invitation("TMLR/-/Submission"), "TMLR/-/Submission")

    def test_x_queries_are_batched_for_grok(self):
        watchlists = {
            "x_accounts": [f"user{i}" for i in range(34)],
            "x_topic_queries": ["one", "two", "three", "four"],
        }
        queries = build_x_queries(watchlists, date(2026, 8, 16), date(2026, 8, 19))
        kinds = [kind for kind, _ in queries]
        self.assertEqual(kinds.count("topics"), 4)
        self.assertGreaterEqual(kinds.count("accounts"), 6)
        self.assertIn("from:user0", queries[0][1])
        self.assertIn("since:2026-08-16", queries[0][1])
        self.assertIn("until:2026-08-20", queries[0][1])
        self.assertNotIn("api.x.com", queries[0][1])

    def test_http_error_messages_are_explicit(self):
        self.assertIn("额度不足", http_error_message(HTTPError("https://example.com", 402, "Payment Required", hdrs=None, fp=None)))
        self.assertIn("请求过于频繁", http_error_message(HTTPError("https://example.com", 429, "Too Many Requests", hdrs=None, fp=None)))
        self.assertNotIn("Developer Console", http_error_message(HTTPError("https://example.com", 402, "Payment Required", hdrs=None, fp=None)))

    def test_overview_leads_with_real_counts(self):
        channels = [
            {"name": "AI × Chem", "stats": {"selected": 16}},
            {"name": "AI × Bio", "stats": {"selected": 10}},
            {"name": "AI × Math", "stats": {"selected": 0}},
        ]
        text = factual_overview(channels, "今日AI×化学与AI×生物各有16项精选。")
        self.assertTrue(text.startswith("今日精选：AI × Chem 16 项，AI × Bio 10 项，AI × Math 0 项。"))


class PipelineContractTests(unittest.TestCase):
    def test_runner_injects_github_token_and_skips_empty_cache(self):
        runner = (ROOT / "ops" / "run_local_pipeline.ps1").read_text(encoding="utf-8")
        pipeline = (ROOT / "backend" / "aix_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("gh auth token", runner)
        self.assertIn("GITHUB_TOKEN", runner)
        self.assertIn("function Invoke-Python", runner)
        self.assertIn("Write-Host $line", runner)
        self.assertIn("Retry complete; still failed", runner)
        self.assertIn("All channels failed after retry; skip combined publish", runner)
        self.assertIn("$DiffCode -eq 1", runner)
        self.assertIn("git diff failed with exit code", runner)
        self.assertIn("if not values:", pipeline)
        self.assertIn("within_window(published, start, end)", pipeline)
        self.assertIn("x_harvest_protocol.md", runner)
        self.assertIn("function Invoke-GrokVisit", runner)
        self.assertIn("grok.exe", runner)
        self.assertIn("daily_visit_prompt.md", runner)
        self.assertTrue((ROOT / "ops" / "grok" / "daily_visit_prompt.md").exists())
        self.assertTrue((ROOT / "AGENTS.md").exists())
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Codex 不执行 `ops/grok/daily_visit_prompt.md`", agents)
        self.assertIn("仅当当前执行者是 Grok", agents)
        self.assertNotIn("XBearerToken", runner)
        self.assertNotIn("X_BEARER_TOKEN", runner)
        self.assertNotIn("X_BEARER_TOKEN", pipeline)
        self.assertNotIn("api.x.com", pipeline)
        self.assertIn("arXiv API returned no entries", (ROOT / "backend" / "daily_digest.py").read_text(encoding="utf-8"))
        self.assertIn("当日未更新，未纳入本期", (ROOT / "backend" / "publish_daily.py").read_text(encoding="utf-8"))
        self.assertNotIn('published[:10] != runtime.run_date.isoformat()', pipeline)
        self.assertNotIn('submittedDate:[', (ROOT / "backend" / "daily_digest.py").read_text(encoding="utf-8"))

    def test_broken_research_feeds_are_removed(self):
        watchlists = (ROOT / "config" / "watchlists.json").read_text(encoding="utf-8")
        self.assertNotIn("www.anthropic.com/news/rss.xml", watchlists)
        self.assertNotIn("allenai.org/blog/rss.xml", watchlists)
        self.assertIn("importai.substack.com/feed", watchlists)


class EmptyArxivAndSuccessTests(unittest.TestCase):
    def test_empty_arxiv_first_page_is_an_error(self):
        empty = b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        with patch("daily_digest.http_get", return_value=empty):
            with self.assertRaisesRegex(RuntimeError, "no entries"):
                fetch_arxiv(date(2026, 8, 18), date(2026, 8, 18))

    def test_old_arxiv_entries_are_an_empty_window_not_success_page(self):
        atom = (
            b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
            b"<entry><id>http://arxiv.org/abs/2301.00001</id><title>Old</title>"
            b"<summary>Abstract</summary><published>2020-01-01T00:00:00Z</published>"
            b"<updated>2020-01-01T00:00:00Z</updated><author><name>Ada</name></author>"
            b'<category term="cs.LG"/></entry></feed>'
        )
        with patch("daily_digest.http_get", return_value=atom):
            self.assertEqual(fetch_arxiv(date(2026, 8, 18), date(2026, 8, 18)), [])

    def test_mark_success_does_not_advance_on_empty_count(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory), date(2026, 8, 18))
            runtime.mark_success("arxiv", 0)
            self.assertEqual(load_json(runtime.state_path, {}), {})
            runtime.mark_success("arxiv", 3)
            self.assertIn("arxiv", load_json(runtime.state_path, {}))


if __name__ == "__main__":
    unittest.main()
