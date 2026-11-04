---
name: y2linux
description: Y2Linux and Reborn — Linux 6.18 kernel and MT6582 device tree, Buildroot rootfs, Rust platform services, OTA/recovery, partition ownership and build environment. Use for kernel, driver, platform or install work on the Y2 Linux port.
---

# Y2Linux

Y2Linux replaces Android on the Y2's internal storage with a Buildroot Linux
system and the Rust **Reborn** player. It leaves bootloaders, calibration and
factory partitions untouched. It is a different world from the Android
firmware: no Java, no adb, no Android services, and no Python on the player.

## Current shape

| Item | Value |
| --- | --- |
| Kernel | Linux 6.18 long-term, `6.18.56-y2linux-1.0.0-beta.9.3.7` at baseline 215 |
| Root filesystem | `2026.08-platform-v1.238` (Buildroot 2026.08) |
| Platform | `y2-platform` Rust services: battery, sleep, Wi-Fi, Bluetooth, storage, update, USB, reports |
| Player | Y2Reborn, Rust, OpenGL ES on Mali-400 via DRM + Lima, FFmpeg, SQLite |
| Bluetooth | SBC, AAC (fdk-aac-free), LDAC; BlueZ 5.87, BlueALSA |
| Main components | GCC 15.3/glibc 2.44, Mesa 26.2.4, FFmpeg 9.0.2, OpenSSL 4.0.3 |
| Hardware | Y2 board `eastaeon82_wet_kk`, MT6582, 7.8 GB eMMC, stock 3.2.0 FM |

Supported panels: **GC9503V and ST7701S**. Sleep current is about 2 mA on the
developer's player; stock is about 1.3 mA. The radio firmware is proprietary and
is taken from the owner's stock package; it is not in the repository or images.

## Source layout

| Path | Contents |
| --- | --- |
| `kernel/` | Config, device tree, platform drivers (`kernel/platform`, `kernel/usb`, `kernel/audio`), Linux 6.18 overlay patches |
| `buildroot/` | External tree: defconfig, board overlays, local packages (Reborn, connectivity, MTP, updater) |
| `initramfs/` | Boot rescue and handover to the internal root filesystem |
| `platform/` | `y2-platform` service and CLI; `platform/CONTRACT.md` is the API boundary |
| `tools/build/` | Locked, network-isolated kernel build environment (bubblewrap) |
| `tools/production/` | Production build, packaging, validation, releases |
| `tools/host/` | Desktop transfer, diagnostics, qualification, audio fixtures |
| `tools/connectivity/` | Wi-Fi/Bluetooth services and stock radio provisioning |
| `tests/` | Host and container suites (`tools/production/tests.sh`) |
| `docs/` | Architecture, build, validation and current-state records |

## Device tree facts you must preserve

The Y2 hardware dossier is `skills/y2-hardware/SKILL.md`. When touching the
kernel, these are the load-bearing parts:

- PMIC **MT6323** on PWRAP; charger uses ADC channels 7/5/6/3; power-off on a
  charger intentionally restarts into LK charging mode.
- DAC **CS43131** on I²C1 `0x30`, rails GPIO 20 → 18 → 15 with a 50 ms settle;
  `VGP2` is runtime-PM owned and can be off while the DAC is idle.
- Speaker amp **AW87559/OCA72559** on I²C1 `0x58`, enable GPIO 8.
- Wheel **APT32F** on I²C0 `0x51`, IRQ GPIO 55, reset GPIO 56.
- Navigation GPIO 6/7/9/10/54; volume keys through the MT6582 keypad.
- eMMC `mmc0` 1-bit 13 MHz; microSD `mmc1` 1-bit 13 MHz, broken card detect.
- Panel GC9503V with `innioasis,lk-powered`; ST7701S also supported.
- UART0 console **921600 8N1**.
- CPU OPPs 598 MHz–1.3 GHz; DVFS owned by PWRAP/SPM, never written by a driver.
- Reserved memory: loader gap `0x81800000` (40 MiB), radio `0xbdf00000`
  (33 MiB), ramoops at `0xbde00000` (1 MiB).

The partition map and boot-image contract are in `skills/y2-hardware/SKILL.md`.
Y2Linux uses BOOTIMG for its kernel + DT + initramfs and RECOVERY for the
recovery variant; the only difference in the tree is `Y2_RECOVERY` and the
`y2.recovery=1` bootarg.

## Building

