#!/usr/bin/env python3
"""Headless firmware flash helper for Innioasis / Timmkoo MediaTek players.

This script is the machine-readable half of the ``flash-innioasis-device``
skill. It performs the same steps Updater CE performs for a guided install,
in the same order, using the same back ends:

1. resolve the firmware package (folder, .zip, or an already-extracted tree),
2. pick the package's own scatter (``*_Android_scatter.txt`` beats a
   ``preserve_data`` variant and any other ``*scatter*.txt``),
3. require every image the scatter declares,
4. read platform / storage / model facts and refuse an obvious mismatch,
5. flash through the app's own headless MTKClient entry point
   (``--flash-cli``), or through SP Flash Tool console mode on Windows/Linux,
6. report the package's post-install page and the one-time donation ask.

It never formats flash (Download Only), never writes MBR/EBR, and never
builds its own scatter addresses: those decisions belong to the app's flash
engine, which this script invokes rather than reimplements.

Exit codes
    0  flash succeeded
    1  flash ran and failed (device may need a power cycle before a retry)
    2  preflight refused (package incomplete / wrong model / no permission)
    3  no usable backend on this machine, or a required tool is missing
    4  the user declined, or ``--check``/``--dry-run`` finished without writing
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DONATE_URL = "https://ko-fi.com/teamslide"
ARCHIVE_URL = "https://github.com/y1-community"
CATALOGUE_URL = "https://innioasis.app/slidia_manifest.xml"
SP_DA_NAME = "MTK_AllInOne_DA.bin"
KEEP_DATA_SCATTER_NAME = ".updater_keepdata.txt"

# SoC -> model, used only as a cross-check. The authoritative mapping lives in
# src/catalog.py (infer_model_from_scatter); keep this table in step with it.
PLATFORM_MODELS = {
    "MT6572": "Y1",
    "MT6582": "Y2",
    "MT6580": "Y2",
    "MT6753": "G1",
    "MT6765": "PR1",
}
PROJECT_MODELS = {
    "eastaeon72_wet_jb3": "Y1",
    "eastaeon82_wet_kk": "Y2",
    "eastaeon80_wet_kk": "Q5",
    "k53v1_64_bsp": "G1",
    "k62v1_64_bsp": "PR1",
    "j5052": "SR1",
    "g368_nyx": "R1",
}

OK, FAILED, REFUSED, NO_BACKEND, DECLINED = 0, 1, 2, 3, 4


# --------------------------------------------------------------------------- #
# discovery
# --------------------------------------------------------------------------- #
def repo_root(start: Path) -> Optional[Path]:
    """The Updater CE checkout containing this script, when there is one."""
    for candidate in [start, *start.parents]:
        if (candidate / "src" / "flash_service.py").is_file():
            return candidate
    return None


def import_app_modules(root: Optional[Path]):
    """Import the app's own modules so the CLI matches the guided flow.

    Returns a namespace of the callables we use, or ``None`` when this is not
    a checkout (a user who installed the app but has no source tree).
    """
    if root is None:
        return None
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from src import flash_service  # noqa: F401
        from src import terminal_install
        from src import sp_console_config
    except Exception:
        return None
    return {
        "flash_service": flash_service,
        "terminal_install": terminal_install,
        "sp_console_config": sp_console_config,
    }


def find_app_binary() -> Optional[Path]:
    """An installed Updater CE / MediaTek Installer executable, if present."""
    env = os.environ.get("INNIOASIS_UPDATER") or os.environ.get("UPDATER_CE")
    if env and Path(env).is_file():
        return Path(env)
    candidates = [
        Path("/Applications/Updater CE.app/Contents/MacOS/UpdaterCE"),
        Path.home() / "Applications" / "Updater CE.app" / "Contents" / "MacOS" / "UpdaterCE",
        Path("/usr/bin/updater-ce"),
        Path("/usr/local/bin/updater-ce"),
        Path.home() / ".local" / "bin" / "updater-ce",
        Path("C:/Program Files/Updater CE/InnioasisUpdater.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    for name in ("updater-ce", "InnioasisUpdater", "MediaTekInstaller"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


# --------------------------------------------------------------------------- #
# package facts
# --------------------------------------------------------------------------- #
@dataclass
class Package:
    folder: Path
    scatter: Path
    platform: str = ""
    storage: str = ""
    project: str = ""
    model: str = ""
    name: str = ""
    version: str = ""
    type: str = ""
    post_install: str = ""
    post_install_2: str = ""
    images: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    keep_data_capable: bool = False
    temp_dir: Optional[Path] = None

    def as_dict(self) -> dict:
        return {
            "folder": str(self.folder),
            "scatter": self.scatter.name,
            "platform": self.platform,
            "storage": self.storage,
            "project": self.project,
            "model": self.model,
            "name": self.name,
            "version": self.version,
            "type": self.type,
            "images": len(self.images),
            "missing": self.missing,
            "keep_data_capable": self.keep_data_capable,
            "post_install": self.post_install,
            "post_install_2": self.post_install_2,
        }


_SCATTER_LINE_RE = re.compile(
    r"^\s*-?\s*(partition_name|file_name|is_download|partition_size|"
    r"linear_start_addr|physical_start_addr|region|platform|storage|project)\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)


def select_scatter(folder: Path) -> Optional[Path]:
    """The package's own scatter, mirroring src/fw_package.pick_scatter rules."""
    try:
        matches = [
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() == ".txt" and "scatter" in p.name.lower()
        ]
    except OSError:
        return None
    if not matches:
        return None

    def rank(path: Path) -> int:
        stem = path.name.lower()
        if any(tag in stem for tag in ("preserve", "keep_data", "keepdata", "nodata")):
            return 1
        return 0 if stem.endswith("android_scatter.txt") else 2

    best = min(rank(p) for p in matches)
    winners = [p for p in matches if rank(p) == best]
    return winners[0] if len(winners) == 1 else None


