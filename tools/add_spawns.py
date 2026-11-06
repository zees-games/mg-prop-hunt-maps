#!/usr/bin/env python3
"""Tops a committed map document up to 8 prop spawns and 4 hunter spawns, in place.

    tools/add_spawns.py <id> [--props=8] [--hunters=4]

The importer finds extra starts only on the ground at y = 0, which a multi-level map (the author's six starts
sit on five levels) does not have. New starts go on the levels the author's starts use, on a 2 m grid, on a
floor box, clear of props and walls (build_maps.Map._blocked), 6 m from every other start. Idempotent.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_maps  # noqa: E402


def top_up(doc, want_props=8, want_hunters=4, gap=6.0):
    m = build_maps.Map(doc["id"], doc["name"], "", doc["environment"])
    m.boxes, m.props = doc["boxes"], doc["props"]
    m.spawns = doc["spawns"]
    levels = sorted({round(s["at"][1] - 0.05, 2) for side in m.spawns.values() for s in side})
    xs = [b["at"][0] for b in m.boxes]
    zs = [b["at"][2] for b in m.boxes]
    have = [(s["at"][0], s["at"][2], s["at"][1]) for side in m.spawns.values() for s in side]
    added = 0
    for side, want in (("props", want_props), ("hunters", want_hunters)):
        n = len(m.spawns[side])
        cand = []
        for y in levels:
            x = min(xs)
            while x <= max(xs):
                z = min(zs)
                while z <= max(zs):
                    if m._floored(x, y, z) and m._blocked(x, y + 0.05, z) is None:
                        cand.append((x, y, z))
                    z += 2.0
                x += 2.0
        # Prefer floor with open space round it: the most free neighbours on the grid.
        free = set((round(x), round(y, 1), round(z)) for x, y, z in cand)
        cand.sort(key=lambda c: -sum((round(c[0] + dx), round(c[1], 1), round(c[2] + dz)) in free for dx in (-2, 0, 2) for dz in (-2, 0, 2)))
        for x, y, z in cand:
            if n >= want:
                break
            if all((x - a) ** 2 + (z - b) ** 2 >= gap * gap or abs(y + 0.05 - c) > 1.5 for a, b, c in have):
                m.spawn(side, x, z, yaw=(37 * (n + 1)) % 360 - 180, y=y + 0.05)
                have.append((x, z, y + 0.05))
                n += 1
                added += 1
    return added


if __name__ == "__main__":
    mid = sys.argv[1]
    kw = {}
    for a in sys.argv[2:]:
        k, _, v = a.lstrip("-").partition("=")
        kw["want_" + k] = int(v)
    path = os.path.join(os.path.dirname(HERE), "maps", mid + ".json")
    doc = json.load(open(path))
    n = top_up(doc, **kw)
    json.dump(doc, open(path, "w"), indent=1)
    print("added %d spawns to %s" % (n, mid))
