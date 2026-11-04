---
name: y1-hardware
description: Innioasis Y1 hardware and firmware internals — MT6572 SoC, click-wheel key events, 480x360 display, audio/FM/video paths, storage, partition map and flashing. Use for any Y1 driver, input, ROM, app or recovery work.
---

# Innioasis Y1 hardware

The Y1 is a MediaTek MT6572 Android 4.2 player with a click wheel. Almost every
"the wheel doesn't work" or "the app can't see the SD card" bug is explained by
the facts below. They were collected by the Rondo project on a Type A player
running the community Android 4.2 base and are reproduced in
`jarvissax-rondo/docs/device/README.md` with the raw `getevent`, `dumpsys` and
`/proc` captures next to them.

## Quick facts

| Item | Value | Source |
| --- | --- | --- |
| SoC | MediaTek MT6572, 2 × Cortex-A7 with NEON/VFPv4 | `docs/device/proc-cpuinfo.txt` |
| RAM | 494,376 kB visible | `docs/device/proc-meminfo.txt` |
| OS | Android 4.2.2, API 17, kernel 3.4.5, `ALPS.JB3.MP` | `docs/device/proc-version.txt` |
| Display | 480 × 360, density 160 (`mdpi`), panel about 250 ppi, 36.43 fps | `dumpsys-display.txt`, `lcd-density.txt` |
| Display id | `Y1_001` | Rondo device notes |
| Storage | microSD + internal FAT partition + 629 MB `/system`, 1.9 GB `/data`, 503 MB `/cache` | Rondo device notes |
| Wi-Fi | 2.4 GHz only, MediaTek combo radio | Rondo device notes |
| FM | MT6627-class, `/dev/fm`, `libfmjni.so` | Rondo device notes |
| Buttons | Wheel + Centre + Menu + Play/Pause + Next + Prev + Power | `getevent-*.txt` |

### Type A and Type B

Two Y1 hardware revisions exist. **Type A** is the common one and shipped with
software 2.0.0 or later; **Type B** is an early low-volume revision. Packages
are named `rom.zip` for Type A and `rom_type_b.zip` for Type B
(`y1-community/y1-ata-rom/README.md`). The preloader for the ROMs seen so far is
`preloader_g368_nyx.bin`; the kernel image is `kernel_g368_nyx.bin`. Do not
assume a Type B file works on Type A, and never cross-flash a preloader.

## Input: the wheel is a keyboard, not a touch ring

Every detent produces an instantaneous press and release on
`/dev/input/event2` (`mtk-tpd`). There is no axis, no touch ring, and no hold or
auto-repeat from the wheel itself.

| Physical control | Device | Linux key (scancode) | Android keycode |
| --- | --- | --- | --- |
| Wheel clockwise | `event2` `mtk-tpd` | `KEY_DOWN` (108) | `DPAD_RIGHT` (22) |
| Wheel counter-clockwise | `event2` `mtk-tpd` | `KEY_UP` (103) | `DPAD_LEFT` (21) |
| Centre | `event0` `mtk-kpd` | `KEY_REPLY` (232) | `ENTER` (66), `WAKE_DROPPED` |
| Menu (top) | `event2` | `KEY_BACK` (158) | `BACK` (4) |
| Play/Pause (bottom) | `event2` | `KEY_PLAYPAUSE` (164) | `MEDIA_PLAY_PAUSE` (85) |
| Next (right) | `event2` | `KEY_RIGHT` (106) | `MEDIA_NEXT` (87) |
| Prev (left) | `event2` | `KEY_LEFT` (105) | `MEDIA_PREVIOUS` (88) |
| Power | `event0` `mtk-kpd` | `KEY_POWER` (116) | `POWER`, `WAKE` |

Consequences that matter when writing an app or a driver:

- **Two pulses per felt click.** Three counted clicks produced six events; five
  produced ten. Treat one pulse as one step (Rockbox and Rondo do) or halve the
  count, but be consistent. Rondo's `input/WheelInput.kt` counts one step per
  pulse.
- **A fast spin sends pulses about 40 ms apart.** Debounce thresholds in the
  launchers differ: JJ drops steps under 40 ms, Inniclassic under 15 ms.
