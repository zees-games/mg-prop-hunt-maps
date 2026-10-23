#!/usr/bin/env python3
"""Applies import_bsp.py's document passes to a COMMITTED map document, in place.

    tools/retune.py <id> [--widen-doors] [--widen-thick-doors] [--prune-pockets|--pocket-margin=0.07|--prune-levels]
                         [--terrain] [--clear=x0,z0,x1,z1] [--drop-beside=x,z,kind] [--field=name=number]
                         [--carve=x0,z0,x1,z1] [--in=FILE] [--out=FILE]

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
