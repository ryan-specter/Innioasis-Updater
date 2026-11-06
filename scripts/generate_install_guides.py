#!/usr/bin/env python3
"""Generate the OS-specific install guide pages under ``install/``.

For every software/model pair in ``firmware-catalog.js`` the generator writes
one page per desktop platform, plus software hubs, per-model hubs, per-platform
hubs and an index.  The pages are ordinary static HTML so search engines and
AI crawlers see the full guide without running JavaScript; ``site-platform.js``
only highlights the visitor's own platform and links static pages to it.

Usage:
    python scripts/generate_install_guides.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import install_guides_data as data

OUT = data.ROOT / "install"
SITE = data.SITE

HEAD_SUFFIX = {
    "windows": "with a Windows PC",
    "macos": "with a Mac",
    "linux": "on Linux",
}
ON_OS = {"windows": "on Windows", "macos": "on macOS", "linux": "on Linux"}
ARTICLE = {"windows": "a Windows PC", "macos": "a Mac", "linux": "a Linux computer"}


def e(value) -> str:
    return html.escape(str(value), quote=True)


def strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return html.unescape(text)


def verb(action: str) -> str:
    return "Restore" if action == "restore" else "Install"


def lower_verb(action: str) -> str:
    return "restore" if action == "restore" else "install"


def page_title(title: str, description: str, canonical: str, keywords: list[str],
               body: str, jsonld: list[dict], body_class: str = "") -> str:
    blocks = "".join(
        '<script type="application/ld+json">%s</script>'
        % json.dumps(block, ensure_ascii=False, separators=(",", ":"))
        for block in jsonld
    )
    classes = "site-themes-app install-page" + ((" " + body_class) if body_class else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="author" content="Innioasis and Ryan Specter">
<meta name="creator" content="Innioasis and Ryan Specter">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="keywords" content="{e(', '.join(dict.fromkeys(keywords)))}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{SITE}/assets/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{SITE}/assets/og-image.png">
<meta property="og:site_name" content="Innioasis Software Updates">
<link rel="icon" href="../y1_illustration.png">
<link rel="stylesheet" href="../site-theme.css?v=20260803">
<link rel="stylesheet" href="../lumen.css?v=20261114video">
<link rel="stylesheet" href="../site-pages.css?v=20260818">
<link rel="stylesheet" href="../site-toolbar.css?v=20261105dockclose">
<link rel="stylesheet" href="../install.css?v=20261106">
<script src="../site-init.js?v=20260803" defer></script>
{blocks}
</head>
<body class="{classes}"><a class="lumen-skip-link" href="#main">Skip to content</a>
<div id="nav-root"></div>
<main id="main" class="lumen-guide lumen-install">
{body}
</main>
<div id="footer-root"></div><div id="support-toolbar-slot"></div>
<script src="../nav.js?v=20261105copyleft" defer></script>
<script src="../site-i18n.js?v=20260830" defer></script>
<script src="../site-platform.js?v=20261106" defer></script>
</body></html>
"""


def crumb(items: list[tuple[str, str]]) -> str:
    parts = []
    for label, href in items:
        if href:
            parts.append('<a href="%s">%s</a>' % (e(href), e(label)))
        else:
            parts.append('<span aria-current="page">%s</span>' % e(label))
    return ('<nav class="install-crumb" aria-label="Breadcrumb">'
            + ' <span class="install-crumb-sep">/</span> '.join(parts)
            + "</nav>")


def breadcrumb_json(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": index + 1, "name": label, "item": href}
            for index, (label, href) in enumerate(items)
        ],
    }


def os_picker(current: str, links: dict[str, str], include_all: bool = True) -> str:
    choices = []
    for key in data.OS_ORDER:
        profile = data.OS_PROFILES[key]
        active = ' aria-current="page"' if key == current else ""
        choices.append(
            '<a class="install-os-choice%s" data-os-choice="%s" href="%s"%s>%s</a>'
            % (" install-os-choice--current" if key == current else "", key, e(links[key]), active, e(profile["label"]))
        )
    extra = ' <a class="install-os-choice" href="index.html">All platforms</a>' if include_all else ""
    return (
        '<div class="install-os-picker" data-os-picker>'
        '<span class="install-os-picker-label">Your computer</span>'
        + "".join(choices) + extra +
        '<span class="install-os-detected" data-os-detected hidden></span>'
        "</div>"
    )


def platform_actions(os_key: str) -> str:
    profile = data.OS_PROFILES[os_key]
    return (
        '<div class="lumen-actions">'
        '<a class="lumen-button lumen-button--primary" href="../guide.html#%s">Get Updater CE for %s</a>'
        '<a class="lumen-button" href="%s">%s install guides</a>'
        '<a class="lumen-button" href="../drivers.html#%s">%s</a>'
        "</div>"
        % (e(profile["anchor"]), e(profile["label"]), e(data.platform_name(os_key)),
           e(profile["label"]), e(profile["anchor"]), e(profile["driver_label"]))
    )


def os_setup_section(os_key: str) -> str:
    profile = data.OS_PROFILES[os_key]
    steps = [profile["download"]] + list(profile["setup"])
    items = "".join("<li>%s</li>" % step for step in steps)
    return (
        '<section class="lumen-guide-section install-section">'
        '<h2>Prepare %s for the install</h2>'
        '<ol class="lumen-steps">%s</ol>'
        '<p class="lumen-meta">%s <a href="../drivers.html#%s">Full %s setup notes</a>.</p>'
        "</section>"
        % (e(profile["label"]), items, profile["note"], e(profile["anchor"]), e(profile["label"]))
    )