def parse_scatter(scatter: Path) -> tuple[dict, list]:
    """(general facts, [{name, file, is_download}]) from a scatter file."""
    general: dict = {}
    parts: list = []
    current: Optional[dict] = None
    try:
        text = scatter.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return general, parts
    for line in text.splitlines():
        match = _SCATTER_LINE_RE.match(line)
        if not match:
            continue
        key, value = match.group(1).lower(), match.group(2).strip().strip('"')
        if key in ("platform", "storage", "project"):
            general.setdefault(key, value)
            continue
        if key == "partition_name":
            current = {"name": value, "file": "", "is_download": False}
            parts.append(current)
        elif current is not None:
            if key == "file_name":
                current["file"] = value
            elif key == "is_download":
                current["is_download"] = value.lower() == "true"
    return general, parts


def read_ini(folder: Path) -> dict:
    """Release metadata from fw_package.ini (optional; never required)."""
    ini = folder / "fw_package.ini"
    if not ini.is_file():
        return {}
    try:
        text = ini.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    if not any(line.strip().startswith("[") for line in text.splitlines()):
        text = "[fw_package]\n" + text
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(text)
    except configparser.Error:
        return {}
    if not parser.sections():
        return {}
    section = next(
        (s for s in parser.sections() if s.lower() in ("firmware", "package", "fw_package")),
        parser.sections()[0],
    )
    values = {}
    for key in parser[section]:
        values[key.strip().lower().replace(" ", "_")] = parser[section][key].strip()
    enabled = values.get("enabled", "true").lower() not in ("false", "0", "no", "off")
    if not enabled:
        return {"enabled": "false"}
    return values


