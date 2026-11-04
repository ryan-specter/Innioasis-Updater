# Updater CE screens, prompts and controls

Quoted behaviour, not marketing copy. Use these names when you talk a user
through the app so the words match what is on their screen.

## Navigation

`Select Software` · `Install Software` · `Themes & Fonts` · `Settings` ·
`Support` (`Donate`) · `Diagnostics` · `Notices`.

Advanced Settings is off by default and reveals: install method (MTKClient /
SP Flash Tool), SP Flash Tool GUI handoff, terminal install, run as admin.
Shortcuts `M` and `D` toggle it.

## Select Software

- Device dropdown lists only models the catalogue actually has releases for
  (driven by `slidia_manifest.xml`), plus a software dropdown for that model.
- Local firmware: browsing a folder or dropping a `.zip`/`.rar`/folder on the
  window selects that package instead of a catalogue release.
- Release details show name, version, model, description, release notes and
  the original ROM zip link (which resolves to the portable package for the
  reader's OS when a mirror has one).
- An APK-only entry without a post-install page is not offered at all.

## Install Software

- Heading reads `Get your <model> ready to install <software>` when a release
  name is known, and names the device otherwise.
- **Keep my data** appears only when the package can honour it (same firmware
  family, or the catalogue marks it a derivative). It leaves `usr`/`userdata`
  untouched; everything else is written as usual.
- The pre-install card asks the user to power the player off and connect it.
  The app must already be searching before the cable goes in.
- Progress stages: extracting → please wait → waiting for device → detect →
  download DA → download bootloader → write → done, with a measured ETA once
  the write rate is honest.
- On failure the card names the failure in plain language and keeps the raw
  code (for example `S_FT_DOWNLOAD_FAIL 4008`) for support. Retry is offered
  first; the other back end is offered after a real failure.

## Completion card

- Names the installed software and model, and for portable runs offers
  **Install This App** (Windows: opens the guide page; macOS: reveals the DMG;
  Linux: downloads the matching AppImage).
- Masters the donation appeal: **Buy us a coffee**, **Not now**, and a
  **Don't ask me again** preference (dimmed for portable runs, which store no
  settings, with a hover explanation).
- Rockbox runs also get the themes/fonts stage, which can ask the user to
  power the player on so the transfer can complete.

## Settings

- Language, theme, method selection (advanced), driver guide link, and the
  donation visibility preferences.
- The driver guide is `https://innioasis.app/guide.html`.

## Portable packages

- Windows/Linux: ROM files sit beside a copy of `SP_Flash_Tool` (or a
  `Firmware`/`SP_Flash_Tool` subfolder); macOS: a `Firmware/` folder beside the
  `.app`.
- `fw_package.ini` (optional) supplies name, version, model, type,
  description, `post_install`, `post_install2` and `derivative`.
- A `*rockbox*.txt` marker in the folder means themes/fontpacks install with
  the firmware.
- Only the scatter and the images it lists are needed; everything else a
  release carries is ignored.
