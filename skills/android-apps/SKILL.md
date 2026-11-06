---
name: android-apps
description: Building Android apps for Innioasis players — API 17 (Y1) and API 19 (Y2), wheel input, 480x360 UI, signing and system-app installation, hidden framework APIs and media quirks. Use for app, launcher or service development on either player.
---

# Android apps for the Y1 and Y2

Both players run old AOSP-derived Android with no Google services and a click
wheel. The constraints are closer to a 2013 phone than to a modern device.
Rondo (Y1) and Y2Player (Y2) are the best worked examples of doing it properly.

## Platform matrix

| | Y1 | Y2 |
| --- | --- | --- |
| Android | 4.2.2 | 4.4.2 |
| API | 17 | 19 |
| SoC | MT6572, 2 × A7 | MT6582, 4 × A7 |
| Screen | 480 × 360, mdpi 160, ~250 ppi | 480 × 360 |
| Input | wheel as key events (see below) | wheel via touch/APT32F, nav GPIO keys |
| Storage | microSD `/storage/sdcard0`, internal FAT `/storage/sdcard1` | eMMC + microSD |
| Audio | 44.1 kHz, per-output volume | CS43131 DAC, speaker amp |
| Build | test keys, adbd root on community ROM | production keys, v1 signatures |

`minSdk` 17 covers both. Anything requiring API 21 is out: Jetpack Compose,
Media3, OkHttp 4, Coil, recent Room. Rondo uses classic Views, ExoPlayer 2.19.1
and OkHttp 3.12.13; `androidx.media` 1.6.0 is the last version that works below
API 19.

## Input

### Y1

The wheel is a keyboard. Clockwise is `DPAD_RIGHT`, counter-clockwise
`DPAD_LEFT`, Centre is `ENTER`, Menu is `BACK`, Play/Pause is
`MEDIA_PLAY_PAUSE`, Next/Prev are `MEDIA_NEXT`/`MEDIA_PREVIOUS`. Every detent
sends two pulses (down and up) with the same timestamp, so there is no
auto-repeat; implement long-press with a timer or by counting repeated events.
Full table and quirks: `skills/y1-hardware/SKILL.md`.

Implications:

- Android's own vertical lists ignore left/right. Build your own focus model.
- `Generic.kl` drives every device; do not assume a per-device keylayout.
- Only Power and Centre wake the screen.
- Debounce: JJ drops <40 ms, Inniclassic <15 ms. Pick one and document it.

### Y2

Rockbox and Y2Player see Centre, Back, Play, Prev/Next and volume; the wheel is
read through the touch/APT32F path on stock Android. Preserve the stock
press/hold semantics: short Centre toggles play/pause on Now Playing, long
Centre opens the context menu, holding Prev/Next seeks. Volume Up/Down come from
the keypad, not GPIO.

## UI

- Design at 480 × 360. The Y1 reports mdpi but is physically dense: scale dp
  values (Rondo uses 1.4×) or everything looks tiny.
- The panel refreshes at 36.43 fps on the Y1. Avoid expensive per-frame
  allocation and animated `TransitionDrawable` backgrounds.
- On 4.2, shapes drawn under a scale can be blurry. Draw at final size where
  possible.
- There is no touchscreen on the Y1. Every action must be reachable with the
  wheel and five buttons. On the Y2, touch exists but the wheel is primary.
- Provide a visible focus state. A hidden or clipped focus target makes the app
  unusable.

## Signing and installation

- **Y1 community ROM:** adbd is root and `/system/xbin/su` is setuid, so
  `adb install -r` and `adb push` to `/system` work after `adb remount`.
- **Y2:** stock is not rooted. Install normal APKs with `adb install`; a
  privileged app must be baked into `system.img` (Y2Player uses
  `/system/priv-app/Y2Player.apk`).
- Android 4.4 requires a **v1/JAR signature**. Configure the release build to
  produce one; a v2-only APK fails to install.
- Updating a system app keeps `/system/app/Foo.apk` and runs the `/data/app`
  copy, inheriting the system copy's granted permissions. New permissions need a
  new firmware.
- Same package name + different key = `INSTALL_FAILED_UPDATE_INCOMPATIBLE`.
  Uninstall the old app or sign with the firmware key (Inniclassic's debug-signed
  APKs require uninstalling JJ Launcher first).
- Built-in apps can hold `INSTALL_PACKAGES`, `MOUNT_UNMOUNT_FILESYSTEMS` and
  `SET_WALLPAPER_COMPONENT`; ordinary installs cannot.

## Hidden framework APIs

Reached by reflection (or directly as a system app):

