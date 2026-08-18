#!/usr/bin/env python3
"""Build the AI x Chem preprint digest from public metadata APIs."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


USER_AGENT = "ai-x-daily/1.0 (mailto:wangzc@stu.pku.edu.cn)"
ARXIV_API = "https://export.arxiv.org/api/query"
BIORXIV_API = "https://api.biorxiv.org/details/biorxiv"
CROSSREF_API = "https://api.crossref.org/prefixes/10.26434/works"
EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
ARXIV_CATEGORIES = (
    "cs.LG",
    "cs.AI",
    "cs.CL",
    "cs.NE",
    "stat.ML",
    "cs.LO",
    "cs.FL",
    "cs.SC",
    "math.LO",
    "cs.CE",
    "physics.chem-ph",
    "q-bio.BM",
    "q-bio.GN",
    "q-bio.MN",
    "q-bio.QM",
    "q-bio.NC",
)

AI_TERMS = {
    "artificial intelligence": 6,
    "machine learning": 6,
    "deep learning": 6,
    "foundation model": 7,
    "large language model": 7,
    "language model": 5,
    "graph neural": 7,
    "neural network": 5,
    "generative model": 6,
    "diffusion model": 7,
    "transformer": 5,
    "representation learning": 5,
    "reinforcement learning": 6,
    "active learning": 5,
    "bayesian optimization": 5,
    "computer vision": 4,
    "natural language processing": 4,
    "neural potential": 7,
    "machine-learned potential": 7,
    "machine learning potential": 7,
    "equivariant": 4,
    "embedding": 3,
    "agentic": 5,
    " ai agent": 6,
    " llm": 6,
    " gnn": 6,
}

CHEM_TERMS = {
    "molecule": 4,
    "molecular": 4,
    "chemistry": 5,
    "chemical": 4,
    "reaction": 4,
    "synthesis": 5,
    "retrosynthesis": 7,
    "catalyst": 5,
    "catalysis": 5,
    "polymer": 4,
    "material": 3,
    "crystal": 4,
    "protein": 4,
    "ligand": 5,
    "drug": 5,
    "therapeutic": 4,
    "antibody": 4,
    "enzyme": 4,
    "genome": 3,
    "single-cell": 3,
    "omics": 3,
    "quantum chemistry": 7,
    "density functional": 4,
    "force field": 6,
    "potential energy": 4,
    "spectroscopy": 4,
    "electrolyte": 4,
    "battery": 3,
    "peptide": 4,
    "rna": 3,
    "dna": 3,
    "biomolecular": 4,
}

QUALITY_TERMS = {
    "benchmark": 4,
    "open source": 3,
    "code": 2,
    "dataset": 3,
    "prospective": 4,
    "experimental validation": 5,
    "in vivo": 3,
    "state-of-the-art": 3,
    "out-of-distribution": 3,
    "generalization": 2,
    "ablation": 2,
    "uncertainty": 2,
    "large-scale": 2,
}

TOPIC_RULES = {
    "分子与药物发现": ("drug", "ligand", "therapeutic", "antibody", "retrosynthesis", "synthesis planning", "molecule generation"),
    "结构与生物": ("protein", "enzyme", "rna", "dna", "single-cell", "genome", "antibody", "biomolecular"),
    "材料与催化": ("material", "catal", "crystal", "battery", "electrolyte", "polymer", "perovskite"),
    "方法与模型": ("model", "learning", "neural", "transformer", "diffusion", "foundation", "benchmark", "dataset"),
}

SOURCE_ORDER = {"arXiv": 0, "bioRxiv": 1, "ChemRxiv": 2}


@dataclass
class Paper:
    id: str
    source: str
    title: str
    abstract: str
    authors: list[str]
    published: str
    updated: str
    url: str
    doi: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    relevance_score: float = 0.0
    quality_score: float = 0.0
    summary_zh: str = ""
    why_it_matters_zh: str = ""
    evidence_flags: list[str] = field(default_factory=list)
    rank: int = 0
    featured: bool = False


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\$+", "", text)
    return re.sub(r"\s+", " ", text).strip()


CJK_RE = re.compile(r"[\u3400-\u9fff]")


def looks_cjk(value: Any) -> bool:
    text = clean_text(value)
    if not text:
        return False
    marks = len(CJK_RE.findall(text))
    return marks >= 8 and marks / max(len(text), 1) >= 0.18


SITE_NAME = "AIX每日精读"
SITE_TITLE = "AIX每日精读"
RELEASE_ABSTRACT_LIMIT = 500
JUNK_TAG_STEMS = {
    "chem",
    "molecul",
    "neural",
    "synth",
    "bio",
    "protein",
    "drug",
    "llm",
    "transformer",
    "agent",
    "diffusion",
    "quantum",
    "cell",
    "formal",
    "proof",
    "lean",
    "release",
    "model",
    "framework",
    "github",
    "preprint",
    "chemrxiv",
    "medrxiv",
    "biorxiv",
    "arxiv",
    "peer_reviewed",
    "official blog",
    "accounts",
    "topics",
}


def keep_publish_tag(tag: str, *, category: str = "") -> bool:
    text = clean_text(tag)
    if not text:
        return False
    if category and text == category:
        return True
    if re.search(r"[\u4e00-\u9fff]", text):
        return True
    lower = text.lower()
    if lower in JUNK_TAG_STEMS:
        return False
    if "/" in text:
        return False
    if re.search(r"(?:^|[-_ ])(?:v?\d+\.\d+|\bb\d{3,}\b)", lower):
        return False
    return True


def publish_tags(category: str, reviewed: list[str] | None = None) -> list[str]:
    tags: list[str] = []
    for tag in [category, *(reviewed or [])]:
        text = clean_text(tag)
        if not text or text in tags or not keep_publish_tag(text, category=category or ""):
            continue
        tags.append(text)
    return tags[:6]


def clip_release_text(text: str, limit: int = RELEASE_ABSTRACT_LIMIT) -> str:
    value = clean_text(text)
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "…"


def is_release_item(item: dict[str, Any]) -> bool:
    return item.get("item_type") == "software_release" or item.get("source") == "GitHub Releases"


HOME_ITEM_DROP = {
    "abstract",
    "abstract_or_text",
    "abstract_zh",
    "authors",
    "creators",
    "evidence_flags",
    "featured",
    "language",
    "metadata",
    "metrics",
    "publication_status",
    "quality_score",
    "related_channels",
    "updated_at",
}


def resolved_abstract_zh(item: dict[str, Any], source: str) -> str:
    text = clean_text(item.get("abstract_zh"))
    if text:
        return text
    if looks_cjk(source):
        return clean_text(source)
    return ""


def slim_public_item(item: dict[str, Any], *, include_abstract: bool = True, clip_release: bool = False) -> dict[str, Any]:
    drop = {"abstract"} if include_abstract else HOME_ITEM_DROP
    out = {key: value for key, value in item.items() if key not in drop}
    category = clean_text(out.get("category"))
    out["tags"] = publish_tags(category, out.get("tags") or [])
    if include_abstract:
        text = out.get("abstract_or_text") or item.get("abstract") or ""
        zh = resolved_abstract_zh(item, text)
        if clip_release and is_release_item(out):
            text = clip_release_text(text)
            zh = clip_release_text(zh)
        out["abstract_or_text"] = text
        if zh:
            out["abstract_zh"] = zh
        else:
            out.pop("abstract_zh", None)
    else:
        out.pop("abstract_or_text", None)
        out.pop("abstract_zh", None)
    return out


def slim_channel_payload(payload: dict[str, Any], *, include_abstract: bool = True, clip_release: bool = True) -> dict[str, Any]:
    items = [
        slim_public_item(item, include_abstract=include_abstract, clip_release=clip_release)
        for item in (payload.get("items") or payload.get("papers") or [])
    ]
    out = dict(payload)
    out["items"] = items
    out.pop("papers", None)
    return out


def slim_daily_payload(payload: dict[str, Any], *, include_abstract: bool, clip_release: bool = True) -> dict[str, Any]:
    out = dict(payload)
    out["title"] = SITE_TITLE
    channels = []
    for channel in out.get("channels") or []:
        entry = dict(channel)
        entry["items"] = [
            slim_public_item(item, include_abstract=include_abstract, clip_release=clip_release)
            for item in (channel.get("items") or channel.get("papers") or [])
        ]
        entry.pop("papers", None)
        channels.append(entry)
    out["channels"] = channels
    return out


def http_get(url: str, *, timeout: int = 45, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json, application/atom+xml, application/xml, text/xml, */*",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            delay = 2 ** attempt
            log(f"Request failed ({attempt + 1}/{attempts}), retrying in {delay}s: {url}")
            time.sleep(delay)
    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def http_json(url: str, *, timeout: int = 45) -> dict[str, Any]:
    raw = http_get(url, timeout=timeout)
    return json.loads(raw.decode("utf-8"))


def parse_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, dict):
        parts = value.get("date-parts", [[]])[0]
        if len(parts) >= 3:
            try:
                return date(int(parts[0]), int(parts[1]), int(parts[2])).isoformat()
            except (TypeError, ValueError):
                return ""
        return ""
    text = str(value)
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if not match:
        return ""
    candidate = match.group(0)
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return ""


def arxiv_category_query(categories: tuple[str, ...] = ARXIV_CATEGORIES) -> str:
    return "(" + " OR ".join(f"cat:{category}" for category in categories) + ")"


def fetch_arxiv(start_date: date, end_date: date, categories: tuple[str, ...] = ARXIV_CATEGORIES) -> list[Paper]:
    """Pull recent category listings, then keep papers inside the local date window.

    Date-only submittedDate queries currently return zero hits from the arXiv API.
    """
    papers: list[Paper] = []
    start = 0
    page_size = 100
    namespace = {"a": "http://www.w3.org/2005/Atom", "o": "http://a9.com/-/spec/opensearch/1.1/"}
    query = arxiv_category_query(categories)
    reached_old = False
    while True:
        params = urllib.parse.urlencode(
            {
                "search_query": query,
                "start": start,
                "max_results": page_size,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        root = ET.fromstring(http_get(f"{ARXIV_API}?{params}"))
        entries = root.findall("a:entry", namespace)
        if not entries:
            break
        page_old = 0
        for entry in entries:
            published = parse_date(entry.findtext("a:published", default="", namespaces=namespace))
            try:
                published_day = date.fromisoformat(published[:10]) if published else None
            except ValueError:
                published_day = None
            if published_day is None:
                continue
            if published_day < start_date:
                page_old += 1
                reached_old = True
                continue
            if published_day > end_date:
                continue
            arxiv_id = (entry.findtext("a:id", default="", namespaces=namespace).rstrip("/").split("/")[-1])
            authors = [clean_text(author.findtext("a:name", default="", namespaces=namespace)) for author in entry.findall("a:author", namespace)]
            paper_categories = [node.attrib.get("term", "") for node in entry.findall("a:category", namespace)]
            papers.append(
                Paper(
                    id=f"arxiv:{arxiv_id}",
                    source="arXiv",
                    title=clean_text(entry.findtext("a:title", default="", namespaces=namespace)),
                    abstract=clean_text(entry.findtext("a:summary", default="", namespaces=namespace)),
                    authors=[author for author in authors if author],
                    published=published,
                    updated=parse_date(entry.findtext("a:updated", default="", namespaces=namespace)),
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    category=paper_categories[0] if paper_categories else "",
                    tags=paper_categories[:3],
                )
            )
        start += len(entries)
        if reached_old and page_old >= max(1, len(entries) // 2):
            break
        if len(entries) < page_size or start >= 2000:
            break
        time.sleep(3)
    log(f"arXiv: {len(papers)} records")
    return papers


def fetch_biorxiv(start_date: date, end_date: date) -> list[Paper]:
    papers: list[Paper] = []
    cursor = 0
    while True:
        url = f"{BIORXIV_API}/{start_date.isoformat()}/{end_date.isoformat()}/{cursor}"
        raw = http_get(url)
        if not raw.strip():
            log("bioRxiv API returned an empty body; using Europe PMC metadata")
            return fetch_biorxiv_europe_pmc(start_date, end_date)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            log("bioRxiv API returned invalid JSON; using Europe PMC metadata")
            return fetch_biorxiv_europe_pmc(start_date, end_date)
        if not isinstance(payload, dict):
            log("bioRxiv API returned unexpected payload; using Europe PMC metadata")
            return fetch_biorxiv_europe_pmc(start_date, end_date)
        collection = payload.get("collection") or []
        for item in collection:
            doi = clean_text(item.get("doi"))
            authors = [part.strip() for part in re.split(r"\s*;\s*", clean_text(item.get("authors"))) if part.strip()]
            papers.append(
                Paper(
                    id=f"biorxiv:{doi or item.get('title', '')}",
                    source="bioRxiv",
                    title=clean_text(item.get("title")),
                    abstract=clean_text(item.get("abstract")),
                    authors=authors,
                    published=parse_date(item.get("date")),
                    updated=parse_date(item.get("date")),
                    url=f"https://www.biorxiv.org/content/{doi}" if doi else clean_text(item.get("url")),
                    doi=doi,
                    category=clean_text(item.get("category")),
                    tags=[clean_text(item.get("category"))] if item.get("category") else [],
                )
            )
        messages = payload.get("messages") or [{}]
        message = messages[0] if isinstance(messages, list) else messages
        total = int(message.get("total", len(collection)) or 0)
        cursor += len(collection)
        if not collection or cursor >= total:
            break
        time.sleep(1)
    log(f"bioRxiv: {len(papers)} records")
    return papers


def fetch_biorxiv_europe_pmc(start_date: date, end_date: date) -> list[Paper]:
    query = f'SRC:PPR AND PUBLISHER:"bioRxiv" AND FIRST_PDATE:[{start_date.isoformat()} TO {end_date.isoformat()}]'
    params = urllib.parse.urlencode(
        {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": 1000,
        }
    )
    payload = http_json(f"{EUROPE_PMC_API}?{params}")
    papers: list[Paper] = []
    for item in payload.get("resultList", {}).get("result", []):
        doi = clean_text(item.get("doi"))
        author_nodes = (item.get("authorList") or {}).get("author") or []
        authors = [clean_text(author.get("fullName")) for author in author_nodes if clean_text(author.get("fullName"))]
        if not authors:
            authors = [part.strip() for part in clean_text(item.get("authorString")).rstrip(".").split(",") if part.strip()]
        papers.append(
            Paper(
                id=f"biorxiv:{doi or item.get('id', '')}",
                source="bioRxiv",
                title=clean_text(item.get("title")),
                abstract=clean_text(item.get("abstractText")),
                authors=authors,
                published=parse_date(item.get("firstPublicationDate")),
                updated=parse_date(item.get("dateOfCreation") or item.get("firstIndexDate")),
                url=f"https://www.biorxiv.org/content/{doi}" if doi else f"https://europepmc.org/article/PPR/{item.get('id', '')}",
                doi=doi,
                category="bioRxiv",
                tags=["bioRxiv"],
            )
        )
    log(f"bioRxiv via Europe PMC: {len(papers)} records")
    return papers


def crossref_authors(item: dict[str, Any]) -> list[str]:
    authors = []
    for author in item.get("author") or []:
        name = " ".join(filter(None, [clean_text(author.get("given")), clean_text(author.get("family"))]))
        if name:
            authors.append(name)
    return authors


def fetch_chemrxiv(start_date: date, end_date: date) -> list[Paper]:
    params = urllib.parse.urlencode(
        {
            "filter": f"from-created-date:{start_date.isoformat()},until-created-date:{end_date.isoformat()}",
            "select": "DOI,title,author,created,published,abstract,URL",
            "rows": 1000,
            "sort": "created",
            "order": "desc",
            "mailto": "wangzc@stu.pku.edu.cn",
        }
    )
    payload = http_json(f"{CROSSREF_API}?{params}")
    papers = []
    for item in payload.get("message", {}).get("items", []):
        doi = clean_text(item.get("DOI"))
        title_value = item.get("title") or [""]
        title = clean_text(title_value[0] if isinstance(title_value, list) else title_value)
        published = parse_date(item.get("published") or item.get("created"))
        papers.append(
            Paper(
                id=f"chemrxiv:{doi or title}",
                source="ChemRxiv",
                title=title,
                abstract=clean_text(item.get("abstract")),
                authors=crossref_authors(item),
                published=published,
                updated=parse_date(item.get("created")),
                url=clean_text(item.get("URL")) or (f"https://doi.org/{doi}" if doi else ""),
                doi=doi,
                category="ChemRxiv",
                tags=["ChemRxiv"],
            )
        )
    log(f"ChemRxiv: {len(papers)} records")
    return papers


def phrase_score(text: str, terms: dict[str, int], title: bool = False) -> tuple[float, list[str]]:
    lowered = f" {text.lower()} "
    found = []
    score = 0.0
    multiplier = 1.75 if title else 1.0
    for phrase, weight in terms.items():
        if phrase in lowered:
            found.append(phrase.strip())
            score += weight * multiplier
    return score, found


def choose_topic(paper: Paper) -> str:
    text = f"{paper.title} {paper.abstract}".lower()
    scores = {topic: sum(1 for term in terms if term in text) for topic, terms in TOPIC_RULES.items()}
    topic, score = max(scores.items(), key=lambda item: item[1])
    return topic if score else "方法与模型"


def score_paper(paper: Paper, end_date: date) -> bool:
    ai_title, ai_title_hits = phrase_score(paper.title, AI_TERMS, title=True)
    ai_body, ai_body_hits = phrase_score(paper.abstract, AI_TERMS)
    chem_title, chem_title_hits = phrase_score(paper.title, CHEM_TERMS, title=True)
    chem_body, chem_body_hits = phrase_score(paper.abstract, CHEM_TERMS)
    quality, quality_hits = phrase_score(f"{paper.title} {paper.abstract}", QUALITY_TERMS)
    ai_score = ai_title + min(ai_body, 20)
    chem_score = chem_title + min(chem_body, 20)
    if not ai_title_hits and len(set(ai_body_hits)) < 1:
        return False
    if not chem_title_hits and len(set(chem_body_hits)) < 1:
        return False
    if ai_score < 5 or chem_score < 4:
        return False
    try:
        age = max(0, (end_date - date.fromisoformat(paper.published)).days)
    except ValueError:
        age = 3
    freshness = max(0, 5 - age)
    abstract_bonus = 3 if len(paper.abstract) >= 700 else 1 if len(paper.abstract) >= 250 else -2
    paper.relevance_score = round(ai_score + chem_score + freshness + abstract_bonus, 1)
    paper.quality_score = round(min(100, 42 + paper.relevance_score * 1.25 + quality), 1)
    paper.category = choose_topic(paper)
    useful_tags = list(dict.fromkeys(ai_title_hits + chem_title_hits + ai_body_hits + chem_body_hits))
    paper.tags = list(dict.fromkeys([paper.category, *paper.tags, *useful_tags[:3]]))[:5]
    paper.evidence_flags = [term for term in quality_hits if term in {"benchmark", "dataset", "prospective", "experimental validation", "in vivo", "out-of-distribution", "open source"}]
    return True


def deduplicate(papers: Iterable[Paper]) -> list[Paper]:
    seen: dict[str, Paper] = {}
    for paper in papers:
        key = paper.doi.lower().strip() if paper.doi else re.sub(r"\W+", "", paper.title.lower())
        if not key:
            continue
        previous = seen.get(key)
        if previous is None or len(paper.abstract) > len(previous.abstract):
            seen[key] = paper
    return list(seen.values())


def fallback_commentary(paper: Paper) -> None:
    topic_actions = {
        "分子与药物发现": "用于分子设计或药物发现",
        "结构与生物": "用于解析生物分子结构与功能",
        "材料与催化": "用于材料性质预测或催化研究",
        "方法与模型": "用于化学研究中的建模与计算",
    }
    action = topic_actions.get(paper.category, "用于 AI 与化学交叉研究")
    paper.summary_zh = f"该预印本提出一项{action}的新方法，重点讨论了“{paper.title}”所涉及的模型与验证结果。"
    paper.why_it_matters_zh = "入选依据来自题名、摘要中的方法相关性、验证信息与发布时间；建议阅读全文后再判断其适用范围。"


def order_candidates(candidates: list[Paper]) -> list[Paper]:
    return sorted(
        candidates,
        key=lambda paper: (paper.relevance_score, paper.quality_score, paper.published, -SOURCE_ORDER.get(paper.source, 9)),
        reverse=True,
    )


def select_papers(candidates: list[Paper], limit: int) -> tuple[list[Paper], str]:
    ordered = sorted(
        candidates,
        key=lambda paper: (paper.relevance_score, paper.quality_score, paper.published, -SOURCE_ORDER.get(paper.source, 9)),
        reverse=True,
    )
    selected = ordered[:limit]
    mode = "公开元数据全量抓取 + 自动规则筛选"
    for index, paper in enumerate(selected, 1):
        paper.rank = index
        if index <= 3:
            paper.featured = True
        if not paper.summary_zh or not paper.why_it_matters_zh:
            fallback_commentary(paper)
    return selected, mode


def author_line(authors: list[str]) -> str:
    if not authors:
        return "作者信息暂缺"
    if len(authors) <= 3:
        return ", ".join(authors)
    return f"{', '.join(authors[:3])} 等 {len(authors)} 人"


def digest_payload(
    selected: list[Paper],
    *,
    start_date: date,
    end_date: date,
    source_counts: dict[str, int],
    candidate_count: int,
    mode: str,
    errors: list[str],
) -> dict[str, Any]:
    topics: dict[str, int] = {}
    for paper in selected:
        topics[paper.category] = topics.get(paper.category, 0) + 1
    return {
        "schema_version": 1,
        "date": end_date.isoformat(),
        "window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "title": "AI × Chem 每日预印本精选",
        "subtitle": "面向人工智能与化学交叉研究的每日文献观察",
        "method": mode,
        "method_note": "系统抓取公开元数据，经关键词与证据信号筛选，再对候选摘要进行排序；预印本未经同行评议。",
        "stats": {
            "fetched": sum(source_counts.values()),
            "candidates": candidate_count,
            "selected": len(selected),
            "sources": source_counts,
            "topics": topics,
        },
        "source_errors": errors,
        "papers": [
            {
                **asdict(paper),
                "author_line": author_line(paper.authors),
            }
            for paper in selected
        ],
    }


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


CHEM_ARCHIVE_HREF = "data/channels/aixchem/archive/{day}.json"


def archive_index_entry(day: str, *, selected: int, candidates: int = 0, fetched: int = 0, href: str | None = None) -> dict[str, Any]:
    return {
        "date": day,
        "href": href or CHEM_ARCHIVE_HREF.format(day=day),
        "selected": int(selected or 0),
        "candidates": int(candidates or 0),
        "fetched": int(fetched or 0),
        "kind": "json",
    }


def upsert_archive_index(path: Path, entry: dict[str, Any], *, schema_version: str = "2.0") -> None:
    index = load_json(path, {"schema_version": schema_version, "items": []})
    items = [item for item in index.get("items", []) if item.get("date") != entry["date"]]
    items.append(archive_index_entry(
        entry["date"],
        selected=entry.get("selected", 0),
        candidates=entry.get("candidates", 0),
        fetched=entry.get("fetched", 0),
        href=entry.get("href"),
    ))
    index["schema_version"] = schema_version
    index["items"] = sorted(items, key=lambda item: item.get("date", ""), reverse=True)
    write_json(path, index)


def write_raw_snapshot(
    raw_root: Path,
    papers: list[Paper],
    *,
    start_date: date,
    end_date: date,
    source_counts: dict[str, int],
    errors: list[str],
) -> dict[str, Any]:
    """Write a compact raw snapshot outside the published site."""
    snapshot_root = raw_root / "aixchem" / f"{end_date:%Y}" / f"{end_date:%m}"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    data_path = snapshot_root / f"{end_date.isoformat()}.jsonl.gz"
    with gzip.open(data_path, "wt", encoding="utf-8", newline="\n") as stream:
        for paper in papers:
            stream.write(json.dumps(asdict(paper), ensure_ascii=False, separators=(",", ":")) + "\n")
    manifest = {
        "schema_version": "1.0",
        "channel": "aixchem",
        "date": end_date.isoformat(),
        "window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "record_count": len(papers),
        "source_counts": source_counts,
        "source_errors": errors,
        "data_file": data_path.name,
        "bytes": data_path.stat().st_size,
    }
    write_json(snapshot_root / f"{end_date.isoformat()}.manifest.json", manifest)
    return manifest


def render_email(payload: dict[str, Any], site_url: str) -> tuple[str, str]:
    day = payload["date"]
    stats = payload["stats"]
    selected = payload.get("items") or payload.get("papers") or []
    list_items = []
    markdown_items = []
    for paper in selected[:10]:
        list_items.append(
            f"""<tr><td style="padding:18px 0;border-bottom:1px solid #e6e8ee">
