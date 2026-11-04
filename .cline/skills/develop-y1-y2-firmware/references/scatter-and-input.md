# Scatters, partitions and input maps

## Platform facts

| Model | SoC | Scatter project | Table |
|---|---|---|---|
| Innioasis Y1 | MT6572 | `eastaeon72_wet_jb3` | MBR/EBR |
| Innioasis Y2 | MT6582 | `eastaeon82_wet_kk` | MBR/EBR |
| Timmkoo Q5 | MT6580 | `eastaeon80_wet_kk` | MBR/EBR |
| Innioasis G1 | MT6753 | `k53v1_64_bsp` | GPT |
| Innioasis PR1 | MT6765 | `k62v1_64_bsp` | GPT |
| Innioasis SR1 | — | `j5052` | GPT |
| Innioasis R1 | — | `g368_nyx` | GPT |

Timmkoo / Innioasis A5 is MT6572 and shares the Y1-era engine. The full
recognised lineup, filename tokens and variants live in
`assets/device_models.xml`.

## Scatter anatomy

```yaml
- general: MTK_PLATFORM_CFG
  info: MT6572
  platform: MT6572          # required by SP Flash Tool's console config
  storage: EMMC             # NAAN/EMMC/UFS/NOR/SDMMC
  boot_channel: MSDC_0
  block_size: 0x20000
- partition_index: SYS0
  partition_name: PRELOADER
  file_name: preloader.bin
  is_download: true
  type: SV5_BL_BIN
  linear_start_addr: 0x0
  physical_start_addr: 0x0
  partition_size: 0x40000
  region: EMMC_BOOT_1
  storage: HW_STORAGE_EMMC
  boundary_check: true
```

Rules that matter when you build a package:

- `platform` and `storage` must be present and correct — the console config is
  built from them, and a wrong chip is worse than no flash.
- `file_name` is resolved **relative to the scatter**, which is why staging
  copies the images next to it.
- `is_download: false` means "present but not written" (e.g. a layout-only
  partition). Overlay firmwares use this to leave base partitions alone.
- Legacy MBR devices: `linear_start_addr` is biased from `physical_start_addr`
  (Y2 by 20 MB / `0x1400000`). Do not use either as a write offset; the engine
  reads the live MBR chain and calibrates.
- The preloader belongs in `EMMC_BOOT_1` (`region`), not `EMMC_USER`, and is
  written last through the boot1 path with an `EMMC_BOOT`/`BRLYT` header.

## Variants you will meet

| Variant | How it appears | Consequence |
|---|---|---|
| Y1 Type A / Type B | `rom_type_a*.zip`, `type_a` in the name | different scatter/layout; never cross-flash |
| 360p vs 240p | Rockbox `_240` / `240p` zips | different display build; 240p takes the theme-site note |
| preserve-data | `*_Android_scatter_preserve_data.txt` | a Keep Data variant, not the package scatter |
| overlay | scatter lists a subset of partitions | requires the base firmware already present; Download Only |
| sparse images | first 4 bytes `3a ff 26 ed` (`0xed26ff3a`) | container must be desparsed before writing |
| MTK-signed images | `SSSS` … `EEEE` wrapper | strip 64 B header / 236 B footer before a raw write |

## Input maps and key/scan codes

Different firmware and device builds use different keylayouts and scan codes —
the same physical button can report a different `KEY_*` code on a stock Y1 build
than on an ATA/Rockbox build. Practical approach when working on a build:

- Android-based images (stock Y1/Y2, ATA Android 4.2/4.4): read
  `/system/usr/keylayout/*.kl`, `/system/usr/keychars/*.kcm`, plus
  `/system/build.prop` for the product/device identity.
- Rockbox and Linux builds: the keymap is compiled into the binary or read from
  a config file in the image; check the build's own sources for the target.
- Never assume a code carries across models. Probe, record, and state which
  build and which hardware revision the map came from.

The community's documented ATA/original scan-code tables for Y1 and Y2 are
planned for the developer docs and are **not published here yet**. Until they
exist, treat any table you find (or remember) as unverified, and verify against
the image in front of you.
