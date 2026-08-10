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
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform as shapely_transform

from kml_common import (
    LINE_CODE_RE,
    assign_stops_to_segments,
    dedupe_stops,
    haversine_m,
    parse_kml,
)

INPUT_PATH = Path("data/input/RENetz_2030_v3.kml")
OUTPUT_PATH = Path("data/02_graph.json")

DEDUP_THRESHOLD_M = 150.0          # Halte unter diesem Abstand gelten als derselbe Bahnhof
SNAP_WARN_THRESHOLD_M = 400.0      # ab hier Warnung: Halt liegt ungewoehnlich weit von seiner Linie
SEGMENT_TIE_TOLERANCE_M = 50.0     # mehrere Segmente gelten als "gleich nah", wenn sie sich um weniger als das unterscheiden
ENDPOINT_SNAP_TOLERANCE_M = 60.0   # Halt gilt als der Segment-Endpunkt selbst, wenn er naeher als das dran liegt
UMWEG_FAKTOR = 2.5                 # ab diesem Verhaeltnis Weg/Luftlinie gilt ein Halt als verdaechtig



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
    lines_raw, stops_raw = parse_kml(INPUT_PATH)

    print(f"Eingelesen: {len(lines_raw)} Linien, {len(stops_raw)} Halte-Placemarks (roh)")

    # Halte deduplizieren
    stops, id_by_raw_index, merges_found, suspicious_pairs = dedupe_stops(stops_raw, DEDUP_THRESHOLD_M)
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

        # Halte den Segmenten dieser Linie zuordnen (gemeinsame Logik mit Phase 4,
        # damit Graph und spaetere Buendelgeometrie garantiert dieselbe Zuordnung sehen)
        stops_xy = [(s["stop_id"], *to_metric(s["lon"], s["lat"])) for s in ln["candidate_stops"]]
        assigned, min_dist_by_stop = assign_stops_to_segments(
            ln["segments_metric"], stops_xy, SEGMENT_TIE_TOLERANCE_M
        )
        for s in ln["candidate_stops"]:
            d = min_dist_by_stop.get(s["stop_id"])
            if d is not None and d > SNAP_WARN_THRESHOLD_M:
                snap_warnings.append((ln["name"], s["name"], round(d, 1)))

        stop_lookup = {s["stop_id"]: s for s in ln["candidate_stops"]}
        stops_per_segment = {
            seg_idx: [(arclen, stop_lookup[sid]) for arclen, sid in entries]
            for seg_idx, entries in assigned.items()
        }

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

    # --- Verdacht auf fehlplatzierte Halte ----------------------------------
    # Ein Halt an der falschen Stelle faellt dadurch auf, dass die Linie einen
    # grossen Umweg machen muss: Der Weg ueber ihn ist viel laenger als die
    # Luftlinie zwischen seinen beiden Nachbarhalten. So flog "Essen-Horst"
    # auf, das in der Quell-KML 6 km westlich seiner echten Lage stand.
    umwege = []
    for ln in lines_raw:
        for seq in line_sequences[ln["line_id"]]:
            for vorher, halt, nachher in zip(seq, seq[1:], seq[2:]):
                a, b, c = stop_by_id[vorher], stop_by_id[halt], stop_by_id[nachher]
                direkt = haversine_m(a["lon"], a["lat"], c["lon"], c["lat"])
                ueber = (haversine_m(a["lon"], a["lat"], b["lon"], b["lat"])
                         + haversine_m(b["lon"], b["lat"], c["lon"], c["lat"]))
                if direkt > 500 and ueber > UMWEG_FAKTOR * direkt and ueber - direkt > 4000:
                    umwege.append((ln["code"], b["name"], a["name"], c["name"],
                                   ueber / 1000, direkt / 1000))
    umwege.sort(key=lambda u: -(u[4] - u[5]))
    if umwege:
        print(f"\nVERDACHT AUF FEHLPLATZIERTE HALTE ({len(umwege)}): Der Weg ueber diesen "
              f"Halt ist deutlich laenger als die Luftlinie seiner Nachbarn:")
        gesehen = set()
        for code, halt, vor, nach, ueber, direkt in umwege:
            if halt in gesehen:
                continue
            gesehen.add(halt)
            print(f"  {halt}: {code} faehrt {vor} -> {halt} -> {nach} "
                  f"= {ueber:.1f} km statt {direkt:.1f} km Luftlinie")

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
