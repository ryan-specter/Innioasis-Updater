---
name: launchers
description: Innioasis launcher and firmware projects — JJ Launcher, Inniclassic (Y1/Y2), Solar, Better-Y, Koensayr and Rondo. Covers package names, theme engines, patching techniques, build/update paths and known constraints.
---

# Launcher and firmware projects

These projects replace or patch the Home experience. They share the Y1 input
model but differ in packaging, signing and update strategy. Pick the right one
before changing code.

## JJ Launcher (`ismileblue/y1_launcher`)

The base launcher for the Y1 (and a Y2 build). Java, classic Android views,
package **`com.themoon.y1`**.

- Own theme engine: `/storage/sdcard0/Y1_Themes/<Name>/config.json` plus PNGs,
  and an optional `sample_player_theme.json` widget layout (`player_ui` list of
  `text`, `button`, `icon`, `progress`, `box`, `widget_focus_image` elements;
  standard buttons are ordered by `focus_index` from 0). Both files are
  documented in the repo's `README.md` and sample, not in the stock-family
  reference.
- Wheel drives a focus index (`focus_index` on buttons, starting at 0);
  Centre/Enter activates; Back/DPAD_UP is the "top button".
- Actions are named targets (`Now Playing`, `Music Library`, `Root Folder`,
  `Bluetooth`, `Wi-Fi Settings`, `Settings Menu`, `Web Server`,
  `Display Brightness`, `Storage Info`, `Date & Time Settings`).
- Handles Wi-Fi/Bluetooth setup with its own screens because Android's dialogs
  are touch-only.
- Ships as a flashable ROM and as an APK. The ROM is the safer route on a
  non-rooted player.

Theme details: `README.md` and `sample_player_theme.json` in the repo. The
stock-family reference does not cover this engine.

## Inniclassic (`FabianZettl/inniclassic`, `JonaszPotoniec/inniclassic-y2`)

A separate repository built directly on JJ Launcher's source, aiming at the
iPod Classic experience. Same package name (`com.themoon.y1`) and theme engine.

- Y1 ROM ships firmware 3.1.2 with Inniclassic as the system launcher; the
  standalone APK was verified on system software 2.1.9.
- Release APKs are **debug-signed**. Installing over JJ fails with
  `INSTALL_FAILED_UPDATE_INCOMPATIBLE`; uninstall first:
  `adb uninstall com.themoon.y1` or
  `adb shell pm uninstall --user 0 com.themoon.y1`.
- Uninstalling clears app-private settings but keeps music, themes
  (`/storage/sdcard0/Y1_Themes`) and `.scrobbler.log`.
- Features: iPod-style menus, cover flow, seek/rating modes, key lock, synced
  lyrics (`.lrc` or embedded), favorites, music quiz, podcasts, FM radio,
  libVLC video, audiobooks, Wi-Fi PC upload, Last.fm scrobbling.
- Known limits: gapless only for ≤15-track non-shuffled, non-FLAC queues; video
  needs modest sources (640 × 480, 30 fps, ~2 Mbps; HandBrake preset in
  `tools/handbrake_y1_preset.json`).
- Library cache `.y1_library_cache.json` at the SD root can be prebuilt on a PC
  with `tools/build_library_cache.py` (needs `mutagen`).
- Last.fm needs your own API key/secret in `local.properties`; without it the
  app runs but does not authenticate.

The Y2 fork (`JonaszPotoniec/inniclassic-y2`) ports the same UI and theme
manager; its `ThemeManager.kt`/`AutoThemeManager.kt` are Kotlin and have parity
tests. Treat it as a separate target: Y2 input, signing and package paths differ.

## Solar (`thesolarproject/solar`)

A Y1/Y2 launcher with streaming, Wi-Fi features and an extended theme engine.
Package `com.solar.launcher`.

- Reads the stock Y1 theme keys (`homePageConfig`, `settingConfig`,
  `itemConfig`, `dialogConfig`, `menuConfig`, `fileConfig`, `statusConfig`) and
  overlays a `solarConfig` block for extra shortcuts and preferences.
- Precedence: active theme `solarConfig` → stock block in the same theme →
  nothing. Solar's bundled Aura defaults are never merged into third-party
  themes for icons.
- Key derivation is from English UI labels (`appMusic`, `settingsAbout`,
  `appGet_Music`); sanitisation replaces non-alphanumerics with `_`.
- Can set preferences on theme apply (`enable…`, `disable…`, `set…`), including
  `setStatus_Bar_Text` (`Clock`/`Title`) and `setArtwork_Perspective`
  (`Flat`/`3D`).
- Theme manager: `ThemeManager`, `HomeMenuConfig`, `SettingLookup`,
  `SolarTheming`; bundled themes under `app/src/main/assets/themes/`.
