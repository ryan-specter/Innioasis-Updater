---
name: y2-hardware
description: Innioasis Y2 hardware and boot internals — MT6582 board, device tree, GPIO/I2C map, GC9503V/ST7701S panels, CS43131 DAC, MT6323 PMIC, partition table and Android boot image. Use for Y2 kernel, driver, ROM, Rockbox or Y2Linux work.
---

# Innioasis Y2 hardware

The Y2 is a MediaTek MT6582 Android 4.4 player. It is **not** a bigger Y1: the
SoC, boot chain, partition table, input device and audio path are all different.
The authoritative board description is the Y2Linux device tree
(`schulzcode-y2linux/kernel/dts/innioasis-y2.dts`), which was derived from the
stock and donor device trees and checked against the hardware.

## Quick facts

| Item | Value | Source |
| --- | --- | --- |
| SoC | MediaTek MT6582, 4 × Cortex-A7, 598 MHz–1.3 GHz OPPs | `innioasis-y2.dts` |
| GPU | Mali-400 MP2 (GP + 2 PP cores), hwirqs 202–207 | `innioasis-y2.dts` |
| RAM | 992 MB at `0x80000000` (`0x3e000000`) | `memory@80000000` |
| Storage | 7.8 GB eMMC (user capacity 7,784,103,936 bytes in the stock layout) | `docs/architecture/production-partitions.json` |
| OS (stock) | Android 4.4.2, API 19, board `eastaeon82_wet_kk` | Y2 Rockbox README |
| Stock firmware | 3.1.7 (Rockbox qualification), 3.2.0 FM (Y2Linux qualification) | project READMEs |
| Display | 480 × 360, MIPI-DSI | device tree |
| Panel | GC9503V (`innioasis,y2-gc9503v`); ST7701S also shipped and supported by Y2Linux | DTS + Y2Linux README |
| DAC | Cirrus CS43131 on I²C1 address `0x30` | `i2c1` node |
| Speaker amp | AW87559 (or OCA72559), I²C1 `0x58`, enable GPIO 8 | `amplifier@58` |
| PMIC | MediaTek MT6323 on PWRAP `0x1000d000`, IRQ on GPIO 25 | `pwrap` node |
| Wheel | APT32F controller on I²C0 `0x51`, IRQ GPIO 55, reset GPIO 56 | `wheel@51` |
| Navigation keys | GPIO 6 (Prev), 7 (Menu), 9 (Next), 10 (Play), 54 (Select) | `navigation-keys` |

Only one hardware revision has been tested closely. A Y2 with a different
board, storage size or partition table is unsupported until someone verifies it
(`schulzcode-y2linux/readme.md`, "Supported hardware").

## Board map from the device tree

### Power and audio

- CS43131 rails are sequenced GPIO 20 → 18 → 15, then a 50 ms settle; the
  regulator names are `cs43131-en20`, `en18`, `en15`. `VGP2` feeds the codec and
  is no longer always-on: runtime PM and `vgp2_idle_off` own it.
- The speaker amplifier is enabled by GPIO 8 (low 10 ms, high, 100 ms). Low is
  off and the amp does not answer.
- Haptics use the `regulator-haptic` binding on the `vibr` LDO: a rumble
  switches it on, magnitude selects 1.8/2.0/2.8 V, and memless timing ends it.
  Stock timing is 50 ms at VOSEL 5 (2.8 V).
- The PMIC charger node uses ADC channels 7 (battery voltage), 5 (baton),
  6 (isense) and 3 (PMIC temperature). Powering off on a charger restarts into
  LK's charging mode (`innioasis,rgu`), which is intentional stock behaviour.

### Storage, USB and connectivity

- `mmc0` (`innioasis,y2-mmc`) is the non-removable eMMC root: 1-bit bus, 13 MHz,
  no SD/SDIO, write-protect disabled.
- `mmc1` (`innioasis,y2-sd`) is the microSD slot: 1-bit, 13 MHz, broken card
  detect, no MMC/SDIO. Slow but sufficient; do not raise the clock without
  signal-integrity evidence.
- USB is a peripheral-only MUSB controller at `0x11200000` with its PHY at
  `0x11210800`. There is no host mode and no fabricated fixed USB clock.
