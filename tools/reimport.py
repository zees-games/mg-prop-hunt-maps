#!/usr/bin/env python3
"""Re-runs import_bsp.py for every converted map in ports.txt with its flags, then settles it, into maps/ (or --out=DIR).

    tools/reimport.py [--out=DIR] [--no-settle] [--no-environment] [id ...]

Run it as `heavy -- tools/reimport.py ...`: settling plays bot rounds.

Name, author and source come from the committed document, and the balance numbers it carries (players_per_hunter,
round_seconds, hide_seconds) are passed back as --field so a re-import keeps them. After the import:

1. the author's environment (tools/environments.sh's line for the map) is put back, as the importer writes none;
2. the map is settled: a bot round (mg-prop-hunt's headless_bots, `PH_BOTS_TRACE=1`) names every place cut off from the
   props' start, and retune.py drops the prop beside each, until none is left. These are the fixes that used to be made
   by hand on the committed document and were lost by a re-import. Doorways are widened first when most places are cut off. A map
   whose settling still drops more than SETTLE_LIMIT of its props is refused and the committed document put back: that is a
   wall or a door, a flag in ports.txt, not a prop.

Settling needs the document in the game's maps/ (so --out must be that folder); --out=DIR elsewhere skips it.
"""
import json, os, re, shlex, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get("MAPSRC", os.path.expanduser("~/mapsrc/prophunt"))
GAME = os.environ.get("PH_GAME", os.path.join(os.path.dirname(ROOT), "mg-prop-hunt"))
SETTLE_LIMIT = 0.12
SETTLE_ROUNDS = 10
CUT = re.compile(r"cut off: \(([-\d.]+), ([-\d.]+), ([-\d.]+)\) beside (\S+)")


def bsp_path(wid, name):
    for dirpath, _d, files in os.walk(os.path.join(SRC, wid if os.path.isdir(os.path.join(SRC, wid)) else "gb" + wid)):
        if name in files:
            return os.path.join(dirpath, name)
    sys.exit("no %s under %s" % (name, SRC))


def environment_args(mid):
    """The line environments.sh runs for this map: (bsp path relative to SRC, extra arguments)."""
    for line in open(os.path.join(HERE, "environments.sh")):
        t = line.split()
        if len(t) >= 3 and t[0] == "run" and t[2] == mid:
            return t[1], t[3:]
    return None, []


def cut_off(mid):
    """The places a bot round cannot reach from the props' start, as (x, z, kind), and the number of places."""
    env = dict(os.environ, PH_BOTS_TRACE="1")
    r = subprocess.run(["godot", "--headless", "--path", GAME, "res://examples/headless_bots.tscn", "--", "--map", mid, "--rounds", "1"],
                       capture_output=True, text=True, env=env, timeout=900)
    out = r.stdout + r.stderr
    places = re.search(r"\((\d+) of (\d+)", out.split("at most one place in fifty", 1)[-1]) if "at most one place in fifty" in out else None
    if not places:
        sys.exit("no cut-off line in the bot run for %s:\n%s" % (mid, out[-1500:]))
    return sorted({(float(a), float(c), k) for a, _b, c, k in CUT.findall(out)}), int(places.group(2))


def retune(mid, *flags):
    r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "retune.py"), mid] + list(flags), capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout + r.stderr)
    return r.stdout


AT = re.compile(r"(\w+) at \(([-\d.]+), ([-\d.]+), ([-\d.]+)\)")


def game_audit(mid, path, log):
    """Drops the props mg-prop-hunt's headless_maps names as sunk or floating that are in this document.

    The importer's own audit approximates the game's; what is left (a box that stood on a prop since dropped) is read
    from the game's failing lines until none are named. Returns the number dropped."""
    gone = 0
    for _ in range(8):
        r = subprocess.run(["godot", "--headless", "--path", GAME, "res://examples/headless_maps.tscn"], capture_output=True, text=True, timeout=1200)
        named = {(k, round(float(x), 3), round(float(y), 3), round(float(z), 3))
                 for line in (r.stdout + r.stderr).splitlines() if "FAIL" in line and ("sunk" in line or "stands on something" in line)
                 for k, x, y, z in AT.findall(line)}
        doc = json.load(open(path))
        keep = [q for q in doc["props"] if (q["id"], round(q["at"][0], 3), round(q["at"][1], 3), round(q["at"][2], 3)) not in named]
        if len(keep) == len(doc["props"]):
            break
        gone += len(doc["props"]) - len(keep)
        doc["props"] = keep
        with open(path, "w") as f:
            f.write(json.dumps(doc, indent=1) + "\n")
    log.append("game audit dropped %d props" % gone)
    return gone


