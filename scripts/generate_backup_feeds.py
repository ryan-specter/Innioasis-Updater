#!/usr/bin/env python3
"""Generate 1:1 backup feeds (JSON, Atom XML, and catalog JS) for all firmware repositories.

This script builds complete backup stores of the GitHub Releases & Repository API data
needed by innioasis.app, Innioasis Updater (updater.py), and Updater CE (updater-ce-neo):

  - feeds/releases.json                  1:1 master backup store (all repos, stats, icons, releases, assets, notes)
  - feeds/releases.xml                   Combined XML backup store of all repos and releases
  - feeds/firmware-releases.json         App feed (schema 2): manifest packages, per-repo releases,
                                         portable mirror packages and Updater CE app updates
  - feeds/firmware-feed.xml              The same app feed as Atom with the innioasis firmware namespace
  - feeds/index.json                     Feed discovery: every endpoint and per-repo file
  - feeds/<owner>/<repo>/releases.json   1:1 GitHub API releases array per repository (lowercase path)
  - feeds/<owner>/<repo>/releases.atom   Atom 1.0 feed with <link rel="enclosure"> assets, icons, and raw notes
  - feeds/<owner>/<repo>/repo.json       1:1 GitHub API repository object (name, stars, license, branch)
  - .cache/releases/<owner>_<repo>.json  Pre-populated release cache for Innioasis-Updater (updater.py)
  - firmware-catalog.js                  Updates INNIOASIS_HARDCODED_RELEASES, INNIOASIS_RELEASE_ICONS, INNIOASIS_REPO_STATS

Every mirror named by ``portable_zips`` in ``slidia_manifest.xml`` is collected too, so the
app can download a portable package (or substitute a mirror copy of the release) when GitHub
or the publishing repository cannot be reached.

Usage:
    python scripts/generate_backup_feeds.py [--refresh]
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import generate_doc_pages as gdp  # noqa: E402

ROOT = gdp.ROOT
SITE = gdp.SITE
FEEDS_DIR = ROOT / "feeds"
RELEASES_CACHE_DIR = ROOT / ".cache" / "releases"
DOC_CACHE_DIR = ROOT / ".cache" / "doc-pages"

EXTRA_REPOS = [
    "y1-community/updater-ce-neo",
    "y1-community/Innioasis-Updater",
]

APP_UPDATE_REPOS = {repo.lower() for repo in EXTRA_REPOS}
FEED_JSON_NAME = "firmware-releases.json"
FEED_XML_NAME = "firmware-feed.xml"
SITE = "https://innioasis.app"
MIRROR_INDEX_URL = "https://raw.githubusercontent.com/{repo}/{branch}/index.json"
USABLE_ROM_RE = re.compile(r"\.(zip|7z|rar|tar\.gz|tgz|img|bin|gz|tar)$", re.I)

ICON_ASSET_RE = re.compile(r"^updater\.(png|webp|jpe?g|svg)$", re.I)
DARK_ICON_ASSET_RE = re.compile(r"^updater_dark\.(png|webp|jpe?g|svg)$", re.I)


def load_tokens() -> list[str]:
    tokens: list[str] = []
    for env_key in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = (os.environ.get(env_key) or "").strip()
        if val and val not in tokens:
            tokens.append(val)
    cfg = ROOT / "config.ini"
    if cfg.exists():
        try:
            for raw_line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw_line.strip()
                if not re.match(r"^(key_\d+|token)\s*=", line):
                    continue
                val = line.split("=", 1)[1].strip().strip("\"'")
                if len(val) > 10:
                    if not re.match(r"^(github_pat_|ghp_|gho_|ghu_|ghs_)", val):
                        val = "github_pat_" + val
                    if val not in tokens:
                        tokens.append(val)
        except OSError:
            pass
    return tokens


TOKENS = load_tokens()
DEAD_TOKENS: set[str] = set()


def github_get_json(url: str, refresh: bool = False):
    DOC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    cache_path = DOC_CACHE_DIR / f"{key}.json"
    if not refresh and cache_path.exists() and (time.time() - cache_path.stat().st_mtime < 900):
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached not in (None, {}, []):
                return cached
        except (OSError, json.JSONDecodeError):
            pass

    base_headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "innioasis-backup-feeds-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    attempts = [t for t in TOKENS if t not in DEAD_TOKENS] + [""]
    payload = None
    for token in attempts:
        headers = dict(base_headers)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace"))
                break
        except urllib.error.HTTPError as err:
            if err.code in (401, 403, 429) and token:
                DEAD_TOKENS.add(token)
                continue
            if err.code == 404:
                payload = [] if "/releases?" in url else {}
                break
            print(f"  ! HTTP {err.code} for {url}", file=sys.stderr)
            payload = [] if "/releases?" in url else {}
            break
        except Exception as err:  # noqa: BLE001
            if token:
                continue
            print(f"  ! {err} for {url}", file=sys.stderr)
            payload = [] if "/releases?" in url else {}
            break

    if payload not in (None, {}, []):
        try:
            cache_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass
    elif cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return payload


def fetch_all_repo_releases(repo: str, refresh: bool = False) -> list[dict]:
    collected: list[dict] = []
    seen_tags: set[str] = set()
    for page in range(1, 4):
        url = f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}"
        batch = github_get_json(url, refresh=refresh)
        if not isinstance(batch, list) or not batch:
            break
        for rel in batch:
            if not isinstance(rel, dict) or rel.get("draft"):
                continue
            tag = str(rel.get("tag_name") or "").strip()
            if tag and tag in seen_tags:
                continue
            if tag:
                seen_tags.add(tag)
            collected.append(rel)
        if len(batch) < 100:
            break

    # Also check /releases/latest in case GitHub omitted a republished release from pagination
    latest = github_get_json(f"https://api.github.com/repos/{repo}/releases/latest", refresh=refresh)
    if isinstance(latest, dict) and latest.get("tag_name") and not latest.get("draft"):
        ltag = str(latest.get("tag_name") or "").strip()
        if ltag and ltag not in seen_tags:
            collected.insert(0, latest)
            seen_tags.add(ltag)

    return collected


def fetch_repo_info(repo: str, refresh: bool = False) -> dict:
    data = github_get_json(f"https://api.github.com/repos/{repo}", refresh=refresh)
    if not isinstance(data, dict):
        return {}
    license_obj = data.get("license") if isinstance(data.get("license"), dict) else {}
    return {
        "full_name": data.get("full_name") or repo,
        "description": data.get("description") or "",
        "html_url": data.get("html_url") or f"https://github.com/{repo}",
        "default_branch": data.get("default_branch") or "main",
        "stargazers_count": int(data.get("stargazers_count") or 0),
        "forks_count": int(data.get("forks_count") or 0),
        "open_issues_count": int(data.get("open_issues_count") or 0),
        "updated_at": data.get("updated_at") or "",
        "pushed_at": data.get("pushed_at") or "",
        "license": license_obj.get("spdx_id") or license_obj.get("name") or "",
    }


def extract_release_icons(assets: list[dict], default_icon: str = "", default_dark_icon: str = "") -> tuple[str, str]:
    icon_url = ""
    dark_url = ""
    for asset in assets or []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name") or "").strip()
        dl = str(asset.get("browser_download_url") or "").strip()
        if not name or not dl:
            continue
        if not icon_url and ICON_ASSET_RE.match(name):
            icon_url = dl
        elif not dark_url and DARK_ICON_ASSET_RE.match(name):
            dark_url = dl
    return icon_url or default_icon, dark_url or default_dark_icon


def normalize_asset(asset: dict) -> dict:
    return {
        "id": asset.get("id") or 0,
        "name": str(asset.get("name") or ""),
        "browser_download_url": str(asset.get("browser_download_url") or ""),
        "size": int(asset.get("size") or 0),
        "download_count": int(asset.get("download_count") or 0),
        "content_type": str(asset.get("content_type") or "application/octet-stream"),
        "created_at": str(asset.get("created_at") or ""),
        "updated_at": str(asset.get("updated_at") or ""),
        "url": str(asset.get("url") or ""),
    }


def normalize_release(rel: dict, repo: str, default_icon: str = "", default_dark_icon: str = "") -> dict:
    raw_assets = [a for a in (rel.get("assets") or []) if isinstance(a, dict)]
    assets = [normalize_asset(a) for a in raw_assets if a.get("name") and a.get("browser_download_url")]
    icon_url, icon_dark_url = extract_release_icons(assets, default_icon, default_dark_icon)
    tag = str(rel.get("tag_name") or "")
    return {
        "id": rel.get("id") or 0,
        "tag_name": tag,
        "name": str(rel.get("name") or tag),
        "body": str(rel.get("body") or ""),
        "draft": bool(rel.get("draft", False)),
        "prerelease": bool(rel.get("prerelease", False)),
        "created_at": str(rel.get("created_at") or ""),
        "published_at": str(rel.get("published_at") or rel.get("created_at") or ""),
        "html_url": str(rel.get("html_url") or f"https://github.com/{repo}/releases/tag/{urllib.parse.quote(tag)}"),
        "icon_url": icon_url,
        "icon_dark_url": icon_dark_url,
        "assets": assets,
    }


# --- Helpers for updater.py .cache/releases/<owner>_<repo>.json compatibility ---

def _classify_variant_model(asset_name: str, tag_name: str = "", repo: str = "") -> str:
    lower_name = (asset_name or "").lower()
    lower_tag = (tag_name or "").lower()
    lower_repo = (repo or "").lower()
    if "y2" in lower_name or "6582" in lower_name or "eastaeon" in lower_name:
        return "Y2"
    if "y2" in lower_tag or "6582" in lower_tag or "eastaeon" in lower_tag:
        if "y1" not in lower_tag:
            return "Y2"
    if "y2" in lower_repo.split("/")[-1]:
        return "Y2"
    return "dual"


def _extract_rom_variants(assets: list[dict], tag_name: str, repo: str) -> list[dict]:
    variants: list[dict] = []
    tag_lower = (tag_name or "").lower()
    for asset in assets or []:
        name = str(asset.get("name") or "")
        lower = name.lower()
        if not fnmatch.fnmatch(lower, "rom*.zip") and lower not in ("system.zip", "update.zip") and not lower.endswith(".zip"):
            continue
        if not (fnmatch.fnmatch(lower, "rom*.zip") or lower in ("system.zip", "update.zip") or "y2linux" in lower):
            continue
        is_type_b = "_type_b" in lower or "type-b" in lower or " type b" in lower or "type-b" in tag_lower
        hw_type = "B" if is_type_b else "A"
        if "_360p" in lower:
            resolution = "360p"
        elif "_240p" in lower:
            resolution = "240p"
        else:
            resolution = "native"
        variants.append({
            "asset": asset,
            "type": hw_type,
            "resolution": resolution,
            "model": _classify_variant_model(name, tag_name, repo),
        })
    return variants


def build_legacy_cache_entries(repo: str, releases: list[dict]) -> list[dict]:
    entries: list[dict] = []
    for rel in releases:
        tag_name = str(rel.get("tag_name") or "")
        is_prerelease = bool(rel.get("prerelease", False))
        if "stable" in tag_name.lower():
            is_prerelease = False
        assets = rel.get("assets") or []
        rom_variants = _extract_rom_variants(assets, tag_name, repo)
        zip_asset = rom_variants[0]["asset"] if rom_variants else None
        if not zip_asset:
            for a in assets:
                if str(a.get("name") or "").lower().endswith(".zip"):
                    zip_asset = a
                    break
        if not zip_asset:
            continue
        entries.append({
            "tag_name": tag_name,
            "name": str(rel.get("name") or ""),
            "body": str(rel.get("body") or ""),
            "published_at": str(rel.get("published_at") or ""),
            "download_url": str(zip_asset.get("browser_download_url") or ""),
            "asset_name": str(zip_asset.get("name") or ""),
            "asset_size": int(zip_asset.get("size") or 0),
            "assets": assets,
            "rom_variants": rom_variants,
            "prerelease": is_prerelease,
            "icon_url": str(rel.get("icon_url") or ""),
            "icon_dark_url": str(rel.get("icon_dark_url") or ""),
            "source_repo": repo,
        })
    return entries


def build_atom_feed(repo: str, repo_info: dict, releases: list[dict], generated_at: str) -> str:
    updated = releases[0].get("published_at") if releases else generated_at
    if not updated:
        updated = generated_at
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:innioasis="https://innioasis.app/ns/feeds/1.0">',
        f"  <id>https://innioasis.app/feeds/{html.escape(repo.lower())}/releases.atom</id>",
        f"  <title>Release notes from {html.escape(repo)}</title>",
        f'  <link rel="alternate" type="text/html" href="https://innioasis.app/firmware.html"/>',
        f'  <link rel="self" type="application/atom+xml" href="https://innioasis.app/feeds/{html.escape(repo.lower())}/releases.atom"/>',
        f"  <updated>{html.escape(updated)}</updated>",
    ]
    for rel in releases:
        tag = str(rel.get("tag_name") or "")
        title = str(rel.get("name") or tag)
        pub = str(rel.get("published_at") or updated)
        body = str(rel.get("body") or "")
        html_url = str(rel.get("html_url") or f"https://github.com/{repo}/releases/tag/{urllib.parse.quote(tag)}")
        prerelease = "true" if rel.get("prerelease") else "false"
        icon_url = str(rel.get("icon_url") or "")
        icon_dark_url = str(rel.get("icon_dark_url") or "")
        lines.extend([
            "  <entry>",
            f"    <id>tag:innioasis.app,2026:{html.escape(repo)}/{html.escape(tag)}</id>",
            f"    <updated>{html.escape(pub)}</updated>",
            f"    <published>{html.escape(pub)}</published>",
            f"    <title>{html.escape(title)}</title>",
            f'    <link rel="alternate" type="text/html" href="{html.escape(html_url, quote=True)}"/>',
            f"    <innioasis:tag_name>{html.escape(tag)}</innioasis:tag_name>",
            f"    <innioasis:prerelease>{prerelease}</innioasis:prerelease>",
        ])
        if icon_url:
            lines.append(f"    <innioasis:icon_url>{html.escape(icon_url)}</innioasis:icon_url>")
        if icon_dark_url:
            lines.append(f"    <innioasis:icon_dark_url>{html.escape(icon_dark_url)}</innioasis:icon_dark_url>")
        for asset in rel.get("assets") or []:
            aname = html.escape(str(asset.get("name") or ""), quote=True)
            aurl = html.escape(str(asset.get("browser_download_url") or ""), quote=True)
            asize = int(asset.get("size") or 0)
            actype = html.escape(str(asset.get("content_type") or "application/octet-stream"), quote=True)
            adlcount = int(asset.get("download_count") or 0)
            aid = int(asset.get("id") or 0)
            lines.append(
                f'    <link rel="enclosure" href="{aurl}" title="{aname}" '
                f'length="{asize}" type="{actype}" '
                f'innioasis:download_count="{adlcount}" innioasis:asset_id="{aid}"/>'
            )
        lines.append(f'    <content type="text">{html.escape(body)}</content>')
        lines.append("  </entry>")
    lines.append("</feed>\n")
    return "\n".join(lines)


def build_combined_xml(repos_payload: dict[str, dict], generated_at: str) -> str:
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<releases_backup generated_at="{html.escape(generated_at, quote=True)}">',
    ]
    for repo_key, info in repos_payload.items():
        stats = info.get("stats") or {}
        rinfo = info.get("repo_info") or {}
        lines.append(
            f'  <repository name="{html.escape(repo_key, quote=True)}" '
            f'downloads="{int(stats.get("downloads") or 0)}" '
            f'release_count="{int(stats.get("release_count") or 0)}" '
            f'stars="{int(rinfo.get("stargazers_count") or 0)}" '
            f'icon="{html.escape(str(info.get("icon") or ""), quote=True)}" '
            f'icon_dark="{html.escape(str(info.get("icon_dark") or ""), quote=True)}">'
        )
        for rel in info.get("releases") or []:
            lines.append(
                f'    <release id="{int(rel.get("id") or 0)}" '
                f'tag_name="{html.escape(str(rel.get("tag_name") or ""), quote=True)}" '
                f'name="{html.escape(str(rel.get("name") or ""), quote=True)}" '
                f'published_at="{html.escape(str(rel.get("published_at") or ""), quote=True)}" '
                f'prerelease="{"true" if rel.get("prerelease") else "false"}" '
                f'html_url="{html.escape(str(rel.get("html_url") or ""), quote=True)}" '
                f'icon_url="{html.escape(str(rel.get("icon_url") or ""), quote=True)}" '
                f'icon_dark_url="{html.escape(str(rel.get("icon_dark_url") or ""), quote=True)}">'
            )
            lines.append(f'      <body>{html.escape(str(rel.get("body") or ""))}</body>')
            lines.append("      <assets>")
            for asset in rel.get("assets") or []:
                lines.append(
                    f'        <asset id="{int(asset.get("id") or 0)}" '
                    f'name="{html.escape(str(asset.get("name") or ""), quote=True)}" '
                    f'size="{int(asset.get("size") or 0)}" '
                    f'download_count="{int(asset.get("download_count") or 0)}" '
                    f'content_type="{html.escape(str(asset.get("content_type") or ""), quote=True)}" '
                    f'browser_download_url="{html.escape(str(asset.get("browser_download_url") or ""), quote=True)}"/>'
                )
            lines.append("      </assets>")
            lines.append("    </release>")
        lines.append("  </repository>")
    lines.append("</releases_backup>\n")
    return "\n".join(lines)


# --- App feed (schema 2) -------------------------------------------


def load_manifest_packages() -> list[dict]:
    """Every package attribute in ``slidia_manifest.xml``, verbatim.

    The app parses the same file, so the feed carries each attribute it can
    configure: ``repo``, ``device``, ``portable_zips``, ``derivative``,
    ``info_repo``, ``apk_repo``, ``post_install``, ``do_not_keep_data`` and the
    rest. The placeholder entry that tells an old app to update is skipped.
    """
    path = ROOT / "slidia_manifest.xml"
    if not path.exists():
        return []
    packages: list[dict] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as err:
        print(f"  ! slidia_manifest.xml: {err}", file=sys.stderr)
        return []
    for node in root.findall("package"):
        data = {key: (value or "").strip() for key, value in node.attrib.items()}
        name = data.get("name") or ""
        if not name or re.search(r"please update", name, re.I):
            continue
        data["device"] = (data.get("device") or "").upper()
        packages.append(data)
    return packages


def portable_mirror_map(packages: list[dict]) -> dict[str, list[str]]:
    """Source repository (lowercase) -> the mirrors its manifest entry names."""
    mapping: dict[str, list[str]] = {}
    for pkg in packages:
        source = str(pkg.get("repo") or "").strip().lower()
        if not source:
            continue
        for mirror in re.split(r"[\s,]+", str(pkg.get("portable_zips") or "")):
            mirror = mirror.strip().strip("/")
            if "/" not in mirror:
                continue
            if mirror.lower() not in mapping.setdefault(source, []):
                mapping[source].append(mirror)
    return mapping


def fetch_mirror_index(mirror_repo: str, refresh: bool = False) -> dict:
    """A portable packager's ``index.json`` (``main``, then ``master``)."""
    DOC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    branch = "main"
    url = MIRROR_INDEX_URL.format(repo=mirror_repo, branch=branch)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    cache_path = DOC_CACHE_DIR / f"{key}.index.json"
    if not refresh and cache_path.exists() and (time.time() - cache_path.stat().st_mtime < 900):
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached, dict) and cached:
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    for branch in ("main", "master"):
        url = MIRROR_INDEX_URL.format(repo=mirror_repo, branch=branch)
        req = urllib.request.Request(url, headers={"User-Agent": "innioasis-backup-feeds-generator"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8", "replace"))
            if isinstance(payload, dict) and payload:
                cache_path.write_text(json.dumps(payload), encoding="utf-8")
                return payload
        except Exception:  # noqa: BLE001 - a missing mirror index is not fatal
            continue
    return {}


def build_mirror_payload(
    mirror_repo: str,
    source_repos: list[str],
    index: dict,
    releases: list[dict],
    generated_at: str,
) -> dict:
    """One mirror's portable packages, in both shapes the app consumes.

    ``releases`` is the packager's own index (dict keyed by tag, packages keyed
    by platform: what ``src/portable.py`` resolves). App-side,
    ``feed_fallback._build_raw_releases_from_mirror_dict`` synthesizes the
    GitHub-shaped listing from this same dictionary, so the feed does not carry
    a second copy of every mirror release.
    """
    index_by_tag: dict[str, dict] = {}
    for entry in (index.get("releases") or []) if isinstance(index, dict) else []:
        tag = str(entry.get("tag") or "").strip()
        if tag:
            index_by_tag[tag] = entry

    releases_map: dict[str, dict] = {}
    for rel in releases:
        tag = str(rel.get("tag_name") or "").strip()
        if not tag:
            continue
        idx = index_by_tag.get(tag) or {}
        live_assets = {str(a.get("name") or ""): a for a in rel.get("assets") or []}
        by_source: dict[str, dict] = {}

        def source_entry(name: str) -> dict:
            return by_source.setdefault(name, {
                "original_url": "", "original_size": 0,
                "mirror_original_url": "", "packages": {},
            })

        for ia in idx.get("assets") or []:
            name = str(ia.get("name") or "").strip()
            if not name:
                continue
            live = live_assets.get(name) or {}
            url = str(live.get("browser_download_url") or ia.get("url") or "")
            if not url:
                url = "https://github.com/%s/releases/download/%s/%s" % (
                    mirror_repo, urllib.parse.quote(tag), urllib.parse.quote(name))
            platform = str(ia.get("platform") or "").strip()
            source_asset = str(ia.get("source_asset") or "").strip() or name
            size = int(live.get("size") or ia.get("size") or 0)
            entry = source_entry(source_asset)
            if platform:
                entry["packages"][platform] = {
                    "name": name, "url": url, "size": size,
                    "sha256": str(ia.get("sha256") or ia.get("checksum") or ""),
                }
            else:
                entry["mirror_original_url"] = url
                entry["original_size"] = size

        # Files the mirror carries that its index does not describe (a copy of
        # the original package, or a release asset mirrored verbatim).
        covered = {str(entry.get("name") or "") for entry in
                   [p for e in by_source.values() for p in e["packages"].values()]}
        for name, live in live_assets.items():
            if not name or name in covered or not USABLE_ROM_RE.search(name):
                continue
            if name in by_source and by_source[name].get("mirror_original_url"):
                continue
            url = str(live.get("browser_download_url") or "")
            if not url:
                continue
            entry = source_entry(name)
            entry["mirror_original_url"] = url
            entry["original_size"] = int(live.get("size") or 0)

        releases_map[tag] = {
            "original_tag": str(idx.get("tag") or tag),
            "mirror_tag": tag,
            "release_name": str(idx.get("title") or rel.get("name") or tag),
            "published_at": str(idx.get("published_at") or rel.get("published_at") or ""),
            "assets": by_source,
        }

    return {
        "version": 1,
        "schema": int(index.get("schema") or 1) if isinstance(index, dict) else 1,
        "source_repo": str((index.get("source_repo") if isinstance(index, dict) else "")
                           or (source_repos[0] if source_repos else "")),
        "source_repos": source_repos,
        "mirror_repo": mirror_repo,
        "updated_at": str((index.get("generated_at") if isinstance(index, dict) else "")
                          or generated_at),
        "platforms": list(index.get("platforms") or []) if isinstance(index, dict) else [],
        "releases": releases_map,
    }


def build_firmware_feed_json(
    repos_payload: dict[str, dict],
    packages: list[dict],
    mirrors: dict[str, dict],
    generated_at: str,
) -> dict:
    repos = {repo: list(info.get("releases") or []) for repo, info in repos_payload.items()}
    repo_info = {repo: info.get("repo_info") or {} for repo, info in repos_payload.items()}
    app_updates = {repo: rels for repo, rels in repos.items() if repo.lower() in APP_UPDATE_REPOS}
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "manifest_url": SITE + "/slidia_manifest.xml",
        "firmware_list_url": SITE + "/firmware-list.html",
        "feed_urls": {
            "json": SITE + "/feeds/" + FEED_JSON_NAME,
            "xml": SITE + "/feeds/" + FEED_XML_NAME,
            "legacy_json": SITE + "/feeds/releases.json",
            "legacy_xml": SITE + "/feeds/releases.xml",
        },
        "packages": packages,
        "repos": repos,
        "repo_info": repo_info,
        "mirrors": mirrors,
        "app_updates": app_updates,
    }


def build_firmware_feed_xml(feed: dict) -> str:
    """The app feed as Atom, readable by the same parsers as the JSON feed."""
    generated_at = html.escape(str(feed.get("generated_at") or ""), quote=True)
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:inni="https://innioasis.app/ns/firmware/1.0">',
        f"  <id>{SITE}/feeds/{FEED_XML_NAME}</id>",
        "  <title>Innioasis and Timmkoo firmware releases</title>",
        f'  <link rel="alternate" type="text/html" href="{SITE}/firmware-list.html"/>',
        f'  <link rel="self" type="application/atom+xml" href="{SITE}/feeds/{FEED_XML_NAME}"/>',
        f"  <updated>{generated_at}</updated>",
        f"  <inni:schema_version>{int(feed.get('schema_version') or 2)}</inni:schema_version>",
        f"  <inni:manifest_url>{html.escape(str(feed.get('manifest_url') or ''), quote=True)}"
        "</inni:manifest_url>",
        f"  <inni:firmware_list_url>{html.escape(str(feed.get('firmware_list_url') or ''), quote=True)}"
        "</inni:firmware_list_url>",
        "  <inni:packages>",
    ]
    for pkg in feed.get("packages") or []:
        attrs = " ".join(
            f'{html.escape(str(key), quote=True)}="{html.escape(str(value), quote=True)}"'
            for key, value in pkg.items() if str(value) != ""
        )
        lines.append(f"    <inni:package {attrs}/>" if attrs else "    <inni:package/>")
    lines.append("  </inni:packages>")
    lines.append("  <inni:mirrors>")
    for mirror_repo, mirror in (feed.get("mirrors") or {}).items():
        lines.append(
            "    <inni:mirror repo=\"%s\" source_repo=\"%s\" updated_at=\"%s\">"
            % (html.escape(mirror_repo, quote=True),
               html.escape(str(mirror.get("source_repo") or ""), quote=True),
               html.escape(str(mirror.get("updated_at") or ""), quote=True))
        )
        for tag, rel in (mirror.get("releases") or {}).items():
            lines.append(
                "      <inni:release tag=\"%s\" original_tag=\"%s\" mirror_tag=\"%s\" "
                "release_name=\"%s\" published_at=\"%s\">"
                % (html.escape(str(tag), quote=True),
                   html.escape(str(rel.get("original_tag") or tag), quote=True),
                   html.escape(str(rel.get("mirror_tag") or tag), quote=True),
                   html.escape(str(rel.get("release_name") or tag), quote=True),
                   html.escape(str(rel.get("published_at") or ""), quote=True))
            )
            for source_asset, info in (rel.get("assets") or {}).items():
                lines.append(
                    "        <inni:mirror_asset name=\"%s\" tag=\"%s\" original_url=\"%s\" "
                    "original_size=\"%d\" mirror_original_url=\"%s\">"
                    % (html.escape(str(source_asset), quote=True),
                       html.escape(str(tag), quote=True),
                       html.escape(str(info.get("original_url") or ""), quote=True),
                       int(info.get("original_size") or 0),
                       html.escape(str(info.get("mirror_original_url") or ""), quote=True))
                )
                for platform, pkg in (info.get("packages") or {}).items():
                    lines.append(
                        "          <inni:package platform=\"%s\" name=\"%s\" url=\"%s\" size=\"%d\"/>"
                        % (html.escape(str(platform), quote=True),
                           html.escape(str(pkg.get("name") or ""), quote=True),
                           html.escape(str(pkg.get("url") or ""), quote=True),
                           int(pkg.get("size") or 0))
                    )
                lines.append("        </inni:mirror_asset>")
            lines.append("      </inni:release>")
        lines.append("    </inni:mirror>")
    lines.append("  </inni:mirrors>")

    for repo, releases in (feed.get("repos") or {}).items():
        is_update = repo.lower() in APP_UPDATE_REPOS
        for rel in releases:
            tag = str(rel.get("tag_name") or "")
            if not tag:
                continue
            published = html.escape(str(rel.get("published_at") or ""), quote=True)
            lines.append("  <entry>")
            lines.append(f"    <id>tag:innioasis.app,2026:{html.escape(repo)}/{html.escape(tag)}</id>")
            lines.append(f"    <updated>{published}</updated>")
            lines.append(f"    <published>{published}</published>")
            lines.append(f"    <title>{html.escape(str(rel.get('name') or tag))}</title>")
            lines.append(
                '    <link rel="alternate" type="text/html" href="%s"/>'
                % html.escape(str(rel.get("html_url") or ""), quote=True)
            )
            if is_update:
                lines.append('    <category term="app_update"/>')
            lines.append(f"    <inni:repo>{html.escape(repo)}</inni:repo>")
            lines.append(f"    <inni:tag_name>{html.escape(tag)}</inni:tag_name>")
            lines.append(f"    <inni:name>{html.escape(str(rel.get('name') or tag))}</inni:name>")
            lines.append("    <inni:prerelease>%s</inni:prerelease>"
                         % ("true" if rel.get("prerelease") else "false"))
            if rel.get("icon_url"):
                lines.append(f"    <inni:icon_url>{html.escape(str(rel['icon_url']))}</inni:icon_url>")
            if rel.get("icon_dark_url"):
                lines.append("    <inni:icon_dark_url>%s</inni:icon_dark_url>"
                             % html.escape(str(rel["icon_dark_url"])))
            for asset in rel.get("assets") or []:
                lines.append(
                    '    <link rel="enclosure" href="%s" title="%s" length="%d" type="%s"/>'
                    % (html.escape(str(asset.get("browser_download_url") or ""), quote=True),
                       html.escape(str(asset.get("name") or ""), quote=True),
                       int(asset.get("size") or 0),
                       html.escape(str(asset.get("content_type") or "application/octet-stream"),
                                   quote=True))
                )
            lines.append('    <content type="text">%s</content>'
                         % html.escape(str(rel.get("body") or "")))
            lines.append("  </entry>")
    lines.append("</feed>\n")
    return "\n".join(lines)


