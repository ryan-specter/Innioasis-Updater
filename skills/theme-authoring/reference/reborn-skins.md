# Reborn skins (Y2Linux)

Reborn is the Rust player on Y2Linux. A skin changes only what is drawn:
colours, fonts, pictures and screen layouts. Buttons, menus, playback, settings
and built-in screens (Cover Flow, equalizer, text entry, updates) stay Reborn's.
The built-in **Reborn** look is always available and is not a skin.

Canonical document: `SchulzCode-Y2Reborn/docs/skins.md`. Shipped examples:
`SchulzCode-Y2Reborn/skins/` (16 skins installed to
`/usr/share/reborn/skins`).

## Install and select

```
Internal Storage/Skins/<Name>/skin.json
SD card/Skins/<Name>/skin.json
```

`Skins` is case-insensitive; a `Themes` folder (the pre-Beta-7.5 name) is also
read. The folder name is the skin id. Settings → Skin re-reads the list every
time it opens. A skin in `Skins` with the same folder name as a shipped skin is
hidden by the shipped one. A broken skin is greyed out with the reason; choosing
it keeps the current look. If a chosen skin is missing at startup, Reborn uses
its own look for that session and remembers the choice.

## Package

```
Neon/
  skin.json        at most 256 KB
  images/…         PNG, JPEG or WebP, each at most 480 × 360
  fonts/…          TrueType/OpenType, at most 8 MB each
  LICENSE…         font and picture licences
```

Paths in `skin.json` are relative to the folder, use `/`, and must stay inside
it (no `..`, no absolute paths, no outward links).

## `skin.json` shape

```json
{
  "format": 1,
  "name": "Neon",
  "author": "You",
  "version": "1.0",
  "description": "One line for the picker.",
  "palette": { "bg": "#101018", "text": "#F0F0FF", "accent": "cover" },
  "colors":  { "pink": "#FF3EA5" },
  "fonts":   { "menu": { "file": "fonts/MyFont-Bold.ttf", "size": 18 } },
  "images":  { "bar": "images/bar.png" },
  "parts":   { "titlebar": [ /* elements */ ] },
  "screens": { "list": [ /* elements */ ], "now_playing": [ /* elements */ ] }
}
```

Only `format` (always `1`) and `name` are required. **Unknown fields are
errors**, so a typo is reported instead of ignored.

## Palette

Fixed token names; screens you do not describe are drawn in these colours.

| Token | Use | Reborn default |
| --- | --- | --- |
| `bg` | background (always opaque) | `#06070A` |
| `text` | main text | `#F6F6F8` |
| `muted` | secondary text | `#A0A4AE` |
| `dim` | hints, disabled rows | `#848894` |
| `accent` | highlights; `"cover"` follows the playing cover | `cover` |
| `glass` | translucent raised areas | `#FFFFFF` |
| `scrim` | dimming behind sheets | `#000000` |
| `sheet` | sheet/dialog surfaces | `#0E1014` |
| `track` | empty rings/bars | `#1E2023` |
| `danger`, `success`, `warning` | states | `#FF7864`, `#3CC878`, `#FFBE3C` |

Contrast rules: `text` on `bg` must reach 3:1 or the skin is refused; below
4.5:1, and `muted`/`dim` below 3:1, it loads with a warning.

## Colours, fonts, pictures

- A colour can be `#RRGGBB`, `#RRGGBBAA`, a palette token, a name from
  `colors`, or `accent`. Add `/NN` for opacity percent: `"accent/40"`.
