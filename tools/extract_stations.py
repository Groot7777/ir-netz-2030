#!/usr/bin/env python3
"""
Extrahiert STATION_COORDS und STATION_REGIONS aus der HTML-App zu
data/stations.json — Grundlage für die regionsweise Overpass-Abfrage
(tools/overpass_platforms.py). Nur lesend, kein Rückschreibpfad nötig.

Nutzung:
    python3 tools/extract_stations.py \
        --html app/RENetz2030_Fahrplanauskunft.html \
        --out  data/stations.json
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from htmldata import extract_const  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", default="app/RENetz2030_Fahrplanauskunft.html")
    ap.add_argument("--out", default="data/stations.json")
    args = ap.parse_args()

    html_text = pathlib.Path(args.html).read_text(encoding="utf-8")
    coords = extract_const(html_text, "STATION_COORDS")
    regions = extract_const(html_text, "STATION_REGIONS")

    out = {}
    for name, (lon, lat) in coords.items():
        r = regions.get(name, {})
        out[name] = {
            "lon": lon,
            "lat": lat,
            "region_type": r.get("type"),
            "region_code": r.get("code"),
        }

    missing_region = [n for n in coords if n not in regions]
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{len(out)} Stationen -> {args.out} ({len(missing_region)} ohne Region: {missing_region})")


if __name__ == "__main__":
    main()
