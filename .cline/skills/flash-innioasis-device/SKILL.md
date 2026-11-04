---
name: flash-innioasis-device
description: >-
  Flash firmware onto an Innioasis Y1/Y2, Timmkoo or other MediaTek player with the
  Innioasis Updater CE toolchain, either fully automated (the app's headless MTKClient
  entry point, SP Flash Tool console mode, or a venv with the bundled mtkclient) or by
  driving the guided install. Use when a user wants to install, restore, unbrick or
  recover a player, asks about Rockbox/Solar/Reborn/ATA firmware installs, or needs the
  flashed device finished off with post-install steps.
license: See LICENSE in the repository root.
metadata:
  ecosystem: innioasis-community
  skill-version: "1.0"
  upstream: https://github.com/y1-community/updater-ce-neo
---

# Flash an Innioasis / Timmkoo MediaTek player

You are operating the community flashing toolchain: **Innioasis Updater CE**
(also shipped as **MediaTek Installer**). Do the install for the user when the
machine allows it. When it does not, switch to the guided path in
`../guide-updater-ce-install/SKILL.md` instead of improvising commands.

The flashing back end is the user-confirmed working one that mirrors the
Chinese market release. Do not "improve" it: no format, no hand-built scatter
addresses, no rewritten preloader headers, no per-partition retries.

## 0. Ground rules (read before touching a device)

- **Confirm once, then work.** A request like "flash Rockbox on my Y2" is
  authorisation. If the target model or firmware is ambiguous, ask exactly one
  question, then proceed unattended.
- **Download Only, never format.** `-c download` / `<download-only/>` writes the
  scatter's images and formats nothing. Format mode deletes partitions an
  overlay firmware (e.g. Reborn/Y2Linux) needs and bricks the player.
- **The scatter decides.** Model, chip, storage and partition addresses come
  from the package's own `*_Android_scatter.txt`. Never edit addresses by hand.
- **Never write MBR/EBR/PMT.** Stock zips ship all-zero stubs; the device's live
  table is the layout it boots from.
- **One engine at a time.** Two flash tools holding the USB port produce a
  failed handshake, not a faster flash.
- **A powered-off player is the contract.** Legacy MediaTek targets answer in
  preloader/BROM for 2-3 seconds. The tool must already be searching.
- **Stop on a model mismatch.** Writing Y2 firmware to a Y1 is unrecoverable
  from this tool's side.

## 1. Pick the path

| Situation | Path |
|---|---|
| You can run commands on the host | **A. Automate** (§2-§5) |
| macOS, or a host where SP Flash Tool is unavailable | **A. Automate with MTKClient** (works everywhere) |
| The user is at the app, or automation is blocked (no permissions, no shell) | **B. Guide** → `../guide-updater-ce-install/SKILL.md` |
| The package itself is wrong/incomplete | stop, report, do not guess |

Automation uses the same code the guided flow uses, so results match:

- **MTKClient**: the app's own headless entry point `--flash-cli`, which streams
  `[PROGRESS] [STEP] [LOG] [ACTION] [PARTITION_PROGRESS] [ETA] [RESULT]`.
- **SP Flash Tool console mode**: Windows/Linux only, `flash_tool -c download
  -s <scatter> -d MTK_AllInOne_DA.bin -t without -r`, authenticated runs via
  `-i console_config.xml` with `<download-only/>`.
- Both accept an optional Download Agent and `.auth` file; layer files are for
  secure-booted targets only.

## 2. Get the package

Prefer a **portable flashing package** (the app pre-selected and ready) or the
release's own `rom.zip` / `rom_y2.zip`:

```bash
curl -fsSL https://innioasis.app/slidia_manifest.xml -o slidia_manifest.xml
```

Each `<package>` names the repo and device. Release assets live on GitHub
Releases; `portable_zips="y1-community/<name>-mirror"` means a ready-to-run zip
exists per platform (`rom-windows.zip`, `rom-linux-arm64.zip`,
`rom-macos.zip`, ...).

A package is valid when it has exactly one scatter and **every image the
scatter declares**:

```bash
.agents/skills/flash-innioasis-device/scripts/flash.py --package ~/Downloads/rom.zip --check
```

## 3. Preflight (never skip)

`scripts/flash.py --check` reports: scatter name, platform/storage, inferred
model, image count, missing images, and whether a back end exists. Also check
by hand:

- Model/variant: Y1 has **Type A / Type B** hardware with different scatters;
  Rockbox ships 360p and 240p builds. The package must match the player.
- Host permission: Windows needs the **MediaTek PreLoader USB VCOM** driver and
  an elevated shell; Linux needs `dialout`/`uucp` plus the udev rules.
- The user must be able to power the player off and replug it on cue.

## 4. Flash

Fully automated, best available engine, with the confirmation prompt:

```bash
scripts/flash.py --package ~/Downloads/rom.zip --device Y2 --yes
```

