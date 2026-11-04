# `slidia_manifest.xml` — the community firmware catalogue

Live copy: `https://innioasis.app/slidia_manifest.xml` (fallbacks: the
`innioasis.app` raw GitHub copy, then the maintainer fork). The app ships a
snapshot at `assets/online/slidia_manifest.xml` for first-run/offline use, and
caches the parsed result for 5 minutes.

It is **data**. A model appears in the app because the manifest lists a release
for it — nothing in the code is per-model beyond display names.

## Structure

```xml
<slidia>
  <package name="..." repo="owner/repo" device="Y1" url="https://github.com/owner/repo"
           type="img" handler="Custom Firmware" ... />
</slidia>
```

## Attributes the app reads

| Attribute | Meaning |
|---|---|
| `name` | Software name shown in the list and on install cards |
| `repo` | `owner/repo` whose GitHub Releases carry the firmware zip |
| `device` | Target model (`Y1`, `Y2`, `A5`, `Q5`, `G1`, ...) |
| `url` | Human-facing project URL (release notes / repo) |
| `type` | `img` (or `firmware`). Anything else is skipped — APK entries belong elsewhere |
| `handler` | Must contain `firmware` (conventionally `Custom Firmware`) |
| `portable_zips` | Comma-separated `*-mirror` repos that publish ready-to-run packages |
| `derivative` | Repo this firmware is built from; drives Keep Data compatibility |
| `info_repo` / `apk_repo` | Instructions / APK source for companion apps |
| `post_install`, `post_install2` | Page(s) opened after a successful install |
| `icon`, `icon_dark`, `image`, `image_dark` | Catalogue artwork URLs |
| `min_version` / `min_app_version` | Hide the entry from older app builds |
| `package_name` | Release asset name; defaults to `rom.zip` for Y1 and `rom_<device>.zip` otherwise |
| `do_not_keep_data` | `true` marks a firmware that must not inherit user data |

Skipped automatically: `repo="Please-Click/Updates-Available"` (the app's own
update placeholder), non-`img` types, handlers that are not firmware, and
entries whose `min_version` is newer than the running app.

Duplicate attributes (a real typo in the shipped file) are repaired by keeping
the first value, so one mistake cannot hide the whole catalogue.

## How the app resolves a download

1. Entry → `repo` → newest release that contains `package_name`.
2. If `portable_zips` names a mirror and that mirror's `index.json` has a build
   for this OS/arch, download the portable package instead of the plain zip.
   Platform keys: `windows`, `windows-arm64`, `linux`, `linux-arm64`, `macos`.
3. Otherwise take the original asset.

`*_mirror` packages exist because the app can then pre-select the firmware,
stage only the declared images, and offer the portable completion flow.

## Keep Data rules

`derivative` is the whole answer: an install may keep user data when the
software already on the device is the same firmware or a relative of the
incoming one (same `derivative` root). A firmware with no `derivative` is only
compatible with itself. There is an advanced override
(`allow_keep_data_any_firmware`) but it is not the default and should not be
presented as one.

## Changing the catalogue

- Add or edit one `<package>` per model — the same software usually needs a Y1
  and a Y2 entry.
- Keep the XML valid; `xml.etree` rejects duplicate attributes.
- A release must exist before the entry is useful: the app lists the entry, but
  the download 404s otherwise.
- The website reads the same file for its download buttons, so an entry is both
  "in the app" and "on the site".
