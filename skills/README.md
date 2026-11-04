# Innioasis modding skills

A knowledge base for AI agents working on Innioasis Y1 and Y2 players. It is
written from the source of the projects listed in
[`slidia_manifest.xml`](../slidia_manifest.xml), not from marketing copy. Each
skill is a `SKILL.md` with YAML front matter, plus reference files where the
detail does not fit.

The audience is an agent that has to answer a question, write a patch, build a
ROM, author a theme, or explain why a player will not boot. Read the relevant
`SKILL.md` first; it names the reference files and the exact source paths that
back every claim.

## Start here

| Skill | Use it for |
| --- | --- |
| [y1-hardware](y1-hardware/SKILL.md) | Y1 SoC, wheel key events, display, audio/FM, storage, partitions, flashing |
| [y2-hardware](y2-hardware/SKILL.md) | Y2 MT6582 board, device tree, GPIO/I2C map, panels, PMIC, partitions, boot image |
| [firmware-packages](firmware-packages/SKILL.md) | `rom.zip` anatomy, scatter files, Updater contracts, publishing a release |
| [stock-android-roms](stock-android-roms/SKILL.md) | Stock Android 4.2 (Y1) and 4.4 (Y2), image editing, root, patching |
| [rockbox-y1](rockbox-y1/SKILL.md) | Rockbox Y1 port, dual boot, controls, build, themes, Wi-Fi plugins |
| [rockbox-y2](rockbox-y2/SKILL.md) | Rockbox Y2 hosted port, Class A updates, cold-boot routes, recovery |
| [theme-authoring](theme-authoring/SKILL.md) | Themes and skins for stock, JJ/Inniclassic, Solar, Reborn and Y2Player |
| [y2linux](y2linux/SKILL.md) | Y2Linux kernel, Buildroot rootfs, Rust platform services, OTA and recovery |
| [android-apps](android-apps/SKILL.md) | Writing and packaging Android apps for API 17 / API 19 players |
| [launchers](launchers/SKILL.md) | JJ Launcher, Inniclassic, Solar, Better-Y, Koensayr and Rondo internals |
| [release-notes-archive](release-notes-archive/SKILL.md) | Mining the site's release notes and imported docs for device facts |
| [site-publishing](site-publishing/SKILL.md) | The generators, manifest, sitemap, static docs and SEO contract of this repo |

## How to use a skill

1. Read `SKILL.md` completely. It states what is verified, what is inferred,
   and which device revision a fact applies to.
2. Open the reference file named for the task. Prefer the canonical source path
   over a paraphrase when you are about to change code.
3. Check the repository revision. The skills were written against the manifest
   projects as cloned on 2026-11-04; a project may have moved since. Every
   claim that matters should be re-checked with `git log` and the named file.
4. State the model and firmware level in any answer. A Y1 Type B, a Y2 on stock
   3.1.7 and a Y2 running Y2Linux do not share partition tables, boot chains or
   key maps.

## Safety rules that override everything else

- **Never write PRELOADER, NVRAM, PRO_INFO, PROTECT_F, PROTECT_S, SECCFG,
  MISC or BMTPOOL** unless the task is explicitly a verified bootloader
  recovery and the user has a full backup. These hold calibration, identity and
  boot-chain state that no public package can restore.
- **Back up before flashing.** A full partition readback plus a copy of the
  SD card is the minimum. `rom.zip` installs are destructive by design; a
  "keep data" option does not back data up.
- **Match the hardware.** Y1 Type A vs Type B and Y2 board/revision change the
  package. A preloader or scatter from another device is not a recovery tool.
- **Do not invent register values, GPIOs or partition offsets.** The Y2 device
  tree is the authority for the board; the stock scatter is the authority for
  the partition layout. If a value is not in a source file, say so.
- **A successful flash is not a booting device.** Verification means a clean
  boot, working storage, working input, and (where relevant) a readback that
  matches the package.

## Source repositories

The analysis used shallow clones of these projects. Paths in the skills are
relative to each repository root.

| Repository | What it contributes |
| --- | --- |
| `y1-community/y1-stock-rom` | Original Y1 software packages and restore path |
| `y1-community/y1-ata-rom` | Android 4.2 base ROM used by Y1 custom firmware |
| `y1-community/y2-ata-rom` | Android 4.4 base ROM for Y2 development |
| `y1-community/y1-linux-rom` | Early Linux-on-Y1 developer image |
| `rockbox-y1/rockbox` | Rockbox Y1 fork: hosted Android target, themes, Wi-Fi plugins |
| `spycemagic/y2-rockbox` | Rockbox Y2 hosted port and guarded updater contract |
| `schulzcode/y2linux` | Y2Linux kernel, Buildroot, platform services and release process |
| `SchulzCode/Y2Reborn` | Reborn player, skin engine and UI (runs on Y2Linux) |
| `schulzcode/Y2Player` | Y2 Android player/launcher and skin format v2 |
| `jarvissax/rondo` | Rondo Y1 firmware, app, server and dashboard |
| `thesolarproject/solar` | Solar launcher and Y1/Y2 theme engine |
| `ismileblue/y1_launcher` | JJ Launcher, the base of Inniclassic and Solar's Y1 look |
| `FabianZettl/inniclassic` | Inniclassic for Y1 |
| `JonaszPotoniec/inniclassic-y2` | Inniclassic for Y2 |
| `Leska1337/better-Y` | Stock-launcher patch and ROM repack |
| `ryan-specter/koensayr-auto` | Stock Y1 firmware patcher and AVRCP research |

## Conventions used in these skills

- **Verified** means a file in a source repository or a recorded device reading
  supports the statement. The path is given.
- **Observed** means a project documented a measurement on hardware. The
  project and document are named.
- **Inferred** means the conclusion follows from code or documentation but was
  not tested here. Say so when you rely on it.
- Pixel sizes are landscape unless stated: both players are 480 × 360.
- `$REPO` in a command means the root of the relevant clone.
