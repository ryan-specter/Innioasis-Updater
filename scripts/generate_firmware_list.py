#!/usr/bin/env python3
"""Render ``firmware-list.html``: a static, crawlable copy of the archive.

``firmware.html`` draws its release table with JavaScript from the GitHub API.
A crawler that does not run that script, or a reader whose network blocks
``api.github.com``, therefore sees an empty table. This generator writes every
listing as plain HTML with one anchor per release, and publishes the same
facts as schema.org structured data: the device model, the software option,
the project that authors it, the original download URL and each portable
(repackaged) download URL.

The data comes from ``feeds/firmware-releases.json``, written by
``scripts/generate_backup_feeds.py`` in the same workflow run, so the static
page, the app's offline feed and the JSON/Atom feeds always describe the same
releases. ``firmware.html`` gets the same facts injected between the SEO
markers below, so the dynamic page carries the catalogue for engines that
execute scripts.

Usage:
    python scripts/generate_firmware_list.py [--refresh]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import re
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import generate_doc_pages as gdp  # noqa: E402

ROOT = gdp.ROOT
SITE = gdp.SITE
FEED_JSON = ROOT / "feeds" / "firmware-releases.json"
LEGACY_JSON = ROOT / "feeds" / "releases.json"
OUT_PAGE = ROOT / "firmware-list.html"
DYNAMIC_PAGE = ROOT / "firmware.html"

SEO_BEGIN = "<!-- BEGIN GENERATED FIRMWARE SEO -->"
SEO_END = "<!-- END GENERATED FIRMWARE SEO -->"

DEVICE_NAMES = {
    "Y1": "Innioasis Y1",
    "Y2": "Innioasis Y2",
    "G1": "Innioasis G1",
    "G3": "Innioasis G3",
    "G5": "Innioasis G5",
    "Q8": "Innioasis Q8",
    "R1": "Innioasis R1",
    "PR1": "Innioasis PR1",
    "D1": "Innioasis D1",
    "A5": "Timmkoo A5",
    "Q5": "Timmkoo Q5",
    "Q3": "Timmkoo Q3",
}

PLATFORM_LABELS = {
    "windows": "Windows",
    "windows-arm64": "Windows on ARM",
    "linux": "Linux",
    "linux-arm64": "Linux on ARM",
    "macos": "macOS",
}

AUTHOR_ORG = {"@type": "Organization", "name": "Innioasis Community",
              "url": "https://github.com/y1-community"}


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def device_name(model: str) -> str:
    model = str(model or "").upper()
    return DEVICE_NAMES.get(model) or ("Innioasis " + model if model else "Innioasis player")


def human_size(size) -> str:
    try:
        value = int(size)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    if value >= 1024 ** 3:
        return "%.2f GB" % (value / 1024 ** 3)
    return "%.0f MB" % max(1, round(value / 1024 ** 2))


# ---------------------------------------------------------------- data


def load_feed(refresh: bool = False) -> dict:
    """The app-facing feed when it exists, else whatever data is on disk."""
    if FEED_JSON.exists():
        try:
            data = json.loads(FEED_JSON.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("repos"), dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    if LEGACY_JSON.exists():
        try:
            data = json.loads(LEGACY_JSON.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("repos"), dict):
                repos = {
                    key: list(info.get("releases") or [])
                    for key, info in (data.get("repos") or {}).items()
                    if isinstance(info, dict)
                }
                return {"repos": repos, "packages": [], "mirrors": {},
                        "repo_info": {}, "generated_at": str(data.get("generated_at") or ""),
                        "schema_version": 1}
        except (OSError, json.JSONDecodeError):
            pass

    # No feed yet: ask GitHub directly so a local run still produces a page.
    repos: dict[str, list[dict]] = {}
    for repo in sorted({str(item.get("repo") or "") for item in gdp.load_catalog()
                        if item.get("repo")}):
        repos[repo] = [entry for entry in gdp.fetch_releases(repo, refresh=refresh)
                       if not entry.get("draft")]
    return {"repos": repos, "packages": gdp.load_manifest(), "mirrors": {},
            "repo_info": {}, "generated_at": dt.datetime.now(dt.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"), "schema_version": 1}


def releases_for(feed: dict, repo: str) -> list[dict]:
    wanted = str(repo or "").strip().lower()
    for key, value in (feed.get("repos") or {}).items():
        if str(key).strip().lower() == wanted and isinstance(value, list):
            return [entry for entry in value if isinstance(entry, dict) and not entry.get("draft")]
    return []


def mirrors_for(feed: dict, repo: str) -> list[dict]:
    """Portable mirror entries whose ``source_repo`` is this repository."""
    wanted = str(repo or "").strip().lower()
    found = []
    for key, value in (feed.get("mirrors") or {}).items():
        if not isinstance(value, dict):
            continue
        source = str(value.get("source_repo") or "").strip().lower()
        if source == wanted:
            entry = dict(value)
            entry["mirror_repo"] = str(value.get("mirror_repo") or key)
            found.append(entry)
    return found


def package_asset(release: dict, package_name: str) -> dict:
    """The release file Updater CE installs: the named package, else a ROM zip."""
    assets = [a for a in (release.get("assets") or []) if isinstance(a, dict)]
    wanted = str(package_name or "").strip().lower()
    for asset in assets:
        if wanted and str(asset.get("name") or "").lower() == wanted:
            return asset
    for asset in assets:
        name = str(asset.get("name") or "").lower()
        if re.match(r"^rom.*\.zip$", name) or name in ("system.zip", "update.zip"):
            return asset
    for asset in assets:
        if str(asset.get("name") or "").lower().endswith(".zip"):
            return asset
    return {}


def portable_packages(mirrors: list[dict], tag: str, asset_name: str) -> list[dict]:
    """Portable builds of one original asset, best platform first."""
    out: list[dict] = []
    wanted_tag = str(tag or "").strip()
    wanted_asset = str(asset_name or "").strip().lower()
    for mirror in mirrors:
        releases = mirror.get("releases")
        if isinstance(releases, dict):
            entry = releases.get(wanted_tag)
        else:
            entry = next((r for r in (releases or []) if str(r.get("tag") or "") == wanted_tag), None)
        if not isinstance(entry, dict):
            continue
        for source_name, info in (entry.get("assets") or {}).items():
            if not isinstance(info, dict):
                continue
            if wanted_asset and str(source_name).strip().lower() != wanted_asset:
                continue
            for key, pkg in (info.get("packages") or {}).items():
                if not isinstance(pkg, dict) or not pkg.get("url"):
                    continue
                out.append({
                    "platform": str(key),
                    "label": PLATFORM_LABELS.get(str(key), str(key)),
                    "name": str(pkg.get("name") or ""),
                    "url": str(pkg.get("url") or ""),
                    "size": int(pkg.get("size") or 0),
                    "mirror": str(mirror.get("mirror_repo") or ""),
                })
    out.sort(key=lambda item: list(PLATFORM_LABELS).index(item["platform"])
             if item["platform"] in PLATFORM_LABELS else 99)
    return out


def repo_owner(repo: str) -> str:
    owner = str(repo or "").split("/")[0].strip()
    return owner


def repo_author(feed: dict, repo: str) -> dict:
    owner = repo_owner(repo)
    info = {}
    for key, value in (feed.get("repo_info") or {}).items():
        if str(key).strip().lower() == str(repo).strip().lower() and isinstance(value, dict):
            info = value
            break
    name = str(info.get("owner") or owner or "Innioasis Community")
    author = {"@type": "Organization", "name": name, "url": "https://github.com/" + (owner or "y1-community")}
    return author


# ---------------------------------------------------------------- page


def release_anchor(item: dict, tag: str) -> str:
    return "%s-%s" % (item.get("slug") or "release", gdp.tag_slug(tag))


def notes_url(item: dict, tag: str) -> str:
    path = ROOT / "release-notes" / str(item.get("slug") or "") / (gdp.tag_slug(tag) + ".html")
    if path.exists():
        return "%s/release-notes/%s/%s.html" % (SITE, item["slug"], gdp.tag_slug(tag))
    return "%s/firmware.html?model=%s&amp;software=%s" % (
        SITE, urllib.parse.quote(item.get("model") or ""), urllib.parse.quote(item.get("slug") or ""))


def static_notes_url(item: dict, tag: str) -> str:
    """The generated copy of a release's notes, or "" when it was not written."""
    slug = str(item.get("slug") or "")
    if not slug:
        return ""
    path = ROOT / "release-notes" / slug / (gdp.tag_slug(tag) + ".html")
    if not path.exists():
        return ""
    return "%s/release-notes/%s/%s.html" % (SITE, slug, gdp.tag_slug(tag))


