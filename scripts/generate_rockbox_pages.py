#!/usr/bin/env python3
"""Write the Rockbox-Y1 / Rockbox-Y2 search landing pages.

Rockbox is listed in ``slidia_manifest.xml`` and ``firmware-catalog.js``, and
people search for it by many names: Rockbox, Rockbox-Y1, Rockbox for Y1,
"rockbox y1 install", "how to install rockbox on y1", "rockbox-y1 tutorial",
and the same set for the Y2. This generator writes focused, easy-to-read guide
pages for each search topic under a stable, model-scoped URL:

    rockbox-y1/index.html          the Rockbox-Y1 hub
    rockbox-y1/<topic>.html        one topic per page (install, download, …)
    rockbox-y2/index.html          the Rockbox-Y2 hub
    rockbox-y2/<topic>.html
    rockbox-rom-download.html      both models' ROM downloads side by side

Updater CE always downloads firmware packages directly from the community
firmware developers' own releases, and those developers are solely responsible
for listing their software releases in Updater CE.

Usage:
    python scripts/generate_rockbox_pages.py [--refresh]
"""
from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://innioasis.app"
BRAND = "Innioasis Updater"
CACHE = ROOT / ".cache" / "rockbox-pages"
DOC_CACHE = ROOT / ".cache" / "doc-pages"
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
        "repo": "rockbox-y1/rockbox",
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
            "Y1 community builds are labelled by screen resolution: 240p builds work "
            "with classic iPod-style Rockbox themes, while 360p builds use higher-resolution "
            "Y1 themes."
        ),
    },
    "y2": {
        "key": "y2",
        "dir": "rockbox-y2",
        "model": "Y2",
        "label": "Rockbox-Y2",
        "plain": "Rockbox",
        "software": "rockbox-y2",
        "repo": "spycemagic/y2-rockbox",
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
            "Rockbox-Y2 is developed separately for the Y2 hardware. Check the release notes "
            "for your version to see supported features and theme compatibility."
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
    "install": "Install {L} on the Innioasis {M} (Updater CE guide)",
    "download": "{L} ROM download: developer firmware packages",
    "portable-zip": "{L} local ZIP: install from a downloaded ROM package",
    "requirements": "What you need before installing {L}",
    "first-start": "{L} first start: music, themes and settings",
    "sd-card": "{L} and the MicroSD card: .rockbox explained",
    "update": "Update {L}: moving to a newer stable or nightly build",
    "restore-stock": "Undo {L}: restore the original {M} software",
    "dual-boot": "{L} dual boot: switching back to original software",
    "troubleshooting": "{L} install problems and how to fix them",
    "resolution": "{L} 240p and 360p builds: choosing a theme resolution",
    "offline": "{L}: an offline music player with no account",
    "uninstall": "Remove {L} or reset it to defaults",
    "faq": "{L} FAQ: common questions answered",
    "vs-stock": "{L} vs Original Software: what changes",
}

