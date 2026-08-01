#!/usr/bin/env python3
"""Flag any geocoded station whose coordinate falls outside a rough expected
bounding region for its line (catches catastrophic cross-continent mis-geocodes
like a North American station landing in Peru)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES_DIR = os.path.join(ROOT, "data", "lines")
CACHE_PATH = os.path.join(ROOT, "cache", "geocode_cache.json")

# line_id -> (min_lat, max_lat, min_lon, max_lon), generous boxes
REGIONS = {
    "muenster_ruhr": (50.5, 52.5, 5.5, 8.5),
    "wbc": (51.0, 51.8, 6.8, 7.5),
    "oslo_inverness": (49.0, 60.5, -6.0, 13.5),
    "lille_bergen": (49.5, 61.5, -1.0, 12.0),
    "paris_singapur": (0.0, 52.0, 0.0, 105.0),
    "brandenburg_hel": (51.5, 55.5, 11.5, 19.5),
    "ncams": (30.0, 50.5, -128.0, -60.0),
    "pcms": (18.0, 50.5, -128.0, -95.0),
    "nha": (24.0, 50.5, -128.0, -68.0),
    "pnw_mae": (24.0, 50.5, -128.0, -68.0),
    "weltachse1": (44.0, 72.0, -140.0, 180.0),
    "rheinruhrkrim": (44.0, 55.0, 5.5, 34.5),
    "arktis_afrika": (33.0, 72.0, -8.0, 41.0),
}


def main():
    cache = json.load(open(CACHE_PATH))
    problems = []
    for fn in sorted(os.listdir(LINES_DIR)):
        if not fn.endswith(".json"):
            continue
        line = json.load(open(os.path.join(LINES_DIR, fn)))
        lid = line["id"]
        region = REGIONS.get(lid)
        if not region:
            continue
        min_lat, max_lat, min_lon, max_lon = region
        for s in line["stops"]:
            key = s["key"]
            entry = cache.get(key)
            if not entry:
                problems.append((lid, key, "NO_COORD", None, None))
                continue
            lat, lon = entry["lat"], entry["lon"]
            if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                problems.append((lid, key, "OUT_OF_REGION", lat, lon))
    if not problems:
        print("Alle Stationen innerhalb der erwarteten Region.")
        return
    print(f"{len(problems)} Probleme gefunden:")
    for lid, key, kind, lat, lon in problems:
        print(f"  [{lid}] {key!r}: {kind} @ {lat},{lon}")


if __name__ == "__main__":
    main()