def action_buttons(item: dict, os_key: str) -> str:
    family = item["family"]
    model = item["model"]
    return (
        '<div class="lumen-actions">'
        '<a class="lumen-button lumen-button--primary" href="../guide.html#%s">Get Updater CE</a>'
        '<a class="lumen-button" href="%s">All %s platforms</a>'
        '<a class="lumen-button" href="%s">%s install guides</a>'
        '<a class="lumen-button" href="../firmware.html?model=%s&amp;software=%s">Open in Updater</a>'
        "</div>"
        % (e(data.OS_PROFILES[os_key]["anchor"]), e(data.family_name(family["key"])),
           e(family["name"]), e(data.model_hub_name(model)), e(data.display_model(model)),
           e(model), e(item["slug"]))
    )


def before_section(item: dict, os_key: str) -> str:
    family = item["family"]
    model = item["model"]
    note = data.type_note(model, family)
    note_html = '<div class="lumen-warning"><strong>Check the Y1 hardware type.</strong><span>%s</span></div>' % e(note) if note else ""
    return f"""<section class="lumen-guide-section install-section">
<h2>Before you start</h2>
<ul class="install-checklist">
<li><strong>Player:</strong> {e(data.display_model(model))}. Check the model printed on the player; {e(family['name'])} packages for another model will not work.</li>
<li><strong>Computer:</strong> {e(data.OS_PROFILES[os_key]['label'])}. {e(data.OS_PROFILES[os_key]['note'])}</li>
<li><strong>Cable:</strong> a USB cable that carries data, not a charge-only cable.</li>
<li><strong>Power:</strong> charge the player to at least half before you begin.</li>
<li><strong>Backup:</strong> {family['preinstall']}</li>
</ul>
{note_html}
</section>"""


def main_steps(item: dict, os_key: str) -> list[tuple[str, str]]:
    family = item["family"]
    model = item["model"]
    display = data.display_model(model)
    profile = data.OS_PROFILES[os_key]
    release_note = "Choose the newest stable release shown for this model. Nightly and pre-release builds are for testing; tick the nightly-builds option only if you need one."
    return [
        ("Get Updater CE ready",
         f"Install <strong>Innioasis Updater CE</strong> on {e(ARTICLE[os_key])} and open it. The {e(profile['label'])} setup is covered above; the <a href=\"../guide.html#{e(profile['anchor'])}\">main guide</a> has the download links."),
        (f"Select {display}",
         f"In <strong>Device Model</strong>, choose <strong>{e(display)}</strong>. Do not substitute another model, even when the software name is the same."),
        (f"Choose {family['name']}",
         f"In <strong>Software</strong>, choose <strong>{e(family['name'])}</strong>. {family['preinstall']}"),
        ("Choose a release",
         f"{release_note} Read the release note for the {e(display)} before you continue."),
        ("Install / Restore",
         f"Click <strong>Install / Restore</strong>. {profile['connection']}"),
        ("Finish and check",
         f"Leave the player and cable alone until Updater CE shows success. {family['post']}"),
        ("Keep the way back",
         f"{family['restore']} The stock package is always available from the <a href=\"../firmware.html?model={e(model)}\">software archive</a>."),
    ]


def steps_section(item: dict, os_key: str) -> str:
    steps = main_steps(item, os_key)
    rendered = "".join("<li><strong>%s:</strong> %s</li>" % (e(title), text) for title, text in steps)
    return (
        '<section class="lumen-guide-section install-section">'
        '<h2>%s %s on %s %s</h2>'
        '<ol class="lumen-steps">%s</ol>'
        "</section>"
        % (verb(item["family"]["action"]), e(item["family"]["name"]),
           e(data.display_model(item["model"])), e(HEAD_SUFFIX[os_key]), rendered)
    )


def troubleshooting_section(item: dict, os_key: str) -> str:
    profile = data.OS_PROFILES[os_key]
    items = "".join("<li>%s</li>" % entry for entry in profile["troubleshoot"])
    model = item["model"]
    return f"""<section class="lumen-guide-section install-section">
<h2>If the install does not work</h2>
<ol class="lumen-steps">{items}
<li><strong>Wrong package or model:</strong> return to Device Model and confirm the printed model. On a Y1, confirm Type A or Type B before choosing the asset again.</li>
<li><strong>The player stopped responding:</strong> do not keep reconnecting. Read the <a href="../guides/recovery.html">recovery guide</a> and the <a href="../troubleshooting.html">troubleshooting guide</a> before trying a manual flash.</li>
</ol>
<p class="lumen-meta">For a manual recovery on {e(data.display_model(model))}, use the files and scatter file that match the model. <a href="../sp-flash-tool.html">SP Flash Tool notes</a>.</p>
</section>"""


def faq_for(item: dict, os_key: str) -> list[tuple[str, str]]:
    family = item["family"]
    model = item["model"]
    display = data.display_model(model)
    profile = data.OS_PROFILES[os_key]
    alias = family["aliases"][0] if family["aliases"] else family["name"]
    driver_answer = {
        "windows": "Yes. Install <code>DriverInstall.exe</code> and restart Windows before connecting the powered-off player.",
        "macos": "No separate driver is needed. macOS includes the USB support, and the app uses the MTKClient route on a Mac.",
        "linux": "No proprietary driver is needed, but your user needs the udev permission rule for vendor ID <code>0e8d</code> before Updater CE can open the player.",
    }[os_key]
    other_models = sorted({entry["model"] for entry in data.family_items(family["key"])} - {model})
    other_text = (
        "This project is listed for " + ", ".join(data.display_model(name) for name in other_models) + ". Use the model-specific guide for each player."
        if other_models else
        "This project is listed only for the " + display + " in the current catalogue."
    )
    return [
        (f"Can I {lower_verb(family['action'])} {family['name']} on {display} {ON_OS[os_key]}?",
         f"Yes. This page is the {profile['label']} guide for {family['name']} on the {display}. Install Updater CE, select the model, choose the project and follow the install prompt."),
        (f"Do I need a driver on {profile['label']}?",
         driver_answer),
        ("Will this erase my music?",
         family["preinstall"] + " Files on the microSD card are normally left alone, but remove the card first if you want to be certain."),
        (f"Is {alias} the same as {family['name']}?",
         f"Yes. {alias} is one of the names people use for {family['name']}. This guide covers the same project on the {display}."),
        (f"Does {family['name']} work on other models?",
         f"{other_text} Never install a package built for another model."),
        ("How do I undo the install?",
         family["restore"] + f" Open the <a href=\"../firmware.html?model={e(model)}\">software archive</a> or the model restore guide for the exact steps."),
        ("What if the player is not detected?",
         f"Start with the {profile['label']} checklist above, then read the <a href=\"../troubleshooting.html\">troubleshooting guide</a>. A data cable, a direct USB port and connecting only at the prompt fix most connection problems."),
    ]


