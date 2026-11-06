#!/usr/bin/env python3
"""
Pre-render the translated site.

    python scripts/i18n/prerender.py --locales all --tiers core
    python scripts/i18n/prerender.py --locales de,fr,ja --tiers core
    python scripts/i18n/prerender.py --locales all --tiers full --out dist

Each locale becomes its own copy of the tree at <out>/<locale>/<page>.html:
the text is translated in the HTML itself, the region that serves the locale
has already removed the elements it cannot offer, and every copy carries
hreflang alternates plus a canonical URL. That is what makes the translations
indexable; the runtime in site-locale.js is for visitors who switch language
without leaving the page they are on.

Assets (CSS, JS, images) are rewritten to root-absolute URLs so the copies
share one copy of every file and only the HTML is duplicated. Internal .html
links stay relative, so a click inside /de/ stays inside /de/.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional
from xml.sax.saxutils import escape as xml_escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from i18n_core import apply_catalog, load_locales, strip_by_region  # noqa: E402

CONFIG_PATH = os.path.join(ROOT, "i18n", "config.json")
LOCALES_PATH = os.path.join(ROOT, "i18n", "locales.json")
REGIONS_PATH = os.path.join(ROOT, "i18n", "regions.json")

ASSET_ATTR_RE = re.compile(
    r"""(<(?:link|script|img|source|video|audio|iframe)\b[^>]*?\b(?:href|src|poster|data-src)\s*=\s*)(["'])([^"']+)\2""",
    re.IGNORECASE,
)
SRCSET_RE = re.compile(
    r"""(<source\b[^>]*?\bsrcset\s*=\s*)(["'])([^"']+)\2""", re.IGNORECASE
)
CANONICAL_RE = re.compile(
    r"""(<link\b[^>]*?\brel\s*=\s*["']canonical["'][^>]*?\bhref\s*=\s*)(["'])([^"']+)\2""",
    re.IGNORECASE,
)
OGURL_RE = re.compile(
    r"""(<meta\b[^>]*?\bproperty\s*=\s*["']og:url["'][^>]*?\bcontent\s*=\s*)(["'])([^"']+)\2""",
    re.IGNORECASE,
)
HTML_TAG_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)
LANG_ATTR_RE = re.compile(r"""\blang\s*=\s*(["'])([^"']*)\1""", re.IGNORECASE)
DIR_ATTR_RE = re.compile(r"""\bdir\s*=\s*(["'])([^"']*)\1""", re.IGNORECASE)

EXTERNAL_PREFIXES = ("http://", "https://", "//", "mailto:", "tel:", "data:", "javascript:", "#")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def region_for_locale(code: str, regions: dict) -> str:
    """The region whose edition best represents this locale."""
    for region_id, region in regions.get("regions", {}).items():
        if code in region.get("locales", []):
            return region_id
    for region_id, region in regions.get("regions", {}).items():
        if code in (region.get("autoLocales") or {}).values():
            return region_id
    return regions.get("default", "intl")


def merged_strings(catalog: dict, region: dict, code: str) -> Dict[str, str]:
    strings: Dict[str, str] = dict(catalog.get("strings", {}))
    language = code.split("-")[0]
    for source, by_locale in (region.get("copy") or {}).items():
        value = by_locale.get(code) or by_locale.get(language) or by_locale.get("en")
        if value:
            strings[source] = value
    return strings


def absolutise(markup: str, page: str, keep_html_relative: bool = True) -> str:
    """Point asset URLs at the site root so shared files are not duplicated."""

    def resolve(target: str) -> Optional[str]:
        value = target.strip()
        if not value or value.startswith(EXTERNAL_PREFIXES):
            return None
        if value.startswith("/"):
            return None
        clean = value.split("#")[0].split("?")[0]
        if keep_html_relative and clean.lower().endswith((".html", ".htm")):
            return None
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(page), clean))
        if joined.startswith(".."):
            return None
        suffix = value[len(clean):]
        return "/" + joined + suffix

    def swap(match: "re.Match[str]") -> str:
        target = resolve(match.group(3))
        if not target:
            return match.group(0)
        return match.group(1) + match.group(2) + target + match.group(2)

    markup = ASSET_ATTR_RE.sub(swap, markup)

    def swap_srcset(match: "re.Match[str]") -> str:
        parts = []
        changed = False
        for candidate in match.group(3).split(","):
            bits = candidate.strip().split()
            if not bits:
                continue
            target = resolve(bits[0])
            if target:
                bits[0] = target
                changed = True
            parts.append(" ".join(bits))
        if not changed:
            return match.group(0)
        return match.group(1) + match.group(2) + ", ".join(parts) + match.group(2)

    return SRCSET_RE.sub(swap_srcset, markup)


def set_language(markup: str, code: str, direction: str) -> str:
    match = HTML_TAG_RE.search(markup)
    if not match:
        return markup
    attrs = match.group(1)
    attrs = LANG_ATTR_RE.sub(f'lang="{code}"', attrs, count=1)
    if DIR_ATTR_RE.search(attrs):
        attrs = DIR_ATTR_RE.sub(f'dir="{direction}"', attrs, count=1)
    else:
        attrs = attrs.rstrip() + f' dir="{direction}"'
    if "data-locale=" not in attrs:
        attrs = attrs.rstrip() + f' data-locale="{code}"'
    return markup[: match.start()] + "<html" + attrs + ">" + markup[match.end():]


def rewrite_urls(markup: str, page: str, code: str, origin: str) -> str:
    canonical = f"{origin}/{code}/{page}"
    markup = CANONICAL_RE.sub(
        lambda m: m.group(1) + m.group(2) + canonical + m.group(2), markup, count=1
    )
    markup = OGURL_RE.sub(
        lambda m: m.group(1) + m.group(2) + canonical + m.group(2), markup, count=1
    )
    return markup


