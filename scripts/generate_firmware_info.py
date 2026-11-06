#!/usr/bin/env python3
"""Write a README page for every firmware project whose README names Updater CE.

The site renders a project's README at request time on firmware_info.html.
Search engines and answer engines only see that page when they run scripts, so
this generator writes the same document as plain HTML with a stable URL:

    firmware-info/<owner>-<repo>.html    one project README
    firmware-info/index.html             every generated README page
    firmware-info/manifest.js            repo -> page map, read by the site

Only projects whose README mentions Updater CE (or Updater Community Edition)
get a page: the goal is a curated set of projects that speak for themselves on
our site, not a mirror of every repository. Everything else keeps using the
live reader on firmware_info.html.

Markdown handling is imported from generate_doc_pages.py, so relative links,
images, tables, fenced code and the raw-HTML allowlist behave exactly like the
release-notes pages.

Usage:
    python scripts/generate_firmware_info.py [--refresh] [--limit N]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import generate_doc_pages as gdp  # noqa: E402  (path set above)

ROOT = gdp.ROOT
SITE = gdp.SITE
BRAND = gdp.BRAND
esc = gdp.esc

README_PATHS = ("README.md", "readme.md", "Readme.md", "README.markdown", "README.MD", "docs/README.md")
MENTION = re.compile(r"updater\s+ce\b|updater\s+community\s+edition", re.I)

_MANIFEST_REPOS: set[str] | None = None


def manifest_repos() -> set[str]:
    """Repositories an active ``<package>`` in slidia_manifest.xml lists.

    A project that only exists in the feeds still gets a README page, but the
    page must not offer an Updater CE route: the app has no package entry to
    install it from.
    """
    global _MANIFEST_REPOS
    if _MANIFEST_REPOS is None:
        _MANIFEST_REPOS = {
            str(pkg.get("repo") or "").strip().lower()
            for pkg in gdp.load_manifest()
            if str(pkg.get("repo") or "").strip()
        }
    return _MANIFEST_REPOS


# ---------------------------------------------------------------- github data


def use_config_token() -> str:
    """Fall back to the site's own token list when no env token is set.

    config.ini is already public: the browser uses the same values to raise the
    anonymous API allowance, so the generator can share them instead of
    spending a second, smaller allowance.
    """
    if gdp.TOKEN:
        return gdp.TOKEN
    try:
        lines = (ROOT / "config.ini").read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        line = line.strip()
        if not re.match(r"^(key_\d+|token)\s*=", line):
            continue
        value = line.split("=", 1)[1].strip()
        if len(value) > 10:
            gdp.TOKEN = value
            return value
    return ""


def http_get(url: str, headers: dict | None = None, timeout: int = 25) -> str:
    request = urllib.request.Request(url, headers=dict(headers or {}))
    request.add_header("User-Agent", "innioasis-site-generator")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


TOKEN_REJECTED = False


def api_json(url: str, refresh: bool = False):
    """Repository API JSON: the configured token first, then an anonymous call.

    A token the API rejects is retired for the rest of the run, and empty
    answers are never cached, so one expired token cannot poison the next run.
    """
    global TOKEN_REJECTED
    cache = ROOT / ".cache" / "firmware-info"
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    path = cache / (key + ".json")
    if not refresh and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    base_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    attempts = []
    if gdp.TOKEN and not TOKEN_REJECTED:
        attempts.append(dict(base_headers, Authorization="Bearer " + gdp.TOKEN))
    attempts.append(base_headers)
    payload = None
    for headers in attempts:
        try:
            payload = json.loads(http_get(url, headers))
            break
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                TOKEN_REJECTED = True
                continue
            payload = [] if "releases" in url else {}
            break
        except Exception as error:  # noqa: BLE001 - a missing feed must not stop the build
            print("  ! %s for %s" % (error, url), file=sys.stderr)
            payload = [] if "releases" in url else {}
            break
    if payload not in (None, {}, []):
        try:
            path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass
    return payload if payload is not None else {}


def fetch_readme(repo: str, refresh: bool = False) -> tuple[str, str]:
    """Read the repository README: raw hosts first (no quota), API after."""
    tries = [("HEAD", name) for name in README_PATHS] + [("main", "README.md"), ("master", "README.md")]
    for ref, name in tries:
        try:
            markdown = http_get("https://raw.githubusercontent.com/%s/%s/%s" % (repo, ref, name))
        except Exception:  # noqa: BLE001 - a missing file is a normal answer
            continue
        if markdown.strip():
            return markdown, name
    readme = api_json("https://api.github.com/repos/%s/readme" % repo, refresh=refresh)
    if isinstance(readme, dict) and readme.get("content"):
        try:
            markdown = base64.b64decode(str(readme["content"]).replace("\n", "")).decode("utf-8", "replace")
            if markdown.strip():
                return markdown, str(readme.get("path") or "README.md")
        except (ValueError, TypeError):
            pass
    return "", ""


def download_snapshot(repo: str, refresh: bool = False) -> dict:
    """The archive download total for the project's public releases."""
    downloads = 0
    for page in (1, 2, 3):
        batch = api_json(
            "https://api.github.com/repos/%s/releases?per_page=100&page=%d" % (repo, page),
            refresh=refresh,
        )
        releases = [entry for entry in batch if isinstance(entry, dict)] if isinstance(batch, list) else []
        for release in releases:
            if release.get("draft"):
                continue
            for asset in release.get("assets") or []:
                downloads += int(asset.get("download_count") or 0)
        if len(releases) < 100:
            break
    return {"downloads": downloads}


