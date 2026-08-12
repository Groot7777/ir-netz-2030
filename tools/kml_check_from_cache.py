#!/usr/bin/env python3
"""
Wertet ALLE bereits gecachten Overpass-Rohantworten (data/kml_work/
osm_station_cache/*.json, aus mehreren vorherigen Laeufen mit
unterschiedlichen Batch-Groessen) neu aus — komplett offline, keine
Netzwerkabfragen. Poolt alle Elemente aus allen Cache-Dateien global und
matcht dagegen je KML-Station per Name + naechster Distanz (Radius aus
--radius-m). Nutzt dieselbe name_match()-Logik wie kml_station_check.py.

Nutzung:
    python3 tools/kml_check_from_cache.py --kml <pfad> --out data/kml_work/kml_check.json
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from kml_station_check import haversine_m, name_match  # noqa: E402

KML_PLACEMARK_PATTERN = re.compile(
    r"<Placemark>\s*<name>(.*?)</name>.*?<Point><coordinates>([\d.\-]+),([\d.\-]+),\d+</coordinates></Point>\s*</Placemark>",
    re.DOTALL,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kml", required=True)
    ap.add_argument("--cache-dir", default="data/kml_work/osm_station_cache")
    ap.add_argument("--out", default="data/kml_work/kml_check.json")
    ap.add_argument("--radius-m", type=float, default=4000.0)
    ap.add_argument("--threshold-m", type=float, default=150.0)
    args = ap.parse_args()

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    stations = [(m.group(1), float(m.group(2)), float(m.group(3))) for m in KML_PLACEMARK_PATTERN.finditer(kml_text)]
    print(f"{len(stations)} KML-Stationen")

    all_elements = {}
    for f in pathlib.Path(args.cache_dir).glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        for el in data.get("elements", []):
            all_elements[(el["type"], el["id"])] = el
    elements = list(all_elements.values())
    print(f"{len(elements)} einzigartige OSM-Elemente aus {len(list(pathlib.Path(args.cache_dir).glob('*.json')))} Cache-Dateien gepoolt")

    results = {}
    for name, lon, lat in stations:
        candidates = []
        for el in elements:
            osm_name = el.get("tags", {}).get("name")
            if not name_match(name, osm_name):
                continue
            d = haversine_m(lat, lon, el["lat"], el["lon"])
            if d > args.radius_m:
                continue
            candidates.append((d, el["lat"], el["lon"], osm_name, el["type"], el["id"]))
        candidates.sort(key=lambda c: c[0])
        if candidates:
            d, olat, olon, osm_name, etype, eid = candidates[0]
            results[name] = {
                "kml_lon": lon, "kml_lat": lat,
                "osm_lon": round(olon, 7), "osm_lat": round(olat, 7),
                "osm_name": osm_name, "distance_m": round(d, 1),
                "osm_ref": f"{etype}/{eid}", "n_candidates": len(candidates),
            }
        else:
            results[name] = {
                "kml_lon": lon, "kml_lat": lat,
                "osm_lon": None, "osm_lat": None,
                "osm_name": None, "distance_m": None,
                "osm_ref": None, "n_candidates": 0,
            }

    pathlib.Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    n_ok = sum(1 for r in results.values() if r["distance_m"] is not None and r["distance_m"] <= args.threshold_m)
    n_off = sum(1 for r in results.values() if r["distance_m"] is not None and r["distance_m"] > args.threshold_m)
    n_none = sum(1 for r in results.values() if r["distance_m"] is None)
    print(f"\n{len(results)} Stationen -> {args.out}")
    print(f"ok (<= {args.threshold_m:.0f}m): {n_ok}   auffaellig (> {args.threshold_m:.0f}m): {n_off}   kein Treffer im Cache: {n_none}")


if __name__ == "__main__":
    main()