- **Only Power and Centre wake the screen.** The wheel and media keys do not.
- **Android's own vertical lists ignore `DPAD_LEFT/RIGHT`.** Settings and the
  "Complete action using" dialog cannot be driven by the wheel. Apps that need
  wheel navigation must implement their own list focus.
- **`Generic.kl` is loaded for every device** (`mtk-tpd`, `mtk-kpd`,
  `mtk-tpd-kpd`, virtual keyboard). A `mtk-kpd.kl` exists but is not applied for
  vendor 0x2454/product 0x6572. Editing `Generic.kl` changes every button.
- **The click sound is SystemUI's, not the app's.** A pulse plays
  `FX_KEY_CLICK` from `com.android.systemui` while
  `Settings.System.SOUND_EFFECTS_ENABLED` is 1. MediaTek's `audioprofile`
  service restores its own value at boot, so an app that wants the setting to
  stick must also call `setSoundEffectEnabled(profile, on)` by reflection
  (Rondo does).
- **The vibrator** is `/sys/class/timed_output/vibrator`; the MTK driver runs it
  for at least 60 ms. Rockbox maps intensity to 5 ms per level plus 20/8/2/0 ms
  as a spin continues. Inject real pulses for tests with `sendevent` (adb is
  root on the community ROM).

## Display and drawing

The panel is 480 × 360 and reports `mdpi`, so 1 dp = 1 px, but the physical
density is about 250 ppi: mdpi sizes look tiny. Rondo scales everything through
`dp()` (1.4× by default). The compositor refreshes at 36.43 fps, and `wm` does
not exist on 4.2 — do not build tooling that calls it.

Android 4.2's GPU renderer has quirks the Rondo project documented: shapes drawn
under a scale come out blurry, and `TransitionDrawable` backgrounds stall. Use
plain shapes and avoid animated transition drawables on this device.

## Audio, FM and video

- One AudioFlinger output thread at 44.1 kHz.
- **Volume is per output.** Speaker music steps 0–13; wired headphones keep
  their own level. `input keyevent KEYCODE_VOLUME_DOWN` changes only the active
  output.
- The video decoder's audio partner is `OMX.MTK.AUDIO.DECODER.AAC`.
- **FM radio** uses the MT6627-class tuner. `/dev/fm` is `crw-rw---- system
  media`; requesting `android.permission.ACCESS_MTK_MMHW` puts an ordinary app
  in the `media` (1013) and `camera` groups. `libfmjni.so` registers 33 natives
  on `com/mediatek/FMRadio/FMRadioNative` and 24 on
  `com/mediatek/FMTransmitter/FMTransmitterNative`; both Java classes must exist
  with the exact signatures or the library will not load. Band 76–108 MHz,
  100 kHz steps, RDS, 50 µs de-emphasis
  (`/system/etc/fmr/mt6627_fm_cust.cfg`).
- **FM audio is a global switch.** Every `FMAudioPlayer` sends
  `AudioSetFmDigitalEnable=0` when reset or destroyed, and the stock app keeps an
  idle player alive from `Y1Application.onCreate`. If the stock process is
  killed, every other app's FM goes silent while the chip stays tuned. Check
  `getParameters("GetFmEnable")` while playing and recreate the player when it
  turns false (Rondo polls once a second and recovers in about 0.5 s).
- **Video timestamps are broken.** The hardware AVC decoder returns
  `presentationTimeUs = 0` for every frame. ExoPlayer then renders about 9 fps,
  races ahead of audio and empties the buffer after ~18 s. Rondo's
  `player/TimestampFix.kt` assigns each output frame the smallest pending input
  timestamp, which restores 25.0 fps at 360p/480p/720p. Resolution changes
  restart the decoder on API 17; keep one adaptive selection and change the
  preferred height in place.
- The log buffer is tiny. Stream `adb logcat -v time -s Y1:V` during tests
  instead of reading it afterwards.

## Storage and permissions

- The microSD card is `/storage/sdcard0` (vfat). `/storage/sdcard1` is a 433 MB
  FAT partition on internal flash.