- The connectivity block is `innioasis,y2-mt6582-connectivity` at
  `0x18070000`, with the modem/radio reserved region at `0xbdf00000`
  (33 MiB). Bluetooth, Wi-Fi and FM share this MediaTek combo radio. The
  proprietary radio firmware is not redistributable and is taken from the
  owner's stock package.

### Input

- Navigation buttons are `gpio-keys-polled`, 20 ms poll:
  GPIO 6 → `KEY_LEFT`, 7 → `KEY_BACK`, 9 → `KEY_RIGHT`, 10 → `KEY_PLAYPAUSE`,
  54 → `KEY_ENTER`.
- Volume Up/Down come from the MT6582 keypad at `0x10011000`, not GPIO.
- On Y2Linux the wheel is an APT32F controller on I²C0 address `0x51`, with an
  edge interrupt on GPIO 55 and an active-low reset on GPIO 56; the
  `innioasis,apt32f-wheel` driver reads it. Stock Android reaches the wheel
  through its vendor input stack, which is not the Linux driver. When porting,
  preserve the stock reset/suspend sequence.
- Rockbox on Y2 has its own mapping (see `rockbox-y2/SKILL.md`): Centre wakes
  and confirms, short Centre toggles play/pause on Now Playing, long Centre
  opens the context menu, holding Prev/Next seeks, Back returns to Now Playing.

### Display

- MIPI-DSI at `0x1400c000`, MIPI TX PHY at `0x10010000`, DSI clock from the
  26 MHz crystal.
- The panel node is `innioasis,y2-gc9503v`, reset through MMSYS reset 0,
  backlight through `innioasis,y2-backlight`, and marked `innioasis,lk-powered`
  because LK has already powered it.
- Y2Linux supports both GC9503V and ST7701S panels; do not hard-code panel
  timings in an app or a bootloader change without checking which panel the
  unit has.
- UART0 is the debug console at **921600 8N1** (`console=ttyS0,921600n8`).
  Early boot logs are available there before USB or Wi-Fi.

### Clocks, thermal and watchdog

- The clock controller spans `0x10000000`, `0x10003000`, `0x10001000` and
  `0x10209000`; `clk26m` and the 32.768 kHz RTC clock are fixed inputs.
- CPU OPPs are 598 MHz, 747.5 MHz, 1.04 GHz, 1.196 GHz and 1.3 GHz, all at
  1.15–1.25 V. DVFS is owned by PWRAP/SPM; do not write VPROC from a driver.
- Thermal trips: CPU passive 110 °C, critical 120 °C; PMIC critical 150 °C.
- Watchdog is `mediatek,mt6582-wdt` at `0x10007000`.

## Boot chain and boot image

```
Boot ROM → PRELOADER (eMMC boot region) → LK / UBOOT (lk.bin)
        → boot.img (kernel + DT + initramfs) → Android or Linux
```

- LK's load address is `0x80008000`, entry `0x84000000`. These are the real
  addresses; the legacy Android header fields below are not.
- The stock `boot.img` uses the Android header (`ANDROID!`), 2048-byte pages,
  `kernel_addr=0x10008000`, `ramdisk_addr=0x11000000`,
  `second_addr=0x10f00000`, `tags_addr=0x10000100`, zero second/DT sizes and an
  empty cmdline.
- Each MTK payload is wrapped in a 512-byte header: little-endian magic
  `0x58881688`, inner byte length, 32-byte NUL-padded name (`KERNEL` or
  `ROOTFS`), then 472 bytes of `0xff`. Y2Linux writes `Y2Linux-M1` as the name.
- The Linux boot image is: Android header page + page-padded wrapped kernel +
  page-padded wrapped initramfs + **two explicit zero pages**. Its size must
  equal `2048 + align_up(K,2048) + align_up(W,2048) + 4096` and must fit the
  16 MiB `BOOTIMG` partition. See `schulzcode-y2linux/docs/build/bootimg-format.md`.

## Partition table

From `schulzcode-y2linux/docs/architecture/production-partitions.json`, user
capacity 7,784,103,936 bytes. Offsets are the runtime view; the scatter's
linear offsets differ by the 20 MiB preloader span.

