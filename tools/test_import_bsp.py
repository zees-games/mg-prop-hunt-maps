#!/usr/bin/env python3
"""Tests for import_bsp.py's terrain detection on a synthetic map (ph_bikinibottom's sea bed is displacement terrain: with no
--terrain every start was over nothing and the import dropped them all). Set DOTBSP_PATH to the dot-map-convert checkout."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import import_bsp as ib  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("ok   " if ok else "FAIL ") + name)
    fails += 0 if ok else 1


class Bsp:
    def __init__(self, starts, disp):
        # origins are in source units (z up); gd() maps them to the game's frame
        self.entities = [{"classname": "info_player_terrorist", "origin": "%g %g %g" % p} for p in starts]
        self.disp = disp

    def model_faces(self, _m):
        return [(0, 0, 0, 0, 0, 0, 3 if self.disp else -1)]


floor = {"at": [0, -0.15, 0], "size": [20, 0.3, 20], "solid": True}
on_floor = [(0, 0, 0), (50, 50, 0)]
over_nothing = [(5000, 5000, 0), (-5000, 5000, 0)]
check("starts over a floor box: no terrain", not ib.wants_terrain(Bsp(on_floor, True), [floor]))
check("starts over nothing, displacements: terrain", ib.wants_terrain(Bsp(over_nothing, True), [floor]))
check("starts over nothing, no displacements: not terrain", not ib.wants_terrain(Bsp(over_nothing, False), [floor]))
check("no starts: no terrain", not ib.wants_terrain(Bsp([], True), [floor]))
check("starts_unfloored counts them", ib.starts_unfloored(Bsp(over_nothing + on_floor, True), [floor]) == 2)
sys.exit(1 if fails else 0)
