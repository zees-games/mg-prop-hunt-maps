#!/usr/bin/env python3
"""Applies import_bsp.py's document passes to a COMMITTED map document, in place.

    tools/retune.py <id> [--widen-doors] [--widen-thick-doors] [--prune-pockets|--pocket-margin=0.07|--prune-levels]
                         [--terrain] [--clear=x0,z0,x1,z1] [--drop-beside=x,z,kind] [--field=name=number]
                         [--carve=x0,z0,x1,z1] [--prune-exposed=MAX[,SPACING]] [--report-exposure]
                         [--in=FILE] [--out=FILE]

tools/reimport.py does not reproduce the committed documents (the importer has moved on since they
were tuned, and a re-import throws the balance away), so a fix to a ported map is made on the
document itself, with the same functions the importer runs after reading the .bsp. Flags mean what
they mean in import_bsp.py.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import import_bsp as ib  # noqa: E402


def carve(boxes, x0, z0, x1, z1):
    """Opens a doorway: cuts the rectangle out of every solid box between knee and head height.

    A wall piece crossing the rectangle is cut along its long side (the pieces left on either side
    stay); a piece that lies inside it goes. A box the rectangle only clips is left alone.
    """
    n = 0
    for b in list(boxes):
        if not b.get("solid", True) or b["at"][1] + b["size"][1] / 2 < 0.3 or b["at"][1] - b["size"][1] / 2 > 2.0:
            continue
        cx, cy, cz = b["at"]
        sx, sy, sz = b["size"]
        bx0, bx1, bz0, bz1 = cx - sx / 2, cx + sx / 2, cz - sz / 2, cz + sz / 2
        if bx1 <= x0 or bx0 >= x1 or bz1 <= z0 or bz0 >= z1:
            continue
        if bx0 >= x0 and bx1 <= x1 and bz0 >= z0 and bz1 <= z1:
            boxes.remove(b)
            n += 1
        elif sx <= sz and bx0 >= x0 and bx1 <= x1:
            boxes.remove(b)
            n += 1
            for lo, hi in ((bz0, min(bz1, z0)), (max(bz0, z1), bz1)):
                if hi - lo > 0.02:
                    boxes.append(dict(b, at=[cx, cy, round((lo + hi) / 2, 3)], size=[sx, sy, round(hi - lo, 3)]))
        elif sz < sx and bz0 >= z0 and bz1 <= z1:
            boxes.remove(b)
            n += 1
            for lo, hi in ((bx0, min(bx1, x0)), (max(bx0, x1), bx1)):
                if hi - lo > 0.02:
                    boxes.append(dict(b, at=[round((lo + hi) / 2, 3), cy, cz], size=[round(hi - lo, 3), sy, sz]))
    return n


def _prop_boxes(doc, sizes):
    """The props as axis-aligned boxes [(lo, hi)], the yaw rounded to the nearest quarter turn."""
    out = []
    for q in doc["props"]:
        sx, sy, sz = sizes.get(q["id"], {}).get("size", [0.3, 0.3, 0.3])
        if round(q.get("yaw", 0.0) / 90.0) % 2:
            sx, sz = sz, sx
        x, y, z = q["at"]
        out.append(((x - sx / 2, y, z - sz / 2), (x + sx / 2, y + sy, z + sz / 2)))
    return out


def _standing(lo, hi, xs, zs, kill_y):
    """Standing places on a grid: (ix, iz, floor_y) where the top of a solid box has headroom over it."""
    import numpy as np
    out = []
    for ix, x in enumerate(xs):
        for iz, z in enumerate(zs):
            cover = np.nonzero((lo[:, 0] <= x) & (hi[:, 0] >= x) & (lo[:, 2] <= z) & (hi[:, 2] >= z))[0]
            for top in sorted(set(np.round(hi[cover, 1], 2))):
                if top >= kill_y and not ((lo[cover, 1] < top + 1.8) & (hi[cover, 1] > top + 0.1)).any():
                    out.append((ix, iz, float(top)))
    return out


def _reachable(lo, hi, places, xs, zs, starts):
    """The places a walker from `starts` (x, z, y) can get to: steps of at most 0.5 m up or down between neighbours with a clear waist-high line."""
    import numpy as np
    index = {}
    for n, (ix, iz, y) in enumerate(places):
        index.setdefault((ix, iz), []).append(n)
    xy = np.array([(xs[ix], y, zs[iz]) for ix, iz, y in places])
    todo = []
    for sx, sy, sz in starts:
        d = np.linalg.norm(xy - np.array([sx, sy, sz]), axis=1)
        todo.append(int(d.argmin()))
    seen = set(todo)
    while todo:
        n = todo.pop()
        ix, iz, y = places[n]
        cand = [m for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz for m in index.get((ix + dx, iz + dz), []) if m not in seen and abs(places[m][2] - y) <= 0.5]
        if not cand:
            continue
        a = xy[n] + [0, 0.7, 0]
        end = xy[cand] + [0, 0.7, 0]
        ok = ~_blocked(lo, hi, a[None], end)
        for m, good in zip(cand, ok[0]):
            if good:
                seen.add(m)
                todo.append(m)
    return sorted(seen)


def _blocked(lo, hi, eyes, target):
    """eyes (n,3) to targets (m,3): an (n, m) array, true where a box in lo/hi lies on the segment."""
    import numpy as np
    out = np.zeros((len(eyes), len(target)), dtype=bool)
    for j, t in enumerate(target):
        d = t - eyes
        with np.errstate(divide="ignore", invalid="ignore"):
            inv = 1.0 / d
            t1 = (lo[None] - eyes[:, None]) * inv[:, None]
            t2 = (hi[None] - eyes[:, None]) * inv[:, None]
        tmin = np.nan_to_num(np.minimum(t1, t2), nan=-np.inf).max(axis=2)
        tmax = np.nan_to_num(np.maximum(t1, t2), nan=np.inf).min(axis=2)
        out[:, j] = ((tmax >= np.maximum(tmin, 0.0)) & (tmin <= 1.0)).any(axis=1)
    return out


def exposure(doc, sizes, spacing=3.0, eye=1.6, reach=30.0):
    """Per prop, the share of standing points within `reach` m that see it, the way the bots suite's `seen` is measured.

    Standing points are the places a walker can reach from the spawns (a 1 m grid walked in steps of
    at most half a metre, so roofs and shelves nobody can climb to do not count), thinned to every
    `spacing` m. A point sees a prop when no solid box or other prop lies on the line from its eye
    to the prop's middle (half a metre up); the prop's own box and any box holding the target do
    not count. A rough copy of the suite's metric (which asks the physics space): good for ranking
    places, not for predicting the suite's number to the point.
    """
    import numpy as np
    solid = [b for b in doc["boxes"] if b.get("solid", True)]
    lo = np.array([[b["at"][i] - b["size"][i] / 2 for i in range(3)] for b in solid])
    hi = np.array([[b["at"][i] + b["size"][i] / 2 for i in range(3)] for b in solid])
    plo, phi = (np.array(a) for a in zip(*_prop_boxes(doc, sizes))) if doc["props"] else (np.zeros((0, 3)),) * 2
    xs = np.arange(lo[:, 0].min(), hi[:, 0].max(), 1.0)
    zs = np.arange(lo[:, 2].min(), hi[:, 2].max(), 1.0)
    places = _standing(lo, hi, xs, zs, doc.get("kill_y", -30.0))
    sp = doc.get("spawns", {})
    starts = [tuple(s["at"]) for side in ("props", "hunters") for s in (sp.get(side, []) if isinstance(sp, dict) else [])]
    if starts:
        places = [places[n] for n in _reachable(lo, hi, places, xs, zs, starts)]
    step = max(int(round(spacing)), 1)
    eyes = np.array([(xs[ix], y + eye, zs[iz]) for ix, iz, y in places if ix % step == 0 and iz % step == 0])
    blo = np.vstack([lo, plo])
    bhi = np.vstack([hi, phi])
    out = []
    for n, q in enumerate(doc["props"]):
        target = np.array([q["at"][0], q["at"][1] + 0.5, q["at"][2]])
        near = eyes[np.linalg.norm(eyes - target, axis=1) <= reach] if len(eyes) else eyes
        if not len(near):
            out.append(0.5)
            continue
        keep = ~((blo <= target).all(axis=1) & (bhi >= target).all(axis=1))
        keep[len(lo) + n] = False
        blocked = _blocked(blo[keep], bhi[keep], near, target[None])[:, 0]
        out.append(float((~blocked).sum()) / len(near))
    return out


def main(argv):
    ids = [a for a in argv[1:] if not a.startswith("--")]
    if len(ids) != 1:
        sys.exit(__doc__)
    path = os.path.join(os.path.dirname(HERE), "maps", ids[0] + ".json")
    out = path
    widen = thick = pockets = levels = terrain = False
    margin = 0.0
    clears, drops, fields = [], [], {}
    carves = []
    exposed = report = None
    for a in argv[1:]:
        if a.startswith("--out="):
            out = a[6:]
        elif a == "--widen-doors":
            widen = True
        elif a == "--widen-thick-doors":
            widen = thick = True
        elif a == "--prune-pockets":
            pockets = True
        elif a.startswith("--pocket-margin="):
            pockets, margin = True, float(a[16:])
        elif a == "--prune-levels":
            pockets = levels = True
        elif a == "--terrain":
            terrain = True
        elif a.startswith("--clear="):
            clears.append(tuple(float(t) for t in a[8:].split(",")))
        elif a.startswith("--drop-beside="):
            t = a[14:].split(",")
            drops.append((float(t[0]), float(t[1]), t[2] if len(t) > 2 else ""))
        elif a.startswith("--carve="):
            carves.append(tuple(float(t) for t in a[8:].split(",")))
        elif a.startswith("--prune-exposed="):
            exposed = tuple(float(t) for t in a[16:].split(","))
        elif a == "--report-exposure":
            report = True
        elif a.startswith("--in="):
            path = a[5:]
        elif a.startswith("--field="):
            k, _, v = a[8:].partition("=")
            fields[k] = float(v)
    doc = json.load(open(path))
    before = json.dumps(doc, sort_keys=True)
    if widen:
        n = ib.widen_doors(doc["boxes"])
        if thick:
            n += ib.widen_sliced_doors(doc["boxes"])
            print("dropped %d door trim posts" % ib.drop_trim_posts(doc["boxes"]))
        print("widened %d doorways" % n)
    if pockets:
        print("pruned %d props" % ib.prune_pockets(doc, levels=levels, margin=margin, floor_lo=-1.0 if terrain else -0.05))
    for x0, z0, x1, z1 in clears:
        gone = [q for q in doc["props"] if x0 <= q["at"][0] <= x1 and z0 <= q["at"][2] <= z1]
        for q in gone:
            doc["props"].remove(q)
        print("cleared %d props from (%.1f, %.1f) to (%.1f, %.1f)" % (len(gone), x0, z0, x1, z1))
    for dx, dz, kind in drops:
        near = sorted((q for q in doc["props"] if not kind or q["id"] == kind),
                      key=lambda q: (q["at"][0] - dx) ** 2 + (q["at"][2] - dz) ** 2)
        if near and (near[0]["at"][0] - dx) ** 2 + (near[0]["at"][2] - dz) ** 2 <= 2.6 ** 2:
            doc["props"].remove(near[0])
            print("dropped %s at %s" % (near[0]["id"], near[0]["at"]))
    for rect in carves:
        print("carved %d boxes out of %s" % (carve(doc["boxes"], *rect), rect))
    if exposed or report:
        sizes = json.load(open(os.path.join(HERE, "prop_sizes.json")))["props"]
        ex = exposure(doc, sizes, exposed[1] if exposed and len(exposed) > 1 else 3.0)
        print("exposure of %d props: mean %.2f, median %.2f" % (len(ex), sum(ex) / max(len(ex), 1), sorted(ex)[len(ex) // 2] if ex else 0))
        if exposed:
            gone = [q for q, e in zip(doc["props"], ex) if e > exposed[0]]
            doc["props"] = [q for q, e in zip(doc["props"], ex) if e <= exposed[0]]
            print("pruned %d props seen from more than %.0f%% of standing points" % (len(gone), 100 * exposed[0]))
    doc.update(fields)
    doc["boxes"] = [b for b in doc["boxes"] if min(b["size"]) > 0.005]
    print("audit: dropped %d props sunk in a wall or standing on nothing" % ib.audit_props(doc))
    if out == path and json.dumps(doc, sort_keys=True) == before:
        print("unchanged", out)
        return
    with open(out, "w") as f:
        f.write(json.dumps(doc, indent=1) + "\n")
    print("wrote", out, "props", len(doc["props"]), "boxes", len(doc["boxes"]))


if __name__ == "__main__":
    main(sys.argv)