def faq_section(faqs: list[tuple[str, str]]) -> str:
    entries = "".join("<details><summary>%s</summary><p>%s</p></details>" % (e(q), a) for q, a in faqs)
    return '<section class="lumen-guide-section install-section"><h2>Questions people ask</h2>%s</section>' % entries


def faq_json(faqs: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": strip_tags(q),
             "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}}
            for q, a in faqs
        ],
    }


def howto_json(name: str, description: str, steps: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": strip_tags(name),
        "description": strip_tags(description),
        "totalTime": "PT10M",
        "tool": [
            {"@type": "HowToTool", "name": "A computer running Windows, macOS or Linux"},
            {"@type": "HowToTool", "name": "A USB data cable"},
        ],
        "step": [
            {"@type": "HowToStep", "name": strip_tags(title), "text": strip_tags(text)}
            for title, text in steps
        ],
    }


def related_section(item: dict, os_key: str) -> str:
    family = item["family"]
    cards = []
    for other in data.OS_ORDER:
        if other == os_key:
            continue
        profile = data.OS_PROFILES[other]
        cards.append(
            '<article class="lumen-card install-card"><h3>%s install guide</h3>'
            '<p>%s on %s for the %s.</p>'
            '<div class="lumen-actions"><a class="lumen-button" href="%s">%s guide</a></div></article>'
            % (e(profile["label"]), e(family["name"]), e(profile["label"]),
               e(data.display_model(item["model"])), e(data.deep_name(item["slug"], other)), e(profile["label"]))
        )
    return (
        '<section class="lumen-guide-section install-section"><h2>Install this on another computer</h2>'
        '<div class="lumen-grid install-related">%s</div>'
        '<div class="lumen-actions">'
        '<a class="lumen-button" href="%s">All %s guides</a>'
        '<a class="lumen-button" href="%s">%s install guides</a>'
        '<a class="lumen-button" href="%s">All install guides</a>'
        "</div></section>"
        % ("".join(cards), e(data.family_name(family["key"])), e(family["name"]),
           e(data.model_hub_name(item["model"])), e(data.display_model(item["model"])), "index.html")
    )


def feedback_section() -> str:
    return (
        '<section class="lumen-guide-section" data-lumen-feedback data-feedback="install-guide">'
        "<h2>Was this useful?</h2><div class=\"lumen-feedback\">"
        "<p>Your answer helps improve this guide.</p>"
        '<button type="button" data-feedback-value="yes" aria-pressed="false">Yes, I found it useful</button>'
        '<button type="button" data-feedback-value="no" aria-pressed="false">Not yet</button>'
        '<a class="lumen-feedback-support" data-feedback-support hidden '
        'href="https://github.com/y1-community/Innioasis-Updater/issues" target="_blank" '
        'rel="noopener noreferrer">Let us know how we can improve</a>'
        "</div></section>"
    )


def deep_page(item: dict, os_key: str) -> tuple[str, str]:
    item = dict(item)
    item["family"] = data.family_for_slug(item["slug"])
    family = item["family"]
    model = item["model"]
    display = data.display_model(model)
    profile = data.OS_PROFILES[os_key]
    filename = data.deep_name(item["slug"], os_key)
    canonical = data.deep_url(item["slug"], os_key)
    heading = f"{verb(family['action'])} {family['h1_name']} on {display} {HEAD_SUFFIX[os_key]}"
    title = f"{verb(family['action'])} {family['h1_name']} on {display} {HEAD_SUFFIX[os_key]} | {profile['label']} install guide"
    description = (
        f"Step-by-step {family['name']} {model} {profile['label']} install guide. "
        f"{family['summary']} Includes {profile['label']} setup, Updater CE steps, drivers, "
        f"troubleshooting and the stock restore path. {data.aliases_sentence(family)}"
    )
    keywords = [
        f"how to {lower_verb(family['action'])} {family['name']} on {model} with {profile['query']}",
        f"how to {lower_verb(family['action'])} {family['name']} on {model} on {profile['label']}",
        f"{family['name']} {model} {profile['label']} tutorial",
        f"{family['name']} {profile['label']} install",
        f"{model} {profile['label']} install guide",
        f"Innioasis Updater {profile['label']}",
        f"{family['name']} {model}",
        f"install {family['name']} {model}",
    ] + list(family["aliases"])

    links = {key: data.deep_name(item["slug"], key) for key in data.OS_ORDER}
    body = "\n".join([
        crumb([
            ("Home", "../index.html"),
            ("Install guides", "index.html"),
            (family["name"], data.family_name(family["key"])),
            (display, data.model_hub_name(model)),
            (f"{profile['label']} guide", ""),
        ]),
        f"""<header>
<p class="lumen-kicker">{e(family['name'])} · {e(display)} · {e(profile['label'])}</p>
<h1>{e(heading)}</h1>
<p class="lead">{e(family['summary'])} This {e(profile['label'])} tutorial is for the {e(display)} only. {e(data.aliases_sentence(family))}</p>
{action_buttons(item, os_key)}
</header>""",
        os_picker(os_key, links),
        before_section(item, os_key),
        os_setup_section(os_key),
        steps_section(item, os_key),
        troubleshooting_section(item, os_key),
        f'<section class="lumen-guide-section install-section"><h2>Going back to {e(data.family_for_slug("original-y1")["name"])}</h2>'
        f'<p>{family["restore"]} The stock restore uses the same Updater CE flow: choose {e(display)}, choose <strong>Original Software</strong>, pick a stable release and run <strong>Install / Restore</strong>.</p>'
        f'<div class="lumen-actions"><a class="lumen-button" href="../firmware.html?model={e(model)}&amp;software=original-{e(data.model_for(model)["slug"])}">Open the {e(display)} stock restore</a>'
        f'<a class="lumen-button" href="../guides/recovery.html">Recovery guide</a></div></section>',
        faq_section(faq_for(item, os_key)),
        related_section(item, os_key),
        feedback_section(),
    ])
    jsonld = [
        howto_json(heading, description, main_steps(item, os_key)),
        faq_json(faq_for(item, os_key)),
        breadcrumb_json([
            ("Home", SITE + "/"),
            ("Install guides", SITE + "/install/"),
            (family["name"], data.family_url(family["key"])),
            (display, data.model_hub_url(model)),
            (heading, canonical),
        ]),
    ]
    return filename, page_title(title, description, canonical, keywords, body, jsonld, "install-deep")