def parsed_notes_url(item: dict, tag: str) -> str:
    """The live release-notes parser: the page a reader should land on.

    notes_url() keeps the generated static copy for search engines, which is
    never a click target.
    """
    repo = str(item.get("repo") or "")
    author, _, project = repo.partition("/")
    params = {
        "author": author,
        "project": project,
        "version": tag,
        "repo": repo,
        "tag": tag,
        "model": str(item.get("model") or ""),
        "software": str(item.get("slug") or ""),
        "name": str(item.get("name") or ""),
    }
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value})
    return "%s/release_notes.html?%s" % (SITE, query)


def software_section(item: dict, releases: list[dict], mirrors: list[dict], feed: dict) -> tuple[str, dict]:
    """One software/model block: a table of releases plus its structured data."""
    label = gdp.software_label(item)
    model = str(item.get("model") or "").upper()
    device = device_name(model)
    repo = str(item.get("repo") or "")
    package_name = str(item.get("packageName") or "")
    author = repo_author(feed, repo)
    guide = SITE + "/" + str(item.get("guide") or "").lstrip("./") if item.get("guide") else (
        "%s/guide.html?model=%s&software=%s" % (SITE, model, item.get("slug")))
    project_page = gdp.firmware_page_for(repo) or ("%s/firmware-info.html?repo=%s" % (
        SITE, urllib.parse.quote(repo, safe="")))

    rows: list[str] = []
    latest_ld: dict = {}
    for release in releases:
        tag = str(release.get("tag_name") or "").strip()
        if not tag:
            continue
        asset = package_asset(release, package_name)
        asset_url = str(asset.get("browser_download_url") or "")
        asset_size = int(asset.get("size") or 0)
        published = str(release.get("published_at") or release.get("created_at") or "")[:10]
        portable = portable_packages(mirrors, tag, str(asset.get("name") or ""))
        title = str(release.get("name") or "").strip() or ("%s %s" % (label, tag))
        anchor = release_anchor(item, tag)
        notes = notes_url(item, tag)
        live_notes = parsed_notes_url(item, tag)
        # The info glyph links the generated page; the version and the
        # trailing text link stay on the live reader.
        info_notes = static_notes_url(item, tag) or live_notes

        download_cell = []
        if asset_url:
            download_cell.append(
                '<a href="%s" rel="nofollow">%s</a> <span class="lumen-meta">%s</span>'
                % (esc(asset_url), esc(str(asset.get("name") or "Download")), esc(human_size(asset_size))))
        else:
            download_cell.append('<span class="lumen-meta">No package file</span>')
        if portable:
            links = ", ".join(
                '<a href="%s" rel="nofollow">%s</a>' % (esc(p["url"]), esc(p["label"]))
                for p in portable)
            download_cell.append('<div class="lumen-meta">Portable: %s</div>' % links)

        meta = [published] if published else []
        if release.get("prerelease"):
            meta.append("preview build")
        rows.append(
            '<tr id="%s"><td><a class="lumen-version-link" href="%s" title="Release notes for %s">'
            '<strong>%s</strong></a>'
            '<a class="lumen-readme-info" href="%s" title="Release notes for %s" aria-label="Release notes for %s">&#9432;</a>'
            '<div class="lumen-meta">%s</div></td>'
            '<td><a href="%s">%s</a></td>'
            '<td>%s</td>'
            '<td><a href="%s">Release notes</a></td></tr>'
            % (esc(anchor), esc(live_notes), esc(tag), esc(tag),
               esc(info_notes), esc(tag), esc(tag),
               esc(" · ".join(meta)),
               esc(str(release.get("html_url") or project_page)), esc(title),
               "".join(download_cell), esc(live_notes)))

        if not latest_ld:
            latest_ld = {
                "@type": "SoftwareApplication",
                "name": "%s for %s" % (label, device),
                "alternateName": "%s on %s" % (str(item.get("name") or label), device),
                "applicationCategory": "Firmware",
                "applicationSubCategory": str(item.get("name") or label),
                "operatingSystem": device,
                "softwareVersion": tag,
                "datePublished": published or None,
                "downloadUrl": asset_url or None,
                "installUrl": guide,
                "releaseNotes": notes.replace("&amp;", "&"),
                "sameAs": str(release.get("html_url") or ""),
                "url": "%s/firmware-list.html#%s" % (SITE, anchor),
                "author": author,
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD",
                           "availability": "https://schema.org/InStock"},
                "isAccessibleForFree": True,
                "encodingFormat": "application/zip",
                "additionalProperty": [
                    {"@type": "PropertyValue",
                     "name": "Portable package for %s" % p["label"],
                     "value": p["url"]} for p in portable
                ],
            }
            latest_ld = {key: value for key, value in latest_ld.items() if value not in (None, "", [])}
            if asset_size:
                latest_ld["fileSize"] = str(asset_size)
            icon = str(item.get("icon") or "")
            if icon:
                latest_ld["image"] = icon

    description = str(item.get("description") or ("%s for the %s." % (label, device)))
    block = [
        '<section class="lumen-section firmware-list-software" id="%s">' % esc(item.get("slug") or ""),
        '<div class="lumen-section-head"><div>',
        '<p class="lumen-kicker">%s · %s</p>' % (esc(device), esc(str(item.get("name") or label))),
        "<h3>%s</h3>" % esc(label),
        '<p class="lumen-meta">%s</p>' % esc(description),
        '<p class="lumen-meta">By <a href="https://github.com/%s" rel="noopener noreferrer">%s</a>'
        ' · <a href="%s">Project page</a> · <a href="%s">Install guide</a></p>'
        % (esc(repo_owner(repo)), esc(repo_owner(repo) or "Innioasis Community"),
           esc(project_page.replace("&amp;", "&")), esc(guide)),
        "</div></div>",
        '<div class="lumen-table-wrap"><table class="lumen-release-table">',
        "<caption>%s releases for the %s</caption>" % (esc(label), esc(device)),
        "<thead><tr><th scope=\"col\">Release</th><th scope=\"col\">Package</th>"
        "<th scope=\"col\">Download</th><th scope=\"col\"><span class=\"lumen-visually-hidden\">"
        "Notes</span></th></tr></thead>",
        "<tbody>%s</tbody>" % "".join(rows),
        "</table></div></section>",
    ]
    if not rows:
        block = [
            '<section class="lumen-section firmware-list-software" id="%s">' % esc(item.get("slug") or ""),
            '<div class="lumen-section-head"><div><p class="lumen-kicker">%s</p><h3>%s</h3>' % (esc(device), esc(label)),
            '<p class="lumen-meta">No published releases are listed for this software yet. '
            '<a href="%s">Open it in the archive</a>.</p></div></div></section>'
            % esc(project_page.replace("&amp;", "&")),
        ]
    return "".join(block), latest_ld


