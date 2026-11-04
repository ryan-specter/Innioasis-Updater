#!/usr/bin/env python3
"""Write a static page for every firmware release and post-install guide.

The live site renders these from GitHub at request time (release_notes.html,
post_install.html). Search engines and answer engines only see that rendering
when they execute scripts, so this generator writes the same documents as
plain HTML with stable URLs:

    release-notes/<software>/<tag>.html    one release's notes
    release-notes/<software>/index.html    every release of one software
    release-notes/index.html               the archive index
    post-install/<software>.html           imported post-install Markdown
    post-install/index.html                the post-install index

Everything is driven by slidia_manifest.xml plus firmware-catalog.js, so a new
release (or a new project) appears on the next run of the workflow. Old
releases keep their pages; nothing is hand-maintained.

Markdown handling intentionally mirrors docs-viewer.js: GitHub blob/raw URLs
are resolved to raw files, relative links and images are rewritten against the
repository, and tables, nested lists, task lists, fenced code, images and
quotes all render. Raw HTML from a README is kept only for a small allowlist
of tags and with event handlers and script URLs stripped.

Usage:
    python scripts/generate_doc_pages.py [--refresh] [--limit N]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://innioasis.app"
BRAND = "Innioasis Updater"
CACHE = ROOT / ".cache" / "doc-pages"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
MAX_RELEASES = int(os.environ.get("MAX_RELEASES_PER_REPO", "200"))
ALLOWED_HANDLERS = {"", "Custom Firmware"}

# ---------------------------------------------------------------- utilities


def read_mirror_repo() -> str:
    """Read the mirror repo from docs-viewer.js so both sides agree."""
    env = (os.environ.get("PORTABLE_MIRROR_REPO") or "").strip()
    if env:
        return env
    try:
        source = (ROOT / "docs-viewer.js").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r'PORTABLE_MIRROR_REPO\s*=\s*"([^"]+)"', source)
    return match.group(1) if match else ""


MIRROR_REPO = read_mirror_repo()


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def one_line(value: str, limit: int = 180) -> str:
    text = re.sub(r"[*_`#>\[\]|]", " ", str(value or ""))
    text = re.sub(r"\(([^)]*)\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].strip()


def software_label(item: dict) -> str:
    """The name a software's pages should carry.

    The catalogue lists the software as "Rockbox" for both players, but people
    search for the port by model name. A project that publishes one build per
    player is titled "Rockbox-Y1" / "Rockbox-Y2" so its release notes and
    post-install pages name the build a reader arrived for. Anything a
    catalogue row declares as ``label`` wins over this default.
    """
    declared = str(item.get("label") or "").strip()
    if declared:
        return declared
    name = str(item.get("name") or item.get("slug") or "").strip()
    model = str(item.get("model") or "").strip()
    if name and model and name.lower() == "rockbox":
        return "%s-%s" % (name, model)
    return name or str(item.get("slug") or "")


def tag_slug(tag: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", str(tag or "").lower()).strip("-")
    return slug or "release"


def software_slug(name: str, device: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    return (base + "-" + str(device or "").lower()).strip("-")


SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def safe_slug(value: str) -> bool:
    return bool(value) and bool(SAFE_NAME.match(value)) and ".." not in value


# ---------------------------------------------------------------- data files


def load_catalog() -> list[dict]:
    path = ROOT / "firmware-catalog.js"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    match = re.search(r"window\.INNIOASIS_FIRMWARE_CATALOG\s*=\s*(\[[\s\S]*?\n\]);", text)
    if not match:
        return []
    try:
        items = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return [item for item in items if isinstance(item, dict) and item.get("slug")]


def load_manifest() -> list[dict]:
    path = ROOT / "slidia_manifest.xml"
    if not path.exists():
        return []
    tree = ET.parse(path)
    packages = []
    for node in tree.getroot().findall("package"):
        data = {key: (value or "").strip() for key, value in node.attrib.items()}
        name = data.get("name", "")
        if not name or re.search(r"please update", name, re.I):
            continue
        if (data.get("handler") or "") not in ALLOWED_HANDLERS:
            continue
        if data.get("device_type") == "0":
            continue
        data["device"] = (data.get("device") or "").upper()
        packages.append(data)
    return packages


def build_software(catalog: list[dict], manifest: list[dict]) -> list[dict]:
    """One record per software/model, preferring the catalog's slug and repo."""
    by_key: dict[tuple[str, str], dict] = {}
    for item in catalog:
        key = (item.get("repo", "").lower(), (item.get("model") or "").upper())
        by_key[key] = dict(item, model=(item.get("model") or "").upper())

    for pkg in manifest:
        repo = pkg.get("repo", "").lower()
        device = pkg.get("device", "")
        match = by_key.get((repo, device))
        if not match:
            match = next(
                (item for item in by_key.values()
                 if item.get("name", "").lower() == pkg.get("name", "").lower()
                 and item.get("model") == device),
                None,
            )
        if match is None:
            slug = software_slug(pkg.get("name", ""), device)
            match = {
                "slug": slug,
                "name": pkg.get("name", ""),
                "model": device,
                "repo": pkg.get("repo", ""),
                "packageName": "rom_y2.zip" if device == "Y2" else "rom.zip",
                "description": "Community firmware package for the " + device + ".",
                "guide": "",
                "seoPage": "",
            }
            by_key[(repo, device)] = match
        if pkg.get("post_install"):
            match["post_install"] = pkg["post_install"]
        if pkg.get("post_install2"):
            match["post_install2"] = pkg["post_install2"]
        if pkg.get("icon") and not match.get("icon"):
            match["icon"] = pkg["icon"]
        # The manifest is what Updater CE reads, so its repository is the one
        # whose releases belong on these pages.
        if pkg.get("repo"):
            match["repo"] = pkg["repo"]

    seen: dict[str, dict] = {}
    for item in by_key.values():
        slug = item.get("slug") or software_slug(item.get("name", ""), item.get("model", ""))
        if not safe_slug(slug):
            continue
        item["slug"] = slug
        item["model"] = (item.get("model") or "").upper()
        seen[slug] = item
    return sorted(seen.values(), key=lambda entry: (entry.get("model", ""), entry.get("name", "")))


# ---------------------------------------------------------------- github api