- The theming doc is the contract for adding a new shortcut or settings row: add
  the row, wire the icon through `ThemeManager.getHomeMenuIcon`/
  `getSettingsRowIcon`, document the English label/key, register the pref in
  `SettingLookup`, add a test.

Details: `skills/theme-authoring/reference/y1-stock-themes.md`.

## Better-Y (`Leska1337/better-Y`)

A mod of the stock Y1 launcher based on firmware 3.1.2, distributed as a ROM.

- Patches `com.innioasis.y1_3.1.2.apk` with apktool 2.11.1, edits smali, signs
  with the platform testkey, and rebuilds the images with `simg2img`/`debugfs`.
- Adds metadata-driven track numbers, artist/genre splitting, album-artist
  support, external `cover.*`/`folder.*` covers, disk numbers, interactive Now
  Playing buttons (like, shuffle, repeat, lyrics, AB loop, queue, bookmark,
  speed, sleep timer), light/dark/theme colours.
- Optional `/better-Y/comma_artists.txt` on the SD card handles artists with
  commas.
- The `build/` tree contains the decoded APK, smali and scripts; use it as the
  reference for stock-launcher patching.

## Koensayr (`ryan-specter/koensayr-auto`)

A stock Y1 firmware patcher and research toolkit (MT6572 / Android 4.2.2), not a
launcher replacement.

- `apply.bash` dispatches `--adb`, `--avrcp`, `--bluetooth`, `--music-apk`,
  `--remove-apps`, `--root`, `--all`; `--no-flash` writes patched images only.
- Extracts `system.img` from `rom.zip`, loop-mounts it, applies
  byte/smali patches, unmounts, flashes with MTKclient.
- `--avrcp` patches `mtkbt`, `libextavrcp.so`, `libextavrcp_jni.so`,
  `MtkBt.odex`, `libaudio.a2dp.default.so`, `AVRCP.kl` and installs
  `Y1Bridge.apk`.
- `--root` installs a ~1–2 KB direct-syscall ARM `su` at `/system/xbin/su`
  (06755); stock `/sbin/adbd` stays untouched.
- Known firmwares are gated by MD5 (`KNOWN_FIRMWARES`). Add a row for a new
  build; do not skip the gate on untested versions.
- Diagnostics (`@btlog`, post-root probe, gdbserver attach) are separate from
  the patch flow.

## Rondo (`jarvissax/rondo`)

A full Y1 firmware plus app, server, dashboard and web updater.

- App: Kotlin, classic Views, `minSdk 17`, ExoPlayer 2.19.1, OkHttp 3.12.13.
- Firmware: `firmware/build.sh <apk>` downloads the y1-community Android 4.2
  base, edits `system`/`data` with `debugfs` (no mount/root), removes stock apps
  including SystemUI, installs Rondo at `/system/app/Rondo.apk`, adds boot
  logo/animation and `fw_package.ini`/`updater.png`.
- No SystemUI means Rondo owns the wheel click, low-battery warning, boot
  wallpaper and power screen.
- App updates use `pm install -r` with `INSTALL_PACKAGES`; a firmware-level
  change bumps `ro.rondo.firmware` and the APK refuses a too-old firmware.
- Server (Node 22, Fastify, youtubei.js + yt-dlp) and dashboard are optional;
  local music, FM and Bluetooth work without them.
- Update paths: Settings → Software update, dashboard Install, WebUSB page.
  All read `latest.json` published with the release.

Details: `skills/stock-android-roms/SKILL.md`,
`skills/android-apps/SKILL.md`, `skills/y1-hardware/SKILL.md`.

## Choosing an approach

| Goal | Use |
| --- | --- |
| New Home UI on Y1, minimal risk | JJ/Inniclassic APK, or a ROM if it needs system permissions |
| Theme only | Y1 `config.json` theme (Original Software, Better-Y, Solar, Koensayr) |
| Patch stock behaviour without replacing Home | Koensayr-style image patch |
| Full custom Y1 firmware | Rondo's `firmware/build.sh` pattern |
| Streaming/server features | Solar or Rondo (both have network features) |
| Y2 player-first Home | Y2Player or Inniclassic Y2 |

## Source map

| Project | Key paths |
| --- | --- |
| JJ | `ismileblue-y1_launcher/app/src/main/java/com/themoon/y1/`, `README.md` |
| Inniclassic Y1 | `FabianZettl-inniclassic/app/`, `README.md`, `docs/` |
| Inniclassic Y2 | `JonaszPotoniec-inniclassic-y2/app/src/main/java/com/themoon/y1/` |
| Solar | `thesolarproject-solar/app/src/main/java/com/solar/launcher/`, `docs/theming.md` |
| Better-Y | `Leska1337/better-Y/files/`, `build/`, `README.md` |
| Koensayr | `ryan-specter-koensayr-auto/apply.bash`, `src/patches/`, `docs/PATCHES.md` |
| Rondo | `jarvissax-rondo/app/`, `firmware/build.sh`, `docs/building.md` |
