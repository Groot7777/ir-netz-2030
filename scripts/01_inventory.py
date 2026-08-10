#!/usr/bin/env python3
"""
Phase 1 - Bestandsaufnahme der KML-Datei.

Liest die KML-Rohdatei ein und erstellt einen strukturierten Bericht
(Placemark-Typen, Liniennamen, Ordnerstruktur, Farben, Bounding Box),
ohne irgendetwas zu rendern oder zu verändern.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

KML_NS = "{http://www.opengis.net/kml/2.2}"
INPUT_PATH = Path("data/input/RENetz_2030_v3.kml")
OUTPUT_PATH = Path("data/01_inventory.json")


def kml_color_to_hex(kml_color: str) -> str:
    """KML-Farben sind aabbggrr (Alpha, Blau, Grün, Rot) -> #rrggbb umwandeln."""
    kml_color = kml_color.strip()
    if len(kml_color) != 8:
        return "#000000"
    aa, bb, gg, rr = kml_color[0:2], kml_color[2:4], kml_color[4:6], kml_color[6:8]
    return f"#{rr}{gg}{bb}"


def parse_coords(text: str):
    """KML-Koordinatentext 'lon,lat,alt lon,lat,alt ...' in Liste von (lon, lat) umwandeln."""
    points = []
    for tok in text.split():
        parts = tok.split(",")
        lon, lat = float(parts[0]), float(parts[1])
        points.append((lon, lat))
    return points


def tag(elem):
    """Namespace-Präfix vom Tag-Namen entfernen."""
    return elem.tag.replace(KML_NS, "")


def walk_folders(elem, path):
    """Rekursiv durch Document/Folder laufen und Placemarks mit ihrem Ordnerpfad sammeln."""
    results = []
    for child in elem:
        t = tag(child)
        if t == "Folder":
            name_el = child.find(f"{KML_NS}name")
            folder_name = name_el.text.strip() if name_el is not None and name_el.text else "(unbenannt)"
            results.extend(walk_folders(child, path + [folder_name]))
        elif t == "Placemark":
            results.append((child, list(path)))
        else:
            # rekursiv auch in andere Container schauen (z.B. verschachtelte Document)
            if len(list(child)) > 0:
                results.extend(walk_folders(child, path))
    return results


def extract_geometry(placemark):
    """Liefert Liste von (geom_typ, koordinaten) fuer ein Placemark, inkl. MultiGeometry."""
    geoms = []

    def handle(elem):
        t = tag(elem)
        if t == "LineString":
            coords_el = elem.find(f"{KML_NS}coordinates")
            if coords_el is not None and coords_el.text:
                geoms.append(("LineString", parse_coords(coords_el.text)))
        elif t == "Point":
            coords_el = elem.find(f"{KML_NS}coordinates")
            if coords_el is not None and coords_el.text:
                geoms.append(("Point", parse_coords(coords_el.text)))
        elif t == "MultiGeometry":
            for sub in elem:
                handle(sub)

    for child in placemark:
        t = tag(child)
        if t in ("LineString", "Point", "MultiGeometry"):
            handle(child)
    return geoms


