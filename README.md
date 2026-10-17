The maps for [**mg-prop-hunt**](https://github.com/zees-games/mg-prop-hunt): a whole primary school with its grounds, a family house with a garden and a pool, an office floor, and a clearing in the woods at golden hour. Four maps to start with, plus the practice house built into the game.

Every map is a **JSON document**, not a scene. A server reads the documents in its map directory and sends the one it is playing to every client when the map changes, so players need no map files at all and a new map is one file dropped into a directory. [`maps/README.md`](maps/README.md) is the format.

## Using it

[dot-bootstrap](https://github.com/modcommunity/dot-bootstrap) clones this repository next to mg-prop-hunt and links it into the game as `maps/`, so `./game.sh` in mg-prop-hunt plays these maps with nothing else to do. On a server they are delivered as a pack of their own (`prophunt_maps`), which mg-prop-hunt's `./game.sh online` and `./game.sh server` build for you.

## The maps

| Map | What it is |
| --- | --- |
| `ph_school` (Maple Grove School) | Four classrooms, a library, a cafeteria, a gym, bathrooms, the offices and a hallway of lockers, then the playground, the field, the car park and a ring of trees outside |
| `ph_house` (Willow Lane) | A living room, kitchen, two bedrooms, a bathroom and a garage, with a garden, a deck and a pool behind it and the street in front |
| `ph_office` (Brightline Offices) | Open-plan desks, glass meeting rooms, a break room and a store room full of boxes, on one floor with glass all round |
| `ph_woods` (Pinecrest Woods) | A log cabin in a clearing, a woodpile, a pumpkin patch, a pond and a lot of trees and rocks to be |
| `ph_frontyard` (Front Yard) | **Converted from a community map** (see Credits): a walled yard with a small house, a melon patch, an oil-drum yard and a lot of lamps, crates and furniture to be |
| `ph_office221` (Presentation Office) | **Converted from a community map** (see Credits): a small corporate floor with a curved lobby, a presentation room, filing cabinets, binders, cardboard boxes and a lot of desk clutter to be |

## Credits: community maps

These are other people's work, converted with their layout kept and every texture and model replaced by the game's own CC0 stand-ins. Each is credited here, and **any author can ask for removal at any time and it is removed**: open an issue or write to the maintainers.

| Map | Author | Source | Original licence text |
| --- | --- | --- | --- |
| `ph_frontyard` | axoh | https://gamebanana.com/mods/398632 (`ph_frontyard.rar`, 2022-08-28) | "do whatever idc just dont say this terrible map is urs"; GameBanana's checklist leaves redistribution and modification as "ask". Credit and removal on request is the arrangement. |
| `ph_office221` | Z(Rus) (zeromapping) | https://gamebanana.com/mods/61503 (`ph_office221_2.7z`, 2014-01-01 release) | Creative Commons Attribution-NonCommercial-NoDerivs 4.0; GameBanana's checklist leaves redistribution and modification as "ask". Credit and removal on request is the arrangement: **this map is removed on request**. |

`tools/import_bsp.py` does the conversion (`tools/bsp_read.py` is copied from game-g2gfast's importer): brushes become boxes (a brush turned off the grid becomes a box with a yaw, and a wedge of a curved wall the smallest turned box round it), the author's `prop_physics*` and `prop_dynamic*` become catalogue props, the start entities of either team are shared between the teams. Door leaves the author left standing ajar are dropped (they close a doorway to the bots' nav), scenery out of reach of the starts is pruned, `--field=name=value` keeps a balance number (`players_per_hunter`, `hide_seconds`) across reruns, and `--drop-beside` and `--clear` take away the props that wall a place off, as named by the `PH_BOTS_TRACE=1` "cut off" lines of headless_bots (ph_office221 uses both: a row of cabinets a hand's width off the lobby wall, and a sunken cubby of counters too tall to step over). A map the author left as a developer grid is given suburban surfaces by shape with `--style=yard` (ph_frontyard); a skinned map keeps the surfaces its material names say. Unlike the generated maps above, an imported map's JSON is **not** rewritten by `build_maps.py`; rerun the importer with the original `.bsp`.

## How they are made

`tools/build_maps.py` writes every document in `maps/`. A wall with its doors and windows, a room with its floor, ceiling and lights, and a furnished classroom are one call each, and every prop is placed by where it stands.

```bash
python3 tools/build_maps.py                # rewrite maps/*.json
python3 tools/build_maps.py --check        # exit 1 if a file differs from what the builder writes
python3 tools/build_maps.py --sync-sizes   # copy prop sizes from ../mg-prop-hunt after it measures new models
```

The JSON is still what the game reads and is committed; CI runs `--check`, so a hand edit to a built document is caught instead of being lost on the next build. Hand-written documents the builder does not produce are fine too: anything in `maps/` with a `.json` extension is loaded.

The builder moves any spawn that a prop or a wall was put on top of to the nearest clear spot and says so. It refuses to write a map with furniture in a doorway or out in the middle of a hallway, and names the piece. Every map is then checked by mg-prop-hunt's `examples/headless_maps.tscn`: it fits on the wire, every prop is one the game knows, every spawn has a floor and room for a person, no prop is sunk into a wall, and every prop stands on something.

## License

MIT. See [LICENSE](LICENSE). The furniture and nature models the maps name are Kenney's (CC0) and live in mg-prop-hunt.
