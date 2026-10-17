#!/usr/bin/env python3
"""Converts a Source 1 community prop-hunt .bsp (VBSP 19/20) into a mg-prop-hunt map document.

    tools/import_bsp.py <map.bsp> <id> "<Name>" <author> <page-url> [--out=maps/<id>.json] [--style=yard] [--field=players_per_hunter=4] [--drop-beside=x,z,kind] [--clear=x0,z0,x1,z1]

--field=<name>=<number> sets a document number the map's own band wants (players_per_hunter, round_seconds,
hide_seconds), found by headless_bots, so a rerun of the importer keeps it.

--drop-beside=x,z,kind (repeatable, in the finished map's coordinates) drops the prop of that kind nearest that point (any kind if left out): the
headless_bots trace prints "cut off: (x, y, z) beside <prop>" for a place no route reaches, and spots
are found beside props, so this takes the place away. Reruns keep it.

--clear=x0,z0,x1,z1 (in the finished map's coordinates) drops every prop inside the rectangle: a cubby the
author walled in with counters too tall for a bot to step over, where one prop at a time is whack-a-mole.

--style=yard gives the developer-grid boxes a suburban surface by their shape (a yard map the
author left unskinned); other maps keep the surface their material names say.

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
    ("CEILINGTILE", "ceiling", None),
    ("OFFCEILING", "concrete", None),
    ("CARPET", "carpet", None),
    ("BLINDS", "glass", None),
    ("LIGHTCOVER", "glass", (1.00, 1.00, 0.92)),
    ("OFFWNDW", "glass", None),
    ("TRUSS", "metal", None),
    ("DRTRIM", "metal", None),
    ("ELEVDR", "metal", None),
    ("PARTICLEBOARD", "wood", None),
    ("OFFDR", "wood", None),
    ("DESKTOP", "wood", None),
    ("WALLOFFICE", "paint", (0.92, 0.94, 1.00)),
    ("OFFWLLB", "plaster", (0.90, 0.95, 1.00)),
    ("OFFWLLC", "paint", (0.96, 0.94, 0.88)),
    ("BUILDING", "concrete", None),
    ("PLASTER", "plaster", (0.95, 0.92, 0.84)),
    ("GRASS", "grass", (0.85, 0.95, 0.75)),
    ("ACOUSTICCEILING", "ceiling", None),
    ("TILEFLOOR", "tile", None),
    ("WOODFLOOR", "parquet", None),
    ("TILEROOF", "roof", (1.00, 0.72, 0.62)),
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
    # An office (ph_office221): paper, drawers, screens and boxes.
    "file_cabinet1": "furniture_side_table_drawers",
    "file_cabinet2": "furniture_side_table_drawers",
    "file_cabinet3": "furniture_side_table_drawers",
    "chair_office": "furniture_chair_desk",
    "binderredlabel": "furniture_books",
    "bindergreen": "furniture_books",
    "binderblue": "furniture_books",
    "bindergraylabel01a": "furniture_books",
    "bindergraylabel01b": "furniture_books",
    "binderbluelabel": "furniture_books",
    "bindergreenlabel": "furniture_books",
    "clipboard": "furniture_books",
    "cardboard_box01": "furniture_cardboard_box_closed",
    "cardboard_box02": "furniture_cardboard_box_closed",
    "cardboard_box03": "furniture_cardboard_box_closed",
    "cardboard_box001a": "furniture_cardboard_box_closed",
    "cardboard_box003a": "furniture_cardboard_box_open",
    "cardboard_box003b": "furniture_cardboard_box_open",
    "cardboard_box004a": "furniture_cardboard_box_closed",
    "box01a": "survival_box",
    "box01b": "survival_box",
    "file_box": "survival_box",
    "plant01": "furniture_potted_plant",
    "cactus": "nature_cactus_tall",
    "coffee_mug": "food_mug",
    "coffee_mug2": "food_mug",
    "coffee_mug3": "food_mug",
    "garbage_coffeemug001a_forevergibs": "food_cup_coffee",
    "phone": "furniture_speaker_small",
    "projector": "furniture_speaker_small",
    "projector_remote": "furniture_computer_mouse",
    "computer_caseb": "furniture_speaker",
    "computer_keyboard": "furniture_computer_keyboard",
    "computer_monitor": "furniture_computer_screen",
    "computer_mouse": "furniture_computer_mouse",
    "trash_can": "furniture_trashcan",
    "trash_can_p": "furniture_trashcan",
    "garbage_beercan01a": "food_soda_can",
    "garbage_plasticbottle001a": "survival_bottle",
    "garbage_plasticbottle002a": "survival_bottle",
    "garbage_plasticbottle002a_fullsheet": "survival_bottle",
    "garbage_takeoutcarton001a": "food_carton_small",
    "suitcase_passenger_physics": "survival_chest",
    "metalbucket01a": "survival_bucket",
    "pi_bucket": "survival_bucket",
    "tv_plasma": "furniture_television_modern",
    "table_coffee": "furniture_table_coffee",
}


# The author left every wall that is not a house as a developer grid. Those are given a
# suburban surface by what the box IS, since its texture says nothing: size and height tell a
# neighbour's tall wall from a fence, a path, a roof slab or a shed. Every name is an existing
# PhMaterials surface; the tint only chooses which pastel family it is.
SIDING_BLUE = (0.80, 0.88, 1.00)
SIDING_GREEN = (0.82, 0.96, 0.84)
BRICK_RED = (1.00, 0.86, 0.80)
ROOF_RED = (1.00, 0.72, 0.62)
FENCE_WHITE = (1.00, 0.96, 0.90)


def suburban_surface(at, size):
    """(mat, tint) for a developer-grid box, from its centre `at` and `size` in metres."""
    w, h, d = size
    top = at[1] + h / 2
    if h < 0.7 and max(w, d) > 2.0:
        # A slab: high up it is a roof or a balcony, at the ground a path or the drive.
        return ("roof", ROOF_RED) if top > 5.0 else ("sidewalk", None)
    if min(w, d) < 0.6 and h > 2.0:
        return "wood", FENCE_WHITE          # slats and pickets
    if h >= 8.0:
        # A neighbour's house wall round the yard: brick on two sides, siding on the others.
        if d > w:
            return "brick", BRICK_RED
        return ("plaster", SIDING_BLUE) if at[2] < 0 else ("plaster", SIDING_GREEN)
    if h >= 4.5:
        return "plaster", SIDING_BLUE        # the upper storey of a house
    if abs(w - h) < 0.1 and abs(d - h) < 0.1:
        return "brick", BRICK_RED            # a shed block or a chimney stack
    return "wood", FENCE_WHITE               # a yard fence or a low wall


def classify(name):
    """A Source material name without its per-map folder and cubemap suffix. vbsp renames a
    material the map patches to MAPS/<map>/<group>/<name>_<x>_<y>_<z>, and the folder carries
    the map's own name, which must not decide a surface (a map called ph_school would match
    SCHOOL-anything); only the material's own name does."""
    n = name.upper()
    if n.startswith("MAPS/"):
        n = n.split("/", 2)[-1]
    return re.sub(r"(_-?\d+){3}$", "", n)