def build_feed_index(feed: dict, generated_at: str) -> dict:
    """Where every generated file lives, for the app and for readers."""
    repos: dict[str, dict] = {}
    for repo in (feed.get("repos") or {}):
        lower = repo.lower()
        repos[repo] = {
            "repo": repo,
            "releases_json": f"{SITE}/feeds/{lower}/releases.json",
            "releases_atom": f"{SITE}/feeds/{lower}/releases.atom",
            "repo_json": f"{SITE}/feeds/{lower}/repo.json",
        }
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "manifest_url": feed.get("manifest_url"),
        "firmware_list_url": feed.get("firmware_list_url"),
        "feeds": feed.get("feed_urls"),
        "legacy": {
            "json": SITE + "/feeds/releases.json",
            "xml": SITE + "/feeds/releases.xml",
        },
        "repos": repos,
        "mirrors": {
            repo: {"source_repo": info.get("source_repo"), "updated_at": info.get("updated_at")}
            for repo, info in (feed.get("mirrors") or {}).items()
        },
    }


def update_firmware_catalog_js(
    hardcoded_releases: dict[str, list[dict]],
    release_icons: dict[str, str],
    repo_stats: dict[str, dict],
) -> None:
    catalog_path = ROOT / "firmware-catalog.js"
    if not catalog_path.exists():
        return
    text = catalog_path.read_text(encoding="utf-8")
    match = re.search(r"(window\.INNIOASIS_FIRMWARE_CATALOG\s*=\s*\[[\s\S]*?\n\];)", text)
    if not match:
        print("  ! Could not locate INNIOASIS_FIRMWARE_CATALOG in firmware-catalog.js", file=sys.stderr)
        return
    catalog_block = match.group(1)
    new_content = (
        catalog_block
        + "\n\nwindow.INNIOASIS_HARDCODED_RELEASES = "
        + json.dumps(hardcoded_releases, indent=2)
        + ";\n\nwindow.INNIOASIS_RELEASE_ICONS = "
        + json.dumps(release_icons, indent=2, sort_keys=True)
        + ";\n\nwindow.INNIOASIS_REPO_STATS = "
        + json.dumps(repo_stats, indent=2, sort_keys=True)
        + ";\n"
    )
    catalog_path.write_text(new_content, encoding="utf-8")