def family_os_page(key: str, os_key: str) -> tuple[str, str]:
    family = data.FAMILIES[key]
    items = data.family_items(key)
    profile = data.OS_PROFILES[os_key]
    filename = data.family_os_name(key, os_key)
    canonical = data.family_os_url(key, os_key)
    heading = f"{verb(family['action'])} {family['h1_name']} {ON_OS[os_key]}"
    title = f"{heading} | {profile['label']} install guide"
    description = (
        f"How to {lower_verb(family['action'])} {family['name']} on {profile['query']} for every supported "
        f"Innioasis and Timmkoo model. {family['summary']} Choose the model first, then follow the "
        f"{profile['label']} Updater CE steps."
    )
    keywords = [
        f"how to {lower_verb(family['action'])} {family['name']} on {profile['label']}",
        f"{family['name']} {profile['label']} install",
        f"{family['name']} {profile['label']} tutorial",
        f"{family['name']} install guide",
        f"Innioasis Updater {profile['label']}",
    ] + list(family["aliases"])
    cards = []
    for item in items:
        cards.append(
            '<article class="lumen-card install-card"><p class="lumen-kicker">%s</p>'
            '<h3>%s on %s</h3><p>%s</p>'
            '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%s">%s guide</a>'
            '<a class="lumen-button" href="%s">Model guides</a></div></article>'
            % (e(item["model"]), e(family["name"]), e(data.display_model(item["model"])),
               e(item.get("description") or family["summary"]), e(data.deep_name(item["slug"], os_key)),
               e(profile["label"]), e(data.model_hub_name(item["model"])))
        )
    links = {other: data.family_os_name(key, other) for other in data.OS_ORDER}
    faqs = [
        (f"Which {family['name']} package should I download on {profile['label']}?",
         f"Use Innioasis Updater CE and select the model first. The app downloads the package from the project's official release. If you download manually, use the ZIP that names the model and, on a Y1, the correct Type A or Type B asset."),
        (f"Does {family['name']} work on every model?",
         "This project is listed for " + ", ".join(data.display_model(item["model"]) for item in items) + ". Open the model card for the exact guide."),
        (f"Is {family['aliases'][0]} the same as {family['name']}?",
         f"Yes. {', '.join(family['aliases'][:3])} are names people use for the same project."),
        ("Do I need a driver?",
         {"windows": "Yes. Install the MediaTek driver with DriverInstall.exe and restart before connecting the player.",
          "macos": "No separate driver is needed. Approve the app in Privacy & Security on first launch.",
          "linux": "No proprietary driver, but the udev rule for vendor ID 0e8d and your user in plugdev are required."}[os_key]),
        ("Can I undo it?", family["restore"]),
    ]
    body = "\n".join([
        crumb([("Home", "../index.html"), ("Install guides", "index.html"),
               (profile["label"], data.platform_name(os_key)), (family["name"], "")]),
        f"""<header><p class="lumen-kicker">{e(family['name'])} · {e(profile['label'])}</p>
<h1>{e(heading)}</h1>
<p class="lead">{e(family['summary'])} These {e(profile['label'])} guides cover every model the project supports. {e(data.aliases_sentence(family))}</p>
{platform_actions(os_key)}</header>""",
        os_picker(os_key, links),
        os_setup_section(os_key),
        f'<section class="lumen-guide-section install-section"><h2>Choose your model</h2><div class="lumen-grid install-related">{"".join(cards)}</div></section>',
        f'<section class="lumen-guide-section install-section"><h2>How the install works</h2><ol class="lumen-steps">'
        f'<li>Install Updater CE on {e(profile["label"])} using the steps above.</li>'
        f'<li>Select the model printed on the player, then choose <strong>{e(family["name"])}</strong>.</li>'
        f'<li>Choose a stable release listed for that model.</li>'
        f'<li>Click <strong>Install / Restore</strong>, power the player off and connect it at the prompt.</li>'
        f'<li>Wait for success. {family["post"]}</li></ol></section>',
        faq_section(faqs),
        f'<section class="lumen-guide-section install-section"><h2>Other platforms</h2><div class="lumen-actions">'
        + "".join('<a class="lumen-button" href="%s">%s</a>' % (e(data.family_os_name(key, other)), e(data.OS_PROFILES[other]["label"])) for other in data.OS_ORDER if other != os_key)
        + f'<a class="lumen-button" href="{e(data.family_name(key))}">All {e(family["name"])} guides</a>'
        + '<a class="lumen-button" href="index.html">All install guides</a></div></section>',
        feedback_section(),
    ])
    jsonld = [
        {"@context": "https://schema.org", "@type": "CollectionPage",
         "name": strip_tags(heading), "description": strip_tags(description),
         "url": canonical,
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": index + 1, "name": f"{family['name']} on {data.display_model(item['model'])} {profile['label']}",
              "url": data.deep_url(item["slug"], os_key)}
             for index, item in enumerate(items)
         ]}},
        faq_json(faqs),
        breadcrumb_json([("Home", SITE + "/"), ("Install guides", SITE + "/install/"),
                         (profile["label"], data.platform_url(os_key)),
                         (family["name"], canonical)]),
    ]
    return filename, page_title(title, description, canonical, keywords, body, jsonld, "install-family-os")