def render_page(feed: dict, software: list[dict]) -> tuple[str, list[dict]]:
    generated_at = str(feed.get("generated_at") or "")[:10] or dt.date.today().isoformat()
    models: dict[str, list[str]] = {}
    cards: list[dict] = []
    total = 0
    for item in software:
        releases = releases_for(feed, str(item.get("repo") or ""))
        releases.sort(key=lambda entry: str(entry.get("published_at") or ""), reverse=True)
        total += len(releases)
        block, ld = software_section(item, releases, mirrors_for(feed, str(item.get("repo") or "")), feed)
        model = str(item.get("model") or "").upper() or "OTHER"
        models.setdefault(model, []).append(block)
        if ld:
            cards.append(ld)

    sections = []
    for model in sorted(models):
        sections.append(
            '<section class="lumen-section" id="model-%s" aria-labelledby="model-%s-title">'
            '<div class="lumen-section-head"><div><p class="lumen-kicker">%s</p>'
            '<h2 id="model-%s-title">%s software and firmware</h2>'
            '<p class="lumen-meta">Every listed release for this model, with the original '
            'download URL and the portable packages built for each computer.</p></div></div>%s</section>'
            % (esc(model.lower()), esc(model.lower()), esc(device_name(model)),
               esc(model.lower()), esc(device_name(model)), "".join(models[model])))

    toc = ", ".join('<a href="#model-%s">%s</a>' % (esc(m.lower()), esc(device_name(m)))
                    for m in sorted(models))

    item_list = {
        "@type": "ItemList",
        "name": "Innioasis and Timmkoo firmware by software and model",
        "description": "Every software option in the Innioasis Firmware Archive, its author, "
                       "its current version, its download URL and its portable packages.",
        "numberOfItems": len(cards),
        "itemListElement": [
            {"@type": "ListItem", "position": position + 1, "item": card}
            for position, card in enumerate(cards)
        ],
    }
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": "Firmware list - every Innioasis and Timmkoo release",
                "url": SITE + "/firmware-list.html",
                "description": "A static, searchable list of every firmware and software release "
                               "for Innioasis Y1, Y2, G1, G3, G5, Q8, R1, PR1, D1 and Timmkoo A5, Q5, Q3.",
                "dateModified": generated_at,
                "author": AUTHOR_ORG,
                "isPartOf": {"@type": "WebSite", "name": "Innioasis Updater", "url": SITE + "/"},
                "mainEntity": item_list,
            },
            item_list,
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Firmware archive",
                     "item": SITE + "/firmware.html"},
                    {"@type": "ListItem", "position": 3, "name": "Firmware list",
                     "item": SITE + "/firmware-list.html"},
                ],
            },
        ],
    }

    main = [
        '<main id="main" class="lumen-directory">',
        '<header class="lumen-directory-hero"><div>',
        '<p class="lumen-kicker">Innioasis &amp; Timmkoo Firmware Archive</p>',
        "<h1>Firmware list: every release, model and download</h1></div><div>",
        "<p>Every release listed for every model, in plain HTML. Each entry names the software, "
        "its author, the device model, the original package and the portable build for Windows, "
        "macOS and Linux.</p>",
        '<p class="lumen-meta">Updated %s · %d software options · %d releases</p>'
        % (esc(generated_at), len(cards), total),
        '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="firmware.html">'
        "Open the installer view</a>"
        '<a class="lumen-button" href="feeds/firmware-feed.xml">Atom feed</a>'
        '<a class="lumen-button" href="feeds/firmware-releases.json">JSON data</a></div>',
        '<p class="lumen-meta">Jump to %s.</p></div></header>' % toc,
        "".join(sections),
        '<section class="lumen-section"><div class="lumen-callout">',
        "<h2>Install from a downloaded package</h2>",
        "<p>If this computer cannot reach the firmware archive, download the package on another "
        "device and hand it to Updater CE on the Install page. Updater CE finds the scatter file "
        "inside the archive, including in its <code>Firmware</code> or <code>SP_Flash_Tool</code> "
        "folder, and installs it without a network connection.</p>",
        '<div class="lumen-actions"><a class="lumen-button" href="guide.html#download-updater">'
        "Get Updater CE</a><a class=\"lumen-button\" href=\"troubleshooting.html\">Troubleshooting</a>"
        "</div></div></section>",
        "</main>",
    ]

    head_args = {
        "title": "Firmware list - every Innioasis and Timmkoo release | Innioasis Updater",
        "description": "Every Innioasis and Timmkoo firmware release in one static list: model, "
                       "software, author, original download URL and portable packages for Windows, "
                       "macOS and Linux.",
        "canonical": SITE + "/firmware-list.html",
    }
    extra = [
        '<meta name="keywords" content="Innioasis firmware list, Innioasis stock firmware, '
        'Timmkoo firmware, Rockbox Y1, Rockbox Y2, Y2Linux, Better-Y, Solar, Rondo, firmware download">',
        '<meta property="og:image" content="%s/assets/og-image.png">' % SITE,
        '<link rel="alternate" type="application/atom+xml" href="%s/feeds/firmware-feed.xml" '
        'title="Firmware releases">' % SITE,
        '<link rel="alternate" type="application/json" href="%s/feeds/firmware-releases.json" '
        'title="Firmware release data">' % SITE,
        '<script type="application/ld+json">%s</script>'
        % json.dumps(graph, ensure_ascii=False, separators=(",", ":")),
    ]
    head = gdp.HEAD.format(brand=gdp.BRAND, up="", **head_args).replace(
        "</head>", "\n".join(extra) + "\n</head>")
    foot = gdp.FOOT.format(up="").replace("</body></html>", gdp.FOOT_SCRIPT)
    return head + "".join(main) + foot, cards


