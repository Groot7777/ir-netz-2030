#!/usr/bin/env python3
"""Assemble the combined network KML from data/lines/*.json + cache/geocode_cache.json
+ cache/overpass_cache.json + data/ocean_crossings.json.

Structural rules (hard-won, do not violate):
- NEVER put Placemarks inside a <Folder> -- flat <Document>, Placemarks as direct children.
- Placemark child order: name, description, LookAt, styleUrl, geometry.
- LookAt child order: longitude, latitude, altitude, heading, tilt, range, altitudeMode.
- Colors in KML are AABBGGRR (reverse of RGB).
- Branches -> MultiGeometry with multiple LineStrings in one Placemark (not used currently,
  no line in this network needs true branching after data review).
"""
import html
import json
import math
import os
import sys
from xml.sax.saxutils import escape as xml_escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_utils import douglas_peucker, great_circle_points, haversine_km

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES_DIR = os.path.join(ROOT, "data", "lines")
GEOCODE_CACHE_PATH = os.path.join(ROOT, "cache", "geocode_cache.json")
OVERPASS_CACHE_PATH = os.path.join(ROOT, "cache", "overpass_cache.json")
CROSSINGS_PATH = os.path.join(ROOT, "data", "ocean_crossings.json")
OUTPUT_PATH = os.path.join(ROOT, "output", "ir_netz_2030.kml")

SIMPLIFY_TOLERANCE_M = 18.0
UMLAUT_SORT = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss", "Ä": "A", "Ö": "O", "Ü": "U"})


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def sort_key(name):
    return name.translate(UMLAUT_SORT).lower()


def rgb_to_kml_color(rgb_hex, alpha="ff"):
    rgb_hex = rgb_hex.lstrip("#")
    r, g, b = rgb_hex[0:2], rgb_hex[2:4], rgb_hex[4:6]
    return f"{alpha}{b}{g}{r}".lower()


def fmt_hms_to_takt(hms):
    # "HH:MM:SS" -> "xx:MM"
    if not hms:
        return None
    parts = hms.split(":")
    return f"xx:{parts[1]}"


def fmt_hms_clock(hms):
    if not hms:
        return None
    parts = hms.split(":")
    return f"{parts[0]}:{parts[1]}"


def hms_to_seconds(hms):
    h, m, s = [int(x) for x in hms.split(":")]
    return h * 3600 + m * 60 + s


def seconds_to_hms(secs):
    secs = int(round(secs)) % (24 * 3600)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_reverse_schedule(stops, start_time):
    """Symmetric mirroring: reverse stop order; each stop's mirrored arr/dep is
    total_duration minus the forward dep/arr (in seconds from line start), preserving
    dwell times but running the clock backwards through the trip."""
    t0 = hms_to_seconds(start_time)
    fwd_arr_sec = []
    fwd_dep_sec = []
    for i, s in enumerate(stops):
        day = s.get("day_offset", 0) or 0
        a = (hms_to_seconds(s["arr"]) + day * 24 * 3600 - t0) if s.get("arr") else None
        d = (hms_to_seconds(s["dep"]) + day * 24 * 3600 - t0) if s.get("dep") else None
        # only fall back to a same-day wraparound when the line has no explicit
        # day_offset data at all (short single-day trips where a later stop's clock
        # time is numerically smaller than the start, e.g. crossing midnight once)
        if not any(st.get("day_offset") for st in stops):
            if a is not None and a < 0:
                a += 24 * 3600
            if d is not None and d < 0:
                d += 24 * 3600
        fwd_arr_sec.append(a)
        fwd_dep_sec.append(d)
    total = fwd_arr_sec[-1] if fwd_arr_sec[-1] is not None else fwd_dep_sec[-1]

    rev_stops = []
    n = len(stops)
    for i in range(n - 1, -1, -1):
        s = stops[i]
        # mirrored arrival = total - forward departure of this stop (unless it's the
        # new-first stop, which has no arrival, mirroring the old-last stop's null arr)
        mirrored_arr = None if fwd_dep_sec[i] is None else total - fwd_dep_sec[i]
        mirrored_dep = None if fwd_arr_sec[i] is None else total - fwd_arr_sec[i]
        rev_stops.append({
            "key": s["key"], "display": s.get("display"), "note": s.get("note"),
            "arr_sec": mirrored_arr, "dep_sec": mirrored_dep,
        })
    return rev_stops, total


def display_name(key, geocode_cache_entry, stop=None):
    if stop and stop.get("display"):
        return stop["display"]
    return key


def load_all_lines():
    lines = []
    for fn in sorted(os.listdir(LINES_DIR)):
        if fn.endswith(".json"):
            lines.append(load_json(os.path.join(LINES_DIR, fn), {}))
    return lines


def crossing_key_set(crossings):
    return {"||".join(sorted([c["a"], c["b"]])): c for c in crossings.get("crossings", [])}


