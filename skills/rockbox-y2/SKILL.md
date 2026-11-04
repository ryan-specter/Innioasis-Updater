---
name: rockbox-y2
description: Rockbox for the Innioasis Y2 — hosted Android port, guarded Class A installation, cold-boot routes, controls, themes, recovery and beta limitations. Use for Y2 Rockbox install, packaging or behaviour questions.
---

# Rockbox on the Y2

`spycemagic/y2-rockbox` puts a full-screen Rockbox player inside the Y2's
original Android 4.4.2 firmware. It keeps the stock interface and its guarded
recovery path, and adds selectable cold-boot routes, USB mass-storage return and
normal Rockbox theme support.

> The project supports **only** the Innioasis Y2 on the official Stock 3.1.7
> lineage. Beta V2 is a prerelease. Flashing can erase data or leave the player
> temporarily unbootable.

## Supported hardware

```
Device:            Innioasis Y2
Official firmware: Stock 3.1.7
Android:           4.4.2 / SDK 19
Platform:          MediaTek MT6582
Board:             eastaeon82_wet_kk
```

## Package contract

Beta V2 is distributed **only** as a Class A state-preserving update. Both
platform files are byte-identical, 361,774,260 bytes, SHA-256
`409DDB4D2D18111FB8C3AB619F10F04B916B6B2A3FC04D1D38011324563F326A`:

| Platform | Filename |
| --- | --- |
| macOS | `Y2-Rockbox-Beta-v0.2.0-UPDATE-ONLY.zip` |
| Windows | `Y2-Rockbox-Beta-v0.2.0-Windows-UPDATE-ONLY.zip` |

The ZIP contains exactly eight members:

```
MT6582_Android_scatter.txt  lk.bin  boot.img  recovery.img
logo.bin  system.img  UPDATE-MANIFEST.json  SHA256SUMS.txt
```

The only permitted write set is **UBOOT, BOOTIMG, RECOVERY, LOGO, ANDROID**.
PRELOADER, MBR, EBR1, EBR2, SEC_RO, CACHE, USRDATA and every protected/runtime
partition are excluded. Format All, Firmware Upgrade, whole-device erase,
omitted-partition cleanup, protected-partition writes and automatic retry are
forbidden.

**Never rename the asset to `rom_y2.zip`.** Testing showed the legacy name enters
an unqualified generic full-firmware path that produced non-booting and looping
devices. Do not use a withdrawn Beta V2 archive, `InnioasisUpdater_Setup_1.1.2.exe`,
a Y1 package, or a generic full-format route.

The reviewed Updater CE route (V30) accepts only the repository, release tag,
Windows filename, size and SHA-256 above, and rejects a changed payload or any
write plan outside the five targets.

## Installation

1. Copy internal storage and microSD content to a computer.
2. Back up the complete hidden `.rockbox` directory: themes, playlists, settings
   and databases.
3. Keep an extracted, hash-verified official Stock 3.1.7 recovery package.
4. Charge the player, use a reliable data cable, avoid hubs, and close software
   that may claim MediaTek or Android USB devices.
5. Install with an Updater that explicitly carries the guarded Y2 Class A route.

After the updater reports completed verification:

1. Unplug the Y2 completely.
2. Power it off if necessary.
3. Press and release the bottom pinhole once while unplugged.
4. Start the Y2 normally.

The automatic boot attached to the updater can inherit temporary loader/display
state (upper-screen artifacts, broken screen sleep) and is not the qualified
first boot. A clean post-pinhole boot reaches Rockbox in about 28 seconds.

## Cold-boot routes

Start from a fully powered-off player. Hold a route button before pressing
Power and keep it held until the normal haptic release cue.

| Input | Destination |
| --- | --- |
| No Volume button | Saved normal player; Rockbox by default |
| Volume Up | Opposite player; Stock by default |
| Volume Down | Boot Settings |

Boot Settings changes the no-button route. Volume Up stays the opposite player.
Holding both Volume buttons at once is unsupported.

## Controls and storage

- Centre confirms selections and wakes the display.
- On Now Playing, short Centre toggles play/pause; long Centre opens the
  standard context menu.
- Previous/Next navigate; holding them seeks within a track.
- Short Back returns from the database to Now Playing; long Back from Now
  Playing returns to the database context.
- Play/Pause controls playback; the wheel navigates lists and adjusts volume.
- An optional setting makes held Volume buttons skip tracks while short presses
  keep changing volume.
- For USB Storage, safely eject every mounted Y2 volume on the computer before
  turning USB storage off or unplugging. Rockbox does not resume a paused track
  after USB; that is normal.

## Themes

Use complete 480 × 360 Rockbox themes. Merge the theme's complete `.rockbox`
subtree into the existing directory; never replace or delete the whole tree.
Beta V2 added selectable themes and diagnostics; lyrics/theme diagnostics are a
Beta V3 priority.

## Recovery

Restore the official complete Y2 Stock 3.1.7 package after a failed install,
persistent boot loop, repeated wrong route, missing storage or a persistent
crash dialog. Never substitute a preloader, scatter or recovery from another
device. `SAFETY.md` and `PUBLIC_INSTALL_STRATEGY.md` hold the engineering and
distribution rules.

## What Beta V2 changes

- Bluetooth settings, pairing, A2DP playback, media controls, disconnect and
  reconnect work from both Rockbox and Stock.
- Holding Previous/Next seeks within a track; optional held-Volume track skip.
- Time/date changes persist without freezing the Rockbox UI.
- Wheel vibration is adjustable through true-off and independent of Stock's
  key-vibration setting.
- First-connect and repeated USB Storage flows are stable.
- Clean boot reaches a responsive Rockbox root in about 28 seconds.
- Centre wake, long-Centre Now Playing context, Back/Database navigation,
  PictureFlow recovery and saved Rockbox/Stock routing are proven.

Known rough edges: the final power-down animation, high-resolution FLAC
stability, DAC/wired-audio qualification, PictureFlow polish, and
database/playlist presentation controls. Beta V3 targets these.

## Development layout

The public repository deliberately excludes development evidence and generated
firmware. The useful paths are:

| Path | Contents |
| --- | --- |
| `00_project_docs/` | Safety, install, release records, updater format contract, build/test runbooks |
| `00_tools/` | Per-version WSL build scripts, system-image builders, release assemblers |
| Rockbox submodule/tree | The hosted Rockbox port itself |

The `00_tools/build_rockbox_y2_v*.sh` scripts show the exact per-version patch
and build sequence; `build_y2_rockbox_v*_system.sh` builds the Android system
image. Read the matching `build_rockbox_y2_v*_wsl.sh` before reproducing a
release, and use the release's own source archive for GPL compliance.

## Source map

| Question | File |
| --- | --- |
| Install, reset, cold-boot routes | `spycemagic-y2-rockbox/README.md`, `00_project_docs/Y2_ROCKBOX_BETA_V2_INSTALL_GUIDE.md` |
| Exact package contract | `00_project_docs/Y2_BETA_V2_UPDATER_FORMATS.md` |
| Safety and distribution rules | `00_project_docs/SAFETY.md`, `PUBLIC_INSTALL_STRATEGY.md` |
| Release record | `00_project_docs/Y2_ROCKBOX_BETA_V2_RELEASE.md` |
| Build/test runbooks | `00_project_docs/Y2_V88_*`, `Y2_V89_*` and the `00_tools/` scripts |
