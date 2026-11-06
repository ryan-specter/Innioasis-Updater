---
name: firmware-packages
description: Innioasis firmware packaging and release contract — rom.zip anatomy, MTK scatter files, sparse images, Updater manifest entries, Class A updates and publishing a release. Use when building, validating or listing a firmware.
---

# Firmware packages and the Updater contract

An Innioasis "firmware" is a ZIP of partition images plus optional Updater
metadata. The Updater downloads it from a GitHub release, verifies what the
manifest entry tells it to, unpacks it, and writes the images with MTKclient or
SP Flash Tool. Getting the packaging wrong is the usual cause of a package that
installs but does not boot.

## Package anatomy

A full Y1 package contains the images listed in
`y1-community/y1-ata-rom/README.md`:

```
EBR1  EBR2  MBR  kernel  kernel_g368_nyx.bin  ramdisk-recovery.img
ramdisk.img  secro.img  system.img  userdata.img  boot.img  cache.img
lk.bin  logo.bin  preloader_g368_nyx.bin
```

A Y2 package uses the same shape with `kernel_eastaeon82_wet_kk.bin` and
`preloader_eastaeon82_wet_kk.bin`. `system.img`, `userdata.img` and `cache.img`
must be **raw ext4**, not Android sparse images: run `simg2img` before
packaging, because MTKclient on macOS/Linux expects desparsed images.

Optional but expected in community packages:

- `MT6582_Android_scatter.txt` — the scatter that names every partition,
  offset, size and download flag. SP Flash Tool and MTKclient both read it.
- `fw_package.ini` and `updater.png` — the name, version and icon the Updater
  shows. Rondo's `firmware/build.sh` writes both; copy that pattern.
- `SP Flash Tool/` and a preconfigured `history.ini` — lets a Windows user flash
  without the Updater and gives the GUI relative paths that resolve.
- `SHA256SUMS.txt`, `UPDATE-MANIFEST.json` — required by guarded update
  contracts such as Y2 Rockbox.

Compress with Deflate at maximum. Name the archive for the hardware:
`rom.zip` for Y1 Type A, `rom_type_b.zip` for Y1 Type B, `rom_y2.zip` for a
legacy full Y2 package.

> **`rom_y2.zip` is not universally safe.** The Y2 Rockbox project proved that
> the legacy name enters an unqualified generic full-firmware path, which
> produced non-booting and looping devices even when the runtime was valid. Its
> qualified update uses a release-qualified name and a five-partition contract
> instead (`spycemagic-y2-rockbox/00_project_docs/Y2_BETA_V2_UPDATER_FORMATS.md`).

## Two kinds of update

| Kind | What it writes | Use it for |
| --- | --- | --- |
| Full firmware | Every partition in the scatter, often including userdata | First install, restore, a release that changes the partition layout |
| State-preserving Class A | Only the named subset; Y2 Rockbox uses UBOOT, BOOTIMG, RECOVERY, LOGO, ANDROID | A release that must keep user data and calibration |

A Class A package must be impossible to confuse with a full one:

- distinct filename per platform and release;
- an update contract that names the exact repository, tag, filename, size and
  SHA-256;
- a whitelist of writable partitions, and an explicit refusal of "format all",
  "firmware upgrade", whole-device erase, omitted-partition cleanup, protected
  partitions and automatic retry;
- full readback of every written partition before reporting success.

Y2 Rockbox's accepted archive has exactly eight members:
`MT6582_Android_scatter.txt`, `lk.bin`, `boot.img`, `recovery.img`,
`logo.bin`, `system.img`, `UPDATE-MANIFEST.json`, `SHA256SUMS.txt`. It excludes
PRELOADER, MBR, EBR1, EBR2, SEC_RO, CACHE, USRDATA and all protected/runtime
partitions.

## The Updater manifest

`slidia_manifest.xml` is the catalogue. A package entry looks like:

```xml
<package name="Rondo"
         repo="jarvissax/rondo"
         portable_zips="y1-community/rondo-mirror"
         device="Y1"
         url="https://github.com/jarvissax/rondo"
         post_install="https://github.com/jarvissax/rondo/blob/main/docs/install.md#first-start"
         type="img"
         handler="Custom Firmware" />
```