def cached_json(url: str, refresh: bool = False):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    path = CACHE / (key + ".json")
    if not refresh and path.exists() and time.time() - path.stat().st_mtime < 3600:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "innioasis-site-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in (403, 404, 422):
            payload = [] if "releases" in url else {}
        else:
            print("  ! HTTP %s for %s" % (error.code, url), file=sys.stderr)
            payload = [] if "releases" in url else {}
    except Exception as error:  # noqa: BLE001 - a missing feed must not stop the build
        print("  ! %s for %s" % (error, url), file=sys.stderr)
        payload = [] if "releases" in url else {}
    try:
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass
    return payload


def fetch_releases(repo: str, refresh: bool = False) -> list[dict]:
    if not repo:
        return []
    releases: list[dict] = []
    page = 1
    while len(releases) < MAX_RELEASES:
        batch = cached_json(
            "https://api.github.com/repos/%s/releases?per_page=100&page=%d" % (repo, page),
            refresh=refresh,
        )
        if not isinstance(batch, list) or not batch:
            break
        releases.extend(entry for entry in batch if isinstance(entry, dict))
        if len(batch) < 100:
            break
        page += 1
    return releases[:MAX_RELEASES]


def mirror_index(refresh: bool = False) -> dict[tuple[str, str], list[dict]]:
    """Map (repo-slug, tag) to repackaged portable assets."""
    index: dict[tuple[str, str], list[dict]] = {}
    if not MIRROR_REPO:
        return index
    releases: list[dict] = []
    for page in (1, 2):
        batch = cached_json(
            "https://api.github.com/repos/%s/releases?per_page=100&page=%d" % (MIRROR_REPO, page),
            refresh=refresh,
        )
        if isinstance(batch, list):
            releases.extend(batch)
    for release in releases:
        names = [str(release.get("tag_name") or ""), str(release.get("name") or "")]
        for key, asset in [
            (name, asset)
            for name in names
            for asset in (release.get("assets") or [])
        ]:
            lower_name = key.lower()
            if "@" not in lower_name:
                continue
            slug, _, tag = lower_name.partition("@")
            asset_name = str(asset.get("name") or "")
            if not re.search(r"\.(zip|7z|tar\.gz)$", asset_name, re.I):
                continue
            index.setdefault((slug.strip(), tag.strip()), []).append(asset)
    return index


# ---------------------------------------------------------------- markdown

ALLOWED_HTML = {
    "a", "abbr", "b", "blockquote", "br", "caption", "center", "code", "col",
    "colgroup", "dd", "del", "details", "div", "dl", "dt", "em", "figcaption",
    "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "input",
    "kbd", "li", "mark", "ol", "p", "picture", "pre", "q", "s", "samp",
    "small", "source", "span", "strike", "strong", "sub", "summary", "sup",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul", "var",
    "video", "wbr",
}
DROP_BLOCKS = re.compile(
    r"(?is)<(script|style|iframe|object|embed|form|button|select|textarea|template|noscript)\b.*?</\1>"
)


def clean_html(markup: str, ctx: dict | None = None) -> str:
    markup = DROP_BLOCKS.sub("", markup or "")

    def rewrite_attr(match: re.Match) -> str:
        name, quote_char, value = match.group(1), match.group(2), match.group(3)
        plain = html.unescape(value)
        resolved = resolve_link(plain, ctx) if name.lower() == "href" else resolve_asset(plain, ctx)
        if resolved == plain:
            return match.group(0)
        return " %s=%s%s%s" % (name, quote_char, esc(resolved), quote_char)

    def replace_tag(match: re.Match) -> str:
        closing, name, attrs = match.group(1), match.group(2).lower(), match.group(3) or ""
        if name not in ALLOWED_HTML:
            return ""
        attrs = re.sub(r"(?i)\son[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", attrs)
        attrs = re.sub(r"(?is)\s(srcdoc|formaction)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", attrs)
        attrs = re.sub(
            r"(?i)\s(href|src|poster)\s*=\s*(\"|')\s*(javascript|vbscript|data:text/html):[^\"']*\2",
            r' \1="#"',
            attrs,
        )
        # Relative paths in raw README HTML only resolve inside the repository.
        attrs = re.sub(r"(?is)\s(href|src|poster)\s*=\s*(\"|')([^\"']*)\2", rewrite_attr, attrs)
        return "<%s%s%s>" % (closing, name, attrs)

    return re.sub(r"(?is)<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:\s[^<>]*)?)>", replace_tag, markup)


def parse_source(url: str):
    """Resolve a post_install or doc URL to a raw file plus its base paths."""
    if not url:
        return None
    url = url.strip()
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        return None
    host = parsed.netloc.lower()
    segments = [urllib.parse.unquote(s) for s in parsed.path.split("/") if s]
    anchor = ("#" + parsed.fragment) if parsed.fragment else ""

    def github(repo, ref, path, source_url):
        directory = path.rsplit("/", 1)[0] if "/" in path else ""
        raw_dir = "https://raw.githubusercontent.com/%s/%s/%s" % (repo, ref, directory + "/" if directory else "")
        blob_dir = "https://github.com/%s/blob/%s/%s" % (repo, ref, directory + "/" if directory else "")
        return {
            "kind": "github",
            "host": "GitHub",
            "repo": repo,
            "ref": ref,
            "path": path,
            "raw_url": "https://raw.githubusercontent.com/%s/%s/%s" % (repo, ref, path),
            "blob_url": "https://github.com/%s/blob/%s/%s" % (repo, ref, path),
            "raw_dir": raw_dir,
            "blob_dir": blob_dir,
            "source_url": source_url,
            "anchor": anchor,
        }

    if host in ("github.com", "www.github.com") and len(segments) >= 4 and segments[2] in ("blob", "raw"):
        repo = segments[0] + "/" + segments[1]
        ref = segments[3]
        path = "/".join(segments[4:])
        if path and re.search(r"\.(md|markdown|mdown|mkd|mdx)$", path, re.I):
            return github(repo, ref, path, url)
        return None

    if host == "raw.githubusercontent.com" and len(segments) >= 4:
        repo = segments[0] + "/" + segments[1]
        ref = segments[2]
        path = "/".join(segments[3:])
        if path and re.search(r"\.(md|markdown|mdown|mkd|mdx)$", path, re.I):
            resolved = github(repo, ref, path, url)
            resolved["kind"] = "github-raw"
            resolved["raw_url"] = urllib.parse.urlunsplit(parsed._replace(fragment=""))
            return resolved
        return None

    if host == "gist.github.com" and len(segments) >= 2:
        raw = "https://gist.githubusercontent.com/%s/%s/raw" % (segments[0], segments[1])
        return {
            "kind": "gist", "host": "GitHub Gist", "repo": "", "ref": "",
            "path": "/".join(segments[2:]) or segments[1],
            "raw_url": raw, "blob_url": url.split("#")[0],
            "raw_dir": raw + "/", "blob_dir": url.split("#")[0],
            "source_url": url, "anchor": anchor,
        }

    if host == "gitlab.com" and "-" in segments:
        dash = segments.index("-")
        if segments[dash + 1 : dash + 2] and segments[dash + 1] in ("blob", "raw"):
            repo = "/".join(segments[:dash])
            ref = segments[dash + 2]
            path = "/".join(segments[dash + 3 :])
            if path and re.search(r"\.(md|markdown|mdown|mkd)$", path, re.I):
                directory = path.rsplit("/", 1)[0] if "/" in path else ""
                raw_dir = "https://gitlab.com/%s/-/raw/%s/%s" % (repo, ref, directory + "/" if directory else "")
                blob_dir = "https://gitlab.com/%s/-/blob/%s/%s" % (repo, ref, directory + "/" if directory else "")
                return {
                    "kind": "gitlab", "host": "GitLab", "repo": repo, "ref": ref, "path": path,
                    "raw_url": "https://gitlab.com/%s/-/raw/%s/%s" % (repo, ref, path),
                    "blob_url": "https://gitlab.com/%s/-/blob/%s/%s" % (repo, ref, path),
                    "raw_dir": raw_dir, "blob_dir": blob_dir,
                    "source_url": url, "anchor": anchor,
                }

    if re.search(r"\.(md|markdown|mdown|mkd|mdx)$", parsed.path, re.I):
        base = url.split("#")[0]
        directory = base.rsplit("/", 1)[0] + "/" if "/" in base else base
        return {
            "kind": "direct", "host": host, "repo": "", "ref": "",
            "path": parsed.path.rsplit("/", 1)[-1],
            "raw_url": base, "blob_url": base,
            "raw_dir": directory, "blob_dir": directory,
            "source_url": url, "anchor": anchor,
        }
    return None


