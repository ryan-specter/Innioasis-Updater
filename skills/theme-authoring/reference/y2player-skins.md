# Y2Player skins (format 2)

Y2Player is an Android 4.4 player/launcher for the Y2. Its skin engine is
declarative, never executes scripts, and has two versions:

- **v1** community skins keep their original behaviour.
- **v2** adds shared styles, parameterised components, layout containers, more
  primitives, visual states, custom wheel focus and richer bindings. Set
  `formatVersion: 2`.

Canonical documents:
`schulzcode-Y2Player/docs/skins/FORMAT_V2.md`,
`docs/skins/skin-v2.schema.json`, `docs/skins/preview-fixtures.json` and
`docs/skins/example-v2/skin.json`. The visual editor is `theme-studio/`.

## Package and install

A theme is a folder with `skin.json` and its assets. Install by extracting the
theme ZIP into `Y2Player/Skins` on internal storage or the SD card. Theme Studio
exports an installable ZIP; it also imports `skin.json`, folders and ZIPs.

The manifest limit is **256 KiB**. JSON nesting is capped at 64 before parsing.
Version 2 compiles under a global 4096-node budget including unused templates;
each expanded screen is limited to 4096 nodes including repeated cells. Nested
repeaters are rejected, source child nesting is capped at 12, component graphs
must be acyclic, and at most 16 font faces load per skin (external font files
≤ 2 MiB). Existing image/asset path limits still apply.

## Styles and components

`styles` maps names to shared visual/text properties. A node's `style` selects
one; explicit properties override it. Supported style properties: `color`,
`background`, `opacity`, `borderColor`, `borderWidth`, `radius`, `size`, `bold`,
`font`, `lineSpacing`, `overflow`, `verticalAlign`. Styles do not inherit other
styles. Palette references use `colors`.

Components are arrays or objects with `parameters` and `nodes`:

```json
{
  "parameters": {"label": "Play", "width": 100},
  "nodes": [
    {"type": "text", "bounds": [0, 0, "{param.width}", 40],
     "text": "{param.label}"}
  ]
}
```

A component instance supplies `props` to override defaults. Parameters are
strings, numbers or booleans; overrides must have the same scalar type. A whole
`{param.name}` token preserves its type; tokens embedded in strings interpolate.
Defaults are required, unknown parameters are rejected, and each instance is
compiled independently. Use parameterised focus ids when repeating components.
An instance becomes a group; its children use local coordinates. Use
`anchor: "stretch"` or a layout container for resizing content.

## Drawing and text

| Property | Values |
| --- | --- |
| `font` | system family or relative font file; omitted inherits the skin font |
| `lineSpacing` | 0.5–3, default 1 |
| `verticalAlign` | `top`, `center` (default), `bottom` |
| `overflow` | `ellipsis` (default), `clip`, `marquee` |
| `marqueeSpeed` | 8–80 units/s, default 24 |
| `imageFit` | `stretch` (legacy), `fit`, `crop` |
| `imageX`, `imageY` | 0–1 alignment, default 0.5 |
| `opacity` | 0–1, inherited by group descendants |
| `radius` | rounded rect or image clip |
| `borderColor`, `borderWidth` | outline, width ≤ 16 |
| `gradient` | `{ "endColor": "accent", "direction": "vertical" }` (or horizontal) |

Version 2 text honours explicit newlines, wraps on font measurements/whole code
points/word boundaries, and marquee scrolls back and forth with one-second
pauses. Hidden screens do not animate. Fonts load during reload, not drawing.

New primitives:

- `circle`: ellipse inscribed in bounds.
- `line`: top-left to bottom-right (use a path for other directions).
- `path`: 2–128 normalised `[x,y]` points, each 0–1; `closed` joins endpoints.
  Open paths stroke; closed paths fill unless `stroke` is positive.

Gradients fill primitives/text, not images. Borders are rectangular/rounded
except circles. Image fit/crop clips to node bounds. Touch targets use the
clipped bounding rectangle.

## Layout

Groups and component instances accept `layout`:

- `absolute` (default): child bounds + anchor.
- `row` / `column`: children keep main-axis size; positive `weight` divides
  remaining space; cross-axis fills.
- `grid`: equal cells, `columns`; rows follow children.
- `stack`: every child fills the inner rectangle in draw order.

`padding` is a uniform inset, `gap` spacing. In absolute layout `anchor` is
`topLeft`, `topRight`, `bottomLeft`, `bottomRight`, `center` or `stretch`.
Corner anchors treat x/y as margins; center as offsets; stretch as symmetric
insets with width/height ignored. Anchors evaluate against the current parent.
Oversized content clips; only row repeaters scroll.

