#!/usr/bin/env python3
"""Re-runs import_bsp.py for every converted map in ports.txt with its flags, into a directory (default: maps/).

    tools/reimport.py [--out=DIR] [id ...]

Name, author and source come from the committed document, and the balance numbers it carries (players_per_hunter,
round_seconds, hide_seconds) are passed back as --field so a re-import keeps them. The result has no environment:
run tools/environments.sh on it.
"""
import json, os, shlex, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get("MAPSRC", os.path.expanduser("~/mapsrc/prophunt"))


def bsp_path(wid, name):
    for dirpath, _d, files in os.walk(os.path.join(SRC, wid if os.path.isdir(os.path.join(SRC, wid)) else "gb" + wid)):
        if name in files:
            return os.path.join(dirpath, name)
    sys.exit("no %s under %s" % (name, SRC))


def main(argv):
    out = os.path.join(ROOT, "maps")
    only = []
    for a in argv[1:]:
        if a.startswith("--out="):
            out = a[6:]
        else:
            only.append(a)
    for line in open(os.path.join(HERE, "ports.txt")):
        cols = line.rstrip("\n").split("\t")
        mid, wid, bsp, flags, extra = (cols + [""] * 5)[:5]
        if only and mid not in only:
            continue
        doc = json.load(open(os.path.join(ROOT, "maps", mid + ".json")))
        fields = ["--field=%s=%s" % (k, doc[k]) for k in ("players_per_hunter", "round_seconds", "hide_seconds") if doc.get(k)]
        if any(f.startswith("--field=players_per_hunter") for f in flags.split()):
            fields = [f for f in fields if not f.startswith("--field=players_per_hunter")]
        cmd = [sys.executable, "-I", os.path.join(HERE, "import_bsp.py"), bsp_path(wid, bsp), mid, doc["name"], doc["author"], doc["source"],
               "--out=" + os.path.join(out, mid + ".json")] + flags.split() + shlex.split(extra) + fields
        log = subprocess.run(cmd, capture_output=True, text=True)
        open(os.path.join(out, mid + ".log"), "w").write(log.stdout + log.stderr)
        print(mid, "rc", log.returncode)


if __name__ == "__main__":
    main(sys.argv)