def family_hub_page(key: str) -> tuple[str, str]:
    family = data.FAMILIES[key]
    items = data.family_items(key)
    filename = data.family_name(key)
    canonical = data.family_url(key)
    heading = f"{family['name']} install guides for Windows, macOS and Linux"
    title = f"{heading} | Innioasis Updater"
    description = (
        f"Every {family['name']} install guide for Innioasis and Timmkoo players, by model and by computer. "
        f"{family['summary']} Choose Windows, macOS or Linux, then follow the Updater CE steps."
    )
    keywords = [f"{family['name']} install", f"{family['name']} install guide",
                f"how to install {family['name']}", f"{family['name']} Windows macOS Linux"] + list(family["aliases"])
    os_cards = []
    for os_key in data.OS_ORDER:
        profile = data.OS_PROFILES[os_key]
        os_cards.append(
            '<article class="lumen-card install-card"><h3>%s</h3>'
            '<p>Install %s on %s, with the setup notes for that platform.</p>'
            '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%s">%s guide</a></div></article>'
            % (e(profile["label"]), e(family["name"]), e(profile["query"]),
               e(data.family_os_name(key, os_key)), e(profile["label"]))
        )
    rows = []
    for item in items:
        rows.append(
            "<tr><td><strong>%s</strong><br><span class=\"lumen-meta\">%s</span></td>%s</tr>"
            % (e(data.display_model(item["model"])), e(item.get("description") or ""),
               "".join('<td><a href="%s">%s</a></td>' % (e(data.deep_name(item["slug"], os_key)), e(data.OS_PROFILES[os_key]["label"])) for os_key in data.OS_ORDER))
        )
    faqs = [
        (f"What is {family['name']}?", family["summary"] + " " + family["why"]),
        (f"Is {family['aliases'][0]} the same as {family['name']}?" if family["aliases"] else "Which models support it?",
         f"Yes. {', '.join(family['aliases'])} all refer to the same project." if family["aliases"] else family["summary"]),
        ("Which models are supported?", ", ".join(data.display_model(item["model"]) for item in items) + ". Use the model-specific guide before installing."),
        ("How do I go back to stock?", family["restore"]),
    ]
    body = "\n".join([
        crumb([("Home", "../index.html"), ("Install guides", "index.html"), (family["name"], "")]),
        f"""<header><p class="lumen-kicker">{e(family['name'])} · Install guides</p>
<h1>{e(heading)}</h1>
<p class="lead">{e(family['summary'])} Pick your computer first, then the model. {e(data.aliases_sentence(family))}</p>
<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="index.html">All install guides</a>
<a class="lumen-button" href="../firmware.html">Browse the software archive</a></div></header>""",
        f'<section class="lumen-guide-section install-section"><h2>Choose your computer</h2><div class="lumen-grid install-related">{"".join(os_cards)}</div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Every {e(family["name"])} install by model</h2>'
        f'<div class="lumen-table-wrap"><table class="install-matrix"><thead><tr><th>Model</th><th>Windows</th><th>macOS</th><th>Linux</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Why people install {e(family["name"])}</h2><p>{family["why"]}</p>'
        f'<p class="lumen-meta">Source: <a href="{e(family["source"])}" target="_blank" rel="noopener noreferrer">{e(family["source_label"])}</a></p></section>',
        faq_section(faqs),
        feedback_section(),
    ])
    jsonld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": strip_tags(heading),
         "description": strip_tags(description), "url": canonical,
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": index + 1,
              "name": f"{family['name']} on {data.display_model(item['model'])}",
              "url": data.deep_url(item["slug"], "windows")} for index, item in enumerate(items)
         ]}},
        faq_json(faqs),
        breadcrumb_json([("Home", SITE + "/"), ("Install guides", SITE + "/install/"),
                         (family["name"], canonical)]),
    ]
    return filename, page_title(title, description, canonical, keywords, body, jsonld, "install-family")