# Every entity class an author uses for a loose prop; the _dynamic ones are placed furniture
# that does not move in the original, which a catalogue prop is not either (it is a disguise).
PROP_CLASSES = ("prop_physics", "prop_physics_multiplayer", "prop_physics_override",
                "prop_dynamic", "prop_dynamic_override")
START_CLASSES = ("info_player_start", "info_player_terrorist", "info_player_counterterrorist",
                 "info_player_deathmatch", "info_player_teamspawn")


def within(b, x, z, slack=0.0):
    """Whether (x, z) is under box b's footprint, which a turned box (yaw) shares only in its own
    frame: the point is taken into it first (godot turns a box about +y)."""
    dx, dz = x - b["at"][0], z - b["at"][2]
    yaw = b.get("yaw", 0.0)
    if yaw:
        c, sn = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        dx, dz = dx * c - dz * sn, dx * sn + dz * c
    return abs(dx) <= b["size"][0] / 2 + slack and abs(dz) <= b["size"][2] / 2 + slack


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
    best = classify(max(set(pool), key=pool.count))
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


def box_in_frame(pts, phi, tol):
    """The hull's extents in a frame turned phi degrees about z, or None when some corner is not
    a corner of that bounding box. (x0, x1), (y0, y1), (z0, z1), in the turned frame."""
    c, sn = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    q = [(p[0] * c + p[1] * sn, -p[0] * sn + p[1] * c, p[2]) for p in pts]
    x0, x1 = min(p[0] for p in q), max(p[0] for p in q)
    y0, y1 = min(p[1] for p in q), max(p[1] for p in q)
    z0, z1 = min(p[2] for p in q), max(p[2] for p in q)
    for p in q:
        if not ((abs(p[0] - x0) < tol or abs(p[0] - x1) < tol) and (abs(p[1] - y0) < tol or abs(p[1] - y1) < tol)
                and (abs(p[2] - z0) < tol or abs(p[2] - z1) < tol)):
            return None
    return (x0, x1), (y0, y1), (z0, z1)