# ---------------------------------------------------------------- dynamic page


def seo_block(cards: list[dict], generated_at: str) -> str:
    """The same catalogue, injected into the JavaScript-driven archive page."""
    items = []
    for position, card in enumerate(cards, start=1):
        items.append({
            "@type": "ListItem",
            "position": position,
            "item": {
                "@type": "SoftwareApplication",
                "name": card.get("name"),
                "operatingSystem": card.get("operatingSystem"),
                "applicationCategory": "Firmware",
                "author": card.get("author"),
                "softwareVersion": card.get("softwareVersion"),
                "downloadUrl": card.get("downloadUrl"),
                "releaseNotes": card.get("releaseNotes"),
                "url": card.get("url"),
            },
        })
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ItemList",
                "name": "Innioasis and Timmkoo software by model",
                "numberOfItems": len(items),
                "itemListElement": items,
                "dateModified": generated_at,
            },
            {
                "@type": "DataFeed",
                "name": "Innioasis firmware releases",
                "url": SITE + "/feeds/firmware-releases.json",
                "description": "Machine-readable release data for every catalogue repository, "
                               "used by Updater CE when GitHub is unreachable.",
                "dateModified": generated_at,
                "creator": AUTHOR_ORG,
            },
        ],
    }
    lines = [
        SEO_BEGIN,
        '<link rel="alternate" type="text/html" href="%s/firmware-list.html" '
        'title="Static firmware list">' % SITE,
        '<link rel="alternate" type="application/atom+xml" href="%s/feeds/firmware-feed.xml" '
        'title="Firmware releases">' % SITE,
        '<link rel="alternate" type="application/json" href="%s/feeds/firmware-releases.json" '
        'title="Firmware release data">' % SITE,
        '<meta name="innioasis-catalog" content="%s/feeds/firmware-releases.json">' % SITE,
        '<meta name="innioasis-firmware-list" content="%s/firmware-list.html">' % SITE,
        '<script type="application/ld+json">%s</script>'
        % json.dumps(graph, ensure_ascii=False, separators=(",", ":")),
        SEO_END,
    ]
    return "\n".join(lines)


