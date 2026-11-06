#!/usr/bin/env python3
"""Shared data for the OS-specific install guide pages.

The page generator reads the live software catalogue from
``firmware-catalog.js`` and pairs it with the family copy and platform
profiles below.  Keeping the copy here means a new release of a project does
not require touching the page templates, and a new platform only needs one
entry.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://innioasis.app"

sys.path.insert(0, str(ROOT / "scripts"))
import model_registry  # noqa: E402

MODELS = model_registry.MODELS
MODEL_BY_ID = {model["id"].upper(): model for model in MODELS}
MODEL_BY_SLUG = {model["slug"]: model for model in MODELS}

OS_ORDER = ("windows", "macos", "linux")

OS_PROFILES = {
    "windows": {
        "key": "windows",
        "slug": "windows",
        "label": "Windows",
        "query": "a Windows PC",
        "article": "a Windows PC",
        "anchor": "windows",
        "download": "Download the Innioasis Updater CE installer (<code>installer.exe</code>) from the official GitHub release and run it. If SmartScreen says &ldquo;Windows protected your PC&rdquo;, choose <strong>More info</strong> then <strong>Run anyway</strong> only for the file you just downloaded from <code>github.com/y1-community/Innioasis-Updater</code>.",
        "setup": [
            "Install the MediaTek USB driver with <code>DriverInstall.exe</code>, then restart the PC. The driver is what lets Windows see a powered-off player when Updater CE asks for it.",
            "Use a USB port on the PC itself and a cable that carries data. A charge-only cable or an unpowered hub is the usual reason the player never appears.",
        ],
        "connection": "When Updater CE asks, power the player fully off and plug it into the Windows PC. Device Manager should briefly show a <strong>MediaTek PreLoader USB VCOM</strong> or <strong>MTK USB Port</strong> entry while the player is connected.",
        "troubleshoot": [
            "Updater CE cannot see the player: reinstall <code>DriverInstall.exe</code>, restart Windows, and try another USB port. If Core isolation / Memory integrity is enabled, Windows Security can block the MediaTek driver. Turn it off, reinstall the driver, then turn it back on when you are finished.",
            "The install waits for the device: unplug the cable, power the player off again, click <strong>Install / Restore</strong>, and reconnect only at the fresh prompt.",
            "SmartScreen or antivirus blocks the app: check that the file came from the official <code>y1-community/Innioasis-Updater</code> release, then allow it. Do not run an installer from an untrusted mirror.",
        ],
        "note": "Windows 10 and 11 x64 are the normal targets. ARM64 Windows is experimental.",
        "driver_link": "drivers.html#windows",
        "dl_label": "Download Updater CE for Windows",
        "driver_label": "Download the Windows MediaTek driver",
    },
    "macos": {
        "key": "macos",
        "slug": "mac",
        "label": "macOS",
        "query": "a Mac",
        "article": "a Mac",
        "anchor": "macos",
        "download": "Download the macOS disk image (<code>Innioasis.Updater.for.Mac.dmg</code>), open it, and drag Innioasis Updater CE into <strong>Applications</strong>.",
        "setup": [
            "The first launch is blocked by Gatekeeper until you approve it. Right-click the app and choose <strong>Open</strong>, or open <strong>System Settings &rarr; Privacy &amp; Security</strong> and click <strong>Open Anyway</strong>. Do not disable Gatekeeper for the whole Mac.",
            "No separate USB driver is needed. Connect the player directly to the Mac, not through an unpowered hub; some USB-C adapters drop the connection during a flash.",
        ],
        "connection": "Power the player fully off and connect it only when Updater CE prompts. To confirm the Mac sees it, open <strong>System Information &rarr; USB</strong>, or run <code>system_profiler SPUSBDataType</code> in Terminal and look for a brief MediaTek entry.",
        "troubleshoot": [
            "macOS says the app is damaged or cannot be opened: that is quarantine, not a corrupt download. Approve it in <strong>System Settings &rarr; Privacy &amp; Security</strong> with <strong>Open Anyway</strong>.",
            "The player disconnects during the install: use a direct port, keep the Mac awake, and avoid hubs or adapters. Reconnect only when Updater CE asks.",
            "SP Flash Tool is not available on macOS. Updater CE uses the MTKClient route on a Mac; for manual SP Flash Tool recovery, use a Windows or Linux computer.",
        ],
        "note": "Intel and Apple Silicon Macs are supported. The current guide targets macOS Ventura or later.",
        "driver_link": "drivers.html#macos",
        "dl_label": "Download Updater CE for macOS",
        "driver_label": "macOS setup notes",
    },
    "linux": {
        "key": "linux",
        "slug": "linux",
        "label": "Linux",
        "query": "Linux",
        "article": "a Linux computer",
        "anchor": "linux",
        "download": "Download <code>UpdaterCE.AppImage</code>, make it executable with <code>chmod +x UpdaterCE.AppImage</code>, and run it. The current AppImage targets Intel/AMD x86_64 systems.",
        "setup": [
            "If the AppImage does not start on Ubuntu 22.04 or newer, install <code>libfuse2</code> with your package manager. On Ubuntu 24.04 the package is <code>libfuse2t64</code>. Do not run the app as root.",
            "If Updater CE cannot open the player, add the MediaTek USB permission rule: save <code>SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0e8d\", MODE=\"0666\", GROUP=\"plugdev\"</code> as <code>/etc/udev/rules.d/51-innioasis.rules</code>, then run <code>sudo udevadm control --reload &amp;&amp; sudo udevadm trigger</code>. Add your user to <code>plugdev</code> if needed.",
        ],
        "connection": "Power the player fully off, then connect it only when Updater CE asks. Run <code>lsusb</code> in another terminal to see the MediaTek vendor ID <code>0e8d</code> appear briefly.",
        "troubleshoot": [
            "Permission denied or cannot open the USB port: the udev rule is missing or your user is not in <code>plugdev</code>. Add both, unplug the player, and reconnect.",
            "The AppImage will not launch: check <code>chmod +x</code>, install <code>libfuse2</code> or <code>libfuse2t64</code>, and confirm you are on x86_64. A blank window under Wayland usually means trying an X11 session.",
            "The player is not detected: use a data cable and a direct port, avoid hubs, and connect only at the prompt. Check <code>lsusb</code> while the player is plugged in.",
        ],
        "note": "The official AppImage is for Intel/AMD Linux. No Linux ARM build is listed.",
        "driver_link": "drivers.html#linux",
        "dl_label": "Download Updater CE for Linux",
        "driver_label": "Linux USB permission notes",
    },
}

FAMILIES = {
    "original-software": {
        "key": "original-software",
        "name": "Original Software",
        "h1_name": "Original Software (stock firmware)",
        "action": "restore",
        "aliases": ["stock firmware", "factory firmware", "stock ROM", "original firmware", "restore firmware"],
        "summary": "The factory system image from Innioasis or Timmkoo, used to undo a custom install or recover a player that will not boot.",
        "why": "A stock restore replaces the system with the build the player shipped with. It is the safe way back from Rockbox, Solar, JJ Launcher, Reborn or any other custom system, and it is the first recovery step when an update leaves the player stuck.",
        "preinstall": "Back up music and recordings first. A stock restore replaces the system and can wipe internal storage; the microSD card is normally left alone.",
        "post": "The first start can take a few minutes. Set the language, Wi-Fi and Bluetooth again if the restore cleared them.",
        "restore": "This is the restore path itself: choose Original Software for the model and run Install / Restore.",
        "source": "https://github.com/y1-community/y1-stock-rom",
        "source_label": "y1-community stock firmware archive",
    },
    "reborn": {
        "key": "reborn",
        "name": "Reborn (Y2Linux)",
        "h1_name": "Reborn (Y2Linux / y2reborn)",
        "action": "install",
        "aliases": ["Y2Linux", "Y2 Reborn", "y2reborn", "Reborn Y2", "Y2 Linux", "Reborn OS"],
        "summary": "A Debian-based Linux system with the native Reborn music player for the Innioasis Y2.",
        "why": "Reborn replaces the stock Android system with Linux and a music-first interface. It is the project people search for as y2reborn, Y2Linux or Reborn on Y2.",
        "preinstall": "Reborn is for the Y2 only. Back up the microSD and internal storage; the install replaces the system. Keep a stock Y2 package available for the way back.",
        "post": "After the first start, copy <code>system.img</code> from the stock Y2 package into the <strong>Firmware</strong> folder on Internal Storage to enable Wi-Fi, FM radio and Bluetooth. Follow the Y2 Reborn radio setup guide for the exact steps.",
        "restore": "Restore Original Software for Y2 if you want the stock player back.",
        "source": "https://github.com/schulzcode/y2linux",
        "source_label": "SchulzCode/Y2Linux",
        "post_url": "y2reborn_wifibt.html",
        "post_label": "Y2 Reborn Wi-Fi, FM and Bluetooth setup",
    },
    "rondo": {
        "key": "rondo",
        "name": "Rondo",
        "h1_name": "Rondo",
        "action": "install",
        "aliases": ["Rondo Y1", "Rondo firmware", "Rondo music player"],
        "summary": "A lightweight custom audio system for the Y1 with iPod-style click-wheel menus.",
        "why": "Rondo is built for the Y1's wheel: fast menus, local music and videos, a dashboard, and optional streaming through your own server.",
        "preinstall": "Rondo is for the Y1 Type A only (players that shipped with software 2.0.0 or later). Do not install it on a Type B Y1 or a Y2.",
        "post": "The first start takes a couple of minutes. For YouTube Music and YouTube, set up a Rondo server; the card, radio and Bluetooth work without one.",
        "restore": "Restore Original Software for Y1 if you want the stock player back.",
        "source": "https://github.com/jarvissax/rondo",
        "source_label": "jarvissax/rondo",
    },
    "rockbox": {
        "key": "rockbox",
        "name": "Rockbox",
        "h1_name": "Rockbox",
        "action": "install",
        "aliases": ["Rockbox-Y1", "Rockbox-Y2", "Rockbox for Y1", "Rockbox for Y2", "Rockbox firmware"],
        "summary": "Music-first custom firmware with a tag database, gapless playback, EQ, themes and plugins.",
        "why": "Rockbox is the long-running community firmware for both Y1 and Y2. It adds a real music database, gapless playback, a graphic equalizer, themes and a large plugin set.",
        "preinstall": "Use the build for this exact model. Rockbox-Y1 and Rockbox-Y2 are separate packages. On a Y1, check whether the player is Type A or Type B before you pick the asset.",
        "post": "On first start, let Rockbox scan the microSD card. Themes and settings live on the card, so keep a copy before you change cards.",
        "restore": "Restore Original Software for the same model if you want the stock player back.",
        "source": "https://github.com/rockbox-y1/rockbox",
        "source_label": "rockbox-y1/rockbox and spycemagic/y2-rockbox",
    },
    "solar": {
        "key": "solar",
        "name": "Solar",
        "h1_name": "Solar",
        "action": "install",
        "aliases": ["Solar Y1", "Solar Y2", "Solar firmware", "Solar music player"],
        "summary": "A network-first custom system with podcasts, YouTube, streaming and a global quick menu.",
        "why": "Solar turns the player into a connected music device while keeping the local library. It is listed for both Y1 and Y2, with separate builds and feature sets.",
        "preinstall": "Check the release notes for the model you have: Solar features differ between Y1 and Y2. Keep a stock package ready because this is a full system replacement.",
        "post": "Connect to Wi-Fi after the first boot and sign in to the services you use. Podcasts and streaming need a working network.",
        "restore": "Restore Original Software for the same model if you want the stock player back.",
        "source": "https://github.com/thesolarproject/solar",
        "source_label": "thesolarproject/solar",
    },
    "jj-launcher": {
        "key": "jj-launcher",
        "name": "JJ Launcher",
        "h1_name": "JJ Launcher",
        "action": "install",
        "aliases": ["JJLauncher", "JJ launcher", "y1_launcher", "JJ Launcher Y1", "JJ Launcher Y2"],
        "summary": "A fast, wheel-friendly home screen replacement for the Y1 and Y2.",
        "why": "JJ Launcher keeps the player's music-first flow but makes the home screen quicker to move around with the wheel, with hardware-key shortcuts and wireless uploads.",
        "preinstall": "Choose the build that matches the model. The Y1 package is not the Y2 package, even when both entries share the same project name.",
        "post": "Set your preferred home layout after the first boot. Your music library stays on the card.",
        "restore": "Restore Original Software for the same model if you want the stock home screen back.",
        "source": "https://github.com/ismileblue/y1_launcher",
        "source_label": "ismileblue/y1_launcher",
    },
    "inniclassic": {
        "key": "inniclassic",
        "name": "Inniclassic",
        "h1_name": "Inniclassic (iPod Classic interface)",
        "action": "install",
        "aliases": ["InniClassic", "Inni Classic", "iPod Classic firmware", "Classic Y1", "Classic Y2"],
        "summary": "An iPod Classic-style interface for the Innioasis Y1 and Y2.",
        "why": "Inniclassic recreates the click-wheel Classic experience with modern fixes: dual-storage library scanning, a microSD watchdog, FM radio support and lower headphone gain.",
        "preinstall": "The Y1 and Y2 builds come from separate release lines. Never cross-flash them, and pick the Type B asset if you have an early Y1.",
        "post": "The first boot may take longer while the library indexes. Let the scan finish before you judge performance.",
        "restore": "Restore Original Software for the same model if you want the stock interface back.",
        "source": "https://github.com/FabianZettl/inniclassic",
        "source_label": "FabianZettl/inniclassic and JonaszPotoniec/inniclassic-y2",
    },
    "y2player": {
        "key": "y2player",
        "name": "Y2Player",
        "h1_name": "Y2Player",
        "action": "install",
        "aliases": ["Y2 Player", "Y2Player firmware", "Y2 Player firmware"],
        "summary": "A music-first home screen for the Innioasis Y2.",
        "why": "Y2Player is built around local playback: a simple home screen, quick access to the library and fewer distractions than the stock Android interface.",
        "preinstall": "Y2Player is Y2-only. Back up first; it replaces the system.",
        "post": "Let the library scan finish before judging the first start.",
        "restore": "Restore Original Software for Y2 if you want the stock interface back.",
        "source": "https://github.com/schulzcode/Y2Player",
        "source_label": "schulzcode/Y2Player",
    },
    "koensayr": {
        "key": "koensayr",
        "name": "Koensayr",
        "h1_name": "Koensayr",
        "action": "install",
        "aliases": ["Koensayr Y1", "Koensayr Auto", "Koensayr firmware"],
        "summary": "A stock-derived Y1 patch that adds Artist-to-Album navigation and root while keeping the stock feel.",
        "why": "Koensayr improves the stock Y1 software instead of replacing it: Artist-to-Album navigation, a root option and a small set of audio patches.",
        "preinstall": "Koensayr is a Y1 build based on stock firmware. Check the supported stock version in the release notes before you start.",
        "post": "Open the post-install notes for the extra patch options and the first-start checks.",
        "restore": "Restore Original Software for Y1 if you want the untouched stock software back.",
        "source": "https://github.com/ryan-specter/koensayr-auto",
        "source_label": "ryan-specter/koensayr-auto",
    },
    "better-y": {
        "key": "better-y",
        "name": "Better-Y",
        "h1_name": "Better-Y",
        "action": "install",
        "aliases": ["Better Y", "BetterY", "Better-Y Y1"],
        "summary": "A polished stock-based Y1 system with metadata fixes, caching and Now Playing controls.",
        "why": "Better-Y keeps the stock player familiar while adding track numbers, multi-artist and genre tag splitting, interactive Now Playing controls and memory caching.",
        "preinstall": "Better-Y releases are Y1 Type A packages. Do not flash them on a Type B Y1; use Rockbox-Y1 Type B for early units.",
        "post": "No extra setup is needed for the core features. Check the release notes for the stock version it builds on.",
        "restore": "Restore Original Software for Y1 if you want the stock software back.",
        "source": "https://github.com/Leska1337/better-Y",
        "source_label": "Leska1337/better-Y",
    },
    "android-dev": {
        "key": "android-dev",
        "name": "Android development ROM",
        "h1_name": "Android 4.2 / 4.4 development ROM",
        "action": "install",
        "aliases": ["Android 4.2", "Android 4.4", "Android dev ROM", "ATA ROM", "Innioasis Android"],
        "summary": "A development Android image for testing, not a daily-driver system.",
        "why": "The Android development images are the base ROMs used by firmware projects. They are useful for testing and recovery work, not for everyday listening.",
        "preinstall": "This is a development build. Expect missing features, and keep a stock restore package ready before you flash.",
        "post": "Boot may take longer. Reinstall Original Software when you finish testing.",
        "restore": "Restore Original Software for the same model when you are done testing.",
        "source": "https://github.com/y1-community/y1-ata-rom",
        "source_label": "y1-community ATA ROM projects",
    },
    "linux-dev": {
        "key": "linux-dev",
        "name": "Linux for Y1 (Dev)",
        "h1_name": "Linux for Y1 (Dev)",
        "action": "install",
        "aliases": ["Linux for Y1", "Y1 Linux", "Linux dev ROM"],
        "summary": "A development Linux image for the Innioasis Y1.",
        "why": "Linux for Y1 is an early development build that explores a Linux userspace on the Y1 hardware. It is for testing, not for a finished daily-driver experience.",
        "preinstall": "This is an early development build. Keep a stock restore ready and expect rough edges.",
        "post": "Expect missing features and occasional instability. Reinstall Original Software when you finish testing.",
        "restore": "Restore Original Software for Y1 when you are done testing.",
        "source": "https://github.com/y1-community/y1-linux-rom",
        "source_label": "y1-community/y1-linux-rom",
    },
}


def _json_array(text: str, marker: str) -> list:
    start = text.index("[", text.index(marker))
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:index + 1])
    raise ValueError("unterminated JSON array after %s" % marker)


def load_catalog() -> list[dict]:
    text = (ROOT / "firmware-catalog.js").read_text(encoding="utf-8")
    return _json_array(text, "window.INNIOASIS_FIRMWARE_CATALOG =")


CATALOG = load_catalog()


SLUG_ALIASES = {"linux-y1": "linux-dev"}


def family_key_for_slug(slug: str) -> str:
    if slug in SLUG_ALIASES:
        return SLUG_ALIASES[slug]
    if slug.startswith("original-"):
        return "original-software"
    if slug.startswith("android-"):
        return "android-dev"
    for key in FAMILIES:
        if slug == key or slug.startswith(key + "-"):
            return key
    raise KeyError("no family for software slug %r" % slug)


def family_for_slug(slug: str) -> dict:
    return FAMILIES[family_key_for_slug(slug)]


def family_items(key: str) -> list[dict]:
    return [item for item in CATALOG if family_key_for_slug(item["slug"]) == key]


def model_items(model_id: str) -> list[dict]:
    wanted = str(model_id).upper()
    return [item for item in CATALOG if str(item.get("model") or "").upper() == wanted]


def model_for(model_id: str) -> dict:
    return MODEL_BY_ID[str(model_id).upper()]


def display_model(model_id: str) -> str:
    return model_registry.display_name(model_for(model_id))


def model_description(model_id: str) -> str:
    return model_for(model_id).get("description") or ""


def deep_name(slug: str, os_key: str) -> str:
    return "%s-%s.html" % (slug, OS_PROFILES[os_key]["slug"])


def family_os_name(key: str, os_key: str) -> str:
    return "%s-%s.html" % (key, OS_PROFILES[os_key]["slug"])


def family_name(key: str) -> str:
    return "%s.html" % key


def model_os_name(model_id: str, os_key: str) -> str:
    model = model_for(model_id)
    return "%s-%s.html" % (model["slug"], OS_PROFILES[os_key]["slug"])


def model_hub_name(model_id: str) -> str:
    return "%s.html" % model_for(model_id)["slug"]


def platform_name(os_key: str) -> str:
    return "%s.html" % OS_PROFILES[os_key]["slug"]


def deep_url(slug: str, os_key: str) -> str:
    return SITE + "/install/" + deep_name(slug, os_key)


def family_os_url(key: str, os_key: str) -> str:
    return SITE + "/install/" + family_os_name(key, os_key)


def family_url(key: str) -> str:
    return SITE + "/install/" + family_name(key)


def model_os_url(model_id: str, os_key: str) -> str:
    return SITE + "/install/" + model_os_name(model_id, os_key)


def model_hub_url(model_id: str) -> str:
    return SITE + "/install/" + model_hub_name(model_id)


def platform_url(os_key: str) -> str:
    return SITE + "/install/" + platform_name(os_key)


def model_software(model_id: str) -> list[dict]:
    """Every catalog entry for a model, with the family metadata attached."""
    result = []
    for item in model_items(model_id):
        entry = dict(item)
        entry["family"] = family_for_slug(item["slug"])
        result.append(entry)
    return result


def aliases_sentence(family: dict) -> str:
    aliases = family.get("aliases") or []
    if not aliases:
        return ""
    return "People also search for %s; this is the same %s install." % (
        ", ".join(aliases[:4]),
        family["name"],
    )


def type_note(model_id: str, family: dict | None = None) -> str:
    if str(model_id).upper() != "Y1":
        return ""
    if family and family["key"] == "better-y":
        return "Better-Y is a Type A build. If your Y1 is Type B, use the Rockbox-Y1 Type B route instead."
    return "Y1 players shipped in two hardware revisions. Players that shipped with software 2.0.0 or later are Type A; earlier units are Type B. Pick the matching asset in Updater CE."
