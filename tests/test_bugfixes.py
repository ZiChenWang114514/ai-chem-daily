import gzip
import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from aix_pipeline import CHANNELS, LIMITS, Runtime, fetch_openreview, fetch_x, publication_date  # noqa: E402
from apply_channel_curation import earlier_channel_keys, main as apply_channel_curation_main  # noqa: E402
from apply_curation import main as apply_curation_main  # noqa: E402
from build_channel_pages import render_channel_page  # noqa: E402
from daily_digest import archive_index_entry, author_line, looks_cjk, parse_date, publish_tags, slim_public_item, upsert_archive_index  # noqa: E402
from hub_publish import build_hub_interfaces  # noqa: E402
from import_intake import publish_generic_digest, safe_channel, safe_date  # noqa: E402
from import_legacy import item_id  # noqa: E402
from publish_daily import build as build_daily  # noqa: E402


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_item(item_id_value: str, title: str, url: str) -> dict:
    return {
        "id": item_id_value,
        "channel": "aixchem",
        "related_channels": [],
        "item_type": "paper",
        "source": "arXiv",
        "title": title,
        "url": url,
        "published_at": "2026-08-16",
        "updated_at": "2026-08-16",
        "creators": ["Ada"],
        "language": "en",
        "abstract_or_text": "abstract",
        "abstract_zh": "这是用于测试的中文摘要译文，长度足够通过校验。",
        "summary_zh": "This Chinese summary is long enough to pass the curation validator.",
        "why_it_matters_zh": "This reason is also long enough to pass.",
        "quality_score": 80,
        "tags": ["方法与模型"],
        "evidence_flags": [],
        "publication_status": "preprint",
        "rank": 1,
        "featured": True,
        "category": "方法与模型",
        "metrics": {},
        "metadata": {},
        "authors": ["Ada"],
        "abstract": "abstract",
        "published": "2026-08-16",
        "author_line": "Ada",
    }


def channel_payload(channel: str, day: str, items: list[dict]) -> dict:
    return {
        "schema_version": "2.0",
        "date": day,
        "channel": channel,
        "stats": {"fetched": len(items), "candidates": len(items), "selected": len(items), "sources": {}},
        "source_errors": [],
        "items": items,
        "papers": items,
    }


