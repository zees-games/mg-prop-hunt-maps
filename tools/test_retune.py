#!/usr/bin/env python3
"""Unit tests for tools/retune.py: --carve and --widen-doors on a synthetic map, idempotence, no-op rewrite."""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retune  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("ok   " if ok else "FAIL ") + name)
    fails += 0 if ok else 1


def wall(x, z, sx, sz):
    return {"at": [x, 1.5, z], "size": [sx, 3.0, sz], "mat": "wall"}


def doc():
    floor = {"at": [0, -0.15, 0], "size": [20, 0.3, 20], "mat": "grass"}
    # a long wall along x at z=0 cut into two slabs with a 0.9 m door gap, plus a lone wall to carve
    return {"format": 1, "boxes": [floor, wall(-2.95, 0, 5.0, 0.2), wall(2.95, 0, 5.0, 0.2), wall(8, 5, 0.2, 6.0)],
            "props": [], "lights": [], "spawns": [], "toys": []}


def run(path, *args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "retune.py"), "x", "--in=" + path, "--out=" + path] + list(args),
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr)
    return r.stdout


with tempfile.TemporaryDirectory() as t:
    # carve: the long wall (x 5.5..10.5 wide? no: 0.2 x 6 along z at x=8) is cut by a rect across it
    boxes = doc()["boxes"]
    n = retune.carve(boxes, 7.0, 4.0, 9.0, 6.0)
    pieces = sorted((b["at"][2], b["size"][2]) for b in boxes if b["at"][0] == 8)
    check("carve cut one wall", n == 1)
    check("carve left the two end pieces", pieces == [(3.0, 2.0), (7.0, 2.0)])
    check("carve pieces avoid the opening", all(not (z - s / 2 < 6 and z + s / 2 > 4) for z, s in pieces))
    boxes = doc()["boxes"]
    check("carve elsewhere is a no-op", retune.carve(boxes, -9, 8, -8, 9) == 0 and len(boxes) == 4)
    boxes = doc()["boxes"]
    check("carve inside-only box goes", retune.carve(boxes, 7.5, 1.0, 8.5, 9.0) == 1 and len(boxes) == 3)

    p = os.path.join(t, "m.json")
    json.dump(doc(), open(p, "w"), indent=1)
    out = run(p, "--widen-doors")
    d = json.load(open(p))
    gap = None
    slabs = sorted((b for b in d["boxes"] if abs(b["at"][2]) < 0.01 and b["size"][1] == 3.0), key=lambda b: b["at"][0])
    if len(slabs) == 2:
        gap = (slabs[1]["at"][0] - slabs[1]["size"][0] / 2) - (slabs[0]["at"][0] + slabs[0]["size"][0] / 2)
    check("widen-doors widened 1 doorway", "widened 1 doorways" in out)
    check("widen-doors gap is 1.4 m", gap is not None and abs(gap - 1.4) < 0.01)
    first = open(p, "rb").read()
    out2 = run(p, "--widen-doors")
    check("widen-doors idempotent (bytes)", open(p, "rb").read() == first)
    check("second run reports unchanged", "unchanged" in out2)

    json.dump(doc(), open(p, "w"), indent=1)
    run(p, "--carve=7,4,9,6")
    first = open(p, "rb").read()
    run(p, "--carve=7,4,9,6")
    check("carve idempotent (bytes)", open(p, "rb").read() == first)

    # a no-op run never rewrites a file, even one formatted differently from our writer's output
    odd = os.path.join(t, "odd.json")
    open(odd, "w").write(json.dumps(doc()))
    before = open(odd, "rb").read()
    mt = os.stat(odd).st_mtime_ns
    run(odd)
    check("no-op leaves bytes and mtime", open(odd, "rb").read() == before and os.stat(odd).st_mtime_ns == mt)

# reimport.py: the trace line the settle step reads, and the environment line it re-applies
import reimport  # noqa: E402
m = reimport.CUT.findall("    cut off: (-13.0, 0.1, 6.5) beside furniture_bookcase_open_low\n    cut off: (1.7, 0.0, -13.8) beside survival_bucket")
check("settle parses cut-off lines", m == [("-13.0", "0.1", "6.5", "furniture_bookcase_open_low"), ("1.7", "0.0", "-13.8", "survival_bucket")])
rel, extra = reimport.environment_args("ph_westerncity")
check("environment line found", rel.endswith("ph_westerncity.bsp") and extra == ["--ambience=amb_wind"])
check("unknown map has no environment line", reimport.environment_args("ph_nope") == (None, []))
check("ports.txt has no stray text in the extra column", all(len(l.split("\t")) <= 5 and "FAIL" not in l for l in open(os.path.join(HERE, "ports.txt"))))

print("%d failed" % fails)
sys.exit(1 if fails else 0)
