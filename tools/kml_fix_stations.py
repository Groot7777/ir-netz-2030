#!/usr/bin/env python3
"""
Wendet die von tools/kml_station_check.py gefundenen OSM-Korrekturen auf
eine Kopie der KML an: für jede Station, deren Symbol laut Check weiter
als --threshold-m vom echten OSM-Bahnhofsknoten entfernt liegt, werden
sowohl <Point><coordinates> als auch <LookAt><longitude>/<latitude> auf
die OSM-Position gesetzt. Alles andere (Linien, Beschreibungen, Styles)
bleibt byte-identisch — reiner Koordinaten-Fix je betroffenem Placemark.

Nutzung:
    python3 tools/kml_fix_stations.py \
        --kml <original.kml> --check data/kml_work/kml_check.json \
        --threshold-m 150 --out <korrigiert.kml>
"""
import argparse
import json
import pathlib
import re


def fix_placemark(block, name, new_lon, new_lat):
    # <LookAt><longitude>X</longitude><latitude>Y</latitude> ...
    block = re.sub(
        r"(<LookAt><longitude>)[\d.\-]+(</longitude><latitude>)[\d.\-]+(</latitude>)",
        rf"\g<1>{new_lon}\g<2>{new_lat}\g<3>",
        block,
        count=1,
    )
    # <Point><coordinates>lon,lat,0</coordinates></Point>
    block = re.sub(
        r"(<Point><coordinates>)[\d.\-]+,[\d.\-]+(,\d+</coordinates></Point>)",
        rf"\g<1>{new_lon},{new_lat}\g<2>",
        block,
        count=1,
    )
    return block


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kml", required=True)
    ap.add_argument("--check", default="data/kml_work/kml_check.json")
    ap.add_argument("--threshold-m", type=float, default=150.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    check = json.loads(pathlib.Path(args.check).read_text(encoding="utf-8"))

    to_fix = {
        name: r for name, r in check.items()
        if r["distance_m"] is not None and r["distance_m"] > args.threshold_m and r["osm_lon"] is not None
    }

    placemark_pat = re.compile(r"<Placemark>\s*<name>(.*?)</name>.*?</Placemark>", re.DOTALL)

    fixed = []
    def repl(m):
        name = m.group(1)
        if name in to_fix:
            r = to_fix[name]
            fixed.append((name, r["distance_m"], r["osm_name"]))
            return fix_placemark(m.group(0), name, r["osm_lon"], r["osm_lat"])
        return m.group(0)

    new_kml = placemark_pat.sub(repl, kml_text)

    pathlib.Path(args.out).write_text(new_kml, encoding="utf-8")
    print(f"{len(fixed)} von {len(to_fix)} Kandidaten korrigiert -> {args.out}")
    for name, dist, osm_name in sorted(fixed, key=lambda x: -x[1]):
        print(f"  {name!r:45s} {dist:7.0f} m  (OSM: {osm_name!r})")
    missing = set(to_fix) - {f[0] for f in fixed}
    if missing:
        print("NICHT gefunden/ersetzt (Placemark-Name mismatch?):", missing)


if __name__ == "__main__":
    main()