class PublishDailyTests(unittest.TestCase):
    def test_dedup_is_memory_only_and_date_comes_from_channels(self):
        shared = sample_item("arxiv:1234", "Shared paper", "https://arxiv.org/abs/1234")
        bio_only = sample_item("arxiv:5678", "Bio only", "https://arxiv.org/abs/5678")
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for channel in CHANNELS:
                items = [dict(shared, channel=channel)]
                if channel == "aixbio":
                    items.append(dict(bio_only, channel=channel))
                write_json(site / "data" / "channels" / channel / "latest.json", channel_payload(channel, "2026-08-16", items))
            before = {
                channel: (site / "data" / "channels" / channel / "latest.json").read_text(encoding="utf-8")
                for channel in CHANNELS
            }
            payload = build_daily(site, None, "https://example.com/")
            self.assertEqual(payload["date"], "2026-08-16")
            for channel in CHANNELS:
                self.assertEqual(
                    (site / "data" / "channels" / channel / "latest.json").read_text(encoding="utf-8"),
                    before[channel],
                )
            home_ids = [item["id"] for channel in payload["channels"] for item in channel["items"]]
            self.assertEqual(home_ids.count("arxiv:1234"), 1)
            archive = json.loads((site / "data" / "daily" / "archive" / "2026-08-16.json").read_text(encoding="utf-8"))
            archive_ids = [item["id"] for channel in archive["channels"] for item in channel["items"]]
            self.assertIn("arxiv:5678", archive_ids)
            index = json.loads((site / "data" / "daily" / "archive" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["items"][0]["date"], "2026-08-16")

    def test_stale_channel_items_are_not_leaked_into_today(self):
        today = sample_item("arxiv:today", "Today paper", "https://arxiv.org/abs/today")
        stale = sample_item("arxiv:stale", "Yesterday paper", "https://arxiv.org/abs/stale")
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for channel in CHANNELS:
                day = "2026-08-17" if channel == "aixmath" else "2026-08-18"
                item = stale if channel == "aixmath" else today
                write_json(site / "data" / "channels" / channel / "latest.json", channel_payload(channel, day, [item]))
            payload = build_daily(site, None, "https://example.com/")
            self.assertEqual(payload["date"], "2026-08-18")
            by_id = {channel["id"]: channel for channel in payload["channels"]}
            self.assertEqual(by_id["aixmath"]["items"], [])
            self.assertEqual(by_id["aixmath"]["stats"]["selected"], 0)
            self.assertIn("当日未更新，未纳入本期", by_id["aixmath"]["source_errors"])
            home_ids = [item["id"] for channel in payload["channels"] for item in channel["items"]]
            self.assertNotIn("arxiv:stale", home_ids)
            self.assertIn("arxiv:today", home_ids)


class ApplyCurationTests(unittest.TestCase):
    def _prepare(self, site: Path, candidate_key: str = "items", selected_count: int = 6) -> Path:
        papers = [
            sample_item(f"arxiv:{index}", f"Paper {index}", f"https://arxiv.org/abs/{index}")
            for index in range(1, selected_count + 1)
        ]
        latest = {
            "date": "2026-08-18",
            "title": "AI × Chem 每日预印本精选",
            "overview_zh": "测试总览",
            "stats": {"fetched": len(papers), "candidates": len(papers), "selected": 0, "topics": {}, "sources": {}},
            "papers": [],
        }
        write_json(site / "data" / "latest.json", latest)
        write_json(site / "data" / "candidates" / "latest.json", {candidate_key: papers})
        selected = [
            {
                "id": paper["id"],
                "category": "方法与模型",
                "summary_zh": paper["summary_zh"],
                "why_it_matters_zh": paper["why_it_matters_zh"],
                "abstract_zh": paper["abstract_zh"],
                "quality_score": 80,
                "tags": ["方法与模型"],
            }
            for paper in papers
        ]
        curation_path = site / "curation.json"
        write_json(curation_path, {"date": "2026-08-18", "selected": selected})
        return curation_path

    def test_accepts_schema_v2_items_and_inserts_archive_index(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            curation = self._prepare(site, "items", 6)
            argv = ["apply_curation.py", str(curation), "--site-root", str(site)]
            previous = sys.argv
            sys.argv = argv
            try:
                self.assertEqual(apply_curation_main(), 0)
            finally:
                sys.argv = previous
            latest = json.loads((site / "data" / "latest.json").read_text(encoding="utf-8"))
            index = json.loads((site / "data" / "archive" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["stats"]["selected"], 6)
            self.assertEqual(index["items"][0]["date"], "2026-08-18")
            self.assertEqual(index["items"][0]["selected"], 6)
            self.assertEqual(index["items"][0]["fetched"], 6)
            self.assertEqual(index["items"][0]["href"], "data/channels/aixchem/archive/2026-08-18.json")
            self.assertEqual(index["schema_version"], "2.0")

    def test_rejects_more_than_site_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            curation = self._prepare(site, "papers", LIMITS["aixchem"] + 1)
            argv = ["apply_curation.py", str(curation), "--site-root", str(site)]
            previous = sys.argv
            sys.argv = argv
            try:
                with self.assertRaises(ValueError):
                    apply_curation_main()
            finally:
                sys.argv = previous


class IntakeSafetyTests(unittest.TestCase):
    def test_digest_missing_channel_raises_not_keyerror(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            with self.assertRaises(ValueError):
                publish_generic_digest(site, {"intake_type": "digest", "items": []}, {"number": "1", "url": ""})

    def test_digest_missing_date_does_not_keyerror(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            publish_generic_digest(
                site,
                {"channel": "aixmath", "items": [{"title": "A", "url": "https://example.com", "summary_zh": "示例"}]},
                {"number": "1", "url": ""},
            )
            latest = json.loads((site / "data" / "channels" / "aixmath" / "latest.json").read_text(encoding="utf-8"))
            self.assertRegex(latest["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_digest_uses_supplied_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            publish_generic_digest(
                site,
                {"channel": "aixmath", "date": "2026-08-18", "items": [{"title": "A", "url": "https://example.com", "summary_zh": "示例"}]},
                {"number": "1", "url": ""},
            )
            latest = json.loads((site / "data" / "channels" / "aixmath" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(latest["date"], "2026-08-18")

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            safe_channel("../etc")
        with self.assertRaises(ValueError):
            safe_channel("aixchem/../../secret")
        with self.assertRaises(ValueError):
            safe_date("2026-13-45")
        with self.assertRaises(ValueError):
            safe_date("not-a-date")


class DailyArchiveContractTests(unittest.TestCase):
    def test_home_history_dates_have_archive_files(self):
        daily = ROOT / "public" / "data" / "daily"
        index = json.loads((daily / "archive" / "index.json").read_text(encoding="utf-8"))
        dates = {item["date"] for item in index["items"]}
        self.assertIn("2026-08-17", dates)
        self.assertIn("2026-08-18", dates)
        for item in index["items"]:
            archive = json.loads((daily / "archive" / f"{item['date']}.json").read_text(encoding="utf-8"))
            listed = sum(len(channel.get("items") or channel.get("papers") or []) for channel in archive.get("channels", []))
            self.assertEqual(archive["date"], item["date"])
            self.assertEqual(item["selected"], listed)
        latest = json.loads((daily / "latest.json").read_text(encoding="utf-8"))
        today_archive = json.loads((daily / "archive" / f"{latest['date']}.json").read_text(encoding="utf-8"))
        latest_count = sum(len(channel.get("items") or []) for channel in latest.get("channels", []))
        archive_count = sum(len(channel.get("items") or []) for channel in today_archive.get("channels", []))
        self.assertEqual(archive_count, latest_count)
        self.assertEqual(latest_count, sum(int(channel["stats"]["selected"]) for channel in latest["channels"]))
        for channel in latest["channels"]:
            for item in channel.get("items") or []:
                self.assertNotIn("abstract", item)
                self.assertNotIn("abstract_or_text", item)
                self.assertNotIn("abstract_zh", item)
                self.assertNotIn("papers", channel)
        for channel in today_archive["channels"]:
            for item in channel.get("items") or []:
                self.assertNotIn("abstract", item)
                if item.get("abstract_or_text"):
                    self.assertTrue(item.get("abstract_zh"), item.get("id"))
                if item.get("item_type") == "software_release":
                    self.assertLessEqual(len(item.get("abstract_or_text") or ""), 520)
                    self.assertLessEqual(len(item.get("abstract_zh") or ""), 520)


class LegacyImportTests(unittest.TestCase):
    def test_old_arxiv_ids_keep_archive_prefix(self):
        self.assertEqual(item_id("https://arxiv.org/abs/solv-int/9901001v1", "arXiv"), "arxiv:solv-int/9901001")
        self.assertEqual(item_id("https://arxiv.org/abs/2301.12345v12", "arXiv"), "arxiv:2301.12345")
        self.assertEqual(item_id("https://arxiv.org/abs/math/0309136v1", "arXiv"), "arxiv:math/0309136")


class DateParsingTests(unittest.TestCase):
    def test_parse_date_rejects_year_only_and_invalid_calendar(self):
        self.assertEqual(parse_date({"date-parts": [[2026]]}), "")
        self.assertEqual(parse_date({"date-parts": [[2026, 8, 16]]}), "2026-08-16")
        self.assertEqual(parse_date("2026"), "")
        self.assertEqual(parse_date("2026-13-45"), "")
        self.assertEqual(parse_date("Published 2026-08-16T00:00:00Z"), "2026-08-16")

    def test_publication_date_does_not_raise_on_invalid_iso(self):
        self.assertIsNone(publication_date("2026-13-45"))
        self.assertIsNone(publication_date("not-a-date"))
        self.assertEqual(publication_date("Mon, 17 Aug 2026 12:00:00 GMT"), date(2026, 8, 17))
        self.assertEqual(publication_date("2026-08-16T20:00:00Z"), date(2026, 8, 17))


class CredentialCacheTests(unittest.TestCase):
    def test_openreview_and_x_use_cache_without_credentials(self):
        previous = {
            name: os.environ.pop(name, None)
            for name in ("OPENREVIEW_USERNAME", "OPENREVIEW_PASSWORD", "X_BEARER_TOKEN")
        }
        try:
            with tempfile.TemporaryDirectory() as directory:
                runtime = Runtime(Path(directory), date(2026, 8, 18))
                openreview_path = runtime.cache_root / "openreview" / "2026-08-18.json.gz"
                x_path = runtime.cache_root / "x" / "2026-08-18.json.gz"
                openreview_path.parent.mkdir(parents=True, exist_ok=True)
                x_path.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(openreview_path, "wt", encoding="utf-8") as stream:
                    json.dump([{"id": "openreview:cached"}], stream)
                with gzip.open(x_path, "wt", encoding="utf-8") as stream:
                    json.dump([{"id": "x:cached"}], stream)
                self.assertEqual(fetch_openreview(runtime, {"openreview_domains": []})[0]["id"], "openreview:cached")
                self.assertEqual(fetch_x(runtime, {"x_accounts": [], "x_topic_queries": []})[0]["id"], "x:cached")
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


class ChannelCurationDedupTests(unittest.TestCase):
    def test_skips_items_already_claimed_by_earlier_channel(self):
        shared = sample_item("arxiv:shared", "Shared", "https://arxiv.org/abs/shared")
        bio_only = sample_item("arxiv:bio", "Bio only", "https://arxiv.org/abs/bio")
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            write_json(site / "data" / "channels" / "aixchem" / "latest.json", channel_payload("aixchem", "2026-08-18", [shared]))
            write_json(site / "data" / "channels" / "aixbio" / "latest.json", channel_payload("aixbio", "2026-08-18", []))
            write_json(
                site / "data" / "channels" / "aixbio" / "candidates" / "latest.json",
                {"items": [dict(shared, channel="aixbio"), dict(bio_only, channel="aixbio")]},
            )
            curation = site / "bio.json"
            write_json(curation, {
                "date": "2026-08-18",
                "channel": "aixbio",
                "selected": [
                    {"id": "arxiv:shared", "category": "方法与模型", "summary_zh": shared["summary_zh"], "why_it_matters_zh": shared["why_it_matters_zh"], "abstract_zh": shared["abstract_zh"], "quality_score": 80, "tags": []},
                    {"id": "arxiv:bio", "category": "方法与模型", "summary_zh": bio_only["summary_zh"], "why_it_matters_zh": bio_only["why_it_matters_zh"], "abstract_zh": bio_only["abstract_zh"], "quality_score": 80, "tags": []},
                ],
            })
            claimed = earlier_channel_keys(site, "aixbio", "2026-08-18")
            self.assertTrue(claimed)
            previous = sys.argv
            sys.argv = ["apply_channel_curation.py", "aixbio", str(curation), "--site-root", str(site)]
            try:
                self.assertEqual(apply_channel_curation_main(), 0)
            finally:
                sys.argv = previous
            latest = json.loads((site / "data" / "channels" / "aixbio" / "latest.json").read_text(encoding="utf-8"))
            ids = [item["id"] for item in latest["items"]]
            self.assertEqual(ids, ["arxiv:bio"])
            self.assertEqual(latest["stats"]["selected"], 1)
            self.assertFalse((site / "data" / "daily" / "latest.json").exists())

    def test_standalone_curation_refreshes_email_without_daily_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            item = sample_item("arxiv:1", "Paper", "https://arxiv.org/abs/1")
            for channel in CHANNELS:
                write_json(site / "data" / "channels" / channel / "latest.json", channel_payload(channel, "2026-08-18", [item] if channel == "aixchem" else []))
            write_json(site / "data" / "channels" / "aixchem" / "candidates" / "latest.json", {"items": [item]})
            curation = site / "chem.json"
            write_json(curation, {
                "date": "2026-08-18",
                "channel": "aixchem",
                "selected": [{
                    "id": "arxiv:1",
                    "category": "方法与模型",
                    "summary_zh": item["summary_zh"],
                    "why_it_matters_zh": item["why_it_matters_zh"],
                    "abstract_zh": item["abstract_zh"],
                    "quality_score": 80,
                    "tags": ["方法与模型"],
                }],
            })
            previous = sys.argv
            sys.argv = ["apply_channel_curation.py", "aixchem", str(curation), "--site-root", str(site)]
            try:
                self.assertEqual(apply_channel_curation_main(), 0)
            finally:
                sys.argv = previous
            self.assertTrue((site / "email" / "latest.html").exists())
            self.assertFalse((site / "data" / "daily" / "latest.json").exists())


class ChannelPageTests(unittest.TestCase):
    def test_rewrite_requires_home_markers_and_injects_channel(self):
        source = (
            '<body data-page="home" data-root="">'
            '<a href="assets/x.css"></a>'
            '<img src="assets/art/hero.jpg" srcset="assets/art/hero.webp">'
            '<link href="data/daily/latest.json">'
        )
        page = render_channel_page(source, "aixmath")
        self.assertIn('data-channel="aixmath"', page)
        self.assertIn('href="../../assets/x.css"', page)
        self.assertIn("assets/art/aixmath.webp", page)
        self.assertIn("../../data/channels/aixmath/latest.json", page)
        self.assertIn("../../assets/collection.js", render_channel_page('<body data-page="home" data-root=""><script src="assets/collection.js"></script>', "aixmath"))
        self.assertIn("../../library/", render_channel_page('<body data-page="home" data-root=""><a href="library/">收藏</a>', "aixmath"))
        self.assertIn('aria-label="AIxDaily 首页"', render_channel_page('<body data-page="home" data-root=""><a href="./" aria-label="AIxDaily 首页">AIxDaily</a>', "aixmath"))
        with self.assertRaises(ValueError):
            render_channel_page("<body></body>", "aixmath")

    def test_real_home_shell_marks_current_channel_before_js(self):
        source = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        page = render_channel_page(source, "aixchem")
        self.assertIn('data-channel="aixchem"', page)
        self.assertIn('id="eyebrow">AI × Chem', page)
        self.assertIn('id="hero-title">化学', page)
        self.assertIn('class="channel-nav__item is-active" href="../aixchem/" aria-current="page"', page)
        self.assertNotIn('class="channel-nav__item is-active" href="../../"', page)
        self.assertIn("abstract-summary-label", page)


class LibraryPageTests(unittest.TestCase):
    def test_library_page_is_local_first_and_linked(self):
        library = (ROOT / "public" / "library" / "index.html").read_text(encoding="utf-8")
        home = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "public" / "assets" / "app.js").read_text(encoding="utf-8")
        collection = (ROOT / "public" / "assets" / "collection.js").read_text(encoding="utf-8")
        self.assertIn('data-page="library"', library)
        self.assertIn("本机", library)
        self.assertIn("不需要登录", library)
        self.assertIn('id="channel-rail"', library)
        self.assertIn("按频道", library)
        self.assertIn('href="library/"', home)
        self.assertIn("save-button", home)
        self.assertIn("note-field", home)
        self.assertIn("abstract-lang", home)
        self.assertIn("assets/collection.js", home)
        self.assertIn("aix-daily.collection.v1", collection)
        self.assertIn("CHANNEL_ORDER", collection)
        self.assertIn("UNTAGGED_LABEL", script)
        self.assertIn("已取消收藏，笔记仍留在本机", script)
        self.assertIn("全部收藏", script)
        self.assertIn("hydrateHomeAbstracts", script)
        self.assertIn("ensureHomeAbstracts", script)
        self.assertIn("scheduleActivityLoad", script)
        self.assertIn("window.displayTitle", script)
        self.assertIn("formatTitleHtml", script)
        self.assertIn("setRichTitle", script)
        self.assertIn("bindDebouncedSearch", script)
        self.assertIn("收起摘要", script)
        self.assertIn("itemAnchor", script)
        self.assertIn("formatAuthorLine", script)
        self.assertIn("HUB_SOURCES", script)
        self.assertIn("medRxiv", script)
        self.assertIn("GitHub Releases", script)
        self.assertIn("copyItemLink", script)
        self.assertIn("ArrowLeft", script)
        self.assertIn("copy-link", home)
        self.assertIn("data-theme-button", home)
        self.assertIn("assets/theme.js", home)
        self.assertIn("item.summary_zh", script)
        self.assertIn("channel_name", script)
        self.assertNotIn("item.category = channel.name", script)
        self.assertNotIn("window.confirm", script)


class FrontendPerformanceTests(unittest.TestCase):
    def test_pages_preload_and_avoid_blocking_cjk_font(self):
        home = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
        task = (ROOT / "public" / "task" / "index.html").read_text(encoding="utf-8")
        self.assertIn('fetchpriority="high"', home)
        self.assertIn("assets/art/hero.webp", home)
        self.assertIn('rel="preload" as="fetch" href="data/daily/latest.json"', home)
        self.assertIn('rel="preload" as="script" href="assets/app.js"', home)
        self.assertNotIn("data/daily/archive/", home)
        self.assertIn("aix-daily.theme.v1", home)
        self.assertNotIn("fonts.googleapis.com", home)
        self.assertNotIn("fonts.gstatic.com", home)
        self.assertNotIn("Noto+Serif+SC", home)
        self.assertIn("empty-art-webp", home)
        self.assertNotIn("no-store", (ROOT / "public" / "assets" / "app.js").read_text(encoding="utf-8"))
        self.assertNotIn("no-store", task)
        self.assertIn("hero.webp", task)
        self.assertIn("AIxDaily", home)
        self.assertIn('id="hero-title">今日研究更新', home)
        self.assertIn('id="channel-title">频道', home)
        self.assertIn("history-button__chevron", home)
        self.assertNotIn(">⌄</span>", home)

    def test_display_images_have_webp_companions(self):
        art = ROOT / "public" / "assets" / "art"
        for name in ("hero", "empty", "aixchem", "aixbio", "aixmath", "aivoices", "engineering"):
            webp = art / f"{name}.webp"
            jpeg = art / f"{name}.jpg"
            self.assertTrue(webp.exists(), webp)
            self.assertTrue(jpeg.exists(), jpeg)
            self.assertLess(webp.stat().st_size, 80_000)
            self.assertLess(jpeg.stat().st_size, 80_000)


class AuthorLineTests(unittest.TestCase):
    def test_author_line_keeps_every_name(self):
        names = [
            "Pedro de Sena Murteira Pinheiro",
            "Jefferson Muniz Alves da Silva",
            "Bárbara da Silva Mascarenhas de Jesus",
            "Daniel Alencar Rodrigues",
            "Lídia Moreira Lima",
        ]
        self.assertEqual(author_line(names), ", ".join(names))
        self.assertNotIn("等", author_line(names))


class ArchiveIndexContractTests(unittest.TestCase):
    def test_shared_helper_writes_schema_v2_with_fetched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            upsert_archive_index(path, archive_index_entry("2026-08-18", selected=10, candidates=20, fetched=30))
            index = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(index["schema_version"], "2.0")
            self.assertEqual(index["items"][0]["href"], "data/channels/aixchem/archive/2026-08-18.json")
            self.assertEqual(index["items"][0]["fetched"], 30)

    def test_task_page_distinguishes_partial_state(self):
        text = (ROOT / "public" / "task" / "index.html").read_text(encoding="utf-8")
        self.assertIn("部分频道已更新", text)
        self.assertIn("partial:", text)


class PublishTagAndPayloadTests(unittest.TestCase):
    def test_looks_cjk_requires_enough_han_characters(self):
        self.assertFalse(looks_cjk("abstract"))
        self.assertFalse(looks_cjk("This English abstract mentions 模型 once."))
        self.assertTrue(looks_cjk("这是一段足够长的中文摘要，用于判断文本是否已经是中文。"))

    def test_channel_curation_requires_chinese_abstract(self):
        shared = sample_item("arxiv:need-zh", "Need zh", "https://arxiv.org/abs/need-zh")
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            write_json(site / "data" / "channels" / "aixchem" / "latest.json", channel_payload("aixchem", "2026-08-18", []))
            write_json(site / "data" / "channels" / "aixchem" / "candidates" / "latest.json", {"items": [shared]})
            curation = site / "chem.json"
            write_json(curation, {
                "date": "2026-08-18",
                "channel": "aixchem",
                "selected": [{
                    "id": "arxiv:need-zh",
                    "category": "方法与模型",
                    "summary_zh": shared["summary_zh"],
                    "why_it_matters_zh": shared["why_it_matters_zh"],
                    "quality_score": 80,
                    "tags": ["方法与模型"],
                }],
            })
            previous = sys.argv
            sys.argv = ["apply_channel_curation.py", "aixchem", str(curation), "--site-root", str(site)]
            try:
                with self.assertRaises(ValueError):
                    apply_channel_curation_main()
            finally:
                sys.argv = previous

    def test_publish_tags_keep_chinese_and_drop_stems(self):
        self.assertEqual(
            publish_tags("分子与药物发现", ["chem", "molecul", "神经母细胞瘤", "ggml-org/llama.cpp", "b10448", "jax-v0.11.1"]),
            ["分子与药物发现", "神经母细胞瘤"],
        )

    def test_slim_item_drops_abstract_and_clips_release(self):
        item = slim_public_item(
            {
                "title": "b10448",
                "abstract": "dup",
                "abstract_or_text": "a" * 900,
                "abstract_zh": "这是软件发布说明的中文译文。" + ("甲" * 600),
                "category": "工具链更新",
                "tags": ["ggml-org/llama.cpp", "b10448"],
                "item_type": "software_release",
                "source": "GitHub Releases",
            },
            include_abstract=True,
            clip_release=True,
        )
        self.assertNotIn("abstract", item)
        self.assertLessEqual(len(item["abstract_or_text"]), 520)
        self.assertLessEqual(len(item["abstract_zh"]), 520)
        self.assertEqual(item["tags"], ["工具链更新"])
        home_item = slim_public_item(item, include_abstract=False)
        self.assertNotIn("abstract_or_text", home_item)
        self.assertNotIn("abstract_zh", home_item)

    def test_pipeline_commits_library(self):
        runner = (ROOT / "ops" / "run_local_pipeline.ps1").read_text(encoding="utf-8")
        self.assertIn("public/library", runner)

    def test_channel_latest_has_no_papers_duplicate(self):
        latest = json.loads((ROOT / "public" / "data" / "channels" / "engineering" / "latest.json").read_text(encoding="utf-8"))
        self.assertIn("items", latest)
        self.assertNotIn("papers", latest)
        for item in latest.get("items") or []:
            self.assertNotIn("abstract", item)
            if item.get("abstract_or_text"):
                self.assertTrue(item.get("abstract_zh"), item.get("id"))


class HubFreshnessTests(unittest.TestCase):
    def test_partial_when_only_some_channels_are_today(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            config = {
                "hub": {"timezone": "Asia/Shanghai"},
                "channels": [
                    {"id": channel, "status": "active", "latest_path": f"data/channels/{channel}/latest.json", "archive_path": f"data/channels/{channel}/archive/index.json"}
                    for channel in CHANNELS
                ],
            }
            config_path = site / "channels.json"
            write_json(config_path, config)
            today = datetime.now(timezone(timedelta(hours=8))).date()
            yesterday = (today - timedelta(days=1)).isoformat()
            for index, channel in enumerate(CHANNELS):
                day = today.isoformat() if index == 0 else yesterday
                write_json(site / "data" / "channels" / channel / "latest.json", {"date": day, "stats": {}, "source_errors": []})
                write_json(site / "data" / "channels" / channel / "archive" / "index.json", {"items": []})
            result = build_hub_interfaces(site, config_path, "https://example.com/")
            self.assertEqual(result["status"]["state"], "partial")
            self.assertEqual(result["status"]["expected_date"], today.isoformat())


if __name__ == "__main__":
    unittest.main()