def turned_box(bsp, index, pts):
    """(box, phi) when the brush is a box turned about the vertical axis, else None. The author's
    building is not always on the grid (a room at thirty degrees to the rest), and cutting such a
    wall into axis-aligned slabs gives a saw-tooth the players catch on. The angle is each upright
    side's direction modulo 90, tried in turn; the document's boxes carry a yaw."""
    first, count, _ = bsp.brushes[index]
    tried = set()
    for sd in bsp.brushsides[first:first + count]:
        if sd[3]:
            continue
        nx, ny, nz, _d = bsp.planes[sd[0]][:4]
        if abs(nz) > 1e-4:
            continue
        phi = round(math.degrees(math.atan2(ny, nx)) % 90.0, 2)
        if phi in tried or phi < 0.05 or phi > 89.95:
            continue
        tried.add(phi)
        # Four-decimal planes at 1000 units leave a unit of slack in the corners.
        box = box_in_frame(pts, phi, 1.5)
        if box is not None:
            return box, phi
    return None


def prism_box(pts):
    """(box, phi) for a brush that is a vertical prism of any plan shape: the smallest turned
    rectangle round its plan. A curved wall is a run of such wedges and a column of a round room
    is one; the box overhangs the wedge by a sliver, where cutting it into axis-aligned slabs (a
    slope's treatment, wrong for a plan shape) bit chunks out of the room. None for a brush whose
    top or bottom is not flat and level."""
    zs = sorted({round(p[2], 1) for p in pts})
    if len(zs) != 2:
        return None
    low = {(round(p[0], 1), round(p[1], 1)) for p in pts if abs(p[2] - zs[0]) < 0.15}
    high = {(round(p[0], 1), round(p[1], 1)) for p in pts if abs(p[2] - zs[1]) < 0.15}
    if low != high or len(low) < 3:
        return None
    plan = [(x, y, zs[0]) for x, y in low]
    best = None
    for (ax, ay), (bx_, by) in ((p, q) for p in low for q in low if p != q):
        phi = math.degrees(math.atan2(by - ay, bx_ - ax)) % 90.0
        box = box_in_frame(plan, phi, 1e9)
        area = (box[0][1] - box[0][0]) * (box[1][1] - box[1][0])
        if best is None or area < best[0] - 1e-6:
            best = (area, phi, box)
    _a, phi, box = best
    return (box[0], box[1], (zs[0], zs[1])), phi


def brush_boxes(bsp, index):
    """[((x range), (y range), (z range), phi)] in Source units, the ranges in a frame turned phi
    degrees (0 for most), and whether the brush had to be cut into slabs."""
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
        return [((x0, x1), (y0, y1), (z0, z1), 0.0)], 0
    tb = turned_box(bsp, index, pts)
    if tb is not None:
        return [tb[0] + (tb[1],)], 0
    pb = prism_box(pts)
    if pb is not None:
        return [pb[0] + (pb[1],)], 0
    pl = planes_of(bsp, index)
    out = []
    if x1 - x0 >= y1 - y0:
        n = max(1, math.ceil((x1 - x0) / SLAB))
        for i in range(n):
            a, b = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
            lo, hi = z_range(pl, (a + b) / 2, (y0 + y1) / 2)
            lo, hi = max(lo, z0), min(hi, z1)
            if hi - lo > 0.5:
                out.append(((a, b), (y0, y1), (lo, hi), 0.0))
    else:
        n = max(1, math.ceil((y1 - y0) / SLAB))
        for i in range(n):
            a, b = y0 + (y1 - y0) * i / n, y0 + (y1 - y0) * (i + 1) / n
            lo, hi = z_range(pl, (x0 + x1) / 2, (a + b) / 2)
            lo, hi = max(lo, z0), min(hi, z1)
            if hi - lo > 0.5:
                out.append(((x0, x1), (a, b), (lo, hi), 0.0))
    return out, 1


def drop_door_leaves(m):
    """Remove door leaves the author left standing ajar in a doorway.

    A leaf is a wood slab as tall as a door, about a door wide and under 15 cm thick. In the
    source it swings clear of the opening; here it is a fixed box in the middle of a gap that is
    then too narrow for the bots' nav (radius plus a cell either side), which cuts a whole room
    off. The frame and the wall stay, so the doorway reads as a doorway."""
    kept, dropped = [], 0
    for b in m.boxes:
        w, h, d = b["size"]
        thin, wide = sorted((w, d))
        if b.get("mat") == "wood" and 1.9 <= h <= 2.3 and thin < 0.15 and 0.6 <= wide <= 1.1:
            dropped += 1
            continue
        kept.append(b)
    m.boxes[:] = kept
    return dropped


