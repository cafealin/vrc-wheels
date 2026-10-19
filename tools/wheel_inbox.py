#!/usr/bin/env python3
"""Turns a wheel shared from the app (Wheel > Share this wheel...) into a pull request for this library.

  python tools/wheel_inbox.py "<the Model: link from the email>"        download, prepare, preview, open a PR
  python tools/wheel_inbox.py "<link>" --no-pr                           everything but the branch and the PR
  python tools/wheel_inbox.py "<link>" --axes=-x,z,y --maker Simagic     turn the model / fix the maker name

What it does:
  1. Downloads the model and its details through the private links from the email (they expire after 60 days).
  2. Puts the model in the library convention with normalize_wheel.py (metres, facing +Z, the hub at the origin,
     front at z = 0.02), keeping its real size. --axes turns it first; --width rescales it if the sender's was wrong.
  3. Carries the sender's screen fit over into the model's extras (extras.cockpitxr.screen), moved with the model,
     so the screen sits right when someone installs it.
  4. Writes wheel.json (the sender is the author, CC BY 4.0), renders preview.png with the app's cxr_arms_preview
     and rebuilds index.json.
  5. Commits it on a branch wheel/<id> and opens a pull request. Look at preview.png, then merge, or close it.

Standard library only (plus git and gh for the PR). The preview renderer is found next to this repo
(../cockpitxr/build-release/tools/arms_preview/...) or set CXR_ARMS_PREVIEW to its path.
"""
import argparse, datetime, json, math, os, re, shutil, struct, subprocess, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
APP = os.path.join(os.path.dirname(ROOT), 'cockpitxr')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'vrc-wheels wheel_inbox'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-') or 'wheel'


def glb_parts(d):
    if d[:4] != b'glTF' or struct.unpack('<I', d[4:8])[0] != 2:
        raise SystemExit('the download is not a glTF 2.0 binary (.glb)')
    jl = struct.unpack('<I', d[12:16])[0]
    return json.loads(d[20:20 + jl]), d[20 + jl:]


def write_glb(path, j, binchunk):
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + len(binchunk)) + struct.pack('<II', len(js), 0x4E4F534A) + js + binchunk
    with open(path, 'wb') as f:
        f.write(out)


def axes_map(spec):
    out = []
    for t in spec.split(','):
        out.append((-1.0 if t.startswith('-') else 1.0, 'xyz'.index(t[-1])))
    return out


def remap(axes, v):
    return [s * v[i] for s, i in axes]