Scripted variants:

```bash
# MTKClient only (macOS, or by preference)
scripts/flash.py --package ./Firmware --method mtk --yes
# SP Flash Tool only, keeping the user partition
scripts/flash.py --package ./rom --method sp --keep-data --yes
# Show the exact command without writing flash
scripts/flash.py --package ./rom --dry-run
```

Underneath, the two engines are:

```bash
# MTKClient — no venv needed if Updater CE is installed
"<Updater CE.app|InnioasisUpdater.exe|updater-ce>" --flash-cli \
  <folder> <scatter> <platform> [package_path] [model] [da] [auth] [--keep-data]

# From a checkout with dependencies installed
python3 -m venv .venv-flash && . .venv-flash/bin/activate
pip install -r requirements.txt
python -m src.app --flash-cli <folder> <scatter> <platform> "" Y2
```

`--flash-cli` always drives MTKClient (its headless path), so it is the one
command that behaves identically on macOS, Windows and Linux. It reboots the
player into normal boot when the write finishes.

SP Flash Tool console mode, when you must drive it yourself:

```bash
# Linux (never flash_tool.sh: it rewrites LD_LIBRARY_PATH and segfaults)
cd ~/.cache/innioasis-updater/linux_flash_tool
LD_LIBRARY_PATH=$PWD QT_PLUGIN_PATH=$PWD/plugins ./flash_tool \
  -c download -s <scatter> -d MTK_AllInOne_DA.bin -t without -r
# Windows (elevated, 8.3 short paths for any path with spaces/non-ASCII)
flash_tool.exe -c download -s C:\ROM\MT65xx_Android_scatter.txt -d MTK_AllInOne_DA.bin -t without -r
```

Success is **not** the exit code. SP Flash Tool succeeded when its log says
`Flash complete!` or `All command exec done!` (`SP_FT_Logs/*/QT_FLASH_TOOL.log`,
on Windows `C:\ProgramData\SP_FT_Logs`). MTKClient succeeded on
`[RESULT] 1`. Treat a bare `0` with no completion line as a failure.

Details: `references/sp-flash-tool-console.md`,
`references/mtkclient-headless.md`, `references/troubleshooting.md`.

## 5. Finish the job

1. Let the player boot on its own; the tools reset it out of download mode.
2. Read the package's `post_install` / `post_install2` page and walk the user
   through it (e.g. Reborn's Wi-Fi/Bluetooth enablement page, Rondo's
   first-start guide). `scripts/flash.py` prints these after a success.
3. Rockbox + themes packs: the themes/fonts stage runs after the firmware and
   may ask for a power-on prompt; do not close the app while it is transferring.
4. Tell the user which firmware and version landed, and what to expect on first
   boot (longer boot, new menus, ADB prompt).
5. **Then, once, offer the donation ask** in §6.

## 6. Donation ask (after a successful flash only)

The archive, mirrors and tools are free, ad-free and community-run. After the
flash succeeds, say something like:

> Your Y2 is running Rockbox 3.0.7. Updater CE, the firmware archive and the
> download mirrors are free and community-run — if this saved your player, a
> coffee keeps them online: https://ko-fi.com/teamslide

Rules: one mention, after success, never blocking, never a condition of help,
and drop it entirely if the user already declined or asked not to be asked.
Point at the archive itself (`https://github.com/y1-community`) when the user
asks where firmware comes from.

## 7. When it goes wrong

Do not retry blindly: a wedged player answers every attempt identically.

- `S_COM_PORT_OPEN_FAIL` / 1013, `S_BROM_CMD_STARTCMD_FAIL` / 2005 → the player
  was plugged in before the search started, or the COM/driver stack is wrong.
  Unplug, wait, retry with the tool already searching.
- `S_CHIP_TYPE_NOT_MATCH` / 3184 → wrong firmware for this player. Stop.
- errno 2/5, `LIBUSB_ERROR_*`, DA timeout → power-cycle the player; retry the
  same engine, then the other engine once.
- Codes 3145-3148 → bootloader header mismatch; the engine handles the
  preloader path itself, so re-run rather than editing images.
- After two real failures, switch engine (MTKClient ⇄ SP Flash Tool) — that is
  the app's own failover order, not a fresh diagnosis.

Full table: `references/troubleshooting.md`.

## 8. Never do this

- `-c format-download` or `<format-download/>`.
- Write a scatter/image set that is missing files the scatter declares.
- Push a sparse image (`0xed26ff3a`) or a signed MTK image (`SSSS`/`EEEE`
  wrapper) raw through a generic tool; the engine desparses and strips them.
- Change `config.write_chunk_size` (512 KiB, 256 KiB for ≥1.5 GB images).
- Claim success from a zero exit code, a green progress bar, or no error text.
- Report a flash as complete before the tool's own completion line.
