#!/usr/bin/env python3
"""Checks every wheels/<id>/wheel.json + wheel.glb and writes index.json, the catalogue the app reads.

  python tools/build_index.py            write index.json
  python tools/build_index.py --check    fail when index.json is out of date or a wheel is invalid (CI)

Standard library only. The glb is read for its triangle count, its bounding box (is the hub at the origin, how
wide is it) and the screen fit the app saves in the file's root extras (extras.cockpitxr.screen).
"""
import hashlib, json, os, re, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHEELS = os.path.join(ROOT, 'wheels')
INDEX = os.path.join(ROOT, 'index.json')
REQUIRED = {'id': str, 'name': str, 'maker': str, 'diameterMm': int, 'author': str, 'license': str,
            'version': int, 'appMin': str, 'source': str}
OPTIONAL = {'authorUrl': str, 'derivedFrom': dict, 'screen': (dict, type(None)), 'notes': str}
GENERATED = ('triangles', 'sizeBytes', 'sha256', 'widthMm')
TRI_WARN, TRI_MAX, SIZE_MAX = 300_000, 500_000, 40 << 20

problems = []
def bad(wheel, msg): problems.append(f'{wheel}: {msg}')

def read_glb(path):
    """-> (json dict, triangles, (min xyz, max xyz) of all POSITION accessors)"""
    with open(path, 'rb') as f:
        d = f.read()
    if d[:4] != b'glTF' or struct.unpack('<I', d[4:8])[0] != 2:
        raise ValueError('not a glTF 2.0 binary (.glb)')
    jl, jt = struct.unpack('<II', d[12:20])
    if jt != 0x4E4F534A:
        raise ValueError('first chunk is not JSON')
    j = json.loads(d[20:20 + jl])
    acc = j.get('accessors', [])
    tris = 0
    lo, hi = [float('inf')] * 3, [float('-inf')] * 3
    for m in j.get('meshes', []):
        for p in m.get('primitives', []):
            mode = p.get('mode', 4)
            n = acc[p['indices']]['count'] if 'indices' in p else acc[p['attributes']['POSITION']]['count']
            tris += n // 3 if mode == 4 else max(0, n - 2) if mode in (5, 6) else 0
            a = acc[p['attributes']['POSITION']]
            if 'min' in a and 'max' in a:
                lo = [min(x, y) for x, y in zip(lo, a['min'])]
                hi = [max(x, y) for x, y in zip(hi, a['max'])]
    for node in j.get('nodes', []):
        if any(k in node for k in ('matrix', 'translation', 'rotation', 'scale')):
            raise ValueError('node transforms must be applied (export with transforms applied)')
    return j, tris, (lo, hi)

def screen_size(sc):
    """width and height in mm of a saved fit, from its corners (c0 c1 c2 c3 around the quad)."""
    c = sc.get('corners')
    if not (isinstance(c, list) and len(c) == 4 and all(isinstance(p, list) and len(p) == 3 for p in c)):
        return None
    dist = lambda a, b: sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
    e1, e2 = dist(c[0], c[1]) * 1000, dist(c[1], c[2]) * 1000
    return {'widthMm': round(max(e1, e2), 1), 'heightMm': round(min(e1, e2), 1)}

def git_date(rel):
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', rel], cwd=ROOT, capture_output=True, text=True)
        return out.stdout.strip() or None
    except OSError:
        return None

