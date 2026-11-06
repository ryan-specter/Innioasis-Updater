---
name: rockbox-y1
description: Rockbox for the Innioasis Y1 — hosted Android port, dual boot with stock, controls, installation and updates, Wi-Fi podcast/Last.fm plugins, theme packages and build layout. Use for Rockbox Y1 behaviour, packaging or theme questions.
---

# Rockbox on the Y1

`rockbox-y1/rockbox` is a Rockbox fork built as a hosted Android application.
It runs on top of the Android 4.2 base ROM, not as bare-metal firmware. The
release is a full `rom_[360p|240p].zip` containing Android plus the Rockbox
system app, or an `update.zip` that Rockbox installs over itself.

## What the port adds

- A full-screen Rockbox UI driven by the Y1 wheel and five buttons.
- Dual boot with a modified **better-Y** stock interface: Rockbox →
  `Main Menu > System > Switch to Stock Firmware`; stock →
  `Main Menu > Settings > Back to Rockbox`.
- Podcast download over the built-in Wi-Fi (`INTERNET.md#podcasts`).
- Last.fm, ListenBrainz and Maloja scrobbling over Wi-Fi
  (`INTERNET.md#scrobbling-lastfm-listenbrainz-maloja`).
- Theme support at 240p and 360p, with a theme pack that includes fonts.
- An FM radio plugin and the usual Rockbox database, EQ, gapless playback and
  PictureFlow.

## Controls

Most controls match the iPod 6G manual. The Y1 exceptions:

| Input | Action |
| --- | --- |
| Centre, short | Accept / Enter |
| Centre, long | Open context menu |
| Centre, very long | Turn off screen |
| Play/Pause, short, in text input | Open keyboard |
| Next + Previous held > 10 s | Restart Rockbox |
| FM radio: Back/Menu | Return to Rockbox |
| FM radio: Previous / Next | Left / Right |
| FM radio: Play short / long | Down / Up |
| FM radio: wheel | Volume |

The wheel mapping is the hosted Android target's
`firmware/target/hosted/android/button-android.c`: every key event posts a
button, so one felt click is two steps, and the vibrator buzzes per step.

## Installation and updating

**Update an existing Rockbox** (`INSTALLATION.md`):

1. Download `update_[360p|240p].zip` from the project's releases.
2. Copy it to `.rockbox/update.zip` on the player (the name must be exactly
   `update.zip`).
3. Eject safely.
4. `Main Menu > System > Firmware Update`; the player restarts when done.

**Full installation** is a firmware flash, not a file copy. With MTKclient,
from the unpacked ROM directory:

```bash
python ../mtk.py w logo,uboot,bootimg,recovery,android,usrdata \
  logo.bin,lk.bin,boot.img,recovery.img,system.img,userdata.img
```

Then connect the powered-off player, wait for completion, unplug and power on.
The SP Flash Tool route uses the `MT6572_Android_scatter.txt` from the same ZIP.

**Manual developer install** requires root and ADB: push
`Rockbox.kl` over `/system/usr/keylayout/Generic.kl`, install the APK at
`/system/app/org.rockbox.apk`, push `librockbox.so` to `/system/lib/`, and put
the remaining `armeabi` libraries in `/data/data/org.rockbox/lib/`. The full
sequence is in `INSTALLATION.md`.

## Quirks that generate bug reports

- **Stuck at the Rockbox logo after a theme change:** delete
  `.rockbox/config.cfg` on the SD card. This is the project's documented fix.
- **Keylock exemptions** sometimes need a second press or time to take effect.
  After a long sleep the wheel can stop sending presses; the project attributes
  this to a power-saving behaviour it cannot control without the wheel driver
  sources.
- **Overriding `.rockbox` files:** language files and similar live in
  `/data/data/org.rockbox/app_rockbox/rockbox/` on internal storage, not in the
  SD card's `.rockbox`. A file with the same path in `.rockbox` takes priority.
  To edit them, extract `update.zip`, rename
  `.../langs/libmisc.so` to `libmisc.zip`, extract it, edit, and copy into
  `.rockbox`.
- **Time cannot be set while Wi-Fi is connected.** Turn off automatic time in
  Android Settings first.
- **The Taptic Engine mod** (iPhone 12 mini motor replacing the original, with
  the speaker removed) is supported by `Settings > General Settings > Keyclick >
  Taptic Engine Mode`.

## Themes

The Y1 has two theme geometries:

- **360p** themes: 480 × 360, the native panel. The project's theme pack and
  `ipodmod3blk-y1` are 360p.
- **240p** themes: the older 320 × 240 layout, still supported by the 240p ROM.

Install a theme by merging its `.rockbox` subtree into the existing `.rockbox`
directory — never replace the whole tree. Font packs are optional but many
themes need them. The site's theme guide is `/rockbox-y1-themes.html`.

`theme-authoring/reference/rockbox-themes.md` explains the `.wps`, `.sbs` and
`.cfg` files. The repository's own `THEMES.md` lists the known 360p themes and
the config reset fix.

## Build layout

The repository is the normal Rockbox tree with a hosted Android target and
Y1-specific changes. Useful paths:

| Path | Contents |
| --- | --- |
| `firmware/target/hosted/android/` | Android button, backlight, audio and power glue |
| `apps/` | Rockbox applications, menus, plugins, theme menu |
| `manual/` | The manual sources, including theme settings |
| `utils/themeeditor/` | Qt theme editor |
| `utils/rbutilqt/` | Rockbox Utility, including theme installation |
| `android/` | Android packaging scripts and `Rockbox.kl` |
| `THEMES.md`, `INTERNET.md`, `MISC.md` | Project-specific guides |

The project builds the Android APK plus the `update.zip` payload; `INSTALLATION.md`
and the release assets are the authority for the exact toolchain. Do not assume
a bare-metal Rockbox `configure --target=` invocation applies to this fork.

## Source map

| Question | File |
| --- | --- |
| Install, update, manual install | `rockbox-y1-rockbox/INSTALLATION.md` |
| Controls and dual boot | `rockbox-y1-rockbox/README.md` |
| Themes and known theme links | `rockbox-y1-rockbox/THEMES.md` |
| Podcasts and scrobbling | `rockbox-y1-rockbox/INTERNET.md` |
| Hardware quirks, keylock, file overrides | `rockbox-y1-rockbox/MISC.md` |
| Button mapping | `rockbox-y1-rockbox/firmware/target/hosted/android/button-android.c` |
