#!/usr/bin/env python3
"""
Wendet manuelle STATION_COORDS-Korrekturen (z.B. aus dem KML-Positions-
abgleich, tools/kml_station_check.py) direkt auf die App-HTML an.

Nutzung:
    python3 tools/apply_station_coords.py --corrections data/kml_work/kml_check_final.json
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from htmldata import extract_const, replace_const  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", default="app/RENetz2030_Fahrplanauskunft.html")
    ap.add_argument("--corrections", required=True, help="JSON: {name: {osm_lon, osm_lat, ...}}")
    args = ap.parse_args()

    html_path = pathlib.Path(args.html)
    html_text = html_path.read_text(encoding="utf-8")
    coords = extract_const(html_text, "STATION_COORDS")
    corrections = json.loads(pathlib.Path(args.corrections).read_text(encoding="utf-8"))

    applied = []
    for name, c in corrections.items():
        if name not in coords:
            print(f"  UEBERSPRUNGEN (kein STATION_COORDS-Eintrag): {name!r}")
            continue
        old = coords[name]
        new = [round(c["osm_lon"], 5), round(c["osm_lat"], 5)]
        coords[name] = new
        applied.append((name, old, new))

    new_html = replace_const(html_text, "STATION_COORDS", coords)
    html_path.write_text(new_html, encoding="utf-8")

    print(f"{len(applied)} STATION_COORDS korrigiert:")
    for name, old, new in applied:
        print(f"  {name!r:30s} {old} -> {new}")


if __name__ == "__main__":
    main()