def main():
    if not INPUT_PATH.exists():
        print(f"Fehler: {INPUT_PATH} nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    tree = ET.parse(INPUT_PATH)
    root = tree.getroot()
    document = root.find(f"{KML_NS}Document")
    if document is None:
        document = root

    # --- Styles einlesen (Linienfarben) ---
    styles = {}
    for style_el in document.iter(f"{KML_NS}Style"):
        style_id = style_el.get("id")
        line_style = style_el.find(f"{KML_NS}LineStyle")
        if line_style is not None:
            color_el = line_style.find(f"{KML_NS}color")
            width_el = line_style.find(f"{KML_NS}width")
            styles[style_id] = {
                "type": "LineStyle",
                "kml_color": color_el.text if color_el is not None else None,
                "hex_color": kml_color_to_hex(color_el.text) if color_el is not None and color_el.text else None,
                "width": float(width_el.text) if width_el is not None and width_el.text else None,
            }
        else:
            icon_style = style_el.find(f"{KML_NS}IconStyle")
            if icon_style is not None:
                icon_el = icon_style.find(f"{KML_NS}Icon/{KML_NS}href")
                styles[style_id] = {
                    "type": "IconStyle",
                    "icon_href": icon_el.text if icon_el is not None else None,
                }

    # --- Placemarks inkl. Ordnerpfad sammeln ---
    placemark_folder_pairs = walk_folders(document, [])

    folder_paths_used = sorted({" / ".join(p) for _, p in placemark_folder_pairs if p})

    geometry_type_counts = {"LineString": 0, "Point": 0, "MultiGeometry_LineString": 0, "MultiGeometry_Point": 0}
    line_placemarks = []
    point_placemarks = []
    all_lons = []
    all_lats = []

    for placemark, folder_path in placemark_folder_pairs:
        name_el = placemark.find(f"{KML_NS}name")
        name = name_el.text.strip() if name_el is not None and name_el.text else None
        style_url_el = placemark.find(f"{KML_NS}styleUrl")
        style_url = style_url_el.text.lstrip("#") if style_url_el is not None and style_url_el.text else None

        # direkte Kinder-Tags pruefen, um zu wissen ob MultiGeometry vorliegt
        direct_tags = [tag(c) for c in placemark]
        has_multigeom = "MultiGeometry" in direct_tags

        geoms = extract_geometry(placemark)
        geom_types_here = [g[0] for g in geoms]

        for gtype, coords in geoms:
            for lon, lat in coords:
                all_lons.append(lon)
                all_lats.append(lat)

        if "LineString" in geom_types_here:
            if has_multigeom:
                geometry_type_counts["MultiGeometry_LineString"] += 1
            else:
                geometry_type_counts["LineString"] += 1
            n_segments = sum(1 for g in geom_types_here if g == "LineString")
            total_points = sum(len(c) for t, c in geoms if t == "LineString")
            line_placemarks.append({
                "name": name,
                "style_url": style_url,
                "hex_color": styles.get(style_url, {}).get("hex_color"),
                "width": styles.get(style_url, {}).get("width"),
                "folder_path": folder_path,
                "is_multigeometry": has_multigeom,
                "n_linestring_segments": n_segments,
                "n_coordinate_points": total_points,
            })
        elif "Point" in geom_types_here:
            if has_multigeom:
                geometry_type_counts["MultiGeometry_Point"] += 1
            else:
                geometry_type_counts["Point"] += 1
            lon, lat = geoms[0][1][0]
            point_placemarks.append({
                "name": name,
                "style_url": style_url,
                "folder_path": folder_path,
                "lon": lon,
                "lat": lat,
            })

    # --- Style-IDs die als Linienstile aussehen, aber nicht verwendet werden ---
    used_style_urls = {p["style_url"] for p in line_placemarks} | {p["style_url"] for p in point_placemarks}
    line_style_ids = {sid for sid, s in styles.items() if s["type"] == "LineStyle"}
    unused_line_styles = sorted(line_style_ids - used_style_urls)

    # --- Namens-Duplikate bei Punkten (Hinweis auf Halte, die von mehreren Linien erwaehnt werden) ---
    point_name_counts = {}
    for p in point_placemarks:
        point_name_counts[p["name"]] = point_name_counts.get(p["name"], 0) + 1
    duplicate_point_names = sorted([n for n, c in point_name_counts.items() if c > 1])

    bbox = None
    if all_lons and all_lats:
        bbox = {
            "min_lon": min(all_lons),
            "max_lon": max(all_lons),
            "min_lat": min(all_lats),
            "max_lat": max(all_lats),
        }

    report = {
        "input_file": str(INPUT_PATH),
        "summary": {
            "total_placemarks": len(placemark_folder_pairs),
            "geometry_type_counts": geometry_type_counts,
            "n_line_placemarks": len(line_placemarks),
            "n_point_placemarks": len(point_placemarks),
            "n_styles_total": len(styles),
            "n_line_styles": len(line_style_ids),
            "n_unused_line_styles": len(unused_line_styles),
            "n_distinct_point_names": len(point_name_counts),
            "n_duplicate_point_names": len(duplicate_point_names),
        },
        "folder_structure": {
            "has_folders": len(folder_paths_used) > 0,
            "folder_paths_used": folder_paths_used,
        },
        "line_placemarks": line_placemarks,
        "unused_line_styles": [{"style_id": sid, **styles[sid]} for sid in unused_line_styles],
        "duplicate_point_names_sample": duplicate_point_names[:20],
        "bounding_box": bbox,
        "styles": styles,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Konsolen-Bericht ---
    print("=== Phase 1: Bestandsaufnahme ===")
    print(f"Placemarks gesamt: {report['summary']['total_placemarks']}")
    print(f"  davon LineString (einzeln):        {geometry_type_counts['LineString']}")
    print(f"  davon LineString (in MultiGeometry): {geometry_type_counts['MultiGeometry_LineString']}")
    print(f"  davon Point (einzeln):              {geometry_type_counts['Point']}")
    print(f"  davon Point (in MultiGeometry):      {geometry_type_counts['MultiGeometry_Point']}")
    print(f"Linien-Placemarks: {len(line_placemarks)}")
    print(f"Halte-Placemarks (Points): {len(point_placemarks)} ({len(point_name_counts)} eindeutige Namen)")
    print(f"Ordnerstruktur vorhanden: {report['folder_structure']['has_folders']}")
    print(f"Styles gesamt: {len(styles)} (davon {len(line_style_ids)} Linienstile, {len(unused_line_styles)} ungenutzt)")
    if unused_line_styles:
        print(f"  Ungenutzte Linienstile: {unused_line_styles}")
    print(f"Bounding Box: {bbox}")
    print(f"\nBericht geschrieben nach {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
