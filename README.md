# mg-prop-hunt-maps

The maps for [mg-prop-hunt](https://github.com/zees-games/mg-prop-hunt). Four maps of our own (a school, a family house, an office floor and a clearing in the woods) and 29 converted from community maps. The game also has a practice house built in.

A map is a JSON document, not a scene. The server reads every `.json` file in its map directory and sends the current map to each client, so players need no map files. To add a map, drop one file in the directory. The format is in [maps/README.md](maps/README.md).

## Using it

[dot-bootstrap](https://github.com/modcommunity/dot-bootstrap) clones this repository next to mg-prop-hunt and links it in as `maps/`. Run `./game.sh` in mg-prop-hunt and you play these maps. On a server they are delivered as one pack (`prophunt_maps`), which `./game.sh online` and `./game.sh server` build for you.

## Our maps

| Map | What is in it |
| --- | --- |
| `ph_school` (Maple Grove School) | Classrooms, library, cafeteria, gym, offices, lockers, then the playground, field, car park and trees |
| `ph_house` (Willow Lane) | Living room, kitchen, bedrooms, garage, a garden with a deck and pool, the street in front |
| `ph_office` (Brightline Offices) | Open-plan desks, glass meeting rooms, a break room, a store room full of boxes |
| `ph_woods` (Pinecrest Woods) | A log cabin in a clearing, a woodpile, a pumpkin patch, a pond, trees and rocks |

## Converted community maps

Each map keeps the author's layout. Every texture, model and sound is replaced with the game's own CC0 stand-ins. Each document carries the author and source in its own fields, and the full licence entry is in [licence.json](licence.json).

| Map | Author | Source | Licence |
| --- | --- | --- | --- |
| `ph_abandoned_church` (Abandoned Church) | Z(Rus) | [GameBanana](https://gamebanana.com/mods/61478) | CC BY-NC-ND 4.0 |
| `ph_abandoned_hotel` (Abandoned Hotel) | Ethosaur | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=324656288) | none stated |
| `ph_airbus` (Airbus) | Officer_B (uploaded by Zaratusa) | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=253297309) | none stated |
| `ph_apartment` (Apartment) | Tib | [GameBanana](https://gamebanana.com/mods/61479) | CC BY-NC-ND 4.0 |
| `ph_autumngetaway` (Autumn Getaway) | I am tired | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3439942760) | none stated |
| `ph_bank` (Bank) | EHOT | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=667484197) | none stated |
| `ph_bikinibottom` (Bikini Bottom) | iitzRayD | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=1123262520) | none stated |
| `ph_cyber_dinner` (Cyber Diner) | MiniYLITKA | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3594394752) | none stated |
| `ph_deco_mansion` (Deco Mansion) | Gastly_Furby_777 | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3698815153) | none stated |
| `ph_elementary_school` (Elementary School) | Ethosaur | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=331545400) | none stated |
| `ph_frontyard` (Front Yard) | axoh | [GameBanana](https://gamebanana.com/mods/398632) | none stated |
| `ph_functionalist_night` (Functionalist Night) | VITAPLEX | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3382694345) | none stated |
| `ph_gas_station` (Gas Station) | Kung Fu Jesus | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=233540367) | none stated |
| `ph_hotel` (Hotel) | 1Vodker1 | [GameBanana](https://gamebanana.com/mods/61495) | CC BY-NC-ND 4.0 |
| `ph_islandhouse` (Island House) | wolvindra | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=2942742596) | none stated |
| `ph_library` (Library) | Mikey | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=230076815) | none stated |
| `ph_midwestapartment` (Midwest Apartment) | Punkychaz | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3037478073) | none stated |
| `ph_mountainresort` (Mountain Resort) | prvec | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=2312309380) | none stated |
| `ph_oceanwaves` (Ocean Waves) | Gvarados | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=1654704542) | none stated |
| `ph_office221` (Presentation Office) | Z(Rus) (zeromapping) | [GameBanana](https://gamebanana.com/mods/61503) | CC BY-NC-ND 4.0 |
| `ph_restaurant_os` (Restaurant) | Wolvindra Vinzuerio | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3270930065) | none stated |
| `ph_rooftops_2016` (Rooftops 2016) | youmenow1 | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=534491717) | none stated |
| `ph_sunken_resort` (Sunken Resort) | Praisemantas | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3376822715) | none stated |
| `ph_swimmingpool` (Swimming Pool) | Wolvindra Vinzuerio | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=2927317814) | none stated |
| `ph_villa` (Villa) | korka007 | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=2633639653) | none stated |
| `ph_volcano` (Volcano) | Patrick™ | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=1073300849) | none stated |
| `ph_warehouse` (Warehouse) | Max Power | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=177889282) | none stated |
| `ph_westerncity` (Western City) | Skate6788 | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=1738480835) | none stated |
| `ph_wolfsmanor` (Wolf's Manor) | gruesomegit | [GameBanana](https://gamebanana.com/mods/61511) | CC BY-NC-ND 4.0 |

"None stated" means the source page gives no licence. A few Workshop pages carry extra terms, for example `ph_mountainresort` forbids re-uploading; it is converted by the owner's decision and removed on request.

If you made one of these maps and want it removed, open an issue at <https://github.com/zees-games/mg-prop-hunt-maps/issues> and it goes.

## Building the maps

`tools/build_maps.py` writes the four own maps. Walls with doors and windows, rooms with floor, ceiling and lights, and furnished classrooms are one call each.

```bash
python3 tools/build_maps.py                # rewrite maps/*.json
python3 tools/build_maps.py --check        # exit 1 if a file differs from the builder's output
python3 tools/build_maps.py --sync-sizes   # copy prop sizes from ../mg-prop-hunt
```

The JSON is committed and CI runs `--check`. The builder moves a spawn that sits under a prop or wall to the nearest clear spot, and refuses to write a map with furniture in a doorway. Hand-written documents are fine too: any `.json` file in `maps/` loads.

Converted maps come from `tools/import_bsp.py`. It turns brushes into boxes, the author's physics and dynamic props into catalogue props, and shares start points between the teams. Useful flags: `--field=name=value` keeps a balance number such as `players_per_hunter` across reruns, `--drop-beside` and `--clear` remove props that wall a place off, `--style=yard` dresses a grid-textured map, `--terrain` converts ground heightfields. Rerun the importer with the original `.bsp`; `build_maps.py` does not touch imported maps.

mg-prop-hunt's `examples/headless_maps.tscn` checks every map: size on the wire, known props, spawns with floor and headroom, no prop sunk in a wall, every prop standing on something.

## Licence

MIT, see [LICENSE](LICENSE). The furniture and nature models are Kenney's (CC0) and live in mg-prop-hunt. The converted maps keep the licences listed above.
