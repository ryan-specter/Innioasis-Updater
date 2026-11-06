#!/usr/bin/env python3
"""Keep ``sitemap.xml`` in step with the pages in this repository.

Every page that ships in the repository should be listed, and every URL the
sitemap lists should exist. The generators add their own URLs as they write
pages, which cannot remove an entry for a page that was deleted, renamed or
never written. This script is the auditor and the repair:

* a listed URL whose file is gone is dropped;
* a page on disk that is not listed is added (with the lastmod, changefreq and
  priority the existing sitemap uses for pages like it);
* existing entries keep their own lastmod so a re-run is byte-identical.

``--check`` exits non-zero when the sitemap is out of date, for CI.

Usage:
    python scripts/generate_sitemap.py [--check]
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://innioasis.app"
SITEMAP = ROOT / "sitemap.xml"

# Folders that are not part of the published site, and files that must never be
# indexed.
SKIP_DIRS = {
    "innioasis.app website archive",
    "node_modules",
    ".git",
    ".cache",
    ".github",
    "src",
    "scripts",
    "feeds",
    "assets",
    "dist",
}
# 404 is not a page to index, support_toolbar.html is an HTML fragment that is
# injected into other pages, firmware_info.html is noindex and innioasis-embed.html
# is the bare widget that other sites iframe. None of them belong in a sitemap.
SKIP_FILES = {"404.html", "support_toolbar.html", "firmware_info.html", "innioasis-embed.html"}

URL_RE = re.compile(r"\s*<url>.*?</url>", re.S)


def rel_for(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def page_files() -> list[pathlib.Path]:
    pages = []
    for path in ROOT.rglob("*.html"):
        rel = rel_for(path)
        parts = rel.split("/")
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue
        if rel in SKIP_FILES or parts[0].startswith("."):
            continue
        pages.append(path)
    return sorted(pages, key=rel_for)


def url_for(rel: str) -> str:
    if rel == "index.html":
        return SITE + "/"
    if rel == "install/index.html":
        return SITE + "/install/"
    return SITE + "/" + rel


def rel_from_loc(loc: str) -> str:
    path = re.sub(r"^https?://[^/]+", "", loc).split("?")[0].split("#")[0]
    rel = path.lstrip("/")
    if not rel or rel.endswith("/"):
        rel += "index.html"
    return rel


def changefreq_for(rel: str) -> str:
    if rel in ("index.html", "firmware.html", "firmware-list.html"):
        return "weekly"
    if rel.startswith("release-notes/") or rel.startswith("post-install/"):
        return "monthly"
    return "monthly"


def priority_for(rel: str) -> str:
    if rel == "index.html":
        return "1.0"
    if rel == "install/index.html":
        return "0.9"
    if rel.startswith("install/"):
        return "0.8"
    if rel in ("firmware.html", "firmware-list.html"):
        return "0.9"
    if rel.startswith(("release-notes/", "post-install/", "firmware-info/", "rockbox-y1/", "rockbox-y2/")):
        return "0.6"
    if rel.count("/") == 1 and rel.endswith("index.html"):
        return "0.7"
    return "0.7"


def entry_for(rel: str, lastmod: str) -> str:
    return (
        "  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq>"
        "<priority>%s</priority></url>" % (url_for(rel), lastmod, changefreq_for(rel), priority_for(rel))
    )


def build(today: str | None = None) -> tuple[str, list[str], list[str]]:
    today = today or dt.date.today().isoformat()
    text = SITEMAP.read_text(encoding="utf-8") if SITEMAP.exists() else (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>\n'
    )
    existing: dict[str, str] = {}
    for block in URL_RE.findall(text):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        if not loc:
            continue
        rel = rel_from_loc(loc.group(1))
        if rel not in existing:
            existing[rel] = block.strip()
    # Correct a stale host (http, www, a fork) on entries we keep.
    fixed: dict[str, str] = {}
    for rel, block in existing.items():
        fixed[rel] = re.sub(
            r"<loc>[^<]+</loc>", "<loc>%s</loc>" % url_for(rel), block, count=1
        )

    files = {rel_for(path) for path in page_files()}
    kept = [rel for rel in fixed if rel in files]
    dropped = sorted(rel for rel in fixed if rel not in files)
    added = sorted(rel for rel in files if rel not in fixed)

    # Keep each kept entry's own indentation and formatting, so a re-run only
    # changes the entries it actually had to add or drop.
    body = ["  " + fixed[rel].strip() for rel in kept]
    body.extend(entry_for(rel, today) for rel in added)
    out = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(body)
        + "\n</urlset>\n"
    )
    return out, added, dropped


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and repair sitemap.xml.")
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero when sitemap.xml is out of date")
    args = parser.parse_args()

    current = SITEMAP.read_text(encoding="utf-8") if SITEMAP.exists() else ""
    out, added, dropped = build()
    if out == current:
        print("sitemap: up to date (%d URLs)" % out.count("<url>"))
        return 0
    if args.check:
        print("sitemap: out of date", file=sys.stderr)
        for rel in added:
            print("  + %s" % url_for(rel), file=sys.stderr)
        for rel in dropped:
            print("  - %s (page is gone)" % url_for(rel), file=sys.stderr)
        return 1
    SITEMAP.write_text(out, encoding="utf-8")
    print("sitemap: %d added, %d removed, %d URLs"
          % (len(added), len(dropped), out.count("<url>")))
    for rel in added:
        print("  + %s" % url_for(rel))
    for rel in dropped:
        print("  - %s (page is gone)" % url_for(rel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