def model_os_page(model_id: str, os_key: str) -> tuple[str, str]:
    model = data.model_for(model_id)
    display = data.display_model(model_id)
    items = data.model_software(model_id)
    profile = data.OS_PROFILES[os_key]
    filename = data.model_os_name(model_id, os_key)
    canonical = data.model_os_url(model_id, os_key)
    heading = f"Install software on {display} {HEAD_SUFFIX[os_key]}"
    title = f"{heading} | {profile['label']} install guide"
    description = (
        f"How to install custom software and restore the stock system on the {display} with {profile['query']}. "
        f"{profile['label']} setup, Updater CE steps, model checks and troubleshooting."
    )
    keywords = [f"install software on {model_id} with {profile['query']}",
                f"{model_id} {profile['label']} install guide", f"{display} firmware {profile['label']}",
                f"{display} software {profile['label']}", f"Innioasis Updater {profile['label']}"]
    cards = []
    for item in items:
        cards.append(
            '<article class="lumen-card install-card"><p class="lumen-kicker">%s</p>'
            '<h3>%s on %s</h3><p>%s</p>'
            '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%s">%s guide</a>'
            '<a class="lumen-button" href="%s">Family guides</a></div></article>'
            % (e(item["family"]["name"]), e(item["name"]), e(display), e(item.get("description") or item["family"]["summary"]),
               e(data.deep_name(item["slug"], os_key)), e(profile["label"]),
               e(data.family_name(item["family"]["key"])))
        )
    if not cards:
        cards.append(
            '<article class="lumen-card install-card"><h3>No public custom package yet</h3>'
            '<p>The community archive does not list a dedicated custom system for this model yet. '
            f'Use <a href="../firmware.html?model={e(model_id)}">the {e(display)} archive page</a> to check for a stock restore package, and read the <a href="../guides/recovery.html">recovery guide</a> if the player will not start.</p></article>'
        )
    original = next((item for item in items if item["slug"].startswith("original-")), None)
    stock_action = (
        f'<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="{e(data.deep_name(original["slug"], os_key))}">Restore Original Software on {e(display)}</a>'
        f'<a class="lumen-button" href="../firmware.html?model={e(model_id)}">Browse the {e(display)} archive</a></div>'
        if original else
        f'<div class="lumen-actions"><a class="lumen-button" href="../firmware.html?model={e(model_id)}">Browse the {e(display)} archive</a></div>'
    )
    links = {other: data.model_os_name(model_id, other) for other in data.OS_ORDER}
    faqs = [
        (f"Can I install custom software on the {display} with {profile['label']}?",
         f"Yes, when the project lists the {display}. Every project card above opens the {profile['label']} guide for that software and model."),
        (f"Do I need a driver on {profile['label']}?",
         {"windows": "Yes, install the MediaTek driver and restart.",
          "macos": "No separate driver. Approve the app in Privacy & Security on first launch.",
          "linux": "Add the udev rule for vendor ID 0e8d and make the AppImage executable."}[os_key]),
        ("Will I lose my music?", "Back up first. A full system install can wipe internal storage; the microSD card is normally left alone."),
        ("How do I restore the factory software?", "Choose the model and Original Software in Updater CE, pick a stable release, then run Install / Restore."),
    ]
    body = "\n".join([
        crumb([("Home", "../index.html"), ("Install guides", "index.html"),
               (display, data.model_hub_name(model_id)), (profile["label"], "")]),
        f"""<header><p class="lumen-kicker">{e(display)} · {e(profile['label'])}</p>
<h1>{e(heading)}</h1>
<p class="lead">{e(model.get('description') or model.get('blurb') or '')} These are the {e(profile['label'])} routes for the {e(display)}.</p>
{platform_actions(os_key)}</header>""",
        os_picker(os_key, links),
        os_setup_section(os_key),
        f'<section class="lumen-guide-section install-section"><h2>Software for the {e(display)}</h2><div class="lumen-grid install-related">{"".join(cards)}</div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Restore the stock system</h2><p>{e(model.get("description") or "")}</p>{stock_action}</section>',
        faq_section(faqs),
        f'<section class="lumen-guide-section install-section"><h2>Other platforms</h2><div class="lumen-actions">'
        + "".join('<a class="lumen-button" href="%s">%s</a>' % (e(data.model_os_name(model_id, other)), e(data.OS_PROFILES[other]["label"])) for other in data.OS_ORDER if other != os_key)
        + f'<a class="lumen-button" href="{e(data.model_hub_name(model_id))}">All {e(display)} guides</a>'
        + '<a class="lumen-button" href="index.html">All install guides</a></div></section>',
        feedback_section(),
    ])
    jsonld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": strip_tags(heading),
         "description": strip_tags(description), "url": canonical},
        faq_json(faqs),
        breadcrumb_json([("Home", SITE + "/"), ("Install guides", SITE + "/install/"),
                         (display, data.model_hub_url(model_id)), (profile["label"], canonical)]),
    ]
    return filename, page_title(title, description, canonical, keywords, body, jsonld, "install-model-os")


def model_hub_page(model_id: str) -> tuple[str, str]:
    model = data.model_for(model_id)
    display = data.display_model(model_id)
    items = data.model_software(model_id)
    filename = data.model_hub_name(model_id)
    canonical = data.model_hub_url(model_id)
    heading = f"{display} software and firmware install guides"
    title = f"{heading} | Windows, macOS and Linux"
    description = (
        f"Install custom software or restore the factory system on the {display}. Guides for every supported "
        f"project on Windows, macOS and Linux, with model checks, drivers and recovery."
    )
    keywords = [f"{display} software", f"{display} firmware", f"{display} install guide",
                f"{model_id} software install", f"{display} Windows macOS Linux"]
    os_cards = []
    for os_key in data.OS_ORDER:
        profile = data.OS_PROFILES[os_key]
        os_cards.append(
            '<article class="lumen-card install-card"><h3>%s</h3>'
            '<p>Install or restore software on the %s with %s.</p>'
            '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%s">%s guide</a></div></article>'
            % (e(profile["label"]), e(display), e(profile["query"]),
               e(data.model_os_name(model_id, os_key)), e(profile["label"]))
        )
    rows = []
    for item in items:
        rows.append(
            "<tr><td><strong>%s</strong><br><span class=\"lumen-meta\">%s</span></td>%s</tr>"
            % (e(item["name"]), e(item.get("description") or ""),
               "".join('<td><a href="%s">%s</a></td>' % (e(data.deep_name(item["slug"], os_key)), e(data.OS_PROFILES[os_key]["label"])) for os_key in data.OS_ORDER))
        )
    if not rows:
        rows.append('<tr><td colspan="4">No dedicated custom software is listed for this model yet. Use the archive page to check for a stock restore package.</td></tr>')
    body = "\n".join([
        crumb([("Home", "../index.html"), ("Install guides", "index.html"), (display, "")]),
        f"""<header><p class="lumen-kicker">{e(display)} · Software and firmware</p>
<h1>{e(heading)}</h1>
<p class="lead">{e(model.get('description') or model.get('blurb') or '')}</p>
<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="../firmware.html?model={e(model_id)}">Browse the {e(display)} archive</a>
<a class="lumen-button" href="index.html">All install guides</a>
<a class="lumen-button" href="../guides/recovery.html">Recovery guide</a></div></header>""",
        f'<section class="lumen-guide-section install-section"><h2>Choose your computer</h2><div class="lumen-grid install-related">{"".join(os_cards)}</div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Software and firmware for the {e(display)}</h2>'
        f'<div class="lumen-table-wrap"><table class="install-matrix"><thead><tr><th>Software</th><th>Windows</th><th>macOS</th><th>Linux</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Model details</h2><ul class="install-checklist">'
        f'<li><strong>Brand:</strong> {e(model.get("brand"))}</li>'
        f'<li><strong>Model:</strong> {e(model_id)}</li>'
        f'<li><strong>Platform:</strong> {e(model.get("platform") or "Not listed")}</li>'
        f'<li><strong>Stock package:</strong> {e(model.get("package") or "See the archive")}</li></ul>'
        f'<p class="lumen-meta">' + (f'Player manual: <a href="../{e(model.get("manual"))}">{e(display)} manual</a> · ' if model.get("manual") else '') + f'<a href="../firmware.html?model={e(model_id)}">Firmware archive</a></p></section>',
        feedback_section(),
    ])
    jsonld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": strip_tags(heading),
         "description": strip_tags(description), "url": canonical},
        breadcrumb_json([("Home", SITE + "/"), ("Install guides", SITE + "/install/"),
                         (display, canonical)]),
    ]
    return filename, page_title(title, description, canonical, keywords, body, jsonld, "install-model")


