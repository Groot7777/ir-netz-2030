# -*- coding: utf-8 -*-
"""Extrahiert Name->Koordinate aller bestehenden Bahnhofs-Placemarks aus der Baseline-KML."""
import xml.etree.ElementTree as ET
import json
import os

NS = {"k": "http://www.opengis.net/kml/2.2"}
BASELINE = os.path.join(os.path.dirname(__file__), "..", "data", "RENetz_2030_v2_baseline.kml")
OUT = os.path.join(os.path.dirname(__file__), "..", "cache", "existing_stations.json")


def main():
    tree = ET.parse(BASELINE)
    root = tree.getroot()
    doc = root.find("k:Document", NS)
    result = {}
    for pm in doc.findall("k:Placemark", NS):
        name_el = pm.find("k:name", NS)
        point_el = pm.find("k:Point", NS)
        if point_el is None:
            continue  # Linien-Placemarks haben LineString/MultiGeometry, keine Point
        name = name_el.text
        coords_el = point_el.find("k:coordinates", NS)
        lon, lat, _alt = coords_el.text.strip().split(",")
        result[name] = {"lon": float(lon), "lat": float(lat)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{len(result)} bestehende Stationen extrahiert -> {OUT}")


if __name__ == "__main__":
    main()
