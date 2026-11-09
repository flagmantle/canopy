# Canopy Builder

Single-file browser app (`index.html`, ~4,700 lines, no build step) for designing an Australian 4WD ute tray, canopy and fit-out in 3D, with a 2D blueprint view. Planned to become a Steam game / utility; browser app first. Dark UI, white accent.

Live artifact (claude.ai, private): https://claude.ai/artifact/7QmPSRokeZ1SQ3gMpek38C (version 19 matches this file).

## Run

- Open `index.html` in a browser. It needs internet for **three.js r128** (cdnjs) and Google Fonts (Inter, JetBrains Mono).
- No bundler, no npm. Keep it one file unless the user asks to split it. The three region markers below make a future split easy.
- Only `three.min.js` is external. Everything else (models, textures, icons) is generated in code or inline SVG.

## File map (line numbers approximate, check with grep)

| Region | Lines | Contents |
|---|---|---|
| CSS + HTML shell | 1–288 | tokens, grid layout, panel/controls styles, canvases `#gl` (3D) and `#bp` (blueprint) |
| `/*LOGIC-START*/` … `/*LOGIC-END*/` | 289–1259 | catalogue (`BRANDS`, `ITEMS`, `RACKS`, `VEHICLES`), `state`, `clampState`, geometry (`geo`, `canopyProf`, `headProfile`, `layout`), weights, wiring, load check, parts list, share code |
| `/*SCENE-START*/` … | 1260–3374 | three.js scene, shed, `buildTray` (1593), `buildVehicle` (2093), `buildCanopy` (2433), gear models, awnings, `queueRebuild` (2936), `syncItems` (2970), camera, pointer input, 3D wiring |
| `/*UI-START*/` … | 3375–end | panels (`panelTray` 3482, `panelCanopy` 3550, `picker` 3477), blueprint (`bpDraw` 4039), `applyChange` (4389), `chooseTray`/`chooseCanopy` (4401/4408), events, init |

Logic is deliberately free of three.js so it can be tested headless.

## Conventions

- **Units:** mm in logic and state, metres in 3D (`MM = 0.001`).
- **Axes:** x across (right +), z along the ute (rear +), deck top is y = 0, ground y = -1.
- **Constants:** `HB_T = 40` (headboard), `WALL_T = 30`, `ROOF_T = 40`.
- **Brands are knock-offs** on purpose (BRA = ARB, Queens = Kings, Engal = Engel...). Real name sits in `BRANDS[x].real`. Swap names there when sponsors sign on. Dimensions are real; items flagged `est: true` are not yet checked against a spec sheet. Utes: HyLux, Rangar, Cruiser 79.
- Colours are CSS tokens at the top (`--accent: #ffffff`). Keep the dark look. Low tolerance for presentation errors: no overlapping UI, no broken states.

## State and data flow

`state` = `{ step, paint, tray, canopy, items, wires, payload, carOff, view, open, sel, ... }` (see `defaultState`).

```
UI event (data-set / data-act / rng / seg / picker)
  -> applyChange(path, val) -> setP -> clampState() -> queueRebuild(partsFor(path))
  -> buildTray / buildCanopy / buildVehicle / syncItems  -> bpDraw if blueprint is open
```

`clampState()` is the single place that enforces rules. Always route changes through it.

**Start state is an empty chassis:** `tray.design = 'none'`, `canopy.shape = 'none'`. The Tray step picks a design, the Canopy step picks a shape. Rules enforced in `clampState`:
- No tray => no canopy. "No tray" chip is disabled while a canopy exists.
- No canopy => `carOff = false`, items and wires cleared. "No canopy" chip is disabled while gear exists. Fit-out and Wiring need a canopy (`needCanopy()`).

