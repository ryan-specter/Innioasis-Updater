---
name: stock-android-roms
description: Working with the stock Android images — Y1 Android 4.2.2 API 17 and Y2 Android 4.4.2 API 19. Covers ext4 image editing with debugfs, root, system-app signing, hidden APIs, debloating and repacking. Use for ROM patches, launcher replacement and system-level features.
---

# Stock Android ROMs (Y1 4.2, Y2 4.4)

Both players run AOSP-derived MediaTek Android with test keys and no Google
services. Custom firmware is built by editing the stock `system.img` (and
sometimes `userdata.img`) and repacking the partition images, not by compiling
AOSP.

## Base images

| Device | Base | Android | API | Notes |
| --- | --- | --- | --- | --- |
| Y1 | `y1-community/y1-ata-rom` | 4.2.2 | 17 | Kernel 3.4.5, `ALPS.JB3.MP`, `ro.secure=0`, `ro.debuggable=1`, adbd root |
| Y1 | `y1-community/y1-stock-rom` | stock | 17 | Original software and restore path |
| Y2 | `y1-community/y2-ata-rom` / stock 3.1.7 or 3.2.0 FM | 4.4.2 | 19 | `eastaeon82_wet_kk`, MT6582 |
| Y2 | `schulzcode/Y2Player` system-image pipeline | 4.4.2 | 19 | Builds a minimized system image from a matching stock package |

The Y1 base is permissive: `ro.secure=0`, `ro.debuggable=1`, adbd runs as root,
and `/system/xbin/su` is setuid root. The Y2 stock image is the normal
production security model; Y2Player's optional ADB boot image is a separate
development artifact, not part of the release firmware.

## Editing `system.img` without mounting

Mounting requires root and loop devices. The projects use `debugfs`, which works
on any host with `e2fsprogs`:

```bash
# Inspect
debugfs -R "ls -l /system/app" system.img
debugfs -R "cat /system/build.prop" system.img

# Extract one file
debugfs -R "dump /system/app/Rondo.apk /tmp/Rondo.apk" system.img

# Replace or add a file (debugfs writes in place)
debugfs -w -R "rm /system/app/Rondo.apk" system.img
debugfs -w -R "write /tmp/Rondo.apk /system/app/Rondo.apk" system.img

# Permissions and ownership
debugfs -w -R "sif /system/app/Rondo.apk mode 0100644" system.img
debugfs -w -R "sif /system/app/Rondo.apk uid 0" system.img
debugfs -w -R "sif /system/app/Rondo.apk gid 0" system.img

# Always check afterwards
e2fsck -fn system.img
```

Rondo's `firmware/build.sh` is the reference implementation: it downloads the
base ROM with a SHA-256 check, edits the system and data images with `debugfs`,
removes apps, installs the APK, adds the boot logo/animation and the Updater
metadata, then runs `e2fsck` and stops if anything is wrong. Copy that structure
instead of inventing a new one.

## System apps, privileges and signing

- A launcher that replaces Home must declare `HOME` + `DEFAULT` and be made the
  default through the "Complete action using" dialog or by preinstalling it.
- A built-in app gets permissions that normal installs cannot: Rondo uses
  `INSTALL_PACKAGES` for APK self-updates, `MOUNT_UNMOUNT_FILESYSTEMS` for USB
  mass storage and `SET_WALLPAPER_COMPONENT` for its boot wallpaper.
- **Signature continuity matters.** Android only accepts an update signed with
  the same key as the installed copy. Rondo ships built-in and updates through
  `pm install -r` because both use the firmware key. Inniclassic's release APKs
  are debug-signed, so installing over JJ Launcher (`com.themoon.y1`) fails with
  `INSTALL_FAILED_UPDATE_INCOMPATIBLE`; uninstall first.
- Android 4.4 requires a **v1/JAR signature**. Y2Player's release build config
  produces it; a modern v2-only APK will not install.
- System-app paths: `/system/app/Foo.apk` on 4.2 and 4.4. Y2Player uses
  `/system/priv-app/Y2Player.apk` for privileged permissions.
- Replacing a system app keeps the firmware copy in `/system/app` and runs the
  updated copy from `/data/app`, inheriting the firmware copy's granted
  permissions (not new ones). A new permission needs a new firmware.

## Hidden framework APIs used by the projects

These exist on both releases and are reached by reflection or as a built-in app:

