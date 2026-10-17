#!/usr/bin/env python3
"""Converts a Source 1 community prop-hunt .bsp (VBSP 19/20) into a mg-prop-hunt map document.

    tools/import_bsp.py <map.bsp> <id> "<Name>" <author> <page-url> [--out maps/<id>.json]

What it does, and why each choice:

- The world's brushes become BOXES, because a map document has no meshes. Each brush's convex
  hull is found (bsp_read.Bsp.brush_hull, copied from game-g2gfast's importer) and its bounding
  box is written; a brush that is NOT a box (a roof slope, a stair) is cut into slabs along its
  longer horizontal axis, each slab as tall as the brush is at the slab's middle, so a ramp
  becomes a staircase of 0.3 m risers rather than a block twice its height.
- Axes: Source is Z-up, godot = (x, z, -y). Scale: 1 unit = 0.01905 m (the engine's own
  0.75 inch), which makes a 108-unit door 2.06 m, fits the game's 1.4 m x 2.3 m door convention.
- Textures are NOT carried. The author's textures are replaced with the game's own materials
  (Kenney's grid under pastels, ph_materials.gd); TEXTURE_MAP says which, by name.
- prop_physics become catalogue props by PROP_MAP (the author's HL2 models have no licence we can
  ship; the catalogue is Kenney, CC0). A model with no entry is dropped and counted.
- info_player_start entries are shared out between the two teams; `light` entities become omni lights.
- Tool brushes (skybox, clip, trigger, hint, nodraw-only) are dropped.

The output goes through build_maps.Map.build(), so spawns are settled and checked there.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bsp_read  # noqa: E402
import build_maps  # noqa: E402

S = 0.01905
SLAB = 28.0     # source units: ~0.53 m, a slope's riser

TOOLS = ("TOOLS/", "tools/")
TEXTURE_MAP = [
    ("PLASTER", "plaster", (0.95, 0.92, 0.84)),
    ("GRASS", "grass", (0.85, 0.95, 0.75)),
    ("ACOUSTICCEILING", "ceiling", None),
    ("TILEFLOOR", "tile", None),
    ("WOODFLOOR", "parquet", None),
    ("TILEROOF", "roof", None),
    ("COMBINEGLASS", "glass", None),
    ("CONCRETE", "concrete", None),
    ("STONE", "stone", None),
    ("BRICK", "brick", None),
    ("WOOD", "wood", None),
    ("METAL", "metal", None),
    ("DEV/", "flat", (0.8, 0.8, 0.82)),
]

# HL2 model -> catalogue id. Pieces with no counterpart in the catalogue are left out.
PROP_MAP = {
    "furniture_lamp01a": "furniture_lamp_round_table",
    "watermelon01": "food_watermelon",
    "chair_wood01": "furniture_chair",
    "oildrum001": "survival_barrel",
    "metal_paintcan001a": "survival_bucket",
    "garbage_newspaper001a": "furniture_books",
    "cardboard_box001b": "furniture_cardboard_box_closed",
    "furnituretable001a": "furniture_table",
    "glassbottle01a": "survival_bottle",
    "trashbin01a": "furniture_trashcan",
    "plasticcrate01a": "survival_box",
    "garbage_milkcarton002a": "food_carton_small",
    "popcan01a": "food_soda_can",
    "wood_crate001a": "survival_box_large",
    "wood_crate002a": "survival_box",
    "furniturecouch001a": "furniture_lounge_sofa",
    "tv_monitor01": "furniture_television_vintage",
    "furnituredresser001a": "furniture_cabinet_bed_drawer_table",
    "breenglobe": "nature_pot_small",
    "monitor01a": "furniture_computer_screen",
    "computer01_keyboard": "furniture_computer_keyboard",
    "breenclock": "furniture_radio",
    "huladoll": "furniture_bear",
}


def gd(p):
    return (p[0] * S, p[2] * S, -p[1] * S)


def kv(e, k, default=None):
    return e.get(k, default)


def vec(s):
    return [float(x) for x in s.split()]


def brush_material(bsp, index):
    first, count, _ = bsp.brushes[index]
    names = []
    for s in bsp.brushsides[first:first + count]:
        if s[3] or s[1] < 0:
            continue
        ti = bsp.texinfo[s[1]]
        td = int(ti[17])
        if 0 <= td < len(bsp.texdata):
            names.append(bsp.texnames[bsp.texdata[td][3]].upper())
    return names


def pick_material(names):
    real = [n for n in names if not n.startswith("TOOLS/")]
    if not real:
        return None
    # Majority of the sides, ignoring dev grids when anything else is there.
    pool = [n for n in real if not n.startswith("DEV/")] or real
    best = max(set(pool), key=pool.count)
    for key, mat, tint in TEXTURE_MAP:
        if key in best:
            return mat, tint
    return "flat", None


def planes_of(bsp, index):
    first, count, _ = bsp.brushes[index]
    return [bsp.planes[s[0]][:4] for s in bsp.brushsides[first:first + count] if not s[3]]


def z_range(planes, x, y):
    lo, hi = -1e9, 1e9
    for nx, ny, nz, d in planes:
        if abs(nz) < 1e-6:
            continue
        z = (d - nx * x - ny * y) / nz
        if nz > 0:
            hi = min(hi, z)
        else:
            lo = max(lo, z)
    return lo, hi


def brush_boxes(bsp, index):
    pts = bsp.brush_hull(index)
    if len(pts) < 4:
        return [], 0
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    z0, z1 = min(p[2] for p in pts), max(p[2] for p in pts)
    box_vol = (x1 - x0) * (y1 - y0) * (z1 - z0)
    # Hull volume from the corner points: a brush is a box when every corner is a box corner.
    corners = sum(1 for p in pts if (abs(p[0] - x0) < 0.5 or abs(p[0] - x1) < 0.5) and (abs(p[1] - y0) < 0.5 or abs(p[1] - y1) < 0.5) and (abs(p[2] - z0) < 0.5 or abs(p[2] - z1) < 0.5))
    if corners == len(pts):
        return [((x0, x1), (y0, y1), (z0, z1))], 0
    pl = planes_of(bsp, index)
    out = []
    if x1 - x0 >= y1 - y0:
        n = max(1, math.ceil((x1 - x0) / SLAB))
        for i in range(n):
            a, b = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
            lo, hi = z_range(pl, (a + b) / 2, (y0 + y1) / 2)
            lo, hi = max(lo, z0), min(hi, z1)
            if hi - lo > 0.5:
                out.append(((a, b), (y0, y1), (lo, hi)))
    else:
        n = max(1, math.ceil((y1 - y0) / SLAB))
        for i in range(n):
            a, b = y0 + (y1 - y0) * i / n, y0 + (y1 - y0) * (i + 1) / n
            lo, hi = z_range(pl, (x0 + x1) / 2, (a + b) / 2)
            lo, hi = max(lo, z0), min(hi, z1)
            if hi - lo > 0.5:
                out.append(((x0, x1), (a, b), (lo, hi)))
    return out, 1


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    out_path = None
    for a in argv[1:]:
        if a.startswith("--out="):
            out_path = a[6:]
    bsp_path, mid, name, author, url = args[:5]
    bsp = bsp_read.Bsp(bsp_path).load()
    m = build_maps.Map(
        mid, name, "Converted from %s by %s (%s)." % (os.path.basename(bsp_path), author, url),
        {"sky_top": [0.32, 0.52, 0.82], "sky_horizon": [0.72, 0.82, 0.92], "ground": [0.35, 0.33, 0.30],
         "sun_pitch": -55, "sun_yaw": 30, "sun_energy": 1.0, "ambient": [0.62, 0.66, 0.72], "ambient_energy": 0.5},
        kill_y=-20.0)
    m.doc["author"] = author
    m.doc["source"] = url

    sliced = skipped = 0
    for bi in sorted(bsp.model_brushes(0)):
        names = brush_material(bsp, bi)
        mt = pick_material(names)
        invisible = False
        if mt is None:
            # The author's sky box is the map's wall: solid to a player, drawn as nothing.
            if any("TOOLSSKYBOX" in n for n in names):
                mt, invisible = ("flat", None), True
            else:
                skipped += 1
                continue
        boxes, was_sliced = brush_boxes(bsp, bi)
        sliced += was_sliced
        for (x0, x1), (y0, y1), (z0, z1) in boxes:
            # Source y is godot -z: the box's range flips.
            bx = m.span(x0 * S, x1 * S, z0 * S, z1 * S, -y1 * S, -y0 * S, mt[0], mt[1])
            if invisible and bx is not None:
                bx["visible"] = False
    print("brushes %d  tool-only %d  sliced %d  boxes %d" % (len(bsp.model_brushes(0)), skipped, sliced, len(m.boxes)))

    # Props: sit on the highest solid box under the footprint when one is within reach of the
    # source height, else at the source height (a lamp on a table the author placed as a prop).
    def support(x, z, pid, yaw, ymax):
        """The highest thing under the footprint no higher than ymax: a box's top, or a prop
        already set down (`rest_on`, its collision as the game measured it). The catalogue's
        table is not the author's table, so a lamp set at the author's table-top height would
        hang in the air; it is put on whatever is really there instead."""
        best = 0.0 if ymax >= 0.0 else None
        fw, fd = build_maps.footprint(pid, yaw)
        for b in m.boxes:
            if not b.get("solid", True):
                continue
            hx, hz = b["size"][0] / 2, b["size"][2] / 2
            if abs(x - b["at"][0]) <= hx + 0.001 and abs(z - b["at"][2]) <= hz + 0.001:
                t = b["at"][1] + b["size"][1] / 2
                if t <= ymax and (best is None or t > best):
                    best = t
        for q in m.props:
            qw, qd = build_maps.footprint(q["id"], q.get("yaw", 0.0))
            if abs(x - q["at"][0]) <= qw / 2 and abs(z - q["at"][2]) <= qd / 2:
                t = q["at"][1] + build_maps.rest_on(q, x - q["at"][0], z - q["at"][2], pid, yaw)
                if t <= ymax and (best is None or t > best):
                    best = t
        return best

    dropped = {}
    placed = []
    for e in bsp.entities:
        cls = e.get("classname")
        if cls == "prop_physics":
            key = os.path.splitext(os.path.basename(e.get("model", "")))[0]
            pid = PROP_MAP.get(key)
            if pid is None:
                dropped[key] = dropped.get(key, 0) + 1
                continue
            placed.append((vec(e["origin"])[2], e, pid))
        elif cls == "light":
            o = vec(e["origin"])
            gx, gy, gz = gd(o)
            c = vec(e.get("_light", "255 255 255 200"))
            m.light(gx, gy, gz, rng=9.0, energy=min(1.2, c[3] / 200.0), colour=[c[0] / 255, c[1] / 255, c[2] / 255])
    def floor_corners_ok(x, z, pid, yaw, y):
        """A prop standing on the ground has solid floor under every corner of its footprint:
        the author's cellar stair is a hole in the floor, and a crate on its rim hung half over it."""
        fw, fd = build_maps.footprint(pid, yaw)
        for dx in (-fw / 2 + 0.03, fw / 2 - 0.03):
            for dz in (-fd / 2 + 0.03, fd / 2 - 0.03):
                ok = False
                for b in m.boxes:
                    if not b.get("solid", True):
                        continue
                    if abs(x + dx - b["at"][0]) <= b["size"][0] / 2 and abs(z + dz - b["at"][2]) <= b["size"][2] / 2:
                        if abs(b["at"][1] + b["size"][1] / 2 - y) < 0.06:
                            ok = True
                            break
                if not ok:
                    return False
        return True

    # Lowest first, so a table is down before the lamp the author put on it.
    for _, e, pid in sorted(placed, key=lambda t: t[0]):
        ang = vec(e.get("angles", "0 0 0"))
        gx, gy, gz = gd(vec(e["origin"]))
        yaw = (ang[1] + 90.0) % 360.0
        y = support(gx, gz, pid, yaw, gy + 0.35)
        if y is None:
            y = max(gy, 0.0)
        if y < 0.06 and not floor_corners_ok(gx, gz, pid, yaw, y) and not any(
                abs(q["at"][0] - gx) < 0.01 and abs(q["at"][2] - gz) < 0.01 for q in m.props):
            dropped["(over a hole)"] = dropped.get("(over a hole)", 0) + 1
            continue
        m.prop(pid, gx, gz, yaw=yaw, y=y)
    starts = [e for e in bsp.entities if e.get("classname") == "info_player_start"]
    for i, e in enumerate(starts):
        o = vec(e["origin"])
        gx, gy, gz = gd(o)
        ang = vec(e.get("angles", "0 0 0"))
        m.spawn("props" if i % 2 == 0 else "hunters", gx, gz, yaw=ang[1] - 90.0, y=max(gy, 0.0) + 0.05)
    # The author gave six starts; a prop hunt wants six hiding starts and three hunter ones.
    # More are taken from the clearest open floor, at least 3 m from any other start.
    have = [(sp["at"][0], sp["at"][2]) for side in m.spawns.values() for sp in side]
    for size, x, z in m.spots(step=1.5, top=60):
        if len(m.spawns["props"]) >= 8:
            break
        if all((x - a) ** 2 + (z - b) ** 2 >= 9.0 for a, b in have):
            m.spawn("props", x, z, yaw=0.0)
            have.append((x, z))
    for tid, near in (("football", 5.0), ("barrel", 5.0), ("beach_ball", 5.0)):
        spot = next(((x, z) for size, x, z in m.spots(step=1.5, top=60) if all((x - a) ** 2 + (z - b) ** 2 >= 4.0 for a, b in have)), None)
        if spot:
            m.toy(tid, spot[0], spot[1], near=near)
            have.append(spot)
    print("props %d  lights %d  spawns %d  dropped models %s" % (len(m.props), len(m.lights), len(starts), dropped))
    doc = m.build()
    # Move the map so its origin stands on open ground. The collision audit tests a drawn
    # MultiMesh by its bounds, which a headless renderer reports as a point at the origin; a
    # map whose origin hangs in the air (this one's was outside the yard) fails it for every prop.
    ground = [b for b in doc["boxes"] if b.get("solid", True) and abs(b["at"][1] + b["size"][1] / 2) < 0.05
              and b["size"][0] > 4.0 and b["size"][2] > 4.0]
    if ground:
        cx = sum(sp["at"][0] for sp in doc["spawns"]["hunters"]) / len(doc["spawns"]["hunters"])
        cz = sum(sp["at"][2] for sp in doc["spawns"]["hunters"]) / len(doc["spawns"]["hunters"])
        g = min(ground, key=lambda b: (b["at"][0] - cx) ** 2 + (b["at"][2] - cz) ** 2)
        ox, oz = g["at"][0], g["at"][2]
        def shift(o):
            if isinstance(o, dict):
                if isinstance(o.get("at"), list) and len(o["at"]) == 3:
                    o["at"] = [round(o["at"][0] - ox, 3), o["at"][1], round(o["at"][2] - oz, 3)]
                for v in o.values():
                    shift(v)
            elif isinstance(o, list):
                for v in o:
                    shift(v)
        for key in ("boxes", "props", "lights", "spawns", "toys"):
            shift(doc.get(key))
    out_path = out_path or os.path.join(build_maps.ROOT, "maps", mid + ".json")
    with open(out_path, "w") as f:
        f.write(json.dumps(doc, indent=1) + "\n")
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv)
