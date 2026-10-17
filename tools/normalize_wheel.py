# Puts a wheel .glb in the bundled-wheel convention (assets/models): metres, front facing +Z, centred on X / Y, the
# front-most point at z = 0.02, a given width across X. Rewrites POSITION and NORMAL data in place; the rest of the file
# (materials, textures) is kept byte for byte. Node transforms must be identity (true for the app's importer output
# and for Blender exports with transforms applied).
#   python tools/models/normalize_wheel.py in.glb out.glb --axes=-x,z,y --width 0.35
# --axes maps the new X, Y, Z to source axes (signed): "-x,z,y" = new X is -old X, new Y is old Z, new Z is old Y.
import argparse, json, struct

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--axes', default='x,y,z')
ap.add_argument('--width', type=float, default=0.32)
ap.add_argument('--front', type=float, default=0.02)
a = ap.parse_args()

d = bytearray(open(a.src, 'rb').read())
jl = struct.unpack('<I', d[12:16])[0]
j = json.loads(d[20:20 + jl])
bin_off = 20 + jl + 8
axes = []
for t in a.axes.split(','):
    sign = -1.0 if t.startswith('-') else 1.0
    axes.append((sign, 'xyz'.index(t[-1])))

def views(attr):
    out = []
    for m in j['meshes']:
        for p in m['primitives']:
            if attr in p['attributes']:
                acc = j['accessors'][p['attributes'][attr]]
                bv = j['bufferViews'][acc['bufferView']]
                out.append((acc, bin_off + bv.get('byteOffset', 0) + acc.get('byteOffset', 0), bv.get('byteStride', 12)))
    return out

def remap(v): return [s * v[i] for s, i in axes]

# pass 1: rotate, measure
pts = []
for acc, off, stride in views('POSITION'):
    for k in range(acc['count']):
        o = off + k * stride
        pts.append(remap(struct.unpack_from('<3f', d, o)))
mn = [min(p[i] for p in pts) for i in range(3)]
mx = [max(p[i] for p in pts) for i in range(3)]
k = a.width / (mx[0] - mn[0])
shift = [-(mn[0] + mx[0]) / 2 * k, -(mn[1] + mx[1]) / 2 * k, a.front - mx[2] * k]
# pass 2: write positions (+ min / max) and normals
for acc, off, stride in views('POSITION'):
    lo, hi = [1e30] * 3, [-1e30] * 3
    for i in range(acc['count']):
        o = off + i * stride
        p = [c * k + s for c, s in zip(remap(struct.unpack_from('<3f', d, o)), shift)]
        struct.pack_into('<3f', d, o, *p)
        lo = [min(x, y) for x, y in zip(lo, p)]; hi = [max(x, y) for x, y in zip(hi, p)]
    acc['min'], acc['max'] = lo, hi
for acc, off, stride in views('NORMAL'):
    for i in range(acc['count']):
        o = off + i * stride
        struct.pack_into('<3f', d, o, *remap(struct.unpack_from('<3f', d, o)))
# a mirroring axis map would flip the winding; refuse it rather than write inside-out triangles
det = 1
m = [[0] * 3 for _ in range(3)]
for r, (s, i) in enumerate(axes): m[r][i] = s
det = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
assert det > 0, 'the axis map mirrors the model (determinant < 0)'
js = json.dumps(j, separators=(',', ':')).encode()
js += b' ' * ((4 - len(js) % 4) % 4)
binchunk = d[20 + jl:]
out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + len(binchunk)) + struct.pack('<II', len(js), 0x4E4F534A) + js + binchunk
open(a.dst, 'wb').write(out)
print('scale %.5f, size %s m' % (k, [round((mx[i] - mn[i]) * k, 4) for i in range(3)]))