def load_markdown(source: dict, refresh: bool = False) -> str:
    """Fetch the Markdown with the same fallbacks the browser uses."""
    urls = [source["raw_url"]]
    if source.get("repo") and source.get("ref") and source.get("path"):
        urls.append(
            "https://cdn.jsdelivr.net/gh/%s@%s/%s"
            % (source["repo"], source["ref"], source["path"])
        )
    for candidate in urls:
        request = urllib.request.Request(
            candidate,
            headers={"User-Agent": "innioasis-site-generator", "Accept": "text/plain"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001
            print("  ! markdown fetch failed (%s): %s" % (candidate, error), file=sys.stderr)
    if source.get("repo") and source.get("path"):
        api = "https://api.github.com/repos/%s/contents/%s?ref=%s" % (
            source["repo"], source["path"], urllib.parse.quote(source.get("ref") or "")
        )
        payload = cached_json(api, refresh=refresh)
        if isinstance(payload, dict) and payload.get("content"):
            try:
                return base64.b64decode(payload["content"]).decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass
    return ""


def resolve_asset(href: str, ctx: dict | None) -> str:
    if not href or not ctx:
        return href
    if re.match(r"^(https?:|mailto:|tel:|data:|#)", href, re.I):
        return href
    if href.startswith("/") and ctx.get("repo") and ctx.get("ref"):
        return "https://raw.githubusercontent.com/%s/%s%s" % (ctx["repo"], ctx["ref"], href)
    base = ctx.get("raw_dir") or ""
    return urllib.parse.urljoin(base, href) if base else href


# Repo -> catalogue slug, filled in by build(), so a note that links to the
# project's own releases can point at our release notes page instead.
SLUG_BY_REPO: dict[str, str] = {}

ASSET_LINK_RE = re.compile(r"^https?://(?:www\.)?github\.com/[^/]+/[^/]+/releases/download/", re.I)
RELEASE_LINK_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/([^/]+/[^/]+)/releases(?:/tag/([^?#]+))?", re.I
)
COMPARE_LINK_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+/[^/]+)/compare/", re.I)


def parser_release_query(repo: str, tag: str = "", software: str = "") -> str:
    """Query for the release-notes parser: author, project and version."""
    repo = repo or ""
    author, _, project = repo.partition("/")
    params = {}
    if author:
        params["author"] = author
    if project:
        params["project"] = project
    if tag:
        params["version"] = tag
    if software:
        params["software"] = software
    return urllib.parse.urlencode(params)


def release_notes_href(repo: str, tag: str = "") -> str:
    """The release-notes parser page; static copies are sitemap-only."""
    slug = SLUG_BY_REPO.get((repo or "").lower(), "")
    query = parser_release_query(repo, tag, slug)
    return SITE + "/release_notes.html" + ("?" + query if query else "")


def resolve_link(href: str, ctx: dict | None) -> str:
    if not href:
        return "#"
    if re.match(r"^(mailto:|tel:|data:|#)", href, re.I):
        return href
    if re.match(r"^https?:", href, re.I):
        # A release's own files are never listed here, and a link to the
        # project's GitHub releases page becomes our release notes page.
        if ASSET_LINK_RE.match(href):
            return ""
        release = RELEASE_LINK_RE.match(href)
        if release:
            return release_notes_href(release.group(1), urllib.parse.unquote(release.group(2) or ""))
        # A "Full Changelog" compare link is the project's release notes by
        # another name: send it to our release history for that software.
        compare = COMPARE_LINK_RE.match(href)
        if compare:
            return release_notes_href(compare.group(1))
        nested = parse_source(href)
        if nested and nested["kind"] == "github":
            query = {"url": href}
            if nested.get("anchor"):
                query["anchor"] = nested["anchor"].lstrip("#")
            return SITE + "/post_install.html?" + urllib.parse.urlencode(query)
        return href
    if not ctx:
        return href
    if href.startswith("/") and ctx.get("repo") and ctx.get("ref"):
        return "https://github.com/%s/blob/%s%s" % (ctx["repo"], ctx["ref"], href)
    base = ctx.get("blob_dir") or ""
    return urllib.parse.urljoin(base, href) if base else href


TOKEN_RE = re.compile(r"\x00([A-Z])(\d+)\x00")


def inline_markdown(text: str, ctx: dict | None) -> str:
    if not text:
        return ""
    protected: list[str] = []

    def protect(markup: str) -> str:
        protected.append(markup)
        return "\x00I%d\x00" % (len(protected) - 1)

    text = re.sub(r"(`+)([\s\S]*?)\1", lambda m: protect("<code>%s</code>" % esc(m.group(2).strip())), text)
    text = re.sub(
        r"(?is)</?([a-zA-Z][a-zA-Z0-9-]*)((?:\s[^<>]*)?)>",
        lambda m: m.group(0) if m.group(1).lower() in ALLOWED_HTML else "",
        text,
    )
    text = esc(text)

    def image(match: re.Match) -> str:
        alt, src, title = match.group(1), match.group(2), match.group(3)
        resolved = resolve_asset(src, ctx)
        return '<img src="%s" alt="%s"%s loading="lazy" decoding="async">' % (
            esc(resolved), alt, ' title="%s"' % esc(title) if title else ""
        )

    def link(match: re.Match) -> str:
        label, href, title = match.group(1), match.group(2), match.group(3)
        resolved = resolve_link(href, ctx)
        if not resolved:
            return label
        external = resolved.startswith("http") and "innioasis.app" not in resolved
        return '<a href="%s"%s%s>%s</a>' % (
            esc(resolved),
            ' title="%s"' % esc(title) if title else "",
            ' target="_blank" rel="noopener noreferrer"' if external else "",
            label,
        )

    text = re.sub(r"!\[([^\]]*)\]\(\s*([^\s)]+)(?:\s+&quot;([^&]*)&quot;)?\s*\)", image, text)
    text = re.sub(r"\[([^\]]+)\]\(\s*([^\s)]+)(?:\s+&quot;([^&]*)&quot;)?\s*\)", link, text)
    def autolink(match: re.Match) -> str:
        target = resolve_link(match.group(2), ctx)
        if not target:
            return match.group(1) + match.group(2)
        external = target.startswith("http") and "innioasis.app" not in target
        return match.group(1) + '<a href="%s"%s>%s</a>' % (
            esc(target),
            ' target="_blank" rel="noopener noreferrer"' if external else "",
            match.group(2),
        )

    text = re.sub(r"(^|[\s(])(https?://[^\s<)\"]+)", autolink, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)", r"\1<em>\2</em>", text)
    text = re.sub(r"(^|[\s(])_([^_\n]+)_(?=[\s).,;:!?]|$)", r"\1<em>\2</em>", text)
    text = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", text)

    text = text.replace("\n", " ")

    def restore(match: re.Match) -> str:
        try:
            return protected[int(match.group(2))]
        except (IndexError, ValueError):
            return ""

    return TOKEN_RE.sub(lambda m: restore(m) if m.group(1) == "I" else "", text)


def split_row(line: str) -> list[str]:
    cells, current, escaped = [], "", False
    for char in line:
        if escaped:
            current += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append(current)
            current = ""
        else:
            current += char
    cells.append(current)
    stripped = line.strip()
    if cells and not cells[0].strip() and stripped.startswith("|"):
        cells = cells[1:]
    if cells and not cells[-1].strip() and stripped.endswith("|"):
        cells = cells[:-1]
    return [cell.strip() for cell in cells]


def is_delimiter_row(line: str) -> bool:
    if "|" not in line and "-" not in line:
        return False
    cells = split_row(line)
    return bool(cells) and all(re.match(r"^:?-{2,}:?$", cell.replace(" ", "")) for cell in cells)


BLOCK_START = re.compile(r"^\s{0,3}(#{1,6}\s|>|```|~~~|[-*+]\s|\d+[.)]\s|\|)")


def parse_list_block(lines: list[str], start: int, ctx: dict | None) -> tuple[str, int]:
    ordered = bool(re.match(r"^\s{0,3}\d+[.)]\s+", lines[start]))
    items: list[list[str]] = []
    index = start
    while index < len(lines):
        line = lines[index]
        match = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if not match:
            if items and line.strip() and re.match(r"^\s{2,}", line):
                items[-1].append(line[2:])
                index += 1
                continue
            if items and not line.strip():
                probe = index + 1
                while probe < len(lines) and not lines[probe].strip():
                    probe += 1
                if probe < len(lines) and re.match(r"^\s{0,3}([-*+]|\d+[.)])\s+", lines[probe]):
                    index = probe
                    continue
            break
        indent = len(match.group(1))
        item_ordered = bool(re.match(r"^\d+[.)]$", match.group(2)))
        if indent < 2 and items and item_ordered != ordered:
            break
        if indent >= 2 and items:
            items[-1].append(match.group(2) + " " + match.group(3))
            index += 1
            continue
        items.append([match.group(3)])
        index += 1

    tag = "ol" if ordered else "ul"
    parts = ["<%s>" % tag]
    for entry in items:
        head = entry[0] if entry else ""
        checkbox = ""
        task = re.match(r"^\[( |x|X)\]\s+(.*)$", head)
        if task:
            checkbox = '<input type="checkbox" disabled%s> ' % (" checked" if task.group(1).lower() == "x" else "")
            head = task.group(2)
        nested = entry[1:]
        nested_html = ""
        if nested and re.match(r"^([-*+]|\d+[.)])\s+", nested[0]):
            nested_html, _ = parse_list_block(nested, 0, ctx)
        elif nested:
            nested_html = "<p>%s</p>" % " ".join(inline_markdown(row.strip(), ctx) for row in nested)
        parts.append("<li>%s%s%s</li>" % (checkbox, inline_markdown(head, ctx), nested_html))
    parts.append("</%s>" % tag)
    return "".join(parts), index


def markdown_to_html(markdown: str, ctx: dict | None = None) -> str:
    text = DROP_BLOCKS.sub("", (markdown or "").replace("\r\n", "\n").replace("\r", "\n"))
    text = text.replace("\t", "    ").replace("\u00a0", " ")
    lines = text.split("\n")
    out: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        fence = re.match(r"^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)\s*$", line)
        if fence:
            marker, language = fence.group(1)[0], fence.group(2)
            code: list[str] = []
            index += 1
            while index < len(lines) and not re.match(r"^\s{0,3}%s{3,}\s*$" % re.escape(marker), lines[index]):
                code.append(lines[index])
                index += 1
            index += 1
            out.append(
                '<pre><code%s>%s</code></pre>'
                % (' class="language-%s"' % esc(language) if language else "", esc("\n".join(code)))
            )
            continue

        if re.match(r"^ {4}\S", line):
            block: list[str] = []
            while index < len(lines) and (re.match(r"^ {4}", lines[index]) or not lines[index].strip()):
                block.append(re.sub(r"^ {4}", "", lines[index]))
                index += 1
            while block and not block[-1].strip():
                block.pop()
            out.append("<pre><code>%s</code></pre>" % esc("\n".join(block)))
            continue

        if re.match(r"^\s{0,3}<[a-zA-Z!/]", line):
            block = []
            while index < len(lines) and lines[index].strip():
                block.append(lines[index])
                index += 1
            out.append(clean_html("\n".join(block), ctx))
            continue

        heading = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if heading:
            level = min(6, len(heading.group(1)))
            body = heading.group(2)
            anchor_id = re.sub(r"[^a-z0-9\s-]", "", body.lower()).strip().replace(" ", "-")
            out.append(
                "<h%d%s>%s</h%d>"
                % (level, ' id="%s"' % esc(anchor_id) if anchor_id else "", inline_markdown(body, ctx), level)
            )
            index += 1
            continue

        if index + 1 < len(lines) and re.match(r"^\s{0,3}(=+|-{2,})\s*$", lines[index + 1]) and line.strip():
            level = 1 if lines[index + 1].strip()[0] == "=" else 2
            out.append("<h%d>%s</h%d>" % (level, inline_markdown(line.strip(), ctx), level))
            index += 2
            continue

        if re.match(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$", line):
            out.append("<hr>")
            index += 1
            continue

        if "|" in line and index + 1 < len(lines) and is_delimiter_row(lines[index + 1]):
            header = split_row(line)
            alignment = []
            for cell in split_row(lines[index + 1]):
                compact = cell.replace(" ", "")
                if re.match(r"^:-+:$", compact):
                    alignment.append("center")
                elif re.match(r"^:-+$", compact):
                    alignment.append("left")
                elif re.match(r"^-+:$", compact):
                    alignment.append("right")
                else:
                    alignment.append("")
            index += 2
            rows = []
            while index < len(lines) and lines[index].strip() and "|" in lines[index]:
                rows.append(split_row(lines[index]))
                index += 1
            table = ["<table><thead><tr>"]
            for position, cell in enumerate(header):
                table.append(
                    '<th%s>%s</th>'
                    % (' style="text-align:%s"' % alignment[position] if position < len(alignment) and alignment[position] else "",
                       inline_markdown(cell, ctx))
                )
            table.append("</tr></thead><tbody>")
            for row in rows:
                table.append("<tr>")
                for position in range(len(header)):
                    cell = row[position] if position < len(row) else ""
                    table.append(
                        '<td%s>%s</td>'
                        % (' style="text-align:%s"' % alignment[position] if position < len(alignment) and alignment[position] else "",
                           inline_markdown(cell, ctx))
                    )
                table.append("</tr>")
            table.append("</tbody></table>")
            out.append("".join(table))
            continue

        if re.match(r"^\s{0,3}>", line):
            quoted: list[str] = []
            while index < len(lines) and (re.match(r"^\s{0,3}>", lines[index]) or (quoted and lines[index].strip())):
                quoted.append(re.sub(r"^\s{0,3}>\s?", "", lines[index]))
                index += 1
            out.append("<blockquote>%s</blockquote>" % markdown_to_html("\n".join(quoted), ctx))
            continue

        if re.match(r"^\s{0,3}([-*+]|\d+[.)])\s+", line):
            block_html, index = parse_list_block(lines, index, ctx)
            out.append(block_html)
            continue

        paragraph: list[str] = []
        while index < len(lines) and lines[index].strip():
            if paragraph and (BLOCK_START.match(lines[index]) or re.match(r"^\s{0,3}<[a-zA-Z!/]", lines[index])):
                break
            if paragraph and index + 1 < len(lines) and re.match(r"^\s{0,3}(=+|-{2,})\s*$", lines[index + 1]):
                break
            paragraph.append(lines[index])
            index += 1
        rendered = []
        for row in paragraph:
            hard_break = bool(re.search(r"(\s{2,}|\\)$", row))
            clean = re.sub(r"\\\s*$", "", row).rstrip()
            rendered.append(inline_markdown(clean, ctx) + ("<br>" if hard_break else ""))
        out.append("<p>%s</p>" % " ".join(rendered))

    return clean_html("\n".join(out), ctx)


# ---------------------------------------------------------------- templates

HEAD = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="author" content="Ryan Specter &amp; Innioasis Community">
  <meta name="creator" content="Ryan Specter &amp; Innioasis Community">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="{brand}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{canonical}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <link rel="icon" href="{up}y1_illustration.png">
  <link rel="stylesheet" href="{up}site-theme.css?v=20260803">
  <link rel="stylesheet" href="{up}lumen.css?v=20261105hero">
  <link rel="stylesheet" href="{up}site-pages.css?v=20260818">
  <link rel="stylesheet" href="{up}site-toolbar.css?v=20261105dockclose">
  <link rel="stylesheet" href="{up}docs-viewer.css?v=20261112cites">
  <script src="{up}site-init.js?v=20260803" defer></script>
</head>
<body class="site-themes-app">
<a class="lumen-skip-link" href="#main">Skip to content</a>
<div id="nav-root"></div>
"""

FOOT = """<div id="footer-root"></div><div id="support-toolbar-slot"></div>
<script src="{up}firmware-catalog.js?v=20260803" defer></script>
<script src="{up}docs-viewer.js?v=20261107silo" defer></script>
<script src="{up}portable-zip-links.js?v=20261103direct" defer></script>
<script src="{up}nav.js?v=20261103brand" defer></script>
<script src="{up}site-i18n.js?v=20260830" defer></script>
</body></html>
"""

# A project can publish a second post-install page for visitors who keep
# donation appeals on. Static pages link to the ordinary one and swap it in
# here, so the choice follows the visitor's own setting. Kept out of the
# templates above because it is JavaScript, not a format string.
FOOT_SCRIPT = """
<script>
document.addEventListener("DOMContentLoaded", function () {
  var D = window.InnioasisDocs;
  if (D && D.applyPostInstall2Links) D.applyPostInstall2Links(document);
});
</script>
</body></html>
"""


def page(head_args: dict, main: str, up: str) -> str:
    return (HEAD.format(brand=BRAND, up=up, **head_args) + main +
            FOOT.format(up=up).replace("</body></html>", FOOT_SCRIPT))


def release_version(release: dict) -> str:
    name = str(release.get("name") or "")
    match = re.search(r"(?:^|\s)(v?\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.]+)?)(?:\s|$)", name)
    if match:
        return match.group(1)
    return str(release.get("tag_name") or "")


def guide_href(item: dict, up: str) -> str:
    return "%sguide.html?model=%s&software=%s" % (
        up, urllib.parse.quote(item.get("model", "")), urllib.parse.quote(item.get("slug", ""))
    )


COG_SVG = '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" aria-hidden="true"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>'

UPDATER_ICON_RE = re.compile(r"^updater\.(png|webp|jpe?g|svg)$", re.I)

# The squircle the site falls back to when a project ships no icon: never a
# developer avatar.
GENERIC_RELEASE_ICON = (
    '<span class="lumen-release-icon lumen-release-icon--generic" aria-hidden="true">'
    + COG_SVG + "</span>"
)


def release_icon_html(item: dict, release: dict) -> str:
    """Release-shipped updater.* icon, then the manifest/catalog icon, then
    the generic cog squircle."""
    src = ""
    for asset in (release or {}).get("assets") or []:
        if UPDATER_ICON_RE.match(str(asset.get("name") or "").strip()):
            src = asset.get("browser_download_url") or ""
            if src:
                break
    if not src:
        src = (item or {}).get("icon") or ""
    if not src:
        return GENERIC_RELEASE_ICON
    return '<img class="lumen-release-icon" src="%s" alt="" loading="lazy">' % esc(src)


def source_citations(item: dict, tag: str = "") -> str:
    """Quiet numbered references to the project that publishes the firmware.

    [1] the project repository, [2] the exact release, [3] the catalogue pull
    requests that project has opened. They sit in the small print so readers
    who need them can follow them while the page stays about the firmware.
    """
    repo = str(item.get("repo") or "").strip()
    if "/" not in repo:
        return ""
    owner = repo.split("/")[0]
    repo_url = "https://github.com/" + repo
    parts = [
        '<p class="lumen-doc-sources">Published by the '
        '<a href="%s" rel="noopener">%s</a> project '
        '<a class="lumen-cite" href="%s" rel="noopener" title="Project repository">[1]</a>'
        % (esc(repo_url), esc(repo), esc(repo_url))
    ]
    if tag:
        parts.append(
            ' <a class="lumen-cite" href="%s/releases/tag/%s" rel="noopener" title="Release">[2]</a>'
            % (esc(repo_url), esc(urllib.parse.quote(str(tag), safe="")))
        )
    pulls = "https://github.com/y1-community/Innioasis-Updater/pulls?q=" + urllib.parse.quote(
        "is:pr author:%s" % owner, safe=""
    )
    parts.append(
        ' <a class="lumen-cite" href="%s" rel="noopener" title="Catalogue pull requests">[3]</a></p>'
        % esc(pulls)
    )
    return "".join(parts)


def release_page(item: dict, release: dict, siblings: list[dict], mirrored: list[dict]) -> str:
    up = "../../"
    name = software_label(item)
    model = item.get("model") or ""
    tag = str(release.get("tag_name") or release.get("name") or "")
    version = release_version(release)
    title = release.get("name") or ("%s %s" % (name, version)).strip()
    published = str(release.get("published_at") or "")[:10]
    canonical = "%s/release-notes/%s/%s.html" % (SITE, item["slug"], tag_slug(tag))
    description = one_line(
        (release.get("body") or "").strip() or
        ("Release notes, downloads and the Updater CE install guide for %s %s on the Innioasis %s." % (name, version, model))
    )
    meta_bits = ['<span class="lumen-release-pill">%s</span>' % esc(tag)]
    if model:
        meta_bits.append("<span>%s</span>" % esc(model))
    if published:
        meta_bits.append("<span>%s</span>" % esc(published))
    if release.get("prerelease"):
        meta_bits.append('<span class="lumen-release-pill lumen-release-pill--prerelease">Preview build</span>')
    if release.get("draft"):
        meta_bits.append('<span class="lumen-release-pill lumen-release-pill--prerelease">Draft</span>')

    repo_slug = str(item.get("repo") or "")
    if "/" in repo_slug:
        meta_bits.append(
            '<a class="lumen-release-repo" href="https://github.com/%s" rel="noopener">%s</a>'
            % (esc(repo_slug), esc(repo_slug))
        )

    icon_html = release_icon_html(item, release)

    body_ctx = {"repo": item.get("repo", ""), "ref": tag,
                "raw_dir": "https://raw.githubusercontent.com/%s/%s/" % (item.get("repo", ""), tag),
                "blob_dir": "https://github.com/%s/blob/%s/" % (item.get("repo", ""), tag)}
    notes = markdown_to_html(release.get("body") or "", body_ctx) if (release.get("body") or "").strip() else ""
    if not notes:
        notes = '<p class="lumen-doc-status">This release has no published notes yet. Install it with Updater CE, or from the firmware directory.</p>'

    related = []
    post_install = item.get("post_install") or item.get("post_install2") or ""
    post_install2 = item.get("post_install2") or ""
    source = parse_source(post_install)
    if source:
        related.append(
            '<li><a href="%spost_install.html?software=%s" data-post-install-link data-slug="%s"%s>'
            "<strong>Post-install setup</strong>"
            "<small>The steps to finish after this firmware is installed</small></a></li>"
            % (
                up, esc(item["slug"]), esc(item["slug"]),
                (' data-post-install2="%s"' % esc(post_install2)) if post_install2 else "",
            )
        )
    if item.get("guide") or item.get("seoPage"):
        related.append(
            '<li><a href="%s%s"><strong>Install guide</strong><small>Step-by-step install for %s</small></a></li>'
            % (up, esc(item.get("guide") or item.get("seoPage")), esc(name))
        )
    for sibling in siblings[:8]:
        if sibling.get("tag_name") == release.get("tag_name"):
            continue
        related.append(
            '<li><a href="%srelease_notes.html?%s"><strong>%s</strong><small>%s%s</small></a></li>'
            % (
                up, esc(parser_release_query(item.get("repo") or "", str(sibling.get("tag_name") or ""), item["slug"])),
                esc(sibling.get("name") or sibling.get("tag_name") or "Release"),
                esc(sibling.get("tag_name") or ""),
                (" · " + esc(str(sibling.get("published_at") or "")[:10])) if sibling.get("published_at") else "",
            )
        )

    main = [
        '<main id="main" class="lumen-guide lumen-doc-page lumen-release-page">',
        '<p class="lumen-doc-back"><a href="%sfirmware.html?model=%s&amp;software=%s">← Firmware Downloads</a></p>'
        % (up, esc(model), esc(item["slug"])),
        '<header class="lumen-doc-head">',
        '<div class="lumen-release-head">%s<div class="lumen-release-titles">' % icon_html,
        '<p class="lumen-kicker">Firmware release notes · %s%s</p>' % (esc(name), (" · " + esc(model)) if model else ""),
        "<h1>%s</h1></div></div>" % esc(title),
        '<p class="lumen-lead">%s</p>' % esc(item.get("description") or "What changed in this release, and how to install it."),
        '<div class="lumen-release-tag-row">%s</div>' % "".join(meta_bits),
        '<div class="lumen-doc-actions">',
        '<a class="lumen-button lumen-button--primary" href="%s">Get it in Updater CE</a>'
        % esc(guide_href(item, up)),
        '<a class="lumen-button" href="%sfirmware.html?model=%s&amp;software=%s">Firmware Downloads</a>'
        % (up, esc(model), esc(item["slug"])),
        "</div></header>",
        '<article class="lumen-doc-body lumen-release-body">%s</article>' % notes,
    ]
    if related:
        main.append(
            '<section class="lumen-doc-related"><h2>Also useful</h2>'
            '<ul class="lumen-doc-related-list">%s</ul></section>' % "".join(related)
        )
    main.append(
        '<p class="lumen-doc-footer-note">Notes as published by the %s project. '
        "Install it with Updater CE, or download it from the firmware directory.</p>"
        % esc(name)
    )
    main.append(source_citations(item, tag))
    main.append("</main>")

    return page({
        "title": "%s - %s" % (title, BRAND),
        "description": description,
        "canonical": canonical,
    }, "".join(main), up)


def software_index_page(item: dict, releases: list[dict]) -> str:
    up = "../"
    name = software_label(item)
    model = item.get("model") or ""
    canonical = "%s/release-notes/%s/index.html" % (SITE, item["slug"])
    cards = []
    for release in releases:
        tag = str(release.get("tag_name") or "")
        cards.append(
            '<article class="lumen-card"><small>%s%s</small>'
            '<h3><a href="../../release_notes.html?author=%s&amp;project=%s&amp;version=%s">%s</a></h3><p>%s</p></article>'
            % (
                esc(str(release.get("published_at") or "")[:10]),
                " · Preview" if release.get("prerelease") else "",
                esc(str(item.get("repo") or "").partition("/")[0]),
                esc(str(item.get("repo") or "").partition("/")[2]),
                esc(urllib.parse.quote(str(tag or ""), safe="")),
                esc(release.get("name") or tag or "Release"),
                esc(one_line(release.get("body") or "", 150) or "No notes published."),
            )
        )
    if not cards:
        cards.append('<p class="lumen-doc-status">No public releases yet.</p>')
    main = (
        '<main id="main" class="lumen-guide"><p class="lumen-doc-back">'
        '<a href="../../firmware.html?model=%s&amp;software=%s">← Firmware Downloads</a></p>'
        "<header><p class=\"lumen-kicker\">Release history · %s</p><h1>%s release notes</h1>"
        '<p class="lead">Every published release of %s for the %s, with downloads and the Updater CE install guide.</p>'
        '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%s">Get it in Updater CE</a>'
        '<a class="lumen-button" href="../index.html">All firmware</a></div></header>'
        '<section class="lumen-guide-section"><div class="lumen-grid">%s</div></section></main>'
        % (esc(model), esc(item["slug"]), esc(name), esc(name), esc(name), esc(model),
           esc(guide_href(item, "../../")), "".join(cards))
    )
    return page({
        "title": "%s release notes - %s" % (name, BRAND),
        "description": "Every published %s release for the Innioasis %s, with downloads and install guide." % (name, model),
        "canonical": canonical,
    }, main, up)


def master_index_page(software: list[dict], release_counts: dict[str, int], post_install_items: list[dict]) -> str:
    up = "../../"
    cards = []
    for item in software:
        count = release_counts.get(item["slug"], 0)
        cards.append(
            '<article class="lumen-card"><small>%s%s</small>'
            '<h3><a href="../release_notes.html?%s">%s</a></h3><p>%s</p>'
            '<div class="lumen-actions"><a class="lumen-button" href="../release_notes.html?%s">%s release%s</a></div></article>'
            % (
                esc(item.get("model", "")),
                " · " + esc(item.get("name", "")) if item.get("name") else "",
                esc(parser_release_query(item.get("repo") or "", "", item["slug"])), esc(software_label(item)),
                esc(item.get("description") or ""),
                esc(parser_release_query(item.get("repo") or "", "", item["slug"])), count, "" if count == 1 else "s",
            )
        )
    post_cards = []
    for item, source in post_install_items:
        post_cards.append(
            '<article class="lumen-card"><small>%s</small><h3><a href="../post_install.html?software=%s">%s post-install</a></h3>'
            '<p>Setup steps published by the project, shown here in the site style.</p></article>'
            % (esc(item.get("model", "")), esc(item["slug"]), esc(software_label(item)))
        )

    main = (
        '<main id="main" class="lumen-guide"><header><p class="lumen-kicker">Firmware release notes</p>'
        "<h1>Every firmware release, readable here</h1>"
        '<p class="lead">Release notes for every published build in the Innioasis Updater catalogue, '
        "with portable ZIP downloads and a one-click install guide. These pages mirror what Updater CE shows.</p>"
        '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%sfirmware.html">Firmware Downloads</a>'
        '</div></header>'
        '<section class="lumen-guide-section"><div class="lumen-grid">%s</div></section>'
        % (up, "".join(cards) or '<p class="lumen-doc-status">No software is listed yet.</p>')
    )
    if post_cards:
        main += (
            '<section class="lumen-guide-section"><h2>Post-install setup</h2><div class="lumen-grid">%s</div></section>'
            % "".join(post_cards)
        )
    main += "</main>"
    return page({
        "title": "Firmware release notes archive - %s" % BRAND,
        "description": "Release notes, downloads and install guides for every firmware release in the Innioasis Updater catalogue.",
        "canonical": SITE + "/release-notes/index.html",
    }, main, up)


def post_install_page(item: dict, source: dict, markdown: str, release_tags: list[str]) -> str:
    up = "../"
    name = software_label(item)
    model = item.get("model") or ""
    title = "Post-install setup for %s" % name
    heading = re.search(r"^\s{0,3}#\s+(.+)$", markdown, re.M)
    if heading:
        title = re.sub(r"[`*_]", "", heading.group(1)).strip()
    canonical = "%s/post-install/%s.html" % (SITE, item["slug"])
    body = markdown_to_html(markdown, source)
    description = one_line(markdown, 170) or ("Post-install setup instructions for %s on the Innioasis %s." % (name, model))
    latest = release_tags[0] if release_tags else ""

    main = (
        '<main id="main" class="lumen-guide lumen-doc-page">'
        '<p class="lumen-doc-back"><a href="%sfirmware.html?model=%s&amp;software=%s">← Firmware Downloads</a></p>'
        '<header class="lumen-doc-head"><p class="lumen-kicker">Post-install setup · %s%s</p>'
        "<h1>%s</h1>"
        '<p class="lumen-lead">%s</p>'
        '<p class="lumen-doc-source">Instructions published by the project, shown here word for word.</p>'
        '<div class="lumen-doc-actions">'
        '<a class="lumen-button lumen-button--primary" href="%sfirmware.html?model=%s&amp;software=%s">Firmware Downloads →</a>'
        '<a class="lumen-button" href="%s">Install guide</a>'
        "</div></header>"
        '<article class="lumen-doc-body">%s</article>'
        '<p class="lumen-doc-footer-note">These are %s\'s own instructions, shown here word for word.</p>%s</main>'
        % (
            up, esc(model), esc(item["slug"]), esc(name), (" · " + esc(model)) if model else "",
            esc(title), esc(item.get("description") or "The steps the project asks you to finish after the firmware is installed."),
            up, esc(model), esc(item["slug"]),
            esc(guide_href(item, up)), body, esc(name), source_citations(item, latest),
        )
    )
    return page({
        "title": "%s - %s" % (title, BRAND),
        "description": description,
        "canonical": canonical,
    }, main, up)


def post_install_index_page(entries: list[dict]) -> str:
    up = "../../"
    cards = "".join(entries) or '<p class="lumen-doc-status">No imported post-install guides yet.</p>'
    main = (
        '<main id="main" class="lumen-guide"><header><p class="lumen-kicker">Post-install guides</p>'
        "<h1>After the firmware is installed</h1>"
        '<p class="lead">Setup steps published by each project, imported here and shown in the site style. '
        "Finish these before you rely on the player.</p>"
        '<div class="lumen-actions"><a class="lumen-button lumen-button--primary" href="%sfirmware.html">Firmware Downloads</a>'
        '</div></header>'
        '<section class="lumen-guide-section"><div class="lumen-grid">%s</div></section></main>'
        % (up, cards)
    )
    return page({
        "title": "Post-install guides - %s" % BRAND,
        "description": "Post-install setup guides for community firmware on Innioasis Y1 and Y2 players.",
        "canonical": SITE + "/post-install/index.html",
    }, main, up)


def update_sitemap(urls: list[str]) -> None:
    path = ROOT / "sitemap.xml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    added = 0
    for loc in urls:
        if not loc or loc in text:
            continue
        text = text.replace(
            "</urlset>",
            "  <url><loc>%s</loc><changefreq>weekly</changefreq></url>\n</urlset>" % esc(loc),
        )
        added += 1
    if added:
        path.write_text(text, encoding="utf-8")
    print("sitemap: %d new URLs" % added)


# ---------------------------------------------------------------- build


def build(refresh: bool = False) -> None:
    catalog = load_catalog()
    manifest = load_manifest()
    software = build_software(catalog, manifest)
    SLUG_BY_REPO.clear()
    for entry in software:
        if entry.get("repo"):
            SLUG_BY_REPO[entry["repo"].lower()] = entry["slug"]
    mirror = mirror_index(refresh=refresh)
    print("software entries: %d" % len(software))

    release_root = ROOT / "release-notes"
    post_root = ROOT / "post-install"
    release_root.mkdir(exist_ok=True)
    post_root.mkdir(exist_ok=True)

    sitemap_urls: list[str] = [SITE + "/release-notes/index.html", SITE + "/post-install/index.html"]
    release_counts: dict[str, int] = {}
    post_install_items: list[tuple[dict, dict]] = []
    post_install_cards: list[str] = []

    for item in software:
        repo = item.get("repo") or ""
        slug = item["slug"]
        releases = [entry for entry in fetch_releases(repo, refresh=refresh) if not entry.get("draft")]
        releases.sort(key=lambda entry: str(entry.get("published_at") or ""), reverse=True)
        release_counts[slug] = len(releases)
        if releases:
            folder = release_root / slug
            folder.mkdir(exist_ok=True)
            for release in releases:
                tag = str(release.get("tag_name") or "")
                if not tag:
                    continue
                repo_slug = repo.replace("/", "-").lower()
                mirrored = mirror.get((repo_slug, tag.lower())) or mirror.get((repo_slug, tag_slug(tag)))
                (folder / (tag_slug(tag) + ".html")).write_text(
                    release_page(item, release, releases, mirrored or []), encoding="utf-8"
                )
                sitemap_urls.append("%s/release-notes/%s/%s.html" % (SITE, slug, tag_slug(tag)))
            (folder / "index.html").write_text(software_index_page(item, releases), encoding="utf-8")
            sitemap_urls.append("%s/release-notes/%s/index.html" % (SITE, slug))
            print("  %-32s %3d releases" % (slug, len(releases)))
        else:
            print("  %-32s   0 releases" % slug)

        post_install = item.get("post_install") or item.get("post_install2") or ""
        source = parse_source(post_install)
        if not source:
            continue
        markdown = load_markdown(source, refresh=refresh)
        if not markdown.strip():
            print("  ! post-install could not be fetched for %s" % slug)
            continue
        tags = [str(entry.get("tag_name") or "") for entry in releases if entry.get("tag_name")]
        (post_root / (slug + ".html")).write_text(
            post_install_page(item, source, markdown, tags), encoding="utf-8"
        )
        sitemap_urls.append("%s/post-install/%s.html" % (SITE, slug))
        post_install_items.append((item, source))
        post_install_cards.append(
            '<article class="lumen-card"><small>%s</small><h3><a href="../post_install.html?software=%s">%s post-install</a></h3>'
            '<p>%s</p></article>'
            % (esc(item.get("model", "")), esc(slug), esc(software_label(item)),
               esc(one_line(markdown, 150) or "Setup steps published by the project."))
        )

    (release_root / "index.html").write_text(
        master_index_page(software, release_counts, post_install_items), encoding="utf-8"
    )
    (post_root / "index.html").write_text(post_install_index_page(post_install_cards), encoding="utf-8")
    update_sitemap(sitemap_urls)
    print("done: %d release pages, %d post-install pages" % (sum(release_counts.values()), len(post_install_items)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate static release-notes and post-install pages.")
    parser.add_argument("--refresh", action="store_true", help="ignore the on-disk GitHub cache")
    args = parser.parse_args()
    build(refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
