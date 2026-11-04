# SP Flash Tool console mode

SP Flash Tool v5.1904 ships inside Updater CE for **Windows (x86/x64)** and
**Linux (x86-64)**. macOS has no build; use MTKClient there.

## Command shape

```bash
flash_tool -c download -s <scatter> -d MTK_AllInOne_DA.bin -t without -r
```

| Flag | Meaning |
|---|---|
| `-c download` | Download Only: write the scatter's images, format nothing |
| `-s` | the package's scatter file |
| `-d` | Download Agent (`MTK_AllInOne_DA.bin` sits beside the tool) |
| `-t without` | USB-powered, battery optional |
| `-r` | redirect the debug log to the console stream |

An authentication file has **no CLI switch**. It travels in SP Flash Tool's
console configuration file, passed with `-i`:

```xml
<flashtool-config version="2.0">
  <general>
    <chip-name>MT6572</chip-name>
    <storage-type>EMMC</storage-type>
    <download-agent>MTK_AllInOne_DA.bin</download-agent>
    <scatter>MT6572_Android_scatter.txt</scatter>
    <authentication>custom.auth</authentication>
    <connection type="BromUSB" high-speed="true" without-battery="true" timeout-count="60000" com-port="" />
  </general>
  <commands><download-only/></commands>
</flashtool-config>
```

`chip-name` and `storage-type` are read from the scatter's `platform:` and
`storage:` lines — a wrong guess is worse than no flash, so refuse when they are
absent. The app builds this file (`src/sp_console_config.py`); if you must
hand-write one, never change `<commands>` to `<format-download/>`.

## Where the binary lives

| Host | Path |
|---|---|
| Windows install | `<install dir>\SP_Flash_Tool\flash_tool.exe` (Inno Setup: `Program Files\Updater CE`) |
| Windows portable pack | `SP_Flash_Tool\flash_tool.exe` beside the app binary |
| Linux staged | `~/.cache/innioasis-updater/linux_flash_tool/flash_tool` |
| Dev checkout | `tools/linux/SP_Flash_Tool_v5.1904_Linux/`, `tools/windows/SP_Flash_Tool_v5.1904_Win/` |
| Override | `$SP_FLASH_TOOL_DIR` |

Linux: run the **binary**, never `flash_tool.sh` (it overwrites
`LD_LIBRARY_PATH` and segfaults). Export `LD_LIBRARY_PATH=<stage>` and
`QT_PLUGIN_PATH=<stage>/plugins`, and fix `option.ini`'s `LogPath` to a real
absolute path first. The bundled Qt4 app dies on paths with spaces or non-ASCII;
on Windows convert scatter/DA with `GetShortPathNameW`.

## Reading the result

The tool writes its own internal log:

- Windows: `C:\ProgramData\SP_FT_Logs\<timestamp>\QT_FLASH_TOOL.log`
- Linux: `~/.cache/innioasis-updater/linux_flash_tool/SP_FT_Logs/...`

Success markers: `Flash complete! Disconnect USB and reboot the device.` or
`All command exec done!` (`incomplete` disqualifies a match). A disconnect or
`SP_EXIT_*` after a completion line is a post-flash artefact, not a failure.

Progress markers: `USB port detected`, `BROM connected`, `Download DA now`,
`N% of DA has been sent`, `N% of bootloader has been sent`,
`N% of image data has been sent`, `N% of flash has been formatted`, `Download OK`.

Error markers: `S_<NAME> (<code>)`, `Exception: err_code[<code>]`.

## Host requirements

**Windows** — MediaTek PreLoader USB VCOM driver must be the real one; Zadig /
WinUSB / libusb-win32 / UsbDk installed over the preloader interface break the
handshake. Run elevated. Keep every path ASCII and space-free (or 8.3).
ARM64 Windows gets MTKClient instead: the SP Flash Tool build is x86 only.

**Linux** — udev rules for `0e8d:0003` / `0e8d:2000` with `TAG+="uaccess"`,
`MODE="0666"` and `RUN+="/bin/chmod 0666 /dev/%k"`; membership of `dialout`
(Debian/Fedora/SUSE) or `uucp` (Arch/SteamOS). `cdc_acm` must be loadable so the
preloader exposes `/dev/ttyACM*`. `brltty` and `ModemManager` can steal the
port: stop or neutralize them for the run.

**Order of operations** — start the tool first, *then* plug the powered-off
player in. The preloader is only visible for 2-3 seconds.