TOPIC_DESCRIPTIONS = {
    "install": "How to install {L} on an Innioasis {M} with Innioasis Updater CE: select {M}, choose Rockbox, pick a release from the community developer, and connect your powered-off player when prompted.",
    "download": "Download {L} firmware ROM packages published by the community developers for the Innioasis {M}, or install directly in Innioasis Updater CE.",
    "portable-zip": "How to install {L} on your Innioasis {M} from a downloaded ROM ZIP package using Innioasis Updater CE.",
    "requirements": "What you need before installing {L} on an Innioasis {M}: a USB data cable, charged battery, computer setup, and model check.",
    "first-start": "Getting started after installing {L} on your Innioasis {M}: adding music to the MicroSD card, refreshing the library database, and installing themes.",
    "sd-card": "How {L} uses the MicroSD card on the Innioasis {M}: the hidden .rockbox folder, formatting, library updates, and resetting settings safely.",
    "update": "How to update {L} on your Innioasis {M} to a newer stable or nightly release in Updater CE while keeping your music, themes, and settings.",
    "restore-stock": "How to return an Innioasis {M} to its factory Original Software after installing {L} using Innioasis Updater CE.",
    "dual-boot": "How {L} and Original Software work together on the Innioasis {M}, and how to switch between them.",
    "troubleshooting": "Fix common {L} installation issues on the Innioasis {M}: model selection, USB data cables, drivers, and connection timing.",
    "resolution": "Understanding 240p and 360p {L} builds on the Innioasis {M} and how to choose the right build for your themes.",
    "offline": "Why {L} on the Innioasis {M} is ideal for offline listening: local audio files, no accounts, no subscriptions, and tag-based library browsing.",
    "uninstall": "How to remove {L} by restoring Original Software on your Innioasis {M}, or reset {L} settings by clearing the .rockbox folder.",
    "faq": "Frequently asked questions about {L} on the Innioasis {M}: safety, direct developer downloads in Updater CE, themes, updates, and restoring stock firmware.",
    "vs-stock": "Compare {L} and Original Software on the Innioasis {M}: music library, gapless playback, equalizer, themes, FM radio, and restoring factory firmware.",
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
        '<section class="lumen-guide-section"><h2 id="faq">Frequently asked questions</h2>%s</section>'
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
<script src="{up}firmware-catalog.js?v=20261104cite" defer></script>
<script src="{up}docs-viewer.js?v=20261104cite" defer></script>
<script src="{up}portable-zip-links.js?v=20261103direct" defer></script>
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
        "about": {"@type": "Product", "name": "Innioasis player"},
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


# ---------------------------------------------------------------- release data

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


def project_releases(repo: str, refresh: bool = False) -> list[dict]:
    """Published releases of a developer firmware repo (cached on disk)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (repo.replace("/", "-") + ".json")
    if path.exists() and not refresh:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(cached, list) and cached:
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    doc_url = "https://api.github.com/repos/%s/releases?per_page=100&page=1" % repo
    doc_cache_path = DOC_CACHE / (hashlib.sha1(doc_url.encode("utf-8")).hexdigest() + ".json")
    releases = None
    if doc_cache_path.exists() and not refresh:
        try:
            candidate = json.loads(doc_cache_path.read_text(encoding="utf-8"))
            if isinstance(candidate, list) and candidate:
                releases = candidate
        except (OSError, json.JSONDecodeError):
            pass
    if releases is None:
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
    """The release a visitor should start with."""
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


def release_notes_url(m, tag: str, up: str = "../") -> str:
    author, _, project = m["repo"].partition("/")
    params = {"author": author, "project": project}
    if tag:
        params["version"] = tag
    if m.get("software"):
        params["software"] = m["software"]
    return "%srelease_notes.html?%s" % (up, urllib.parse.urlencode(params))


def firmware_dir_url(m, up: str = "../") -> str:
    return "%sfirmware.html?model=%s&amp;software=%s" % (up, esc(m["model"]), esc(m["software"]))


def firmware_readme_url(m, up: str = "../") -> str:
    return "%sfirmware_info.html?repo=%s&amp;software=%s" % (
        up, esc(urllib.parse.quote(m["repo"], safe="")), esc(m["software"])
    )


def package_rows(release: dict, m) -> list[tuple[str, str, str]]:
    """(label, filename, url) for the developer ROM packages in ``release``."""
    tag = release.get("tag_name") or m["stable_tag"]
    assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets") or []}
    rows = []
    rom_url = assets.get(m["rom_name"]) or (
        "https://github.com/%s/releases/download/%s/%s" % (m["repo"], tag, m["rom_name"])
    )
    rows.append(("%s developer ROM package" % m["label"], m["rom_name"], rom_url))
    if m.get("type_b"):
        type_b_url = assets.get("rom_type_b.zip") or (
            "https://github.com/%s/releases/download/%s/rom_type_b.zip" % (m["repo"], tag)
        )
        rows.append(("%s Type B developer ROM package" % m["label"], "rom_type_b.zip", type_b_url))
    return rows


def download_table(m, release: dict, up: str = "../") -> str:
    rows = package_rows(release, m)
    tag = release.get("tag_name") or m["stable_tag"]
    notes_href = release_notes_url(m, tag, up=up)
    dir_href = firmware_dir_url(m, up=up)
    readme_href = firmware_readme_url(m, up=up)
    body = "".join(
        '<tr><th scope="row">%s</th><td><code>%s</code></td><td><a href="%s" rel="noopener">Download</a></td></tr>'
        % (esc(label), esc(name), esc(url))
        for label, name, url in rows
    )
    return (
        '<table class="lumen-table"><thead><tr><th>Package</th><th>File</th><th>Link</th></tr></thead><tbody>%s</tbody></table>'
        '<p class="lumen-meta">Published by the <a href="%s">%s</a> developers in release '
        '<a href="%s">%s</a> (<a href="%s">project README</a>). '
        "Innioasis Updater CE always downloads firmware packages directly from the community firmware developers "
        "themselves, and those developers are solely responsible for listing their releases in Updater CE.</p>"
        % (body, dir_href, esc(m["repo"]), esc(notes_href), esc(tag), readme_href)
    )


def download_summary(m, release: dict, up: str = "../") -> str:
    tag = release.get("tag_name") or m["stable_tag"]
    return (
        '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="download.html">%s downloads</a>'
        '<a class="lumen-button" href="%s">Get it in Updater CE</a>'
        '<a class="lumen-button" href="%s">Release notes (%s)</a></div>'
        % (esc(m["label"]), esc(guide_href(m)), esc(release_notes_url(m, tag, up=up)), esc(tag))
    )


def guide_href(m) -> str:
    return "../guide.html?model=%s&amp;software=%s" % (esc(m["model"]), esc(m["software"]))


# ---------------------------------------------------------------- page bodies

def hub_body(m, release) -> tuple[str, str, list, list]:
    other = MODELS[m["other"]]
    lead = (
        "%s is the community Rockbox firmware for the Innioasis %s. It adds a tag-based music "
        "library, gapless playback, a full equalizer, and custom themes. Use this hub to install "
        "%s with Updater CE, download ROM packages, browse themes, or restore the factory software."
        % (m["label"], m["model"], m["label"])
    )
    sections = [
        section(
            "Rockbox, Rockbox-%s and “Rockbox for %s” are the same firmware" % (m["model"], m["model"]),
            p(
                "Innioasis Updater CE lists this firmware as <strong>Rockbox</strong> under device model "
                "<strong>%s</strong>. Guides, videos, and search results also call it <strong>%s</strong> "
                "or <strong>Rockbox for %s</strong>. All of these names refer to the exact same %s port. "
                "Always select <strong>%s</strong> first so you do not install a %s build by mistake."
                % (m["model"], m["label"], m["model"], m["model"], m["model"], other["model"]),
            ),
            "names",
        ),
        section("Quick links", actions(
            ("Install %s" % m["label"], "install.html"),
            ("Download the ROM", "download.html"),
            ("Full written tutorial", m["guide"]),
            ("Restore Original Software", "restore-stock.html"),
        )),
        section(
            "Direct downloads from the community developers",
            p(
                "Innioasis Updater CE always downloads firmware packages directly from the community "
                "firmware developers (<a href=\"%s\">%s</a>), who are solely responsible for publishing "
                "and listing their software releases in Updater CE. You can let Updater CE download and "
                "install the release for you, or download the ROM package from our firmware directory."
                % (firmware_dir_url(m), esc(m["repo"]))
            ) + download_summary(m, release),
            "downloads",
        ),
        section(
            "Before you install",
            ul([
                "Select <strong>%s</strong> in <strong>Device Model</strong> before choosing Rockbox." % m["model"],
                "Choose a stable release for daily use, or enable nightly builds if you want to test a preview.",
                "Use a USB data cable and a charged player; power the player off and connect it only when Updater CE asks.",
                "You can return to factory firmware at any time by installing <strong>Original Software</strong> for the %s." % m["model"],
            ]) + p(m["build_note"]),
            "before",
        ),
    ]
    faqs = [
        (
            "Is %s safe to install?" % m["label"],
            "Yes. It uses the same MediaTek flashing process as the factory firmware, and you can restore "
            "Original Software at any time. Always use a reliable USB data cable and keep the player charged.",
        ),
        (
            "Where does Updater CE download %s from?" % m["label"],
            "Updater CE downloads firmware packages directly from the community firmware developers' own "
            "releases (%s). The developers themselves are solely responsible for listing their releases in Updater CE."
            % esc(m["repo"]),
        ),
        (
            "Can I install %s on an Innioasis %s?" % (m["label"], other["model"]),
            "No. The Y1 and Y2 use different hardware and separate firmware builds. Select %s in Updater CE "
            "and use the <a href=\"%s\">%s guide</a> instead." % (other["model"], m["other_dir"], other["label"]),
        ),
        (
            "How do I return to the original factory software?",
            "In Updater CE, select <strong>%s</strong>, choose <strong>Original Software</strong>, pick a stable "
            "release, and click <strong>Install / Restore</strong>. See the <a href=\"restore-stock.html\">restore guide</a>."
            % m["model"],
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
        "Select <strong>Rockbox</strong> in the <strong>Software</strong> dropdown.",
        "Pick a stable release (or check <strong>Show nightly builds</strong> to test a preview).",
        "Click <strong>Install / Restore</strong> so Updater CE downloads the package directly from the developer's release.",
        "Power the %s completely off, then connect it with a USB data cable when Updater CE prompts you." % model,
        "Wait for the completion message before unplugging and turning on your player.",
    ]
    faqs: list = []
    sections: list[str] = []
    howto: list[str] = []
    extra_ld: list = []

    if slug == "install":
        lead = (
            "Install %s on your Innioasis %s in six steps with Innioasis Updater CE. Select your model "
            "first, choose Rockbox, pick a release, and connect your powered-off player when prompted."
            % (label, model)
        )
        sections.append(section("Step-by-step installation", ol(steps), "steps"))
        sections.append(section(
            "Why selecting %s first matters" % model,
            p(
                "Updater CE shows only the firmware listed for the device model you select. Setting "
                "<strong>Device Model</strong> to <strong>%s</strong> ensures you get the %s build "
                "published by <strong>%s</strong> instead of a %s package."
                % (model, label, esc(m["repo"]), other["model"]),
                "If you already downloaded a ROM ZIP to your computer, see "
                "<a href=\"portable-zip.html\">installing from a local ZIP package</a>.",
            ),
        ))
        sections.append(section("How Updater CE installs the firmware", p(
            "Updater CE downloads the firmware package directly from the community developer's release "
            "(the developer is solely responsible for listing their releases in Updater CE), unpacks it, "
            "and flashes your player over USB while the player is powered off."
        )))
        sections.append(section("Next steps", actions(
            ("Full written tutorial", m["guide"]),
            ("First start & themes", "first-start.html"),
            ("ROM downloads", "download.html"),
        )))
        faqs += [
            ("How long does installing %s take?" % label,
             "Once the download finishes, flashing takes only a couple of minutes. Keep the USB cable connected until Updater CE shows the success message."),
            ("Do I need to root or unlock the %s first?" % model,
             "No. Updater CE flashes the player directly while it is powered off."),
            ("Which release should I choose?",
             "Choose the latest stable release for everyday use. Nightly builds are preview releases for testing new changes."),
        ]
        howto = [re.sub(r"<[^>]+>", "", step) for step in steps]

    elif slug == "download":
        tag = release.get("tag_name") or m["stable_tag"]
        lead = (
            "Download %s ROM packages for the Innioasis %s. Innioasis Updater CE always downloads "
            "firmware packages directly from the community firmware developers, who are solely "
            "responsible for listing their releases in Updater CE." % (label, model)
        )
        sections.append(section("%s download files" % label, download_table(m, release), "files"))
        sections.append(section(
            "Which package should I choose?",
            ul([
                "<strong>Install with Updater CE (recommended)</strong> — Updater CE downloads the package directly from the developer's release and flashes your %s automatically." % model,
                "<strong>Developer ROM package (<code>%s</code>)</strong> — the firmware ZIP published by the developer for offline archiving or manual installation." % m["rom_name"],
                "<strong>Type B ROM package (<code>rom_type_b.zip</code>)</strong> — for Y1 players that shipped with pre-2.0.0 factory firmware." if m.get("type_b") else "<strong>Earlier beta builds</strong> — browse all versions in the <a href=\"%s\">firmware directory</a>." % firmware_dir_url(m),
            ]) + p("Current recommended release tag: <strong>%s</strong>." % esc(tag)),
        ))
        sections.append(section("Install with one click in Updater CE", p(
            "You do not need to download ZIP files manually for a normal install. Open Updater CE, "
            "select %s and Rockbox, and it will download the release directly from the developer." % model
        ) + actions(("Get it in Updater CE", gui), ("Browse all releases", firmware_dir_url(m)))))
        faqs += [
            ("Where do %s downloads come from?" % label,
             "Updater CE always downloads packages directly from the community firmware developer's "
             "releases (%s). The developer is solely responsible for listing their releases in Updater CE." % esc(m["repo"])),
            ("Can I copy the ROM ZIP onto the MicroSD card to install it?",
             "No. Firmware ROM packages are flashed from a computer over USB using Updater CE. See "
             "<a href=\"portable-zip.html\">installing from a downloaded ZIP</a>."),
        ]
        extra_ld.append({
            "@context": "https://schema.org",
            "@type": "DataDownload",
            "name": "%s ROM package" % label,
            "contentUrl": "%s/firmware.html?model=%s&software=%s" % (SITE, m["model"], m["software"]),
        })

    elif slug == "portable-zip":
        lead = (
            "If you downloaded a %s ROM ZIP package ahead of time, you can install it from your "
            "computer or let Updater CE handle the entire download and flash for you." % label
        )
        sections.append(section("Download the ROM package", ul([
            "<code>%s</code> — the standard %s firmware package published by the developer." % (m["rom_name"], label),
            "On our <a href=\"%s\">Firmware Downloads</a> page, the download button can also bundle platform flashing scripts for Windows, macOS, or Linux when you want a standalone web download." % firmware_dir_url(m),
        ]) + download_summary(m, release)))
        sections.append(section("How to install from a downloaded ZIP", ol([
            "Download the ROM ZIP and extract it to a folder on your computer (avoid folder paths with special characters).",
            "Open Innioasis Updater CE and set <strong>Device Model</strong> to <strong>%s</strong>." % model,
            "Select the local package option and choose your downloaded ZIP or extracted folder.",
            "Click <strong>Install / Restore</strong>.",
            "Power off your %s completely and connect it over USB when Updater CE prompts you." % model,
        ])))
        sections.append(section("What is inside the ROM package", p(
            "Each ROM package contains a MediaTek scatter file and the partition images for your %s. "
            "Keep all files in the extracted folder together so the scatter file can locate every image." % model
        )))
        faqs += [
            ("Does Updater CE use the website's standalone portable ZIP mirror?",
             "No. Updater CE always downloads firmware packages directly from the community firmware "
             "developers themselves, who are solely responsible for listing their releases in Updater CE."),
            ("Do I need to install Python or MediaTek tools separately?",
             "No. Updater CE includes everything needed to flash the ROM."),
            ("Can I flash the ZIP from the player's MicroSD card?",
             "No. Flashing is always performed from a computer over USB while the player is powered off."),
        ]
        howto = [
            "Download the ROM ZIP to your computer.",
            "Open Innioasis Updater CE and select %s." % model,
            "Load the downloaded package or choose Rockbox from the Software list.",
            "Click Install / Restore and connect the powered-off player when prompted.",
        ]

    elif slug == "requirements":
        lead = (
            "Check these five items before installing %s on your Innioasis %s: the model printed on "
            "the player, a USB data cable, battery charge, computer drivers, and connection timing."
            % (label, model)
        )
        sections.append(section("What you need", ul([
            "An Innioasis <strong>%s</strong> — verify the model name on the player." % model,
            "A USB <strong>data</strong> cable (charge-only cables cannot transfer firmware).",
            "A charged battery (at least 50%% recommended).",
            "Windows: MediaTek USB drivers. Linux: udev permissions for <code>0e8d:*</code>. macOS: no extra driver needed.",
            "About 1 GB of free disk space on your computer.",
        ]) + p("Need help with drivers? See the <a href=\"../drivers.html\">USB drivers guide</a> "
               "or <a href=\"troubleshooting.html\">troubleshooting</a>.")))
        sections.append(section("Choosing the right %s build" % label, p(m["build_note"]) + ul([
            "Y1: Choose Type A if your player shipped with software 2.0.0+, or Type B for earlier units." if m.get("type_b") else "Y2: Only install builds listed for the Y2.",
            "Choose a stable release for everyday use, or a nightly build to test the latest changes.",
        ])))
        faqs += [
            ("Does my player need to be charged before flashing?",
             "Yes. Charging your player first prevents it from losing power during the flash."),
            ("Does Updater CE work on Apple Silicon Macs, Windows, and Linux?",
             "Yes. Updater CE runs natively on Windows, macOS (Intel and Apple Silicon), and Linux."),
            ("Does the player need Wi-Fi to install %s?" % label,
             "No. Your computer downloads the firmware and flashes the player over USB."),
        ]

    elif slug == "first-start":
        lead = (
            "After installing %s on your Innioasis %s, the first boot sets up the <code>.rockbox</code> "
            "folder on your MicroSD card and indexes your music library." % (label, model)
        )
        sections.append(section("First boot checklist", ol([
            "Turn on the player and let it finish its initial startup.",
            "Insert a MicroSD card formatted as FAT32 or exFAT with your music files.",
            "Allow the Rockbox database to scan your music library.",
            "Install themes using Updater CE or copy them to the <code>.rockbox</code> folder on your card.",
        ])))
        sections.append(section("Useful settings on day one", ul([
            "<strong>Database → Update Now</strong> after adding new music folders.",
            "<strong>Theme Settings</strong> to change fonts, status bars, and Now Playing screens.",
            "<strong>Sound Settings</strong> for gapless playback, crossfade, and the parametric equalizer.",
        ]) + p("See the <a href=\"%s\">%s theme guide</a> and the <a href=\"sd-card.html\">MicroSD card guide</a> "
               "for more details." % (m["themes"], label))))
        faqs += [
            ("My player started with no music showing — what should I do?",
             "Make sure your music is on the MicroSD card, then open Database in the menu and initialize or update it."),
            ("How do I install themes?",
             "Updater CE transfers Rockbox themes for you when it can, and walks you through copying them when manual transfer is needed. See the <a href=\"%s\">theme guide</a>." % m["themes"]),
            ("Can I switch back to the original software?",
             "Yes. You can reboot into the original software on builds that support dual boot, or restore Original Software in Updater CE."),
        ]

    elif slug == "sd-card":
        lead = (
            "%s stores your settings, themes, playlists, and music database on the MicroSD card inside "
            "a hidden folder named <code>.rockbox</code>." % label
        )
        sections.append(section("How the .rockbox folder works", p(
            "Because the firmware itself lives on the player's internal storage and your settings live "
            "in <code>.rockbox</code> on the MicroSD card, renaming or deleting <code>.rockbox</code> "
            "safely resets all settings and themes to defaults without uninstalling %s." % label
        ) + ol([
            "Connect the player over USB or put the MicroSD card into your computer.",
            "Show hidden files (macOS: <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>.</kbd>; Windows: View → Hidden items).",
            "Rename <code>.rockbox</code> to <code>.rockbox-backup</code> to reset your configuration.",
            "Restart the player so it creates a fresh <code>.rockbox</code> folder.",
        ])))
        sections.append(section("MicroSD card tips", ul([
            "Organize music in normal folders; Rockbox can browse both by folder and by ID3/vorbis tags.",
            "Refresh the database after copying new albums.",
            "Use FAT32 (or exFAT where supported) for reliable card reading.",
        ])))
        faqs += [
            ("Will deleting .rockbox erase my music?",
             "No, as long as your music folders are stored outside the .rockbox folder on the card."),
            ("Why can't I see the .rockbox folder on my computer?",
             "Folders starting with a dot are hidden by default on Windows, macOS, and Linux. Enable hidden files in your file manager."),
        ]

    elif slug == "update":
        lead = (
            "Updating %s on your Innioasis %s uses the exact same steps in Updater CE as a first-time "
            "install, and keeps the music, themes, and settings stored on your MicroSD card." % (label, model)
        )
        sections.append(section("How to update to a newer release", ol([
            "Open Innioasis Updater CE and select <strong>%s</strong> in <strong>Device Model</strong>." % model,
            "Choose <strong>Rockbox</strong> and select the newer stable or nightly release.",
            "Click <strong>Install / Restore</strong> and connect your powered-off player when prompted.",
            "Turn on the player once the update finishes.",
        ]) + p("Updater CE downloads the new release directly from the community developer's repository.")))
        sections.append(section("Stable vs. nightly builds", p(
            "Stable releases are recommended for everyday listening. Nightly builds let you test the "
            "newest changes and bug fixes. You can read what changed in every version on the "
            "<a href=\"%s\">%s release notes page</a>." % (m["release_notes"], label)
        )))
        faqs += [
            ("Do I need to uninstall the old version before updating?",
             "No. Flashing the new release overwrites the previous firmware while leaving your MicroSD card untouched."),
            ("Can I downgrade to an earlier release?",
             "Yes. Select any earlier release listed for your model in Updater CE and install it the same way."),
        ]

    elif slug == "restore-stock":
        lead = (
            "You can return your Innioasis %s to its factory Original Software at any time using "
            "Innioasis Updater CE." % model
        )
        sections.append(section("Restore Original Software on the %s" % model, ol([
            "Open Innioasis Updater CE and set <strong>Device Model</strong> to <strong>%s</strong>." % model,
            "Select <strong>Original Software</strong> in the <strong>Software</strong> dropdown.",
            "Pick a stable factory release for the %s." % model,
            "Click <strong>Install / Restore</strong>, power off your player, and connect it when prompted.",
            "Wait for the success message, then disconnect and turn on the player.",
        ]) + p("For a full walkthrough, see the <a href=\"%s\">%s Original Software restore guide</a>."
               % (m["restore"], model))))
        sections.append(section("Good to know before restoring", ul([
            "Your music files on the MicroSD card are not erased when restoring Original Software.",
            "You do not need to delete Rockbox files before flashing Original Software.",
            "If the flash does not start when you plug in the player, check our <a href=\"../troubleshooting.html\">troubleshooting guide</a>.",
        ])))
        faqs += [
            ("Does restoring Original Software delete my music?",
             "No. Flashing Original Software updates the internal firmware and leaves your MicroSD card files intact."),
            ("Can I install %s again later?" % label,
             "Yes. You can switch between Original Software and Rockbox whenever you like."),
        ]

    elif slug == "dual-boot":
        lead = (
            "Many %s builds allow you to switch between Rockbox and the factory Original Software "
            "without reflashing your player." % label
        )
        sections.append(section("How to switch between Rockbox and Original Software", ul([
            "From Rockbox: check the System menu for an option to restart into the original player software.",
            "From Original Software: on supported builds, hold <kbd>Menu/Back</kbd> + <kbd>Play/Pause</kbd> while powering on (check your release notes for build-specific shortcuts).",
            "If you want to remove Rockbox completely and run only factory software, follow the <a href=\"restore-stock.html\">restore guide</a>.",
        ])))
        sections.append(section("When to restore instead of dual booting", p(
            "If you are giving the player to someone else or want a clean factory setup, flash "
            "<strong>Original Software</strong> in Updater CE."
        )))
        faqs += [
            ("Is switching between dual-boot systems safe?",
             "Yes. Switching only reboots the player into the other system; it does not reflash the storage."),
            ("Where can I check if my version supports dual boot?",
             "Check the <a href=\"%s\">%s release notes</a> for the build you installed." % (m["release_notes"], label)),
        ]

    elif slug == "troubleshooting":
        lead = (
            "If your %s installation does not start or stops early, check these five common causes in order."
            % label
        )
        sections.append(section("5 checks that fix most install issues", ol([
            "<strong>Device Model</strong>: Confirm <strong>%s</strong> is selected in Updater CE before choosing Rockbox." % model,
            "<strong>USB Cable</strong>: Use a known-good USB data cable; charge-only cables never connect.",
            "<strong>Connection Timing</strong>: Click <strong>Install / Restore</strong> first, power the player completely off, and plug it in only when Updater CE asks.",
            "<strong>USB Drivers</strong>: On Windows, install the MediaTek driver; on Linux, add udev permissions (<a href=\"../drivers.html\">drivers guide</a>).",
            "<strong>Recovery</strong>: If an interrupted flash leaves the player unresponsive, follow the <a href=\"../guides/recovery.html\">recovery guide</a>.",
        ])))
        sections.append(section("More troubleshooting help", p(
            "See the main <a href=\"../troubleshooting.html\">Innioasis Updater troubleshooting page</a> "
            "for step-by-step diagnostics on Windows, macOS, and Linux."
        )))
        faqs += [
            ("Updater CE does not detect my player when I plug it in.",
             "Make sure the player is powered completely off before connecting the USB cable, try a different USB data cable, and check your USB drivers."),
            ("The flash stopped halfway through — is my player bricked?",
             "Usually not. MediaTek preloader mode stays available even after an interrupted flash. Re-run Install / Restore in Updater CE."),
        ]

    elif slug == "resolution":
        lead = m["build_note"]
        sections.append(section("What 240p and 360p mean", p(
            "Resolution labels describe the display layout and theme format that the build uses. "
            "A 240p theme is designed for 320×240 builds, while a 360p theme is designed for "
            "480×360 builds."
        )))
        sections.append(section("How to choose", ul([
            "Pick the build resolution that matches the themes you want to use.",
            "If you want the widest library of classic Rockbox themes, 240p builds have the broadest compatibility.",
            "If you want sharper text and newer Y1-specific themes, choose a 360p build.",
        ]) + actions(("Browse themes", "../theme_downloader.html"), ("%s theme guide" % label, m["themes"]))))
        faqs += [
            ("Can installing the wrong resolution harm my player?",
             "No. Both are safe for the hardware; you just need themes that match the build resolution you installed."),
            ("Can I switch between 240p and 360p later?",
             "Yes. Just select the other build in Updater CE and install it."),
        ]

    elif slug == "offline":
        lead = (
            "%s turns your Innioasis %s into a dedicated offline music player: local files on a "
            "MicroSD card, no accounts, no subscriptions, and no internet connection required."
            % (label, model)
        )
        sections.append(section("Built for local music libraries", ul([
            "Plays MP3, FLAC, AAC, Ogg Vorbis, WAV, and more directly from your MicroSD card.",
            "Indexes tracks by artist, album, genre, and year using audio tags, or lets you browse folders directly.",
            "Includes gapless playback, ReplayGain, crossfade, and a parametric equalizer.",
            "Works 100%% offline with zero accounts or cloud services.",
        ])))
        sections.append(section("Switching from streaming", p(
            "Copy your audio files onto a MicroSD card, insert it into your %s, and run "
            "<strong>Database → Update Now</strong>." % model
        )))
        faqs += [
            ("Does %s require Wi-Fi or an account?" % label,
             "No. Everything runs locally from the files on your MicroSD card."),
            ("Which audio formats are supported?",
             "Standard lossless and lossy formats including FLAC, MP3, AAC/M4A, Ogg Vorbis, Opus, and WAV."),
        ]

    elif slug == "uninstall":
        lead = (
            "Whether you want to remove %s completely and return to factory software, or simply reset "
            "%s back to default settings, both take only a few minutes." % (label, label)
        )
        sections.append(section("Option 1: Return to factory Original Software", p(
            "To replace %s with the factory firmware, open Innioasis Updater CE, select "
            "<strong>%s</strong>, choose <strong>Original Software</strong>, and click "
            "<strong>Install / Restore</strong>. See the <a href=\"restore-stock.html\">restore guide</a>."
            % (label, model)
        )))
        sections.append(section("Option 2: Reset %s settings to default" % label, p(
            "To keep %s installed but reset all settings, themes, and database caches, delete or "
            "rename the hidden <code>.rockbox</code> folder on your MicroSD card and reboot the player. "
            "See the <a href=\"sd-card.html\">MicroSD card guide</a>." % label
        )))
        faqs += [
            ("Does deleting .rockbox uninstall the firmware?",
             "No. It only resets your settings and themes; the player recreates a clean .rockbox folder on the next boot."),
            ("Can I reinstall %s after restoring Original Software?" % label,
             "Yes, at any time through Innioasis Updater CE."),
        ]

    elif slug == "faq":
        lead = (
            "Clear answers to the most common questions about installing, updating, and using %s "
            "on the Innioasis %s." % (label, model)
        )
        sections.append(section("At a glance", p(
            "Rockbox, %s, and “Rockbox for %s” are the same community firmware for the Innioasis %s. "
            "Innioasis Updater CE always downloads packages directly from the community firmware "
            "developers (%s), who are solely responsible for listing their releases in Updater CE."
            % (label, model, model, esc(m["repo"]))
        )))
        faqs += [
            ("Are Rockbox, %s, and Rockbox for %s the same thing?" % (label, model),
             "Yes. Updater CE lists it as Rockbox when %s is selected, while guides and release notes call it %s so it is clear which player model it is for." % (model, label)),
            ("Where does Updater CE download %s from?" % label,
             "Updater CE always downloads firmware packages directly from the community firmware developers' own releases (%s), never from a mirror archive. The developers are solely responsible for listing their software releases in Updater CE." % esc(m["repo"])),
            ("How do I install %s?" % label,
             "Follow the <a href=\"install.html\">6-step install guide</a> in Innioasis Updater CE."),
            ("Can I install %s on an Innioasis %s?" % (label, other["model"]),
             "No. Use <a href=\"%s\">%s</a> for the %s." % (m["other_dir"], other["label"], other["model"])),
            ("Will installing %s erase my music?" % label,
             "No. Your music lives on the MicroSD card and is not touched by flashing the firmware."),
            ("How do I go back to factory software?",
             "Install <strong>Original Software</strong> for %s in Updater CE (<a href=\"restore-stock.html\">restore guide</a>)." % model),
        ]

    elif slug == "vs-stock":
        lead = (
            "Compare %s and the factory Original Software on the Innioasis %s so you can decide "
            "which system fits how you listen." % (label, model)
        )
        sections.append(section("Feature comparison", (
            '<table class="lumen-table"><thead><tr><th>Feature</th><th>Original Software</th>'
            "<th>%s</th></tr></thead><tbody>"
            "<tr><th scope=\"row\">Music library</th><td>Folder and basic tag browsing</td><td>Full tag database (artist, album, genre, year) + folder view</td></tr>"
            "<tr><th scope=\"row\">Playback</th><td>Standard playback</td><td>Gapless playback, crossfade, ReplayGain, parametric EQ</td></tr>"
            "<tr><th scope=\"row\">Themes</th><td>Built-in factory themes</td><td>Hundreds of custom community themes</td></tr>"
            "<tr><th scope=\"row\">FM radio</th><td>Built-in FM radio</td><td>Included on builds/models with FM hardware</td></tr>"
            "<tr><th scope=\"row\">Restoring factory OS</th><td>Already installed</td><td>One-click restore via Original Software in Updater CE</td></tr>"
            "</tbody></table>" % esc(label)
        ), "table"))
        sections.append(section("Which should you choose?", ul([
            "Choose <strong>%s</strong> if you want gapless playback, custom themes, a faster tag database, and fine-grained audio controls." % label,
            "Choose <strong>Original Software</strong> if you prefer the simple out-of-the-box factory interface.",
            "You can switch back and forth at any time using Innioasis Updater CE.",
        ]) + actions(("Install %s" % label, "install.html"), ("Why Rockbox", "../rockbox-benefits.html"))))
        faqs += [
            ("Does Rockbox browse large music libraries faster?",
             "Yes. Once the tag database is built, scrolling and searching large MicroSD cards is very fast."),
            ("Can I switch back to Original Software if I prefer how the player shipped?",
             "Yes. Select %s and Original Software in Updater CE to restore factory firmware." % model),
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
        (m["for_page"], "Rockbox for %s: overview & downloads" % m["model"]),
        ("../rockbox-y1-vs-y2.html", "Rockbox-Y1 vs Rockbox-Y2"),
        (m["themes"], "%s themes" % m["label"]),
        (m["guide"], "Full %s written tutorial" % m["label"]),
        (m["release_notes"], "%s release notes" % m["label"]),
        (m["other_dir"], "%s hub" % other["label"]),
    ]
    cards.extend('<article class="lumen-card lumen-card--link"><h3><a href="%s">%s</a></h3></article>' % (href, esc(text))
                 for href, text in extras if href != "%s.html" % current)
    return ('<section class="lumen-guide-section"><h2>More %s guides</h2>'
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
        "Complete guide to %s on the Innioasis %s: install with Updater CE, download developer ROM "
        "packages, customize themes, restore Original Software, and troubleshoot." % (m["label"], m["model"])
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
        "Download Rockbox ROM firmware packages for the Innioasis Y1 (Rockbox-Y1) and Y2 (Rockbox-Y2) "
        "directly from the community developers, or install in one click with Innioasis Updater CE."
    )
    blocks = [
        article_ld(title, description, canonical, []),
        breadcrumb_ld([("Home", SITE + "/"), ("Firmware Downloads", SITE + "/firmware.html"), (title, canonical)]),
    ]
    body = [section(
        "Choose your player model first",
        p(
            "Rockbox-Y1 and Rockbox-Y2 are separate firmware builds created for different hardware. "
            "Check whether your player is an Innioasis Y1 or Y2 before downloading or flashing."
        ),
    )]
    for key in ("y1", "y2"):
        m = MODELS[key]
        release = releases.get(key) or {}
        body.append(section(
            "%s (Innioasis %s)" % (m["label"], m["model"]),
            download_table(m, release, up="")
            + actions(("Install %s" % m["label"], "%s/install.html" % m["dir"]),
                      ("%s downloads" % m["label"], "%s/download.html" % m["dir"]),
                      ("Rockbox for %s" % m["model"], m["for_page"].replace("../", ""))),
            key,
        ))
    body.append(section(
        "How Updater CE downloads firmware",
        p(
            "Innioasis Updater CE always downloads firmware packages directly from the community "
            "firmware developers' own releases, and the developers themselves are solely responsible "
            "for listing their software releases in Updater CE. Each ROM package contains the MediaTek "
            "scatter file and partition images for that model."
        ) + ul([
            "Rockbox-Y1 developer release package: <code>rom.zip</code> (and <code>rom_type_b.zip</code> for Type B Y1 units).",
            "Rockbox-Y2 developer release package: <code>rom_y2.zip</code>.",
        ]),
        "what",
    ))
    body.append(section("Install automatically with Updater CE", p(
        "For the easiest setup, open Innioasis Updater CE, select your player model and Rockbox, and "
        "let the app download and flash the release directly. Follow the <a href=\"rockbox-y1/install.html\">Rockbox-Y1 "
        "install guide</a> or the <a href=\"rockbox-y2/install.html\">Rockbox-Y2 install guide</a>."
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
    lines = [
        LLMS_MARKER,
        "",
        "Rockbox is community firmware for Innioasis players. This site calls the Y1 build",
        "Rockbox-Y1 (or \"Rockbox for Y1\") and the Y2 build Rockbox-Y2 (or \"Rockbox for Y2\").",
        "Innioasis Updater CE always downloads firmware packages directly from the community",
        "firmware developers themselves, and those developers are solely responsible for",
        "listing their software releases in Updater CE.",
        "",
    ]
    for key in ("y1", "y2"):
        m = MODELS[key]
        lines.append("- [%s hub](%s/%s/): Install, developer ROM downloads, themes, restore and troubleshooting for the %s."
                     % (m["label"], SITE, m["dir"], m["model"]))
        lines.append("- [Install %s](%s/%s/install.html): Step-by-step Updater CE install guide."
                     % (m["label"], SITE, m["dir"]))
        lines.append("- [%s ROM download](%s/%s/download.html): Direct developer ROM packages for the %s."
                     % (m["label"], SITE, m["dir"], m["model"]))
        lines.append("- [Rockbox for %s](%s/rockbox-for-%s.html): Overview of %s on the Innioasis %s."
                     % (m["model"], SITE, key, m["label"], m["model"]))
        lines.append("- [%s tutorial](%s/guides/rockbox-%s.html): Full written installation walkthrough."
                     % (m["label"], SITE, key))
        lines.append("- [%s themes](%s/rockbox-%s-themes.html): Theme installation, 240p and 360p builds." % (m["label"], SITE, key))
    lines.append("- [Rockbox ROM download, both models](%s/rockbox-rom-download.html): Y1 and Y2 developer ROM packages side by side." % SITE)
    lines.append("- [Rockbox-Y1 vs Rockbox-Y2](%s/rockbox-y1-vs-y2.html): Hardware and build comparison." % SITE)
    new_block = "\n".join(lines) + "\n"
    if LLMS_MARKER in text:
        before, _, _after = text.partition(LLMS_MARKER)
        path.write_text(before.rstrip() + "\n\n" + new_block, encoding="utf-8")
        print("llms.txt: updated the Rockbox section")
    else:
        path.write_text(text.rstrip() + "\n\n" + new_block, encoding="utf-8")
        print("llms.txt: added the Rockbox section")


# ---------------------------------------------------------------- build

def build(refresh: bool = False) -> None:
    SITEMAP.clear()
    releases = {}
    for key, m in MODELS.items():
        available = project_releases(m["repo"], refresh=refresh)
        releases[key] = stable_release(available, m["stable_tag"])
        tag = releases[key].get("tag_name") or m["stable_tag"]
        print("  %-12s repo %s -> %s (%d assets)"
              % (m["label"], m["repo"], tag, len(releases[key].get("assets") or [])))
    for key, m in MODELS.items():
        hub_page(m, releases[key])
        for slug, priority in TOPICS:
            topic_page(m, slug, priority, releases[key])
        print("  %-12s wrote %d pages" % (m["label"], len(TOPICS) + 1))
    rom_download_page(releases)
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
