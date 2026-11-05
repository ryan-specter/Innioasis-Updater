#!/usr/bin/env python3
"""Create and fill one GitHub repository per stock-firmware model.

The local archive in ``All Timmkoo and Innioasis Firmware`` holds one folder
per published stock firmware, named exactly as its release tag must be
(``MX3-9_EN-V1.03-20260707``). This script turns each of those folders into a
release in the model's own repository:

    Innioasis G1/MX3-9_EN-V1.03-20260707/ -> y1-community/g1-stock-rom
                                             tag  MX3-9_EN-V1.03-20260707
                                             file rom_g1.zip

Repository, package and brand names come from ``DEVICES`` and follow the
existing ``y1-stock-rom`` convention. Runs are idempotent: an existing
repository is reused, an existing release with the same tag is updated in
place, and an asset that is already uploaded at the same size is skipped, so
an interrupted run can simply be started again.

GitHub caps a release asset at 2 GiB. A package larger than that is written as
numbered volumes (``rom_pr1.zip.001``, ``.002``, ...) which the reader
concatenates before unzipping (``cat rom_pr1.zip.* > rom_pr1.zip``).

Usage:
    python scripts/publish_stock_repos.py [--dry-run] [--device G1,G3]
                                          [--limit N] [--force]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "All Timmkoo and Innioasis Firmware"
ORG = "y1-community"
WORK = ROOT / ".cache" / "publish"
API = "https://api.github.com"
MAX_ASSET = 2 * 1024 ** 3
VOLUME = 1900 * 1024 ** 2

#: Local folder -> repository and brand. Every package is named
#: ``rom_<model>.zip`` (rom_g1.zip, rom_pr1.zip, ...), matching the convention
#: the other stock ROM releases already use.
DEVICES = {
    "Innioasis G1": {"device": "G1", "brand": "Innioasis", "repo": "g1-stock-rom",
                     "package": "rom_g1.zip", "name": "Innioasis G1"},
    "Innioasis G3": {"device": "G3", "brand": "Innioasis", "repo": "g3-stock-rom",
                     "package": "rom_g3.zip", "name": "Innioasis G3"},
    "Innioasis G5": {"device": "G5", "brand": "Innioasis", "repo": "g5-stock-rom",
                     "package": "rom_g5.zip", "name": "Innioasis G5"},
    "Innioasis PR1": {"device": "PR1", "brand": "Innioasis", "repo": "pr1-stock-rom",
                      "package": "rom_pr1.zip", "name": "Innioasis PR1"},
    "Innioasis R1": {"device": "R1", "brand": "Innioasis", "repo": "r1-stock-rom",
                     "package": "rom_r1.zip", "name": "Innioasis R1"},
    "Timmkoo SR1": {"device": "SR1", "brand": "Timmkoo", "repo": "sr1-stock-rom",
                    "package": "rom_sr1.zip", "name": "Timmkoo SR1"},
}


def token() -> str:
    """Reuse the GitHub credential Git already has, never a copied value."""
    for variable in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = (os.environ.get(variable) or "").strip()
        if value:
            return value
    try:
        output = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return ""
    for line in output.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return ""


TOKEN = token()


def api(method: str, path: str, payload: dict | None = None):
    """JSON API call: returns (status, body)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(API + path, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", "Bearer " + TOKEN)
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", "replace")
            return response.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"message": raw[:400]}


def ensure_repo(meta: dict) -> str:
    repo = "%s/%s" % (ORG, meta["repo"])
    status, body = api("GET", "/repos/" + repo)
    if status == 200:
        return repo
    status, body = api("POST", "/orgs/%s/repos" % ORG, {
        "name": meta["repo"],
        "description": "Original (stock) firmware releases for the %s, "
                       "archived from the official Innioasis packages."
                       % meta["name"],
        "private": False,
        "has_issues": True,
        "has_wiki": False,
        "has_projects": False,
        "auto_init": False,
    })
    if status not in (200, 201):
        raise SystemExit("could not create %s: %s %s" % (repo, status, body))
    print("  created repository %s" % repo)
    return repo


def ensure_readme(repo: str, meta: dict) -> None:
    body = readme_markdown(meta)
    status, current = api("GET", "/repos/%s/contents/README.md" % repo)
    payload = {
        "message": "Document the %s stock firmware archive" % meta["name"],
        "content": __import__("base64").b64encode(body.encode("utf-8")).decode("ascii"),
    }
    if status == 200 and isinstance(current, dict) and current.get("sha"):
        payload["sha"] = current["sha"]
    api("PUT", "/repos/%s/contents/README.md" % repo, payload)


