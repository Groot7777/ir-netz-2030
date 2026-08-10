#!/usr/bin/env python3
"""
Phase 4 - Buendelung.

Wo mehrere Linien dieselbe Kante befahren, muessen sie als parallele Bahnen
nebeneinander laufen. Kernpunkte der Umsetzung:

1. GEMEINSAME KANTENGEOMETRIE. Fuer jede Kante wird EINE kanonische Polylinie
   gewaehlt (die detaillierteste der beteiligten Linien). Alle Linien des
   Buendels benutzen dieselbe Basisgeometrie - nur so laufen sie wirklich
   parallel. Wuerde jede Linie ihre eigene KML-Geometrie behalten, wuerden die
   Bahnen des Buendels sichtbar auseinanderdriften.

2. KANONISCHE RICHTUNG. Die Slots werden entlang einer festen Kantenrichtung
   (stop_a -> stop_b, alphabetisch sortiert) vergeben. Befaehrt eine Linie die
   Kante rueckwaerts, wird ihr Slot-Vorzeichen gespiegelt - dadurch liegen alle
   Linien physisch an derselben Stelle, unabhaengig von der Fahrtrichtung.

3. GLOBALE SLOT-REIHENFOLGE. Alle Linien werden einmal global sortiert
   (Liniennummer). Auf jeder Kante werden die dort verkehrenden Linien nach
   diesem globalen Rang angeordnet. Dadurch bleibt die Reihenfolge im Buendel
   ueber aufeinanderfolgende Kanten stabil; Slots verschieben sich nur dort,
   wo Linien dazukommen oder abzweigen.

4. WEICHE SLOT-UEBERGAENGE. Der Slot-Wert wird entlang des Wegs ueber ein
   Bogenlaengen-Fenster geglaettet. Wo eine Linie den Slot wechselt (Abzweig),
   entsteht so eine schraege Rampe statt eines Sprungs.

5. VEREINFACHEN VOR, GLAETTEN NACH dem Versatz (Douglas-Peucker bzw. Chaikin),
   damit das Buendel nicht ausfranst.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import substring, transform as shapely_transform

from kml_common import assign_stops_to_segments, parse_kml

INPUT_KML = Path("data/input/RENetz_2030_v3.kml")
GRAPH_PATH = Path("data/02_graph.json")
BASEMAP_PATH = Path("data/03_basemap.json")
OUTPUT_PATH = Path("data/04_bundled.json")

PROJECTED_CRS = "EPSG:3034"          # wie Phase 3: ETRS89 / LCC Europe

SVG_WIDTH = 3000.0                   # Breite der Zeichenflaeche in px
MARGIN_PX = 60.0                     # Rand um das Netz herum

LINE_WIDTH_PX = 4.0                  # Linienbreite bei Standardzoom
SLOT_SPACING_PX = 1.3 * LINE_WIDTH_PX  # Abstand zwischen zwei Bahnen im Buendel

SIMPLIFY_TOLERANCE_PX = 1.2          # Douglas-Peucker VOR dem Versatz
DENSIFY_MAX_SEG_PX = 5.0             # lange Segmente unterteilen, damit Rampen greifen koennen
SLOT_TRANSITION_PX = 20.0            # Obergrenze fuer die Laenge eines Slot-Wechsels
CHAIKIN_ITERATIONS = 1               # Glaettung NACH dem Versatz
MITER_LIMIT = 2.5                    # Begrenzung der Gehrung an spitzen Ecken

SEGMENT_TIE_TOLERANCE_M = 50.0       # identisch zu Phase 2
EDGE_DEVIATION_WARN_PX = 12.0        # ab hier: Linien nehmen auf derselben Kante spuerbar andere Wege


# --- Geometrie-Hilfsfunktionen ----------------------------------------------

def natural_sort_key(line):
    """
    Globale Sortierung der Linien: nach Praefix (RB/RE/S), dann Nummer, dann Suffix.
    line_id als Tiebreaker, weil es zwei verschiedene Linien namens RE17 gibt.
    """
    m = re.match(r'^([A-Za-z]+)(\d+)([A-Za-z]*)$', line["code"])
    if m:
        return (m.group(1), int(m.group(2)), m.group(3), line["line_id"])
    return (line["code"], 0, "", line["line_id"])


def dedup_consecutive(pts, eps=1e-6):
    """Aufeinanderfolgende identische Punkte entfernen (sonst sind Normalen nicht definiert)."""
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    return out


def left_normal(dx, dy):
    """Einheits-Normale links zur Richtung (dx, dy)."""
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return (0.0, 0.0)
    return (-dy / length, dx / length)


def cumulative_arclen(pts):
    """Kumulierte Bogenlaenge je Stuetzpunkt."""
    out = [0.0]
    for a, b in zip(pts, pts[1:]):
        out.append(out[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return out


def densify(pts, max_seg_px):
    """
    Lange Segmente unterteilen.

    Noetig, damit Slot-Rampen und die Glaettung ueberhaupt Stuetzpunkte haben,
    an denen sie wirken koennen - eine vereinfachte Kante besteht sonst
    stellenweise nur aus zwei Punkten.
    """
    if max_seg_px <= 0 or len(pts) < 2:
        return list(pts)
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        dist = math.hypot(b[0] - a[0], b[1] - a[1])
        n_sub = int(dist / max_seg_px)
        for k in range(1, n_sub + 1):
            t = k / (n_sub + 1)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        out.append(b)
    return out


def ramp_slots(pts, slots, max_transition_px):
    """
    Slot-Wechsel als begrenzte Rampe ausfuehren statt als Sprung.

    Wichtig: Die Rampenbreite wird an die Laenge der angrenzenden Abschnitte
    mit konstantem Slot angepasst (hoechstens 45 % davon). Eine feste
    Fensterbreite waere im dichten Netz (Ruhrgebiet: Halte teils nur wenige
    Pixel auseinander) laenger als ganze Kanten und wuerde die Slots ueber
    mehrere Kanten hinweg auf null verschmieren - das Buendel liefe dann
    wieder deckungsgleich statt parallel.
    """
    n = len(pts)
    if n < 2:
        return list(slots)
    s = cumulative_arclen(pts)

    # Abschnitte mit konstantem Slot bestimmen
    runs = []
    start = 0
    for i in range(1, n):
        if abs(slots[i] - slots[start]) > 1e-9:
            runs.append((start, i - 1, slots[start]))
            start = i
    runs.append((start, n - 1, slots[start]))
    if len(runs) == 1:
        return list(slots)

    out = list(slots)
    for k in range(len(runs) - 1):
        i0, i1, s0 = runs[k]
        j0, j1, s1 = runs[k + 1]
        boundary = 0.5 * (s[i1] + s[j0])
        len_before = s[i1] - s[i0]
        len_after = s[j1] - s[j0]
        # 45 % je Seite: benachbarte Rampen koennen sich dadurch nie ueberlappen
        w = min(max_transition_px / 2.0, len_before * 0.45, len_after * 0.45)
        if w <= 1e-6:
            continue
        for idx in range(i0, j1 + 1):
            t = (s[idx] - boundary) / w
            if t <= -1.0 or t >= 1.0:
                continue
            u = (t + 1.0) / 2.0
            out[idx] = s0 + (s1 - s0) * (u * u * (3.0 - 2.0 * u))  # Smoothstep
    return out


def offset_polyline(pts, offsets, miter_limit=MITER_LIMIT):
    """
    Polylinie senkrecht zur Laufrichtung versetzen, mit Gehrung an den Ecken.

    offsets: pro Stuetzpunkt der Versatz in px (positiv = links zur Laufrichtung).
    An Ecken wird der Versatz um 1/cos(halber Innenwinkel) verlaengert, damit
    aufeinanderfolgende Segmente ohne Luecke aneinanderstossen. Die Verlaengerung
    wird begrenzt, damit sehr spitze Ecken nicht ausreissen.
    """
    n = len(pts)
    if n < 2:
        return list(pts)
    out = []
    for i in range(n):
        if i == 0:
            nx, ny = left_normal(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
            scale = 1.0
        elif i == n - 1:
            nx, ny = left_normal(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            scale = 1.0
        else:
            n1 = left_normal(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            n2 = left_normal(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            mx, my = n1[0] + n2[0], n1[1] + n2[1]
            mlen = math.hypot(mx, my)
            if mlen < 1e-9:
                # 180-Grad-Kehre: Gehrung nicht definiert, einfache Normale nehmen
                nx, ny = n1
                scale = 1.0
            else:
                nx, ny = mx / mlen, my / mlen
                cos_half = max(nx * n1[0] + ny * n1[1], 1e-6)
                scale = min(1.0 / cos_half, miter_limit)
        out.append((pts[i][0] + nx * offsets[i] * scale,
                    pts[i][1] + ny * offsets[i] * scale))
    return out


def chaikin(pts, iterations=1):
    """Chaikin-Eckenschnitt zur Glaettung; Anfangs- und Endpunkt bleiben erhalten."""
    for _ in range(iterations):
        if len(pts) < 3:
            return pts
        new = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            new.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            new.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        new.append(pts[-1])
        pts = new
    return pts


# --- Hauptprogramm -----------------------------------------------------------

def main(debug_edge=None):
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    basemap = json.loads(BASEMAP_PATH.read_text(encoding="utf-8"))
    lines_raw, _stops_raw = parse_kml(INPUT_KML)

    stop_by_id = {s["stop_id"]: s for s in graph["stops"]}
    line_by_id = {ln["line_id"]: ln for ln in lines_raw}

    to_proj = Transformer.from_crs("EPSG:4326", PROJECTED_CRS, always_xy=True).transform

    # --- 1. Alles nach EPSG:3034 (Meter) projizieren -------------------------
    for ln in lines_raw:
        ln["segments_proj"] = [
            shapely_transform(to_proj, LineString(seg)) if len(seg) >= 2 else None
            for seg in ln["segments"]
        ]
    for s in graph["stops"]:
        s["px_m"], s["py_m"] = to_proj(s["lon"], s["lat"])

    # --- 2. Bildausschnitt bestimmen (Netz + Rand) ---------------------------
    all_x = [s["px_m"] for s in graph["stops"]]
    all_y = [s["py_m"] for s in graph["stops"]]
    for ln in lines_raw:
        for seg in ln["segments_proj"]:
            if seg is None:
                continue
            xs, ys = seg.xy
            all_x.extend(xs)
            all_y.extend(ys)

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    span_x, span_y = max_x - min_x, max_y - min_y
    scale = (SVG_WIDTH - 2 * MARGIN_PX) / span_x
    svg_height = span_y * scale + 2 * MARGIN_PX

    def to_px(x, y):
        """EPSG:3034-Meter -> SVG-Pixel (Y-Achse gespiegelt, SVG waechst nach unten)."""
        return (MARGIN_PX + (x - min_x) * scale,
                MARGIN_PX + (max_y - y) * scale)

    print(f"Zeichenflaeche: {SVG_WIDTH:.0f} x {svg_height:.0f} px")
    print(f"Massstab: {scale * 1000:.2f} px/km  ({1/scale:.0f} m/px)")
    print(f"Slot-Abstand: {SLOT_SPACING_PX:.1f} px = {SLOT_SPACING_PX / scale / 1000:.1f} km")

    # --- 3. Pro Linie: Halte auf Segmente snappen und Kanten herausschneiden --
    # edge_candidates[(a,b)] = Liste von (line_id, Polylinie in kanonischer Richtung, px)
    edge_candidates = defaultdict(list)
    line_branches = {}   # line_id -> Liste von Halte-Sequenzen (je Ast)

    for ln in lines_raw:
        graph_line = next(g for g in graph["lines"] if g["line_id"] == ln["line_id"])
        candidate_ids = {sid for seq in graph_line["sequences"] for sid in seq}
        stops_xy = [(sid, stop_by_id[sid]["px_m"], stop_by_id[sid]["py_m"]) for sid in candidate_ids]

        assigned, _ = assign_stops_to_segments(ln["segments_proj"], stops_xy, SEGMENT_TIE_TOLERANCE_M)

        branches = []
        for seg_idx in sorted(assigned.keys()):
            entries = assigned[seg_idx]
            if len(entries) < 2:
                continue
            seg = ln["segments_proj"][seg_idx]
            seq_ids = []
            for (arc_a, id_a), (arc_b, id_b) in zip(entries, entries[1:]):
                if not seq_ids:
                    seq_ids.append(id_a)
                seq_ids.append(id_b)
                if arc_b - arc_a < 1.0:      # zwei Halte auf praktisch demselben Punkt
                    continue
                piece = substring(seg, arc_a, arc_b)
                if piece.geom_type != "LineString" or len(piece.coords) < 2:
                    continue
                pts_px = [to_px(x, y) for x, y in piece.coords]
                key = tuple(sorted((id_a, id_b)))
                # in kanonische Richtung drehen (immer key[0] -> key[1])
                if (id_a, id_b) != key:
                    pts_px = pts_px[::-1]
                edge_candidates[key].append((ln["line_id"], pts_px))
            if len(seq_ids) >= 2:
                branches.append(seq_ids)
        line_branches[ln["line_id"]] = branches

    print(f"\nKanten mit Geometrie: {len(edge_candidates)}")

    # --- 4. Kanonische Geometrie je Kante waehlen und vereinfachen -----------
    edge_geom = {}
    deviations = []
    for key, candidates in edge_candidates.items():
        # detaillierteste Variante als Referenz
        best_line_id, best_pts = max(candidates, key=lambda c: len(c[1]))
        ref = LineString(dedup_consecutive(best_pts)) if len(dedup_consecutive(best_pts)) >= 2 else None
        if ref is None:
            continue
        for line_id, pts in candidates:
            pts_clean = dedup_consecutive(pts)
            if line_id == best_line_id or len(pts_clean) < 2:
                continue
            dev = ref.hausdorff_distance(LineString(pts_clean))
            if dev > EDGE_DEVIATION_WARN_PX:
                deviations.append((key, best_line_id, line_id, dev))
        simplified = ref.simplify(SIMPLIFY_TOLERANCE_PX, preserve_topology=False)
        # erst vereinfachen (entfernt GPS-Zittern), dann gleichmaessig unterteilen
        edge_geom[key] = densify(dedup_consecutive(list(simplified.coords)), DENSIFY_MAX_SEG_PX)

    if deviations:
        deviations.sort(key=lambda d: -d[3])
        print(f"\nHinweis: {len(deviations)} Kanten, auf denen Linien spuerbar verschiedene Wege nehmen")
        print(f"(> {EDGE_DEVIATION_WARN_PX:.0f} px Hausdorff-Abstand). Alle Linien nutzen dort die "
              f"detaillierteste Variante:")
        for key, ref_id, other_id, dev in deviations[:8]:
            name_a = stop_by_id[key[0]]["name"]
            name_b = stop_by_id[key[1]]["name"]
            print(f"  {name_a} <-> {name_b}: {other_id} weicht {dev:.0f} px von {ref_id} ab")

    # --- 5. Globale Linienreihenfolge und Slot-Vergabe je Kante --------------
    ordered_lines = sorted(lines_raw, key=natural_sort_key)
    rank_by_line = {ln["line_id"]: i for i, ln in enumerate(ordered_lines)}
    print(f"\nGlobale Linienreihenfolge: {', '.join(ln['code'] for ln in ordered_lines)}")

    edge_slots = {}   # (a,b) -> {line_id: slot}  (Slot in kanonischer Richtung)
    for key in edge_geom:
        lines_here = sorted(
            {lid for lid, _ in edge_candidates[key]},
            key=lambda lid: rank_by_line[lid],
        )
        n = len(lines_here)
        edge_slots[key] = {lid: (i - (n - 1) / 2.0) for i, lid in enumerate(lines_here)}

    max_bundle = max(len(v) for v in edge_slots.values())
    print(f"Groesstes Buendel: {max_bundle} Linien "
          f"({(max_bundle - 1) * SLOT_SPACING_PX + LINE_WIDTH_PX:.0f} px breit)")

    # --- 6. Pro Linie und Ast: Weg zusammensetzen, Slots glaetten, versetzen --
    output_lines = []
    slot_change_count = 0
    debug_points = []

    for ln in ordered_lines:
        branch_paths = []
        for seq in line_branches[ln["line_id"]]:
            pts = []
            slots = []
            vertex_edge = []   # Kante, zu der jeder Stuetzpunkt gehoert (fuer Diagnose)
            for id_a, id_b in zip(seq, seq[1:]):
                key = tuple(sorted((id_a, id_b)))
                if key not in edge_geom:
                    continue
                geom = edge_geom[key]
                forward = (id_a, id_b) == key
                seg_pts = geom if forward else geom[::-1]
                # Slot in kanonischer Richtung; bei Rueckwaertsfahrt spiegeln,
                # damit die Linie physisch an derselben Stelle des Buendels liegt
                slot = edge_slots[key][ln["line_id"]]
                slot_signed = slot if forward else -slot
                if pts and slots and abs(slots[-1] - slot_signed) > 1e-9:
                    slot_change_count += 1
                start = 1 if pts else 0   # gemeinsamen Knotenpunkt nicht doppelt anhaengen
                pts.extend(seg_pts[start:])
                slots.extend([slot_signed] * len(seg_pts[start:]))
                vertex_edge.extend([key] * len(seg_pts[start:]))

            if len(pts) < 2:
                continue

            # Duplikate entfernen, dabei Slots und Kantenzuordnung mitfuehren
            clean_pts, clean_slots, clean_edges = [], [], []
            for p, s, e in zip(pts, slots, vertex_edge):
                if not clean_pts or abs(p[0] - clean_pts[-1][0]) > 1e-6 or abs(p[1] - clean_pts[-1][1]) > 1e-6:
                    clean_pts.append(p)
                    clean_slots.append(s)
                    clean_edges.append(e)
            if len(clean_pts) < 2:
                continue

            smoothed = ramp_slots(clean_pts, clean_slots, SLOT_TRANSITION_PX)

            offsets = [s * SLOT_SPACING_PX for s in smoothed]
            offset_pts = offset_polyline(clean_pts, offsets)

            if debug_edge:
                idx = [i for i, e in enumerate(clean_edges) if e == debug_edge]
                if idx:
                    mid_i = idx[len(idx) // 2]
                    seg_len = sum(
                        math.hypot(clean_pts[b][0] - clean_pts[a][0], clean_pts[b][1] - clean_pts[a][1])
                        for a, b in zip(idx, idx[1:])
                    )
                    print(f"  [debug] {ln['code']:6s} Stuetzpunkte={len(idx):3d} Laenge={seg_len:6.1f}px "
                          f"Soll-Slot={clean_slots[mid_i]:+.1f} gerampt={smoothed[mid_i]:+.2f} "
                          f"Basispunkt=({clean_pts[mid_i][0]:.1f},{clean_pts[mid_i][1]:.1f}) "
                          f"versetzt=({offset_pts[mid_i][0]:.1f},{offset_pts[mid_i][1]:.1f})")
                    debug_points.append((ln["code"], clean_pts[mid_i], offset_pts[mid_i]))
            final_pts = chaikin(offset_pts, CHAIKIN_ITERATIONS)
            branch_paths.append([(round(x, 1), round(y, 1)) for x, y in final_pts])

        output_lines.append({
            "line_id": ln["line_id"],
            "code": ln["code"],
            "name": ln["name"],
            "color": ln["color"],
            "rank": rank_by_line[ln["line_id"]],
            "branches": branch_paths,
        })

    if debug_points:
        print("\n  [debug] Paarweise Abstaende der versetzten Bahnen an derselben Stelle der Kante:")
        for i in range(len(debug_points)):
            for j in range(i + 1, len(debug_points)):
                code_i, base_i, off_i = debug_points[i]
                code_j, base_j, off_j = debug_points[j]
                same_base = math.hypot(base_i[0] - base_j[0], base_i[1] - base_j[1]) < 0.05
                gap = math.hypot(off_i[0] - off_j[0], off_i[1] - off_j[1])
                print(f"    {code_i:5s} <-> {code_j:5s}: {gap:5.2f} px"
                      f"{'' if same_base else '   (ACHTUNG: unterschiedliche Basisgeometrie!)'}")

    # --- 7. Haltemarker: Richtung und Breite des Buendels am Halt ------------
    edges_by_stop = defaultdict(list)
    for key in edge_geom:
        edges_by_stop[key[0]].append(key)
        edges_by_stop[key[1]].append(key)

    output_stops = []
    for s in graph["stops"]:
        sid = s["stop_id"]
        incident = edges_by_stop.get(sid, [])
        lines_here = sorted(
            {lid for key in incident for lid in edge_slots.get(key, {})},
            key=lambda lid: rank_by_line[lid],
        )
        x, y = to_px(s["px_m"], s["py_m"])

        angle_deg = 0.0
        n_widest = 1
        if incident:
            # breiteste anliegende Kante bestimmt Ausrichtung und Laenge des Markers
            widest = max(incident, key=lambda k: len(edge_slots.get(k, {})))
            n_widest = max(len(edge_slots.get(widest, {})), 1)
            geom = edge_geom[widest]
            # Richtung am Halt: erstes bzw. letztes Segment der Kante nehmen
            if widest[0] == sid:
                dx, dy = geom[1][0] - geom[0][0], geom[1][1] - geom[0][1]
            else:
                dx, dy = geom[-1][0] - geom[-2][0], geom[-1][1] - geom[-2][1]
            angle_deg = math.degrees(math.atan2(dy, dx))

        output_stops.append({
            "stop_id": sid,
            "name": s["name"],
            "x": round(x, 1),
            "y": round(y, 1),
            "n_lines": len(lines_here),
            "lines": lines_here,
            "bundle_angle_deg": round(angle_deg, 1),
            "bundle_half_len": round((n_widest - 1) / 2.0 * SLOT_SPACING_PX, 2),
        })

    # --- 8. Basiskarte in dieselben Pixelkoordinaten umrechnen ---------------
    countries_px = []
    for c in basemap["countries"]:
        polys = [[[round(v, 1) for v in to_px(x, y)] for x, y in ring] for ring in c["polygons"]]
        lx, ly = to_px(c["label_x"], c["label_y"])
        countries_px.append({
            "name": c["name"],
            "label_x": round(lx, 1),
            "label_y": round(ly, 1),
            "polygons": polys,
        })

    output = {
        "meta": {
            "svg_width": SVG_WIDTH,
            "svg_height": round(svg_height, 1),
            "scale_px_per_m": scale,
            "projected_crs": PROJECTED_CRS,
            "line_width_px": LINE_WIDTH_PX,
            "slot_spacing_px": SLOT_SPACING_PX,
            "simplify_tolerance_px": SIMPLIFY_TOLERANCE_PX,
            "slot_transition_px": SLOT_TRANSITION_PX,
            "chaikin_iterations": CHAIKIN_ITERATIONS,
        },
        "countries": countries_px,
        "lines": output_lines,
        "stops": output_stops,
        "stats": {
            "n_lines": len(output_lines),
            "n_stops": len(output_stops),
            "n_edges": len(edge_geom),
            "max_bundle_size": max_bundle,
            "n_slot_changes": slot_change_count,
            "n_edge_deviations": len(deviations),
        },
    }

    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    n_pts = sum(len(b) for l in output_lines for b in l["branches"])
    print(f"\n=== Phase 4: Buendelung ===")
    print(f"Linien: {len(output_lines)}, Halte: {len(output_stops)}, Kanten: {len(edge_geom)}")
    print(f"Slot-Wechsel gesamt (Abzweige): {slot_change_count}")
    print(f"Stuetzpunkte in der Ausgabe: {n_pts}")
    print(f"Ausgabe geschrieben nach {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Phase 4 - Buendelung der Linien")
    ap.add_argument("--debug-edge", nargs=2, metavar=("HALT_A", "HALT_B"),
                    help="Slot-Werte aller Linien auf dieser Kante ausgeben (Halte-IDs)")
    args = ap.parse_args()
    main(debug_edge=tuple(sorted(args.debug_edge)) if args.debug_edge else None)