def platform_page(os_key: str) -> tuple[str, str]:
    profile = data.OS_PROFILES[os_key]
    filename = data.platform_name(os_key)
    canonical = data.platform_url(os_key)
    heading = f"Install Innioasis and Timmkoo software on {profile['label']}"
    title = f"{heading} | OS-specific install guides"
    description = (
        f"Every Innioasis and Timmkoo software install guide for {profile['label']}. Set up Updater CE, "
        f"install the required driver or permissions, then follow the model-specific guide for Rockbox, "
        f"Solar, Reborn, JJ Launcher and the stock restore."
    )
    keywords = [f"install Innioasis software on {profile['label']}", f"Timmkoo firmware {profile['label']}",
                f"Innioasis Updater {profile['label']}", f"Rockbox {profile['label']}",
                f"{profile['label']} install guide"]
    rows = []
    for key, family in data.FAMILIES.items():
        items = data.family_items(key)
        models = ", ".join(data.display_model(item["model"]) for item in items)
        deep_links = " · ".join('<a href="%s">%s</a>' % (e(data.deep_name(item["slug"], os_key)), e(data.display_model(item["model"]))) for item in items)
        rows.append(
            "<tr><td><strong>%s</strong><br><span class=\"lumen-meta\">%s</span></td><td>%s</td><td>%s</td></tr>"
            % (e(family["name"]), e(models), deep_links,
               '<a href="%s">%s guide</a>' % (e(data.family_os_name(key, os_key)), e(family["name"])))
        )
    model_cards = []
    for model in data.MODELS:
        model_cards.append(
            '<article class="lumen-card install-card"><h3>%s</h3>'
            '<p>%s</p><div class="lumen-actions"><a class="lumen-button" href="%s">%s install guides</a></div></article>'
            % (e(data.display_model(model["id"])), e(model.get("blurb") or ""),
               e(data.model_os_name(model["id"], os_key)), e(profile["label"]))
        )
    faqs = [
        (f"Do I need to install a driver on {profile['label']}?",
         {"windows": "Yes. Install DriverInstall.exe and restart before connecting the player.",
          "macos": "No separate driver. Approve Updater CE in Privacy & Security the first time you open it.",
          "linux": "No proprietary driver, but add the udev rule for vendor ID 0e8d and make the AppImage executable."}[os_key]),
        ("Does Updater CE keep my music?", "A normal Updater CE install keeps the music on the microSD card. A full stock restore can wipe internal storage, so back up first."),
        ("Where are the model-specific guides?", "Use the software table above, or open the model card for your player. Every install page names the model and platform in its title."),
        ("Can I use a different computer?", "Yes. Each guide has links to the Windows, macOS and Linux versions at the top of the page."),
    ]
    body = "\n".join([
        crumb([("Home", "../index.html"), ("Install guides", "index.html"), (profile["label"], "")]),
        f"""<header><p class="lumen-kicker">Install guides · {e(profile['label'])}</p>
<h1>{e(heading)}</h1>
<p class="lead">Set up Innioasis Updater CE on {e(profile['article'])}, then use the model-specific guide for the software you want. {e(profile['note'])}</p>
{platform_actions(os_key)}</header>""",
        os_setup_section(os_key),
        f'<section class="lumen-guide-section install-section"><h2>Every software guide for {e(profile["label"])}</h2>'
        f'<div class="lumen-table-wrap"><table class="install-matrix"><thead><tr><th>Software</th><th>Models</th><th>{e(profile["label"])} guide</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Choose your model</h2><div class="lumen-grid install-related">{"".join(model_cards)}</div></section>',
        faq_section(faqs),
        f'<section class="lumen-guide-section install-section"><h2>Other platforms</h2><div class="lumen-actions">'
        + "".join('<a class="lumen-button" href="%s">%s</a>' % (e(data.platform_name(other)), e(data.OS_PROFILES[other]["label"])) for other in data.OS_ORDER if other != os_key)
        + '<a class="lumen-button" href="index.html">All install guides</a></div></section>',
        feedback_section(),
    ])
    jsonld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": strip_tags(heading),
         "description": strip_tags(description), "url": canonical},
        faq_json(faqs),
        breadcrumb_json([("Home", SITE + "/"), ("Install guides", SITE + "/install/"),
                         (profile["label"], canonical)]),
    ]
    return filename, page_title(title, description, canonical, keywords, body, jsonld, "install-platform")


