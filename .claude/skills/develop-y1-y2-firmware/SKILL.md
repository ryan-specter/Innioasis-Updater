---
name: develop-y1-y2-firmware
description: >-
  Help developers target existing Innioasis Y1/Y2 (and Timmkoo/A5) MediaTek firmware
  images, read slidia_manifest.xml and the community firmware archive/publishing
  pipeline, and build a distributable ROM package. Use when analysing a stock or
  custom firmware source base, choosing a scatter/keylayout, publishing a release to
  the community catalogue, mirroring a ROM zip, or writing a custom firmware experience.
license: See LICENSE in the repository root.
metadata:
  ecosystem: innioasis-community
  skill-version: "1.0"
  upstream: https://github.com/y1-community/updater-ce-neo
---

# Develop and publish Y1 / Y2 firmware

This skill is for people **making or packaging** firmware, not installing it.
Installation lives in `../flash-innioasis-device/SKILL.md`.

## 1. Find the images that already exist

The catalogue is data, not code:

```
https://innioasis.app/slidia_manifest.xml          # live
assets/online/slidia_manifest.xml                  # snapshot shipped in the app
```

Each `<package>` names a repo and a device. To get a source base:

1. Read the manifest entry (name, repo, device, derivative, info_repo).
2. `gh release list -R <repo>` then take the newest release's firmware zip —
   `rom.zip` for Y1, `rom_<device>.zip` otherwise (`rom_y2.zip`, `rom_a5.zip`).
3. Prefer a `portable_zips` mirror's package when you only need a ready-to-flash
   build; take the raw repo release when you need the images themselves.

Current families worth knowing: Original Software (`y1-community/y1-stock-rom`),
Rockbox (`rockbox-y1/rockbox`, `spycemagic/y2-rockbox`), Solar, Inniclassic,
Y2Player, Rondo, Koensayr, JJ Launcher, ATA Android 4.2/4.4 dev bases
(`y1-community/y1-ata-rom`, `y1-community/y2-ata-rom`), Linux dev bases, Reborn
(Y2Linux). `derivative=` names the base a custom firmware was built from — that
is the key to Keep Data compatibility and to picking a correct base.

Details: `references/slidia-manifest.md` (every attribute, and how the app
interprets it).

## 2. Read the scatter before you touch an image

A package is defined by its scatter: platform, storage type, partition table
style and every partition's address, size and file. Two builds of the "same"
device can differ; a wrong scatter is a brick.

- Y1: MT6572, project `eastaeon72_wet_jb3`, **Type A / Type B** hardware.
- Y2: MT6582, project `eastaeon82_wet_kk`.
- Timmkoo A5: MT6572; Q5: `eastaeon80_wet_kk`; G1/PR1/SR1/R1: see
  `assets/device_models.xml`.

Legacy scatters (MT6572/6582/6580/8382) use **MBR/EBR**, not GPT: the
`EMMC_USER` linear address is biased (Y2: 20 MB) from the physical address. The
flash engine calibrates against the device's live MBR chain, so addresses you
copy out of a scatter are **not** physical write offsets. Never hand-compute
them; let the engine do it.

Also note in any package you build:

- **Overlay firmware** (Reborn/Y2Linux and friends) lists only a subset of
  partitions. That is deliberate: it relies on the base preloader, MBR/EBR,
  UBOOT/LK, SECCFG and PROTECT_F/S already on the device. It must be flashed in
  Download Only mode, and it must never be documented as a wipe.
- **Keep Data** works by excluding `usr`/`userdata`; a `*_scatter_preserve_data
  .txt` beside the real scatter is that variant, not the package's scatter.
- Keylayouts and scan codes differ per build and per model. The community
  developer docs for ATA/original Y1/Y2 key maps are **not published yet** —
  do not invent a table. Derive them from the image you are working on
  (`/system/usr/keylayout/*.kl`, `/system/usr/keychars/*.kcm`, plus the kernel
  keymap for non-Android builds) and state which build the map came from.

Reference: `references/scatter-and-input.md`.

## 3. Build a package Updater CE can install

Minimum viable package:

```
MyFirmware/
├── MT6572_Android_scatter.txt   # exactly one scatter; every image it lists
├── preloader.bin
├── boot.img
├── system.img
├── ...
├── fw_package.ini               # optional but strongly recommended
└── updater.png                  # optional header icon (also .jpg/.jpeg)
```

`fw_package.ini` fields: `software_name`, `version`, `target_model`,
`target_type`, `description`, `enabled`, `post_install`, `post_install2`,
`derivative` (comma-separated names for Keep Data compatibility). Copy
`assets/fw_package.ini` and edit it.

macOS packs use a `Firmware/` folder beside the `.app`; Windows/Linux packs put
the same files in an `SP_Flash_Tool` folder (or beside a copy of SP Flash Tool).
A `*rockbox*.txt` marker means themes/fontpacks install alongside the firmware.

Validate before publishing:

```bash
.agents/skills/flash-innioasis-device/scripts/flash.py --package ./MyFirmware --check --json
```

That confirms the single scatter, every declared image, the platform/storage
lines, and the inferred model — the same checks the app performs before it will
offer an install.

Packaging and mirror rules: `references/packaging-and-publishing.md`.

## 4. Publish to the community catalogue

1. **Release** the ROM zip on the project's GitHub repo, tagged by version, with
   a real title and notes (the catalogue shows them to users).
2. **Mirror** it (optional but valued): a `y1-community/<name>-mirror`
   repository whose workflow adds one ready-to-run zip per platform
   (`rom-windows.zip`, `rom-linux.zip`, `rom-linux-arm64.zip`,
   `rom-windows-arm64.zip`, `rom-macos.zip`) and an `index.json` (schema 1) with
   `source_asset`, `platform`, size, checksum and URL for each.
3. **Register** the package in `slidia_manifest.xml`:

```xml
<package name="Rockbox" repo="rockbox-y1/rockbox"
         portable_zips="y1-community/rockbox-mirror"
         device="Y1" url="https://github.com/rockbox-y1/rockbox"
         type="img" handler="Custom Firmware"
         post_install="https://example.org/first-start"
         derivative="y1-community/y1-stock-rom" />
```

4. Verify: the app's Select Software list shows the release for the right model,
   the download resolves, the card shows your name/version, and the post-install
   page opens after a successful install.

Never change an existing release's assets in place — users pin and mirror them.
Publish a new tag.

## 5. Never ship

- A package missing an image its scatter lists (the app refuses it, and a
  half-written player is worse than no install).
- A scatter with edited addresses, or an image rewritten to "fix" the preloader
  header — the engine wraps preloaders for boot1 itself.
- A `format-all` instruction, or docs that tell users to format before flashing.
- Credentials, vendor blobs you have no right to redistribute, or a mirror that
  deletes the upstream assets.