### Tray
`tray = { veh, cab, len, wid, design, headShape, hbBend, hbTop, hbIn, head, lightStyle, lights, mat, finish ('smooth' default), colour, sides, boxes, spare }`
- `design`: `none | factory | dropside | rail | flat` (`TRAYS`). Factory = alloy tray with sides.
- Defaults: tall angled headboard (`head: 'full'`, `headShape: 'angled'`).
- Running gear: `tyre` (`TYRES`, knock-off tread brands, real name in `.real`, never shown in the UI), `tyreSize` (`TYRE_SIZES`, `std` = factory), `lift` (suspension, 0-150 mm), `bodyLift` (0/25/50 mm). `tyreSpec()` gives R/W, `rideH()` the deck height off the ground, `archClear()` the front arch gap. Suspension lift drops wheels and axles from the frame; body lift raises only the cab (`buildVehicle` returns a group of body `g` + chassis `gc`).
- Under the tray: `boxes` + `boxStyle` (`BOX_STYLES`), `guards` (`GUARDS`). `spare`: `none | door | door2 (two on the canopy rear) | carrier | under`.
- Vehicles: HyLux, Rangar, Cruiser 79, Colorodo RC (2008-12 Colorado, figures estimated, `VSPEC.colorado` + `faceColorado`).
- `headShape`: `angled` (default) `| square | custom`. Custom dims: `hbBend` (bottom to bend), `hbTop` (bend to top), `hbIn` (step-in). `headProfile(T)` returns `{h, bend, up, inset, rack}` or null.
- `lightStyle`: 8 styles in `LIGHT_STYLES` (factory, round3, round2, oval, slim, pod, strip, bar), `lights` is the colour set (red / smoked / clear). Old style names map through `LIGHT_LEGACY`.

### Canopy
`canopy = { shape, len, wid, hgt, bend, rise, inset, mat, finish, colour, left, right, style, rear, windows, rack, jack, floor, floorMat ('ply'|'alu'), plyT (6-21 mm), aluT (2-6 mm), floorFin, ... }`
- `shape`: `none | aframe (default when chosen) | square | custom`. A-frame = vertical sides up to a bend, then sides angle inward to a narrower roof.
- `canopyProf(C)` -> `{bend, rise, inset, wH, roofW}`. Custom: `bend` (bottom to bend) + `rise` (bend to top) + `inset` (roof steps in per side), `hgt = bend + rise`.
- `geo()` returns `outer`, `inner`, `roof` (inset roof rectangle), `prof`, and zero-size boxes when there is no canopy (`G.none`).
- Canopy 3D: `slab()` hugs the angled outer surface; `polyMesh` makes bevelled panels; `chordHinge()` swings side and barn doors about the bottom-to-top chord of an angled wall.
- Tray sides and tailgate are only drawn where no canopy covers them (bare tray, or behind the canopy).

## Persistence and share codes

- `localStorage` key `canopy-builder-v2` (v1 was dropped so the app can start empty).
- `exportCode()` / `importCode()` = base64 JSON. `applyData()` migrates old codes: missing `tray.design` becomes `{design:'flat', headShape:'square', lightStyle:'factory'}`, missing `canopy.shape` becomes `'square'`. Keep this migration working.

## Testing

`tests/smoke.py` (Python + Playwright, no network needed) loads `index.html` with a **stub THREE** and runs about 1,080 combinations of tray design, headboard shape, light style, canopy shape, doors, racks, extreme custom dims, gear, legacy code import and share-code round trip, and fails on any thrown error.

```
python3 tests/smoke.py     # expect: "errs": []
```

It cannot check how anything *looks*. To render for real offline, `npm pack three@0.128.0`, serve its `build/three.min.js` in place of the CDN script with a Playwright route, and launch Chromium with `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`. With internet available, test visually in a real browser. When editing: `node --check` the extracted script, run the smoke test, then eyeball the 3D view.

## Known gaps / next steps

- **3D look not yet verified by eye** for the new A-frame canopy, angled headboard, tray designs, bare chassis underside and the 8 tail-light styles. First job: open it, orbit around, fix proportions and z-fighting.
- Blueprint selection highlight is still yellow (everything else was changed to white).
- A-frame clash check in `layout()` ("Pokes through the angled side") is approximate: it compares item height against the wall's slope at the item's edge.
- Swing-out and barn doors on an A-frame hinge on the bottom-to-top chord line, so check they open without clipping the roof edge.
- Ideas from the user: more customisation everywhere ("My Dream Setup" style), more tray designs, more tail-light designs, more gear; sponsor brand swap; Steam release (likely wrap with Electron or Tauri later).
