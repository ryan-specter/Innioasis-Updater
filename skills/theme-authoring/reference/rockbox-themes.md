# Rockbox themes (Y1 and Y2)

Rockbox themes are files inside the player's `.rockbox` directory. A theme
package is a ZIP whose `.rockbox` subtree is merged into the existing one; it is
not a single JSON file and it is not installed by replacing the whole folder.

## Files that make a theme

| File | Role |
| --- | --- |
| `*.wps` | While Playing Screen: the Now Playing layout |
| `*.sbs` | Status Bar Skin: the bar drawn above/below screens |
| `*.cfg` | Theme configuration: binds the WPS/SBS, font, colours, icons, selector |
| `*.fnt` | Bitmap fonts referenced by the config |
| `*.bmp` | Backdrops/icons referenced by the skin |
| `config.cfg` | Rockbox's live settings; **delete it if a theme makes Rockbox hang at the logo** |

A minimal `.cfg` names the files:

```
wps: /.rockbox/themes/MyTheme.wps
sbs: /.rockbox/themes/MyTheme.sbs
font: /.rockbox/fonts/16-Rockbox.fnt
```

Rockbox's own manual (`manual/configure_rockbox/theme_settings.tex`) documents
the full set of config options. The theme menu is implemented in
`apps/menus/theme_menu.c`; `apps/plugins/theme_remove.c` removes a theme and its
files.

## Geometry

- **360p**: 480 × 360, native for the Y1 360p build and the Y2.
- **240p**: 320 × 240, used by the older Y1 build. A 240p theme on a 360p build
  (or the reverse) will draw in the wrong place.

The Y1 release ZIPs are `rom_360p.zip` / `rom_240p.zip`; updates are
`update_360p.zip` / `update_240p.zip`. Y2 themes must be complete 480 × 360
themes.

## WPS/SBS syntax in practice

Rockbox skins are a sequence of tags and literal text. The common families:

| Tag family | Purpose |
| --- | --- |
| `%s` | Draw the status bar |
| `%?xx<...|...>` | Conditional: pick a branch based on a tag value |
| `%pb`, `%pv` | Progress bar / volume bar |
| `%pc`, `%pt`, `%ps` | Current time, total time, seconds |
| `%ia`, `%in` | Next track artist / title |
| `%?mp` | Play state (playing, paused, stopped) |
| `%?ps` | Shuffle state |
| `%?mm` | Repeat mode |
| `%ac`, `%al` | Album artist / album |
| `%fn`, `%fc` | File name / codec |
| `%xd`, `%xl` | Draw image / load image strip |

A tiny WPS that shows title, artist and a progress bar:

```
%s
%ac%?ia<%ia|%d2> - %?it<%it|%fn>
%pc / %pt
%pb(0,40,480,10,progress)
```

Syntax details that bite:

- Conditionals use `<true|false>` and can nest; every `<` needs a matching `>`.
- Percent signs introduce tags; a literal `%` is `%%`.
- Coordinates are pixels from the top-left; the viewport is the screen unless a
  viewport tag changes it.
- Image strips are indexed from 0; loading an image (`%xl`) must happen before
  drawing it (`%xd`).
- A syntax error can leave a blank screen or a black backdrop rather than an
  error message, especially on the hosted Android port.

## Installing a theme

1. Download the theme ZIP.
2. Extract it somewhere temporary.
3. Merge its `.rockbox` subtree into the player's `.rockbox` directory.
4. In Rockbox: `Settings > Theme Settings`, choose the `.cfg`.
5. If Rockbox hangs at the logo, delete `.rockbox/config.cfg` on the SD card and
   reboot (documented Y1 fix).

Never replace or delete the whole `.rockbox` tree: it contains settings,
databases, playlists and other themes. The Y2 Rockbox project repeats this
explicitly for its 480 × 360 themes.

## Fonts and assets

- The Y1 theme pack includes fonts; many themes assume a specific `.fnt` exists.
- Fonts must match the build's character set and screen; a missing font makes
  text invisible or substitutes a default.
- Backdrops and icons are BMP (Rockbox's native format) in most themes. PNG
  support depends on the build; stick to BMP for portable themes.

## Tooling

- `utils/themeeditor/` — Qt Rockbox Theme Editor for WPS/SBS layouts.
- `utils/rbutilqt/` — Rockbox Utility can install theme packages.
- `utils/skinupdater/updatetheme.pl` — updates a theme's syntax across Rockbox
  versions.
- The simulator (`docs/UISIMULATOR`) renders skins on a desktop, which is much
  faster than flashing a player for every layout change.

## Y1-specific theme notes

- The project publishes a 360p theme pack with fonts:
  `https://github.com/rockbox-y1/themes/releases/latest`.
- `THEMES.md` lists `ipodmod3blk-y1` and AdwaitaPod-Arcticons as 360p themes.
- Themes made for the iPod 6G at 320 × 240 are **240p**; use them only on the
  240p build.
- The site mirrors the install steps at `/rockbox-y1-themes.html`.

## Y2-specific theme notes

- Use only complete 480 × 360 themes.
- Merge the theme's `.rockbox` subtree; the rooted Android install keeps
  Rockbox's own settings and databases in that tree.
- Beta V2 added selectable themes; lyrics/theme diagnostics are a Beta V3
  priority, so a malformed theme may fail without a useful on-device message.

## Source map

- `rockbox-y1-rockbox/THEMES.md` — install steps, theme links, config reset.
- `rockbox-y1-rockbox/manual/configure_rockbox/theme_settings.tex` — settings.
- `rockbox-y1-rockbox/apps/menus/theme_menu.c` — theme menu.
- `rockbox-y1-rockbox/apps/plugins/theme_remove.c` — removal.
- `rockbox-y1-rockbox/utils/themeeditor/` — editor.
- `spycemagic-y2-rockbox/README.md` — Y2 theme merge rule.
