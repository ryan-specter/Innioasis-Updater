---
name: theme-authoring
description: Authoring themes and skins for every Innioasis target — stock Y1/Solar/JJ/Inniclassic config.json themes, Rockbox WPS/SBS themes, Reborn skin.json skins and Y2Player skin format v2. Use when creating, porting, debugging or documenting a player theme.
---

# Theme and skin authoring

"Theme" means five different formats on these players. Pick the target before
writing a line of JSON or a single `%` tag.

| Target | Format | Install location | Reference |
| --- | --- | --- | --- |
| Stock Y1, JJ Launcher, Inniclassic, Solar | `config.json` + PNG assets | `/storage/sdcard0/Y1_Themes/<Name>/` | [y1-stock-themes](reference/y1-stock-themes.md) |
| Rockbox Y1/Y2 | `.wps`, `.sbs`, `.cfg` inside a `.rockbox` tree | merge into `.rockbox/` | [rockbox-themes](reference/rockbox-themes.md) |
| Reborn (Y2Linux) | `skin.json` format 1 + images/fonts | `Skins/<Name>/` on internal storage or SD | [reborn-skins](reference/reborn-skins.md) |
| Y2Player (Android) | `skin.json` format 2 | `Y2Player/Skins/<Name>/` | [y2player-skins](reference/y2player-skins.md) |
| Rockbox theme *packages* | ZIP containing `.rockbox` | merge, never replace | `rockbox-y1/SKILL.md` |

## Decision tree

1. **Is the player running Android with the stock/JJ-style launcher?**
   Use the `config.json` format. Solar and Inniclassic read the same Y1 keys;
   Solar adds a `solarConfig` block for its extra shortcuts and preferences.
2. **Is it Rockbox?** Use `.wps` for Now Playing, `.sbs` for the status bar and
   `.cfg` to bind them. The screen is 480 × 360 on both Y1 360p and Y2.
3. **Is it Y2Linux/Reborn?** Use the Reborn `skin.json` format 1. It has its own
   screen names, palette tokens, conditions and a 1024 × 1024 texture budget.
4. **Is it the Y2Player Android app?** Use format 2. It is a different schema
   from Reborn's despite also being called `skin.json`; never copy one into the
   other.

## Universal rules

- **Work at 480 × 360.** Both panels are landscape 480 × 360. Y1 stock themes
  are authored for 320 × 240 in some older packs and scaled; do not mix.
- **Keep text readable.** Reborn refuses a skin whose `text`/`bg` contrast is
  below 3:1 and warns below 4.5:1. The Y1's mdpi-at-250-ppi panel makes thin
  fonts worse; use at least 16–18 px for body text.
- **Respect safe areas.** Leave room for the status bar and the wheel
  interaction model; there is no touchscreen to recover a hidden control.
- **Ship licences.** Fonts and artwork need a licence that allows
  redistribution. Reborn's requirements say to include them in the skin folder.
- **Test on the device or the project's renderer.** Reborn has
  `reborn-preview`; Y2Player has Theme Studio and a preview service; Rockbox has
  the simulator; Y1 config themes need a real player or the launcher's editor.
- **Do not rename an installed theme folder to "upgrade" it.** Settings store
  the folder name as the id. Add a new folder or keep the name stable.
- **Unknown fields are errors in Reborn and Y2Player v2.** A typo fails the
  whole skin; validate before copying to the player.

## Porting between formats

There is no automatic converter. A practical port:

1. Capture the source's palette (background, text, muted, accent, danger).
2. Recreate the layout in the destination's primitives. Y1 `config.json` is a
   fixed set of named slots; Reborn and Y2Player are free-form element lists.
3. Re-map assets to the destination's expected names or paths. Y1 expects
   `main_music.png`, `icon_setting_*.png`, and so on; Reborn uses `images/…`
   paths declared in `skin.json`; Y2Player uses its own asset paths.
4. Rebuild interaction-specific pieces separately. Y1 has a focus index and
   named actions; Reborn has `navigation` groups only where a screen opts in;
   Y2Player v2 has `focus` ids and `navigation`.
5. Re-test the wheel on hardware. A layout that looks right can put focus on an
   invisible or clipped control.

## Common failures

| Symptom | Likely cause |
| --- | --- |
| Theme not listed | Wrong folder (`Y1_Themes` vs `Y1_Themes/<Name>`), missing `config.json`, spaces in folder name |
| Colours ignore the theme | Asset missing, or the key is not one the launcher reads |
| Icon shows but is tiny/blurry | Wrong asset size; Y1 themes are pixel-sized, Reborn caps images at 480 × 360 |
| Reborn skin greyed out | Validation error: contrast, unknown field, missing image, texture budget |
| Y2Player skin rejected | `formatVersion` missing/2, unknown parameter, node budget, path outside the skin |
| Rockbox boots to logo after a theme | Delete `.rockbox/config.cfg` (documented Y1 fix) |
| Text missing glyphs | Font lacks the characters; supply a fallback or use `charset: "ascii"` in Reborn |

## Source map

| Target | Canonical files |
| --- | --- |
| Y1 stock keys | `thesolarproject-solar/app/src/main/assets/themes/Classic/config.json` |
| JJ player widgets | `ismileblue-y1_launcher/sample_player_theme.json`, `README.md` |
| Solar extensions | `thesolarproject-solar/docs/theming.md` |
| Rockbox themes | `rockbox-y1-rockbox/THEMES.md`, `manual/configure_rockbox/theme_settings.tex` |
| Reborn skins | `SchulzCode-Y2Reborn/docs/skins.md`, `skins/` examples |
| Y2Player skins | `schulzcode-Y2Player/docs/skins/FORMAT_V2.md`, `skin-v2.schema.json`, `theme-studio/` |
