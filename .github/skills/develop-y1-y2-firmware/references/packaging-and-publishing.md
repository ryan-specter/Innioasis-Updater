# Packaging and publishing a community firmware

## Folder layout the app detects

| Host | Layout |
|---|---|
| Windows / Linux portable | ROM files + `fw_package.ini` inside a copy of `SP_Flash_Tool` (or folder beside the binary) |
| macOS portable | `Firmware/` (or `SP_Flash_Tool/`) folder beside `Updater CE.app` |
| Browsed/dropped | any folder or `.zip`/`.rar` with exactly one scatter |

Only the scatter, the images it lists, `fw_package.ini` and the icon are
required. When a zip is extracted from a portable package, the app prunes
everything else (SP Flash Tool binaries, readmes, archives, logs) before
flashing, and stages what remains into an isolated cache directory so the app's
own files can never be overwritten.

## `fw_package.ini`

```ini
[fw_package]
enabled = true
software_name = Rockbox
version = 3.0.7
target_model = Y1
target_type = Type A
description = Community Rockbox build with 360p theme support.
post_install = https://example.org/first-start
post_install2 = https://example.org/themes
derivative = y1-community/y1-stock-rom
```

Keys are case-insensitive; `name`, `model`, `type`, `post_install_2` and
`compatible` are accepted aliases. `enabled = false` makes the app ignore the
package. Without an ini the app still installs — it infers the model from the
scatter and leaves the software name generic.

## Release naming and checksums

- Tag every release by version; the title and notes are shown to users.
- Firmware asset: `rom.zip` (Y1) / `rom_<device>.zip`, matching
  `package_name` in the manifest when you override it.
- Ship a `.sha256` beside anything the app downloads directly.
- Do not replace an existing release's assets; publish a new tag.

## Website standalone ZIPs (`portable_zips`)

Innioasis Updater CE always downloads `package_name` (`rom.zip` / `rom_<device>.zip`)
directly from the community firmware developer's own `repo` releases, and the
developers themselves are solely responsible for listing their releases in
`slidia_manifest.xml`. Updater CE never downloads from a portable mirror archive.

For visitors downloading standalone ZIPs from the website (`innioasis.app/firmware.html`),
an optional `portable_zips` repo (`y1-community/<name>-mirror`) can provide
per-platform web archives (`rom-windows.zip`, `rom-windows-arm64.zip`,
`rom-linux.zip`, `rom-linux-arm64.zip`, `rom-macos.zip`) indexed by `index.json`
(schema 1). When no web archive applies, the website downloads the developer's
original release asset directly.

## Publishing checklist

- [ ] Scatter is the release's own (not a preserve-data variant), platform and
      storage lines present.
- [ ] Every `is_download` image exists, names match `file_name` exactly.
- [ ] `fw_package.ini` present; model and variant correct.
- [ ] `post_install` page exists for anything that needs first-boot setup.
- [ ] `flash.py --package ... --check --json` reports no problems.
- [ ] Manifest entry added for each target model, with `derivative` where the
      firmware shares the stock data partition.
- [ ] Mirror (optional): `index.json` covers the new tag on every platform you
      built.
- [ ] Install verified on the real hardware for the model you claim — the
      project's contribution rules require hands-on SP Flash Tool and MTKClient
      verification across multiple firmwares before a pull release.

## Archiving ethics

The archive exists so a player owner can always restore what they own.

- Never delete or re-tag upstream assets; mirrors follow, they do not replace.
- Keep release notes with the archived builds — they are the only record of what
  changed, and the app displays them.
- Record provenance: base firmware, `derivative`, and any vendor blobs you did
  not author.
- If a maintainer withdraws a release, mark it in the manifest rather than
  silently republishing a modified copy.
