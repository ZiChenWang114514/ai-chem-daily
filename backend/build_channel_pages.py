#!/usr/bin/env python3
"""Generate lightweight channel pages from the shared site shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("aixchem", "aixbio", "aixmath", "aivoices", "engineering")


def main() -> int:
    source = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
    for channel in CHANNELS:
        page = source.replace('data-page="home" data-root=""', f'data-page="channel" data-channel="{channel}" data-root="../../"')
        page = page.replace('href="assets/', 'href="../../assets/').replace('src="assets/', 'src="../../assets/')
        page = page.replace('href="task/"', 'href="../../task/"').replace('href="api/', 'href="../../api/')
        page = page.replace('href="./" aria-label="AIX Daily 首页"', 'href="../../" aria-label="AIX Daily 首页"')
        page = page.replace('href="./" aria-current="page"', 'href="../../"')
        page = page.replace('href="channels/', 'href="../')
        target = ROOT / "public" / "channels" / channel / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
