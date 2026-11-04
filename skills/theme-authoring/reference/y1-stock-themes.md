# Y1 stock, JJ, Inniclassic and Solar themes

All four read a folder of PNG assets plus a `config.json`. The format began with
the stock Y1 launcher, was adopted by JJ Launcher and Inniclassic, and is
extended by Solar.

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
- The launcher lists folders in `Y1_Themes` (SD card root). Inniclassic keeps
  themes on the SD card, so uninstalling the app does not remove them.
- A theme ZIP normally contains the folder; extract it into `Y1_Themes`, not
  into a nested `Y1_Themes/<Theme>/<Theme>`.
- JJ Launcher's editor can import a `config.json` and export a ZIP.

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
    "repeatOff": "icon_setting_repeat_off.png",
    "equalizer_normal": "icon_setting_eq_1.png",
    "keyLockOn": "icon_key_lock_on.png",
    "keyToneOn": "icon_setting_ringtone_on.png",
    "keyVibrationOn": "icon_setting_vibrate_on.png",
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
    "battery": ["icon_statusbar_battery_0.png", "1.png", "2.png", "3.png", "4.png"],
    "batteryCharging": ["icon_statusbar_battery_0_c.png", "1_c.png", "2_c.png", "3_c.png", "4_c.png"]
  }
}
```

The Classic file is the authoritative list of keys the engine reads; the
excerpt above omits repeated timer/EQ/battery variants for brevity. Copy the
real file when starting a theme.

### Values

- Colours are `#AARRGGBB` (alpha first). `#FFFFFFFF` is opaque white,
  `#DD0F172A` is mostly opaque dark blue.
- Empty string means "use the engine default" for that slot.
- `.9.png` assets are nine-patch images; set
  `itemSelectedBackgroundIs9Patch` when the selected-row background is one.
- Asset paths are filenames inside the theme folder, not subdirectories, in the
  stock schema.

## JJ Launcher player themes

JJ Launcher adds a separate player layout file, `sample_player_theme.json`:

```json
{
  "name": "Custom Player Pro Theme Example",
  "bg_image": "background.png",
  "textPrimary": "#FFFFFF",
  "textSecondary": "#B0B0B0",
  "btnNormal": "#15FFFFFF",
  "btnFocused": "#FF9800",
  "btnFocusedText": "#000000",
  "button_radius": 15,
  "player_ui": [
    {"id": "album_art", "type": "widget_focus_image", "x": 65, "y": 25,
     "width": 190, "height": 190, "gravity": "top|left"},
    {"id": "title", "type": "text", "x": 0, "y": 225, "width": 320, "height": 30,
     "text_size": 22, "text_align": "center", "bg_color": "#FFFFFF",
     "gravity": "top|center"},
    {"id": "progress_bar", "type": "progress", "x": 20, "y": 315,
     "width": 280, "height": 24, "radius": 12, "bg_color": "#FF9800",
     "progress_bg_color": "#55000000", "gravity": "top|left"}
  ]
}
```

Element types seen in the example and README: `text`, `button`, `icon`,
`progress`, `box`, `widget_focus_image`. Standard buttons also carry a
`focus_index` that defines wheel order, starting at 0. Actions are named
targets such as `Now Playing`, `Music Library`, `Root Folder`, `Bluetooth`,
`Wi-Fi Settings`, `Settings Menu`, `Web Server`, `Display Brightness`,
`Storage Info`, `Date & Time Settings`.

The sample's coordinates fit a narrower test layout than the Y1's 480 × 360
panel. Check a layout on the device before shipping; the launcher scales or
clips out-of-range widgets.

## Solar extensions

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

## Inniclassic

Inniclassic uses the JJ theme engine under package `com.themoon.y1` and ships an
iPod Classic light/dark theme. Custom themes still live in
`/storage/sdcard0/Y1_Themes`. Because Inniclassic and JJ share a package name,
only one can be installed at a time, and Inniclassic's debug-signed APKs require
uninstalling JJ first (`adb uninstall com.themoon.y1`).

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

## Source map

- `thesolarproject-solar/app/src/main/assets/themes/Classic/config.json` — full
  working schema.
- `thesolarproject-solar/docs/theming.md` — Solar key rules and preference map.
- `ismileblue-y1_launcher/README.md` — editor workflow and config template.
- `ismileblue-y1_launcher/sample_player_theme.json` — player widget layout.
- `FabianZettl-inniclassic/README.md` — Inniclassic install/signing caveats.