# ---------------------------------------------------------------- page pieces


def repo_slug(repo: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", repo.lower()).strip("-") or "firmware"


def repo_group(catalog: list[dict]) -> list[dict]:
    """One entry per repository, keeping every model that ships from it."""
    groups: dict[str, dict] = {}
    for item in catalog:
        repo = str(item.get("repo") or "").strip()
        if "/" not in repo:
            continue
        key = repo.lower()
        entry = groups.setdefault(key, {"repo": repo, "items": []})
        entry["items"].append(item)
    return list(groups.values())


def stat_tile(label: str, name: str, value, note: str = "", extra: str = "") -> str:
    shown = "—" if value in (None, "") else (f"{value:,}" if isinstance(value, int) else esc(value))
    note_html = ('<span class="lumen-stat-note" data-stat-note="%s">%s</span>' % (esc(name), esc(note))) if note else ""
    return (
        '<div class="lumen-stat%s"><span class="lumen-stat-label">%s</span>'
        '<strong class="lumen-stat-value" data-stat="%s">%s</strong>%s</div>'
        % (extra, esc(label), esc(name), shown, note_html)
    )


def icon_html(item: dict) -> str:
    icon = str((item or {}).get("icon") or "")
    if icon:
        return ('<span class="lumen-release-icon" aria-hidden="true">'
                '<img src="%s" width="40" height="40" alt="" loading="lazy" '
                'style="width:40px;height:40px;object-fit:cover;border-radius:10px;display:block;"></span>' % esc(icon))
    return ('<span class="lumen-release-icon lumen-release-icon--generic" aria-hidden="true">'
            + gdp.COG_SVG + "</span>")


def readme_context(repo: str) -> dict:
    """The link-rewriting context for a repository source.

    The Python renderer reads raw_dir/blob_dir, docs-viewer.js reads
    dirRaw/dirBlob; both are set so a static page and the live reader rewrite
    a README's relative links the same way.
    """
    return {
        "kind": "github",
        "host": "Repository",
        "repo": repo,
        "ref": "HEAD",
        "path": "README.md",
        "raw_dir": "https://raw.githubusercontent.com/%s/HEAD/" % repo,
        "blob_dir": "https://github.com/%s/blob/HEAD/" % repo,
        "dirRaw": "https://raw.githubusercontent.com/%s/HEAD/" % repo,
        "dirBlob": "https://github.com/%s/blob/HEAD/" % repo,
        "rawUrl": "https://raw.githubusercontent.com/%s/HEAD/README.md" % repo,
        "blobUrl": "https://github.com/%s/blob/HEAD/README.md" % repo,
        "fileLabel": "README.md",
    }


def readme_page(entry: dict, markdown_html: str, snapshot: dict, readme_name: str = "README.md") -> str:
    items = entry["items"]
    primary = items[0]
    repo = entry["repo"]
    slug = repo_slug(repo)
    repo_name = repo.split("/")[-1]
    readme_file = readme_name or "README.md"
    name = str(primary.get("name") or repo_name)
    models = sorted({str(item.get("model") or "") for item in items if item.get("model")})
    # The hero names the software; the alias line under it carries the
    # repository, the README filename and the page slug, so a search for any
    # of them (Rockbox-y1, readme.md, rockbox-y1-rockbox) can land here too.
    aliases = " · ".join(dict.fromkeys(
        part for part in (readme_file, repo, repo_name, name, slug) if part))
    title = ("About %s (%s) - %s - Innioasis Updater" % (name, ", ".join(models), readme_file)
             if models else "About %s - %s - Innioasis Updater" % (name, readme_file))
    description = gdp.one_line(
        primary.get("description") or
        "%s firmware README, with its Firmware Archive download total and the Updater CE install route." % name,
        180,
    )
    canonical = "%s/firmware-info/%s.html" % (SITE, slug)
    guide = str(primary.get("guide") or "guide.html?model=%s&software=%s" % (
        primary.get("model") or "", primary.get("slug") or ""))
    directory = "firmware.html?model=%s&software=%s" % (
        primary.get("model") or "", primary.get("slug") or "")

    meta_bits = []
    if models:
        meta_bits.append(esc(" · ".join(models)))

    actions = ['<a class="lumen-button lumen-button--primary" href="../%s">Open the %s guide</a>'
               % (esc(guide.lstrip("./")), esc(name))]
    if str(repo or "").strip().lower() in manifest_repos():
        actions.append('<a class="lumen-button" href="../%s">Install with Updater CE</a>'
                       % esc(directory.lstrip("./")))
    if primary.get("benefits"):
        actions.append('<a class="lumen-button" href="../%s">Why %s?</a>'
                       % (esc(str(primary["benefits"]).lstrip("./")), esc(name)))

    stats = stat_tile("Downloads from Firmware Archive", "downloads", snapshot.get("downloads"))

    main = (
        '<main id="main" class="lumen-guide lumen-doc-page lumen-release-page" data-firmware-info '
        'data-repo="%s">\n'
        '  <p class="lumen-doc-back"><a href="../firmware.html">← Firmware Downloads</a></p>\n'
        '  <header class="lumen-doc-head">\n'
        '    <div class="lumen-release-head">%s<div class="lumen-release-titles">'
        '<p class="lumen-kicker">Firmware README · %s</p><h1>About %s</h1></div></div>\n'
        '    <p class="lumen-lead">%s</p>\n'
        '    <p class="lumen-meta">Also known as: %s</p>\n'
        '    <div class="lumen-release-tag-row">%s</div>\n'
        '    <div class="lumen-doc-actions">%s</div>\n'
        '  </header>\n'
        '  <section class="lumen-firmware-stats" aria-label="Project statistics">%s</section>\n'
        '  <p class="lumen-meta" id="fi-stats-note"></p>\n'
        '  <article class="lumen-doc-body lumen-firmware-readme" id="fi-body">%s</article>\n'
        '</main>\n'
    ) % (
        esc(repo), icon_html(primary), esc(" · ".join(models) or "project"), esc(name),
        esc(description), esc(aliases), "".join('<span>%s</span>' % bit for bit in meta_bits),
        "".join(actions), stats, markdown_html,
    )
    return page_document(title, description, canonical, main, slug)


def page_document(title: str, description: str, canonical: str, main: str, slug: str) -> str:
    return (
        '<!doctype html>\n<html lang="en"><head>\n'
        '  <meta charset="utf-8">\n'
        '  <meta name="author" content="Ryan Specter &amp; Innioasis Community">\n'
        '  <meta name="creator" content="Ryan Specter &amp; Innioasis Community">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <title>%(title)s</title>\n'
        '  <meta name="description" content="%(description)s">\n'
        '  <meta name="robots" content="index, follow">\n'
        '  <link rel="canonical" href="%(canonical)s">\n'
        '  <meta property="og:type" content="article">\n'
        '  <meta property="og:site_name" content="%(brand)s">\n'
        '  <meta property="og:title" content="%(title)s">\n'
        '  <meta property="og:description" content="%(description)s">\n'
        '  <meta property="og:url" content="%(canonical)s">\n'
        '  <meta name="twitter:card" content="summary_large_image">\n'
        '  <link rel="icon" href="../y1_illustration.png">\n'
        '  <link rel="stylesheet" href="../site-theme.css?v=20260803">\n'
        '  <link rel="stylesheet" href="../lumen.css?v=20261113readme">\n'
        '  <link rel="stylesheet" href="../site-pages.css?v=20260818">\n'
        '  <link rel="stylesheet" href="../site-toolbar.css?v=20261105dockclose">\n'
        '  <link rel="stylesheet" href="../docs-viewer.css?v=20261113readme">\n'
        '  <script src="../site-init.js?v=20260803" defer></script>\n'
        '</head>\n<body class="site-themes-app">\n'
        '<a class="lumen-skip-link" href="#main">Skip to content</a>\n'
        '<div id="nav-root"></div>\n'
        '%(main)s'
        '<div id="footer-root"></div><div id="support-toolbar-slot"></div>\n'
        '<script src="../firmware-catalog.js?v=20261104cite" defer></script>\n'
        '<script src="../docs-viewer.js?v=20261104cite" defer></script>\n'
        '<script src="../firmware-info.js?v=20261104cite" defer></script>\n'
        '<script src="../nav.js?v=20261113noticefilter" defer></script>\n'
        '<script src="../site-i18n.js?v=20261113blocklist" defer></script>\n'
        '</body></html>\n'
    ) % {
        "title": esc(title),
        "description": esc(description),
        "canonical": esc(canonical),
        "brand": esc(BRAND),
        "main": main,
    }


def index_page(entries: list[dict]) -> str:
    cards = []
    for entry in entries:
        items = entry["items"]
        primary = items[0]
        name = str(primary.get("name") or entry["repo"].split("/")[-1])
        models = sorted({str(item.get("model") or "") for item in items if item.get("model")})
        cards.append(
            '<article class="lumen-card"><small>%s</small>'
            '<h3><a href="%s.html">%s README</a></h3>'
            '<p>%s</p></article>'
            % (esc(" · ".join(models) or "project"), esc(repo_slug(entry["repo"])), esc(name),
               esc(gdp.one_line(primary.get("description") or "", 140)))
        )
    main = (
        '<main id="main" class="lumen-guide lumen-doc-page">\n'
        '  <p class="lumen-doc-back"><a href="../firmware.html">← Firmware Downloads</a></p>\n'
        '  <header class="lumen-doc-head">\n'
        '    <p class="lumen-kicker">Firmware READMEs</p>\n'
        '    <h1>Read the project notes before you install.</h1>\n'
        '    <p class="lumen-lead">Community firmware project READMEs published here in the site style '
        'with their release statistics and guided Updater CE install route. Every project also '
        'opens through the live reader on <a href="../firmware_info.html">firmware_info.html</a>.</p>\n'
        '  </header>\n'
        '  <div class="lumen-grid">%s</div>\n'
        '</main>\n'
    ) % "".join(cards)
    return page_document(
        "Firmware READMEs - Innioasis Updater",
        "Community firmware project READMEs with release statistics and the guided Updater CE install route.",
        SITE + "/firmware-info/index.html",
        main,
        "index",
    )


def manifest_js(entries: list[dict]) -> str:
    mapping = {}
    for entry in entries:
        mapping[entry["repo"].lower()] = {
            "page": "firmware-info/%s.html" % repo_slug(entry["repo"]),
            "name": str(entry["items"][0].get("name") or ""),
            "slugs": sorted({str(item.get("slug") or "") for item in entry["items"] if item.get("slug")}),
        }
    return (
        "/* Generated by scripts/generate_firmware_info.py - do not edit by hand.\n"
        "   Repositories whose README names Updater CE, mapped to their static page.\n"
        "   Release-table icons link here; anything missing opens firmware_info.html. */\n"
        "window.INNIOASIS_README_PAGES = "
        + json.dumps(mapping, indent=2, sort_keys=True)
        + ";\n"
    )


# ---------------------------------------------------------------------- build


def build(refresh: bool = False, limit: int = 0) -> None:
    use_config_token()
    gdp.DISCOVERED_MD_SOURCES.clear()
    catalog = gdp.load_catalog()
    manifest = gdp.load_manifest()
    software = gdp.build_software(catalog, manifest)
    groups = repo_group(software)
    out_dir = ROOT / "firmware-info"
    out_dir.mkdir(exist_ok=True)
    print("repositories: %d" % len(groups))

    entries: list[dict] = []
    sitemap_urls: list[str] = []
    for group in groups[: limit or None]:
        repo = group["repo"]
        markdown, path = fetch_readme(repo, refresh=refresh)
        if not markdown.strip():
            print("  %-34s no README" % repo)
            continue
        snapshot = download_snapshot(repo, refresh=refresh)
        markup = gdp.markdown_to_html(markdown, readme_context(repo))
        slug = repo_slug(repo)
        (out_dir / (slug + ".html")).write_text(readme_page(group, markup, snapshot, path), encoding="utf-8")
        entries.append(group)
        sitemap_urls.append("%s/firmware-info/%s.html" % (SITE, slug))
        print("  %-34s page written from %s" % (repo, path or "README"))

    extra_urls, _ = gdp.render_discovered_markdown_pages(software, refresh=refresh)
    sitemap_urls.extend(extra_urls)

    (out_dir / "index.html").write_text(index_page(entries), encoding="utf-8")
    (out_dir / "manifest.js").write_text(manifest_js(entries), encoding="utf-8")
    sitemap_urls.append(SITE + "/firmware-info/index.html")
    gdp.update_sitemap(sitemap_urls)
    print(
        "done: %d README pages, %d linked doc pages (manifest: firmware-info/manifest.js)"
        % (len(entries), len(extra_urls))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate static firmware README pages.")
    parser.add_argument("--refresh", action="store_true", help="ignore the on-disk API cache")
    parser.add_argument("--limit", type=int, default=0, help="only the first N repositories")
    args = parser.parse_args()
    build(refresh=args.refresh, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
