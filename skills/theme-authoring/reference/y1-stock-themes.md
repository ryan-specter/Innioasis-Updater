# Y1 stock-family themes: Original Software, Better-Y, Solar, Koensayr

The Original Software (the stock Y1 launcher) defines this format: a folder of
PNG assets plus a `config.json`. Three other targets read the same file, so one
theme can be authored once and shipped to all four.

| Target | What it does with the format |
| --- | --- |
| Original Software | Defines it. Stock launcher on 3.1.x firmware; screens it hardcodes ignore theme artwork. |
| Better-Y | Patched stock 3.1.2 ROM for the Y1 Type A. Themes load unchanged, and screens that were hardcoded now draw with the theme designs. |
| Solar | Reads every stock key, then overlays its own `solarConfig` block on top. |
| Koensayr | A firmware patcher, not a launcher. It edits stock images in place, so the stock launcher and its theme handling are untouched. |

JJ Launcher and Inniclassic are different software with their own (related but
separately documented) theme engine; see `skills/launchers/SKILL.md`. Do not
assume a JJ-only construct such as `sample_player_theme.json` exists here.

## Folder and install

```
/storage/sdcard0/Y1_Themes/<ThemeName>/
  config.json
  main_music.png
  main_now_playing.png
  icon_setting_theme.png
  ...
```

- The folder name is the theme id. Avoid spaces.
- The launcher lists folders in `Y1_Themes` at the SD card root. Themes live on
  the SD card, so installing a ROM or updating the app does not remove them.
- A theme ZIP normally contains the folder; extract it into `Y1_Themes`, not
  into a nested `Y1_Themes/<Theme>/<Theme>`.
- Solar adds a Theme Browser and downloader (`app/src/main/java/com/solar/launcher/theme/`)
  that imports a ZIP into the same folder. It rejects asset paths that point
  outside the theme folder (`..`), so keep every reference a plain filename.

## `config.json` structure

The full stock schema, with the keys the stock/Solar Classic theme actually
uses (`thesolarproject-solar/app/src/main/assets/themes/Classic/config.json`):

```json
{
  "themeCover": "main_now_playing.png",
  "desktopWallpaper": "desk_bg.png",
  "globalWallpaper": "global_bg.png",
  "itemConfig": {
    "itemTextColor": "#FFFFFFFF",
    "itemSelectedTextColor": "#FF00F5FF",
    "itemSelectedBackground": "item_selected_no_arrow.9.png",
    "itemBackground": "",
    "itemRightArrow": "right_arrow.png",
    "itemSelectedBackgroundIs9Patch": true
  },
  "dialogConfig": {
    "dialogOptionBackground": "cancle_bg.png",
    "dialogOptionTextColor": "#FFFFFFFF",
    "dialogOptionSelectedBackground": "conform_bg.png",
    "dialogOptionSelectedTextColor": "#FFFFFFFF",
    "dialogBackgroundColor": ""
  },
  "menuConfig": {
    "menuBackgroundColor": "",
    "menuItemBackground": "",
    "menuItemTextColor": "#FFFFFFFF",
    "menuItemSelectedBackground": "menu_item_selected.png",
    "menuItemSelectedTextColor": "#3B3D78"
  },
  "homePageConfig": {
    "nowPlaying": "main_now_playing.png",
    "music": "main_music.png",
    "video": "main_video.png",
    "audiobooks": "main_audiobook.png",
    "photos": "main_photos.png",
    "fm": "main_fm.png",
    "bluetooth": "icon_setting_bluetooth.png",
    "settings": "main_setting.png",
    "shuffleQuick": "main_shuffle.png",
    "calendar": "main_calendar.png",
    "calculator": "main_calc.png",
    "ebook": "main_book.png",
    "fileManager": "main_file_manager.png"
  },
  "fileConfig": {
    "folderIcon": "folder.png",
    "musicIcon": "music.png"
  },
  "settingConfig": {
    "shutdown": "icon_setting_shutdown.png",
    "timedShutdown_off": "icon_setting_time_off_0.png",
    "timedShutdown_10": "icon_setting_time_off_10.png",
    "shuffleOn": "icon_setting_shuffle_on.png",
    "shuffleOff": "icon_setting_shuffle_off.png",
    "repeatOff": "icon_setting_repeat_off.png",
    "repeatAll": "icon_setting_repeat_all.png",
    "repeatOne": "icon_setting_repeat_one.png",
    "equalizer_normal": "icon_setting_eq_1.png",
    "keyLockOn": "icon_key_lock_on.png",
    "keyLockOff": "icon_key_lock_off.png",
    "keyToneOn": "icon_setting_ringtone_on.png",
    "keyToneOff": "icon_setting_ringtone_off.png",
    "keyVibrationOn": "icon_setting_vibrate_on.png",
    "keyVibrationOff": "icon_setting_vibrate_off.png",
    "wallpaper": "icon_setting_wallpaper.png",
    "backlight_10": "icon_setting_sleep_10.png",
    "brightness": "icon_setting_brightness.png",
    "dateTime": "icon_setting_day.png",
    "language": "icon_setting_language.png",
    "launcher": "icon_setting_launcher.png",
    "factoryReset": "icon_setting_reset.png",
    "clearCache": "icon_setting_clear_cache.png",
    "theme": "icon_setting_theme.png"
  },
  "statusConfig": {
    "playing": "icon_statusbar_play.png",
    "pause": "icon_statusbar_stop.png",
    "blConnected": "icon_bluetooth_2.png",
    "headsetWithMic": "icon_headset_2.png",
    "statusBarColor": "",
    "battery": ["icon_statusbar_battery_0.png", "icon_statusbar_battery_1.png", "icon_statusbar_battery_2.png", "icon_statusbar_battery_3.png", "icon_statusbar_battery_4.png"],
    "batteryCharging": ["icon_statusbar_battery_0_c.png", "icon_statusbar_battery_1_c.png", "icon_statusbar_battery_2_c.png", "icon_statusbar_battery_3_c.png", "icon_statusbar_battery_4_c.png"]
  }
}
```

