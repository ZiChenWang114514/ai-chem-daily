#!/usr/bin/env python3
"""Generate lightweight channel pages from the shared site shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("aixchem", "aixbio", "aixmath", "aivoices", "engineering")
HOME_MARKERS = 'data-page="home" data-root=""'
CHANNEL_COPY = {
    "aixchem": ("AI × Chem", "化学"),
    "aixbio": ("AI × Bio", "生命科学"),
    "aixmath": ("AI × Math", "数学"),
    "aivoices": ("AI Voices", "公开观点"),
    "engineering": ("Engineering", "工程更新"),
}


def render_channel_page(source: str, channel: str) -> str:
    if HOME_MARKERS not in source:
        raise ValueError("Channel page template is missing the home page markers")
    kicker, title = CHANNEL_COPY[channel]
    page = source.replace(HOME_MARKERS, f'data-page="channel" data-channel="{channel}" data-root="../../"')
    page = page.replace('href="assets/', 'href="../../assets/').replace('src="assets/', 'src="../../assets/')
    page = page.replace('srcset="assets/', 'srcset="../../assets/')
    page = page.replace('href="data/daily/latest.json"', f'href="../../data/channels/{channel}/latest.json"')
    page = page.replace("assets/art/hero.webp", f"assets/art/{channel}.webp")
    page = page.replace("assets/art/hero.jpg", f"assets/art/{channel}.jpg")
    page = page.replace('href="task/"', 'href="../../task/"').replace('href="api/', 'href="../../api/')
    page = page.replace('href="library/"', 'href="../../library/"')
    page = page.replace('href="./" aria-label="AIX每日精读首页"', 'href="../../" aria-label="AIX每日精读首页"')
    page = page.replace('href="./" aria-current="page"', 'href="../../"')
    page = page.replace('href="channels/', 'href="../')
    page = page.replace(
        f'<a class="channel-nav__item" href="../{channel}/">',
        f'<a class="channel-nav__item is-active" href="../{channel}/" aria-current="page">',
    )
    page = page.replace(
        '<a class="channel-nav__item is-active" href="../../">',
        '<a class="channel-nav__item" href="../../">',
    )
    page = page.replace('id="eyebrow">今日精选', f"id=\"eyebrow\">{kicker}")
    page = page.replace('id="hero-title">五个频道的研究更新', f'id="hero-title">{title}')
    if f'data-channel="{channel}"' not in page:
        raise ValueError(f"Channel page for {channel} is missing data-channel after rewrite")
    return page


def main() -> int:
    source = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
    for channel in CHANNELS:
        page = render_channel_page(source, channel)
        target = ROOT / "public" / "channels" / channel / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
