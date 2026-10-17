# Contributing a wheel

One pull request per wheel. A maintainer renders the preview and merges.

## Checklist

1. **You may share it.** You made the model, or it is CC BY and you name the author in `derivedFrom`. No rips of
   paid or non-downloadable models. We take a model down if the maker of the wheel asks.
2. **Hub at the origin, facing +Z, metres.** The steering shaft centre is at 0,0,0, the face of the wheel points
   towards +Z (the driver), and the model is its real size (a 300 mm wheel is 0.30 m across X).
   `python tools/normalize_wheel.py in.glb wheel.glb --width 0.30` does the centring and scaling; use
   `--axes` to turn it.
3. **Light enough for VR.** Under 300k triangles, textures 2048 px or smaller, one `.glb` with the textures
   embedded and all node transforms applied.
4. **Checked in the app.** Load it with *Load your own model…*: the pivot sits at the hub, the gloves grip the
   rim, `Test steering` turns it about its centre. If the wheel has a screen, fit it in the app (Wheel › SCREEN ›
   FIT) and export the model again so the fit is saved in the file.
5. **`wheel.json`** filled in (copy one from `wheels/`), then `python tools/build_index.py` passes with no
   problems. Don't edit `index.json` by hand; the script writes it.

## Folder

```
wheels/<id>/
  wheel.glb      the model
  wheel.json     the fields below
  preview.png    rendered by a maintainer (1200 x 800)
  photos/        optional: your reference photos
```

`<id>` is kebab-case: `simagic-gt-neo`, `logitech-rs`, `moza-gs-v2p`.

## wheel.json

| Field | What |
|---|---|
| `id` | the folder name |
| `name`, `maker` | as on the box: `GT Neo`, `Simagic` |
| `diameterMm` | the real rim diameter |
| `screen` | `null`, or `{}` for a wheel with a display (the size is read from the glb) |
| `author`, `authorUrl` | you |
| `source` | how it was made: `photogrammetry (RealityScan), cleaned in Blender`, `modelled in Blender from the maker's drawings` |
| `license` | `CC-BY-4.0` |
| `derivedFrom` | only for conversions: `{ "title", "author", "url", "license" }` of the original |
| `version` | 1, then +1 per change to the glb |
| `appMin` | the oldest app version the model works with; `0.3.6` unless you know otherwise |
| `notes` | optional, anything the next person should know |

## Scanning your wheel

If you have the wheel and a phone, you can make a model in about an hour. The manual chapter *Scan your wheel*
walks through it: masking tape on the shiny parts, three passes of photos, RealityScan or Polycam, ten minutes of
Blender cleanup. Open an issue if you get stuck and attach the export; we'll finish it.
