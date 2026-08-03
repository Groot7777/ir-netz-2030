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


PLACEMARK_RE = re.compile(r"<Placemark>.*?</Placemark>\n?", re.DOTALL)
NAME_IN_PLACEMARK_RE = re.compile(r"<name>(.*?)</name>")


def main():
    with open(BASELINE, encoding="utf-8") as f:
        baseline_text = f.read()

    routes = load_routes()
    station_blocks_by_key = build_station_blocks()

    # Mehrere ASCII-Keys koennen auf denselben Anzeigenamen zeigen (identische reale
    # Station, z.B. "Unna"/"Unna Hbf" oder "Wengern"/"Wengern Ost") -> zusammenfuehren,
    # damit nicht zwei Placemarks am selben Punkt entstehen. Repraesentativer Key pro
    # Anzeigename = der erste in ALL_LINES-Reihenfolge angetroffene.
    station_blocks = {}  # display_name -> Bloecke
    repr_key_for_display = {}  # display_name -> ein ASCII-Key (fuer Koordinate/is_preexisting)
    for key, blocks in station_blocks_by_key.items():
        disp = DISPLAY_NAMES[key]
        station_blocks.setdefault(disp, []).extend(blocks)
        repr_key_for_display.setdefault(disp, key)

    all_display_names = sorted(station_blocks.keys(), key=sort_key_umlaut)

    # 1. Alle bestehenden Stationen patchen (Text bleibt sonst unveraendert)
    patched = 0
    for disp in all_display_names:
        key = repr_key_for_display[disp]
        if ast.is_preexisting(key):
            baseline_text = patch_existing_station(baseline_text, disp, station_blocks[disp])
            patched += 1

    # 2. Kopf (bis zum ersten Placemark) von den Placemarks trennen
    first_pm_idx = baseline_text.index("<Placemark>")
    header = baseline_text[:first_pm_idx]
    rest = baseline_text[first_pm_idx:]
    tail_match = re.search(r"</Document>\s*</kml>\s*$", rest)
    if not tail_match:
        raise RuntimeError("Kein </Document></kml>-Abschluss gefunden")
    body = rest[:tail_match.start()]
    footer = rest[tail_match.start():]

    existing_placemarks = PLACEMARK_RE.findall(body)
    existing_line_pms = [p for p in existing_placemarks if "<LineString" in p or "<MultiGeometry" in p]
    existing_station_pms = [p for p in existing_placemarks if "<Point>" in p]
    assert len(existing_line_pms) + len(existing_station_pms) == len(existing_placemarks)

    # 3. Neue Linien-Placemarks + Styles bauen
    style_defs = []
    new_line_pms = []
    for line in ld.ALL_LINES:
        style_id, placemark_xml = build_line_placemark(line, routes)
        color = LINE_COLORS[line["number"]]
        style_defs.append(f'<Style id="{style_id}"><LineStyle><color>{color}</color><width>4</width></LineStyle></Style>\n')
        new_line_pms.append(placemark_xml)
    header = header.rstrip() + "\n" + "".join(style_defs)

    # 4. Neue Stations-Placemarks bauen
    new_station_pms_by_name = {}
    created = 0
    for disp in all_display_names:
        key = repr_key_for_display[disp]
        if not ast.is_preexisting(key):
            lat, lon = ast.get_coord(key)
            new_station_pms_by_name[disp] = build_new_station_placemark(disp, lat, lon, station_blocks[disp])
            created += 1

    print(f"{patched} bestehende Stationen gepatcht, {created} neue Stationen erstellt")

    # 5. Alle Stations-Placemarks (bestehend, jetzt gepatcht + neu) global alphabetisch sortieren
    all_station_pms = list(existing_station_pms)
    for name, pm in new_station_pms_by_name.items():
        all_station_pms.append(pm)

    def name_of(pm):
        m = NAME_IN_PLACEMARK_RE.search(pm)
        return m.group(1) if m else ""

    all_station_pms.sort(key=lambda pm: sort_key_umlaut(name_of(pm)))

    body_out = "".join(existing_line_pms) + "".join(new_line_pms) + "".join(all_station_pms)

    final_text = header + body_out + footer

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"Geschrieben: {OUTPUT}")
    print(f"Linien: {len(existing_line_pms)} bestehend + {len(new_line_pms)} neu; "
          f"Stationen: {len(all_station_pms)} gesamt")

    # XML-Wohlgeformtheit pruefen
    ET.parse(OUTPUT)
    print("XML ist wohlgeformt.")


if __name__ == "__main__":
    main()