| Need | API |
| --- | --- |
| Wi-Fi join without the touch dialog | `WifiManager.connect(config|netId, listener)` |
| Bluetooth pair/unpair | `BluetoothDevice.createBond`, `removeBond` |
| A2DP connect/disconnect | `BluetoothA2dp.connect`, `disconnect` |
| USB mass storage | `StorageManager.enableUsbMassStorage`, `disableUsbMassStorage` |
| Boot wallpaper | `IWallpaperManager.setWallpaperComponent` |
| MediaTek audio profiles | `AudioProfileManager.setSoundEffectEnabled` |

On the Y1, `isUsbMassStorageEnabled` queries the wrong vold volume and always
returns false; `Environment.getExternalStorageState()` reads `shared` while the
computer owns the card. Poll the card's actual state or listen for the volume
broadcast.

## Media

- **Audio:** one AudioFlinger output at 44.1 kHz; volume is per output (speaker
  0–13 on the Y1). Do not assume a single stream volume.
- **Video:** the Y1's hardware AVC decoder returns `presentationTimeUs = 0` for
  every frame. ExoPlayer 2 then runs ~9 fps and empties the buffer after ~18 s.
  Assign each output frame the smallest pending input timestamp (Rondo's
  `player/TimestampFix.kt`). Resolution changes restart the decoder on API 17;
  change the preferred height in place rather than re-selecting tracks.
- **Codecs:** ExoPlayer 2.19.1 covers the common formats; Inniclassic moved video
  to libVLC because ExoPlayer's frame timing is broken on API 17. Y2Player uses
  one pinned FFmpeg engine for MP3/AAC/ALAC/FLAC/WAV/AIFF/Vorbis/Opus.
- **FM:** the Y1 tuner needs `ACCESS_MTK_MMHW`, the exact `FMRadioNative`
  signatures and a `MediaPlayer` on
  `MEDIATEK://MEDIAPLAYER_PLAYERTYPE_FM`/stream 10. The FM audio switch is
  global; poll `GetFmEnable` and recreate your player if it turns false.
- **TLS:** Android 4.2 has TLS 1.2 off and does not trust Let's Encrypt. Rondo's
  `net/Tls.kt` enables TLS 1.2 and bundles the ISRG roots.
- The log buffer is tiny. Stream `adb logcat -v time -s <TAG>` during a test.

## Storage and file access

- On the Y1 both volumes are mounted `uid=1023,gid=1023` with `fmask=0007`,
  so only `WRITE_EXTERNAL_STORAGE` (which maps to `media_rw`) lets an app list
  them. `READ_EXTERNAL_STORAGE` is not enough.
- There is no reliable MediaProvider scan on the Y1. Walk the card yourself;
  use `MediaMetadataRetriever` for tags/covers and read lyrics from the file.
- Keep app-private state in `/data`; keep user-visible themes, playlists and
  caches on the SD card so an uninstall does not delete them. Inniclassic's
  library cache is `.y1_library_cache.json` at the card root; its scrobbles are
  `.scrobbler.log`.

## Build and test loop

```bash
# Y1 (Rondo example)
cd app
RONDO_SIGNING=/path/to/keystore.properties ./gradlew :app:assembleRelease
adb install -r app/build/outputs/apk/release/app-release.apk

# Y2Player
./tools/build-linux.sh native
./tools/build-linux.sh app
./tools/build-linux.sh release
```

- JDK 17 for Gradle 8.9; newer JDKs can fail to run it.
- Point Gradle at the SDK with `app/local.properties` (`sdk.dir=...`).
- Test on hardware. There is no emulator for the wheel, the FM chip or the
  decoder quirks.
- Install over the firmware copy to test updates; remember the signing rule.
- Keep a stock recovery package for the model you are testing on.

## Packaging into a ROM

If the app is the launcher or needs system permissions, put it in the image:
`/system/app/Foo.apk` (4.2/4.4) or `/system/priv-app/Foo.apk` (4.4 privileged).
Use `debugfs` to replace the file without mounting; see
`skills/stock-android-roms/SKILL.md`. Give the firmware a version property and
have the app refuse updates that need a newer system (Rondo's
`ro.rondo.firmware` pattern).

## Source map

| Question | File |
| --- | --- |
| Y1 device facts, input, FM, video | `jarvissax-rondo/docs/device/README.md` |
| Y1 app implementation | `jarvissax-rondo/app/app/src/main/java/com/jarvissax/rondo/` |
| Y2 player implementation | `schulzcode-Y2Player/app/src/main/kotlin/com/schulzcode/y2player/` |
| Y2 build/firmware pipeline | `schulzcode-Y2Player/tools/build-linux.sh`, `docs/` |
| Launcher patterns | `skills/launchers/SKILL.md` |
| Signing/package collision | `FabianZettl-inniclassic/README.md` |
