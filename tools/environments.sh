#!/bin/bash
# Puts the author's environment into every converted map (see CLAUDE.md, "converted maps carry the author's own environment").
# Run it once on a fresh import (on a map at the 128-light cap a second run thins the lights again). The sources are under ~/mapsrc/prophunt/<workshop id>/x/ (ph_apartment, ph_hotel and ph_office221 have none on this machine).
D=${1:-$(dirname "$0")/../maps}; T=$(dirname "$0"); P=${MAPSRC:-$HOME/mapsrc/prophunt}
run(){ python3 -I "$T/bsp_environment.py" "$P/$1" "$D/$2.json" "${@:3}"; }
run 667484197/x/maps/ph_bank.bsp ph_bank --ambience=amb_city
run 1073300849/x/maps/ph_volcano_v1.bsp ph_volcano --ambience=amb_wind
run 1123262520/x/maps/ph_bikinibottom.bsp ph_bikinibottom
run 1654704542/x/maps/ph_oceanwaves.bsp ph_oceanwaves --ambience=amb_wind
run 1738480835/x/maps/ph_westerncity.bsp ph_westerncity --ambience=amb_wind
run 233540367/x/maps/ph_gas_station.bsp ph_gas_station --ambience=amb_night
run 2927317814/x/maps/ph_swimmingpool.bsp ph_swimmingpool
run 2942742596/x/maps/ph_islandhouse_2014.bsp ph_islandhouse
run 3037478073/x/maps/ph_midwestapartment.bsp ph_midwestapartment --ambience=amb_night
run 324656288/x/maps/ph_abandoned_hotel.bsp ph_abandoned_hotel --ambience=amb_eerie
run 3270930065/x/maps/ph_restaurant_os.bsp ph_restaurant_os
run 331545400/x/maps/ph_elementary_school.bsp ph_elementary_school
run 3439942760/x/maps/ph_autumngetaway.bsp ph_autumngetaway
run 3594394752/x/maps/ph_cyber_dinner.bsp ph_cyber_dinner --ambience=amb_night,amb_city
run 545923884/x/maps/ph_abandoned_church.bsp ph_abandoned_church --ambience=amb_eerie
run gb398632/x/ph_frontyard.bsp ph_frontyard
