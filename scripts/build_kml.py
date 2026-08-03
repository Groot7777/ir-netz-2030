# -*- coding: utf-8 -*-
"""Baut die finale KML: patcht bestehende Stations-Placemarks, fuegt neue Stations-
und Linien-Placemarks hinzu. Haelt sich an die KML-2.2-Elementreihenfolge und die
Regel 'keine Placemarks in Foldern'."""
import os
import re
import xml.etree.ElementTree as ET

import lines_data as ld
import all_stations as ast
from display_names import DISPLAY_NAMES
from descriptions import build_station_blocks, build_line_overview_html
from assemble_paths import load_routes, simplified_branch_path
from kml_helpers import (
    LINE_COLORS, xml_escape, cdata_description, station_lookat,
    line_lookat_from_points, coords_kml,
)

HERE = os.path.dirname(__file__)
BASELINE = os.path.join(HERE, "..", "data", "RENetz_2030_v2_baseline.kml")
OUTPUT = os.path.join(HERE, "..", "output", "RENetz_2030_v3.kml")

NS = {"k": "http://www.opengis.net/kml/2.2"}
ET.register_namespace("", "http://www.opengis.net/kml/2.2")


def sort_key_umlaut(name):
    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
            "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
            "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ś": "s", "ź": "z", "ż": "z",
            "ø": "o", "å": "a", "ě": "e", "ř": "r", "č": "c", "š": "s", "ž": "z"}
    s = name.lower()
    for a, b in repl.items():
        s = s.replace(a.lower(), b.lower())
    return s


def build_new_station_placemark(display_name, lat, lon, blocks):
    inner = "<br/><br/>".join(blocks)
    desc = cdata_description(inner)
    lookat = station_lookat(lat, lon)
    name_tag = f"<name>{xml_escape(display_name)}</name>"
    lon_s, lat_s = f"{lon:.7f}", f"{lat:.7f}"
    return (
        "<Placemark>\n"
        f"{name_tag}\n"
        f"{desc}\n"
        f"{lookat}\n"
        "<styleUrl>#stationPinNoLabel</styleUrl>\n"
        f"<Point><coordinates>{lon_s},{lat_s},0</coordinates></Point>\n"
        "</Placemark>\n"
    )


def build_line_placemark(line, routes):
    number = line["number"]
    color_id = f"line{number.replace('/', '').replace(' ', '')}"
    style_id = f"style_{color_id}"
    desc_html = build_line_overview_html(line)
    desc = cdata_description(desc_html)
    name_tag = f"<name>{xml_escape(number)} {xml_escape(line['route_name'])}</name>"

    branch_paths = []
    all_points = []
    for br in line["branches"]:
        stops = br["stops"]
        if line["kind"] == "ring":
            # Ring schliessen: letzte Station -> erste Station zurueckrouten
            closing_key = stops[0][0]
            stops = list(stops) + [(closing_key,) + stops[0][1:]]
        path = simplified_branch_path(routes, stops, tolerance_m=18.0)
        branch_paths.append(path)
        all_points.extend(path)

    lookat = line_lookat_from_points(all_points)

    if len(branch_paths) == 1:
        geom = f"<LineString><tessellate>1</tessellate><coordinates>{coords_kml(branch_paths[0])}</coordinates></LineString>"
    else:
        parts = "".join(
            f"<LineString><tessellate>1</tessellate><coordinates>{coords_kml(p)}</coordinates></LineString>"
            for p in branch_paths
        )
        geom = f"<MultiGeometry>{parts}</MultiGeometry>"

    return style_id, (
        "<Placemark>\n"
        f"{name_tag}\n"
        f"{desc}\n"
        f"{lookat}\n"
        f"<styleUrl>#{style_id}</styleUrl>\n"
        f"{geom}\n"
        "</Placemark>\n"
    )


def patch_existing_station(baseline_text, display_name, new_blocks):
    """Findet den Placemark mit <name>display_name</name> und fuegt neue Bloecke
    vor dem schliessenden </div> der CDATA-Description ein."""
    name_pattern = re.compile(
        r'(<Placemark>\s*<name>' + re.escape(display_name) + r'</name>\s*<description><!\[CDATA\[)'
        r'(.*?)'
        r'(\]\]></description>)',
        re.DOTALL,
    )
    matches = list(name_pattern.finditer(baseline_text))
    if not matches:
        raise ValueError(f"Placemark fuer '{display_name}' nicht gefunden")
    if len(matches) > 1:
        raise ValueError(f"Mehrdeutiger Name '{display_name}' ({len(matches)} Treffer)")
    m = matches[0]
    cdata_content = m.group(2)
    insert_html = "<br/><br/>" + "<br/><br/>".join(new_blocks)
    div_close_idx = cdata_content.rfind("</div>")
    if div_close_idx == -1:
        raise ValueError(f"Kein </div> in CDATA von '{display_name}' gefunden")
    new_cdata = cdata_content[:div_close_idx] + insert_html + cdata_content[div_close_idx:]
    new_block_text = m.group(1) + new_cdata + m.group(3)
    start, end = m.span()
    return baseline_text[:start] + new_block_text + baseline_text[end:]


def main():
    with open(BASELINE, encoding="utf-8") as f:
        baseline_text = f.read()

    routes = load_routes()
    station_blocks = build_station_blocks()

    all_keys = sorted(station_blocks.keys(), key=lambda k: sort_key_umlaut(DISPLAY_NAMES[k]))

    new_station_xml_parts = []
    patched = 0
    created = 0
    for key in all_keys:
        disp = DISPLAY_NAMES[key]
        blocks = station_blocks[key]
        if ast.is_preexisting(key):
            baseline_text = patch_existing_station(baseline_text, disp, blocks)
            patched += 1
        else:
            lat, lon = ast.get_coord(key)
            new_station_xml_parts.append(build_new_station_placemark(disp, lat, lon, blocks))
            created += 1

    print(f"{patched} bestehende Stationen gepatcht, {created} neue Stationen erstellt")

    # Styles fuer die 6 neuen Linien
    style_defs = []
    line_placemark_parts = []
    for line in ld.ALL_LINES:
        style_id, placemark_xml = build_line_placemark(line, routes)
        color = LINE_COLORS[line["number"]]
        style_defs.append(f'<Style id="{style_id}"><LineStyle><color>{color}</color><width>4</width></LineStyle></Style>\n')
        line_placemark_parts.append(placemark_xml)

    # Neue Styles direkt nach dem letzten bestehenden </Style> vor dem ersten Placemark einfuegen
    style_insert_point = baseline_text.index("<Placemark>")
    baseline_text = (
        baseline_text[:style_insert_point]
        + "".join(style_defs)
        + baseline_text[style_insert_point:]
    )

    new_content = "".join(line_placemark_parts) + "".join(new_station_xml_parts)

    final_text = baseline_text.replace("</Document>\n</kml>", new_content + "</Document>\n</kml>")
    if final_text == baseline_text:
        raise RuntimeError("Einfuegepunkt </Document></kml> nicht gefunden!")

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"Geschrieben: {OUTPUT}")

    # XML-Wohlgeformtheit pruefen
    ET.parse(OUTPUT)
    print("XML ist wohlgeformt.")


if __name__ == "__main__":
    main()