The Classic file is the authoritative list of keys the engine reads; the
excerpt above shortens the repeated timer/EQ/battery variants for brevity. Copy
the real file when starting a theme.

### Classic keys the excerpt shortens

These are in Classic and in the stock schema; a missing slot falls back to the
engine default, so set the ones your theme actually paints.

- `settingConfig`: `backlight_15`, `backlight_30`, `backlight_45`,
  `backlight_60`, `backlight_120`, `backlight_300`, `backlight_always`,
  `timedShutdown_20`, `timedShutdown_30`, `timedShutdown_60`,
  `timedShutdown_90`, `timedShutdown_120`, `equalizer_flat`, `equalizer_rock`,
  `equalizer_pop`, `equalizer_jazz`, `equalizer_classical`, `equalizer_dance`,
  `equalizer_folk`, `equalizer_heavymetal`, `equalizer_hiphop`, `shuffleOff`,
  `repeatAll`, `repeatOne`, `keyLockOff`, `keyToneOff`, `keyVibrationOff`,
  `fileExtensionOn`, `fileExtensionOff`, `displayBatteryOn`,
  `displayBatteryOff`.
- `statusConfig`: `stop`, `blConnecting`, `blDisconnected`,
  `headsetWithoutMic`, `fmPlaying`, `audiobookPlaying`.

### Keys outside the stock schema

These do not appear in Classic. Solar reads them; do not expect the stock or
Better-Y software to draw them.

| Key | Use |
| --- | --- |
| `dialogConfig.dialogTextColor` | Dialog body text |
| `settingConfig.settingMask` | Settings dual-pane frame |
| `desktopMask` | Mask over the desktop wallpaper |
| `playerConfig.progressColor`, `playerConfig.progressBackgroundColor` | Now Playing progress bar |
| `solarConfig.statusBarTextColor`, `homePageConfig.statusBarTextColor` | Status-bar text and icons |
| `fontFamily` | Font file inside the theme folder |

`fontFamily` is loaded by `theme/SystemFontBridge.java` and
`theme/ThemeManager.java`. `theme_info` is metadata, not drawing: `title`,
`author`, `authorUrl`, `description`, `externalDownloadUrl`. Solar's Theme
Browser and downloader read it for the gallery listing
(`theme/ThemeBrowser.java`, `theme/ThemeDownloader.java`); the stock software
ignores the block.

### Values

- Colours are `#AARRGGBB` (alpha first). `#FFFFFFFF` is opaque white,
  `#DD0F172A` is mostly opaque dark blue.
- Empty string means "use the engine default" for that slot.
- `.9.png` assets are nine-patch images; set
  `itemSelectedBackgroundIs9Patch` when the selected-row background is one.
- Asset paths are filenames inside the theme folder, not subdirectories, in the
  stock schema. Keep paths relative and free of `..`.

## Per-target notes

### Original Software

- Stock 3.1.x launcher. The named slots above cover the Home grid, lists,
  menus, dialogs, file manager and status bar; anything the launcher draws with
  its own hardcoded layout stays unthemed.
- Test a theme here first: it is the baseline the other three keep compatible.