The kernel build environment is pinned and network-isolated. From the repository
root (`docs/build/environment.md`):

```bash
python3 tools/build/prepare.py             # fetch exact locked inputs, verify, reconstruct
python3 tools/build/prepare.py --offline   # same checks; missing cache fails
python3 tools/build/run.py --output out/smoke -- sh /project/tools/build/smoke.sh
```

Host requirements: Linux, Python 3.12+, bubblewrap, unprivileged user
namespaces. No Docker daemon and no host package installation. The lock pins the
Linux archive SHA-256 (`9106a460…ced4b`), 31 audited source files and 38 Alpine
APK archives. Changed locks fail closed; reconstruct in a fresh cache instead of
updating packages.

Production builds, first-install images, OTA signing and releases live in
`tools/production/` and are documented in `docs/BUILDING.md`. The platform gate
must print `GATE OK` before every commit:

```bash
tools/development/platform-gate.sh
```

The gate runs `tools/development/code-quality.py`, a ratchet over production
code (function/file length, `unsafe`, `unwrap`, panics, lint exceptions, raw
JSON lookups, unformatted lines, TODO markers) against
`code-quality-baseline.json`. Length limits are ceilings: functions 150 lines,
files 1500.

## Platform services and update model

- `y2-platform` owns battery, sleep, Wi-Fi, Bluetooth, storage, update, USB and
  error reports; Reborn is a client. `platform/CONTRACT.md` and the
  `docs/architecture/platform-*.md` files define the typed records.
- Bluetooth has one owner, the radio daemon `y2-radiod`: `y2-bt-reconnect`,
  `bluetooth-power`, the intent file and operation/PCM locks are gone from the
  old design. Reborn is a client. BlueALSA patches cover LDAC under the Wi-Fi
  ceiling, learned start rates per headset, and AAC channel-bit quirks.
- Wi-Fi and Bluetooth share an antenna. A codec ceiling file
  (`/run/y2/bt-codec-ceiling`) caps AAC/SBC while Wi-Fi is on; Reborn applies a
  refused codec choice at the next pause.
- Sleep is a multi-step platform operation with a journal; a refusal is proven
  by `suspend_stats` and retried, not quarantined blindly. Do not bypass the
  helper's radio quiesce or wake-IRQ handling.
- Updates are signed OTA packages with rollback protection; `/data` is
  rollback-safe and the critical path fails closed with one reason. See
  `docs/architecture/platform-ota-v2.md`, `update-model.md`,
  `ota-recovery-install.md`.
- Recovery is independent: `docs/architecture/production-recovery.md` and
  `production-install.md`. Restore Previous System is a supported path; keep its
  battery gate.

## Installation and returning to stock

- Install from the project's release images; do not hand-write partitions.
- The first install replaces Android on internal storage. Bootloaders,
  calibration and factory partitions are untouched.
- Going back to stock does **not** restore the old storage format: copy music
  off first, then let stock Android format the storage.
- A Y2 with a different board, storage size or partition table is unsupported
  until verified.
- The kernel and platform images are GPL-2.0; Reborn is MIT. Each release
  carries the corresponding sources. The proprietary radio firmware is not
  redistributed.

## Known issues worth checking before blaming a change

- Rare spontaneous power-offs during playback; cause unknown.
- Bluetooth after a pause longer than ~20 s can drop once; pressing play during
  the reconnect can stay silent until the headset returns.
- Speaker uses the headphone volume scale; its loudest step is the stock
  speaker's. Start low.
- HLS-only radio stations (e.g. BBC) do not play yet; FM radio is planned.
- Only one hardware revision has been tested closely.

## Source map

| Question | File |
| --- | --- |
| Current state and known issues | `schulzcode-y2linux/readme.md`, `docs/CURRENT_PLATFORM_STATE.md` |
| Device tree | `kernel/dts/innioasis-y2.dts` |
| Boot image layout | `docs/build/bootimg-format.md` |
| Locked build environment | `docs/build/environment.md` |
| Production install/recovery | `docs/architecture/production-install.md`, `production-recovery.md` |
| Partitions | `docs/architecture/production-partitions.json` |
| Platform API | `platform/CONTRACT.md`, `docs/architecture/platform-*.md` |
| Radio daemon | `docs/architecture/radio-daemon.md` |
| Skins | `SchulzCode-Y2Reborn/docs/skins.md` and `theme-authoring/reference/reborn-skins.md` |