def readme_markdown(meta: dict) -> str:
    return """# %(name)s original software

Archived original (stock) firmware for the %(name)s, published here so a
player can always be restored to the software it shipped with. Every release
tag is the package's own build name from Innioasis.

## Download

Each release carries `%(package)s`. Unzip it and flash it with SP Flash Tool
using the scatter file inside the archive, or install it with Innioasis
Updater CE once the model is listed there.

The archive index for every bundled model is at
<https://innioasis.app/firmware.html?model=%(device)s>.

## Notes

- These are unmodified manufacturer images. No root, no repack.
- Flashing erases the player. Back up music first.
- Always use the scatter file that ships inside the same release.

Maintained by the Innioasis community. Updater CE and this archive are
independent community projects.
""" % meta


def release_body(meta: dict, tag: str, files: list[dict]) -> str:
    date = ""
    match = re.search(r"(20\d{2})(\d{2})(\d{2})", tag)
    if match:
        try:
            date = dt.date(int(match.group(1)), int(match.group(2)),
                           int(match.group(3))).isoformat()
        except ValueError:
            date = ""
    lines = [
        "Original %s software **%s**." % (meta["name"], tag),
        "",
        "- Model: **%s** (%s)" % (meta["device"], meta["brand"]),
        "- Package: `%s`" % meta["package"],
        "- Build tag: `%s`" % tag,
    ]
    if date:
        lines.append("- Build date: %s" % date)
    lines += [
        "",
        "## Install",
        "",
        "1. Download `%s` (every numbered volume if the release has more than "
        "one, then `cat %s.* > %s`)." % (meta["package"], meta["package"], meta["package"]),
        "2. Unzip it. Keep the scatter file next to the images.",
        "3. Open SP Flash Tool, choose **Download Only**, load the scatter file "
        "from the archive and flash.",
        "4. Or use Innioasis Updater CE: <https://innioasis.app/guide.html>",
        "",
        "This wipes the player. Back up music and recordings first.",
        "",
        "## Files",
        "",
        "| File | Size |",
        "| --- | --- |",
    ]
    for entry in files:
        lines.append("| `%s` | %.1f MB |" % (entry["name"], entry["size"] / 1024 ** 2))
    lines += [
        "",
        "Full archive: <https://innioasis.app/firmware.html?model=%s>" % meta["device"],
    ]
    return "\n".join(lines)