def unpack(source: Path) -> tuple[Path, Optional[Path]]:
    """(folder to read, temp dir to clean up) for a folder / zip package."""
    if source.is_dir():
        return source, None
    if source.suffix.lower() != ".zip":
        raise SystemExit(
            f"{source} is not a folder or .zip. Extract .rar/.7z packages first "
            "(the app bundles UnRAR; `unar`/`7z` work too) and pass the folder."
        )
    temp = Path(tempfile.mkdtemp(prefix="innioasis-fw-"))
    with zipfile.ZipFile(source) as archive:
        archive.extractall(temp)
    for candidate in [temp, *sorted(p for p in temp.iterdir() if p.is_dir())]:
        if select_scatter(candidate) is not None:
            return candidate, temp
    return temp, temp


def inspect_package(source: Path) -> Package:
    folder, temp = unpack(source)
    scatter = select_scatter(folder)
    if scatter is None:
        raise SystemExit(
            f"No unambiguous scatter in {folder}. A package needs exactly one "
            "*scatter*.txt; two at the same rank means two different firmwares."
        )
    general, parts = parse_scatter(scatter)
    images = [p for p in parts if p["is_download"] and p["file"].upper() != "NONE"]
    missing = [p["file"] for p in images if not (folder / p["file"]).is_file()]
    ini = read_ini(folder)

    platform = (general.get("platform", "") or "").upper()
    project = general.get("project", "") or ""
    model = (
        (ini.get("target_model") or ini.get("model") or "").strip()
        or PROJECT_MODELS.get(project.lower(), "")
        or PLATFORM_MODELS.get(platform, "")
    )
    keep_data = any(
        "user" in p["name"].lower() or "usr" in p["name"].lower() for p in images
    )
    return Package(
        folder=folder,
        scatter=scatter,
        platform=platform,
        storage=(general.get("storage", "") or "").upper(),
        project=project,
        model=model.upper(),
        name=(ini.get("software_name") or ini.get("name") or "").strip(),
        version=(ini.get("version") or "").strip(),
        type=(ini.get("target_type") or ini.get("type") or "").strip(),
        post_install=(ini.get("post_install") or "").strip(),
        post_install_2=(ini.get("post_install_2") or ini.get("post_install2") or "").strip(),
        images=[p["file"] for p in images],
        missing=missing,
        keep_data_capable=keep_data,
        temp_dir=temp,
    )


def write_keep_data_scatter(pkg: Package) -> Path:
    """Drop userdata from a copy of the scatter, as the app's Keep Data does.

    SP Flash Tool writes what the scatter declares and nothing else, so leaving
    the user partition out is the whole feature. Written beside the images
    (SP resolves ``file_name`` relative to the scatter) and named without
    "scatter" so package discovery never sees a second scatter.
    """
    lines = pkg.scatter.read_text(encoding="utf-8", errors="ignore").splitlines()
    out: list = []
    dropping = False
    for line in lines:
        stripped = line.strip()
        match = re.match(r"^-\s*partition_name\s*:\s*(.+)$", stripped, re.IGNORECASE)
        if match:
            name = match.group(1).strip().strip('"').lower()
            dropping = "user" in name or "usr" in name
        if dropping:
            match = re.match(r"^-\s*is_download\s*:\s*true\s*$", stripped, re.IGNORECASE)
            if match:
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f"{indent}- is_download: false")
                dropping = False
                continue
        out.append(line)
    target = pkg.folder / KEEP_DATA_SCATTER_NAME
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    return target


# --------------------------------------------------------------------------- #
# back ends
# --------------------------------------------------------------------------- #
def sp_tool_dir() -> Optional[Path]:
    """Locate a flash_tool payload: env override, app bundle, dev checkout."""
    env = os.environ.get("SP_FLASH_TOOL_DIR")
    candidates = [Path(env)] if env else []
    for root in {Path.cwd(), *Path.cwd().parents}:
        candidates.extend([
            root / "SP_Flash_Tool",
            root / "sp_flash_tool",
            root / "tools" / "SP_Flash_Tool",
            root / "tools" / "windows" / "SP_Flash_Tool_v5.1904_Win",
            root / "tools" / "linux" / "SP_Flash_Tool_v5.1904_Linux",
        ])
    candidates.extend([
        Path.home() / ".cache" / "innioasis-updater" / "linux_flash_tool",
        Path("/opt/Updater CE/SP_Flash_Tool"),
        Path("C:/Program Files/Updater CE/SP_Flash_Tool"),
    ])
    exe = "flash_tool.exe" if os.name == "nt" else "flash_tool"
    for candidate in candidates:
        try:
            if (candidate / exe).is_file():
                return candidate
        except OSError:
            continue
    return None