def segment_coords(key_a, key_b, coord_a, coord_b, overpass_cache, crossing_keys):
    cache_key = "||".join(sorted([key_a, key_b]))
    if cache_key in crossing_keys:
        return great_circle_points(coord_a, coord_b, n=48), "great_circle"
    entry = overpass_cache.get(cache_key)
    if entry and entry.get("status") == "ok":
        coords = [tuple(p) for p in entry["coords"]]
        # cache is undirected; orient it to start near coord_a
        if haversine_km(coords[0], coord_a) > haversine_km(coords[-1], coord_a):
            coords = list(reversed(coords))
        return coords, "routed"
    # not yet routed: straight-line fallback (flagged, to be replaced once Overpass
    # routing completes for this segment)
    return [coord_a, coord_b], "fallback_straight"


def build_line_path(stops, geocode_cache, overpass_cache, crossing_keys):
    full = []
    fallback_segments = []
    for i in range(len(stops) - 1):
        ka, kb = stops[i]["key"], stops[i + 1]["key"]
        if ka not in geocode_cache or kb not in geocode_cache:
            fallback_segments.append((ka, kb, "missing_geocode"))
            continue
        ca = (geocode_cache[ka]["lat"], geocode_cache[ka]["lon"])
        cb = (geocode_cache[kb]["lat"], geocode_cache[kb]["lon"])
        coords, kind = segment_coords(ka, kb, ca, cb, overpass_cache, crossing_keys)
        if kind == "fallback_straight":
            fallback_segments.append((ka, kb, kind))
        if full and full[-1] == coords[0]:
            full.extend(coords[1:])
        else:
            full.extend(coords)
    return full, fallback_segments


def kml_placemark_line(line, path_simplified, color_hex):
    coords_str = " ".join(f"{lon:.6f},{lat:.6f},0" for lat, lon in path_simplified)
    lats = [p[0] for p in path_simplified]
    lons = [p[1] for p in path_simplified]
    if not lats:
        return ""
    mid_lat = (min(lats) + max(lats)) / 2
    mid_lon = (min(lons) + max(lons)) / 2
    diag_km = haversine_km((min(lats), min(lons)), (max(lats), max(lons)))
    look_range = max(4000, min(400000, diag_km * 1000 * 0.6))

    name = xml_escape(line["name_display"])
    desc_parts = [f"<b>{xml_escape(line['name_display'])}</b><br/>"]
    if line.get("vehicle_note"):
        desc_parts.append(f"{xml_escape(line['vehicle_note'])}<br/>")
    if line.get("infra_note"):
        desc_parts.append(f"{xml_escape(line['infra_note'])}<br/>")
    desc_parts.append("<br/><b>Beispielfahrt (Stopliste):</b><br/>")
    for s in line["stops"]:
        parts = []
        if s.get("arr"):
            parts.append(f"an {fmt_hms_clock(s['arr'])}")
        if s.get("dep"):
            parts.append(f"ab {fmt_hms_clock(s['dep'])}")
        t = " / ".join(parts) if parts else ""
        nm = s.get("display") or s["key"]
        desc_parts.append(f"{xml_escape(nm)}: {t}<br/>")
    desc_parts.append(DARK_MODE_CSS)
    description = "".join(desc_parts)

    return f"""  <Placemark>
    <name>{name}</name>
    <description><![CDATA[{description}]]></description>
    <LookAt>
      <longitude>{mid_lon:.6f}</longitude>
      <latitude>{mid_lat:.6f}</latitude>
      <altitude>0</altitude>
      <heading>0</heading>
      <tilt>0</tilt>
      <range>{look_range:.0f}</range>
      <altitudeMode>clampToGround</altitudeMode>
    </LookAt>
    <styleUrl>#line_{line['id']}</styleUrl>
    <LineString>
      <tessellate>1</tessellate>
      <coordinates>{coords_str}</coordinates>
    </LineString>
  </Placemark>
"""


DARK_MODE_CSS = """<style>@media (prefers-color-scheme: dark) { body { background:#1e1e1e; color:#eee; } }</style>"""


def build_station_registry(lines, geocode_cache):
    stations = {}
    for line in lines:
        rev_stops, total = build_reverse_schedule(line["stops"], line["start_time"])
        fwd_terminus_key = line["stops"][-1]["key"]
        fwd_terminus = line["stops"][-1].get("display") or fwd_terminus_key
        rev_terminus_key = line["stops"][0]["key"]
        rev_terminus = line["stops"][0].get("display") or rev_terminus_key
        for s in line["stops"]:
            key = s["key"]
            st = stations.setdefault(key, {"display": s.get("display") or key, "serving": []})
            if s.get("display") and not stations[key].get("display_is_final"):
                st["display"] = s["display"]
            st["serving"].append({
                "line": line, "direction": "fwd", "stop": s,
                "destination": fwd_terminus, "destination_key": fwd_terminus_key,
            })
        for s in rev_stops:
            key = s["key"]
            st = stations.setdefault(key, {"display": s.get("display") or key, "serving": []})
            st["serving"].append({
                "line": line, "direction": "rev", "stop": s,
                "destination": rev_terminus, "destination_key": rev_terminus_key,
            })
    return stations