| Need | API |
| --- | --- |
| Join Wi-Fi without the touch dialog | `WifiManager.connect(config|netId, listener)` |
| Pair / unpair Bluetooth | `BluetoothDevice.createBond`, `removeBond` |
| A2DP connect / disconnect | `BluetoothA2dp.connect`, `disconnect` |
| USB mass storage | `StorageManager.enableUsbMassStorage`, `disableUsbMassStorage` |
| Set the boot wallpaper | `IWallpaperManager.setWallpaperComponent` |
| Sound effects profile | `AudioProfileManager.setSoundEffectEnabled` |

On the Y1, `isUsbMassStorageEnabled` asks vold about the wrong volume (the card
is `sdcard2`) and always returns false; `Environment.getExternalStorageState()`
reads `shared` while the computer holds the card. Do not trust either as a
completion signal.

## Removing SystemUI and other stock apps

Rondo removes SystemUI because this ROM's SystemUI opens a touch-only "USB
connected" screen and crashes if it is disabled. The app then takes over the
visible jobs:

- wheel click via `AudioManager.playSoundEffect(FX_KEY_CLICK)`, still governed
  by `SOUND_EFFECTS_ENABLED`;
- low-battery warning via `ACTION_BATTERY_LOW`;
- a black `WallpaperService`, because Android 4.2 keeps the boot animation on
  screen until a wallpaper draws and the default `ImageWallpaper` lives in
  SystemUI. The hidden call needs `SET_WALLPAPER_COMPONENT` and is remembered,
  so only the first boot after a flash sets it.

If you remove SystemUI, test the boot animation, USB, low battery and the wheel
click. If you keep it, test that its USB screen is usable without touch.

## Root and patching stock binaries

Koensayr (`ryan-specter/koensayr-auto`) is the reference for byte/smali patching
a stock Y1 image:

- `apply.bash` extracts `system.img`, loop-mounts it, applies patchers in place,
  unmounts and flashes with MTKclient.
- Patches target `mtkbt`, `libextavrcp.so`, `libextavrcp_jni.so`, `MtkBt.odex`,
  `libaudio.a2dp.default.so`, `AVRCP.kl` and the music APK.
- `src/su/` is a ~1–2 KB direct-syscall ARM EABI `su` with no libc, installed
  setuid (06755) at `/system/xbin/su`.
- Stock binaries are gated by MD5 per firmware version (`KNOWN_FIRMWARES`).
  Never bypass a gate on a version you have not tested; add a row instead.
- `--no-flash` writes `system-*-devel.img` for CI or repack.

Better-Y (`Leska1337/better-Y`) is the reference for patching the stock
launcher: apktool 2.11.1, smali edits, platform testkey signing,
`simg2img`/`debugfs` to put the APK back. Its `build/` directory contains the
decoded tree and the tools/scripts that rebuild it.

## Build properties and update levels

Add a property that names the firmware generation, and make the app refuse
updates that need a newer one. Rondo:

- `firmware/build.sh` appends `ro.rondo.firmware=<n>` to `/system/build.prop`;
- `firmwareLevel` in `app/app/build.gradle.kts` is the same number;
- the APK manifest declares `rondo.firmware`;
- Settings, the dashboard and the update page all refuse an APK that needs a
  newer firmware, instead of installing it into an incompatible system.

Keep the stock `ro.build.version` fields intact unless the change really is a
new base; tools and support scripts key off them.

## Testing a repacked ROM

1. `e2fsck -fn` both images.
2. Boot a real device; check first boot completes and Home resolves.
3. Check storage: internal, SD card, USB mass storage handoff.
4. Check input: wheel, Centre, Back, Play, media keys, wake.
5. Check audio: speaker, headphones, Bluetooth, FM if present.
6. Check the updater path: the package installs from a uniquely named ZIP and
   the first boot works after a cold start.
7. Keep a hash-verified stock package for the exact model/revision.

## Source map

| Question | File |
| --- | --- |
| Y1 base package rules | `y1-community/y1-ata-rom/README.md` |
| Worked image build | `jarvissax-rondo/firmware/build.sh`, `docs/building.md` |
| Byte/smali patching and root | `ryan-specter/koensayr-auto/apply.bash`, `src/patches/`, `docs/PATCHES.md` |
| Launcher patch and signing | `Leska1337/better-Y/README.md`, `build/` |
| Y2 system-image pipeline | `schulzcode-Y2Player/tools/build-linux.sh`, `docs/ADB_BOOT_IMAGE.md` |
| Inniclassic package/signing caveats | `FabianZettl-inniclassic/README.md` |
