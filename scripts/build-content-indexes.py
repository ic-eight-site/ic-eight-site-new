#!/usr/bin/env python3
"""Build article-derived indexes from articles.json, the editorial registry."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, time, timezone
from email.utils import format_datetime, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "articles.json"
ARTICLES_PAGE = ROOT / "articles.html"
PVE_PAGE = ROOT / "product-value-evaluations.html"
RSS_FILE = ROOT / "rss.xml"
SITEMAP_FILE = ROOT / "sitemap.xml"
ORIGIN = "https://ic-eight.com"
ALLOWED_TAGS = {
    "Diagnosis & Priority",
    "Value in Use",
    "Positioning & Assumptions",
    "Content Systems",
    "AI & Value Creation",
}
NOSCRIPT_START = "<!-- GENERATED:ARTICLES_NOSCRIPT:START -->"
NOSCRIPT_END = "<!-- GENERATED:ARTICLES_NOSCRIPT:END -->"
PVE_START = "<!-- GENERATED:PVE_LIBRARY:START -->"
PVE_END = "<!-- GENERATED:PVE_LIBRARY:END -->"


class HeadMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        if values.get("name", "").lower() == "description":
            self.description = values.get("content", "").strip()


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(fragment: str) -> str:
    parser = TextParser()
    parser.feed(fragment)
    return " ".join("".join(parser.parts).split())


def read_registry() -> list[dict]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def write_registry(entries: list[dict]) -> None:
    REGISTRY.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def article_path(url: str) -> Path:
    return ROOT / url.lstrip("/")


def article_description(path: Path) -> str:
    parser = HeadMetadataParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.description


def parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def article_date(path: Path) -> datetime:
    source = path.read_text(encoding="utf-8")
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        source,
        re.I | re.S,
    ):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        candidates = data.get("@graph", []) if isinstance(data, dict) else []
        candidates = [data, *candidates] if isinstance(data, dict) else candidates
        for candidate in candidates:
            if not isinstance(candidate, dict) or not candidate.get("datePublished"):
                continue
            raw = str(candidate["datePublished"])
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
                return datetime.combine(datetime.fromisoformat(raw).date(), time(12), timezone.utc)
            return parse_iso_datetime(raw)
    raise ValueError(f"No datePublished found in {path.relative_to(ROOT)}")


def replace_generated(source: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(source):
        raise ValueError(f"Generated block markers not found: {start}")
    return pattern.sub(f"{start}\n{body.rstrip()}\n{end}", source, count=1)


def bootstrap(entries: list[dict]) -> list[dict]:
    """One-time import of current RSS timestamps and PVE card copy."""
    rss_dates: dict[str, str] = {}
    rss_root = ET.parse(RSS_FILE).getroot()
    for item in rss_root.findall("./channel/item"):
        link = item.findtext("link") or ""
        published = item.findtext("pubDate") or ""
        if link and published:
            rss_dates[urlsplit(link).path] = parsedate_to_datetime(published).astimezone(
                timezone.utc
            ).isoformat().replace("+00:00", "Z")

    by_url = {entry["url"]: entry for entry in entries}
    for entry in entries:
        path = article_path(entry["url"])
        if not path.exists():
            raise ValueError(f"Missing article file: {entry['url']}")
        entry["description"] = article_description(path)
        entry["publishedAt"] = rss_dates.get(entry["url"])
        if not entry["publishedAt"]:
            entry["publishedAt"] = article_date(path).isoformat().replace("+00:00", "Z")

    library = PVE_PAGE.read_text(encoding="utf-8")
    sections = re.findall(
        r'<section class="practice" id="([^"]+)">(.*?)</section>', library, re.S
    )
    for order, (section_id, section_html) in enumerate(sections):
        label_match = re.search(r'<p class="section-label">(.*?)</p>', section_html, re.S)
        label = plain_text(label_match.group(1)) if label_match else section_id
        cards = []
        for attrs, card_html in re.findall(
            r'<div class="case-card"([^>]*)>(.*?)</div>', section_html, re.S
        ):
            title_match = re.search(r"<h2>(.*?)</h2>", card_html, re.S)
            meta_match = re.search(r'<p class="case-meta-label">(.*?)</p>', card_html, re.S)
            finding_match = re.search(r'<p class="case-finding">(.*?)</p>', card_html, re.S)
            link_match = re.search(
                r'<a href="([^"]+)" class="text-link">(.*?)</a>', card_html, re.S
            )
            if not finding_match or not link_match:
                raise ValueError(f"Incomplete PVE card in {section_id}")
            card = {
                "finding": plain_text(finding_match.group(1)),
                "url": html.unescape(link_match.group(1)),
                "linkLabel": plain_text(link_match.group(2)),
            }
            if title_match:
                card["title"] = plain_text(title_match.group(1))
            if meta_match:
                card["metaLabel"] = plain_text(meta_match.group(1))
            if "border-bottom: none" in attrs:
                card["noBorder"] = True
            cards.append(card)
        if not cards or cards[0]["url"] not in by_url:
            raise ValueError(f"PVE section {section_id} has no registered primary article")
        by_url[cards[0]["url"]]["pve"] = {
            "id": section_id,
            "label": label,
            "order": order,
            "cards": cards,
        }
    return entries


def validate(entries: list[dict]) -> None:
    errors: list[str] = []
    urls = [entry.get("url") for entry in entries]
    titles = [entry.get("title") for entry in entries]
    if len(urls) != len(set(urls)):
        errors.append("Duplicate article URL in articles.json")
    if len(titles) != len(set(titles)):
        errors.append("Duplicate article title in articles.json")
    pve_ids: list[str] = []
    pve_orders: list[int] = []
    for index, entry in enumerate(entries):
        prefix = f"Entry {index + 1}"
        for field in ("title", "url", "description", "publishedAt"):
            if not entry.get(field):
                errors.append(f"{prefix} is missing {field}")
        if entry.get("tag") not in ALLOWED_TAGS and entry.get("tag") is not None:
            errors.append(f"{prefix} has an unknown tag: {entry.get('tag')}")
        if entry.get("url") and not article_path(entry["url"]).exists():
            errors.append(f"{prefix} points to a missing file: {entry['url']}")
        try:
            parse_iso_datetime(entry.get("publishedAt", ""))
        except (ValueError, TypeError):
            errors.append(f"{prefix} has an invalid publishedAt value")
        pve = entry.get("pve")
        if pve:
            pve_ids.append(pve.get("id", ""))
            if not isinstance(pve.get("order"), int):
                errors.append(f"{prefix} has a PVE entry without an integer order")
            else:
                pve_orders.append(pve["order"])
            if not pve.get("cards"):
                errors.append(f"{prefix} has a PVE entry without cards")
            elif pve["cards"][0].get("url") != entry.get("url"):
                errors.append(f"{prefix} PVE primary card does not point to its article")
            for card in pve.get("cards", []):
                if card.get("url") not in urls:
                    errors.append(
                        f"{prefix} PVE card points outside the registry: {card.get('url')}"
                    )
    if len(pve_ids) != len(set(pve_ids)):
        errors.append("Duplicate PVE id in articles.json")
    if len(pve_orders) != len(set(pve_orders)):
        errors.append("Duplicate PVE order in articles.json")
    if errors:
        raise ValueError("\n".join(errors))


def render_noscript(entries: list[dict]) -> str:
    links = [
        f'  <a href="{html.escape(entry["url"], quote=True)}">'
        f'{html.escape(entry["title"], quote=False)}</a>'
        for entry in entries
    ]
    return '<div class="article-list-static" style="display:none">\n' + "\n".join(links) + "\n</div>"


def render_pve(entries: list[dict]) -> str:
    pves = sorted(
        (entry["pve"] for entry in entries if entry.get("pve")),
        key=lambda value: value["order"],
    )
    sections: list[str] = []
    for pve in pves:
        lines = [
            f'<section class="practice" id="{html.escape(pve["id"], quote=True)}">',
            f'  <p class="section-label">{html.escape(pve["label"], quote=False)}</p>',
        ]
        for card in pve["cards"]:
            style = ' style="border-bottom: none;"' if card.get("noBorder") else ""
            lines.append(f'  <div class="case-card"{style}>')
            if card.get("title"):
                lines.append(f'    <h2>{html.escape(card["title"], quote=False)}</h2>')
            if card.get("metaLabel"):
                lines.append(
                    f'    <p class="case-meta-label">{html.escape(card["metaLabel"], quote=False)}</p>'
                )
            lines.append(
                f'    <p class="case-finding">{html.escape(card["finding"], quote=False)}</p>'
            )
            lines.append(
                f'    <a href="{html.escape(card["url"], quote=True)}" class="text-link">'
                f'{html.escape(card["linkLabel"], quote=False)}</a>'
            )
            lines.append("  </div>")
        lines.append("</section>")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def render_rss(entries: list[dict]) -> str:
    newest = max(parse_iso_datetime(entry["publishedAt"]) for entry in entries)
    newest_first = sorted(
        entries, key=lambda entry: parse_iso_datetime(entry["publishedAt"]), reverse=True
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '<channel>',
        '  <title>IC Eight — Articles</title>',
        '  <link>https://ic-eight.com/articles.html</link>',
        '  <description>Articles on Japan market entry, product UX, AI, and localization, exploring how global technology products land with Japanese users and where intended value gets lost.</description>',
        '  <language>en-us</language>',
        f'  <lastBuildDate>{format_datetime(newest, usegmt=True)}</lastBuildDate>',
    ]
    for entry in newest_first:
        absolute = ORIGIN + entry["url"]
        lines.extend([
            "  <item>",
            f'    <title>{html.escape(entry["title"], quote=False)}</title>',
            f'    <link>{html.escape(absolute, quote=False)}</link>',
            f'    <guid isPermaLink="true">{html.escape(absolute, quote=False)}</guid>',
            f'    <pubDate>{format_datetime(parse_iso_datetime(entry["publishedAt"]), usegmt=True)}</pubDate>',
        ])
        if entry.get("tag"):
            lines.append(f'    <category>{html.escape(entry["tag"], quote=False)}</category>')
        lines.append("  </item>")
    lines.extend(["</channel>", "</rss>", ""])
    return "\n".join(lines)


def render_sitemap(entries: list[dict]) -> str:
    namespace = {"sm": "https://www.sitemaps.org/schemas/sitemap/0.9"}
    current = ET.parse(SITEMAP_FILE).getroot()
    article_urls = {ORIGIN + entry["url"] for entry in entries}
    static_entries: list[tuple[str, str, str]] = []
    for node in current.findall("sm:url", namespace):
        loc = node.findtext("sm:loc", "", namespace)
        if loc in article_urls or urlsplit(loc).path.startswith("/articles/"):
            continue
        static_entries.append((
            loc,
            node.findtext("sm:lastmod", "", namespace),
            node.findtext("sm:priority", "", namespace),
        ))
    home = [entry for entry in static_entries if entry[0] == ORIGIN + "/"]
    other_static = [entry for entry in static_entries if entry[0] != ORIGIN + "/"]
    generated_articles = [(
        ORIGIN + entry["url"],
        parse_iso_datetime(entry["publishedAt"]).date().isoformat(),
        "0.7",
    ) for entry in entries]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod, priority in [*home, *generated_articles, *other_static]:
        lines.extend(["  <url>", f"    <loc>{html.escape(loc, quote=False)}</loc>"])
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        if priority:
            lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.extend(["</urlset>", ""])
    return "\n".join(lines)


def generated_outputs(entries: list[dict]) -> dict[Path, str]:
    articles_source = ARTICLES_PAGE.read_text(encoding="utf-8")
    pve_source = PVE_PAGE.read_text(encoding="utf-8")
    pve_count = sum(1 for entry in entries if entry.get("pve"))
    pve_source = re.sub(
        r'(<p id="pve-results" class="pve-results" role="status" aria-live="polite">)\d+ entries(</p>)',
        rf"\g<1>{pve_count} entries\g<2>",
        pve_source,
        count=1,
    )
    return {
        ARTICLES_PAGE: replace_generated(articles_source, NOSCRIPT_START, NOSCRIPT_END, render_noscript(entries)),
        PVE_PAGE: replace_generated(pve_source, PVE_START, PVE_END, render_pve(entries)),
        RSS_FILE: render_rss(entries),
        SITEMAP_FILE: render_sitemap(entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        entries = read_registry()
        if args.bootstrap:
            entries = bootstrap(entries)
            write_registry(entries)
        validate(entries)
        outputs = generated_outputs(entries)
        stale = [path for path, expected in outputs.items() if path.read_text(encoding="utf-8") != expected]
        if args.check:
            if stale:
                print("Generated files are stale:")
                for path in stale:
                    print(f"- {path.relative_to(ROOT)}")
                return 1
            print(f"Content indexes are current: {len(entries)} articles, {sum(1 for entry in entries if entry.get('pve'))} PVE entries.")
            return 0
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")
        print(f"Generated indexes for {len(entries)} articles and {sum(1 for entry in entries if entry.get('pve'))} PVE entries.")
        return 0
    except (ValueError, KeyError, json.JSONDecodeError, ET.ParseError) as error:
        print(f"Content index build failed:\n{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
