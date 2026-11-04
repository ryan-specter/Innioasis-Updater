# MTKClient headless flashing

The bundled `vendor/mtkclient` is the fork shipped inside Innioasis Updater
1.1.7 — the legacy DA write path, DRAM bring-up, USB read loop and error
strings are what make an install behave like the Chinese reference build. Do
**not** replace it with upstream `bkerler/mtkclient`: upstream differs exactly
where installs succeed or fail.

## Preferred: the app's own headless entry point

```bash
<app binary> --flash-cli <folder> <scatter> <platform> [package_path] [model] [da] [auth] \
             [--keep-data] [--rockbox]
```

- Frozen build: `/Applications/Updater CE.app/Contents/MacOS/UpdaterCE`,
  `InnioasisUpdater.exe`, `MediaTekInstaller.exe`, or `updater-ce` on Linux.
- Checkout: `python -m src.app --flash-cli ...` (falls back to `sys.executable`
  automatically in `--flash-cli`).
- `--flash-cli` always drives the MTKClient engine, so the same command works on
  all three platforms. Extra positions are optional and positional; a trailing
  `--keep-data` is never mistaken for a model.

IPC stream (one line per event, flushed):

```
[PROGRESS] 0..100
[STEP] EXTRACTING|PLEASE_WAIT|WAITING|DETECT|DOWNLOAD_DA|DOWNLOAD_BL|WRITE|DONE
[LOG] <tool output>
[ACTION] <what the user should do now>
[PARTITION_PROGRESS] <partition> <bytes>/<total>
[ETA] <seconds remaining, 0 until the rate is honest>
[RESULT] 1 FLASH_OK      # exit 0
[RESULT] 0 <code>        # exit 1
```

Read `[RESULT]`, not the exit code alone (the worker prints it through a direct
connection before exiting).

## What the engine does (and you must not re-do)

- Opens in **preloader mode (PID 0x2000)** for legacy MT6572/MT6582 targets
  (Y1, Y2, Timmkoo A5). Forcing a watchdog reset into BROM fails on these SoCs.
- Reads the live MBR/EBR chain first and bounds every write by the device's own
  partition size — a package built for a 2 GB userdata must not be pushed into
  a smaller player.
- Desparses Android sparse images (`0xed26ff3a`) and strips MediaTek signed
  wrappers (`SSSS` header 64 B, `EEEE` footer 236 B) before writing.
- Segments USB transfers (50 MiB per legacy command) and chunks each at 512 KiB
  (256 KiB for images ≥1.5 GB). Do not raise these to "speed things up".
- Writes the **preloader last**, through `sdmmc_write_image` (boot1) with an
  `EMMC_BOOT`/`BRLYT` header; `BL_EXIST_MAGIC` must be `0x42424242`.
- Sends the post-install reset (`bootmode=0`, normal boot) so the player leaves
  download mode on its own.
- Keep Data works by excluding the `usr`/`userdata` partition; the same idea as
  omitting it from an SP Flash Tool scatter.

## Fallback: a venv with the fork

Only when no installed app exists (e.g. CI, a bare clone):

```bash
python3 -m venv .venv-flash
. .venv-flash/bin/activate
pip install -r requirements.txt        # PySide6, pyusb, pycryptodome, ...
python -m src.app --flash-cli ./rom ./rom/MT6582_Android_scatter.txt MT6582
```

`src/paths.ensure_mtkclient_importable()` puts `vendor/mtkclient` on the path,
so the fork — not a pip-installed mtkclient — is what runs. Never `pip install
mtkclient` and expect parity.

## Host notes

- **macOS**: no SP Flash Tool; MTKClient is the only engine. `libusb-1.0.dylib`
  in `Contents/Frameworks/` must stay Universal 2. Fast USB mode is forced off
  on Darwin (Apple's driver overflows small transfers).
- **Windows**: x64 needs the MediaTek driver for bulk transfers; ARM64 Windows
  (native or Prism) is MTKClient-only by design.
- **Linux**: libusb soname is `libusb-1.0.so.0` on end-user distros; never
  hardcode `libusb-1.0.so`.
- A player that stops answering (`errno 2/5`) needs a physical power cycle;
  retrying immediately reproduces the same stall.
