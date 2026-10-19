# Adding a wheel

Thanks for helping to grow the library!

The easiest way is from the app. Load your model in Virtual Real Cockpit and set it up (pivot, alignment and the
screen fit if it has one), then pick *Share a wheel…* in the Wheel page's model list. Choose the model, fill in its
name and how you'd like to be credited, tick both boxes and press Send. I'll take care of the rest (centring, the
preview, the catalogue entry and the pull request), and you don't need a GitHub account.

On GitHub, please send one pull request per wheel. I'll render the preview and merge it.

## Before you send it

1. **You're allowed to share it.** You made the model yourself, or it's CC BY and you name its author in
   `derivedFrom`. Please don't send rips of paid or non-downloadable models. If a wheel's maker asks me to take a
   model down, I will.
2. **It's centred on the hub, faces +Z and is in metres.** The centre of the steering shaft is at 0,0,0, the face of
   the wheel points towards +Z (the driver), and it's the real size, so a 300 mm wheel is 0.30 m across X.
   `python tools/normalize_wheel.py in.glb wheel.glb --width 0.30` does the centring and scaling, and `--axes`
   turns it if it's facing the wrong way.
3. **It's light enough for VR.** Under 300k triangles, textures at 2048 px or smaller, and a single `.glb` with the
   textures embedded and the node transforms applied.
4. **It works in the app.** Load it with *Load your own model…* and check that the pivot sits at the hub, the gloves
   grip the rim and `Test steering` turns it about its centre. If the wheel has a screen, fit it in the app
   (Wheel › SCREEN › FIT) and export the model again so the fit is saved in the file.
5. **`wheel.json` is filled in.** Copy one from `wheels/`, then run `python tools/build_index.py` and make sure it
   doesn't report any problems. Please don't edit `index.json` by hand, the script writes it.

## The folder

```
wheels/<id>/
  wheel.glb      the model
  wheel.json     the fields below
  preview.png    I render this one (1200 x 800)
  photos/        optional, your reference photos
```

`<id>` is lower case with dashes, like `simagic-gt-neo`, `logitech-rs` or `moza-gs-v2p`.

## wheel.json

| Field | What goes in it |
|---|---|
| `id` | the folder name |
| `name`, `maker` | as on the box, like `GT Neo` and `Simagic` |
| `diameterMm` | the real rim diameter |
| `screen` | `null`, or `{}` if the wheel has a display (the size is read from the glb) |
| `author`, `authorUrl` | you |
| `source` | how it was made, like `photogrammetry (RealityScan), cleaned in Blender` or `modelled in Blender from the maker's drawings` |
| `license` | `CC-BY-4.0` |
| `derivedFrom` | only for conversions: `{ "title", "author", "url", "license" }` of the original |
| `version` | 1, then +1 every time the glb changes |
| `appMin` | the oldest app version the model works with, `0.3.6` unless you know otherwise |
| `notes` | optional, anything the next person should know |

## For me: wheels shared from the app

Each one arrives as an email to support@ with a private link that lasts 60 days. In this folder:

```
python tools/wheel_inbox.py "<the Model: link>"
```

It downloads the model, centres it without changing its size, carries the sender's screen fit into the model,
writes `wheel.json` with the sender as the author, renders `preview.png` with the app's `cxr_arms_preview`,
rebuilds `index.json` and opens a pull request on a `wheel/<id>` branch. Then check the preview and merge it, or
close the PR. `--axes` turns the model, `--width` rescales it, `--maker`, `--name` and `--id` fix the naming, and
`--no-pr` stops before git. Reply to the email if there's anything to ask the sender.

## Scanning your wheel

If you have the wheel and a phone, you can make a model in about an hour. The manual chapter *Scan your wheel*
goes through it: masking tape on the shiny parts, three rounds of photos, RealityScan or Polycam, then about ten
minutes of cleanup in Blender. If you get stuck, please open an issue and attach the export, and I'll finish it off.