def version_folders(folder: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    """(release tag, source folder) for every build, oldest name first.

    A folder that only wraps one named folder (and a stray download copy such
    as ``R2-V1.34-20260208(1)``) is addressed by its inner name, because that
    is the build's own tag.
    """
    versions: list[tuple[str, pathlib.Path]] = []
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        if not entry.is_dir():
            continue
        tag = re.sub(r"\(\d+\)$", "", entry.name).strip()
        source = entry
        inner = entry / tag
        if inner.is_dir() and any(child.is_file() for child in inner.iterdir()):
            source = inner
        versions.append((tag, source))
    return versions


def build_zip(source: pathlib.Path, target: pathlib.Path) -> None:
    """Zip one firmware folder, skipping archives and unsigned duplicates.

    Some vendor dumps ship ``system.img`` next to ``system-sign.img``. The
    scatter file flashes the signed image, and both are byte-identical, so
    writing both would double the archive for no benefit.
    """
    names = {path.name.lower() for path in source.rglob("*") if path.is_file()}
    skipped = 0
    # Level 9 is deflate's maximum. These images are large enough that the
    # extra pass is worth it: it is what keeps a 3.4 GB G-series package under
    # GitHub's 2 GiB per-asset limit.
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() in (".zip", ".rar", ".7z"):
                continue
            stem, dot, suffix = path.name.rpartition(".")
            if stem and not stem.lower().endswith("-sign") and not stem.lower().endswith("-verified"):
                duplicates = {stem + "-sign." + suffix, stem + "-verified." + suffix}
                if duplicates & names:
                    skipped += 1
                    continue
            archive.write(path, path.relative_to(source).as_posix())
    print("    zip %.2f GB -> %s%s"
          % (target.stat().st_size / 1024 ** 3, target.name,
             " (%d unsigned duplicates skipped)" % skipped if skipped else ""))


def split_volumes(path: pathlib.Path) -> list[pathlib.Path]:
    """Numbered volumes for a package GitHub would reject as one asset."""
    parts: list[pathlib.Path] = []
    with path.open("rb") as source:
        index = 1
        while True:
            chunk = source.read(VOLUME)
            if not chunk:
                break
            part = path.with_name("%s.%03d" % (path.name, index))
            part.write_bytes(chunk)
            parts.append(part)
            index += 1
    path.unlink()
    return parts


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def upload_asset(upload_url: str, path: pathlib.Path) -> bool:
    url = upload_url.split("{", 1)[0] + "?" + urllib.parse.urlencode({"name": path.name})
    result = subprocess.run(
        ["curl", "-sS", "-X", "POST", "--fail-with-body",
         "-H", "Authorization: Bearer " + TOKEN,
         "-H", "Content-Type: application/octet-stream",
         "-H", "Accept: application/vnd.github+json",
         "--data-binary", "@" + str(path), url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("    ! upload failed for %s: %s" % (path.name, (result.stdout or result.stderr)[:300]))
        return False
    return True


def publish_release(repo: str, meta: dict, tag: str, folder: pathlib.Path,
                    force: bool = False) -> None:
    print("  %-24s %s" % (meta["device"], tag))
    WORK.mkdir(parents=True, exist_ok=True)
    zip_path = WORK / meta["package"]
    if not zip_path.exists():
        build_zip(folder, zip_path)
    else:
        print("    reusing %s" % zip_path.name)

    parts = [zip_path]
    if zip_path.stat().st_size > MAX_ASSET:
        print("    %.2f GB exceeds the 2 GiB asset limit: splitting"
              % (zip_path.stat().st_size / 1024 ** 3))
        parts = split_volumes(zip_path)
        for part in parts:
            print("    volume %s (%.2f GB)" % (part.name, part.stat().st_size / 1024 ** 3))

    sums = WORK / ("SHA256SUMS.%s" % re.sub(r"[^A-Za-z0-9._-]+", "-", tag))
    sums.write_text("".join("%s  %s\n" % (sha256(part), part.name) for part in parts),
                    encoding="utf-8")

    status, release = api("GET", "/repos/%s/releases/tags/%s"
                          % (repo, urllib.parse.quote(tag, safe="")))
    body = release_body(meta, tag, [{"name": p.name, "size": p.stat().st_size} for p in parts]
                        + [{"name": "SHA256SUMS", "size": sums.stat().st_size}])
    if status == 200 and isinstance(release, dict) and release.get("id"):
        api("PATCH", "/repos/%s/releases/%s" % (repo, release["id"]), {
            "name": tag, "body": body, "prerelease": False, "draft": False,
        })
        upload_url = release["upload_url"]
        existing = {asset["name"]: asset for asset in release.get("assets") or []}
        print("    release exists (%d assets)" % len(existing))
    else:
        status, release = api("POST", "/repos/%s/releases" % repo, {
            "tag_name": tag, "name": tag, "body": body,
            "draft": False, "prerelease": False,
            "target_commitish": "main",
        })
        if status not in (200, 201):
            print("    ! release creation failed: %s %s" % (status, release))
            return
        upload_url = release["upload_url"]
        existing = {}

    for part in parts + [sums]:
        already = existing.get(part.name)
        if already and int(already.get("size") or 0) == part.stat().st_size and not force:
            print("    %-24s already uploaded" % part.name)
            continue
        if already and force:
            api("DELETE", "/repos/%s/releases/assets/%s" % (repo, already["id"]))
        print("    uploading %-24s %.2f GB" % (part.name, part.stat().st_size / 1024 ** 3))
        if not upload_asset(upload_url, part):
            print("    ! stopped after a failed upload; rerun to resume")
            return
    for part in parts:
        part.unlink(missing_ok=True)
    print("    done: %s/releases/tag/%s" % (repo, tag))


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish stock firmware releases.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--device", default="", help="comma separated models, e.g. G1,G3")
    parser.add_argument("--limit", type=int, default=0, help="releases per model")
    parser.add_argument("--force", action="store_true", help="re-upload existing assets")
    args = parser.parse_args()

    if not args.dry_run and not TOKEN:
        raise SystemExit("no GitHub credential found (git credential fill)")
    wanted = {item.strip().upper() for item in args.device.split(",") if item.strip()}
    if not ARCHIVE.exists():
        raise SystemExit("archive folder not found: %s" % ARCHIVE)

    for folder_name, meta in DEVICES.items():
        if wanted and meta["device"] not in wanted:
            continue
        folder = ARCHIVE / folder_name
        if not folder.exists():
            print("%s: no local folder" % folder_name)
            continue
        versions = version_folders(folder)
        if not versions:
            print("%s: no firmware versions yet" % folder_name)
            continue
        if args.limit:
            versions = versions[-args.limit:]
        print("%s -> %s/%s (%d versions)"
              % (folder_name, ORG, meta["repo"], len(versions)))
        if args.dry_run:
            for tag, _source in versions:
                print("  %-24s %s" % (meta["package"], tag))
            continue
        repo = ensure_repo(meta)
        ensure_readme(repo, meta)
        for tag, source in versions:
            publish_release(repo, meta, tag, source, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