def mtk_command(pkg: Package, args, mods) -> Optional[list]:
    """The app's headless MTKClient entry point for this package."""
    platform = pkg.platform or ""
    if mods is not None:
        cmd = mods["terminal_install"].mtkclient_command(
            pkg.folder, pkg.scatter, platform, "", pkg.model,
            args.da or "", args.auth or "",
        )
        return cmd

    binary = find_app_binary()
    if binary is None:
        return None
    cmd = [str(binary), "--flash-cli", str(pkg.folder), str(pkg.scatter), platform, ""]
    if pkg.model or args.da or args.auth:
        cmd.extend([pkg.model or "", args.da or "", args.auth or ""])
    return cmd


def sp_command(pkg: Package, args, mods) -> Optional[list]:
    if sys.platform == "darwin":
        return None
    tool = sp_tool_dir()
    if tool is None:
        return None
    exe = tool / ("flash_tool.exe" if os.name == "nt" else "flash_tool")
    if not exe.is_file():
        return None
    da = Path(args.da) if args.da else tool / SP_DA_NAME
    scatter = write_keep_data_scatter(pkg) if args.keep_data else pkg.scatter
    if mods is not None:
        from_scatter_args = mods["flash_service"].sp_flash_tool_console_args
        return [str(exe), *from_scatter_args(str(scatter), str(da), args.auth or "")]
    argv = [
        "-c", "download",
        "-s", str(scatter),
        "-d", str(da),
        "-t", "without",
        "-r",
    ]
    if args.auth:
        raise SystemExit(
            "An authentication file needs SP Flash Tool's console configuration "
            "file, which this standalone path cannot build. Use the app "
            "(`sp_flash_tool_console_args`) or MTKClient."
        )
    return [str(exe), *argv]


