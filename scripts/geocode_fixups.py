# -*- coding: utf-8 -*-
"""Gezielte Nachkorrekturen fuer Stationen, die beim ersten Geocoding-Lauf
falsch, unplausibel oder gar nicht getroffen wurden."""
import json
import os
from geocode import photon_query, haversine_km, CACHE_PATH, HEADERS

FIXUPS = {
    # key: (query, bias_lat, bias_lon, osm_tag_or_None)
    "Brandenburg Hbf": ("Brandenburg Hauptbahnhof", 52.4109, 12.5320, "railway:station"),
    "Herbede": ("Witten-Herbede", 51.4090, 7.2810, "railway:halt"),
    "Dahl": ("Dahl Volme", 51.2990, 7.5390, None),
    "Oesterport": ("Osterport", 55.6980, 12.5830, "railway:station"),
    "Steinhelle": ("Steinhelle", 51.3450, 8.4350, None),
    "Siedlinghausen": ("Siedlinghausen", 51.3160, 8.4650, None),
    "Drensteinfurt": ("Drensteinfurt", 51.7970, 7.7440, "railway:station"),
    "Bestwig": ("Bestwig", 51.3260, 8.3830, "railway:station"),
    "Almelo": ("Almelo", 52.3567, 6.6612, "railway:station"),
    "Silbach": ("Silbach", 51.2200, 8.4800, None),
    "Roedby": ("Rodby Station", 54.6900, 11.3900, "railway:station"),
}


def main():
    with open(CACHE_PATH, encoding="utf-8") as f:
        cache = json.load(f)

    for key, (query, blat, blon, tag) in FIXUPS.items():
        data = photon_query(query, blat, blon, osm_tag=tag)
        if not data or not data.get("features"):
            print(f"{key}: weiterhin kein Treffer fuer '{query}'")
            continue
        best, best_dist = None, None
        for feat in data["features"]:
            lon, lat = feat["geometry"]["coordinates"]
            dist = haversine_km(blat, blon, lat, lon)
            if best is None or dist < best_dist:
                best, best_dist = feat, dist
        props = best["properties"]
        lon, lat = best["geometry"]["coordinates"]
        old = cache.get(key)
        print(f"{key}: alt={old} neu=({lat:.4f},{lon:.4f}) {props.get('osm_key')}:{props.get('osm_value')} "
              f"name={props.get('name')} dist={best_dist:.2f}km")
        cache[key] = {
            "lat": lat, "lon": lon,
            "osm_tag": f"{props.get('osm_key')}:{props.get('osm_value')}",
            "matched_name": props.get("name"),
            "query_used": query, "tag_used": tag,
            "distance_km": round(best_dist, 2),
            "estimated": tag is None,
            "manual_fixup": True,
        }

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("gespeichert")


if __name__ == "__main__":
    main()
