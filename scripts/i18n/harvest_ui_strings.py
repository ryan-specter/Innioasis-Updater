#!/usr/bin/env python3
"""
Harvest user-facing strings from the JavaScript shell.

Navigation, the footer, the dock and the directory UI are all rendered by
nav.js and lumen-site.js, so their copy never appears in the static HTML that
extract_strings.py reads. This pulls sentence-like string literals out of those
files into i18n/strings/ui.json, which extract_strings.py merges into the
source catalog.

    python scripts/i18n/harvest_ui_strings.py

The filter is deliberately conservative: a literal must contain a space, start
with a capital letter, and carry no URL, markup or code punctuation. Anything
that slips through is still visible in ui.json and can be dropped by hand.
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

SHELL_FILES = [
    "nav.js",
    "lumen-site.js",
    "site-init.js",
    "firmware-catalog.js",
    "tutorial-video.js",
    "portable-zip-links.js",
    "docs-viewer.js",
    "site-locale.js",
    "support_toolbar.html",
]

# Inline scripts inside a page render their own copy too, so they are scanned
# alongside the shared shell files.
INLINE_SCRIPT_RE = re.compile(
    r"<script\b(?![^>]*\bsrc\s*=)[^>]*>([\s\S]*?)</script>", re.IGNORECASE
)

LITERAL_RE = re.compile(r"""(['"])((?:\\.|(?!\1)[^\\\n]){6,240}?)\1""")
HAS_WORD_RE = re.compile(r"[A-Za-z]{2,}")
REJECT_FRAGMENTS = (
    "http",
    "://",
    "<",
    ">",
    "=",
    "{",
    "}",
    ";",
    "_",
    "/",
    "\\",
    "function",
    "px",
    "%",
    "#",
    "@",
    "(",
    ")",
    "[",
    "]",
)


def looks_like_prose(value: str) -> bool:
    text = value.strip()
    if len(text) < 6 or len(text) > 220:
        return False
    if " " not in text:
        return False
    if not re.match(r"^[A-Z]", text):
        return False
    if not HAS_WORD_RE.search(text):
        return False
    if any(fragment in text for fragment in REJECT_FRAGMENTS):
        return False
    # A CSS rule or a selector is not copy.
    if text.count(",") > 3 or text.count(":") > 1:
        return False
    if re.fullmatch(r"[A-Z0-9 .&+-]+", text):
        return False
    # Copy already written in another script belongs to that edition.
    if re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]", text):
        return False
    # Currency and symbol tables are data, not copy.
    if re.search(r"[\u20a0-\u20bf\u060b\u09f3\u0e3f\u17db\ufdfc]", text):
        return False
    # Prose is mostly letters; a list of three-letter codes is not.
    letters = len(re.findall(r"[A-Za-z]", text))
    if letters / max(1, len(text)) < 0.6:
        return False
    if len(re.findall(r"[A-Za-z]{3,}", text)) < 2:
        return False
    return True


def collect(source: str, origin: str, found: dict[str, list[str]]) -> None:
    for match in LITERAL_RE.finditer(source):
        value = match.group(2)
        if not looks_like_prose(value):
            continue
        found.setdefault(value.strip(), []).append(origin)


def main() -> int:
    found: dict[str, list[str]] = {}
    for relative in SHELL_FILES:
        path = os.path.join(ROOT, relative)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            collect(handle.read(), relative, found)

    inline_pages = 0
    for directory, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            name for name in dirnames
            if name not in {".git", "node_modules", "dist", "_site", ".cache", "__pycache__", "i18n"}
        ]
        for filename in filenames:
            if not filename.lower().endswith((".html", ".htm")):
                continue
            path = os.path.join(directory, filename)
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                markup = handle.read()
            blocks = INLINE_SCRIPT_RE.findall(markup)
            if not blocks:
                continue
            inline_pages += 1
            relative = os.path.relpath(path, ROOT).replace(os.sep, "/")
            for block in blocks:
                collect(block, relative, found)

    output = {
        "note": "Strings rendered by the JS shell. Merged into the source catalog by extract_strings.py.",
        "strings": {text: sorted(set(files)) for text, files in sorted(found.items())},
    }

    target = os.path.join(ROOT, "i18n", "strings", "ui.json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=1)
        handle.write("\n")

    print(f"Harvested {len(found)} shell strings from {len(SHELL_FILES)} files "
          f"and {inline_pages} pages with inline scripts into {os.path.relpath(target, ROOT)}")
    if "--list" in sys.argv:
        for text in sorted(found, key=len, reverse=True):
            print(repr(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