def collect_target_repos() -> tuple[list[str], dict[str, dict]]:
    catalog = gdp.load_catalog()
    manifest = gdp.load_manifest()
    repo_defaults: dict[str, dict] = {}
    ordered_repos: list[str] = []

    def add_repo(repo_name: str, icon: str = "", icon_dark: str = "") -> None:
        repo_clean = (repo_name or "").strip().strip("/")
        if "/" not in repo_clean or "please-click" in repo_clean.lower():
            return
        lower = repo_clean.lower()
        if lower not in repo_defaults:
            repo_defaults[lower] = {
                "repo": repo_clean,
                "icon": icon,
                "icon_dark": icon_dark,
            }
            ordered_repos.append(repo_clean)
        else:
            if icon and not repo_defaults[lower].get("icon"):
                repo_defaults[lower]["icon"] = icon
            if icon_dark and not repo_defaults[lower].get("icon_dark"):
                repo_defaults[lower]["icon_dark"] = icon_dark

    for item in catalog:
        add_repo(str(item.get("repo") or ""), str(item.get("icon") or ""), str(item.get("icon_dark") or ""))
    for pkg in manifest:
        add_repo(str(pkg.get("repo") or ""), str(pkg.get("icon") or ""), str(pkg.get("icon_dark") or ""))
        for attr in ("info_repo", "apk_repo", "derivative"):
            if pkg.get(attr):
                add_repo(str(pkg.get(attr) or ""))
        for mirror in re.split(r"[\s,]+", str(pkg.get("portable_zips") or "")):
            add_repo(mirror)
    for extra in EXTRA_REPOS:
        add_repo(extra)
    return ordered_repos, repo_defaults