def add_alternates(markup: str, page: str, code: str, origin: str, available: List[str]) -> str:
    links = [
        f'<link rel="alternate" hreflang="x-default" href="{origin}/{page}">',
        f'<link rel="alternate" hreflang="{code}" href="{origin}/{code}/{page}">',
    ]
    block = "\n  ".join(links)
    if "</head>" in markup:
        return markup.replace("</head>", f"  {block}\n</head>", 1)
    return markup


def page_list(config: dict, tiers: List[str]) -> List[str]:
    """Same selection rules as extract_strings.py, kept in one place there."""
    sys.path.insert(0, HERE)
    from extract_strings import candidate_pages

    tier_config = dict(config)
    tier_config["tiers"] = {name: config["tiers"][name] for name in tiers if name in config["tiers"]}
    return candidate_pages(tier_config)


def available_locales(catalog_dir: str, bases: List[dict], variants: List[dict]) -> List[dict]:
    entries: List[dict] = []
    for entry in bases:
        if os.path.exists(os.path.join(catalog_dir, entry["code"] + ".json")):
            entries.append(entry)
    for entry in variants:
        # A variant may ship its own reviewed catalog (pt-BR does), or ride on
        # the base language's catalog.
        if os.path.exists(os.path.join(catalog_dir, entry["code"] + ".json")):
            entries.append(entry)
            continue
        base = entry.get("base", "")
        if any(item["code"] == base for item in entries):
            entries.append(entry)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--locales", default="core", help="'all', 'core', or a comma-separated list")
    parser.add_argument("--tiers", default="core")
    parser.add_argument("--out", default="", help="Output directory, defaults to config prerender.outputDir")
    parser.add_argument("--clean", action="store_true", help="Remove the output directory first")
    args = parser.parse_args()

    config = load_json(CONFIG_PATH)
    locales_data = load_json(LOCALES_PATH)
    regions = load_json(REGIONS_PATH)
    bases, variants = locales_data["locales"], locales_data.get("variants", [])
    catalog_dir = os.path.join(ROOT, config["catalogDir"])

    origin = config["prerender"]["siteOrigin"].rstrip("/")
    output_root = os.path.join(ROOT, args.out or config["prerender"]["outputDir"])

    tiers = [name.strip() for name in args.tiers.split(",") if name.strip()]
    pages = page_list(config, tiers)
    if not pages:
        print("No pages selected.", file=sys.stderr)
        return 2

    shipping = available_locales(catalog_dir, bases, variants)
    if args.locales.strip().lower() != "all":
        wanted = [code.strip() for code in args.locales.split(",") if code.strip()]
        shipping = [entry for entry in shipping if entry["code"] in wanted or entry["code"] == "en"]

    shipping = [entry for entry in shipping if entry["code"] != "en"]
    if not shipping:
        print("No translated locales found. Run translate.py first.", file=sys.stderr)
        return 2

    codes = [entry["code"] for entry in shipping]
    if args.clean and os.path.isdir(output_root):
        import shutil

        shutil.rmtree(output_root)

    total_written = 0
    for position, entry in enumerate(shipping, start=1):
        code = entry["code"]
        direction = entry.get("dir", "ltr")
        catalog_path = os.path.join(catalog_dir, code + ".json")
        if not os.path.exists(catalog_path):
            catalog_path = os.path.join(catalog_dir, (entry.get("base") or code) + ".json")
        if not os.path.exists(catalog_path):
            continue
        catalog = load_json(catalog_path)
        region_id = region_for_locale(code, regions)
        region = regions["regions"][region_id]
        strings = merged_strings(catalog, region, code)
        availability = region.get("availability", {})

        replaced_total = 0
        for page in pages:
            source_path = os.path.join(ROOT, page)
            with open(source_path, "r", encoding="utf-8", errors="replace") as handle:
                markup = handle.read()

            markup = strip_by_region(markup, region_id, availability)
            markup, replaced = apply_catalog(markup, strings, ())
            replaced_total += replaced
            markup = set_language(markup, code, direction)
            markup = absolutise(markup, page)
            markup = rewrite_urls(markup, page, code, origin)
            markup = add_alternates(markup, page, code, origin, codes)

            target = os.path.join(output_root, code, page)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(markup)
            total_written += 1

        print(f"[{position}/{len(shipping)}] {code:<8} {len(pages):>4} pages, {replaced_total:>6} strings, region {region_id}")

    write_sitemap(output_root, pages, codes, origin, config)
    print(f"\nWrote {total_written} pages to {os.path.relpath(output_root, ROOT)}")
    return 0


def write_sitemap(output_root: str, pages: List[str], codes: List[str], origin: str, config: dict) -> None:
    """One sitemap carrying the full locale matrix as xhtml:link alternates."""
    name = config["prerender"].get("sitemap", "sitemap-i18n.xml")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for page in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{xml_escape(origin + '/' + page)}</loc>")
        lines.append(
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{xml_escape(origin + "/" + page)}"/>'
        )
        for code in codes:
            lines.append(
                f'    <xhtml:link rel="alternate" hreflang="{code}" '
                f'href="{xml_escape(origin + "/" + code + "/" + page)}"/>'
            )
        lines.append("  </url>")

    for page in pages:
        for code in codes:
            lines.append("  <url>")
            lines.append(f"    <loc>{xml_escape(origin + '/' + code + '/' + page)}</loc>")
            lines.append("  </url>")

    lines.append("</urlset>")
    target = os.path.join(output_root, name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