## Lists and keyboards

`rows.listMode`:

- `grid`: row-major grid with `columns` and `rowHeight`.
- `horizontal`: one strip of `rowWidth` × `rowHeight` cells.
- `carousel`: strip whose window follows selection, centered when possible.
- `radial`: up to 8 cells evenly spaced around an ellipse clockwise from top.

`scrolling` is `page` (default), `follow` or `center`; carousel always centers.
These are discrete selection windows, not free scrolling. Drawing and hit
testing use the same cell geometry; overlapping cells use last-drawn priority.

`keyboard.keyStyle` controls `gap`, `radius`, `color`, `background`,
`focusColor`, `focusBackground`, `borderColor`, `borderWidth`. Font/bold/size
come from the keyboard node. Key labels and wheel behaviour stay owned by
SearchKeyboard; Search keeps native keyboard/results navigation.

## States and motion

`states` maps state names to overrides of `color`, `background`, `opacity`,
`borderColor`, `borderWidth`, `radius`, `size`, `bold`. Applied in order:
`normal`, `paused`/`playing`, `active`, `focused`, `pressed`, `disabled`; later
wins. State overrides do not change actions or geometry. `disabled: true` blocks
the node and descendants; unavailable rows keep selection so the player can
explain availability. New visibility conditions: `pressed`, `disabled`,
`enabled`, `charging`.

`transitionMs` 0–500 (default 0) interpolates colours, opacity, radius and
border width. Text size/weight switch immediately. Motion is capped at 30
redraws/second, stops when hidden/detached, and keeps at most one transition per
visible node. No timeline or scripts.

## Controls, focus and seeking

Opt a screen into custom wheel focus:

```json
"navigation": {"now_playing": {"initial": "play", "wrap": true}}
```

Focusable nodes provide an action (or are row containers) and:

```json
"focus": {"id": "play", "group": "transport", "order": 1,
          "previous": "previous", "next": "next"}
```

IDs are unique per screen. Groups sort by name, items by `order`, ties keep
source order. `previous`/`next` override wheel order. Disabled, hidden or fully
clipped controls are excluded. `nextGroup`/`previousGroup` move between groups.
Confirm activates the focused action. A focused row container enters row
navigation on Confirm; Back leaves that mode first. Screens without navigation
entries keep existing wheel behaviour. Explicit Now Playing navigation uses the
wheel for focus, so add `volumeUp`/`volumeDown` controls there. Physical
transport/volume shortcuts remain.

Additional actions: `volumeUp`, `volumeDown`, `shuffle`, `repeat`; blocked in
Search/FM. `progress.seekable: true` seeks on tap release. Seek fractions are
clamped and ignored without a track/duration or in Search/FM; no intermediate
drag seeks.

## Bindings

| Binding | Value |
| --- | --- |
| `volume` | effective volume percentage, `--` if unavailable |
| `volume.mode` | volume mode enum name |
| `shuffle`, `repeat` | `ON`/`OFF`, repeat enum name |
| `track.codec` | metadata codec |
| `track.sampleRate`, `track.bitDepth`, `track.channels`, `track.bitrate` | metadata numbers, empty if unknown |
| `device.charging`, `device.storageAvailable` | `true`/`false` |
| `device.model` | reported model |
| `display.brightness` | brightness percentage |

These describe metadata, not the DAC's actual output. System volume is cached
for one second and refreshed when drawing.

## Build and preview

```bash
ANDROID_SDK_ROOT=/opt/android-sdk ./gradlew testDebugUnitTest lintDebug assembleRelease
node tools/skin-preview/check.mjs
```

`preview-fixtures.json` is shared by Kotlin tests and the browser preview module
(geometry, image fitting, seeking, text wrapping). Real browser/Android font
rasterisation is not guaranteed identical; the editor must use the same fonts
and compare device captures. The debug-only `SkinPreviewService` renders
synthetic state on Android and checks navigation/touch without playback.

Theme Studio:

```bash
cd theme-studio
npm install
npm run dev
npm run typecheck && npm test && npm run build && npm run test:e2e
```

The production build is a static PWA; projects autosave in the browser and
export an installable ZIP.

## Source map

- `schulzcode-Y2Player/docs/skins/FORMAT_V2.md` — canonical.
- `schulzcode-Y2Player/docs/skins/skin-v2.schema.json` — structural contract.
- `schulzcode-Y2Player/app/src/main/kotlin/.../SkinParser` — semantic checks.
- `schulzcode-Y2Player/theme-studio/` — editor and validator.
- `skills/theme-authoring/SKILL.md` — choosing the right format.
