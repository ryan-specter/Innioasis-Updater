#!/usr/bin/env python3
"""Write the Rockbox-Y1 / Rockbox-Y2 search landing pages.

Rockbox is listed once in ``slidia_manifest.xml`` and once in
``firmware-catalog.js``, but people search for it by many names: Rockbox,
Rockbox-Y1, Rockbox for Y1, "rockbox y1 install", "how to install rockbox on
y1", "rockbox-y1 tutorial", and the same set again for the Y2. One catalogue
row cannot answer all of those queries, so this generator writes a page for
each intent under a stable, model-scoped URL:

    rockbox-y1/index.html          the Rockbox-Y1 hub
    rockbox-y1/<topic>.html        one intent per page (install, download, …)
    rockbox-y2/index.html          the same for Rockbox-Y2
    rockbox-y2/<topic>.html
    rockbox-rom-download.html      both models' ROM downloads side by side

Every page links to the others, to the hand-written entity pages
(``rockbox-for-y1.html``, ``rockbox-y1-vs-y2.html``, the theme pages), and to
the portable mirror releases that actually hold the ROM zips, so a reader —
or an answer engine summarising the site — lands on something that names the
model and hands over the files.

The mirror releases are read from the GitHub API at build time (with a disk
cache), so the download tables name real assets and real tags. When the API
is unreachable the pages still render, pointing at the release index and the
guided updater flow.

Usage:
    python scripts/generate_rockbox_pages.py [--refresh]
"""
from __future__ import annotations

import datetime
import html
import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://innioasis.app"
BRAND = "Innioasis Updater"
CACHE = ROOT / ".cache" / "rockbox-pages"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
TODAY = datetime.date.today().isoformat()

MODELS = {
    "y1": {
        "key": "y1",
        "dir": "rockbox-y1",
        "model": "Y1",
        "label": "Rockbox-Y1",
        "plain": "Rockbox",
        "software": "rockbox-y1",
        "mirror": "y1-community/rockbox-mirror",
        "stable_tag": "stable-v0.5",
        "rom_name": "rom.zip",
        "type_b": True,
        "guide": "../guides/rockbox-y1.html",
        "software_page": "../rockbox-y1-software.html",
        "restore": "../original-software-y1.html",
        "themes": "../rockbox-y1-themes.html",
        "for_page": "../rockbox-for-y1.html",
        "release_notes": "../release-notes/rockbox-y1/index.html",
        "other": "y2",
        "other_label": "Rockbox-Y2",
        "other_dir": "../rockbox-y2/",
        "build_note": (
            "Y1 community builds are labelled by resolution: 240p builds have the "
            "broadest older-theme compatibility, 360p builds are made for the newer "
            "Y1 theme path."
        ),
    },
    "y2": {
        "key": "y2",
        "dir": "rockbox-y2",
        "model": "Y2",
        "label": "Rockbox-Y2",
        "plain": "Rockbox",
        "software": "rockbox-y2",
        "mirror": "y1-community/y2-rockbox-mirror",
        "stable_tag": "v0.2.5-beta",
        "rom_name": "rom_y2.zip",
        "type_b": False,
        "guide": "../guides/rockbox-y2.html",
        "software_page": "../rockbox-y2-software.html",
        "restore": "../original-software-y2.html",
        "themes": "../rockbox-y2-themes.html",
        "for_page": "../rockbox-for-y2.html",
        "release_notes": "../release-notes/rockbox-y2/index.html",
        "other": "y1",
        "other_label": "Rockbox-Y1",
        "other_dir": "../rockbox-y1/",
        "build_note": (
            "The Y2 port is its own beta line. Read the release notes for the build "
            "you are installing before you rely on a theme or on a feature that "
            "appeared in a later beta."
        ),
    },
}

#: One page per search intent. ``priority`` feeds the sitemap.
TOPICS = [
    ("install", 0.9),
    ("download", 0.9),
    ("portable-zip", 0.8),
    ("requirements", 0.7),
    ("first-start", 0.7),
    ("sd-card", 0.65),
    ("update", 0.65),
    ("restore-stock", 0.75),
    ("dual-boot", 0.65),
    ("troubleshooting", 0.75),
    ("resolution", 0.6),
    ("offline", 0.6),
    ("uninstall", 0.6),
    ("faq", 0.8),
    ("vs-stock", 0.7),
]

TOPIC_TITLES = {
    "install": "Install {L} on the Innioasis {M} (Updater guide)",
    "download": "{L} ROM download: portable flashing packages",
    "portable-zip": "{L} portable ZIP: install without the guided flow",
    "requirements": "What you need before installing {L}",
    "first-start": "{L} first start: music, themes and settings",
    "sd-card": "{L} and the MicroSD card: .rockbox explained",
    "update": "Update {L}: moving to a newer stable or nightly",
    "restore-stock": "Undo {L}: restore the original {M} software",
    "dual-boot": "{L} dual boot: switching back to stock software",
    "troubleshooting": "{L} install problems and how to fix them",
    "resolution": "{L} 240p and 360p builds: choosing a theme path",
    "offline": "{L}: an offline music player with no account",
    "uninstall": "Remove {L} or reset it to defaults",
    "faq": "{L} FAQ: the questions people ask first",
    "vs-stock": "{L} vs Original Software: what actually changes",
}

TOPIC_DESCRIPTIONS = {
    "install": "Install {L} on an Innioasis {M} with Innioasis Updater CE: pick the model, choose Rockbox, take a stable release, and connect the powered-off player only at the prompt.",
    "download": "Download {L} ROM packages from the community portable mirror: per-platform ZIPs, the universal ROM, and how to check which file belongs on your {M}.",
    "portable-zip": "Install {L} from a portable flashing ZIP: which archive matches your computer, how to point Updater CE at it, and what the base ROM folders contain.",
    "requirements": "Before you install {L}: the cable, the model check, the battery state, the computer requirements, and the {M} variant notes that decide which build to take.",
    "first-start": "After {L} boots: where the .rockbox folder comes from, how music and themes are laid out, and the settings worth changing on day one.",
    "sd-card": "How {L} uses the MicroSD card: the .rockbox folder, hidden files, FAT32 formatting, database refreshes, and how to reset settings safely.",
    "update": "Update an existing {L} install with a newer stable or nightly build, without losing the themes and settings that live on the card.",
    "restore-stock": "Return an Innioasis {M} to its original software after {L}: the Original Software route in Updater CE and what to check if the flash stops.",
    "dual-boot": "Keep both systems on one player: how {L} builds hand control back to the original software and back again.",
    "troubleshooting": "{L} install did not finish? Model mismatch, cable, driver and connection-timing checks, in the order worth trying.",
    "resolution": "240p or 360p: how {L} build labels relate to themes, and how to avoid installing a build whose theme path does not match your player.",
    "offline": "Why {L} suits people leaving streaming behind: local files, no account, no subscription, and a library sorted by tags instead of file names.",
    "uninstall": "Two different jobs: restoring the original software, or resetting {L} settings by clearing the .rockbox folder. Both are reversible.",
    "faq": "The {L} questions asked most often: is it safe, which release, Y1 or Y2, themes, updates, and how to go back to stock.",
    "vs-stock": "A side-by-side of {L} and the Innioasis {M} Original Software: library, playback, themes, radio, podcasts, and the restore path.",
}