def prune_far_scenery(m, starts, reach=12.0):
    """Drops the boxes of every cluster that is out of reach of the starts. A community map keeps
    its 3D skybox scenery (a distant city, a crane) in the same world as the play space, and the
    overview camera frames all of it, so the real map shrank to a corner of the frame. Boxes are
    grouped by touching (a quarter metre of slack); a group is kept when one of its boxes comes
    within `reach` metres of a start; the author's sky-box walls that bound the play space are
    big enough to pass, and a second, sealed sky cell holding the scenery is dropped with it."""
    if not starts:
        return
    n = len(m.boxes)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def box_range(b):
        h = [b["size"][0] / 2, b["size"][1] / 2, b["size"][2] / 2]
        if b.get("yaw"):
            # The turned box's own bounds, so its slack is not the box's corner sticking out.
            c, sn = abs(math.cos(math.radians(b["yaw"]))), abs(math.sin(math.radians(b["yaw"])))
            h = [h[0] * c + h[2] * sn, h[1], h[0] * sn + h[2] * c]
        return [(b["at"][i] - h[i] - 0.25, b["at"][i] + h[i] + 0.25) for i in range(3)]

    rng = [box_range(b) for b in m.boxes]
    order = sorted(range(n), key=lambda i: rng[i][0][0])
    for ai, a in enumerate(order):
        for b in order[ai + 1:]:
            if rng[b][0][0] > rng[a][0][1]:
                break
            if all(rng[a][k][0] <= rng[b][k][1] and rng[b][k][0] <= rng[a][k][1] for k in (1, 2)):
                parent[find(a)] = find(b)
    keep = set()
    for i, b in enumerate(m.boxes):
        near = any(rng[i][0][0] - reach <= sx <= rng[i][0][1] + reach and rng[i][2][0] - reach <= sz <= rng[i][2][1] + reach
                   for sx, _sy, sz in starts)
        if near:
            keep.add(find(i))
    before = len(m.boxes)
    m.boxes[:] = [b for i, b in enumerate(m.boxes) if find(i) in keep]
    if len(m.boxes) != before:
        print("dropped %d boxes of scenery out of reach of the starts" % (before - len(m.boxes)))


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    out_path = None
    style = ""
    fields = {}
    drops = []
    clears = []
    for a in argv[1:]:
        if a.startswith("--out="):
            out_path = a[6:]
        elif a.startswith("--style="):
            style = a[8:]
        elif a.startswith("--field="):
            k, _, v = a[8:].partition("=")
            fields[k] = float(v)
        elif a.startswith("--clear="):
            clears.append(tuple(float(t) for t in a[8:].split(",")))
        elif a.startswith("--drop-beside="):
            t = a[14:].split(",")
            drops.append((float(t[0]), float(t[1]), t[2] if len(t) > 2 else ""))
    bsp_path, mid, name, author, url = args[:5]
    bsp = bsp_read.Bsp(bsp_path).load()
    m = build_maps.Map(
        mid, name, "Converted from %s by %s (%s)." % (os.path.basename(bsp_path), author, url),
        {"sky_top": [0.32, 0.52, 0.82], "sky_horizon": [0.72, 0.82, 0.92], "ground": [0.35, 0.33, 0.30],
         "sun_pitch": -55, "sun_yaw": 30, "sun_energy": 1.0, "ambient": [0.62, 0.66, 0.72], "ambient_energy": 0.5},
        kill_y=-20.0)
    m.doc["author"] = author
    m.doc.update(fields)
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
        for (x0, x1), (y0, y1), (z0, z1), phi in boxes:
            if phi:
                # A turned box: its centre back out of the turned frame, its sides as measured,
                # its yaw the same angle (Source turns counter-clockwise seen from above, and so
                # does godot about +y once y is flipped to -z).
                if x1 - x0 < 0.05 or y1 - y0 < 0.05 or z1 - z0 < 0.05:
                    continue
                c, sn = math.cos(math.radians(phi)), math.sin(math.radians(phi))
                lx, ly = (x0 + x1) / 2, (y0 + y1) / 2
                gx, gy, gz = gd((lx * c - ly * sn, lx * sn + ly * c, (z0 + z1) / 2))
                bx = m.box((gx, gy, gz), ((x1 - x0) * S, (z1 - z0) * S, (y1 - y0) * S), mt[0], mt[1], yaw=phi)
            else:
                # Source y is godot -z: the box's range flips.
                bx = m.span(x0 * S, x1 * S, z0 * S, z1 * S, -y1 * S, -y0 * S, mt[0], mt[1])
            if invisible and bx is not None:
                bx["visible"] = False
            elif bx is not None and mt[0] == "flat" and style == "yard":
                bx["mat"], tint = suburban_surface(bx["at"], bx["size"])
                if tint is not None:
                    bx["tint"] = list(tint)
                else:
                    bx.pop("tint", None)
    print("brushes %d  tool-only %d  sliced %d  boxes %d" % (len(bsp.model_brushes(0)), skipped, sliced, len(m.boxes)))

    drop_door_leaves(m)
    prune_far_scenery(m, [gd(vec(e["origin"])) for e in bsp.entities if e.get("classname") in START_CLASSES])

    # Props: sit on the highest solid box under the footprint when one is within reach of the
    # source height, else at the source height (a lamp on a table the author placed as a prop).
    def support(x, z, pid, yaw, ymax):
        """The highest thing under the footprint no higher than ymax: a box's top, or a prop
        already set down (`rest_on`, its collision as the game measured it). The catalogue's
        table is not the author's table, so a lamp set at the author's table-top height would
        hang in the air; it is put on whatever is really there instead."""
        best = 0.0 if ymax >= 0.0 else None
        fw, fd = build_maps.footprint(pid, yaw) if pid else (0.0, 0.0)
        for b in m.boxes:
            if not b.get("solid", True):
                continue
            if within(b, x, z, 0.001):
                t = b["at"][1] + b["size"][1] / 2
                if t <= ymax and (best is None or t > best):
                    best = t
        for q in m.props:
            qw, qd = build_maps.footprint(q["id"], q.get("yaw", 0.0))
            # Well inside the footprint, not on its rim: a round bin's corner is air.
            if abs(x - q["at"][0]) <= qw / 2 - 0.08 and abs(z - q["at"][2]) <= qd / 2 - 0.08:
                t = q["at"][1] + build_maps.rest_on(q, x - q["at"][0], z - q["at"][2], pid, yaw)
                if t <= ymax and (best is None or t > best):
                    best = t
        return best

    dropped = {}
    placed = []
    for e in bsp.entities:
        cls = e.get("classname")
        if cls in PROP_CLASSES:
            # Keys are matched lower-cased: authors spell one model Chair_office and chair_office.
            key = os.path.splitext(os.path.basename(e.get("model", "")))[0].lower()
            pid = PROP_MAP.get(key)
            if pid is None:
                dropped[key] = dropped.get(key, 0) + 1
                continue
            placed.append((vec(e["origin"])[2], e, pid))
        elif cls in ("light", "light_spot"):
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
                    if within(b, x + dx, z + dz):
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
    starts = [e for e in bsp.entities if e.get("classname") in START_CLASSES]
    for i, e in enumerate(starts):
        o = vec(e["origin"])
        gx, gy, gz = gd(o)
        ang = vec(e.get("angles", "0 0 0"))
        # Stands on whatever floor is under the start (a sunken room is below zero), not on zero.
        floor = support(gx, gz, None, 0.0, gy + 0.6)
        m.spawn("props" if i % 2 == 0 else "hunters", gx, gz, yaw=ang[1] - 90.0, y=(max(gy, 0.0) if floor is None else floor) + 0.05)
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
    # Spots are found beside props, so taking the prop away takes the spot: for a place the
    # headless_bots trace names as cut off (a slot between a row of furniture and a wall).
    for x0, z0, x1, z1 in clears:
        gone = [q for q in doc["props"] if x0 <= q["at"][0] <= x1 and z0 <= q["at"][2] <= z1]
        for q in gone:
            doc["props"].remove(q)
        print("cleared %d props from the cubby (%.1f, %.1f) to (%.1f, %.1f)" % (len(gone), x0, z0, x1, z1))
    for dx, dz, kind in drops:
        near = [q for q in doc["props"] if not kind or q["id"] == kind]
        near.sort(key=lambda q: (q["at"][0] - dx) ** 2 + (q["at"][2] - dz) ** 2)
        if near and (near[0]["at"][0] - dx) ** 2 + (near[0]["at"][2] - dz) ** 2 <= 1.8 ** 2:
            doc["props"].remove(near[0])
            print("dropped %s at %s beside (%.1f, %.1f)" % (near[0]["id"], near[0]["at"], dx, dz))
    out_path = out_path or os.path.join(build_maps.ROOT, "maps", mid + ".json")
    with open(out_path, "w") as f:
        f.write(json.dumps(doc, indent=1) + "\n")
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv)
