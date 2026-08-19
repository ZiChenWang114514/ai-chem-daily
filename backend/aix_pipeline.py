#!/usr/bin/env python3
"""Collect, normalize, score and publish the five AIX每日精读 channels."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable

from daily_digest import Paper, clean_text, fetch_arxiv, fetch_biorxiv, fetch_chemrxiv, load_json, publish_tags, slim_public_item, write_json


SHANGHAI = timezone(timedelta(hours=8))
USER_AGENT = "aix-daily/2.0 (mailto:wangzc@stu.pku.edu.cn)"
CHANNELS = ("aixchem", "aixbio", "aixmath", "aivoices", "engineering")
RESEARCH_CHANNELS = {"aixchem", "aixbio", "aixmath"}
LIMITS = {"aixchem": 16, "aixbio": 16, "aixmath": 16, "aivoices": 10, "engineering": 10}
THRESHOLDS = {"aixchem": 70, "aixbio": 70, "aixmath": 70, "aivoices": 65, "engineering": 65}

CHANNEL_META = {
    "aixchem": ("AI × Chem 每日精选", "预印本、方法、数据集与实验验证的每日精选。"),
    "aixbio": ("AI × Bio 每日精选", "计算生物学、组学、蛋白质与生物医学模型。"),
    "aixmath": ("AI × Math 每日精选", "自动推理、形式化证明、数学智能与基础模型。"),
    "aivoices": ("AI Voices 每日精选", "研究者公开观点、研究发布与重要讨论。"),
    "engineering": ("Engineering 每日精选", "重要框架、模型与工具链的发布说明。"),
}

AI_TERMS = ("artificial intelligence", "machine learning", "deep learning", "foundation model", "language model", "llm", "transformer", "neural", "diffusion", "generative", "representation learning", "reinforcement learning", "agent")
CHEM_TERMS = ("chem", "molecul", "drug", "protein", "ligand", "reaction", "synth", "catal", "material", "crystal", "polymer", "quantum", "force field", "spectroscop", "battery", "peptide")
BIO_TERMS = ("bio", "protein", "genom", "transcript", "single-cell", "single cell", "omics", "rna", "dna", "clinical", "medical", "disease", "drug", "cell", "imaging", "health", "antibody", "enzyme")
MATH_TERMS = ("theorem", "proof", "formal", "mathemat", "reasoning", "lean", "coq", "isabelle", "verification", "logic", "algebra", "geometry", "calculus", "olympiad")
QUALITY_TERMS = ("benchmark", "dataset", "open source", "github", "experimental", "prospective", "clinical", "in vivo", "state-of-the-art", "ablation", "evaluation", "release", "breaking", "security", "performance")

CATEGORIES = {
    "aixchem": [("分子与药物发现", ("drug", "ligand", "molecule", "retrosynth")), ("材料与催化", ("material", "catal", "crystal", "battery", "polymer")), ("结构与生物", ("protein", "enzyme", "rna", "dna")), ("方法与模型", AI_TERMS)],
    "aixbio": [("蛋白质与结构", ("protein", "structure", "antibody", "enzyme")), ("组学与细胞", ("genom", "transcript", "single-cell", "omics", "cell")), ("生物医学与临床", ("clinical", "medical", "disease", "patient", "health")), ("方法与模型", AI_TERMS)],
    "aixmath": [("形式化证明", ("proof", "lean", "coq", "isabelle", "formal")), ("数学推理", ("mathematical reasoning", "olympiad", "theorem", "reasoning")), ("验证与逻辑", ("verification", "logic", "symbolic")), ("方法与模型", AI_TERMS)],
    "aivoices": [("研究发布", ("paper", "research", "release", "model")), ("观点与讨论", ("think", "argue", "discussion", "opinion")), ("工具与实践", ("code", "tool", "github", "tutorial"))],
    "engineering": [("模型与框架", ("model", "framework", "training", "inference")), ("性能与部署", ("performance", "latency", "throughput", "gpu", "deploy")), ("兼容与安全", ("breaking", "security", "compatib", "deprecat")), ("工具链更新", ("release", "feature", "fix"))],
}


GROK_X_ACCOUNT_BATCH = 6


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def http_error_message(exc: urllib.error.HTTPError) -> str:
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")[:400]
    except Exception:
        body = ""
    name = ""
    try:
        payload = json.loads(body) if body else {}
        name = str(payload.get("name") or payload.get("title") or payload.get("message") or "")
    except json.JSONDecodeError:
        name = ""
    if exc.code == 402:
        return "HTTP 402 额度不足"
    if exc.code == 429:
        return "HTTP 429 请求过于频繁"
    if "ChallengeRequired" in body or "ChallengeRequired" in name:
        return f"HTTP {exc.code} 需要人机验证"
    if name:
        return f"HTTP {exc.code} {name}"
    return f"HTTP {exc.code}"


def within_window(value: str, start: date, end: date) -> bool:
    parsed = publication_date(value)
    return parsed is not None and start <= parsed <= end


def openreview_invitation(domain: str) -> str:
    text = clean_text(domain)
    if "/-/" in text:
        return text
    return f"{text}/-/Submission"


def collection_window(run_date: date, last_success: str | None = None) -> tuple[date, date]:
    minimum = 4 if run_date.weekday() == 0 else 3
    start = run_date - timedelta(days=minimum)
    if last_success:
        try:
            prior = datetime.fromisoformat(last_success).astimezone(SHANGHAI).date() - timedelta(days=2)
            start = min(start, prior)
        except ValueError:
            pass
    return start, run_date


def build_x_queries(
    watchlists: dict[str, Any],
    start: date | None = None,
    end: date | None = None,
    account_batch: int = GROK_X_ACCOUNT_BATCH,
    topic_limit: int | None = None,
) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    date_clause = ""
    if start and end:
        date_clause = f" since:{start.isoformat()} until:{(end + timedelta(days=1)).isoformat()}"
    handles = watchlists.get("x_accounts", [])
    for index in range(0, len(handles), account_batch):
        batch = handles[index:index + account_batch]
        queries.append(("accounts", f"({' OR '.join(f'from:{name}' for name in batch)}) -is:retweet{date_clause}"))
    topics = list(watchlists.get("x_topic_queries", []))
    if topic_limit is not None:
        topics = topics[:topic_limit]
    for query in topics:
        text = clean_text(query)
        if date_clause and "since:" not in text:
            text = f"{text}{date_clause}"
        queries.append(("topics", text))
    return queries


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def request_json(url: str, *, headers: dict[str, str] | None = None, method: str = "GET", body: bytes | None = None, timeout: int = 60) -> tuple[dict[str, Any], dict[str, str]]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers, method=method, data=body)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload, {key.lower(): value for key, value in response.headers.items()}


def item_id(source: str, value: str) -> str:
    normalized = re.sub(r"\s+", " ", clean_text(value)).strip().lower()
    return f"{source.lower()}:{normalized}"


def natural_key(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    for name in ("doi", "arxiv_id", "forum_id", "post_id", "release_id"):
        if metadata.get(name):
            return f"{name}:{str(metadata[name]).lower()}"
    return re.sub(r"[?#].*$", "", str(item.get("url") or item.get("id") or "")).rstrip("/").lower()


def paper_to_item(paper: Paper, channel: str) -> dict[str, Any]:
    arxiv_id = paper.id.split(":", 1)[1] if paper.id.startswith("arxiv:") else ""
    status = "preprint" if paper.source in {"arXiv", "bioRxiv", "medRxiv", "ChemRxiv"} else "peer_reviewed"
    return {
        "id": paper.id,
        "channel": channel,
        "related_channels": [],
        "item_type": "paper",
        "source": paper.source,
        "title": paper.title,
        "url": paper.url,
        "published_at": paper.published,
        "updated_at": paper.updated or paper.published,
        "creators": paper.authors,
        "language": "en",
        "abstract_or_text": paper.abstract,
        "summary_zh": "",
        "why_it_matters_zh": "",
        "quality_score": 0,
        "tags": list(paper.tags),
        "evidence_flags": list(paper.evidence_flags),
        "publication_status": status,
        "rank": 0,
        "featured": False,
        "category": "方法与模型",
        "metrics": {},
        "metadata": {"doi": paper.doi, "arxiv_id": arxiv_id},
    }


def keyword_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term in lower]


def choose_category(channel: str, text: str) -> str:
    lower = text.lower()
    choices = CATEGORIES[channel]
    return max(choices, key=lambda pair: sum(term in lower for term in pair[1]))[0]


def score_item(item: dict[str, Any], channel: str) -> float:
    text = f"{item.get('title', '')} {item.get('abstract_or_text', '')}".lower()
    title = str(item.get("title", "")).lower()
    ai = keyword_hits(text, AI_TERMS)
    domain_terms = CHEM_TERMS if channel == "aixchem" else BIO_TERMS if channel == "aixbio" else MATH_TERMS
    domain = keyword_hits(text, domain_terms) if channel in RESEARCH_CHANNELS else []
    quality = keyword_hits(text, QUALITY_TERMS)
    if channel in RESEARCH_CHANNELS:
        if not ai or not domain:
            return 0
        score = 48 + min(18, len(ai) * 3) + min(18, len(domain) * 3) + min(10, len(quality) * 2)
        if any(term in title for term in AI_TERMS):
            score += 4
        if any(term in title for term in domain_terms):
            score += 4
        if len(item.get("abstract_or_text", "")) >= 500:
            score += 3
    elif channel == "aivoices":
        metrics = item.get("metrics") or {}
        engagement = sum(int(metrics.get(name) or 0) for name in ("like_count", "repost_count", "reply_count", "quote_count"))
        score = 54 + min(15, len(ai) * 3) + min(12, len(quality) * 2) + min(15, int(engagement ** 0.5))
        if item.get("source") != "X":
            score += 8
    else:
        score = 55 + min(18, len(ai) * 3) + min(18, len(quality) * 3)
        release_type = (item.get("metadata") or {}).get("release_type")
        score += 5 if release_type == "release" else 0
    item["quality_score"] = min(100, round(score, 1))
    item["category"] = choose_category(channel, text)
    item["tags"] = publish_tags(item["category"])
    item["evidence_flags"] = list(dict.fromkeys([*(item.get("evidence_flags") or []), *quality]))[:6]
    return item["quality_score"]


class Runtime:
    def __init__(self, root: Path, run_date: date):
        self.root = root
        self.run_date = run_date
        self.cache_root = root / "work" / "source-cache"
        self.raw_root = root / "work" / "raw"
        self.state_path = self.cache_root / "state.json"
        self.request_log = self.cache_root / f"requests-{run_date.isoformat()}.jsonl"
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def record_request(self, host: str, source: str, status: str, count: int = 0) -> None:
        record = {"at": utc_now().isoformat(timespec="seconds"), "host": host, "source": source, "status": status, "count": count}
        with self.request_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def cache(self, source: str, factory: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
        path = self.cache_root / source / f"{self.run_date.isoformat()}.json.gz"
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                values = json.load(stream)
            if values:
                return values
        values = factory()
        if not values:
            return values
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            json.dump(values, stream, ensure_ascii=False)
        return values

    def window(self, source: str) -> tuple[date, date]:
        state = load_json(self.state_path, {})
        return collection_window(self.run_date, state.get(source))

    def mark_success(self, source: str, count: int | None = None) -> None:
        if count == 0:
            return
        state = load_json(self.state_path, {})
        state[source] = utc_now().isoformat(timespec="seconds")
        write_json(self.state_path, state)


def shared_papers(runtime: Runtime, source: str) -> list[dict[str, Any]]:
    start, end = runtime.window(source)
    fetcher = fetch_arxiv if source == "arxiv" else fetch_biorxiv
    display = "arXiv" if source == "arxiv" else "bioRxiv"

    def create() -> list[dict[str, Any]]:
        values = [asdict(paper) for paper in fetcher(start, end)]
        status = "ok" if values else "empty"
        runtime.record_request("export.arxiv.org" if source == "arxiv" else "api.biorxiv.org", display, status, len(values))
        runtime.mark_success(source, len(values))
        return values

    return runtime.cache(source, create)


def fetch_medrxiv(runtime: Runtime) -> list[dict[str, Any]]:
    start, end = runtime.window("medrxiv")

    def create() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor = 0
        while True:
            url = f"https://api.biorxiv.org/details/medrxiv/{start}/{end}/{cursor}"
            payload, _ = request_json(url)
            batch = payload.get("collection") or []
            for value in batch:
                doi = clean_text(value.get("doi"))
                results.append(asdict(Paper(
                    id=f"medrxiv:{doi or clean_text(value.get('title'))}", source="medRxiv",
                    title=clean_text(value.get("title")), abstract=clean_text(value.get("abstract")),
                    authors=[part.strip() for part in clean_text(value.get("authors")).split(";") if part.strip()],
                    published=clean_text(value.get("date"))[:10], updated=clean_text(value.get("date"))[:10],
                    url=f"https://www.medrxiv.org/content/{doi}" if doi else "", doi=doi,
                    category=clean_text(value.get("category")), tags=["medRxiv", "clinical"],
                )))
            cursor += len(batch)
            total = int((payload.get("messages") or [{}])[0].get("total") or len(batch))
            if not batch or cursor >= total:
                break
            time.sleep(4)
        runtime.record_request("api.biorxiv.org", "medRxiv", "ok", len(results))
        runtime.mark_success("medrxiv", len(results))
        return results

    return runtime.cache("medrxiv", create)


def fetch_europe_pmc(runtime: Runtime) -> list[dict[str, Any]]:
    start, end = runtime.window("europepmc")

    def create() -> list[dict[str, Any]]:
        query = f"FIRST_PDATE:[{start} TO {end}] AND (OPEN_ACCESS:Y OR SRC:PPR)"
        params = urllib.parse.urlencode({"query": query, "format": "json", "resultType": "core", "pageSize": 1000})
        payload, _ = request_json(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{params}")
        results: list[dict[str, Any]] = []
        for value in payload.get("resultList", {}).get("result", []):
            title = clean_text(value.get("title"))
            abstract = clean_text(value.get("abstractText"))
            if not title:
                continue
            source = "Europe PMC"
            status = "preprint" if value.get("source") == "PPR" else "peer_reviewed"
            authors = [clean_text(node.get("fullName")) for node in (value.get("authorList") or {}).get("author", []) if clean_text(node.get("fullName"))]
            results.append({
                "id": item_id("europepmc", str(value.get("id") or title)), "channel": "aixbio", "related_channels": [],
                "item_type": "paper", "source": source, "title": title,
                "url": f"https://europepmc.org/article/{value.get('source', 'MED')}/{value.get('id', '')}",
                "published_at": clean_text(value.get("firstPublicationDate"))[:10], "updated_at": clean_text(value.get("firstIndexDate"))[:10],
                "creators": authors, "language": "en", "abstract_or_text": abstract,
                "summary_zh": "", "why_it_matters_zh": "", "quality_score": 0, "tags": [status],
                "evidence_flags": ["clinical"] if "clinical" in f"{title} {abstract}".lower() else [],
                "publication_status": status, "rank": 0, "featured": False, "category": "方法与模型", "metrics": {},
                "metadata": {"doi": clean_text(value.get("doi")), "pmid": clean_text(value.get("pmid"))},
            })
        runtime.record_request("www.ebi.ac.uk", "Europe PMC", "ok", len(results))
        runtime.mark_success("europepmc", len(results))
        return results

    return runtime.cache("europepmc", create)


def unwrap(value: Any) -> Any:
    return value.get("value") if isinstance(value, dict) and "value" in value else value


def resolve_openreview_invitation(domain: str, headers: dict[str, str]) -> str:
    invitation = openreview_invitation(domain)
    try:
        payload, _ = request_json(f"https://api2.openreview.net/groups?id={urllib.parse.quote(domain)}", headers=headers)
        groups = payload.get("groups") or []
        if groups:
            content = groups[0].get("content") or {}
            submission = unwrap(content.get("submission_id"))
            if submission:
                return clean_text(submission)
    except urllib.error.HTTPError:
        return invitation
    return invitation


def fetch_openreview(runtime: Runtime, watchlists: dict[str, Any]) -> list[dict[str, Any]]:
    start, end = runtime.window("openreview")

    def create() -> list[dict[str, Any]]:
        username = os.getenv("OPENREVIEW_USERNAME", "")
        password = os.getenv("OPENREVIEW_PASSWORD", "")
        if not username or not password:
            raise RuntimeError("未配置 OpenReview 账号")
        body = json.dumps({"id": username, "password": password, "expiresIn": 86400}).encode()
        try:
            login, _ = request_json("https://api2.openreview.net/login", method="POST", body=body, headers={"Content-Type": "application/json"})
        except urllib.error.HTTPError as exc:
            raise RuntimeError(http_error_message(exc)) from exc
        token = str(login.get("token") or "")
        if not token:
            raise RuntimeError("登录未返回 token")
        headers = {"Authorization": f"Bearer {token}"}
        results: list[dict[str, Any]] = []
        after = ""
        for domain in watchlists.get("openreview_domains", []):
            invitation = resolve_openreview_invitation(domain, headers)
            while True:
                params: dict[str, Any] = {
                    "invitation": invitation,
                    "limit": 200,
                    "sort": "tcdate:desc",
                    "mintcdate": int(datetime.combine(start, datetime.min.time(), tzinfo=SHANGHAI).timestamp() * 1000),
                }
                if after:
                    params["after"] = after
                try:
                    payload, _ = request_json(f"https://api2.openreview.net/notes?{urllib.parse.urlencode(params)}", headers=headers)
                except urllib.error.HTTPError as exc:
                    raise RuntimeError(f"{domain}: {http_error_message(exc)}") from exc
                notes = payload.get("notes") or []
                for note in notes:
                    content = note.get("content") or {}
                    title = clean_text(unwrap(content.get("title")))
                    abstract = clean_text(unwrap(content.get("abstract")))
                    status_text = clean_text(unwrap(content.get("withdrawal_confirmation")) or unwrap(content.get("venue"))).lower()
                    if not title or "withdraw" in status_text:
                        continue
                    published_at = datetime.fromtimestamp((note.get("cdate") or note.get("tcdate") or 0) / 1000, SHANGHAI).date().isoformat()
                    if not within_window(published_at, start, end):
                        continue
                    forum = str(note.get("forum") or note.get("id") or "")
                    results.append({
                        "id": item_id("openreview", forum), "channel": "aixmath", "related_channels": [], "item_type": "paper",
                        "source": "OpenReview", "title": title, "url": f"https://openreview.net/forum?id={forum}",
                        "published_at": published_at,
                        "updated_at": datetime.fromtimestamp((note.get("mdate") or note.get("tmdate") or note.get("tcdate") or 0) / 1000, SHANGHAI).date().isoformat(),
                        "creators": list(unwrap(content.get("authors")) or []), "language": "en", "abstract_or_text": abstract,
                        "summary_zh": "", "why_it_matters_zh": "", "quality_score": 0, "tags": [domain], "evidence_flags": [],
                        "publication_status": clean_text(unwrap(content.get("venue"))) or "public_submission", "rank": 0, "featured": False,
                        "category": "方法与模型", "metrics": {}, "metadata": {"forum_id": forum, "domain": domain, "invitation": invitation},
                    })
                if len(notes) < 200:
                    break
                after = str(notes[-1].get("id") or "")
                time.sleep(12)
            after = ""
            time.sleep(8)
        runtime.record_request("api2.openreview.net", "OpenReview", "ok", len(results))
        runtime.mark_success("openreview", len(results))
        return results

    return runtime.cache("openreview", create)


def fetch_x(runtime: Runtime, watchlists: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    del watchlists

    def create() -> list[dict[str, Any]]:
        raise RuntimeError("未找到 Grok X 检索缓存。请先按 ops/grok/x_harvest_protocol.md 采集")

    results = runtime.cache("x", create)
    if results:
        runtime.record_request("grok.x.search", "X", "ok", len(results))
        runtime.mark_success("x", len(results))
    return results


def parse_feed(raw: bytes, source: str, url: str) -> list[dict[str, Any]]:
    root = ET.fromstring(raw)
    entries = root.findall(".//item") or root.findall("{http://www.w3.org/2005/Atom}entry")
    results = []
    for entry in entries[:50]:
        def text_of(*names: str) -> str:
            for name in names:
                node = entry.find(name)
                if node is not None:
                    href = node.attrib.get("href")
                    return clean_text(href or node.text)
            return ""
        title = text_of("title", "{http://www.w3.org/2005/Atom}title")
        link = text_of("link", "{http://www.w3.org/2005/Atom}link")
        summary = text_of("description", "{http://www.w3.org/2005/Atom}summary", "{http://www.w3.org/2005/Atom}content")
        published = text_of("pubDate", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated")
        if title and link:
            results.append({
                "id": item_id("feed", link), "channel": "aivoices", "related_channels": [], "item_type": "research_blog",
                "source": source, "title": title, "url": link, "published_at": published, "updated_at": published,
                "creators": [source], "language": "en", "abstract_or_text": summary, "summary_zh": "", "why_it_matters_zh": "",
                "quality_score": 0, "tags": ["official blog"], "evidence_flags": [], "publication_status": "official_update",
                "rank": 0, "featured": False, "category": "研究发布", "metrics": {}, "metadata": {"feed_url": url},
            })
    return results


def publication_date(value: str) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        iso = text[:-1] + "+00:00" if text.endswith("Z") else text
        parsed = datetime.fromisoformat(iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(SHANGHAI).date()
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(SHANGHAI).date()
    except (TypeError, ValueError, OverflowError):
        match = re.search(r"\d{4}-\d{2}-\d{2}", text)
        if not match:
            return None
        try:
            return date.fromisoformat(match.group(0))
        except ValueError:
            return None


def fetch_feeds(runtime: Runtime, watchlists: dict[str, Any]) -> list[dict[str, Any]]:
    start, end = runtime.window("feeds")

    def create() -> list[dict[str, Any]]:
        results = []
        for index, feed in enumerate(watchlists.get("research_feeds", [])):
            name, url = feed["name"], feed["url"]
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    batch = [item for item in parse_feed(response.read(), name, url) if within_window(item.get("published_at", ""), start, end)]
                results.extend(batch)
                runtime.record_request(urllib.parse.urlsplit(url).netloc, name, "ok", len(batch))
            except Exception as exc:  # source status is retained while other feeds continue
                runtime.record_request(urllib.parse.urlsplit(url).netloc, name, f"error:{type(exc).__name__}")
            if index + 1 < len(watchlists.get("research_feeds", [])):
                time.sleep(4)
        runtime.mark_success("feeds", len(results))
        return results
    return runtime.cache("feeds", create)


def fetch_github(runtime: Runtime, watchlists: dict[str, Any]) -> list[dict[str, Any]]:
    start, end = runtime.window("github")

    def create() -> list[dict[str, Any]]:
        results = []
        token = os.getenv("GITHUB_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28"} if token else {"X-GitHub-Api-Version": "2022-11-28"}
        for index, repo in enumerate(watchlists.get("github_repositories", [])):
            payload, response_headers = request_json(f"https://api.github.com/repos/{repo}/releases?per_page=30", headers=headers)
            for release in payload if isinstance(payload, list) else []:
                published = clean_text(release.get("published_at"))
                if not within_window(published, start, end):
                    continue
                prerelease = bool(release.get("prerelease"))
                body = clean_text(release.get("body"))
                important = any(term in f"{release.get('name', '')} {body}".lower() for term in QUALITY_TERMS)
                if prerelease and not important:
                    continue
                release_id = str(release.get("id"))
                results.append({
                    "id": item_id("github", release_id), "channel": "engineering", "related_channels": [], "item_type": "software_release",
                    "source": "GitHub Releases", "title": clean_text(release.get("name") or release.get("tag_name")),
                    "url": clean_text(release.get("html_url")), "published_at": published, "updated_at": clean_text(release.get("created_at")),
                    "creators": [repo], "language": "en", "abstract_or_text": body, "summary_zh": "", "why_it_matters_zh": "",
                    "quality_score": 0, "tags": [repo, clean_text(release.get("tag_name"))], "evidence_flags": [],
                    "publication_status": "prerelease" if prerelease else "release", "rank": 0, "featured": False, "category": "工具链更新",
                    "metrics": {}, "metadata": {"repository": repo, "version": clean_text(release.get("tag_name")), "release_id": release_id, "release_type": "prerelease" if prerelease else "release"},
                })
            runtime.record_request("api.github.com", f"GitHub:{repo}", "ok", len(payload) if isinstance(payload, list) else 0)
            retry = int(response_headers.get("retry-after", "0") or 0)
            if index + 1 < len(watchlists.get("github_repositories", [])):
                time.sleep(max(4, min(30, retry or 4)))
        runtime.mark_success("github", len(results))
        return results
    return runtime.cache("github", create)


def deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for item in items:
        key = natural_key(item)
        if key and (key not in found or len(item.get("abstract_or_text", "")) > len(found[key].get("abstract_or_text", ""))):
            found[key] = item
    return list(found.values())


def write_raw(runtime: Runtime, channel: str, items: list[dict[str, Any]], errors: list[str]) -> None:
    folder = runtime.raw_root / channel / f"{runtime.run_date:%Y}" / f"{runtime.run_date:%m}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{runtime.run_date}.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for item in items:
            stream.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
    write_json(folder / f"{runtime.run_date}.manifest.json", {"channel": channel, "date": str(runtime.run_date), "record_count": len(items), "source_errors": errors, "data_file": path.name})


def collect_channel(root: Path, site_root: Path, channel: str, run_date: date) -> dict[str, Any]:
    runtime = Runtime(root, run_date)
    watchlists = load_json(root / "config" / "watchlists.json", {})
    errors: list[str] = []
    sources: dict[str, list[dict[str, Any]]] = {}

    def attempt(name: str, factory: Callable[[], list[dict[str, Any]]]) -> None:
        try:
            sources[name] = factory()
        except urllib.error.HTTPError as exc:
            errors.append(f"{name}: {http_error_message(exc)}")
            runtime.record_request(urllib.parse.urlsplit(exc.url).netloc, name, f"http:{exc.code}")
            sources[name] = []
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {clean_text(exc)}")
            sources[name] = []

    if channel in {"aixchem", "aixbio", "aixmath"}:
        attempt("arXiv", lambda: [paper_to_item(Paper(**value), channel) for value in shared_papers(runtime, "arxiv")])
    if channel in {"aixchem", "aixbio"}:
        attempt("bioRxiv", lambda: [paper_to_item(Paper(**value), channel) for value in shared_papers(runtime, "biorxiv")])
    if channel == "aixchem":
        start, end = runtime.window("chemrxiv")
        def chem_items() -> list[dict[str, Any]]:
            def create() -> list[dict[str, Any]]:
                values = [asdict(value) for value in fetch_chemrxiv(start, end)]
                runtime.record_request("api.crossref.org", "ChemRxiv", "ok", len(values))
                runtime.mark_success("chemrxiv", len(values))
                return values
            return [paper_to_item(Paper(**value), channel) for value in runtime.cache("chemrxiv", create)]
        attempt("ChemRxiv", chem_items)
    elif channel == "aixbio":
        attempt("medRxiv", lambda: [paper_to_item(Paper(**value), channel) for value in fetch_medrxiv(runtime)])
        attempt("Europe PMC", lambda: fetch_europe_pmc(runtime))
    elif channel == "aixmath":
        attempt("OpenReview", lambda: fetch_openreview(runtime, watchlists))
    elif channel == "aivoices":
        attempt("X", lambda: fetch_x(runtime, watchlists))
        attempt("Research blogs", lambda: fetch_feeds(runtime, watchlists))
    elif channel == "engineering":
        attempt("GitHub Releases", lambda: fetch_github(runtime, watchlists))

    raw = deduplicate([item for batch in sources.values() for item in batch])
    write_raw(runtime, channel, raw, errors)
    candidates = []
    for item in raw:
        score = score_item(item, channel)
        if score >= max(45, THRESHOLDS[channel] - 15):
            candidates.append(item)
    candidates.sort(
        key=lambda item: (item["quality_score"], publication_date(item.get("published_at", "")) or date.min),
        reverse=True,
    )
    candidates = candidates[:60]
    for item in candidates:
        item["related_channels"] = [other for other in RESEARCH_CHANNELS if other != channel and score_item(dict(item), other) >= THRESHOLDS[other]]

    channel_root = site_root / "data" / "channels" / channel
    candidate_payload = {"schema_version": "2.0", "date": str(run_date), "channel": channel, "generated_at": utc_now().isoformat(timespec="seconds"), "count": len(candidates), "items": candidates}
    write_json(channel_root / "candidates" / "latest.json", candidate_payload)
    preliminary = [item for item in candidates if item["quality_score"] >= THRESHOLDS[channel]][:LIMITS[channel]]
    for rank, item in enumerate(preliminary, 1):
        item["rank"] = rank
        item["featured"] = rank <= 3
    title, subtitle = CHANNEL_META[channel]
    payload = {
        "schema_version": "2.0", "date": str(run_date), "channel": channel,
        "generated_at": utc_now().isoformat(timespec="seconds"), "title": title, "subtitle": subtitle,
        "window": {"start": str(collection_window(run_date)[0]), "end": str(run_date)},
        "method": "公开来源采集、规则筛选与模型审阅", "method_note": "系统保存当日公开元数据，依据频道主题与证据信号筛选候选，随后由指定模型阅读全文摘要并完成精选。",
        "stats": {"fetched": len(raw), "candidates": len(candidates), "selected": len(preliminary), "sources": {name: len(batch) for name, batch in sources.items()}},
        "source_status": {
            name: {
                "state": "failed" if any(error.startswith(f"{name}:") for error in errors) else ("ok" if batch else "empty"),
                "count": len(batch),
            }
            for name, batch in sources.items()
        },
        "source_errors": errors,
        "items": [slim_public_item(item, include_abstract=True, clip_release=True) for item in preliminary],
    }
    write_json(channel_root / "latest.json", payload)
    write_json(root / "work" / "local-pipeline" / "status" / f"{channel}.json", {"channel": channel, "date": str(run_date), "state": "collected", "updated_at": utc_now().isoformat(timespec="seconds"), "stats": payload["stats"], "source_errors": errors})
    log(f"{channel}: fetched={len(raw)}, candidates={len(candidates)}, preliminary={len(preliminary)}")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel", choices=CHANNELS)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    parser.add_argument("--date", dest="run_date")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_date = date.fromisoformat(args.run_date) if args.run_date else datetime.now(SHANGHAI).date()
    collect_channel(args.root.resolve(), args.site_root.resolve(), args.channel, run_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