def kml_placemark_station(key, info, geocode_cache):
    if key not in geocode_cache:
        return "", False
    lat, lon = geocode_cache[key]["lat"], geocode_cache[key]["lon"]
    name = xml_escape(info["display"])

    desc_parts = [f"<b>{xml_escape(info['display'])}</b><br/><br/>"]
    for entry in info["serving"]:
        line = entry["line"]
        stop = entry["stop"]
        dest = xml_escape(entry["destination"])
        line_name = xml_escape(line["name_display"])
        if entry["direction"] == "fwd":
            arr_takt = fmt_hms_to_takt(stop.get("arr")) if stop.get("arr") else None
            dep_takt = fmt_hms_to_takt(stop.get("dep")) if stop.get("dep") else None
        else:
            arr_takt = f"xx:{seconds_to_hms(stop['arr_sec'])[3:5]}" if stop.get("arr_sec") is not None else None
            dep_takt = f"xx:{seconds_to_hms(stop['dep_sec'])[3:5]}" if stop.get("dep_sec") is not None else None
        bits = []
        if arr_takt:
            bits.append(f"an {arr_takt}")
        if dep_takt:
            bits.append(f"ab {dep_takt}")
        takt_str = " / ".join(bits) if bits else "(Endstation)"
        note = stop.get("note")
        note_str = f" &mdash; {xml_escape(note)}" if note else ""
        if entry["destination_key"] == key:
            # this station IS the terminus of this direction: "Richtung <self>" would be
            # nonsensical, so label it as the terminus arrival instead
            desc_parts.append(f"<i>{line_name}</i> Endstation: {takt_str}{note_str}<br/>")
        else:
            desc_parts.append(f"<i>{line_name}</i> Richtung {dest}: {takt_str}{note_str}<br/>")
    desc_parts.append(DARK_MODE_CSS)
    description = "".join(desc_parts)

    placemark = f"""  <Placemark>
    <name>{name}</name>
    <description><![CDATA[{description}]]></description>
    <LookAt>
      <longitude>{lon:.6f}</longitude>
      <latitude>{lat:.6f}</latitude>
      <altitude>0</altitude>
      <heading>0</heading>
      <tilt>0</tilt>
      <range>2500</range>
      <altitudeMode>clampToGround</altitudeMode>
    </LookAt>
    <styleUrl>#station_default</styleUrl>
    <Point>
      <coordinates>{lon:.6f},{lat:.6f},0</coordinates>
    </Point>
  </Placemark>
"""
    return placemark, True


def main():
    lines = load_all_lines()
    geocode_cache = load_json(GEOCODE_CACHE_PATH, {})
    overpass_cache = load_json(OVERPASS_CACHE_PATH, {})
    crossings = load_json(CROSSINGS_PATH, {"crossings": []})
    crossing_keys = crossing_key_set(crossings)

    styles = []
    line_placemarks = []
    all_fallbacks = []

    for line in lines:
        color = rgb_to_kml_color(line["color_rgb"])
        styles.append(f"""  <Style id="line_{line['id']}">
    <LineStyle><color>{color}</color><width>4</width></LineStyle>
  </Style>""")
        full_path, fallbacks = build_line_path(line["stops"], geocode_cache, overpass_cache, crossing_keys)
        if fallbacks:
            for ka, kb, kind in fallbacks:
                all_fallbacks.append((line["id"], ka, kb, kind))
        if not full_path:
            continue
        simplified = douglas_peucker(full_path, tolerance_m=SIMPLIFY_TOLERANCE_M)
        line_placemarks.append(kml_placemark_line(line, simplified, color))

    stations = build_station_registry(lines, geocode_cache)
    station_placemarks = []
    missing_geocode = []
    for key in sorted(stations.keys(), key=sort_key):
        pm, ok = kml_placemark_station(key, stations[key], geocode_cache)
        if ok:
            station_placemarks.append(pm)
        else:
            missing_geocode.append(key)

    style_default_icon = """  <Style id="station_default">
    <IconStyle>
      <scale>1.0</scale>
    </IconStyle>
  </Style>"""

    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>IR-Netz 2030 - Globales Maglev-Netzwerk</name>
{style_default_icon}
{os.linesep.join(styles)}
{''.join(line_placemarks)}{''.join(station_placemarks)}</Document>
</kml>
"""

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f"KML geschrieben: {OUTPUT_PATH}")
    print(f"{len(line_placemarks)} Linien, {len(station_placemarks)} Stationen.")
    if missing_geocode:
        print(f"WARNUNG: {len(missing_geocode)} Stationen ohne Geokoordinaten uebersprungen: {missing_geocode[:20]}")
    if all_fallbacks:
        print(f"WARNUNG: {len(all_fallbacks)} Streckenabschnitte nutzen noch eine Geraden-Fallback-Linie (Overpass-Routing steht noch aus):")
        for line_id, ka, kb, kind in all_fallbacks[:40]:
            print(f"    [{line_id}] {ka} -> {kb} ({kind})")
        if len(all_fallbacks) > 40:
            print(f"    ... und {len(all_fallbacks) - 40} weitere.")


if __name__ == "__main__":
    main()
