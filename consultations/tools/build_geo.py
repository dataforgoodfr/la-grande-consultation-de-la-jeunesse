#!/usr/bin/env python3
"""Build resources/geo/france.json (départements + régions, simplified) from public boundaries.

One-off development script (needs `shapely`, NOT needed to run the notebooks):
    python tools/build_geo.py departements-avec-outre-mer.geojson resources/geo/france.json

Source of the boundaries: github.com/gregoiredavid/france-geojson (open data, derived from IGN Admin Express).
The département -> région table below is the post-2016 administrative division.
The regions are built as the union of their départements, so both levels always match.
"""

import json
import sys
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

REGIONS = {
    "11": ("Île-de-France", "75 77 78 91 92 93 94 95"),
    "24": ("Centre-Val de Loire", "18 28 36 37 41 45"),
    "27": ("Bourgogne-Franche-Comté", "21 25 39 58 70 71 89 90"),
    "28": ("Normandie", "14 27 50 61 76"),
    "32": ("Hauts-de-France", "02 59 60 62 80"),
    "44": ("Grand Est", "08 10 51 52 54 55 57 67 68 88"),
    "52": ("Pays de la Loire", "44 49 53 72 85"),
    "53": ("Bretagne", "22 29 35 56"),
    "75": ("Nouvelle-Aquitaine", "16 17 19 23 24 33 40 47 64 79 86 87"),
    "76": ("Occitanie", "09 11 12 30 31 32 34 46 48 65 66 81 82"),
    "84": ("Auvergne-Rhône-Alpes", "01 03 07 15 26 38 42 43 63 69 73 74"),
    "93": ("Provence-Alpes-Côte d'Azur", "04 05 06 13 83 84"),
    "94": ("Corse", "2A 2B"),
    "01": ("Guadeloupe", "971"),
    "02": ("Martinique", "972"),
    "03": ("Guyane", "973"),
    "04": ("La Réunion", "974"),
    "06": ("Mayotte", "976"),
}
TOLERANCE = 0.004  # degrees (about 400 m): small enough for the Île-de-France zoom


def rings(geom):
    """Polygons of a (Multi)Polygon as [[outer ring, hole, ...], ...] with coordinates rounded to 3 decimals."""
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    out = []
    for p in polys:
        if p.is_empty:
            continue
        out.append([[[round(x, 3), round(y, 3)] for x, y in r.coords] for r in [p.exterior, *p.interiors]])
    return out


def main(src, dst):
    region_of = {d: code for code, (_, deps) in REGIONS.items() for d in deps.split()}
    features = json.load(open(src, encoding="utf-8"))["features"]
    departments, geoms = [], {}
    for f in features:
        code = f["properties"]["code"]
        g = shape(f["geometry"]).simplify(TOLERANCE, preserve_topology=True)
        geoms.setdefault(region_of[code], []).append(g)
        departments.append(
            {"code": code, "name": f["properties"]["nom"], "region": region_of[code], "polygons": rings(g)}
        )
    missing = set(region_of) - {d["code"] for d in departments}
    assert not missing, f"départements absents du fichier source : {missing}"
    regions = [
        {
            "code": c,
            "name": REGIONS[c][0],
            "polygons": rings(unary_union(gs).simplify(TOLERANCE, preserve_topology=True)),
        }
        for c, gs in geoms.items()
    ]
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"departments": departments, "regions": regions}, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(departments)} départements, {len(regions)} régions -> {dst} ({Path(dst).stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