def run_sp(cmd: list, tool: Path, args, started: float) -> int:
    env = dict(os.environ)
    if os.name != "nt":
        try:
            from src import linux_sp_flash  # type: ignore

            env = linux_sp_flash.process_env(tool)
        except Exception:
            env.setdefault("LD_LIBRARY_PATH", str(tool))
    print(f"[CMD] {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(
        cmd, cwd=str(tool), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    completed = False
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print(f"[LOG] {line}", flush=True)
        low = line.lower()
        if "flash complete" in low or "all command exec" in low:
            completed = True
    code = proc.wait(timeout=args.timeout)
    # The tool's exit code alone is not the answer: a run that was killed while
    # the device rebooted still finished. The internal log is the record.
    logged = sp_log_completed(started)
    if completed or logged:
        return OK
    print(f"[RESULT] 0 SP_EXIT_{code}", flush=True)
    return FAILED


def sp_log_completed(started: float) -> bool:
    roots = [
        Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "SP_FT_Logs",
        Path.home() / ".cache" / "innioasis-updater" / "linux_flash_tool" / "SP_FT_Logs",
    ]
    for root in roots:
        try:
            logs = list(root.rglob("QT_FLASH_TOOL.log"))
        except OSError:
            continue
        for log in logs:
            try:
                if log.stat().st_mtime < started - 5:
                    continue
                text = log.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            if "flash complete" in text or "all command exec" in text:
                return True
    return False


def run_mtk(cmd: list, args) -> int:
    print(f"[CMD] {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    ok: Optional[bool] = None
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("[RESULT]"):
            ok = line.split()[1] == "1"
        print(line, flush=True)
    code = proc.wait(timeout=args.timeout)
    if ok is None:
        ok = code == 0
    return OK if ok else FAILED


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def backend_available(method: str, pkg: Package, mods) -> tuple[bool, str]:
    if method == "sp":
        tool = sp_tool_dir()
        if os.name == "nt" or sys.platform.startswith("linux"):
            return (tool is not None), f"SP Flash Tool at {tool}" if tool else "no SP Flash Tool"
        return False, "SP Flash Tool does not exist for macOS"
    cmd = mtk_command(pkg, argparse.Namespace(da=None, auth=None), mods)
    if cmd:
        return True, f"MTKClient via {cmd[0]}"
    if repo_root(Path(__file__).resolve().parent) is not None:
        return False, (
            "checkout found but its Python dependencies are not importable with "
            f"{sys.executable}"
        )
    return False, "no Updater CE binary and no checkout"


def choose_backend(args, pkg: Package, mods) -> str:
    if args.method in ("sp", "mtk"):
        return args.method
    if os.name != "nt" and not sys.platform.startswith("linux"):
        return "mtk"
    sp_ok, _ = backend_available("sp", pkg, mods)
    return "sp" if sp_ok else "mtk"


def preflight(pkg: Package, args) -> list:
    problems = []
    if pkg.missing:
        problems.append(
            "package is missing images the scatter declares: " + ", ".join(pkg.missing[:8])
        )
    if not pkg.platform:
        problems.append("scatter declares no `platform:` line, so SP/MTK cannot be configured")
    inferred = PLATFORM_MODELS.get(pkg.platform, "")
    if args.device and pkg.model and args.device.upper() != pkg.model.upper():
        problems.append(
            f"package targets {pkg.model} but --device is {args.device}: refusing to write "
            "the wrong player's firmware"
        )
    elif inferred and pkg.model and inferred != pkg.model:
        problems.append(
            f"scatter platform {pkg.platform} is a {inferred} chip but the package says "
            f"{pkg.model}; confirm the release before flashing"
        )
    if args.keep_data and not pkg.keep_data_capable:
        problems.append("this package declares no user-data partition, so Keep Data is moot")
    if not (pkg.folder / pkg.scatter.name).is_file():
        problems.append("scatter disappeared during preflight")
    return problems


def print_post_install(pkg: Package) -> None:
    if pkg.post_install or pkg.post_install_2:
        print("\nPost-install steps for this release:", flush=True)
        for url in (pkg.post_install, pkg.post_install_2):
            if url:
                print(f"  - {url}", flush=True)
    else:
        print(
            "\nNo post-install page is declared for this package. Open the release notes "
            f"({ARCHIVE_URL}) if the software needs first-boot setup.",
            flush=True,
        )


def print_donation() -> None:
    print(
        "\nUpdater CE, the flashing tools and the firmware archive are free, "
        "ad-free and community-run.\n"
        f"If this install saved your player, one coffee keeps the mirrors online: {DONATE_URL}\n"
        "Mentioning it once is enough; never block the user on it.",
        flush=True,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Flash an Innioasis / Timmkoo MediaTek player with a community firmware package.",
    )
    parser.add_argument("--package", required=True, help="firmware folder, .zip, or extracted tree")
    parser.add_argument("--device", default="", help="expected model (Y1, Y2, A5, ...)")
    parser.add_argument("--method", default="auto", choices=("auto", "sp", "mtk"))
    parser.add_argument("--keep-data", action="store_true", help="leave the user partition alone")
    parser.add_argument("--auth", default="", help="authentication file, when the target needs one")
    parser.add_argument("--da", default="", help="override the Download Agent")
    parser.add_argument("--check", action="store_true", help="preflight only, no flash")
    parser.add_argument("--dry-run", action="store_true", help="print the command, do not run it")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    parser.add_argument("--yes", action="store_true", help="skip the write confirmation")
    parser.add_argument("--timeout", type=int, default=900, help="seconds before giving up")
    args = parser.parse_args(argv)

    root = repo_root(Path(__file__).resolve().parent)
    mods = import_app_modules(root)
    if root:
        print(f"[INFO] using the checkout at {root}", flush=True)
    if root and mods is None:
        print(
            "[WARN] this interpreter cannot import the app's modules (PySide6, pyusb, ...).\n"
            "[WARN] Re-run with the project venv, e.g. .venv-build/bin/python, or "
            "`pip install -r requirements.txt` first.",
            flush=True,
        )

    try:
        pkg = inspect_package(Path(args.package).expanduser())
    except SystemExit as exc:
        print(f"[ERROR] {exc}", flush=True)
        return REFUSED

    problems = preflight(pkg, args)
    method = choose_backend(args, pkg, mods)
    ok, detail = backend_available(method, pkg, mods)

    if args.json:
        print(json.dumps(
            {
                "package": pkg.as_dict(),
                "method": method,
                "backend": detail,
                "backend_available": ok,
                "problems": problems,
            },
            indent=2,
        ))
    else:
        label = f"{pkg.name} {pkg.version}".strip() or "(unnamed package)"
        print(f"[INFO] package : {label}", flush=True)
        print(f"[INFO] target  : {pkg.model or 'unknown'} / {pkg.platform or '?'} / {pkg.storage or '?'}", flush=True)
        print(f"[INFO] scatter : {pkg.scatter.name} ({len(pkg.images)} images)", flush=True)
        print(f"[INFO] back end: {method} — {detail}", flush=True)
        for problem in problems:
            print(f"[WARN] {problem}", flush=True)

    if args.check:
        return DECLINED if not problems else REFUSED
    if problems:
        for problem in problems:
            print(f"[ERROR] {problem}", flush=True)
        print("[HINT] Fix the package or pass the right --device; nothing was written.", flush=True)
        return REFUSED
    if not ok:
        print(
            "[ERROR] No flashing back end is usable here.\n"
            "[HINT] Install Updater CE (or run from a checkout of updater-ce-neo) and retry, "
            "or guide the user through the app's Install Software screen.",
            flush=True,
        )
        return NO_BACKEND

    if method == "sp":
        tool = sp_tool_dir()
        assert tool is not None
        cmd = sp_command(pkg, args, mods)
    else:
        cmd = mtk_command(pkg, args, mods)
    if not cmd:
        print("[ERROR] could not build a command for the chosen back end", flush=True)
        return NO_BACKEND

    if args.dry_run:
        print(f"[DRY-RUN] {' '.join(cmd)}", flush=True)
        return DECLINED

    print(
        "\nConnect the player POWERED OFF; let it be plugged in only once the tool is "
        "searching for it. Do not unplug it during the write.",
        flush=True,
    )
    if not args.yes:
        if not sys.stdin.isatty():
            print("[ERROR] refusing to write flash without --yes in a non-interactive run", flush=True)
            return REFUSED
        answer = input("Type 'flash' to start: ").strip().lower()
        if answer != "flash":
            print("[CANCELLED] nothing was written", flush=True)
            return DECLINED

    started = time.time()
    try:
        if method == "sp":
            code = run_sp(cmd, sp_tool_dir() or pkg.folder, args, started)
        else:
            mtk_args = list(cmd)
            if args.keep_data:
                mtk_args.append("--keep-data")
            code = run_mtk(mtk_args, args)
    except subprocess.TimeoutExpired:
        print("[RESULT] 0 ATTEMPT_TIMEOUT", flush=True)
        code = FAILED

    if pkg.temp_dir:
        shutil.rmtree(pkg.temp_dir, ignore_errors=True)

    if code == OK:
        print("\n[RESULT] 1 FLASH_OK", flush=True)
        print_post_install(pkg)
        print(
            "Let the player boot on its own before unplugging it if the tool has not "
            "already reset it.",
            flush=True,
        )
        print_donation()
    else:
        print(
            "\n[RESULT] 0 FLASH_FAILED\n"
            "Nothing is confirmed written. Power-cycle the player (unplug, wait, plug in "
            "again while the tool searches) and retry; read "
            "../references/troubleshooting.md for the error the tool reported.",
            flush=True,
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