def drop_cut_off(mid, path, log):
    """Drops the prop beside every place cut off until a bot round finds none. Returns the number dropped."""
    dropped, last = 0, None
    for i in range(SETTLE_ROUNDS):
        spots, places = cut_off(mid)
        log.append("settle %d: %d of %d places cut off" % (i, len(spots), places))
        if i == 0 and len(spots) > 0.1 * places:
            # Mostly cut off is a wall, not a prop: open every doorway to 1.4 m first (idempotent, retune.py).
            log.append(retune(mid, "--widen-thick-doors").strip())
            spots, places = cut_off(mid)
            log.append("widened: %d of %d places cut off" % (len(spots), places))
        if not spots or spots == last:
            break
        last = spots
        before = len(json.load(open(path))["props"])
        retune(mid, *["--drop-beside=%s,%s,%s" % s for s in spots])
        after = len(json.load(open(path))["props"])
        dropped += before - after
        if before == after:
            break
    return dropped


def settle(mid, path, log):
    """Cut-off places, then the game's own audit, again until the audit drops nothing (a dropped prop can leave
    another floating, and the audit's drop can cut a place off). Returns the number of props dropped."""
    dropped = 0
    for _ in range(4):
        dropped += drop_cut_off(mid, path, log)
        audited = game_audit(mid, path, log)
        dropped += audited
        if not audited:
            break
    spots, places = cut_off(mid)
    log.append("settled with %d of %d places still cut off" % (len(spots), places))
    return dropped, places


def main(argv):
    out = os.path.join(ROOT, "maps")
    only = []
    do_settle = do_env = True
    for a in argv[1:]:
        if a.startswith("--out="):
            out = a[6:]
        elif a == "--no-settle":
            do_settle = False
        elif a == "--no-environment":
            do_env = False
        else:
            only.append(a)
    if do_settle and os.path.realpath(out) != os.path.realpath(os.path.join(ROOT, "maps")):
        do_settle = False
    for line in open(os.path.join(HERE, "ports.txt")):
        cols = line.rstrip("\n").split("\t")
        mid, wid, bsp, flags, extra = (cols + [""] * 5)[:5]
        if only and mid not in only:
            continue
        committed = open(os.path.join(ROOT, "maps", mid + ".json")).read()
        doc = json.loads(committed)
        fields = ["--field=%s=%s" % (k, doc[k]) for k in ("players_per_hunter", "round_seconds", "hide_seconds") if doc.get(k)]
        if any(f.startswith("--field=players_per_hunter") for f in (flags + " " + extra).split()):
            fields = [f for f in fields if not f.startswith("--field=players_per_hunter")]
        target = os.path.join(out, mid + ".json")
        cmd = [sys.executable, "-I", os.path.join(HERE, "import_bsp.py"), bsp_path(wid, bsp), mid, doc["name"], doc["author"], doc["source"],
               "--out=" + target] + flags.split() + shlex.split(extra) + fields
        log = subprocess.run(cmd, capture_output=True, text=True)
        notes = [log.stdout + log.stderr]
        if log.returncode == 0 and do_env:
            rel, extra_env = environment_args(mid)
            if rel:
                r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "bsp_environment.py"), os.path.join(SRC, rel), target] + extra_env,
                                   capture_output=True, text=True)
                notes.append(r.stdout + r.stderr)
        if log.returncode == 0 and do_settle:
            lines = []
            dropped, places = settle(mid, target, lines)
            notes.append("\n".join(lines) + "\n")
            props = len(json.load(open(target))["props"])
            if dropped > SETTLE_LIMIT * (props + dropped):
                open(target, "w").write(committed)
                notes.append("rejected: settling dropped %d of %d props\n" % (dropped, props + dropped))
                print(mid, "rejected: settling dropped %d of %d props" % (dropped, props + dropped))
                open(os.path.join(SRC, "reimport_" + mid + ".log"), "w").write("".join(notes))
                continue
        open(os.path.join(SRC, "reimport_" + mid + ".log"), "w").write("".join(notes))
        print(mid, "rc", log.returncode)


if __name__ == "__main__":
    main(sys.argv)
