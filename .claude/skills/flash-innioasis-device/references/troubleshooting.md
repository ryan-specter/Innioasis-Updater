# Flash failures → what to actually do

Diagnose from the tool's own words, then act. Never announce success because
the progress bar reached 100% or the process exited 0.

## SP Flash Tool codes

| Code / name | Meaning | Action |
|---|---|---|
| `S_COM_PORT_OPEN_FAIL` (1013) | tool could not open the port | driver/VCOM missing on Windows, udev or `dialout` on Linux |
| `S_BROM_CMD_STARTCMD_FAIL` (2005) | BROM handshake started too early | unplug, wait, replug **after** the search begins |
| `S_TIMEOUT` (1042) | nothing answered in the window | power-cycle; confirm the player is off, not asleep |
| `S_CHIP_TYPE_NOT_MATCH` (3184) | firmware is for another SoC/model | **stop** — wrong package |
| `S_FT_DOWNLOAD_FAIL` (4008) | write failed | check cable/port, retry; then the other engine |
| `S_FT_ENABLE_DRAM_FAIL` (4032) | DA could not bring up DRAM | retry powered-off; try MTKClient |
| `S_DA_INIT_SYNC_ERROR` (1093) | DA upload desynced | replug; retry the whole run |
| `3145`-`3148` | bootloader header mismatch on boot1 | re-run; the engine handles the preloader write. Never patch images by hand |
| `SP_EXIT_<n>` (non-zero) | tool died, usually driver stack | install the MediaTek VCOM driver, run elevated |

## MTKClient signals

| Signal | Meaning | Action |
|---|---|---|
| `errno 2` / `errno 5` | player wedged mid-handshake | power-cycle, retry |
| `LIBUSB_ERROR_OVERFLOW` on macOS | fast-mode transfer too small | use the app's engine (it disables fast mode) |
| `Failed to read the partition table` / `falling back to per-partition reads` | recoverable | continue; the run is fine |
| `WRITE_IMAGE final ack timeout after data accepted` | benign on legacy Y1/Y2 | treat as success; it is ~109-111 s in |
| `Error on sending emmc read flash command, response: 0x0` | real failure | stop, retry whole flash |
| `BROM connected` then silence | DA not answering | power-cycle; do not switch engines yet |

## Sequence that resolves most failures

1. Unplug the player. Wait 5-10 seconds. Confirm it is powered off.
2. Keep the tool's window open and searching, then plug in.
3. Retry the same engine once.
4. Only after a *real* failure (an error code, not a timeout waiting for a
   device), try the other engine: MTKClient ⇄ SP Flash Tool.
5. If both fail on the same player, stop and collect diagnostics rather than
   looping: platform, scatter, package name, the tool's log, whether it is a
   Type A or Type B Y1, and the last 40 lines of output.

## Host checks worth running once

```bash
# Linux readiness
systemctl is-active ModemManager         # must not steal the port mid-flash
groups | tr ' ' '\n' | grep -E 'dialout|uucp'
ls -l /dev/ttyACM* 2>/dev/null
modprobe -n cdc_acm
```

Windows: Device Manager must show *MediaTek PreLoader USB VCOM Port* while the
player is plugged in powered-off; if it shows an unknown device or a WinUSB
device, the driver was replaced by Zadig — remove it and reinstall the MediaTek
driver before flashing again.

## After a partial/flash failure

A failed write is not necessarily a brick: the BROM still answers. Re-run the
same package with the player powered off. Do not format, do not try a different
model's firmware, and do not power the player on repeatedly.