<div style="font-size:12px;color:#0e7c7b;font-weight:700">#{paper['rank']} · {html.escape(paper['source'])} · {html.escape(paper['category'])}</div>
<a href="{html.escape(paper['url'])}" style="display:block;margin:5px 0 6px;color:#16213a;font-size:17px;line-height:1.45;font-weight:700;text-decoration:none">{html.escape(paper['title'])}</a>
<div style="color:#5b6478;font-size:13px">{html.escape(paper['author_line'])} · {html.escape(paper['published'])}</div>
<div style="margin-top:9px;color:#26334d;font-size:14px;line-height:1.7">{html.escape(paper['summary_zh'])}</div>
</td></tr>"""
        )
        markdown_items.append(f"{paper['rank']}. [{paper['title']}]({paper['url']}) — {paper['summary_zh']}")
    email_html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"></head>
<body style="margin:0;background:#f3f5f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;color:#16213a">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="680" cellspacing="0" cellpadding="0" style="width:100%;max-width:680px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(22,33,58,.08)">
<tr><td style="padding:34px 36px;background:linear-gradient(135deg,#16213a,#0e7c7b);color:#fff">
<div style="font-size:12px;letter-spacing:2px;opacity:.75">AI × CHEMISTRY PREPRINT DAILY</div>
<h1 style="margin:8px 0 4px;font-size:27px">AI × Chem 每日预印本精选</h1>
<div style="font-size:14px;opacity:.82">{day} · 抓取 {stats['fetched']} 篇 · 精选 {stats['selected']} 篇</div>
</td></tr>
<tr><td style="padding:12px 36px 32px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0">{''.join(list_items)}</table>
<p style="margin:28px 0 6px;text-align:center"><a href="{html.escape(site_url)}" style="display:inline-block;padding:11px 24px;background:#0e7c7b;color:#fff;border-radius:999px;text-decoration:none;font-weight:700">查看完整日报与历史归档</a></p>
<p style="text-align:center;color:#7a8293;font-size:12px;line-height:1.6">数据来自 arXiv、bioRxiv 与 ChemRxiv 公开元数据。预印本未经同行评议。</p>
</td></tr></table></td></tr></table></body></html>"""
    markdown = (
        f"# AI × Chem 每日预印本精选 · {day}\n\n"
        f"抓取 {stats['fetched']} 篇，筛得 {stats['candidates']} 篇候选，最终精选 {stats['selected']} 篇。\n\n"
        + "\n\n".join(markdown_items)
        + f"\n\n[查看完整日报与历史归档]({site_url})\n\n"
        + "> 数据来自 arXiv、bioRxiv 与 ChemRxiv 公开元数据。预印本未经同行评议。\n"
    )
    return email_html, markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-root", type=Path, default=Path("public"))
    parser.add_argument("--days", type=int, default=3, help="Inclusive rolling date window")
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--date", dest="run_date", help="Digest date in YYYY-MM-DD")
    parser.add_argument("--site-url", default=os.getenv("SITE_URL", "https://zichenwang114514.github.io/ai-x-daily/"))
    parser.add_argument("--raw-root", type=Path, help="Optional private raw snapshot directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    shanghai_today = datetime.now(timezone(timedelta(hours=8))).date()
    end_date = date.fromisoformat(args.run_date) if args.run_date else shanghai_today
    days = max(1, args.days)
    if end_date.weekday() == 0:
        days = max(days, 4)
    start_date = end_date - timedelta(days=days - 1)
    log(f"Building digest for {start_date} through {end_date}")

    all_papers: list[Paper] = []
    source_counts = {"arXiv": 0, "bioRxiv": 0, "ChemRxiv": 0}
    errors: list[str] = []
    fetchers = (("arXiv", fetch_arxiv), ("bioRxiv", fetch_biorxiv), ("ChemRxiv", fetch_chemrxiv))
    for source, fetcher in fetchers:
        try:
            batch = fetcher(start_date, end_date)
            source_counts[source] = len(batch)
            all_papers.extend(batch)
        except Exception as exc:  # noqa: BLE001 - each source is isolated by design
            message = f"{source}: {type(exc).__name__}: {exc}"
            errors.append(message)
            log(f"Source unavailable: {message}")

    if not all_papers:
        raise RuntimeError("All sources returned no records or failed")
    unique = deduplicate(all_papers)
    if args.raw_root:
        raw_manifest = write_raw_snapshot(
            args.raw_root,
            unique,
            start_date=start_date,
            end_date=end_date,
            source_counts=source_counts,
            errors=errors,
        )
        log(
            f"Raw snapshot: {raw_manifest['record_count']} records, "
            f"{raw_manifest['bytes']} bytes compressed"
        )
    candidates = [paper for paper in unique if score_paper(paper, end_date)]
    log(f"Candidate filter: {len(unique)} unique -> {len(candidates)} relevant")
    if not candidates:
        raise RuntimeError("No AI x Chem candidates passed the relevance filter")

    data_root = args.site_root / "data"
    ordered_candidates = order_candidates(candidates)
    candidate_payload = {
        "schema_version": 1,
        "date": end_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "count": len(ordered_candidates),
        "papers": [asdict(paper) for paper in ordered_candidates[:40]],
    }
    write_json(data_root / "candidates" / "latest.json", candidate_payload)

    selected, mode = select_papers(candidates, max(1, args.limit))
    payload = digest_payload(
        selected,
        start_date=start_date,
        end_date=end_date,
        source_counts=source_counts,
        candidate_count=len(candidates),
        mode=mode,
        errors=errors,
    )

    archive_root = data_root / "archive"
    day = end_date.isoformat()
    write_json(data_root / "latest.json", payload)
    write_json(archive_root / f"{day}.json", payload)
    chem_archive = data_root / "channels" / "aixchem" / "archive"
    write_json(chem_archive / f"{day}.json", payload)
    entry = archive_index_entry(
        day,
        selected=len(selected),
        candidates=len(candidates),
        fetched=sum(source_counts.values()),
    )
    upsert_archive_index(archive_root / "index.json", entry)
    upsert_archive_index(chem_archive / "index.json", entry)

    email_html, email_markdown = render_email(payload, args.site_url)
    email_root = args.site_root / "email"
    email_root.mkdir(parents=True, exist_ok=True)
    (email_root / "latest.html").write_text(email_html, encoding="utf-8")
    (email_root / "latest.md").write_text(email_markdown, encoding="utf-8")
    log(f"Digest ready: {len(selected)} papers; mode={mode}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        log(f"Fatal error: {type(exc).__name__}: {exc}")
        raise
