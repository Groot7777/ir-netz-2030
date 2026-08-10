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

4. WEICHE SLOT-UEBERGAENGE. Wo eine Linie den Slot wechselt (Abzweig), wird
   der Wechsel als Rampe ausgefuehrt statt als Sprung. Die Rampenlaenge richtet
   sich nach der Laenge der angrenzenden Kanten - ein festes Glaettungsfenster
   wuerde im dichten Netz die Slots ueber mehrere Kanten hinweg wegmitteln.

5. VEREINFACHEN VOR, GLAETTEN NACH dem Versatz (Douglas-Peucker bzw. Chaikin),
   damit das Buendel nicht ausfranst.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import substring, transform as shapely_transform

from kml_common import assign_stops_to_segments, parse_kml

INPUT_KML = Path("data/input/RENetz_2030_v3.kml")
GRAPH_PATH = Path("data/02_graph.json")
BASEMAP_PATH = Path("data/03_basemap.json")
OUTPUT_PATH = Path("data/04_bundled.json")

PROJECTED_CRS = "EPSG:3034"          # wie Phase 3: ETRS89 / LCC Europe

SVG_WIDTH = 4200.0                   # Breite der Zeichenflaeche in px
MARGIN_PX = 60.0                     # Rand um das Netz herum

LINE_WIDTH_PX = 4.0                  # Linienbreite bei Standardzoom
SLOT_SPACING_PX = 1.3 * LINE_WIDTH_PX  # Abstand zwischen zwei Bahnen im Buendel

SIMPLIFY_TOLERANCE_PX = 1.2          # Douglas-Peucker VOR dem Versatz
DENSIFY_MAX_SEG_PX = 5.0             # lange Segmente unterteilen, damit Rampen greifen koennen
# Obergrenze fuer die Laenge eines Slot-Wechsels, angegeben in Kilometern
# statt Pixeln: Die beiden Kartenseiten haben sehr verschiedene Massstaebe
# (4,8 gegenueber 19 px/km). Ein fester Pixelwert waere auf der
# Ruhrgebietsseite laenger als der halbe Halteabstand und liesse die Linien
# dort dauerhaft weben statt kurz zu versetzen.
SLOT_TRANSITION_KM = 4.0
CHAIKIN_ITERATIONS = 1               # Glaettung NACH dem Versatz
MITER_LIMIT = 2.5                    # Begrenzung der Gehrung an spitzen Ecken

SEGMENT_TIE_TOLERANCE_M = 50.0       # identisch zu Phase 2

# Durchfahrt-Knoten: Ein Express haelt nicht an allen Halten seiner Strecke und
# haette dadurch voellig andere Kanten als der Regionalzug daneben - beide
# koennten nicht gebuendelt werden und wuerden sich gegenseitig verdecken
# (RE35X teilt mit RE35 nur 5 von 24 Kanten). Halte, die dicht an der Strecke
# einer Linie liegen, an denen sie aber nicht haelt, werden deshalb als reine
# Geometrieknoten in ihren Weg eingefuegt. Gezeichnet wird dort kein Halt.
PASSTHROUGH_TOL_M = 60.0
EDGE_DEVIATION_WARN_PX = 12.0        # ab hier: Linien nehmen auf derselben Kante spuerbar andere Wege

# Ballungsraum-Ausschnitt: Im Ruhrgebiet liegen die Halte im Netzmassstab nur
# rund 7 px auseinander - dort ist keine lesbare Beschriftung moeglich. Die drei
# S-Bahn-Linien wandern deshalb komplett auf eine eigene, zweite Kartenseite,
# die den Ballungsraum bildschirmfuellend zeigt. Auf der Hauptkarte markiert ein
# gestricheltes Rechteck den Bereich.
INSET_TITLE = "Ballungsraum Ruhrgebiet"
INSET_CANVAS_WIDTH = 1450.0          # eigene Zeichenflaeche der zweiten Seite
INSET_MARGIN_PX = 70.0
INSET_PAD_M = 6000.0                 # Puffer um die S-Bahn-Halte herum (Meter)


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
        # Hoechstens 32 % je Seite: benachbarte Rampen koennen sich dadurch nie
        # ueberlappen, und der Slot-Wechsel bleibt ein kurzer Versatz statt
        # eines Webens ueber die halbe Kante.
        w = min(max_transition_px / 2.0, len_before * 0.32, len_after * 0.32)
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