# ---------------------------------------------------------------- utilities

def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def p(*paragraphs) -> str:
    return "".join("<p>%s</p>" % text for text in paragraphs)


def ul(items) -> str:
    return '<ul class="lumen-benefits-list">%s</ul>' % "".join("<li>%s</li>" % i for i in items)


def ol(items) -> str:
    return '<ol class="lumen-steps">%s</ol>' % "".join("<li>%s</li>" % i for i in items)


def section(title: str, body: str, anchor: str = "") -> str:
    ident = ' id="%s"' % esc(anchor) if anchor else ""
    return '<section class="lumen-guide-section"><h2%s>%s</h2>%s</section>' % (ident, title, body)


def faq_block(faqs) -> str:
    return (
        '<section class="lumen-guide-section"><h2 id="faq">Questions people ask</h2>%s</section>'
        % "".join("<details><summary>%s</summary>%s</details>" % (q, p(a)) for q, a in faqs)
    )


def actions(*links) -> str:
    return '<div class="lumen-actions">%s</div>' % "".join(
        '<a class="lumen-button%s" href="%s">%s</a>' % (" lumen-button--primary" if index == 0 else "", href, text)
        for index, (text, href) in enumerate(links)
    )


def head(title: str, description: str, canonical: str, up: str) -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="author" content="Ryan Specter &amp; Innioasis Community">
  <meta name="creator" content="Ryan Specter &amp; Innioasis Community">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{brand}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="https://innioasis.app/assets/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="https://innioasis.app/assets/og-image.png">
  <link rel="icon" href="{up}y1_illustration.png">
  <link rel="stylesheet" href="{up}site-theme.css?v=20260803">
  <link rel="stylesheet" href="{up}lumen.css?v=20261105hero">
  <link rel="stylesheet" href="{up}site-pages.css?v=20260818">
  <link rel="stylesheet" href="{up}site-toolbar.css?v=20261105dockclose">
  <script src="{up}site-init.js?v=20260803" defer></script>
</head>
<body class="site-themes-app">
<a class="lumen-skip-link" href="#main">Skip to content</a>
<div id="nav-root"></div>
""".format(title=esc(title), description=esc(description), canonical=esc(canonical), up=up, brand=esc(BRAND))


FOOT = """<div id="footer-root"></div><div id="support-toolbar-slot"></div>
<script src="{up}nav.js?v=20261103brand" defer></script>
<script src="{up}site-i18n.js?v=20260830" defer></script>
</body></html>
"""


def jsonld(blocks) -> str:
    return "".join(
        '<script type="application/ld+json">%s</script>' % json.dumps(block, separators=(",", ":")) for block in blocks
    )


def article_ld(title: str, description: str, canonical: str, crumbs) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title,
        "description": description,
        "image": SITE + "/assets/og-image.png",
        "dateModified": TODAY,
        "author": {"@type": "Organization", "name": "Innioasis Community"},
        "publisher": {"@type": "Organization", "name": "Innioasis Updater"},
        "mainEntityOfPage": canonical,
        "about": {"@type": "Product", "name": "Innioasis " + "player"},
    }


def breadcrumb_ld(trail) -> dict:
    """``trail`` is [(name, url), …] ending with the page itself."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": index + 1, "name": name, "item": url}
            for index, (name, url) in enumerate(trail)
        ],
    }


def faq_ld(faqs) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}
            for q, a in faqs
        ],
    }


# ---------------------------------------------------------------- mirror data