def inject_dynamic_page(cards: list[dict], generated_at: str) -> bool:
    if not DYNAMIC_PAGE.exists():
        return False
    text = DYNAMIC_PAGE.read_text(encoding="utf-8")
    block = seo_block(cards, generated_at)
    if SEO_BEGIN in text and SEO_END in text:
        start = text.index(SEO_BEGIN)
        end = text.index(SEO_END) + len(SEO_END)
        updated = text[:start] + block + text[end:]
    else:
        updated = text.replace("</head>", block + "\n</head>")
    if updated == text:
        return False
    DYNAMIC_PAGE.write_text(updated, encoding="utf-8")
    return True


# ---------------------------------------------------------------- build


def build(refresh: bool = False) -> None:
    feed = load_feed(refresh=refresh)
    catalog = gdp.load_catalog()
    manifest = gdp.load_manifest()
    software = gdp.build_software(catalog, manifest)
    page, cards = render_page(feed, software)
    OUT_PAGE.write_text(page, encoding="utf-8")
    generated_at = str(feed.get("generated_at") or "")[:10] or dt.date.today().isoformat()
    changed = inject_dynamic_page(cards, generated_at)
    gdp.update_sitemap([SITE + "/firmware-list.html"])
    print("firmware-list.html: %d software options, %d releases%s"
          % (len(cards), sum(len(releases_for(feed, str(i.get('repo') or ''))) for i in software),
             ", firmware.html SEO block updated" if changed else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the static firmware list page.")
    parser.add_argument("--refresh", action="store_true", help="ignore the on-disk GitHub cache")
    args = parser.parse_args()
    build(refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
