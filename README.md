# Virtual Real Cockpit wheel library

Ready-to-use 3D models of real steering wheels for [Virtual Real Cockpit](https://virtualrealcockpit.com), the
VR overlay for sim racing. Pick your wheel in the app (Wheel › model select › *Get a wheel…*) and it shows up
in the car where your real one is, turning with the game, with a live dash on its screen if it has one.

Every model here is free to use and share under [CC BY 4.0](LICENSE.md). The app shows the author's name on the
model.

**Looking for a wheel that isn't here?** [MORE-WHEELS.md](MORE-WHEELS.md) has more models you can download,
straight from the wheel makers and the community.

## Wheels

The catalogue is [index.json](index.json); the app reads it when you open *Get a wheel…*. Each wheel lives in
`wheels/<id>/` as `wheel.glb` (the model), `wheel.json` (name, maker, author, licence) and `preview.png`.

## More wheels you can download

Some wheels can't be hosted here, like the 3D files Simucube publishes for its own wheels, or models fans have made
under their own licences. [MORE-WHEELS.md](MORE-WHEELS.md) lists them with links, licences and how to get them into
the app. The same list is in [more-wheels.json](more-wheels.json) if you're building a tool.

## Want a wheel that isn't here?

Open an issue with the wheel's name. If you own it, say so: the fastest way to get a wheel in here is for an
owner to scan it with their phone. The app's manual has a chapter on it, *Scan your wheel*, and we'll help with
the cleanup.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: your own model or a CC BY one with the author named,
hub at the origin, facing +Z, real size in metres, under 300k triangles, one `wheel.glb` with textures inside.
