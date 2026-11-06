#!/usr/bin/env python3
"""
Add the locale runtime to every page.

    python scripts/i18n/install_runtime.py
    python scripts/i18n/install_runtime.py --check

The runtime is disabled for now: the site is English until real catalogs are
in place, so no page loads site-locale.js. Set ENABLED to True to resume
injecting the tag. When enabled, the tag is added once per page, before
</body>, with the correct relative prefix for the page's depth. Re-running is
safe: a page that already loads site-locale.js is left exactly as it is.
--check only reports pages that are missing the runtime, which is what CI
wants once the runtime is back on.
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

# The i18n runtime is off site-wide until the translations are real. The
# scaffolding (catalogs, extractor, translator, prerenderer) stays in place.
ENABLED = False

VERSION = "20261105b"
MARKER = "site-locale.js"
TAG = '<script src="{up}site-locale.js?v=' + VERSION + '" defer></script>'

SKIP_DIRS = {".git", "node_modules", "dist", "_site", ".cache", "__pycache__", "i18n"}


def pages() -> list[str]:
    found: list[str] = []
    for directory, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in filenames:
            if filename.lower().endswith((".html", ".htm")):
                found.append(os.path.join(directory, filename))
    return sorted(found)


def prefix_for(path: str) -> str:
    relative = os.path.relpath(path, ROOT).replace(os.sep, "/")
    depth = relative.count("/")
    return "../" * depth


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Report missing pages without writing")
    args = parser.parse_args()

    if not ENABLED:
        print("The locale runtime is disabled; no page was changed.")
        return 0

    missing: list[str] = []
    written = 0

    for path in pages():
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            markup = handle.read()

        if MARKER in markup:
            continue
        missing.append(os.path.relpath(path, ROOT).replace(os.sep, "/"))
        if args.check:
            continue

        tag = TAG.format(up=prefix_for(path))
        lower = markup.lower()
        position = lower.rfind("</body>")
        if position < 0:
            markup = markup.rstrip() + "\n" + tag + "\n"
        else:
            markup = markup[:position] + tag + markup[position:]

        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(markup)
        written += 1

    if args.check:
        print(f"{len(missing)} page(s) missing the locale runtime.")
        for page in missing[:40]:
            print("  " + page)
        return 1 if missing else 0

    print(f"Updated {written} page(s); {len(missing)} were missing the runtime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