# --- Aufbau einer Ansicht -----------------------------------------------------

def build_view(name, title, lines_raw, graph, stop_by_id, line_ids, to_px,
               scale_px_per_m, allowed_stop_ids=None, debug_edge=None, verbose=True):
    """
    Berechnet Buendelgeometrie fuer eine Kartenansicht.

    Die Slot-Vergabe erfolgt bewusst PRO ANSICHT: Blendet die Hauptkarte die
    S-Bahnen aus, duerfen deren Slots nicht als Luecken im RE-Buendel
    stehenbleiben - die verbleibenden Linien ruecken zusammen und werden neu
    um die Streckenmitte zentriert.

    line_ids:         Menge der Linien, die in dieser Ansicht erscheinen
    allowed_stop_ids: Beschraenkung auf einen Kartenausschnitt (None = alle)
    to_px:            Abbildung EPSG:3034-Meter -> Pixel dieser Ansicht
    """
    # Rampenlaenge aus dem Massstab dieser Ansicht ableiten
    transition_px = SLOT_TRANSITION_KM * 1000.0 * scale_px_per_m

    edge_candidates = defaultdict(list)
    line_branches = {}
    bediente_linien = defaultdict(list)   # stop_id -> Linien, die dort tatsaechlich halten

    stop_pool = (sorted(allowed_stop_ids) if allowed_stop_ids is not None
                 else [s["stop_id"] for s in graph["stops"]])

    for ln in lines_raw:
        if ln["line_id"] not in line_ids:
            continue
        graph_line = next(g for g in graph["lines"] if g["line_id"] == ln["line_id"])
        eigene_halte = {sid for seq in graph_line["sequences"] for sid in seq}
        if allowed_stop_ids is not None:
            eigene_halte &= allowed_stop_ids
        if len(eigene_halte) < 2:
            continue

        # Halte an der Strecke, an denen diese Linie nicht haelt, als reine
        # Geometrieknoten aufnehmen - sonst kann ein Express nicht neben dem
        # Regionalzug gebuendelt werden (siehe Kommentar bei PASSTHROUGH_TOL_M).
        knoten_ids = set(eigene_halte)
        for sid in stop_pool:
            if sid in knoten_ids:
                continue
            s = stop_by_id[sid]
            p = Point(s["px_m"], s["py_m"])
            for seg in ln["segments_proj"]:
                if seg is not None and seg.distance(p) <= PASSTHROUGH_TOL_M:
                    knoten_ids.add(sid)
                    break

        stops_xy = [(sid, stop_by_id[sid]["px_m"], stop_by_id[sid]["py_m"]) for sid in knoten_ids]

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
                if arc_b - arc_a < 1.0:
                    continue
                piece = substring(seg, arc_a, arc_b)
                if piece.geom_type != "LineString" or len(piece.coords) < 2:
                    continue
                pts_px = [to_px(x, y) for x, y in piece.coords]
                key = tuple(sorted((id_a, id_b)))
                if (id_a, id_b) != key:
                    pts_px = pts_px[::-1]
                edge_candidates[key].append((ln["line_id"], pts_px))
            if len(seq_ids) >= 2:
                branches.append(seq_ids)
                for sid in seq_ids:
                    # nur echte Halte bekommen spaeter einen Marker
                    if sid in eigene_halte and ln["line_id"] not in bediente_linien[sid]:
                        bediente_linien[sid].append(ln["line_id"])
        line_branches[ln["line_id"]] = branches

    # kanonische Geometrie je Kante: die detaillierteste Variante, damit alle
    # Linien des Buendels auf derselben Basislinie liegen
    edge_geom = {}
    deviations = []
    for key, candidates in edge_candidates.items():
        best_line_id, best_pts = max(candidates, key=lambda c: len(c[1]))
        ref_pts = dedup_consecutive(best_pts)
        if len(ref_pts) < 2:
            continue
        ref = LineString(ref_pts)
        for line_id, pts in candidates:
            pts_clean = dedup_consecutive(pts)
            if line_id == best_line_id or len(pts_clean) < 2:
                continue
            dev = ref.hausdorff_distance(LineString(pts_clean))
            if dev > EDGE_DEVIATION_WARN_PX:
                deviations.append((key, best_line_id, line_id, dev))
        simplified = ref.simplify(SIMPLIFY_TOLERANCE_PX, preserve_topology=False)
        edge_geom[key] = densify(dedup_consecutive(list(simplified.coords)), DENSIFY_MAX_SEG_PX)

    # globale Linienreihenfolge, aber Slots nur unter den Linien DIESER Ansicht
    view_lines = [ln for ln in sorted(lines_raw, key=natural_sort_key) if ln["line_id"] in line_ids]
    rank_by_line = {ln["line_id"]: i for i, ln in enumerate(view_lines)}

    edge_slots = {}
    for key in edge_geom:
        lines_here = sorted({lid for lid, _ in edge_candidates[key]}, key=lambda lid: rank_by_line[lid])
        n = len(lines_here)
        edge_slots[key] = {lid: (i - (n - 1) / 2.0) for i, lid in enumerate(lines_here)}

    max_bundle = max((len(v) for v in edge_slots.values()), default=0)

    # Wege zusammensetzen, Slot-Rampen legen, versetzen, glaetten
    output_lines = []
    slot_change_count = 0
    debug_points = []

    for ln in view_lines:
        branch_paths = []
        for seq in line_branches.get(ln["line_id"], []):
            pts, slots, vertex_edge = [], [], []
            for id_a, id_b in zip(seq, seq[1:]):
                key = tuple(sorted((id_a, id_b)))
                if key not in edge_geom:
                    continue
                geom = edge_geom[key]
                forward = (id_a, id_b) == key
                seg_pts = geom if forward else geom[::-1]
                slot = edge_slots[key][ln["line_id"]]
                slot_signed = slot if forward else -slot
                if pts and slots and abs(slots[-1] - slot_signed) > 1e-9:
                    slot_change_count += 1
                start = 1 if pts else 0
                pts.extend(seg_pts[start:])
                slots.extend([slot_signed] * len(seg_pts[start:]))
                vertex_edge.extend([key] * len(seg_pts[start:]))

            if len(pts) < 2:
                continue

            clean_pts, clean_slots, clean_edges = [], [], []
            for p, s, e in zip(pts, slots, vertex_edge):
                if not clean_pts or abs(p[0] - clean_pts[-1][0]) > 1e-6 or abs(p[1] - clean_pts[-1][1]) > 1e-6:
                    clean_pts.append(p)
                    clean_slots.append(s)
                    clean_edges.append(e)
            if len(clean_pts) < 2:
                continue

            smoothed = ramp_slots(clean_pts, clean_slots, transition_px)
            offsets = [s * SLOT_SPACING_PX for s in smoothed]
            offset_pts = offset_polyline(clean_pts, offsets)

            if debug_edge:
                idx = [i for i, e in enumerate(clean_edges) if e == debug_edge]
                if idx:
                    mid_i = idx[len(idx) // 2]
                    print(f"  [debug/{name}] {ln['code']:6s} Soll-Slot={clean_slots[mid_i]:+.1f} "
                          f"gerampt={smoothed[mid_i]:+.2f} "
                          f"versetzt=({offset_pts[mid_i][0]:.1f},{offset_pts[mid_i][1]:.1f})")
                    debug_points.append((ln["code"], clean_pts[mid_i], offset_pts[mid_i]))

            final_pts = chaikin(offset_pts, CHAIKIN_ITERATIONS)
            branch_paths.append([(round(x, 1), round(y, 1)) for x, y in final_pts])

        if not branch_paths:
            continue
        output_lines.append({
            "line_id": ln["line_id"],
            "code": ln["code"],
            "name": ln["name"],
            "color": ln["color"],
            "rank": rank_by_line[ln["line_id"]],
            "branches": branch_paths,
        })

    if debug_points:
        print(f"  [debug/{name}] paarweise Abstaende:")
        for i in range(len(debug_points)):
            for j in range(i + 1, len(debug_points)):
                ci, bi, oi = debug_points[i]
                cj, bj, oj = debug_points[j]
                same = math.hypot(bi[0] - bj[0], bi[1] - bj[1]) < 0.05
                print(f"    {ci:5s} <-> {cj:5s}: {math.hypot(oi[0]-oj[0], oi[1]-oj[1]):5.2f} px"
                      f"{'' if same else '   (ACHTUNG: verschiedene Basisgeometrie)'}")

    # Haltemarker: Ausrichtung und Breite des Buendels am Halt
    edges_by_stop = defaultdict(list)
    for key in edge_geom:
        edges_by_stop[key[0]].append(key)
        edges_by_stop[key[1]].append(key)

    view_line_ids = {l["line_id"] for l in output_lines}
    output_stops = []
    for sid, incident in edges_by_stop.items():
        # Nur Halte, an denen wirklich eine Linie haelt. Durchfahrt-Knoten
        # teilen zwar die Kanten, bekommen aber keinen Bahnhofsmarker.
        lines_here = [lid for lid in bediente_linien.get(sid, []) if lid in view_line_ids]
        if not lines_here:
            continue
        lines_here.sort(key=lambda lid: rank_by_line[lid])
        s = stop_by_id[sid]
        x, y = to_px(s["px_m"], s["py_m"])
        n_widest = max((len(edge_slots.get(k, {})) for k in incident), default=1)

        # Ausrichtung des Markers: Durchgangsrichtung der Strecke, gemittelt
        # ueber ALLE anliegenden Kanten. Nur die breiteste Kante zu nehmen
        # laesst benachbarte Marker in verschiedenen Winkeln stehen, wodurch
        # sie sich an Knoten sichtbar ueberkreuzen. Gemittelt wird ueber den
        # doppelten Winkel, weil eine Strecke keine Richtung hat: eine Kante
        # nach Osten und eine nach Westen beschreiben dieselbe Achse.
        sx2 = sy2 = 0.0
        for key in incident:
            geom = edge_geom[key]
            if key[0] == sid:
                dx, dy = geom[1][0] - geom[0][0], geom[1][1] - geom[0][1]
            else:
                dx, dy = geom[-1][0] - geom[-2][0], geom[-1][1] - geom[-2][1]
            laenge = math.hypot(dx, dy)
            if laenge < 1e-9:
                continue
            winkel2 = 2 * math.atan2(dy, dx)
            gewicht = len(edge_slots.get(key, {})) or 1
            sx2 += gewicht * math.cos(winkel2)
            sy2 += gewicht * math.sin(winkel2)
        if abs(sx2) < 1e-12 and abs(sy2) < 1e-12:
            achse = 0.0
        else:
            achse = math.degrees(math.atan2(sy2, sx2)) / 2.0
        output_stops.append({
            "stop_id": sid,
            "name": s["name"],
            "x": round(x, 1),
            "y": round(y, 1),
            "n_lines": len(lines_here),
            "lines": lines_here,
            "degree": len(incident),
            "bundle_angle_deg": round(achse, 1),
            "bundle_half_len": round((n_widest - 1) / 2.0 * SLOT_SPACING_PX, 2),
        })

    if verbose:
        print(f"  Ansicht '{name}': {len(output_lines)} Linien, {len(output_stops)} Halte, "
              f"{len(edge_geom)} Kanten, groesstes Buendel {max_bundle}, "
              f"{slot_change_count} Slot-Wechsel")
        if deviations:
            print(f"    {len(deviations)} Kanten mit abweichender Streckenfuehrung "
                  f"(> {EDGE_DEVIATION_WARN_PX:.0f} px) - dort gilt die detaillierteste Variante")

    return {
        "name": name,
        "title": title,
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


# --- Hauptprogramm -----------------------------------------------------------

def main(debug_edge=None):
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    basemap = json.loads(BASEMAP_PATH.read_text(encoding="utf-8"))
    lines_raw, _stops_raw = parse_kml(INPUT_KML)

    stop_by_id = {s["stop_id"]: s for s in graph["stops"]}
    to_proj = Transformer.from_crs("EPSG:4326", PROJECTED_CRS, always_xy=True).transform

    for ln in lines_raw:
        ln["segments_proj"] = [
            shapely_transform(to_proj, LineString(seg)) if len(seg) >= 2 else None
            for seg in ln["segments"]
        ]
    for s in graph["stops"]:
        s["px_m"], s["py_m"] = to_proj(s["lon"], s["lat"])

    # --- Hauptkarte: Bildausschnitt aus dem gesamten Netz --------------------
    all_x = [s["px_m"] for s in graph["stops"]]
    all_y = [s["py_m"] for s in graph["stops"]]
    for ln in lines_raw:
        for seg in ln["segments_proj"]:
            if seg is not None:
                xs, ys = seg.xy
                all_x.extend(xs)
                all_y.extend(ys)
    min_x, max_x, min_y, max_y = min(all_x), max(all_x), min(all_y), max(all_y)
    scale = (SVG_WIDTH - 2 * MARGIN_PX) / (max_x - min_x)
    svg_height = (max_y - min_y) * scale + 2 * MARGIN_PX

    def to_px(x, y):
        """EPSG:3034-Meter -> Pixel der Hauptkarte (Y gespiegelt, SVG waechst nach unten)."""
        return (MARGIN_PX + (x - min_x) * scale, MARGIN_PX + (max_y - y) * scale)

    print(f"Hauptkarte: {SVG_WIDTH:.0f} x {svg_height:.0f} px, "
          f"{scale * 1000:.2f} px/km, Slot-Abstand {SLOT_SPACING_PX / scale / 1000:.1f} km")

    # --- Linien aufteilen: S-Bahnen kommen in den Ballungsraum-Ausschnitt ----
    s_line_ids = {ln["line_id"] for ln in lines_raw if ln["code"].startswith("S")}
    main_line_ids = {ln["line_id"] for ln in lines_raw} - s_line_ids

    # Ausschnittbereich aus der Lage der S-Bahn-Halte ableiten
    s_stop_ids = set()
    for g in graph["lines"]:
        if g["line_id"] in s_line_ids:
            s_stop_ids.update(sid for seq in g["sequences"] for sid in seq)
    sx = [stop_by_id[i]["px_m"] for i in s_stop_ids]
    sy = [stop_by_id[i]["py_m"] for i in s_stop_ids]
    ix0, ix1 = min(sx) - INSET_PAD_M, max(sx) + INSET_PAD_M
    iy0, iy1 = min(sy) - INSET_PAD_M, max(sy) + INSET_PAD_M

    inset_scale = (INSET_CANVAS_WIDTH - 2 * INSET_MARGIN_PX) / (ix1 - ix0)
    inset_height = (iy1 - iy0) * inset_scale + 2 * INSET_MARGIN_PX

    def to_px_inset(x, y):
        """EPSG:3034-Meter -> Pixel der zweiten Kartenseite (eigene Zeichenflaeche)."""
        return (INSET_MARGIN_PX + (x - ix0) * inset_scale,
                INSET_MARGIN_PX + (iy1 - y) * inset_scale)

    # alle Halte im Ausschnittbereich, und alle Linien, die dort mindestens zwei bedienen
    inset_stop_ids = {s["stop_id"] for s in graph["stops"]
                      if ix0 <= s["px_m"] <= ix1 and iy0 <= s["py_m"] <= iy1}
    inset_line_ids = set()
    for g in graph["lines"]:
        n_inside = len({sid for seq in g["sequences"] for sid in seq} & inset_stop_ids)
        if n_inside >= 2:
            inset_line_ids.add(g["line_id"])

    print(f"Zweite Seite '{INSET_TITLE}': {INSET_CANVAS_WIDTH:.0f} x {inset_height:.0f} px, "
          f"{inset_scale * 1000:.1f} px/km (Hauptkarte {scale * 1000:.1f}), "
          f"{len(inset_stop_ids)} Halte, {len(inset_line_ids)} Linien")

    views = {
        "main": build_view("main", "Gesamtnetz", lines_raw, graph, stop_by_id,
                           main_line_ids, to_px, scale, debug_edge=debug_edge),
        "inset": build_view("inset", INSET_TITLE, lines_raw, graph, stop_by_id,
                            inset_line_ids, to_px_inset, inset_scale,
                            allowed_stop_ids=inset_stop_ids, debug_edge=debug_edge),
    }

    def basiskarte(transform, mit_namen=True):
        """Laenderflaechen und Grenzlinien in die Pixel einer Ansicht umrechnen."""
        laender = []
        for c in basemap["countries"]:
            polys = [[[round(v, 1) for v in transform(x, y)] for x, y in ring]
                     for ring in c["polygons"]]
            eintrag = {"name": c["name"], "polygons": polys}
            if mit_namen:
                lx, ly = transform(c["label_x"], c["label_y"])
                eintrag["label_x"] = round(lx, 1)
                eintrag["label_y"] = round(ly, 1)
            laender.append(eintrag)

        def wege(schluessel):
            return [[[round(v, 1) for v in transform(x, y)] for x, y in weg]
                    for weg in basemap.get(schluessel, [])]

        return {
            "countries": laender,
            "staatsgrenzen": wege("staatsgrenzen"),
            "bundeslaender": wege("bundeslaender"),
        }

    # Rechteck auf der Hauptkarte, das den Bereich der zweiten Seite markiert
    src_x0, src_y0 = to_px(ix0, iy1)
    src_x1, src_y1 = to_px(ix1, iy0)

    output = {
        "meta": {
            "projected_crs": PROJECTED_CRS,
            "line_width_px": LINE_WIDTH_PX,
            "slot_spacing_px": SLOT_SPACING_PX,
            "simplify_tolerance_px": SIMPLIFY_TOLERANCE_PX,
            "slot_transition_km": SLOT_TRANSITION_KM,
            "chaikin_iterations": CHAIKIN_ITERATIONS,
            # Jede Ansicht ist eine eigene Kartenseite mit eigener Zeichenflaeche
            "seiten": {
                "main": {
                    "titel": "Gesamtnetz",
                    "breite": SVG_WIDTH, "hoehe": round(svg_height, 1),
                    "scale_px_per_m": scale,
                    "quellrechteck": [round(src_x0, 1), round(src_y0, 1),
                                      round(src_x1 - src_x0, 1), round(src_y1 - src_y0, 1)],
                    "verweis": INSET_TITLE,
                },
                "inset": {
                    "titel": INSET_TITLE,
                    "breite": INSET_CANVAS_WIDTH, "hoehe": round(inset_height, 1),
                    "scale_px_per_m": inset_scale,
                    "vergroesserung": round(inset_scale / scale, 1),
                },
            },
        },
        "basiskarte": {
            "main": basiskarte(to_px),
            "inset": basiskarte(to_px_inset, mit_namen=False),
        },
        "views": views,
    }

    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nAusgabe geschrieben nach {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Phase 4 - Buendelung der Linien")
    ap.add_argument("--debug-edge", nargs=2, metavar=("HALT_A", "HALT_B"),
                    help="Slot-Werte aller Linien auf dieser Kante ausgeben (Halte-IDs)")
    args = ap.parse_args()
    main(debug_edge=tuple(sorted(args.debug_edge)) if args.debug_edge else None)