def _api(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "innioasis-site-generator",
            "Accept": "application/vnd.github+json",
            **({"Authorization": "Bearer " + TOKEN} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def mirror_releases(repo: str, refresh: bool = False) -> list[dict]:
    """Published releases of a portable mirror repo (cached on disk)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (repo.replace("/", "-") + ".json")
    if path.exists() and not refresh:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    try:
        releases = _api("https://api.github.com/repos/%s/releases?per_page=50" % repo)
    except Exception as error:  # noqa: BLE001 - a build must not fail on the API
        print("  ! could not read %s releases: %s" % (repo, error), file=sys.stderr)
        return []
    if not isinstance(releases, list):
        return []
    slim = [
        {
            "tag_name": str(release.get("tag_name") or ""),
            "name": str(release.get("name") or ""),
            "published_at": str(release.get("published_at") or ""),
            "prerelease": bool(release.get("prerelease")),
            "html_url": str(release.get("html_url") or ""),
            "assets": [
                {
                    "name": str(asset.get("name") or ""),
                    "browser_download_url": str(asset.get("browser_download_url") or ""),
                    "size": int(asset.get("size") or 0),
                }
                for asset in release.get("assets") or []
            ],
        }
        for release in releases
        if isinstance(release, dict)
    ]
    path.write_text(json.dumps(slim, indent=1), encoding="utf-8")
    return slim


def version_key(tag: str) -> tuple:
    """``stable-v0.5`` -> (0, 5), ``v0.2.5-beta`` -> (0, 2, 5)."""
    numbers = re.findall(r"\d+", str(tag or ""))
    return tuple(int(number) for number in numbers[:4])


def stable_release(releases: list[dict], fallback_tag: str) -> dict:
    """The release a visitor should download.

    Newest non-nightly, non-base tag that actually carries ROM zips. Version
    order decides, not publication time: a beta published a few minutes after
    a newer one is still the older build, and a release whose assets are only
    source and checksums cannot be flashed.
    """
    usable = [
        release
        for release in releases
        if release.get("tag_name")
        and "nightly" not in release["tag_name"].lower()
        and "base" not in release["tag_name"].lower()
    ]

    def score(release: dict) -> tuple:
        has_rom = any(
            str(asset.get("name") or "").startswith("rom") and str(asset.get("name") or "").endswith(".zip")
            for asset in release.get("assets") or []
        )
        return (1 if has_rom else 0, version_key(release.get("tag_name") or ""),
                release.get("published_at") or "")

    usable.sort(key=score, reverse=True)
    if usable:
        return usable[0]
    for release in releases:
        if release.get("tag_name") == fallback_tag:
            return release
    return releases[0] if releases else {}


PLATFORM_LABELS = (
    ("windows", "Windows"),
    ("macos", "macOS"),
    ("linux", "Linux"),
)


def platform_rows(release: dict, m) -> list[tuple[str, str, str]]:
    """(label, filename, url) for each per-platform portable ZIP in ``release``."""
    assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets") or []}
    rows = []
    for suffix, label in PLATFORM_LABELS:
        name = "%s-%s.zip" % (m["rom_name"][:-4], suffix)
        if name in assets:
            rows.append(("%s portable ZIP" % label, name, assets[name]))
    if m["rom_name"] in assets:
        rows.append(("Universal ROM package", m["rom_name"], assets[m["rom_name"]]))
    if m.get("type_b"):
        for suffix, label in PLATFORM_LABELS:
            name = "rom_type_b-%s.zip" % suffix
            if name in assets:
                rows.append(("%s Type B portable ZIP" % label, name, assets[name]))
        if "rom_type_b.zip" in assets:
            rows.append(("Type B universal ROM", "rom_type_b.zip", assets["rom_type_b.zip"]))
    return rows


def download_table(m, release: dict) -> str:
    rows = platform_rows(release, m)
    if not rows:
        return (
            '<p class="lumen-doc-status">The mirror release index is the authoritative '
            'list of files: <a href="https://github.com/%s/releases">%s releases</a>.</p>'
            % (esc(m["mirror"]), esc(m["mirror"]))
        )
    body = "".join(
        '<tr><th scope="row">%s</th><td><code>%s</code></td><td><a href="%s" rel="noopener">Download</a></td></tr>'
        % (esc(label), esc(name), esc(url))
        for label, name, url in rows
    )
    tag = release.get("tag_name") or m["stable_tag"]
    return (
        '<table class="lumen-table"><thead><tr><th>Package</th><th>File</th><th>Link</th></tr></thead><tbody>%s</tbody></table>'
        '<p class="lumen-meta">Files come from the <a href="https://github.com/%s/releases/tag/%s" rel="noopener">'
        "%s</a> release of the <a href=\"https://github.com/%s\" rel=\"noopener\">%s</a> portable mirror — the "
        "community repack of the same ROM Updater CE flashes. The universal package is the one to take when "
        "you are not sure; the per-platform ZIPs unpack to the same images.</p>"
        % (body, esc(m["mirror"]), esc(tag), esc(tag), esc(m["mirror"]), esc(m["mirror"]))
    )


def download_summary(m, release: dict) -> str:
    tag = release.get("tag_name") or m["stable_tag"]
    return (
        '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="download.html">%s downloads</a>'
        '<a class="lumen-button" href="%s">Get it in Updater CE</a>'
        '<a class="lumen-button" href="https://github.com/%s/releases/tag/%s" rel="noopener">Mirror release %s</a></div>'
        % (esc(m["label"]), esc(guide_href(m)), esc(m["mirror"]), esc(tag), esc(tag))
    )


def guide_href(m) -> str:
    return "../guide.html?model=%s&amp;software=%s" % (esc(m["model"]), esc(m["software"]))


# ---------------------------------------------------------------- page bodies

def hub_body(m, release) -> tuple[str, str, list, list]:
    other = MODELS[m["other"]]
    lead = (
        "%s is the Innioasis %s build of Rockbox: community firmware that replaces the stock "
        "player with a tag-based library, gapless playback, an equalizer and a deep theme "
        "library. This page is the index for everything on this site about %s — install "
        "steps, ROM downloads from the portable mirror, themes, restoring the original "
        "software, and the fixes worth trying when a flash stops." % (m["label"], m["model"], m["label"])
    )
    sections = [
        section(
            "Rockbox, Rockbox-%s and “Rockbox for %s” are the same software" % (m["model"], m["model"]),
            p(
                "The project publishes one port per player. The catalogue lists it as "
                "<strong>Rockbox</strong> with device <code>%s</code>; search engines, videos and forum "
                "posts call the same build <strong>%s</strong>, <strong>Rockbox for %s</strong>, or "
                "<strong>rockbox-%s</strong> in a URL. Nothing differs between the names — only the "
                "spelling. What does matter is the model: a %s build is not a %s build."
                % (m["model"], m["label"], m["model"], m["model"].lower(), m["model"], other["model"]),
                "The release notes for this software are titled %s release notes so the version "
                "history and the search result agree on the name." % m["label"],
            ),
            "names",
        ),
        section("Start where you are", actions(
            ("Install %s" % m["label"], "install.html"),
            ("Download the ROM", "download.html"),
            ("Full written tutorial", m["guide"]),
            ("Restore the original software", "restore-stock.html"),
        )),
        section(
            "Downloads come from the portable mirror",
            p(
                "Updater CE downloads and flashes the ROM for you. If you want the files in hand — "
                "to flash from another computer, to keep an archive, or to install from a local "
                "package — take them from the <a href=\"https://github.com/%s\" rel=\"noopener\">%s</a> "
                "mirror. Its releases carry the same ROM as per-platform portable ZIPs, including "
                "Type B variants where the %s needs one." % (esc(m["mirror"]), esc(m["mirror"]), m["model"])
            ) + download_summary(m, release),
            "downloads",
        ),
        section(
            "Before you flash",
            ul([
                "Set <strong>Device Model</strong> to <strong>%s</strong> before you pick Rockbox." % m["model"],
                "Prefer a stable release unless you are deliberately testing a nightly build.",
                "Use a data cable and a charged battery; connect the powered-off player only when Updater asks.",
                "The flash replaces the player software. The matching Original Software package is the way back.",
            ]) + p(m["build_note"]),
            "before",
        ),
    ]
    faqs = [
        (
            "Is %s safe to install?" % m["label"],
            "It runs on the same flashing path as the stock firmware, and the community has installed "
            "it on many players. It is still custom firmware on a MediaTek device: an interrupted "
            "flash can leave the player needing a recovery run, so use a good cable, a charged battery "
            "and do not disturb the connection.",
        ),
        (
            "Can I put the %s build on a %s?" % (m["label"], other["model"]),
            "No. The two ports are separate packages. Select %s in Updater CE and use the "
            "<a href=\"%s\">%s pages</a> instead." % (other["model"], m["other_dir"], other["label"]),
        ),
        (
            "How do I go back to the original software?",
            "Choose %s again, select <strong>Original Software</strong>, pick a stable release and run "
            "<strong>Install / Restore</strong>. The <a href=\"restore-stock.html\">restore page</a> walks "
            "through it." % m["model"],
        ),
    ]
    howto = []
    return lead, "".join(sections), faqs, howto


def topic_body(m, slug: str, release) -> tuple[str, str, list, list, list]:
    """(lead, sections html, faqs, howto steps, extra json-ld blocks)."""
    other = MODELS[m["other"]]
    label, model = m["label"], m["model"]
    gui = guide_href(m)
    steps = [
        "Open Innioasis Updater CE and set <strong>Device Model</strong> to <strong>%s</strong>." % model,
        "Choose <strong>Rockbox</strong> in <strong>Software</strong> — the release data may label it %s." % label,
        "Choose a stable release (or the nightly you mean to test).",
        "Click <strong>Install / Restore</strong> and let the package download and extract.",
        "Power the %s fully off, then connect the USB data cable only when Updater asks." % model,
        "Disconnect only after the success message, then start the player.",
    ]
    faqs: list = []
    sections: list[str] = []
    howto: list[str] = []
    extra_ld: list = []

    if slug == "install":
        lead = (
            "Installing %s is a guided flow in Innioasis Updater CE. The order matters more than "
            "the clicking: the model comes first, then the software, then the release, and the "
            "player is connected last — powered off — only when the app asks for it." % label
        )
        sections.append(section("The install, step by step", ol(steps), "steps"))
        sections.append(section(
            "Why the model comes first",
            p(
                "Updater CE filters releases by the model you select. Picking Rockbox before the model "
                "is how people end up staring at a %s package on a %s player. The catalogue row for "
                "this software is <code>%s</code> with device <code>%s</code>, so as long as the model "
                "is right the release list is right."
                % (other["model"], model, m["software"], model),
                "If you would rather not use the app, the same ROM is available as a portable ZIP — "
                "see <a href=\"portable-zip.html\">installing from a portable package</a>.",
            ),
        ))
        sections.append(section("What Updater does with the package", p(
            "It downloads the ROM, unpacks the images, and writes them with MediaTek's download "
            "protocol through either SP Flash Tool or MTKClient depending on your platform. The "
            "player does not need to boot into anything special: it is flashed in preloader mode, "
            "which is why it must be off and connected at the right moment."
        )))
        sections.append(section("Where to go next", actions(
            ("Full written tutorial", m["guide"]),
            ("First start after install", "first-start.html"),
            ("Downloads", "download.html"),
        )))
        faqs += [
            ("How long does a %s install take?" % label,
             "Usually a few minutes once the ROM is downloaded; the download itself is the slow part "
             "on a typical connection. Leave the player alone until Updater reports success."),
            ("Do I need to unlock or root the %s first?" % model,
             "No. The flash uses the MediaTek preloader, so there is nothing to unlock beforehand."),
            ("Which release should I pick?",
             "A stable release is the default answer. Nightlies are for testing a specific fix and are "
             "labelled as previews in the app and on the release-notes pages."),
        ]
        howto = [re.sub(r"<[^>]+>", "", step) for step in steps]

    elif slug == "download":
        tag = release.get("tag_name") or m["stable_tag"]
        lead = (
            "%s downloads are ROM packages, not installers. The portable mirror publishes the same "
            "ROM the app flashes, split into per-platform ZIPs, so you can keep a copy, flash from "
            "another computer, or install from a local file." % label
        )
        sections.append(section("%s download files" % label, download_table(m, release), "files"))
        sections.append(section(
            "Which file do I want?",
            ul([
                "<strong>Windows / macOS / Linux portable ZIP</strong> — pick the one matching the computer you will flash from.",
                "<strong>Universal ROM package</strong> — the plain <code>%s</code>; useful for archives and for Updater's local-package mode." % m["rom_name"],
                "<strong>Type B ZIPs</strong> — only for Y1 players that need the Type B build." if m.get("type_b") else "<strong>Beta builds</strong> — earlier releases stay published so an older build can be re-flashed.",
            ]) + p("The tag to quote when someone asks which build you are on is <strong>%s</strong>." % tag),
        ))
        sections.append(section("Prefer the app?", p(
            "Updater CE picks the release for your model, downloads it, verifies the archive and runs "
            "the flash. The download pages exist for the cases the app cannot cover: offline "
            "machines, archives, and people who want to see the files first."
        ) + actions(("Get it in Updater CE", gui), ("Portable ZIP route", "portable-zip.html"))))
        faqs += [
            ("Are these the official Rockbox files?",
             "They are the community port for this player, repacked by the mirror release. They are "
             "not a mainline Rockbox build for another device."),
            ("Why are there several ZIPs with the same ROM inside?",
             "The per-platform archives exist so the download is convenient on each system; the images "
             "inside are the same ones Updater writes."),
            ("Can I flash the ZIP directly?",
             "No — it is a package for Updater or for the manual route, not a bootable image. See "
             "<a href=\"portable-zip.html\">the portable ZIP page</a>."),
        ]
        extra_ld.append({
            "@context": "https://schema.org",
            "@type": "DataDownload",
            "name": "%s ROM package" % label,
            "contentUrl": "https://github.com/%s/releases/tag/%s" % (m["mirror"], tag),
        })

    elif slug == "portable-zip":
        lead = (
            "The portable ZIP is the no-wizard path: a release archive that contains the ROM images "
            "for this player, arranged so Updater CE can flash them from a local folder — or so you "
            "can hand the folder to the manual flashing tool of your choice."
        )
        sections.append(section("Pick the archive for your computer", ul([
            "<code>%s-windows.zip</code>, <code>%s-macos.zip</code>, <code>%s-linux.zip</code> — the same ROM, packaged for each platform's default extraction and path handling." % (m["rom_name"][:-4], m["rom_name"][:-4], m["rom_name"][:-4]),
            "<code>%s</code> — the universal package when you want one file for every machine." % m["rom_name"],
        ]) + download_summary(m, release)))
        sections.append(section("Install from the extracted folder", ol([
            "Download the ZIP and extract it to a path with no spaces or unusual characters.",
            "Open Updater CE, set <strong>Device Model</strong> to <strong>%s</strong>." % model,
            "Choose the local-package / browse option and point it at the extracted folder.",
            "Confirm the images it found, then run <strong>Install / Restore</strong>.",
            "Power the %s off and connect it only at the prompt." % model,
        ])))
        sections.append(section("What is inside", p(
            "A scatter file plus the partition images the flash writes. The scatter is what tells the "
            "flashing tool where each image belongs, and it is why the extracted folder must stay "
            "intact — moving a single image out breaks the mapping."
        )))
        faqs += [
            ("Do I need Python or MTKClient installed?",
             "No. Updater CE bundles what it needs; the ZIP is only the ROM."),
            ("Can I keep the ZIP on the SD card?",
             "You can store it there, but flashing reads it from the computer. Extract it on the "
             "machine doing the flash."),
            ("The folder has several images — do I flash all of them?",
             "Yes, the flash writes the set the scatter names. Do not cherry-pick."),
        ]
        howto = [
            "Download the portable ZIP for your platform.",
            "Extract it to a path without spaces.",
            "Select %s in Updater CE and browse to the extracted folder." % model,
            "Run Install / Restore and connect the powered-off player at the prompt.",
        ]

    elif slug == "requirements":
        lead = (
            "Almost every failed %s install traces back to one of five things: the wrong model, a "
            "charge-only cable, a flat battery, a missing driver, or connecting the player before the "
            "app was listening. Check them before you start." % label
        )
        sections.append(section("Hardware and computer", ul([
            "An Innioasis %s — check the model on the player itself, not on the box." % model,
            "A USB <strong>data</strong> cable; charge-only cables enumerate nothing.",
            "A charged player, and a computer that will not sleep mid-flash.",
            "Windows: the MediaTek preloader driver. Linux: USB permissions for <code>0e8d:*</code>.",
            "About a gigabyte of free space for the download and extraction.",
        ]) + p("The driver and permission details live on the <a href=\"../drivers.html\">drivers page</a>, "
               "and connection-timing failures are covered in <a href=\"troubleshooting.html\">troubleshooting</a>.")))
        sections.append(section("Which build of %s" % label, p(m["build_note"]) + ul([
            "Y1: Type A unless you already know the player needs Type B." if m.get("type_b") else "Y2: only builds listed for Y2; the Y1 package is a different ROM.",
            "A stable build for everyday use; nightlies for testing.",
        ])))
        faqs += [
            ("Does the player need to be charged first?",
             "Yes — a flash that loses power mid-write is the one failure worth avoiding."),
            ("Does it work on ARM Macs?",
             "Yes. Updater CE ships for Apple silicon and Intel Macs, and the portable ZIP has a macOS package."),
            ("Do I need internet on the player?",
             "No. The download happens on the computer."),
        ]

    elif slug == "first-start":
        lead = (
            "The first boot after a %s install is not the end of the job: the player builds its "
            "database, creates the settings folder on the card, and waits for music." % label
        )
        sections.append(section("What happens on the first boot", ol([
            "Start the player and let it finish its first-boot routine — do not pull the card.",
            "Insert a MicroSD card with music on it (FAT32/exFAT is the safe choice).",
            "Let the database build; large libraries take a while the first time.",
            "Install a theme that matches your build, then reboot to see it applied.",
        ])))
        sections.append(section("Worth changing on day one", ul([
            "Database → update now, once the music is on the card.",
            "Theme settings, so the wheel and the screen match how you browse.",
            "Playback settings: gapless and crossfade are the two people notice first.",
            "If the build supports it, point scrobbling at your Last.fm / ListenBrainz / Maloja account.",
        ]) + p("Themes are covered on the <a href=\"%s\">%s theme page</a>, and the card layout on "
               "<a href=\"sd-card.html\">the MicroSD page</a>." % (m["themes"], label))))
        faqs += [
            ("The player booted with no music — is the install broken?",
             "No. Rockbox reads the card, not internal storage. Add music to the card and refresh the database."),
            ("Can I install themes before flashing?",
             "You can copy them to the card first, but apply them after the build is running."),
            ("How do I get back to stock software from here?",
             "Either from the player's own system menu when the build offers it, or by reflashing "
             "Original Software — see <a href=\"dual-boot.html\">dual boot</a>."),
        ]

    elif slug == "sd-card":
        lead = (
            "%s keeps nearly everything you can change on the MicroSD card, inside a folder called "
            "<code>.rockbox</code>. That one fact explains most of the questions about settings, "
            "themes and resets." % label
        )
        sections.append(section("The .rockbox folder", p(
            "Settings, themes, playlists, caches and the database live there. The firmware itself is "
            "on the player's internal flash, so deleting the folder does not uninstall anything — it "
            "returns the software to a clean default state and the folder is rebuilt on the next boot."
        ) + ol([
            "Power off and remove the card, or connect the player as a USB drive.",
            "Turn on hidden files (macOS: <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>.</kbd>; Windows: View → Hidden items).",
            "Rename <code>.rockbox</code> to <code>.rockbox-old</code> if you might want it back.",
            "Boot the player again and let it recreate the folder.",
        ])))
        sections.append(section("Card housekeeping", ul([
            "Keep music in ordinary folders; the database sorts by tags, not by directory name.",
            "Large libraries: update the database after copying, not during playback.",
            "A card that drops out mid-playback is usually a card problem, not firmware.",
        ])))
        faqs += [
            ("Will deleting .rockbox delete my music?",
             "No. Music lives outside that folder; only settings, themes and caches are inside it."),
            ("Why can't I see the folder?",
             "Names starting with a dot are hidden by default on Windows, macOS and Linux."),
            ("Does a bigger card make the player faster?",
             "No, but a faster card makes the database build and scrolling smoother."),
        ]

    elif slug == "update":
        lead = (
            "Updating %s is the same flow as installing it: model, software, release, then the "
            "connection prompt. Settings and themes on the card normally survive, because they are "
            "not part of the ROM." % label
        )
        sections.append(section("Update to a newer build", ol([
            "Set <strong>Device Model</strong> to <strong>%s</strong>." % model,
            "Choose <strong>Rockbox</strong>, then the newer stable (or the nightly you want).",
            "Run <strong>Install / Restore</strong> and connect the powered-off player at the prompt.",
            "Boot once, then check the theme and database still look right.",
        ]) + p("If you keep a backup of <code>.rockbox</code> from before the update, a theme that "
               "stops working can be rolled back without losing the whole install.")))
        sections.append(section("Stable or nightly?", p(
            "Stable builds are what most people want: they are the ones the guides and theme notes "
            "assume. Nightlies exist to test a specific fix and are marked as previews in the app and "
            "on the release pages. The full history is on <a href=\"%s\">the %s release notes</a>."
            % (m["release_notes"].replace("../", "../"), label)
        )))
        faqs += [
            ("Do I need to uninstall first?",
             "No. The flash writes over the old build."),
            ("Will my themes break?",
             "Themes that match the build's resolution keep working; a theme built for the other "
             "resolution will not look right."),
            ("Can I downgrade?",
             "Yes — the old tags stay published on the mirror, and reflashing an older build is the "
             "same operation."),
        ]

    elif slug == "restore-stock":
        lead = (
            "Going back is the same route in reverse: choose %s, choose <strong>Original Software</strong>, "
            "pick a stable release, and flash it." % model
        )
        sections.append(section("Restore the original %s software" % model, ol([
            "Open Updater CE and set <strong>Device Model</strong> to <strong>%s</strong>." % model,
            "Choose <strong>Original Software</strong> in <strong>Software</strong>.",
            "Pick a stable release — not a Rockbox one.",
            "Run <strong>Install / Restore</strong>, then power off and connect at the prompt.",
            "Leave the player alone until the success message, then boot it.",
        ]) + p("The dedicated route with screenshots is the <a href=\"%s\">%s restore guide</a>."
               % (m["restore"], model))))
        sections.append(section("Before you restore", ul([
            "Back up anything on the card you care about; the stock software does not read <code>.rockbox</code>.",
            "Do not delete Rockbox files first — flashing the stock ROM is the supported path.",
            "If the flash fails after detection, stop and read <a href=\"../troubleshooting.html\">troubleshooting</a> "
            "before trying again.",
        ])))
        faqs += [
            ("Does restoring wipe my music?",
             "No. The card is not reformatted by the ROM flash; your music files stay where they are."),
            ("Will I lose the ability to reinstall Rockbox?",
             "No. Rockbox remains available in the catalogue for this model."),
            ("Which Original Software release do I pick?",
             "A stable one listed for the same model. Choosing the other model's stock package is the "
             "one mistake worth double-checking."),
        ]

    elif slug == "dual-boot":
        lead = (
            "Most %s builds on this player coexist with the original software: you can start one or "
            "the other without reflashing. How you switch depends on the build, so treat the player "
            "menu, not a forum post, as the answer for yours." % label
        )
        sections.append(section("Switching between the two", ul([
            "From the custom software, the system menu offers a restart into the original software on builds that support it.",
            "From the original software, the community shortcut is holding <kbd>Menu/Back</kbd> + <kbd>Play/Pause</kbd> at power-on — confirm it on your build.",
            "A build that offers no switch can still be undone by flashing Original Software.",
        ]) + p("If you are unsure whether your build supports the switch, read the release notes for that "
               "tag before you rely on it.")))
        sections.append(section("When dual boot is not what you want", p(
            "If the plan is to hand the player to someone else, flashing the original software is "
            "cleaner than leaving two systems installed. The <a href=\"restore-stock.html\">restore page</a> "
            "covers that path."
        )))
        faqs += [
            ("Does dual boot cost storage?",
             "The two systems occupy the player's internal partitions; the card is shared. The exact "
             "layout is the build's business, not something you configure."),
            ("Can I brick the player by switching?",
             "Switching is not flashing. An interrupted flash is the risky operation, not a reboot."),
            ("Which system starts by default?",
             "Whichever the installed build defaults to; the player's menu is the authority."),
        ]

    elif slug == "troubleshooting":
        lead = (
            "A %s install fails in a small number of recognisable ways. Work through them in this "
            "order — most people find their answer in the first three." % label
        )
        sections.append(section("In the order worth trying", ol([
            "Wrong model selected: confirm <strong>%s</strong> in Device Model before choosing Rockbox." % model,
            "Cable: swap for a known data cable; charge-only cables never enumerate.",
            "Timing: the preloader window is only a few seconds. Start the flash, then connect the powered-off player.",
            "Drivers and permissions: install the MediaTek preloader driver on Windows, fix <code>0e8d:*</code> "
            "permissions on Linux (<a href=\"../drivers.html\">drivers page</a>).",
            "Interrupted transfer: reconnect and repeat; if the player no longer appears at all, follow the "
            "<a href=\"../guides/recovery.html\">recovery guide</a>.",
        ])))
        sections.append(section("Where it usually stops", p(
            "Before the USB prompt the problem is almost always the computer or the package. After the "
            "player is detected, the problem is the connection or the ROM. That split is what "
            "<a href=\"../troubleshooting.html\">the troubleshooting page</a> is organised around."
        )))
        faqs += [
            ("Updater says it cannot find the player. What now?",
             "Connect it powered off, in the same moment the app starts listening, and check the cable "
             "and driver first."),
            ("The flash reached 99% and stopped. Is the player dead?",
             "Usually not. Repeat the flash; a player that will not enumerate needs the recovery route."),
            ("Can a bad MicroSD card break the install?",
             "Not the flash itself, but it will break the first boot's database build. Try another card."),
        ]

    elif slug == "resolution":
        lead = m["build_note"] + " This page is about choosing between those labels without guessing."
        sections.append(section("What the labels mean", p(
            "The labels describe the screen and theme path the build targets, not the player's "
            "hardware revision. A theme written for one resolution will render wrong — or not at all — "
            "on the other, which is why builds and theme packs are labelled the same way."
        )))
        sections.append(section("Choosing", ul([
            "Match the label on the theme you intend to use first; themes are the reason the distinction exists.",
            "If you have no theme preference, take the newer stable build and its default theme.",
            "Read the release notes for that tag when the label is not obvious.",
        ]) + actions(("Browse themes", "../theme_downloader.html"), ("%s theme guide" % label, m["themes"]))))
        faqs += [
            ("Will the wrong resolution brick anything?",
             "No. It is a display and theme mismatch, not a hardware risk."),
            ("Can I switch later?",
             "Yes — flash the other build, the same way you installed this one."),
            ("Do all Y1 themes follow this?",
             "Older collections predate the labels; check the theme's own notes."),
        ]

    elif slug == "offline":
        lead = (
            "%s plays the files on your card. There is no account, no streaming service and no "
            "subscription — which is exactly why a lot of people install it." % label
        )
        sections.append(section("An offline player by design", ul([
            "The library is built from tags on your own files.",
            "Playback, the equalizer and the themes work with no network at all.",
            "Nothing about your listening requires a login.",
            "Podcast and scrobbling features are optional extras, not requirements.",
        ]) + p("If you are moving a library off a streaming service, the practical order is: copy the "
               "files to the card, boot the player, refresh the database, then tune the settings.")))
        sections.append(section("What it is not", p(
            "It is not a streaming client and it does not download your subscriptions. It replaces the "
            "player software; your music still has to exist as files."
        )))
        faqs += [
            ("Does it need Wi-Fi?",
             "No. Wi-Fi is only used by optional features on builds that offer them."),
            ("Which formats?",
             "Rockbox's usual set — MP3, FLAC, AAC and Ogg among them. Check the release notes for the "
             "build you install if you rely on an unusual format."),
            ("Is my listening data sent anywhere?",
             "Only if you configure scrobbling yourself."),
        ]

    elif slug == "uninstall":
        lead = (
            "“Uninstall %s” usually means one of two different things, and they have different "
            "answers: going back to the original software, or resetting the settings the build keeps "
            "on the card." % label
        )
        sections.append(section("Going back to the original software", p(
            "This is a flash, not a deletion. Select <strong>%s</strong>, choose <strong>Original "
            "Software</strong>, pick a stable release and run <strong>Install / Restore</strong>. "
            "The <a href=\"restore-stock.html\">restore page</a> has the full sequence." % model
        )))
        sections.append(section("Resetting only the settings", p(
            "Delete or rename the <code>.rockbox</code> folder on the MicroSD card and boot again. "
            "That clears settings, themes and caches, leaves the firmware installed, and reverts the "
            "player to defaults — see <a href=\"sd-card.html\">the MicroSD page</a>."
        )))
        faqs += [
            ("Does deleting .rockbox remove the firmware?",
             "No — it removes settings and themes; the build rebuilt the folder on the next boot."),
            ("Can I reinstall later?",
             "Yes, the release stays in the catalogue for this model."),
            ("Is either operation reversible?",
             "Yes, in both directions: flashing Original Software and flashing Rockbox again."),
        ]

    elif slug == "faq":
        lead = (
            "The questions that come up first about %s, answered plainly — with links to the page "
            "that goes deeper." % label
        )
        sections.append(section("Short answers", p(
            "Rockbox, %s and “Rockbox for %s” are the same port for the Innioasis %s. You install it "
            "with Innioasis Updater CE by selecting the model, choosing Rockbox, picking a release and "
            "connecting the powered-off player when the app asks. You undo it by flashing Original "
            "Software for the same model." % (label, model, model)
        )))
        faqs += [
            ("Is Rockbox the same as %s?" % label,
             "Yes. The catalogue lists the software as Rockbox with device %s; this site titles its "
             "release notes %s so the name matches what people search for." % (model, label)),
            ("How do I install Rockbox on the %s?" % model,
             "Use <a href=\"install.html\">the install page</a>: model first, then Rockbox, then a "
             "stable release, then the USB prompt."),
            ("Which file do I download?",
             "The <a href=\"download.html\">download page</a> lists the portable ZIPs per platform and "
             "the universal ROM; the app downloads the same package for you."),
            ("Can I use the %s build on the %s?" % (label, other["model"]),
             "No. Use <a href=\"%s\">%s</a> for that model." % (m["other_dir"], other["label"])),
            ("Will I lose my music?",
             "No. Music sits on the MicroSD card; flashing the ROM does not erase it."),
            ("How do I go back?",
             "Flash <strong>Original Software</strong> for %s — <a href=\"restore-stock.html\">restore page</a>." % model),
            ("Is it safe?",
             "It uses the same MediaTek flashing path as stock firmware. Use a good cable, a charged "
             "player, and do not interrupt the flash."),
        ]

    elif slug == "vs-stock":
        lead = (
            "The original %s software and %s are different players on the same hardware. This is what "
            "actually changes, without the marketing." % (model, label)
        )
        sections.append(section("Side by side", (
            '<table class="lumen-table"><thead><tr><th>What</th><th>Original Software</th>'
            "<th>%s</th></tr></thead><tbody>"
            "<tr><th scope=\"row\">Library</th><td>Browses the files you copied</td><td>Tag-based database: artist, album, genre</td></tr>"
            "<tr><th scope=\"row\">Playback</th><td>Straightforward player</td><td>Gapless, crossfade, equalizer</td></tr>"
            "<tr><th scope=\"row\">Themes</th><td>Stock interface</td><td>Large community theme library</td></tr>"
            "<tr><th scope=\"row\">Radio</th><td>Included where the model has FM</td><td>FM app inside the build</td></tr>"
            "<tr><th scope=\"row\">Extras</th><td>Stock feature set</td><td>Podcast downloads and scrobbling on builds that offer them</td></tr>"
            "<tr><th scope=\"row\">Going back</th><td>—</td><td>Flash the matching Original Software package</td></tr>"
            "</tbody></table>" % esc(label)
        ), "table"))
        sections.append(section("The honest trade-offs", ul([
            "It is an experimental community build, not a vendor release.",
            "Themes and builds are resolution-labelled; mismatches look wrong.",
            "Stock software is the simpler choice if you do not want to think about any of this.",
        ]) + actions(("Install %s" % label, "install.html"), ("Why Rockbox", "../rockbox-benefits.html"))))
        faqs += [
            ("Is Rockbox faster?",
             "Browsing is usually quicker because the library is indexed by tags instead of filenames; "
             "it is not a different CPU."),
            ("Do I lose the FM radio?",
             "No — the build includes an FM app on models that have the hardware."),
            ("Can I keep both?",
             "Often yes; see <a href=\"dual-boot.html\">dual boot</a>."),
        ]

    else:  # pragma: no cover - guarded by TOPICS
        raise SystemExit("unknown topic: %s" % slug)

    return lead, "".join(sections), faqs, howto, extra_ld


def related_grid(m, current: str) -> str:
    cards = []
    for slug, _priority in TOPICS:
        if slug == current:
            continue
        title = TOPIC_TITLES[slug].format(L=m["label"], M=m["model"])
        cards.append('<article class="lumen-card"><h3><a href="%s.html">%s</a></h3></article>' % (slug, esc(title)))
    other = MODELS[m["other"]]
    extras = [
        (m["for_page"], "Rockbox for %s: what the name means" % m["model"]),
        ("../rockbox-y1-vs-y2.html", "Rockbox-Y1 vs Rockbox-Y2"),
        (m["themes"], "%s themes" % m["label"]),
        (m["guide"], "Full %s written tutorial" % m["label"]),
        (m["release_notes"], "%s release notes" % m["label"]),
        (m["other_dir"], "%s hub" % other["label"]),
    ]
    cards.extend('<article class="lumen-card lumen-card--link"><h3><a href="%s">%s</a></h3></article>' % (href, esc(text))
                 for href, text in extras if href != "%s.html" % current)
    return ('<section class="lumen-guide-section"><h2>More %s pages</h2>'
            '<div class="lumen-grid">%s</div></section>' % (m["label"], "".join(cards)))


def write_page(path: pathlib.Path, title: str, description: str, canonical: str, up: str,
               main: str, ld_blocks: list, priority: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = (
        head(title, description, canonical, up)
        + jsonld(ld_blocks)
        + '<main id="main" class="lumen-guide">'
        + main
        + "</main>"
        + FOOT.format(up=up)
    )
    path.write_text(document, encoding="utf-8")
    SITEMAP.append((canonical, priority))


SITEMAP: list[tuple[str, str]] = []


def hub_page(m, release) -> None:
    lead, body, faqs, _howto = hub_body(m, release)
    canonical = "%s/%s/" % (SITE, m["dir"])
    title = "%s: install, ROM download and tutorial hub" % m["label"]
    description = (
        "Everything for %s on the Innioasis %s: install steps, portable ROM downloads, themes, "
        "restore-to-stock, dual boot and troubleshooting." % (m["label"], m["model"])
    )
    main = (
        '<p class="lumen-doc-back"><a href="../firmware.html?model=%s&amp;software=%s">← Firmware Downloads</a></p>'
        '<header><p class="lumen-kicker">%s · Innioasis %s</p><h1>%s</h1><p class="lead">%s</p>%s</header>'
        % (esc(m["model"]), esc(m["software"]), esc(m["label"]), esc(m["model"]), esc(title.split(":")[0]),
           esc(lead), actions(("Install %s" % m["label"], "install.html"), ("Download the ROM", "download.html"),
                              ("Full written tutorial", m["guide"])))
    )
    main += body + faq_block(faqs) + related_grid(m, "index")
    write_page(ROOT / m["dir"] / "index.html", title, description, canonical, "../", main,
               [article_ld(title, description, canonical, []),
                breadcrumb_ld([("Home", SITE + "/"), ("Firmware Downloads", SITE + "/firmware.html"),
                               (m["label"], canonical)]),
                faq_ld(faqs)],
               "0.9")


def topic_page(m, slug: str, priority: str, release) -> None:
    lead, body, faqs, howto, extra_ld = topic_body(m, slug, release)
    title = TOPIC_TITLES[slug].format(L=m["label"], M=m["model"])
    description = TOPIC_DESCRIPTIONS[slug].format(L=m["label"], M=m["model"])
    canonical = "%s/%s/%s.html" % (SITE, m["dir"], slug)
    blocks = [
        article_ld(title, description, canonical, []),
        breadcrumb_ld([("Home", SITE + "/"), ("Firmware Downloads", SITE + "/firmware.html"),
                       (m["label"], "%s/%s/" % (SITE, m["dir"])), (title, canonical)]),
    ]
    if howto:
        blocks.append({
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": description,
            "totalTime": "PT10M",
            "tool": [{"@type": "HowToTool", "name": "Innioasis Updater CE"}],
            "step": [{"@type": "HowToStep", "position": index + 1, "text": step}
                     for index, step in enumerate(howto)],
        })
    if faqs:
        blocks.append(faq_ld(faqs))
    blocks.extend(extra_ld)
    main = (
        '<p class="lumen-doc-back"><a href="./">← %s hub</a></p>'
        '<header><p class="lumen-kicker">%s · Innioasis %s</p><h1>%s</h1><p class="lead">%s</p>%s</header>'
        % (esc(m["label"]), esc(m["label"]), esc(m["model"]), esc(title.split(":")[0]), esc(lead),
           actions(("Get it in Updater CE", guide_href(m)), ("Full written tutorial", m["guide"])))
    )
    main += body
    if faqs:
        main += faq_block(faqs)
    main += related_grid(m, slug)
    write_page(ROOT / m["dir"] / (slug + ".html"), title, description, canonical, "../", main, blocks, priority)


def rom_download_page(releases: dict) -> None:
    canonical = SITE + "/rockbox-rom-download.html"
    title = "Rockbox ROM download for Innioasis Y1 and Y2"
    description = (
        "Rockbox ROM downloads for the Innioasis Y1 (Rockbox-Y1) and Y2 (Rockbox-Y2): portable "
        "flashing packages from the community mirror, per platform, with the Updater route beside them."
    )
    blocks = [
        article_ld(title, description, canonical, []),
        breadcrumb_ld([("Home", SITE + "/"), ("Firmware Downloads", SITE + "/firmware.html"), (title, canonical)]),
    ]
    body = [section(
        "Pick the model first",
        p(
            "There is no single Rockbox ROM for both players. The Y1 port and the Y2 port are "
            "separate builds with separate mirrors, and the model decides which one is safe to "
            "flash. Links below go straight to the mirror release that holds the zips."
        ),
    )]
    for key in ("y1", "y2"):
        m = MODELS[key]
        release = releases.get(key) or {}
        body.append(section(
            "%s (%s)" % (m["label"], m["model"]),
            download_table(m, release)
            + actions(("Install %s" % m["label"], "%s/install.html" % m["dir"]),
                      ("%s downloads" % m["label"], "%s/download.html" % m["dir"]),
                      ("Rockbox for %s" % m["model"], m["for_page"].replace("../", ""))),
            key,
        ))
    body.append(section(
        "What these files are",
        p(
            "Each mirror release repacks the ROM from the project's own release as a portable "
            "flashing package: a scatter file and the partition images. Updater CE downloads the "
            "same images and writes them with MediaTek's download protocol. Nothing here is a "
            "mainline Rockbox build for another device, and none of it is an installer."
        ) + ul([
            "Universal package: one archive for every computer.",
            "Per-platform package: the same images, packaged for Windows, macOS or Linux.",
            "Type B package (Y1 only): for players that need the Type B build.",
        ]),
        "what",
    ))
    body.append(section("Install any of them with the guided flow", p(
        "If you would rather not handle files, skip the downloads entirely: Updater CE picks the "
        "release for your model and flashes it. The <a href=\"rockbox-y1/install.html\">Rockbox-Y1 "
        "install guide</a> and the <a href=\"rockbox-y2/install.html\">Rockbox-Y2 install guide</a> "
        "both assume that route."
    )))
    main = (
        '<p class="lumen-doc-back"><a href="firmware.html?software=rockbox-y1">← Firmware Downloads</a></p>'
        '<header><p class="lumen-kicker">Rockbox ROM downloads</p><h1>Rockbox ROM download for the Y1 and Y2</h1>'
        '<p class="lead">%s</p></header>' % esc(description)
    ) + "".join(body)
    write_page(ROOT / "rockbox-rom-download.html", title, description, canonical, "", main, blocks, "0.9")


# ---------------------------------------------------------------- sitemap / llms.txt

def update_sitemap() -> None:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    added = 0
    for loc, priority in SITEMAP:
        if "<loc>%s</loc>" % loc in text:
            continue
        text = text.replace(
            "</urlset>",
            '  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq>'
            "<priority>%s</priority></url>\n</urlset>" % (esc(loc), TODAY, priority),
        )
        added += 1
    if added:
        path.write_text(text, encoding="utf-8")
    print("sitemap: %d new URLs" % added)


LLMS_MARKER = "## Rockbox-Y1 (Rockbox for Y1) and Rockbox-Y2"


def update_llms() -> None:
    path = ROOT / "llms.txt"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if LLMS_MARKER in text:
        return
    lines = [
        "",
        LLMS_MARKER,
        "",
        "Rockbox is the community firmware for Innioasis players. This site titles the Y1 port",
        "Rockbox-Y1 and the Y2 port Rockbox-Y2; \"Rockbox for Y1\" and \"rockbox-y1\" mean the",
        "same software. Every page below names the model, and the download pages link to the",
        "community portable mirror releases that hold the ROM zips.",
        "",
    ]
    for key in ("y1", "y2"):
        m = MODELS[key]
        lines.append("- [%s hub](%s/%s/): Install, ROM downloads, themes, restore and troubleshooting for the %s."
                     % (m["label"], SITE, m["dir"], m["model"]))
        lines.append("- [Install %s](%s/%s/install.html): The model-first Updater CE install in six steps."
                     % (m["label"], SITE, m["dir"]))
        lines.append("- [%s ROM download](%s/%s/download.html): Portable ZIPs and the universal ROM from the mirror."
                     % (m["label"], SITE, m["dir"]))
        lines.append("- [Rockbox for %s](%s/rockbox-for-%s.html): Why the names Rockbox, %s and \"Rockbox for %s\" are the same port."
                     % (m["model"], SITE, key, m["label"], m["model"]))
        lines.append("- [%s tutorial](%s/guides/rockbox-%s.html): The full written walkthrough."
                     % (m["label"], SITE, key))
        lines.append("- [%s themes](%s/rockbox-%s-themes.html): Theme paths, 240p and 360p builds." % (m["label"], SITE, key))
    lines.append("- [Rockbox ROM download, both models](%s/rockbox-rom-download.html): Y1 and Y2 packages side by side." % SITE)
    lines.append("- [Rockbox-Y1 vs Rockbox-Y2](%s/rockbox-y1-vs-y2.html): The differences that decide which build to flash." % SITE)
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print("llms.txt: added the Rockbox section")


# ---------------------------------------------------------------- build

def build(refresh: bool = False) -> None:
    SITEMAP.clear()
    releases = {}
    for key, m in MODELS.items():
        available = mirror_releases(m["mirror"], refresh=refresh)
        releases[key] = stable_release(available, m["stable_tag"])
        tag = releases[key].get("tag_name") or m["stable_tag"]
        print("  %-12s mirror %s -> %s (%d assets)"
              % (m["label"], m["mirror"], tag, len(releases[key].get("assets") or [])))
    for key, m in MODELS.items():
        hub_page(m, releases[key])
        for slug, priority in TOPICS:
            topic_page(m, slug, priority, releases[key])
        print("  %-12s wrote %d pages" % (m["label"], len(TOPICS) + 1))
    rom_download_page(releases)
    # The hand-written entity pages are part of the same crawl surface.
    for page_name, priority in (
        ("rockbox-for-y1.html", "0.85"),
        ("rockbox-for-y2.html", "0.85"),
        ("rockbox-y1-vs-y2.html", "0.75"),
        ("rockbox-y1-themes.html", "0.75"),
        ("rockbox-y2-themes.html", "0.75"),
    ):
        if (ROOT / page_name).exists():
            SITEMAP.append(("%s/%s" % (SITE, page_name), priority))
    update_sitemap()
    update_llms()
    print("done: %d urls" % len(SITEMAP))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate Rockbox-Y1 / Rockbox-Y2 landing pages.")
    parser.add_argument("--refresh", action="store_true", help="ignore the on-disk release cache")
    args = parser.parse_args()
    build(refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