| Partition | Size | Runtime offset | Contents |
| --- | --- | --- | --- |
| PRELOADER | 20 MiB span (`EMMC_BOOT_1`) | — | Boot ROM handoff, `preloader_eastaeon82_wet_kk.bin` |
| MBR | 512 KiB | `0x0` | Stock partition table |
| EBR1 | 512 KiB | `0x80000` | Extended partition table |
| PRO_INFO | 3 MiB | `0x100000` | Device/product identity, **do not touch** |
| NVRAM | 5 MiB | `0x400000` | Calibration and MAC, **do not touch** |
| PROTECT_F | 10 MiB | `0x900000` | Protected device data |
| PROTECT_S | 10 MiB | `0x1300000` | Protected device data |
| SECCFG | 128 KiB | `0x1d00000` | Security configuration |
| UBOOT | 384 KiB | `0x1d20000` | `lk.bin` |
| BOOTIMG | 16 MiB | `0x1d80000` | `boot.img` |
| RECOVERY | 16 MiB | `0x2d80000` | `recovery.img` |
| SEC_RO | 6 MiB | `0x3d80000` | `secro.img` |
| MISC | 512 KiB | `0x4380000` | Boot/recovery control |
| LOGO | 3 MiB | `0x4400000` | `logo.bin` |
| EBR2 | 512 KiB | `0x4700000` | Second extended table |
| EXPDB | 10 MiB | `0x4780000` | Legacy crash records |
| ANDROID | 820 MiB | `0x5180000` | `system.img` (ext4, `Y2ROOT` label in Y2Linux) |
| CACHE | 126 MiB | `0x38580000` | `cache.img` |
| USRDATA | 800 MiB | `0x40380000` | `userdata.img`, destructive first init |
| FAT | dynamic (~5.5 GiB) | `0x72380000` | Internal shared storage |
| BMTPOOL | 21 MiB | sentinel `0xfebf00a8` | Vendor sentinel, **do not touch** |

The exact stock scatter is the authority. A package must not invent offsets or
sizes, and a partial update must name only the partitions it writes.

## What is safe to flash

Rockbox Y2's qualified Class A update writes exactly five targets: **UBOOT
(`lk.bin`), BOOTIMG (`boot.img`), RECOVERY (`recovery.img`), LOGO (`logo.bin`),
ANDROID (`system.img`)**. It explicitly excludes PRELOADER, MBR, EBR1, EBR2,
SEC_RO, CACHE, USRDATA and every protected/runtime partition, and forbids
"format all", "firmware upgrade", erase and automatic retry
(`spycemagic-y2-rockbox/00_project_docs/Y2_BETA_V2_UPDATER_FORMATS.md`).

Y2Linux replaces Android on internal storage but leaves bootloaders, calibration
and factory partitions untouched. Going back to stock does not restore the old
storage format; copy music off first.

## After a Y2 flash

The mandatory reset is physical: unplug the player, power it off, press and
release the bottom pinhole once while unplugged, then boot normally. An
automatic boot attached to the Updater can inherit temporary loader/display
state (upper-screen artifacts, broken screen sleep) and is not a qualified first
boot. A clean boot reaches Rockbox in about 28 seconds.

## Source map

| Question | File |
| --- | --- |
| Full board description, GPIOs, regulators, panels | `schulzcode-y2linux/kernel/dts/innioasis-y2.dts` |
| Production partition map and classification | `schulzcode-y2linux/docs/architecture/production-partitions.json` |
| Boot image layout and MTK wrapper | `schulzcode-y2linux/docs/build/bootimg-format.md` |
| Y2 Rockbox package contract | `spycemagic-y2-rockbox/00_project_docs/Y2_BETA_V2_UPDATER_FORMATS.md` |
| Y2 Rockbox install and recovery | `spycemagic-y2-rockbox/00_project_docs/Y2_ROCKBOX_BETA_V2_INSTALL_GUIDE.md`, `SAFETY.md` |
| Y2 stock base and build pipeline | `schulzcode-Y2Player/docs/` and `tools/build-linux.sh` |
| Android 4.4 system image work | `stock-android-roms/SKILL.md` |