- Both are mounted `uid=1023,gid=1023` (media_rw) with `fmask=0007,dmask=0007`,
  so other apps cannot even list them. On this firmware's `platform.xml` only
  `WRITE_EXTERNAL_STORAGE` maps to `media_rw`; `READ_EXTERNAL_STORAGE` is not
  enough.
- There is no reliable MediaProvider scan. Walk the card yourself and read tags
  with `MediaMetadataRetriever`; FLAC tags and embedded covers work on 4.2,
  lyrics do not (read them from the file).
- The updater deletes the ZIP it unpacked and reuses an extraction folder keyed
  by ZIP filename. A rebuilt `rom.zip` with the same name can flash the old
  images. Give every build a unique name or delete the extracted folder
  (`docs/device/README.md`, "The Rondo firmware").

## Battery and clock

There is no fuel gauge: `/sys/devices/platform/battery_meter/FG_*` reads 0.
`/sys/class/power_supply/battery/BatteryAverageCurrent` (mA) is the only current
reading and shows charging current on USB, so measure discharge unplugged (adb
over Wi-Fi). Automatic time is on, but the timezone defaults to `Asia/Shanghai`
and there is no modem to correct it.

## Network

Wi-Fi is 2.4 GHz only. A scan entry named `NVRAM WARNING: Err = 0x10` is
MediaTek's sign that calibration and MAC are not provisioned; the MAC changes on
every Wi-Fi start. There is no `wpa_cli`; switch Wi-Fi with
`svc wifi disable|enable`. On some hotspots ~70% of new TCP connections are
refused instantly with `EHOSTUNREACH` while established connections work, so
retry connects (Rondo retries every 250 ms, up to 20 times).

## Partition map and flashing

The Y1 package contains these partition images
(`y1-community/y1-ata-rom/README.md`):

```
EBR1  EBR2  MBR  kernel  kernel_g368_nyx.bin  ramdisk-recovery.img
ramdisk.img  secro.img  system.img  userdata.img  boot.img  cache.img
lk.bin  logo.bin  preloader_g368_nyx.bin
```

- `system.img`, `userdata.img` and `cache.img` must be **desparsed with
  `simg2img`** before packaging: MTKclient on macOS/Linux prefers raw images.
- A Windows-portable package also carries SP Flash Tool and a preconfigured
  `history.ini` so the GUI finds the files with relative paths.
- Name the archive for the hardware: `rom.zip` (Type A), `rom_type_b.zip`
  (Type B), and compress with Deflate at maximum.
- The full package writes every partition, including userdata. There is no
  non-destructive "keep data" guarantee inside the ZIP.

`firmware-packages/SKILL.md` covers the archive contract, the Updater manifest
and the release checklist. `stock-android-roms/SKILL.md` covers editing
`system.img` without mounting it.

## Development entry points on a running Y1

- adbd runs as root (`ro.secure=0`, `ro.debuggable=1`); `/system/xbin/su` is
  setuid root on the community ROM.
- The stock UI is `com.innioasis.y1`; its home activity is
  `com.innioasis.y1/.activity.SplashActivity` (MAIN + HOME, no LAUNCHER, so
  `getLaunchIntentForPackage` returns null).
- The Android 4.2 base ROM ships Rockbox at `/system/app/org.rockbox.apk` and
  `/system/etc/init.d/99Y1ButtonScript`: holding Back + Play for 10 s enables
  Rockbox, disables the stock UI, copies `Rockbox.kl` over `Generic.kl` and
  restarts.
- Rondo's `firmware/build.sh` is the cleanest worked example of editing the
  base images with `debugfs` and repacking a flashable ROM.

## Source map

| Question | File |
| --- | --- |
| Input, display, storage, FM, video, updater quirks | `jarvissax-rondo/docs/device/README.md` and the captures beside it |
| Base ROM package rules and partition list | `y1-community/y1-ata-rom/README.md` |
| Wheel handling and haptics in an app | `jarvissax-rondo/app/app/src/main/java/com/jarvissax/rondo/input/` |
| Rockbox button mapping | `rockbox-y1-rockbox/firmware/target/hosted/android/button-android.c` |
| Rooted stock patch examples | `ryan-specter-koensayr-auto/` |
| Stock launcher patch examples | `Leska1337/better-Y/` |
