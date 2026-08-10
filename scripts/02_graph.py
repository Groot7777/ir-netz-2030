#!/usr/bin/env python3
"""
Phase 2 - Netzgraph.

Baut aus den KML-Rohdaten einen sauberen Graphen:
- Halte deduplizieren (Haversine < 150 m => derselbe Bahnhof)
- Jede Linie wird zu (einer oder mehreren, bei Verzweigung) geordneten Halte-Sequenzen
- Kanten = Halt-zu-Halt-Verbindungen mit Liste der befahrenden Linien

Kernidee fuer die Zuordnung Halt -> Linie -> Position:
Die Point-Placemarks (Halte) liegen NICHT exakt auf den LineString-Stuetzpunkten
(siehe Phase 1). Wir ermitteln daher pro Halt anhand der <description> (enthaelt
"<b>REXX</b> Linienname ...") welche Linien dort verkehren (Ground Truth), snappen
den Halt anschliessend auf die naechste Position entlang der passenden Linien-
Geometrie (lineares Referenzieren) und sortieren die Halte pro Liniensegment nach
dieser Position entlang der Strecke.
"""
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform as shapely_transform

KML_NS = "{http://www.opengis.net/kml/2.2}"
INPUT_PATH = Path("data/input/RENetz_2030_v3.kml")
OUTPUT_PATH = Path("data/02_graph.json")

DEDUP_THRESHOLD_M = 150.0          # Halte unter diesem Abstand gelten als derselbe Bahnhof
SNAP_WARN_THRESHOLD_M = 400.0      # ab hier Warnung: Halt liegt ungewoehnlich weit von seiner Linie
SEGMENT_TIE_TOLERANCE_M = 50.0     # mehrere Segmente gelten als "gleich nah", wenn sie sich um weniger als das unterscheiden
ENDPOINT_SNAP_TOLERANCE_M = 60.0   # Halt gilt als der Segment-Endpunkt selbst, wenn er naeher als das dran liegt

LINE_CODE_RE = re.compile(r'<b>([A-Za-z0-9]+)</b>')


def tag(elem):
    return elem.tag.replace(KML_NS, "")


def kml_color_to_hex(kml_color):
    if not kml_color or len(kml_color) != 8:
        return "#000000"
    rr, gg, bb = kml_color[6:8], kml_color[4:6], kml_color[2:4]
    return f"#{rr}{gg}{bb}"