def index_page() -> tuple[str, str]:
    filename = "index.html"
    canonical = SITE + "/install/"
    heading = "Install guides for every Innioasis and Timmkoo software"
    title = "Innioasis and Timmkoo install guides for Windows, macOS and Linux"
    description = (
        "Every Innioasis Updater software guide, by platform and by player. Install Rockbox, Solar, "
        "Reborn (Y2Linux), JJ Launcher, Inniclassic, Y2Player, Koensayr, Better-Y, Rondo or the stock "
        "firmware on Windows, macOS or Linux."
    )
    keywords = ["Innioasis install guides", "Timmkoo install guides", "Innioasis Updater install",
                "Rockbox install guide", "Reborn Y2Linux install", "JJ Launcher install",
                "Windows macOS Linux firmware install"]
    platform_cards = []
    for os_key in data.OS_ORDER:
        profile = data.OS_PROFILES[os_key]
        platform_cards.append(
            '<article class="lumen-card install-card"><h3>%s</h3>'
            '<p>Setup notes and every software guide for %s.</p>'
            '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%s">%s install guides</a></div></article>'
            % (e(profile["label"]), e(profile["query"]), e(data.platform_name(os_key)), e(profile["label"]))
        )
    family_rows = []
    for key, family in data.FAMILIES.items():
        items = data.family_items(key)
        family_rows.append(
            "<tr><td><strong>%s</strong> <a class=\"lumen-meta\" href=\"%s\">all</a><br><span class=\"lumen-meta\">%s</span></td>%s</tr>"
            % (e(family["name"]), e(data.family_name(key)),
               e(", ".join(data.display_model(item["model"]) for item in items)),
               "".join('<td><a href="%s">%s</a></td>' % (e(data.family_os_name(key, os_key)), e(data.OS_PROFILES[os_key]["label"])) for os_key in data.OS_ORDER))
        )
    deep_rows = []
    for item in data.CATALOG:
        deep_rows.append(
            "<tr><td><strong>%s</strong><br><span class=\"lumen-meta\">%s</span></td>%s</tr>"
            % (e(data.display_model(item["model"])), e(item["name"]),
               "".join('<td><a href="%s">%s</a></td>' % (e(data.deep_name(item["slug"], os_key)), e(data.OS_PROFILES[os_key]["label"])) for os_key in data.OS_ORDER))
        )
    model_cards = []
    for model in data.MODELS:
        model_cards.append(
            '<article class="lumen-card install-card"><h3>%s</h3><p>%s</p>'
            '<div class="lumen-actions"><a class="lumen-button" href="%s">Install guides</a></div></article>'
            % (e(data.display_model(model["id"])), e(model.get("blurb") or ""), e(data.model_hub_name(model["id"])))
        )
    faqs = [
        ("Which install guide should I open?",
         "Open the platform page for the computer you are using, then choose the model and software. Every guide names both the model and the platform in its title."),
        ("Do the guides cover Windows, macOS and Linux?",
         "Yes. Each software/model combination has a Windows, a macOS and a Linux page, and the top of every page links to the other two platforms."),
        ("What software is covered?",
         "Rockbox, Solar, Reborn (Y2Linux), JJ Launcher, Inniclassic, Y2Player, Koensayr, Better-Y, Rondo, the Android development ROMs, Linux for Y1 and Original Software for every supported model."),
        ("Where do downloads come from?",
         "Innioasis Updater CE downloads each package from the project's official release. The software archive also links the original release and portable ZIPs."),
    ]
    body = "\n".join([
        crumb([("Home", "../index.html"), ("Install guides", "")]),
        f"""<header><p class="lumen-kicker">Install guides · Windows, macOS, Linux</p>
<h1>{e(heading)}</h1>
<p class="lead">Pick your computer, then your player and software. Every page is a complete install tutorial with the platform setup, Updater CE steps, model checks and the way back to stock.</p>
<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="../guide.html">Get Innioasis Updater CE</a>
<a class="lumen-button" href="../firmware.html">Browse the software archive</a>
<a class="lumen-button" href="../troubleshooting.html">Troubleshooting</a></div></header>""",
        f'<section class="lumen-guide-section install-section"><h2>Choose your computer</h2><div class="lumen-grid install-related">{"".join(platform_cards)}</div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Software by platform</h2>'
        f'<div class="lumen-table-wrap"><table class="install-matrix"><thead><tr><th>Software and models</th><th>Windows</th><th>macOS</th><th>Linux</th></tr></thead><tbody>{"".join(family_rows)}</tbody></table></div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Every install guide</h2>'
        f'<div class="lumen-table-wrap"><table class="install-matrix"><thead><tr><th>Model and software</th><th>Windows</th><th>macOS</th><th>Linux</th></tr></thead><tbody>{"".join(deep_rows)}</tbody></table></div></section>',
        f'<section class="lumen-guide-section install-section"><h2>Install guides by player</h2><div class="lumen-grid install-related">{"".join(model_cards)}</div></section>',
        faq_section(faqs),
        feedback_section(),
    ])
    jsonld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": strip_tags(heading),
         "description": strip_tags(description), "url": canonical},
        faq_json(faqs),
        breadcrumb_json([("Home", SITE + "/"), ("Install guides", canonical)]),
    ]
    return filename, page_title(title, description, canonical, keywords, body, jsonld, "install-index")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    written = []
    for item in data.CATALOG:
        for os_key in data.OS_ORDER:
            filename, text = deep_page(item, os_key)
            (OUT / filename).write_text(text, encoding="utf-8")
            written.append(filename)
    for key in data.FAMILIES:
        for os_key in data.OS_ORDER:
            filename, text = family_os_page(key, os_key)
            (OUT / filename).write_text(text, encoding="utf-8")
            written.append(filename)
        filename, text = family_hub_page(key)
        (OUT / filename).write_text(text, encoding="utf-8")
        written.append(filename)
    for model in data.MODELS:
        for os_key in data.OS_ORDER:
            filename, text = model_os_page(model["id"], os_key)
            (OUT / filename).write_text(text, encoding="utf-8")
            written.append(filename)
        filename, text = model_hub_page(model["id"])
        (OUT / filename).write_text(text, encoding="utf-8")
        written.append(filename)
    for os_key in data.OS_ORDER:
        filename, text = platform_page(os_key)
        (OUT / filename).write_text(text, encoding="utf-8")
        written.append(filename)
    filename, text = index_page()
    (OUT / filename).write_text(text, encoding="utf-8")
    written.append(filename)
    print("install guides: wrote %d pages" % len(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