def build():
    entries = []
    for wid in sorted(os.listdir(WHEELS)):
        folder = os.path.join(WHEELS, wid)
        if not os.path.isdir(folder):
            continue
        jp, gp, pp = (os.path.join(folder, f) for f in ('wheel.json', 'wheel.glb', 'preview.png'))
        if not os.path.exists(jp):
            bad(wid, 'no wheel.json'); continue
        try:
            meta = json.load(open(jp, encoding='utf-8'))
        except ValueError as e:
            bad(wid, f'wheel.json: {e}'); continue
        if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', wid):
            bad(wid, 'folder name must be kebab-case (a-z, 0-9, -)')
        for k, t in REQUIRED.items():
            if k not in meta:
                bad(wid, f'wheel.json: missing "{k}"')
            elif not isinstance(meta[k], t) or (t is int and isinstance(meta[k], bool)):
                bad(wid, f'wheel.json: "{k}" must be {t.__name__}')
        for k, t in OPTIONAL.items():
            if k in meta and not isinstance(meta[k], t):
                bad(wid, f'wheel.json: "{k}" has the wrong type')
        for k in meta:
            if k not in REQUIRED and k not in OPTIONAL:
                bad(wid, f'wheel.json: unknown field "{k}" (generated fields belong in index.json, not here)')
        if meta.get('id') != wid:
            bad(wid, f'wheel.json: "id" must be "{wid}"')
        if meta.get('license') != 'CC-BY-4.0':
            bad(wid, 'wheel.json: "license" must be "CC-BY-4.0"')
        if not re.fullmatch(r'\d+\.\d+\.\d+', str(meta.get('appMin', ''))):
            bad(wid, 'wheel.json: "appMin" must look like 0.3.6')
        if isinstance(meta.get('diameterMm'), int) and not 200 <= meta['diameterMm'] <= 400:
            bad(wid, 'wheel.json: "diameterMm" should be the real rim diameter, 200 to 400')
        if 'derivedFrom' in meta:
            for k in ('title', 'author', 'url', 'license'):
                if not isinstance(meta['derivedFrom'].get(k), str):
                    bad(wid, f'wheel.json: derivedFrom.{k} missing')
        if not os.path.exists(gp):
            bad(wid, 'no wheel.glb'); continue
        if not os.path.exists(pp):
            bad(wid, 'no preview.png (a maintainer renders it before merging)')
        size = os.path.getsize(gp)
        if size > SIZE_MAX:
            bad(wid, f'wheel.glb is {size / 2**20:.1f} MB; keep it under {SIZE_MAX >> 20} MB')
        try:
            j, tris, (lo, hi) = read_glb(gp)
        except (ValueError, KeyError, IndexError) as e:
            bad(wid, f'wheel.glb: {e}'); continue
        if tris > TRI_MAX:
            bad(wid, f'wheel.glb has {tris:,} triangles; the limit is {TRI_MAX:,}')
        elif tris > TRI_WARN:
            print(f'note: {wid}: {tris:,} triangles, above the {TRI_WARN:,} we aim for')
        width = (hi[0] - lo[0]) * 1000 if hi[0] > lo[0] else 0
        if not 150 <= width <= 450:
            bad(wid, f'wheel.glb is {width:.0f} mm across X: the model must be in metres at real size (tools/normalize_wheel.py)')
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        if width and (abs(cx) > 0.1 * width / 1000 or abs(cy) > 0.15 * width / 1000):
            bad(wid, f'wheel.glb is off centre (centre at x {cx * 1000:.0f} mm, y {cy * 1000:.0f} mm): the hub must be at the origin')
        if hi[2] < 0 or lo[2] > 0.05 or hi[2] > 0.15:
            bad(wid, f'wheel.glb: the face must point towards +Z, with the front-most point just in front of the origin (z {lo[2]:.3f} to {hi[2]:.3f} m)')
        fit = j.get('extras', {}).get('cockpitxr', {}).get('screen') if isinstance(j.get('extras'), dict) else None
        sc = screen_size(fit) if isinstance(fit, dict) and fit.get('enabled', True) else None
        if meta.get('screen') and not sc:
            bad(wid, 'wheel.json says the wheel has a screen but wheel.glb carries no screen fit (fit it in the app, then export)')
        entry = dict(meta)
        entry.update({'screen': sc, 'triangles': tris, 'sizeBytes': size,
                      'sha256': hashlib.sha256(open(gp, 'rb').read()).hexdigest(), 'widthMm': round(width),
                      'glb': f'wheels/{wid}/wheel.glb', 'preview': f'wheels/{wid}/preview.png',
                      'updated': git_date(f'wheels/{wid}')})
        entries.append(entry)
    return {'schema': 1, 'wheels': entries}

index = build()
if problems:
    print('\n'.join(problems))
    sys.exit(1)
text = json.dumps(index, indent=2, ensure_ascii=False) + '\n'
if '--check' in sys.argv:
    cur = open(INDEX, encoding='utf-8').read() if os.path.exists(INDEX) else ''
    if cur != text:
        print('index.json is out of date: run python tools/build_index.py and commit it')
        sys.exit(1)
    print(f'ok: {len(index["wheels"])} wheels')
else:
    open(INDEX, 'w', encoding='utf-8', newline='\n').write(text)
    print(f'wrote index.json: {len(index["wheels"])} wheels')
