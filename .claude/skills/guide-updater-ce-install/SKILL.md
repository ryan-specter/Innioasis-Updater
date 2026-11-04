---
name: guide-updater-ce-install
description: >-
  Walk a user step by step through installing firmware on an Innioasis Y1/Y2,
  Timmkoo or other MediaTek player with the Innioasis Updater CE app or a portable
  ROM.zip package and its bundled GUIs. Use when the user wants to be guided rather
  than have the flash automated, is installing the app itself, is stuck on a screen or
  error card, or asks what a button or prompt in the updater means.
license: See LICENSE in the repository root.
metadata:
  ecosystem: innioasis-community
  skill-version: "1.0"
  upstream: https://github.com/y1-community/updater-ce-neo
---

# Guide a user through Updater CE

Use this when the flash should happen **in the app with the user driving**, or
when automation is blocked (no shell, no permissions, a locked-down machine).
For an unattended install, use `../flash-innioasis-device/SKILL.md` instead.

Your job: get the right app, the right package and the right order of clicks,
then read the app's own error card back to the user and act on it.

## 1. Get the app on the right machine

Downloads are per platform and per architecture; names are fixed
(`docs/RELEASE_FILES.md`):

| Host | File |
|---|---|
| Windows x64 | `installer.exe` (or `UpdaterCE-Windows-Portable.zip`) |
| macOS (Universal 2) | `Innioasis.Updater.for.Mac.dmg` |
| Linux x86-64 | `UpdaterCE.appimage` (or `UpdaterCE-Linux-Portable.tar.gz`) |
| Linux arm64 | `UpdaterCE-arm64.appimage` |

Releases are staggered: a newer tag without a file for the machine means "stay
on the previous release", not "build it yourself". A release's zip is offered
as the portable package for the reader's platform where a mirror exists.

Install notes to state plainly:

- **Windows**: the installer needs admin; the MediaTek PreLoader VCOM driver
  must be installed (the app's settings page links the driver guide). Do not
  install Zadig/WinUSB over the preloader port.
- **macOS**: no SP Flash Tool; the app uses MTKClient in-process. Drag the app
  to Applications, then launch it from there.
- **Linux**: make the AppImage executable, or use the portable tar.gz if FUSE
  is missing. The user needs `dialout`/`uucp` membership; the app stages SP
  Flash Tool and the udev rules itself on first run.

## 2. Choose the firmware the user actually wants

The catalogue is `https://innioasis.app/slidia_manifest.xml`; the app also
ships a snapshot so a fresh offline install still lists releases. Ask which
they want, or infer from their goal:

| Goal | Typical release |
|---|---|
| restore/repair a player | **Original Software** (stock) |
| music-first player | **Rockbox** (+ themes/fonts pack) |
| modern UI / network features | **Solar**, **Inniclassic**, **Y2Player** |
| Linux on the player | **Reborn (Y2Linux)**, **Linux for Y1 (Dev)** |
| Android base for hacking | **Android 4.2 (Dev)** Y1, **Android 4.4 (Dev)** Y2 |

The package must match the player and its variant: Y1 **Type A / Type B** have
different scatters, and Rockbox has 360p and 240p builds. If the user is not
sure, ask them to read the model off the back of the player.

## 3. Portable ROM.zip route (no catalogue, no account)

Best when the user already has a downloaded release:

1. Unzip the package **with the app inside it** (or put the app and the
   `Firmware/` folder side by side). Windows/Linux packs keep the ROM beside a
   copy of `SP_Flash_Tool`; macOS packs use a `Firmware/` folder next to the
   `.app`.
2. Launch the app from inside that folder. It detects the single scatter (and
   `fw_package.ini` if present), fills in the software name/version/model, stages
   only the declared images, and opens **Install Software** — no file picking.
3. Confirm the release name and model shown in the card before continuing.

Dragging a `.zip`/`.rar`/folder onto the app window works too, and a browsed
local package behaves the same. `fw_package.ini` is optional; the app infers
the model from the scatter when it is absent.

## 4. The install, screen by screen

1. **Select Software** → pick the release, then **Install**.
2. **Install Software** → the card lists what will be written. Offer
   **Keep my data** when the package supports it (same firmware family /
   derivative). Do not offer it across unrelated firmwares.
3. The card asks the user to **power the player off and connect it** — say the
   order out loud: powered off first, plugged in only when the app is asking.
4. Progress runs: extract → detect → download DA → write partitions → verify.
   Expect a few minutes; user storage is the long partition.
5. On success the completion card names the software and model, may offer
   **Install This App** (portable runs) and shows the donation appeal.

Never promise that "connected" means "flashing": the card only moves on when
the tool reports the player.

## 5. When the user is stuck

| They see | Say / do |
|---|---|
| "Waiting for device" forever | player was on or plugged in too early: unplug, power off, reconnect while the app searches |
| SP Flash Tool 1013 / 2005 | driver or ordering problem — same replay as above; check the VCOM driver |
| "Wrong model" card | stop; the package does not match the player |
| USB lost mid-write | do not touch anything; reconnect when asked, then retry the install |
| Install failed, retry offered | retry the same engine once, then let the app fail over to the other back end |
| Progress stuck at 99% | extraction finished; the card is about to move to the connect step |
| Themes card waiting for power-on | the themes/fonts transfer needs the player on; do not close the app |

Two real failures in a row is where the app offers the **other** install method
(MTKClient ⇄ SP Flash Tool). Advanced Settings (the `M` / `D` shortcuts, or the
Advanced switch) exposes the backend choice, the SP Flash Tool GUI handoff, and
a **terminal install** that opens the exact command in a terminal — useful when
the user wants to watch the tool or paste output for support.

Diagnostics live in the app's **Diagnostics** section: install log, SP Flash
Tool's internal `QT_FLASH_TOOL.log` tail, and environment facts. Ask for that
export rather than guessing.

## 6. Finish and close out

1. Post-install: open the release's `post_install` page when the catalogue
   declares one (Reborn: Wi-Fi/Bluetooth enablement; Rondo: first-start guide).
2. Rockbox: mention the themes/fonts stage, and that a 240p build takes the
   theme-site note instead of the bundled pack.
3. Tell them what changed and what a first boot looks like.
4. Portable runs clean up after themselves on close (staged images, caches) and
   leave their original files alone.

## 7. Donation ask

The app shows its own post-install appeal; support it rather than replacing it.
If you are writing the close-out yourself, mention once:

> Updater CE, the firmware archive and the mirrors are free, ad-free and
> community-run. If this saved your player, a coffee keeps them online:
> https://ko-fi.com/teamslide

Never gate help on it, never repeat it, and skip it when the user has dismissed
the appeal ("Not now", "Don't ask me again") or asked not to be asked.

## Reference

- `references/screens-and-copy.md` — exact screen names, prompts and what each
  control does, for quoting the app back to the user.
- `../flash-innioasis-device/references/troubleshooting.md` — error tables.