def bbox(j, binchunk, axes):
    """min / max of every POSITION after the axis map (reads the vertices: accessor min / max can be missing)."""
    bin_off = 8   # the BIN chunk's own header
    lo, hi = [1e30] * 3, [-1e30] * 3
    for m in j.get('meshes', []):
        for p in m.get('primitives', []):
            if 'POSITION' not in p.get('attributes', {}):
                continue
            acc = j['accessors'][p['attributes']['POSITION']]
            bv = j['bufferViews'][acc['bufferView']]
            off = bin_off + bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
            stride = bv.get('byteStride', 12)
            for k in range(acc['count']):
                v = remap(axes, struct.unpack_from('<3f', binchunk, off + k * stride))
                lo = [min(a, b) for a, b in zip(lo, v)]
                hi = [max(a, b) for a, b in zip(hi, v)]
    if lo[0] > hi[0]:
        raise SystemExit('the model has no vertices')
    return lo, hi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('link', help='the "Model:" link from the email')
    ap.add_argument('--id', help='folder name (default: from the wheel name)')
    ap.add_argument('--maker', help="the wheel's maker (default: the first word of the name)")
    ap.add_argument('--name', help='the model name without the maker (default: the rest of the name)')
    ap.add_argument('--axes', default='x,y,z', help='turn the model first, as normalize_wheel.py --axes')
    ap.add_argument('--width', type=float, help='rescale to this width in metres (default: keep the size)')
    ap.add_argument('--diameter', type=int, help='rim diameter in mm for wheel.json (default: the model width)')
    ap.add_argument('--no-pr', action='store_true', help='leave the files in place, no branch or PR')
    a = ap.parse_args()

    link = a.link.strip().strip('"')
    if '/wheel-inbox/' not in link or 'sig=' not in link:
        raise SystemExit('that is not a wheel inbox link (copy the whole "Model:" line from the email)')
    print('downloading the details and the model...')
    sub = json.loads(fetch(link + '&part=json'))
    glb = fetch(link)
    j, binchunk = glb_parts(glb)

    name_full = sub['name'].strip()
    maker = a.maker or sub.get('maker') or name_full.split()[0]
    name = a.name or (name_full[len(maker):].strip() if name_full.lower().startswith(maker.lower() + ' ') else name_full)
    wid = a.id or slug(f'{maker} {name}' if not name.lower().startswith(maker.lower()) else name)
    folder = os.path.join(ROOT, 'wheels', wid)
    if os.path.exists(folder):
        raise SystemExit(f'wheels/{wid} exists already: pass --id to pick another folder name, or update it by hand')

    # the same transform normalize_wheel.py applies: axis map, scale k, then shift (hub to the origin, front at 0.02)
    axes = axes_map(a.axes)
    lo, hi = bbox(j, binchunk, axes)
    width = hi[0] - lo[0]
    target = a.width or width
    k = target / width
    shift = [-(lo[0] + hi[0]) / 2 * k, -(lo[1] + hi[1]) / 2 * k, 0.02 - hi[2] * k]
    move = lambda p: [c * k + s for c, s in zip(remap(axes, p), shift)]
    print(f'model {width * 1000:.0f} mm wide' + (f', rescaled to {target * 1000:.0f} mm' if a.width else ''))

    os.makedirs(folder)
    tmp = tempfile.mkdtemp(prefix='wheel-inbox-')
    src = os.path.join(tmp, 'shared.glb')
    with open(src, 'wb') as f:
        f.write(glb)
    out = os.path.join(folder, 'wheel.glb')
    subprocess.run([sys.executable, os.path.join(TOOLS, 'normalize_wheel.py'), src, out, f'--axes={a.axes}', '--width', repr(target)], check=True)

    # the sender's screen fit, moved with the model, into the file the app reads it from
    sc = sub.get('screen')
    if sc and len(sc.get('corners', [])) == 4:
        j2, bin2 = glb_parts(open(out, 'rb').read())
        corners = [[round(c, 6) for c in move(p)] for p in sc['corners']]
        j2.setdefault('extras', {}).setdefault('cockpitxr', {})['screen'] = {
            'enabled': True, 'fitted': True, 'corners': corners,
            'radiusMm': sc.get('radiusMm') or [0, 0, 0, 0], 'depthMm': sc.get('depthMm', 0)}
        write_glb(out, j2, bin2)
        print('screen fit carried over')
    pivot = move(sub.get('pivot') or [0, 0, 0])
    off_mm = math.hypot(pivot[0], pivot[1]) * 1000
    if off_mm > 5:
        print(f'NOTE: the sender put the pivot {off_mm:.0f} mm from the model centre; the library puts the hub at the centre. Check the preview.')

    day = sub.get('received', '')[:10] or datetime.date.today().isoformat()
    meta = {
        'id': wid, 'name': name, 'maker': maker,
        'diameterMm': a.diameter or int(round(target * 1000)),
        'screen': {} if sc else None,
        'author': sub['credit'], 'source': f"Shared from the app (Virtual Real Cockpit {sub.get('app', '')})".replace(' )', ')'),
        'license': 'CC-BY-4.0', 'version': 1, 'appMin': '0.3.7',
        'notes': f'Shared on {day}.' + (f' The sender\'s pivot was {off_mm:.0f} mm off centre.' if off_mm > 5 else ''),
    }
    with open(os.path.join(folder, 'wheel.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write('\n')

    # preview: the gloved hands holding the wheel, as the other previews (1200 x 800)
    exe = os.environ.get('CXR_ARMS_PREVIEW') or next((p for p in [
        os.path.join(APP, 'build-release', 'tools', 'arms_preview', 'RelWithDebInfo', 'cxr_arms_preview.exe'),
        os.path.join(APP, 'build', 'tools', 'arms_preview', 'RelWithDebInfo', 'cxr_arms_preview.exe')] if os.path.exists(p)), None)
    arms = os.path.join(APP, 'assets', 'models', 'driver_arms.glb')
    if exe and os.path.exists(arms):
        shot = os.path.join(tmp, 'preview.png')
        subprocess.run([exe, arms, shot, '--wheel', out, '--hero', '1200', '800'], check=True, cwd=os.path.dirname(exe))
        shutil.copyfile(os.path.join(tmp, 'preview-hero.png'), os.path.join(folder, 'preview.png'))
        print('preview rendered')
    else:
        print('NOTE: no cxr_arms_preview found (set CXR_ARMS_PREVIEW); add preview.png by hand')
    shutil.rmtree(tmp, ignore_errors=True)

    subprocess.run([sys.executable, os.path.join(TOOLS, 'build_index.py')], check=True, cwd=ROOT)
    print(f'\nwheels/{wid} is ready: {os.path.join(folder, "preview.png")}')
    if a.no_pr:
        return
    branch = f'wheel/{wid}'
    git = lambda *args: subprocess.run(['git', *args], check=True, cwd=ROOT)
    git('switch', '-c', branch)
    git('add', os.path.join('wheels', wid), 'index.json')
    git('commit', '-m', f'{maker} {name}, shared from the app by {sub["credit"]}')
    git('push', '-u', 'origin', branch)
    body = (f'Shared from the app on {day} by **{sub["credit"]}** (CC BY 4.0, both confirmations ticked).\n\n'
            f'- Model: {sub["file"]["bytes"] / 1048576:.1f} MB, {sub["file"].get("meshes", "?")} meshes'
            f'{", made with " + sub["file"]["generator"] if sub["file"].get("generator") else ""}\n'
            f'- Screen: {"fit carried over" if sc else "none"}\n- Size: {target * 1000:.0f} mm wide\n\n'
            'Check preview.png, then merge. Close the PR to reject it.')
    subprocess.run(['gh', 'pr', 'create', '--title', f'{maker} {name}', '--body', body], check=True, cwd=ROOT)
    git('switch', '-')


if __name__ == '__main__':
    main()