- `fonts` maps a name to a file and a pixel size 8–72. Each entry is rasterised
  once at load for Latin-1, Latin Extended-A and common punctuation. Large sizes
  may not fit the texture; add `"charset": "ascii"` to carry only ASCII (other
  letters fall back to Reborn's font). Text can also use built-in fonts: `R11`,
  `R13`, `R15`, `R17`, `L23`, `L44`, `S10`, `S13`, `S15`, `S17`, `S20`, `S25`,
  `S28`, `S36`.
- `images` maps a name to a file (PNG/JPEG/WebP, max 480 × 360, max 64 images).
  `slice: [left, top, right, bottom]` makes a nine-slice. Pictures and font
  glyphs share one **1024 × 1024** texture; a skin that does not fit is refused.

## Screens

`screens` maps a screen name to an ordered element list (later elements draw on
top). The viewport is 480 × 360, origin top-left. Reborn resolves the most
specific name first:

| Name | Shown for |
| --- | --- |
| `home` | main menu (else `list`) |
| `now_playing` | Now Playing |
| `list` | every list: library, settings, pickers, diagnostics |
| `page` | heading/facts pages (About, Storage, Song Info) |
| `artists`, `albums`, `genres`, `songs`, `folders`, `album`, `artist`, `queue` | one library screen (else `list`) |
| `cover_flow` | Albums Cover Flow (only this name; else Reborn's) |
| `music`, `song_info`, `settings`, `wifi`, `bluetooth`, `computer`, `sound`, `playback`, `crossfade`, `screen_off`, `theme`, `library`, `display`, `service`, `battery`, `sleep`, `storage`, `updates`, `about`, `maintenance`, `diagnostics`, `diagnostic`, `value` | one settings/system screen (else `page`/`list`); `theme` is the Skin picker |
| `time_zone`, `date_time` | those pickers (else `page`/`list`) |
| `search`, `playlists`, `playlist`, `radio`, `radio_stations`, `radio_categories` | those screens (else `list`) |
| `radio_info` | Station Info (else `page`) |
| `equalizer` | equalizer (only this name; else Reborn's) |
| `sheet`, `dialog`, `toast` | option sheets, questions, short messages |
| `volume` | fading volume indicator |
| `keyboard` | full-screen keyboard; draw a title bar and `{sheet_title}` over a `native` `screen` part |

Pairing, update installation, Power hold and start/shutdown screens are always
Reborn's, drawn in the skin's palette.

## Elements

Every element has `type` and may have `if`; `x`/`y` default to 0 and are
relative to a list row or group/part.

| Type | Fields |
| --- | --- |
| `rect` | `x y w h color`, `radius`, `stroke` (1–3, outline only) |
| `gradient` | `x y w h top bottom` (vertical) |
| `image` | `x y w h image`, `slice`, `tint` |
| `text` | `x y w h text`, `font`, `color`, `align`, `lines` 1–6, `line_height`, `tracking`, `case` |
| `icon` | `x y size icon`, `color` |
| `bar` | `x y w h value`, `track`/`fill` or `track_image`/`fill_image`, `radius`, `vertical`, `knob`, `knob_radius` |
| `art` | `x y size`, `source` `current` or `row`, `radius` |
| `list` | `x y w rows row_height row`, `focused`, `source` `rows`/`facts`/`sheet`, `scrollbar` |
| `group` | `elements`, `x y` offset |
| `part` | `name` from `parts`, `x y` offset |
| `native` | `part` `screen` or `status`, `x y`, `recolor` |
| `indicators` | `x y size gap color charge` — charging, computer, Bluetooth, Wi-Fi |

Text is cut with `…` to `w`; one line is vertically centred in `h`, several
lines are centred as a block or start at `y` when `h` is 0. A `list` draws
`rows` rows of `row_height` from `rows`/`facts`/`sheet`; `row` is drawn per row,
`focused` for the selection, and scrolling keeps the selection visible.

## Text values

`{name}` inside `text`:

`title artist album album_artist genre track_number station elapsed remaining
duration queue_index queue_length quality output playback sleep screen battery
volume clock position date status page_title page_body empty_title empty_body
empty_action message sheet_title sheet_body skin label detail number count`.

Examples: `{elapsed}` → `1:23`, `{remaining}` → `-2:05`, `{quality}` →
`LOSSLESS · 96 kHz`, `{position}` → `25 of 100`, `{clock}` → `21:41`,
`{date}` → `Sat 31 Oct`.

## Conditions

`if` takes names joined with `&` (and), `|` (or, lower precedence) and `!`
(not), e.g. `"playing & !shuffle | paused"`.

Global: `playing paused has_track has_art shuffle shuffle_albums repeat
repeat_one charging battery_low bluetooth bluetooth_connected wifi
wifi_connected back empty error danger eq gapless crossfade normalise sleep
has_status has_clock live favorite has_body has_title has_action has_facts
interactive`.

Inside rows: `focused disabled toggle on check checked chevron has_detail
row_art numbered current first last odd`.

## Icons

`back chevron check close play pause prev next play_large pause_large prev_large
next_large shuffle repeat repeat_one gapless eq normalise bluetooth wifi lock
bolt folder note speaker headphones sd usb warning info sun drive power download
refresh search vinyl person crossfade heart palette moon play_pause
play_pause_large repeat_mode`.

## Limits and validation

- `skin.json` 256 KB; 64 pictures ≤ 480 × 360; 8 fonts ≤ 8 MB; 4000 elements;
  one 1024 × 1024 texture.
- The loader names the first problem with its place, e.g.
  `screens.list[2] (text): unknown value "{lyrics}"`.

## Preview and install

From a Y2Reborn checkout (needs FFmpeg development files):

```bash
cargo run --bin reborn-preview -- out/preview --skin path/to/Neon
python3 tools/preview/render_previews.py out/preview
```

`out/preview/png/` holds every screen plus a contact sheet. On the player:

```bash
rebornctl theme          # list installed skins and their problems
rebornctl theme Neon     # switch
rebornctl theme reborn   # back to the built-in look
```

`charset` and `case: lower` (used by Zune) need Reborn after candidate 33.

## Source map

- `SchulzCode-Y2Reborn/docs/skins.md` — canonical.
- `SchulzCode-Y2Reborn/skins/` — 16 complete examples.
- `SchulzCode-Y2Reborn/app/reborn/src/runtime/themes.rs` — runtime.
- `SchulzCode-Y2Reborn/crates/reborn-ui/src/theme.rs` — element model.
