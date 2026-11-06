#!/usr/bin/env python3
"""Add an OS install strip to every existing software page and guide.

The heavy lifting lives in ``install/``. This script only adds a compact,
static strip after the page header, links it to the three platform-specific
guides, and loads ``site-platform.js`` so a desktop visitor sees their own
guide first. It is idempotent: a page that already has the strip is skipped.
"""
from __future__ import annotations

import html
import pathlib

import install_guides_data as data

ROOT = data.ROOT


def e(value) -> str:
    return html.escape(str(value), quote=True)


def strip_for(item: dict, prefix: str) -> str:
    family = item["family"]
    model = item["model"]
    action = "Restore" if family["action"] == "restore" else "Install"
    links = "".join(
        '<a class="lumen-button" data-os-guide="%s" href="%sinstall/%s">%s guide</a>'
        % (key, prefix, e(data.deep_name(item["slug"], key)), e(data.OS_PROFILES[key]["label"]))
        for key in data.OS_ORDER
    )
    return (
        '<section class="lumen-guide-section install-os-strip" data-os-install-strip>'
        '<p class="lumen-kicker">Install guide for your computer</p>'
        '<h2>%s %s on your %s with your computer</h2>'
        '<p>Pick the guide for the computer you are using. <span data-os-strip-note>'
        'Every version has the platform setup, Updater CE steps and the way back to stock.</span></p>'
        '<div class="lumen-actions install-os-actions">%s</div>'
        '<p class="lumen-meta"><a href="%sinstall/%s">All %s guides</a> · '
        '<a href="%sinstall/%s">All %s guides</a></p>'
        "</section>"
        % (action, e(family["name"]), e(model), links,
           prefix, e(data.model_hub_name(model)), e(data.display_model(model)),
           prefix, e(data.family_name(family["key"])), e(family["name"]))
    )


def patch(rel: str, item: dict) -> str:
    path = ROOT / rel
    if not path.is_file():
        return "missing"
    text = path.read_text(encoding="utf-8")
    prefix = "../" * (len(pathlib.Path(rel).parts) - 1)
    changed = False
    if "data-os-install-strip" not in text:
        main_at = text.find("<main")
        header_end = text.find("</header>", main_at if main_at >= 0 else 0)
        if header_end < 0:
            return "no-header"
        insert_at = header_end + len("</header>")
        text = text[:insert_at] + "\n" + strip_for(item, prefix) + text[insert_at:]
        changed = True
    if "install.css" not in text:
        text = text.replace(
            "</head>",
            '<link rel="stylesheet" href="%sinstall.css?v=20261106"></head>' % prefix,
            1,
        )
        changed = True
    if "site-platform.js" not in text:
        text = text.replace(
            "</body>",
            '<script src="%ssite-platform.js?v=20261106" defer></script></body>' % prefix,
            1,
        )
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8", newline="")
        return "patched"
    return "already"


def main() -> int:
    counts = {"patched": 0, "already": 0, "missing": 0, "no-header": 0}
    examples = []
    for item in data.CATALOG:
        item = dict(item)
        item["family"] = data.family_for_slug(item["slug"])
        rels = []
        if item.get("seoPage"):
            rels.append(item["seoPage"])
        if item.get("guide"):
            rels.append(item["guide"])
        for rel in dict.fromkeys(rels):
            result = patch(rel, item)
            counts[result] += 1
            if result in ("missing", "no-header"):
                examples.append((rel, result))
    for key, value in counts.items():
        print("%s: %d" % (key, value))
    for rel, result in examples:
        print("  %s: %s" % (result, rel))
    return 0 if not examples else 0


if __name__ == "__main__":
    raise SystemExit(main())
