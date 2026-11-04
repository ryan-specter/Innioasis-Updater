#!/usr/bin/env python3
"""Innioasis Updater 2.0.8 — the handover to the rewritten app.

This is the last release of the legacy updater. It no longer downloads
firmware or shows a firmware list. It fetches the rewritten Innioasis Updater
for the user's OS and architecture, hands it over in Downloads, and quietly
clears what it can of the old installation before quitting.

Kept deliberately small: PySide6 and requests only, both already shipped with
the legacy app.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import requests
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

APP_VERSION = "2.0.8"

APP_NAME = "Innioasis Updater"
GUIDE_URL = "https://innioasis.app"
API_RELEASES = "https://api.github.com/repos/{repo}/releases?per_page=30"
PRIMARY_REPO = "y1-community/innioasis-updater"
PORTABLE_REPO = "y1-community/updater-ce-neo"
USER_AGENT = f"InnioasisUpdater/{APP_VERSION} (+https://innioasis.app)"
REQUEST_TIMEOUT = (10, 60)
# The handover only trusts a legacy-repo release that is at least this new, so
# an older legacy release can never be downloaded as if it were the rewrite.
MIN_LEGACY_TAG = (2, 0, 8)

RETIRED_TITLE = "This version has retired."
RETIRED_BODY = (
    "This version of Innioasis Updater has been retired. Head to "
    "www.innioasis.app to download the new and improved version."
)

# Anything the running Python or the launcher needs. Never touched.
_PROTECTED_DIRS = {
    ".git",
    "lib",
    "libs",
    "lib64",
    "dlls",
    "winpython",
    "venv",
    ".venv",
    "site-packages",
    "scripts",
    "include",
    "tcl",
    "tk",
    "platform-tools",
    "node_modules",
    ".cache",
}
_PROTECTED_SUFFIXES = {".exe", ".dll", ".pyd", ".so", ".dylib", ".msi", ".sys"}
_PROTECTED_FILES = {"qt.conf", "pyvenv.cfg", "python._pth"}

_LEGACY_SHORTCUTS = (
    "Innioasis Updater.lnk",
    "Innioasis Toolkit.lnk",
    "Recover Firmware Install.lnk",
    "Recover Firmware Install - SP Flash Tool.lnk",
    "Rockbox 240p Theme Downloader.lnk",
    "Rockbox 360p Theme Downloader.lnk",
    "MTKclient.lnk",
)


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------


def platform_name() -> str:
    system = platform.system()
    if system == "Windows":
        return "Windows"
    if system == "Darwin":
        return "macOS"
    return "Linux"


def architecture() -> str:
    machine = (platform.machine() or "").lower()
    if machine in ("arm64", "aarch64", "armv8l"):
        return "arm64"
    return "x64"


def downloads_dir() -> Path:
    home = Path.home()
    target = home / "Downloads"
    if platform_name() == "Linux":
        xdg = os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))
        try:
            for line in (Path(xdg) / "user-dirs.dirs").read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                if line.startswith("XDG_DOWNLOAD_DIR="):
                    value = line.split("=", 1)[1].strip().strip('"')
                    value = value.replace("$HOME", str(home))
                    if value:
                        target = Path(value)
                    break
        except OSError:
            pass
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        target = home
    return target


def _mb(value: float) -> str:
    return f"{value / (1024 * 1024):.1f} MB"


def _pick_asset(assets, plat: str, arch: str, portable: bool = False):
    """Best asset for this OS and architecture, or None."""
    best = None
    best_score = -1
    for asset in assets:
        name = (asset.get("name") or "").strip()
        low = name.lower()
        url = asset.get("browser_download_url") or ""
        if not url:
            continue

        score = None
        if portable:
            if not low.endswith(".zip") or "portable" not in low:
                continue
            score = 100
            if arch == "arm64":
                if "arm64" not in low and "aarch64" not in low:
                    continue
                score += 40
            elif "arm" in low:
                continue
            if "linux" in low:
                score += 10
        elif plat == "Windows":
            if not low.endswith(".exe") or "installer" not in low:
                continue
            if "uninstall" in low:
                continue
            score = 100
            if arch == "arm64":
                if "arm64" in low or "aarch64" in low:
                    score += 40
            elif "arm" not in low:
                score += 20
            if low == "installer.exe":
                score += 30
        elif plat == "macOS":
            if not low.endswith(".dmg"):
                continue
            score = 100
            if arch == "arm64":
                if "arm64" in low or "aarch64" in low or "universal" in low:
                    score += 30
            elif "arm" in low:
                continue
            if low == "innioasis.updater.for.mac.dmg":
                score += 30
        elif plat == "Linux":
            if not low.endswith(".appimage"):
                continue
            score = 100
            if arch == "arm64":
                if "arm64" not in low and "aarch64" not in low:
                    continue
                score += 40
            else:
                if "arm" in low:
                    continue
                score += 20
            if "updaterce" in low:
                score += 10
        else:
            continue

        if score > best_score:
            best_score = score
            best = {
                "name": name,
                "url": url,
                "size": int(asset.get("size") or 0),
            }
    return best


def _release_version(tag: str):
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", tag or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def find_release_asset(portable: bool = False):
    """Latest release that ships an asset for this machine."""
    plat, arch = platform_name(), architecture()
    repos = (PORTABLE_REPO, PRIMARY_REPO) if portable else (PRIMARY_REPO, PORTABLE_REPO)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    for repo in repos:
        try:
            response = requests.get(
                API_RELEASES.format(repo=repo), headers=headers, timeout=REQUEST_TIMEOUT
            )
            if response.status_code != 200:
                continue
            releases = response.json()
        except (requests.RequestException, ValueError):
            continue
        if not isinstance(releases, list):
            continue
        for release in releases:
            if not isinstance(release, dict) or release.get("draft"):
                continue
            if repo == PRIMARY_REPO:
                version = _release_version(release.get("tag_name") or "")
                if version is None or version < MIN_LEGACY_TAG:
                    continue
            asset = _pick_asset(release.get("assets") or [], plat, arch, portable)
            if asset:
                asset["tag"] = release.get("tag_name") or ""
                return asset
    return None


def reveal_in_file_manager(path: Path) -> None:
    """Show the downloaded file. Failures are silent."""
    try:
        if platform_name() == "Windows":
            subprocess.Popen(
                ["explorer", f"/select,{path}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        if platform_name() == "macOS":
            try:
                subprocess.Popen(
                    ["open", "-R", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).wait(timeout=5)
            except Exception:
                subprocess.Popen(["open", str(path.parent)])
            return
        if platform_name() == "Linux":
            revealed = False
            try:
                shown = subprocess.Popen(
                    [
                        "dbus-send",
                        "--session",
                        "--dest=org.freedesktop.FileManager1",
                        "--type=method_call",
                        "/org/freedesktop/FileManager1",
                        "org.freedesktop.FileManager1.ShowItems",
                        f"array:string:{path.resolve().as_uri()}",
                        "string:",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                revealed = shown.wait(timeout=3) == 0
            except Exception:
                pass
            if not revealed:
                subprocess.Popen(
                    ["xdg-open", str(path.parent)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Legacy clean-up
# ---------------------------------------------------------------------------


def _protected_dir(path: Path) -> bool:
    name = path.name.lower()
    if name in _PROTECTED_DIRS or name.startswith("python"):
        return True
    try:
        if (path / "python.exe").is_file() or (path / "python3").is_file():
            return True
        if (path / "Lib" / "site-packages").is_dir():
            return True
    except OSError:
        pass
    return False


def _purge_dir(path: Path, keep_name: str) -> None:
    if _protected_dir(path):
        return
    try:
        entries = list(path.iterdir())
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_symlink():
                entry.unlink()
            elif entry.is_dir():
                _purge_dir(entry, keep_name)
            elif entry.name == keep_name or entry.name.lower() in _PROTECTED_FILES:
                continue
            elif entry.suffix.lower() in _PROTECTED_SUFFIXES:
                continue
            else:
                entry.unlink()
        except OSError:
            pass
    try:
        path.rmdir()
    except OSError:
        pass


def _remove_shortcuts(root: Path) -> None:
    home = Path.home()
    targets = []
    if platform_name() == "Windows":
        bases = [
            home / "Desktop",
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs",
            Path(os.environ.get("PROGRAMDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs",
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup",
        ]
        for base in bases:
            if not str(base):
                continue
            for name in _LEGACY_SHORTCUTS:
                targets.append(base / name)
            # Any shortcut that points at this install, whatever it was named.
            try:
                links = list(base.rglob("*.lnk"))[:300]
            except OSError:
                links = []
            for link in links:
                try:
                    blob = link.read_bytes()[:1_000_000].lower()
                    if (
                        str(root).lower().encode("utf-16-le") in blob
                        or str(root).lower().encode("utf-8") in blob
                    ):
                        targets.append(link)
                except OSError:
                    pass
    elif platform_name() == "Linux":
        targets = [
            home / ".local" / "share" / "applications" / "innioasis-updater.desktop",
            home / "Desktop" / "innioasis-updater.desktop",
            home / ".local" / "bin" / "innioasis-updater",
            home / ".config" / "autostart" / "innioasis-updater.desktop",
        ]
    for target in targets:
        try:
            if target.is_file() or target.is_symlink():
                target.unlink()
        except OSError:
            pass


def clean_legacy_install() -> None:
    """Delete what the old app left behind. Never raises, never nags."""
    try:
        root = Path(__file__).resolve().parent
        if (root / ".git").exists():
            return
        markers = ("firmware_downloader.py", "updater.py", "test.py", "config.ini")
        if not any((root / marker).exists() for marker in markers):
            return
        keep_name = Path(__file__).name
        for entry in list(root.iterdir()):
            try:
                if entry.is_dir():
                    _purge_dir(entry, keep_name)
                elif entry.name == keep_name or entry.name.lower() in _PROTECTED_FILES:
                    continue
                elif entry.suffix.lower() in _PROTECTED_SUFFIXES:
                    continue
                else:
                    entry.unlink()
            except OSError:
                pass
        _remove_shortcuts(root)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Download worker
# ---------------------------------------------------------------------------


class DownloadWorker(QThread):
    status = Signal(str)
    progress = Signal(int, str)
    done = Signal(bool, str, str)  # ok, path-or-reason, mode

    def __init__(self, portable: bool = False, remove_first: str = ""):
        super().__init__()
        self.portable = portable
        self.remove_first = remove_first
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        mode = "portable" if self.portable else "app"
        self.status.emit("Finding the latest version…")
        asset = find_release_asset(portable=self.portable)
        if not asset:
            self.done.emit(False, "unavailable", mode)
            return

        destination = downloads_dir() / asset["name"]
        temporary = destination.with_name(destination.name + ".part")
        self.status.emit(f"Downloading {asset['name']}")

        try:
            with requests.get(
                asset["url"],
                stream=True,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            ) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length") or asset["size"] or 0)
                received = 0
                started = time.monotonic()
                window = []
                last_emit = 0.0
                with open(temporary, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=131072):
                        if self._stop:
                            break
                        if not chunk:
                            continue
                        handle.write(chunk)
                        received += len(chunk)
                        now = time.monotonic()
                        window.append((now, received))
                        while len(window) > 2 and now - window[0][0] > 2.0:
                            window.pop(0)
                        if now - last_emit < 0.1:
                            continue
                        last_emit = now
                        elapsed = max(window[-1][0] - window[0][0], 0.001)
                        speed = (window[-1][1] - window[0][1]) / elapsed if len(window) > 1 else 0
                        if total > 0:
                            percent = min(99, int(received * 100 / total))
                            detail = (
                                f"{_mb(received)} of {_mb(total)}"
                                + (f" · {_mb(speed)}/s" if speed > 0 else "")
                            )
                        else:
                            percent = 0
                            detail = _mb(received) + (f" · {_mb(speed)}/s" if speed > 0 else "")
                        self.progress.emit(percent, detail)
            if self._stop:
                temporary.unlink(missing_ok=True)
                self.done.emit(False, "cancelled", mode)
                return
            if not temporary.is_file() or temporary.stat().st_size == 0:
                temporary.unlink(missing_ok=True)
                self.done.emit(False, "unavailable", mode)
                return
            os.replace(temporary, destination)
            if self.remove_first:
                try:
                    Path(self.remove_first).unlink()
                except OSError:
                    pass
            self.progress.emit(100, "")
            self.done.emit(True, str(destination), mode)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            self.done.emit(False, "unavailable", mode)


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------


class HandoverWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.handover_ok = False
        self.closing = False
        self.downloaded = ""
        self.setWindowTitle(APP_NAME)
        self.setFixedWidth(500)
        self.setStyleSheet(
            """
            QWidget { background: #0b0f14; color: #e5e7eb; }
            QLabel#kicker { color: #34d399; font-size: 11px; font-weight: 700;
                            letter-spacing: 1.6px; }
            QLabel#title { color: #f8fafc; font-size: 21px; font-weight: 700; }
            QLabel#body { color: #94a3b8; font-size: 13px; }
            QLabel#detail { color: #64748b; font-size: 11px; }
            QProgressBar { background: #16202b; border: 0; border-radius: 3px;
                           height: 6px; }
            QProgressBar::chunk { background: #34d399; border-radius: 3px; }
            QPushButton { background: #34d399; color: #06231a; border: 0;
                          border-radius: 8px; padding: 9px 18px; font-size: 12px;
                          font-weight: 700; }
            QPushButton:hover { background: #6ee7b7; }
            QPushButton#quiet { background: transparent; color: #94a3b8;
                                font-weight: 600; }
            QPushButton#quiet:hover { color: #e5e7eb; }
            """
        )
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 26)
        layout.setSpacing(10)

        self.kicker = QLabel("INNIOASIS UPDATER")
        self.kicker.setObjectName("kicker")
        self.title = QLabel("Grabbing the all-new Innioasis Updater for you.")
        self.title.setObjectName("title")
        self.title.setWordWrap(True)
        self.body = QLabel(
            f"Downloading the latest version for {platform_name()}. "
            "It only takes a moment."
        )
        self.body.setObjectName("body")
        self.body.setWordWrap(True)
        self.body.setMinimumHeight(40)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.detail = QLabel(" ")
        self.detail.setObjectName("detail")

        self.footer = QHBoxLayout()
        self.footer.setSpacing(8)
        self.zip_link = QLabel(
            '<a href="zip" style="color:#34d399;text-decoration:none;">'
            "Prefer the app as a .zip?</a>"
        )
        self.zip_link.setTextFormat(Qt.RichText)
        self.zip_link.linkActivated.connect(self._wants_zip)
        self.zip_link.hide()
        self.primary = QPushButton("Quit")
        self.primary.setObjectName("quiet")
        self.primary.clicked.connect(self.close)
        self.footer.addWidget(self.zip_link)
        self.footer.addStretch(1)
        self.footer.addWidget(self.primary)

        layout.addWidget(self.kicker)
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        layout.addSpacing(6)
        layout.addWidget(self.progress)
        layout.addWidget(self.detail)
        layout.addSpacing(6)
        layout.addLayout(self.footer)

        self._set_icon()

    def _set_icon(self):
        for name in ("icon.ico", "y1_illustration.png"):
            icon = Path(__file__).resolve().with_name(name)
            if icon.is_file():
                self.setWindowIcon(QIcon(str(icon)))
                break

    def _center(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geometry = screen.availableGeometry()
        self.adjustSize()
        self.move(
            geometry.center().x() - self.width() // 2,
            geometry.center().y() - self.height() // 2,
        )

    def start(self):
        QTimer.singleShot(0, self._begin)

    def _begin(self):
        self._center()
        self.worker = DownloadWorker()
        self.worker.status.connect(self._on_status)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_status(self, text: str):
        self.detail.setText(text)

    def _on_progress(self, percent: int, text: str):
        self.progress.setRange(0, 100)
        self.progress.setValue(percent)
        if text:
            self.detail.setText(text)

    def _show_success(self, path: Path, mode: str):
        reveal_in_file_manager(path)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.kicker.setText("DOWNLOAD COMPLETE")
        self.title.setText("You're all set.")
        self.detail.setText(f"Saved to {path.parent}")
        self.primary.setText("Quit")
        self.primary.setObjectName("quiet")
        self.primary.style().unpolish(self.primary)
        self.primary.style().polish(self.primary)
        try:
            self.primary.clicked.disconnect()
        except RuntimeError:
            pass
        self.primary.clicked.connect(self.close)

        lower = path.name.lower()
        if mode == "portable" or lower.endswith(".zip"):
            self.body.setText(
                f"Your download is in Downloads. Unzip {path.name}, then open "
                "Innioasis Updater from the folder."
            )
            self.zip_link.hide()
        elif lower.endswith(".dmg"):
            self.body.setText(
                f"Your download is in Downloads. Open {path.name}, then drag "
                "Innioasis Updater into Applications."
            )
            self.zip_link.hide()
        else:
            self.body.setText(
                f"Your download is in Downloads. Right-click {path.name} → "
                "Properties → Permissions → Allow executing file as program, "
                "then double-click it."
            )
            if platform_name() == "Linux" and "arm" not in lower:
                self.zip_link.show()

    def _on_done(self, ok: bool, payload: str, mode: str):
        if self.closing:
            return
        if not ok:
            if payload == "cancelled":
                self.close()
            elif mode == "portable" and self.downloaded:
                self._show_success(Path(self.downloaded), "app")
                self.body.setText(
                    "The .zip isn't available right now, so your AppImage is "
                    "still in Downloads and ready to run."
                )
            else:
                self._show_retired()
            return

        self.downloaded = payload
        self.handover_ok = True
        path = Path(payload)

        if platform_name() == "Windows":
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            self.detail.setText("Starting the installer…")
            self.title.setText("Up and running in a moment.")
            self.body.setText(
                "The new Innioasis Updater installer is starting. "
                "Follow it to finish, then open the app from your Start menu."
            )
            QTimer.singleShot(700, self._run_windows_installer)
            return

        self._show_success(path, mode)

    def _run_windows_installer(self):
        try:
            os.startfile(self.downloaded)  # type: ignore[attr-defined]
            QTimer.singleShot(500, self.close)
        except Exception:
            reveal_in_file_manager(Path(self.downloaded))
            self.title.setText("The installer is ready.")
            self.body.setText(
                "Open installer.exe from your Downloads folder to finish "
                "installing the new Innioasis Updater."
            )
            self.handover_ok = False
            self.primary.setText("Quit")
            try:
                self.primary.clicked.disconnect()
            except RuntimeError:
                pass
            self.primary.clicked.connect(self.close)

    def _wants_zip(self):
        if self.worker and self.worker.isRunning():
            return
        self.zip_link.hide()
        self.kicker.setText("PORTABLE DOWNLOAD")
        self.title.setText("Getting the .zip instead.")
        self.body.setText("Replacing the AppImage with the portable .zip…")
        self.progress.setRange(0, 0)
        self.detail.setText("Finding the latest version…")
        self.worker = DownloadWorker(portable=True, remove_first=self.downloaded)
        self.worker.status.connect(self._on_status)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _show_retired(self):
        self.progress.hide()
        self.detail.hide()
        self.zip_link.hide()
        self.kicker.setText("INNIOASIS UPDATER")
        self.title.setText(RETIRED_TITLE)
        self.body.setText(RETIRED_BODY)
        self.primary.setText("Open innioasis.app")
        self.primary.setObjectName("")
        self.primary.style().unpolish(self.primary)
        self.primary.style().polish(self.primary)
        try:
            self.primary.clicked.disconnect()
        except RuntimeError:
            pass
        self.primary.clicked.connect(self._open_site)
        self._center()

    def _open_site(self):
        try:
            webbrowser.open(GUIDE_URL)
        except Exception:
            pass
        self.close()

    def closeEvent(self, event):
        if not self.closing:
            self.closing = True
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(2000)
            if self.handover_ok:
                clean_legacy_install()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    window = HandoverWindow()
    window.show()
    window.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