### Better-Y

- A patched stock 3.1.2 ROM (Y1 Type A only), distributed through the updater.
  It keeps 100% compatibility with existing stock themes, so an Original
  Software theme needs no porting.
- Extended theme support: screens that stock draws with hardcoded colours — the
  queue among them — now use the theme's item/menu designs.
- The Now Playing icons, text and lyrics can be set to Light, Dark or Theme
  colour. That is a launcher setting, not a `config.json` key, so do not try to
  encode it in the theme.
- Better-Y's fixed main-menu and Settings margins suit most themes. Turn the fix
  off for themes whose backgrounds are drawn for the stock margins — the bundled
  Melody Munchkin, for example.
- The in-app data backup keeps the selected theme along with stock settings,
  playlists and audiobook progress.

### Solar extensions

Solar reads every stock key, then overlays `solarConfig` from the active theme.
Precedence for an icon/colour: **solarConfig → stock block in the same theme →
nothing**. Solar's bundled Aura defaults are never merged into third-party
themes for icons.

Open-ended key rules (`thesolarproject-solar/docs/theming.md`):

| Pattern | Used for | Example |
| --- | --- | --- |
| `app{Name}` | Home shortcut | `appMusic` |
| `app{Name}` | Solar-only shortcut | `appGet_Music` |
| `settings{Name}` | Settings right-pane icon | `settingsAbout` |

Sanitisation: runs of non-alphanumerics become `_`, leading/trailing `_`
trimmed. Settings labels use the English UI title, so keys stay stable across
languages. Renamed rows matter: `settingsWi_Fi` replaced
`settingsWi_Fi_Setup`, `settingsBluetooth` replaced
`settingsBluetooth_Setup`, and the new submenu parents are `settingsConnections`,
`settingsDevice`, `settingsPlayback`, `settingsLibrary`, `settingsMedia`,
`settingsPower`, `settingsUSB`.

Solar can also set preferences when a theme is applied:

| Prefix | Meaning | Value |
| --- | --- | --- |
| `enable…` | Turn on | ignored |
| `disable…` | Turn off | ignored |
| `set…` | Explicit value | boolean or English option label |

Examples: `enableMatch_Now_Playing_To_Theme`, `enableLCD_album_art`,
`setStatus_Bar_Text` (`Clock` or `Title`), `setArtwork_Perspective` (`Flat` or
`3D`). Parenthetical hints in a row label are ignored.

A stock theme with no `solarConfig` still applies; Solar just uses the stock
blocks as written and leaves its own shortcuts at the defaults.

### Koensayr

- A stock Y1 firmware patcher (MT6572 / Android 4.2.2), not a launcher
  replacement. `apply.bash` extracts `system.img` from `rom.zip`, loop-mounts
  it, applies byte/smali patches and flashes the result.
- Its patches change `mtkbt`/AVRCP libraries, the stock music APK and the app
  set; the Home launcher and its theme engine are left alone. It rewrites the
  system image only, so `/storage/sdcard0/Y1_Themes` on the SD card is not
  touched by a re-patch.
- Author exactly as for Original Software, then verify on the patched build:
  `--music-apk` replaces the stock player, so re-check the Now Playing screen
  against the theme after patching.

## Testing checklist

1. Folder name has no spaces; `config.json` parses (`python -m json.tool`).
2. Every referenced asset exists and is a valid PNG; nine-patch files have the
   `.9.png` suffix.
3. Menu, dialog, settings and status-bar previews all draw; no slot falls back
   to an unrelated icon.
4. Wheel focus order matches the visible order.
5. Text contrast is readable on the panel at arm's length.
6. Battery and charging variants both appear; headphones/Bluetooth states swap.
7. Theme survives a reboot and an app update; settings still point at the folder.
8. Load the same folder on each target you claim: Original Software, Better-Y,
   Solar (with and without `solarConfig`) and Koensayr.

## Source map

- `thesolarproject-solar/app/src/main/assets/themes/Classic/config.json` — full
  working stock schema.
- `thesolarproject-solar/docs/theming.md` — Solar key rules and preference map.
- `thesolarproject-solar/app/src/main/java/com/solar/launcher/theme/` —
  `ThemeManager`, `ThemeBrowser`, `ThemeDownloader`, `SystemFontBridge`.
- `Leska1337-better-Y/README.md` — extended theme support, colour and margin
  settings, data backup.
- `ryan-specter-koensayr-auto/apply.bash`, `docs/PATCHES.md` — patches that
  leave the launcher and its themes alone.
- `y1-community/y1-stock-rom` — Original Software packages and the restore path.