def build(refresh: bool = False) -> None:
    FEEDS_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    ordered_repos, repo_defaults = collect_target_repos()
    packages = load_manifest_packages()
    mirror_map = portable_mirror_map(packages)
    mirror_repos = {mirror.lower() for mirrors in mirror_map.values() for mirror in mirrors}
    skip_catalog = {repo.lower() for repo in EXTRA_REPOS} | mirror_repos
    print("Generating 1:1 backup feeds for %d repositories (%d portable mirrors)..."
          % (len(ordered_repos), len(mirror_repos)))

    existing_backup: dict[str, dict] = {}
    master_json_path = FEEDS_DIR / "releases.json"
    if master_json_path.exists():
        try:
            loaded = json.loads(master_json_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("repos"), dict):
                existing_backup = loaded["repos"]
        except (OSError, json.JSONDecodeError):
            pass

    repos_payload: dict[str, dict] = {}
    hardcoded_releases: dict[str, list[dict]] = {}
    release_icons: dict[str, str] = {}
    repo_stats: dict[str, dict] = {}

    for repo in ordered_repos:
        lower = repo.lower()
        defaults = repo_defaults.get(lower, {})
        default_icon = str(defaults.get("icon") or "")
        default_dark_icon = str(defaults.get("icon_dark") or "")

        raw_releases = fetch_all_repo_releases(repo, refresh=refresh)
        repo_info = fetch_repo_info(repo, refresh=refresh)

        if not raw_releases and repo in existing_backup:
            print(f"  ! {repo}: using existing backup ({len(existing_backup[repo].get('releases', []))} releases)")
            normalized = existing_backup[repo].get("releases", [])
            if not repo_info:
                repo_info = existing_backup[repo].get("repo_info", {})
        else:
            normalized = [normalize_release(r, repo, default_icon, default_dark_icon) for r in raw_releases]

        total_downloads = 0
        resolved_repo_icon = default_icon
        resolved_repo_dark_icon = default_dark_icon
        for rel in normalized:
            if rel.get("icon_url") and not resolved_repo_icon:
                resolved_repo_icon = rel["icon_url"]
            if rel.get("icon_dark_url") and not resolved_repo_dark_icon:
                resolved_repo_dark_icon = rel["icon_dark_url"]
            for asset in rel.get("assets") or []:
                total_downloads += int(asset.get("download_count") or 0)

        stats = {
            "downloads": total_downloads,
            "release_count": len(normalized),
            "stars": int(repo_info.get("stargazers_count") or 0),
            "forks": int(repo_info.get("forks_count") or 0),
            "updated_at": str(repo_info.get("updated_at") or (normalized[0].get("published_at") if normalized else "")),
        }

        repos_payload[repo] = {
            "repo": repo,
            "icon": resolved_repo_icon,
            "icon_dark": resolved_repo_dark_icon,
            "stats": stats,
            "repo_info": repo_info,
            "releases": normalized,
        }
        repo_stats[lower] = stats
        if resolved_repo_icon:
            release_icons[lower] = resolved_repo_icon

        # Write per-repo feeds under lowercase path feeds/<owner>/<repo>/releases.{json,atom}
        owner_part, name_part = lower.split("/", 1)
        repo_feed_dir = FEEDS_DIR / owner_part / name_part
        repo_feed_dir.mkdir(parents=True, exist_ok=True)
        (repo_feed_dir / "releases.json").write_text(
            json.dumps(normalized, indent=2), encoding="utf-8"
        )
        (repo_feed_dir / "releases.atom").write_text(
            build_atom_feed(repo, repo_info, normalized, generated_at), encoding="utf-8"
        )
        (repo_feed_dir / "repo.json").write_text(
            json.dumps(repo_info, indent=2), encoding="utf-8"
        )

        # Write .cache/releases/<owner>_<repo>.json for Innioasis-Updater (updater.py)
        legacy_entries = build_legacy_cache_entries(repo, normalized)
        if legacy_entries:
            cache_file = RELEASES_CACHE_DIR / f"{repo.replace('/', '_')}.json"
            cache_file.write_text(
                json.dumps({"timestamp": time.time(), "releases": legacy_entries}),
                encoding="utf-8",
            )

        # Include in firmware-catalog.js INNIOASIS_HARDCODED_RELEASES for catalog repos
        if lower not in skip_catalog:
            catalog_releases = []
            for rel in normalized:
                catalog_releases.append({
                    "id": rel.get("id") or 0,
                    "tag_name": rel.get("tag_name") or "",
                    "name": rel.get("name") or "",
                    "published_at": rel.get("published_at") or "",
                    "prerelease": bool(rel.get("prerelease", False)),
                    "html_url": rel.get("html_url") or "",
                    "icon_url": rel.get("icon_url") or "",
                    "icon_dark_url": rel.get("icon_dark_url") or "",
                    "body": rel.get("body") or "",
                    "assets": [
                        {
                            "id": a.get("id") or 0,
                            "name": a.get("name") or "",
                            "browser_download_url": a.get("browser_download_url") or "",
                            "size": int(a.get("size") or 0),
                            "download_count": int(a.get("download_count") or 0),
                            "content_type": a.get("content_type") or "",
                        }
                        for a in (rel.get("assets") or [])
                    ],
                })
            hardcoded_releases[repo] = catalog_releases

        print(f"  ✓ {repo:<36} {len(normalized):>3} releases, {total_downloads:>7,} downloads")

    master_payload = {
        "generated_at": generated_at,
        "repos": repos_payload,
    }
    master_json_path.write_text(json.dumps(master_payload, indent=2), encoding="utf-8")
    (FEEDS_DIR / "releases.xml").write_text(
        build_combined_xml(repos_payload, generated_at), encoding="utf-8"
    )

    # Portable mirrors: the packages that let the app install without GitHub.
    mirrors: dict[str, dict] = {}
    sources_by_mirror: dict[str, list[str]] = {}
    for source, mirrors_for_source in mirror_map.items():
        for mirror in mirrors_for_source:
            sources_by_mirror.setdefault(mirror.lower(), []).append(source)
    for mirror_lower, sources in sorted(sources_by_mirror.items()):
        payload = next((info for repo, info in repos_payload.items() if repo.lower() == mirror_lower), None)
        if payload is None:
            print(f"  ! {mirror_lower}: mirror repository not collected", file=sys.stderr)
            continue
        index = fetch_mirror_index(payload["repo"], refresh=refresh)
        mirror_entry = build_mirror_payload(
            payload["repo"], sources, index, payload.get("releases") or [], generated_at
        )
        mirrors[payload["repo"]] = mirror_entry
        print(f"  ✓ mirror {payload['repo']:<34} {len(mirror_entry['releases']):>3} portable releases"
              f"{' (no index.json)' if not index else ''}")

    firmware_feed = build_firmware_feed_json(repos_payload, packages, mirrors, generated_at)
    (FEEDS_DIR / FEED_JSON_NAME).write_text(
        json.dumps(firmware_feed, indent=2), encoding="utf-8"
    )
    (FEEDS_DIR / FEED_XML_NAME).write_text(build_firmware_feed_xml(firmware_feed), encoding="utf-8")
    (FEEDS_DIR / "index.json").write_text(
        json.dumps(build_feed_index(firmware_feed, generated_at), indent=2), encoding="utf-8"
    )

    update_firmware_catalog_js(hardcoded_releases, release_icons, repo_stats)
    print("Done: wrote feeds/releases.{json,xml}, feeds/firmware-releases.json, "
          "feeds/firmware-feed.xml, feeds/index.json, per-repo feeds, "
          ".cache/releases, and firmware-catalog.js")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 1:1 backup feeds for GitHub releases and metadata.")
    parser.add_argument("--refresh", action="store_true", help="ignore cached GitHub responses")
    args = parser.parse_args()
    build(refresh=args.refresh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