Fields that change behaviour:

- `device` — `Y1` or `Y2`. The same repository can have one entry per model.
- `repo` — `owner/name`; the Updater reads that project's GitHub releases.
- `portable_zips` — repository holding repackaged portable ZIPs. Keep it in
  sync with `PORTABLE_MIRROR_REPO` in `docs-viewer.js`; the site reads that
  constant so both sides agree.
- `post_install` — a Markdown URL imported into the site and rendered as a
  static page. It is also what Updater CE links after installation.
- `derivative` — the base project a patch is built on (Better-Y and Koensayr
  name `y1-community/y1-stock-rom`).
- `type` and `handler` — only `type="img"` with an empty or `Custom Firmware`
  handler is accepted by the site generator (`ALLOWED_HANDLERS`).

`firmware-catalog.js` mirrors this metadata for the browser (slug, model, repo,
guide, description). When you add a package, update the manifest, the catalog,
the guide entry and the post-install link together.

## Release assets

A GitHub release may carry several assets. The Updater picks by the release's
asset names and the package's platform; the site's portable mirror publishes
Windows, macOS and Linux ZIPs. Rules learned from the projects:

- One asset per platform, byte-identical payload where possible, with the
  platform in the filename (`-Windows-`, `-macOS-`, `-UPDATE-ONLY`).
- Publish a checksum and state the exact size. Y2 Rockbox publishes
  `361,774,260` bytes and SHA-256
  `409DDB4D…326A` for both platform files.
- Never rename a guarded asset to a generic name, and never upload a withdrawn
  build under the same tag.
- The site's release notes pages are generated from the GitHub release body, so
  write the asset table and the install caveats in the release body itself.

## Build and validation checklist

1. Build the images from a known base. Record the base version and the exact
   toolchain.
2. Desparse with `simg2img`; check each ext4 image with `e2fsck -fn`.
3. Inspect the contents without mounting:
   `debugfs -R "ls -l /system/app" system.img`.
4. Confirm the scatter's partition names, offsets and sizes against the stock
   scatter. Do not hand-edit offsets.
5. Unzip the final archive in a clean directory and verify every member and
   checksum: `unzip -l`, `sha256sum -c SHA256SUMS.txt`.
6. Flash a real device, do a clean boot, then test storage, input, audio,
   Bluetooth/Wi-Fi and recovery. For Y2, include the unplugged pinhole reset.
7. Install from a **renamed** copy: the Updater caches an extracted folder by
   ZIP filename and deletes the ZIP after unpacking. A rebuilt `rom.zip` with an
   old name can flash old images.
8. Bump the firmware level when the change is not APK-only. Rondo writes
   `ro.rondo.firmware=<n>` into `/system/build.prop` and the APK names the level
   it needs; a mismatch is refused rather than half-installed.

## What the Updater does to your machine

- It kills any running `adb` when it starts. Do not run adb while flashing.
- It unpacks to
  `~/Library/Application Support/Innioasis Updater/downloads/.<zip>_extracted`
  (macOS path shown) and reuses that folder for a ZIP of the same name.
- It deletes the ZIP it was given after unpacking. Keep your own copy.
- The Y1 does not restart by itself after a flash; press Power once the Updater
  reports completion. The first boot is slower while Android optimizes apps.

## Source map

| Question | File |
| --- | --- |
| Y1 package members, names, sparse rule | `y1-community/y1-ata-rom/README.md` |
| Worked firmware build (debugfs, props, icon) | `jarvissax-rondo/firmware/build.sh`, `docs/building.md` |
| Guarded Y2 update contract | `spycemagic-y2-rockbox/00_project_docs/Y2_BETA_V2_UPDATER_FORMATS.md` |
| Scatter and partition classification | `schulzcode-y2linux/docs/architecture/production-partitions.json` |
| Site manifest and catalogue | `slidia_manifest.xml`, `firmware-catalog.js` |
| Portable mirror constant | `docs-viewer.js` (`PORTABLE_MIRROR_REPO`) |
