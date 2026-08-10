#!/usr/bin/env python3
"""
Gemeinsame Bausteine fuer alle Phasen: KML-Parsing, Halte-Dedup, Snapping.

Liegt bewusst in einem eigenen Modul, damit Phase 2 (Netzgraph) und Phase 4
(Buendelung) exakt dieselbe Zuordnung Halt -> Liniensegment berechnen und
nicht auseinanderdriften.
"""
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

from shapely.geometry import Point

KML_NS = "{http://www.opengis.net/kml/2.2}"

# Liniencodes tauchen in den Halte-Beschreibungen als <b>RE5</b> o.ae. auf.
LINE_CODE_RE = re.compile(r'<b>([A-Za-z0-9]+)</b>')


def tag(elem):
    """Namespace-Praefix vom Tag-Namen entfernen."""
    return elem.tag.replace(KML_NS, "")


def kml_color_to_hex(kml_color):
    """KML-Farben sind aabbggrr (Alpha, Blau, Gruen, Rot) -> #rrggbb umwandeln."""
    if not kml_color or len(kml_color) != 8:
        return "#000000"
    rr, gg, bb = kml_color[6:8], kml_color[4:6], kml_color[2:4]
    return f"#{rr}{gg}{bb}"


def haversine_m(lon1, lat1, lon2, lat2):
    """Grosskreis-Distanz in Metern (Kugelnaeherung, ausreichend fuer die 150-m-Schwelle)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def normalize_core(name):
    """Namenskern ohne Klammerzusaetze/Bahnhofs-Suffixe, fuer den Aehnlichkeitsvergleich beim Dedup."""
    n = re.sub(r"\([^)]*\)", "", name)
    n = re.sub(r"\b(Hauptbahnhof|Hbf|Bahnhof|Bf|Haltepunkt|Hp)\b", "", n, flags=re.I)
    n = re.sub(r"[^a-zA-ZäöüÄÖÜß]+", "", n).lower()
    return n


def names_look_related(name_a, name_b):
    """True, wenn zwei Haltenamen plausibel denselben Bahnhof meinen."""
    ca, cb = normalize_core(name_a), normalize_core(name_b)
    if not ca or not cb:
        return False
    return ca == cb or ca in cb or cb in ca


def slugify(name):
    """Stabile, ASCII-sichere ID aus einem Haltenamen."""
    repl = {
        "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
        "é": "e", "è": "e", "ą": "a", "ę": "e", "ł": "l", "ń": "n", "ż": "z", "ź": "z",
        "ć": "c", "ś": "s", "ř": "r", "ě": "e", "ů": "u", "ň": "n", "š": "s", "č": "c",
        "ý": "y", "ø": "oe", "Ø": "Oe", "å": "aa", "Å": "Aa", "æ": "ae", "Æ": "Ae",
    }
    s = "".join(repl.get(ch, ch) for ch in name)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "halt"


def parse_kml(input_path):
    """
    KML einlesen.

    Rueckgabe: (lines, stops_raw)
      lines:     Liste von {line_id, code, name, color, segments} wobei segments
                 eine Liste von Polylinien ist (je Polylinie Liste von (lon, lat)).
                 Mehrere Segmente = verzweigte Linie (Fluegelzug).
      stops_raw: Liste von {name, lon, lat, description}
    """
    tree = ET.parse(input_path)
    root = tree.getroot()
    document = root.find(f"{KML_NS}Document")
    if document is None:
        document = root

    styles = {}
    for style_el in document.iter(f"{KML_NS}Style"):
        sid = style_el.get("id")
        line_style = style_el.find(f"{KML_NS}LineStyle")
        if line_style is not None:
            color_el = line_style.find(f"{KML_NS}color")
            styles[sid] = kml_color_to_hex(color_el.text if color_el is not None else None)

    lines = []
    stops_raw = []

    for placemark in document.findall(f"{KML_NS}Placemark"):
        name_el = placemark.find(f"{KML_NS}name")
        name = name_el.text.strip() if name_el is not None and name_el.text else None
        style_url_el = placemark.find(f"{KML_NS}styleUrl")
        style_url = style_url_el.text.lstrip("#") if style_url_el is not None and style_url_el.text else None
        desc_el = placemark.find(f"{KML_NS}description")
        desc = desc_el.text if desc_el is not None and desc_el.text else ""

        direct_tags = [tag(c) for c in placemark]

        if "LineString" in direct_tags or "MultiGeometry" in direct_tags:
            segments = []
            for ls in placemark.iter(f"{KML_NS}LineString"):
                coords_el = ls.find(f"{KML_NS}coordinates")
                pts = []
                for tok in coords_el.text.split():
                    lon, lat = map(float, tok.split(",")[:2])
                    pts.append((lon, lat))
                segments.append(pts)
            code_match = re.match(r'^(RB\d+|RE\d+X?b?|S\d+)\b', name)
            code = code_match.group(1) if code_match else name.split()[0]
            lines.append({
                "line_id": style_url,   # eindeutig, auch bei doppelt vergebenen Codes (zwei RE17)
                "code": code,
                "name": name,
                "color": styles.get(style_url, "#000000"),
                "segments": segments,
            })
        elif "Point" in direct_tags:
            pt_el = placemark.find(f"{KML_NS}Point/{KML_NS}coordinates")
            lon, lat = map(float, pt_el.text.split(",")[:2])
            stops_raw.append({"name": name, "lon": lon, "lat": lat, "description": desc})

    return lines, stops_raw


def dedupe_stops(stops_raw, threshold_m=150.0):
    """
    Halte zusammenfuehren, die unter threshold_m auseinanderliegen UND deren Namen
    plausibel denselben Bahnhof meinen.

    Nah beieinanderliegende Halte mit voellig unverwandten Namen werden NICHT
    zusammengefuehrt, sondern als Verdacht auf einen Koordinatenfehler gemeldet.

    Rueckgabe: (merged_stops, id_by_raw_index, merges_found, suspicious_pairs)
    """
    n = len(stops_raw)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    # Grid-Bucketing statt O(n^2)-Vergleich aller Paare
    cell_deg = 0.02
    buckets = defaultdict(list)
    for i, s in enumerate(stops_raw):
        buckets[(round(s["lon"] / cell_deg), round(s["lat"] / cell_deg))].append(i)

    merges_found = []
    suspicious_pairs = []
    for i, s in enumerate(stops_raw):
        cx, cy = round(s["lon"] / cell_deg), round(s["lat"] / cell_deg)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in buckets.get((cx + dx, cy + dy), []):
                    if j <= i:
                        continue
                    d = haversine_m(s["lon"], s["lat"], stops_raw[j]["lon"], stops_raw[j]["lat"])
                    if d >= threshold_m:
                        continue
                    same_name = stops_raw[i]["name"] == stops_raw[j]["name"]
                    if same_name or names_look_related(stops_raw[i]["name"], stops_raw[j]["name"]):
                        union(i, j)
                        if not same_name:
                            merges_found.append((stops_raw[i]["name"], stops_raw[j]["name"], round(d, 1)))
                    else:
                        suspicious_pairs.append((stops_raw[i]["name"], stops_raw[j]["name"], round(d, 1)))

    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    merged_stops = []
    id_by_raw_index = {}
    for group in groups.values():
        members = [stops_raw[i] for i in group]
        primary = min(members, key=lambda m: len(m["name"]))
        merged_stops.append({
            "stop_id": slugify(primary["name"]),
            "name": primary["name"],
            "alt_names": sorted({m["name"] for m in members if m["name"] != primary["name"]}),
            "lon": sum(m["lon"] for m in members) / len(members),
            "lat": sum(m["lat"] for m in members) / len(members),
            "description_raw": primary["description"],
        })
        for i in group:
            id_by_raw_index[i] = merged_stops[-1]["stop_id"]

    # Slug-Kollisionen zwischen verschiedenen Halten aufloesen
    seen = {}
    for s in merged_stops:
        base = s["stop_id"]
        if base in seen:
            seen[base] += 1
            s["stop_id"] = f"{base}_{seen[base]}"
        else:
            seen[base] = 0

    return merged_stops, id_by_raw_index, merges_found, suspicious_pairs


# Uebliche Kuerzel der Deutschen Bahn fuer Stadtteilbahnhoefe. Bewusst
# vorgegeben statt automatisch abgeleitet, weil sich Berlin/Bochum und
# Dortmund/Duesseldorf sonst um denselben Anfangsbuchstaben streiten.
STADT_KUERZEL = {
    "Berlin": "B", "Bochum": "BO", "Bremen": "HB", "Dortmund": "DO",
    "Duisburg": "DU", "Düsseldorf": "D", "Essen": "E", "Frankfurt": "F",
    "Gelsenkirchen": "GE", "Hagen": "HA", "Hamburg": "HH", "Hannover": "H",
    "Köln": "K", "Leipzig": "L", "Mülheim": "MH", "München": "M",
    "Münster": "MS", "Nürnberg": "N", "Stuttgart": "S", "Wuppertal": "W",
}

# "Bad Oldesloe" und "Bad Kleinen" sind verschiedene Staedte, kein gemeinsamer
# Stadtname - solche Praefixe duerfen nicht als Stadt durchgehen.
KEINE_STADT = {"Bad", "Sankt", "St."}

MIN_HALTE_FUER_KUERZEL = 3


def anzeigenamen(namen):
    """
    Kartenbeschriftung je Haltename bestimmen.

    Zwei Kuerzungen, beide von Verkehrskarten uebernommen:
    - "Hauptbahnhof" wird immer zu "Hbf".
    - Stadtteilbahnhoefe grosser Staedte bekommen das Stadtkuerzel:
      "Duesseldorf-Bilk" -> "D-Bilk", "Berlin Suedkreuz" -> "B-Suedkreuz".
      Das spart im Ruhrgebiet und um Duesseldorf herum erheblich Platz.

    Nicht gekuerzt werden der Hauptbahnhof selbst (dort steht der Stadtname
    ausgeschrieben) und Namen, deren Zusatz in Klammern steht - "Frankfurt
    (Oder)" und "Essen (Oldb)" sind eigene Staedte, keine Stadtteile.
    """
    import re as _re
    from collections import Counter as _Counter

    def stadt_und_rest(name):
        m = _re.match(r"^([^-\s]+)[-\s]+(.+)$", name)
        if not m:
            return None, None
        return m.group(1), m.group(2)

    zaehler = _Counter()
    for name in namen:
        stadt, rest = stadt_und_rest(name)
        if stadt and stadt not in KEINE_STADT and not rest.startswith("("):
            zaehler[stadt] += 1

    ergebnis = {}
    for name in namen:
        kurz = name.replace("Hauptbahnhof", "Hbf").replace("hauptbahnhof", "hbf")
        stadt, rest = stadt_und_rest(name)
        ist_hbf = kurz.endswith("Hbf")
        if (stadt and not ist_hbf and stadt in STADT_KUERZEL
                and stadt not in KEINE_STADT
                and not rest.startswith("(")
                and zaehler[stadt] >= MIN_HALTE_FUER_KUERZEL):
            kurz = f"{STADT_KUERZEL[stadt]}-{rest}"
        ergebnis[name] = kurz
    return ergebnis


def assign_stops_to_segments(segments_proj, stops_xy, tie_tolerance_m):
    """
    Ordnet Halte den Segmenten einer Linie zu und bestimmt ihre Position entlang
    des Segments (Bogenlaenge).

    Ein Halt kann bewusst MEHREREN Segmenten zugeordnet werden, wenn er von
    beiden praktisch gleich weit entfernt ist (tie_tolerance_m). Das ist noetig,
    weil sich bei Fluegelzuegen zwei Aeste an genau einem Bahnhof treffen und
    dieser Bahnhof zu beiden Aesten gehoert.

    segments_proj: Liste von shapely-LineStrings (projiziert, metrisch)
    stops_xy:      Liste von (stop_id, x, y)
    Rueckgabe: ({seg_idx: [(arclen, stop_id), ...] aufsteigend}, {stop_id: min_dist})
    """
    result = defaultdict(list)
    min_dist_by_stop = {}

    for stop_id, x, y in stops_xy:
        p = Point(x, y)
        entries = []
        for seg_idx, seg in enumerate(segments_proj):
            if seg is None:
                continue
            entries.append((seg_idx, seg.distance(p), seg.project(p)))
        if not entries:
            continue
        global_min = min(d for _, d, _ in entries)
        min_dist_by_stop[stop_id] = global_min
        for seg_idx, d, arclen in entries:
            if d <= global_min + tie_tolerance_m:
                result[seg_idx].append((arclen, stop_id))

    for seg_idx in result:
        result[seg_idx].sort()

    return result, min_dist_by_stop