def haversine_m(lon1, lat1, lon2, lat2):
    """Praezise Grossskreis-Distanz in Metern (WGS84-Kugelnaeherung, ausreichend fuer 150m-Schwelle)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def normalize_core(name):
    """Namenskern ohne Klammerzusaetze/Bahnhofs-Suffixe, fuer den Aehnlichkeitsvergleich beim Dedup."""
    n = re.sub(r"\([^)]*\)", "", name)  # Klammerinhalte weg, z.B. "(Ruhr)"
    n = re.sub(r"\b(Hauptbahnhof|Hbf|Bahnhof|Bf|Haltepunkt|Hp)\b", "", n, flags=re.I)
    n = re.sub(r"[^a-zA-ZäöüÄÖÜß]+", "", n).lower()
    return n


def names_look_related(name_a, name_b):
    ca, cb = normalize_core(name_a), normalize_core(name_b)
    if not ca or not cb:
        return False
    return ca == cb or ca in cb or cb in ca


def slugify(name):
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


# --- KML einlesen -----------------------------------------------------------

def parse_kml():
    tree = ET.parse(INPUT_PATH)
    root = tree.getroot()
    document = root.find(f"{KML_NS}Document")

    styles = {}
    for style_el in document.iter(f"{KML_NS}Style"):
        sid = style_el.get("id")
        line_style = style_el.find(f"{KML_NS}LineStyle")
        if line_style is not None:
            color_el = line_style.find(f"{KML_NS}color")
            styles[sid] = kml_color_to_hex(color_el.text if color_el is not None else None)

    lines = []       # Rohdaten der Linien-Placemarks
    stops_raw = []    # Rohdaten der Point-Placemarks

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
                "line_id": style_url,           # eindeutig (styleUrl), auch bei doppelten Codes wie RE17
                "code": code,                   # Liniennummer, ggf. mehrfach vergeben (siehe Phase 1)
                "name": name,
                "color": styles.get(style_url, "#000000"),
                "segments": segments,
            })
        elif "Point" in direct_tags:
            pt_el = placemark.find(f"{KML_NS}Point/{KML_NS}coordinates")
            lon, lat = map(float, pt_el.text.split(",")[:2])
            stops_raw.append({"name": name, "lon": lon, "lat": lat, "description": desc})

    return lines, stops_raw


# --- Halte deduplizieren (Haversine < 150m) ---------------------------------

def dedupe_stops(stops_raw):
    """Union-Find ueber alle Halte-Paare unter DEDUP_THRESHOLD_M, unabhaengig vom Namen."""
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

    # Einfaches Grid-Bucketing statt O(n^2), reicht bei 466 Halten locker,
    # aber sauberer/robuster fuer groessere Netze
    cell_deg = 0.02  # ~1.5-2 km je nach Breite, grob genug fuer 150m-Nachbarschaftssuche
    buckets = defaultdict(list)
    for i, s in enumerate(stops_raw):
        cell = (round(s["lon"] / cell_deg), round(s["lat"] / cell_deg))
        buckets[cell].append(i)

    merges_found = []
    suspicious_pairs = []  # nah beieinander, aber Namen sehen NICHT verwandt aus -> vermutlich Datenfehler, nicht mergen
    for i, s in enumerate(stops_raw):
        cx, cy = round(s["lon"] / cell_deg), round(s["lat"] / cell_deg)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in buckets.get((cx + dx, cy + dy), []):
                    if j <= i:
                        continue
                    d = haversine_m(s["lon"], s["lat"], stops_raw[j]["lon"], stops_raw[j]["lat"])
                    if d >= DEDUP_THRESHOLD_M:
                        continue
                    same_name = stops_raw[i]["name"] == stops_raw[j]["name"]
                    related = same_name or names_look_related(stops_raw[i]["name"], stops_raw[j]["name"])
                    if related:
                        union(i, j)
                        if not same_name:
                            merges_found.append((stops_raw[i]["name"], stops_raw[j]["name"], round(d, 1)))
                    else:
                        # Namen unverwandt trotz < 150m Abstand: vermutlich fehlerhafte Koordinate
                        # in der Quell-KML, NICHT automatisch zusammenfuehren.
                        suspicious_pairs.append((stops_raw[i]["name"], stops_raw[j]["name"], round(d, 1)))

    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    merged_stops = []
    id_by_raw_index = {}
    for group in groups.values():
        members = [stops_raw[i] for i in group]
        # repraesentativen Namen waehlen: kuerzester Name (meist der "kanonische")
        primary = min(members, key=lambda m: len(m["name"]))
        lon = sum(m["lon"] for m in members) / len(members)
        lat = sum(m["lat"] for m in members) / len(members)
        stop_id = slugify(primary["name"])
        merged_stops.append({
            "stop_id": stop_id,
            "name": primary["name"],
            "alt_names": sorted({m["name"] for m in members if m["name"] != primary["name"]}),
            "lon": lon,
            "lat": lat,
            "description_raw": primary["description"],
        })
        for i in group:
            id_by_raw_index[i] = stop_id

    # stop_id Kollisionen (verschiedene, nicht zusammengefuehrte Halte mit gleichem Slug) aufloesen
    seen = {}
    for s in merged_stops:
        base = s["stop_id"]
        if base in seen:
            seen[base] += 1
            s["stop_id"] = f"{base}_{seen[base]}"
        else:
            seen[base] = 0

    return merged_stops, id_by_raw_index, merges_found, suspicious_pairs


# --- Liniencode -> Linien-Placemark(s) Zuordnung (RE17-Kollision beachten) --

def match_line_code_to_stop(code, name_hint, candidates, stop_lon, stop_lat, metric_transform):
    """Bei mehrdeutigem Code (z.B. RE17) die geometrisch naechstgelegene Linie waehlen."""
    same_code = [ln for ln in candidates if ln["code"] == code]
    if not same_code:
        return None
    if len(same_code) == 1:
        return same_code[0]
    # mehrere Linien mit gleichem Code -> per Distanz zum Halt disambiguieren
    p = Point(*metric_transform(stop_lon, stop_lat))
    best, best_d = None, float("inf")
    for ln in same_code:
        for seg in ln["segments_metric"]:
            d = seg.distance(p)
            if d < best_d:
                best_d, best = d, ln
    return best


# --- Hauptprogramm -----------------------------------------------------------

def main():
    lines_raw, stops_raw = parse_kml()

    print(f"Eingelesen: {len(lines_raw)} Linien, {len(stops_raw)} Halte-Placemarks (roh)")

    # Halte deduplizieren
    stops, id_by_raw_index, merges_found, suspicious_pairs = dedupe_stops(stops_raw)
    print(f"Nach Dedup (<{DEDUP_THRESHOLD_M:.0f} m): {len(stops)} eindeutige Halte")
    if merges_found:
        print(f"  Zusammengefuehrte Halte mit unterschiedlichem, aber verwandtem Namen ({len(merges_found)}):")
        for a, b, d in merges_found:
            print(f"    '{a}' <-> '{b}'  ({d} m)")
    else:
        print("  Keine namensverwandten Halte innerhalb 150 m gefunden.")
    if suspicious_pairs:
        print(f"  VERDACHT AUF DATENFEHLER ({len(suspicious_pairs)}): Halte < 150m auseinander, aber unverwandte Namen -> NICHT automatisch zusammengefuehrt:")
        for a, b, d in suspicious_pairs:
            print(f"    '{a}' <-> '{b}'  ({d} m)  -- bitte Koordinaten in der Quell-KML pruefen")

    stop_by_id = {s["stop_id"]: s for s in stops}

    # Metrische Projektion fuer lineares Referenzieren: Azimuthal-Equidistant um den Netz-Schwerpunkt
    center_lon = sum(s["lon"] for s in stops) / len(stops)
    center_lat = sum(s["lat"] for s in stops) / len(stops)
    aeqd_crs = f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} +units=m +ellps=WGS84"
    to_metric = Transformer.from_crs("EPSG:4326", aeqd_crs, always_xy=True).transform
    from_metric = Transformer.from_crs(aeqd_crs, "EPSG:4326", always_xy=True).transform

    for ln in lines_raw:
        ln["segments_metric"] = [
            shapely_transform(to_metric, LineString(seg)) if len(seg) >= 2 else None
            for seg in ln["segments"]
        ]

    # Fuer jeden Halt: bedienende Linien aus der Beschreibung extrahieren
    known_codes = {ln["code"] for ln in lines_raw}
    for s in stops:
        codes_in_desc = []
        for code in LINE_CODE_RE.findall(s["description_raw"] or ""):
            if code in known_codes and code not in codes_in_desc:
                codes_in_desc.append(code)
        s["_codes_in_description"] = codes_in_desc

    # Pro Linie: Liste der Halte sammeln, die laut Beschreibung zu ihr gehoeren
    # (bei doppelt vergebenen Codes wie RE17 anhand der Naehe disambiguiert)
    for ln in lines_raw:
        ln["candidate_stops"] = []
    for s in stops:
        for code in s["_codes_in_description"]:
            candidates = [ln for ln in lines_raw if ln["code"] == code]
            best_line = match_line_code_to_stop(code, s["name"], candidates, s["lon"], s["lat"], to_metric)
            if best_line is not None:
                best_line["candidate_stops"].append(s)

    # --- Segment-Topologie pro Linie aufbauen -------------------------------
    # Mehrsegmentige Linien (Fluegelzuege / Astverzweigungen) treffen sich an
    # Punkten, die oft KEIN benannter Halt sind, sondern reine Gleisverzweigungen.
    # Diese werden als synthetische Verzweigungsknoten (is_junction=True) in den
    # Graphen aufgenommen, damit die Aeste an der richtigen Stelle zusammenlaufen,
    # aber sie zaehlen NICHT als "Halt" in der Statistik und werden in Phase 5
    # nicht als Bahnhof gezeichnet.
    junction_nodes = {}   # node_id -> {"lon":.., "lat":.., "line_id":.., "is_junction": True}
    snap_warnings = []

    def get_or_create_junction(line_id, lon, lat, registry):
        key = (line_id, round(lon, 6), round(lat, 6))
        if key in registry:
            return registry[key]
        node_id = f"jct_{line_id}_{sum(1 for k in registry if k[0] == line_id)}"
        registry[key] = node_id
        junction_nodes[node_id] = {"lon": lon, "lat": lat, "line_id": line_id, "is_junction": True}
        return node_id

    for ln in lines_raw:
        registry = {}
        seq_list = []

        # Fuer jeden Kandidaten-Halt einmal die Distanz zu ALLEN Segmenten dieser Linie
        # berechnen, damit wir ihn dem/den wirklich naechstgelegenen Segment(en) zuordnen
        # koennen (statt pro Segment isoliert zu urteilen).
        per_stop_seg_dists = {}  # stop_id -> Liste von (seg_idx, dist, arclen)
        for s in ln["candidate_stops"]:
            p = Point(*to_metric(s["lon"], s["lat"]))
            entries = []
            for seg_idx, seg in enumerate(ln["segments_metric"]):
                if seg is None:
                    continue
                entries.append((seg_idx, seg.distance(p), seg.project(p)))
            per_stop_seg_dists[s["stop_id"]] = entries
            global_min = min(d for _, d, _ in entries)
            if global_min > SNAP_WARN_THRESHOLD_M:
                snap_warnings.append((ln["name"], s["name"], round(global_min, 1)))

        stops_per_segment = defaultdict(list)  # seg_idx -> Liste von (arclen, stop)
        for s in ln["candidate_stops"]:
            entries = per_stop_seg_dists[s["stop_id"]]
            global_min = min(d for _, d, _ in entries)
            for seg_idx, d, arclen in entries:
                if d <= global_min + SEGMENT_TIE_TOLERANCE_M:
                    stops_per_segment[seg_idx].append((arclen, s))

        for seg_idx, seg in enumerate(ln["segments_metric"]):
            if seg is None:
                continue
            seg_len = seg.length
            on_this_segment = sorted(stops_per_segment.get(seg_idx, []), key=lambda t: t[0])

            start_lon, start_lat = ln["segments"][seg_idx][0]
            end_lon, end_lat = ln["segments"][seg_idx][-1]

            chain = []

            # Start des Segments: existierender Halt in der Naehe, oder Verzweigungsknoten
            if on_this_segment and on_this_segment[0][0] <= ENDPOINT_SNAP_TOLERANCE_M:
                pass  # der erste Halt in der Liste UEBERNIMMT die Startposition, kein Extra-Knoten
            else:
                chain.append(get_or_create_junction(ln["line_id"], start_lon, start_lat, registry))

            for arclen, s in on_this_segment:
                if not chain or chain[-1] != s["stop_id"]:
                    chain.append(s["stop_id"])

            if on_this_segment and (seg_len - on_this_segment[-1][0]) <= ENDPOINT_SNAP_TOLERANCE_M:
                pass  # letzter Halt uebernimmt die Endposition
            else:
                end_node = get_or_create_junction(ln["line_id"], end_lon, end_lat, registry)
                if not chain or chain[-1] != end_node:
                    chain.append(end_node)

            if len(chain) >= 2:
                seq_list.append(chain)

        ln["sequences_with_junctions"] = seq_list

    if snap_warnings:
        print(f"\nWarnung: {len(snap_warnings)} Halte liegen > {SNAP_WARN_THRESHOLD_M:.0f} m von jedem Segment ihrer Linie entfernt:")
        for line_name, stop_name, d in snap_warnings:
            print(f"  {line_name}: {stop_name} ({d} m)")

    # line_sequences (nur echte Halt-IDs, fuer Statistik/Bericht) + volle Sequenzen (inkl. Junctions, fuer Kanten)
    line_sequences = {ln["line_id"]: [
        [n for n in chain if n in stop_by_id] for chain in ln["sequences_with_junctions"]
    ] for ln in lines_raw}
    line_sequences = {lid: [seq for seq in seqs if len(seq) >= 2] for lid, seqs in line_sequences.items()}

    # Kanten aufbauen: Knoten-zu-Knoten (Halt oder Junction), mit Liste der befahrenden Linien
    edges = {}
    for ln in lines_raw:
        for chain in ln["sequences_with_junctions"]:
            for a, b in zip(chain, chain[1:]):
                key = tuple(sorted((a, b)))
                if key not in edges:
                    edges[key] = {"stop_a": key[0], "stop_b": key[1], "lines": []}
                if ln["line_id"] not in edges[key]["lines"]:
                    edges[key]["lines"].append(ln["line_id"])

    # Statistik: meistbefahrene Kanten (nur echte Halt-zu-Halt-Kanten, Verzweigungsknoten
    # sind reine Geometrie-Hilfskonstrukte und fuer diese Statistik nicht relevant)
    real_edges = [e for e in edges.values() if e["stop_a"] in stop_by_id and e["stop_b"] in stop_by_id]
    junction_edges = [e for e in edges.values() if e not in real_edges]
    top_edges = sorted(real_edges, key=lambda e: len(e["lines"]), reverse=True)[:10]

    # Statistik: Halte, die nur von einer einzigen Linie bedient werden
    stop_line_count = defaultdict(set)
    for ln in lines_raw:
        for seq in line_sequences[ln["line_id"]]:
            for sid in seq:
                stop_line_count[sid].add(ln["line_id"])
    single_line_stops = sorted(
        [stop_by_id[sid]["name"] for sid, lset in stop_line_count.items() if len(lset) == 1]
    )

    # unbediente Halte (kamen in keiner description-Linienliste vor bzw. konnten nicht gesnappt werden)
    served_stop_ids = set(stop_line_count.keys())
    unserved_stops = [s["name"] for s in stops if s["stop_id"] not in served_stop_ids]

    # --- Ausgabe zusammenbauen ---
    output = {
        "meta": {
            "dedup_threshold_m": DEDUP_THRESHOLD_M,
            "snap_warn_threshold_m": SNAP_WARN_THRESHOLD_M,
            "projection_for_snapping": aeqd_crs,
        },
        "stops": [
            {
                "stop_id": s["stop_id"],
                "name": s["name"],
                "alt_names": s["alt_names"],
                "lon": s["lon"],
                "lat": s["lat"],
                "n_lines": len(stop_line_count.get(s["stop_id"], [])),
            }
            for s in stops
        ],
        "lines": [
            {
                "line_id": ln["line_id"],
                "code": ln["code"],
                "name": ln["name"],
                "color": ln["color"],
                "n_segments": len(ln["segments"]),
                "sequences": line_sequences[ln["line_id"]],
            }
            for ln in lines_raw
        ],
        "junction_nodes": [
            {"node_id": nid, **info} for nid, info in junction_nodes.items()
        ],
        "edges": [
            {
                "stop_a": e["stop_a"], "stop_b": e["stop_b"], "lines": e["lines"], "n_lines": len(e["lines"]),
                "is_junction_edge": not (e["stop_a"] in stop_by_id and e["stop_b"] in stop_by_id),
            }
            for e in edges.values()
        ],
        "stats": {
            "n_stops": len(stops),
            "n_edges": len(edges),
            "n_real_edges": len(real_edges),
            "n_junction_edges": len(junction_edges),
            "n_junction_nodes": len(junction_nodes),
            "n_lines": len(lines_raw),
            "top_10_edges": [
                {
                    "stop_a": stop_by_id[e["stop_a"]]["name"],
                    "stop_b": stop_by_id[e["stop_b"]]["name"],
                    "n_lines": len(e["lines"]),
                    "lines": [next(l["name"] for l in lines_raw if l["line_id"] == lid) for lid in e["lines"]],
                }
                for e in top_edges
            ],
            "single_line_stops": single_line_stops,
            "n_single_line_stops": len(single_line_stops),
            "unserved_stops": unserved_stops,
            "n_unserved_stops": len(unserved_stops),
            "n_merges_found": len(merges_found),
            "merges_found": [{"a": a, "b": b, "dist_m": d} for a, b, d in merges_found],
            "n_snap_warnings": len(snap_warnings),
            "suspicious_coordinate_pairs": [
                {"a": a, "b": b, "dist_m": d} for a, b, d in suspicious_pairs
            ],
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Phase 2: Netzgraph ===")
    print(f"Halte: {len(stops)}")
    print(f"Kanten: {len(edges)} (davon {len(real_edges)} Halt-zu-Halt, {len(junction_edges)} an Verzweigungsknoten)")
    print(f"Verzweigungsknoten (synthetisch, keine Halte): {len(junction_nodes)}")
    print(f"Linien: {len(lines_raw)}")
    print(f"Unbediente Halte (kein Snap gefunden): {len(unserved_stops)}")
    if unserved_stops:
        print(f"  {unserved_stops}")
    print(f"Halte mit nur einer Linie: {len(single_line_stops)}")
    print("\nTop 10 meistbefahrene Kanten:")
    for e in output["stats"]["top_10_edges"]:
        print(f"  {e['stop_a']} <-> {e['stop_b']}: {e['n_lines']} Linien ({', '.join(e['lines'])})")
    print(f"\nBericht geschrieben nach {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
