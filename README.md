# Virtual Real Cockpit wheel library

3D models of real sim racing wheels for [Virtual Real Cockpit](https://virtualrealcockpit.com), my VR overlay for
sim racing. In the app, go to Wheel › model select › *Get a wheel…* and pick yours. It then shows up in the car
where your real wheel is and turns with the game, and if it has a screen you can put a live dash on it.

All the models here are free to use and share under [CC BY 4.0](LICENSE.md), and the app shows who made each one.

If your wheel isn't here, have a look at [MORE-WHEELS.md](MORE-WHEELS.md). It has more models you can download,
from the wheel makers and from other people.

## What's in here

[index.json](index.json) is the list the app reads when you open *Get a wheel…*. Each wheel has its own folder in
`wheels/` with the model (`wheel.glb`), its details (`wheel.json`: name, maker, author and licence) and a preview
picture.

## More wheels to download

Some models can't live here because of their licence, like the files Simucube puts out for its own wheels.
[MORE-WHEELS.md](MORE-WHEELS.md) links to them and explains how to get them into the app. The same list is in
[more-wheels.json](more-wheels.json) if you'd like to use it in a tool.

## Asking for a wheel

Please open an issue with the wheel's name. If you own the wheel, let me know, because the quickest way to get it
in here is for an owner to scan it with their phone. The app's manual has a chapter on it (*Scan your wheel*), and
I'm happy to help with the cleanup afterwards.

## Adding a wheel

Thanks for helping out! [CONTRIBUTING.md](CONTRIBUTING.md) has the details.
In short, it needs to be your own model or a CC BY one with its author named, centred on the hub, facing +Z, at
its real size in metres, under 300k triangles, and a single `wheel.glb` with the textures inside.
