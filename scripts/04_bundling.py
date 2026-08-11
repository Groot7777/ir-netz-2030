#!/usr/bin/env python3
"""
Phase 4 - Buendelung.

Wo mehrere Linien dieselbe Kante befahren, muessen sie als parallele Bahnen
nebeneinander laufen. Kernpunkte der Umsetzung:

1. GEMEINSAME KANTENGEOMETRIE. Fuer jede Kante wird EINE kanonische Polylinie
   gewaehlt (die detaillierteste der beteiligten Linien). Alle Linien des
   Buendels benutzen dieselbe Basisgeometrie - nur so laufen sie wirklich
   parallel.

2. PROPAGIERTE KANTENORIENTIERUNG. Slots werden in der Orientierung einer
   Kante vergeben. Diese Orientierung wird entlang der Korridore propagiert und
   liegt nicht willkuerlich (etwa alphabetisch) fest: Sonst spiegelt sich das
   gesamte Buendel an jedem Knoten, an dem die Orientierung gegen die
   Fahrtrichtung kippt, und die Linien tauschen dort ihre Seite.

3. STABILE SPUREN. Die Slots werden NICHT je Kante neu auf die Streckenmitte
   zentriert. Sonst ruecken alle Linien seitwaerts, sobald irgendwo eine Linie
   dazukommt oder abzweigt - obwohl sie unveraendert parallel weiterlaufen.
   Stattdessen behaelt jede Linie ihre Spur, und eine Kante wird nur so weit
   verschoben, dass moeglichst viele gemeinsame Linien darauf stehenbleiben.

4. SPURWECHSEL NUR AM BAHNHOF. Wo eine Linie die Spur wechselt, geschieht das
   als kurze Rampe unmittelbar am Knoten - dort verdeckt sie der weisse
   Haltemarker. Die Rampe wird an den echten Kantengrenzen gemessen und auf
   RAMPEN_ANTEIL je Seite begrenzt, damit sie nie auf freie Strecke reicht.

5. VEREINFACHEN VOR, GLAETTEN NACH dem Versatz (Douglas-Peucker bzw. Chaikin),
   damit das Buendel nicht ausfranst.

Das Skript prueft sein eigenes Ergebnis und meldet: Seitenwechsel parallel
laufender Linien, groesster Seitenversatz und den kleinsten Abstand zweier
Linien auf freier Strecke.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import substring, transform as shapely_transform, unary_union

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
# Ein Spurwechsel soll kurz und am Bahnhof passieren - dort verdeckt ihn der
# weisse Haltemarker, wie auf gedruckten Verkehrskarten. Deshalb in Pixeln
# (Markergroesse ist in beiden Ansichten gleich); zusaetzlich begrenzt
# ramp_slots die Rampe auf 32 % der angrenzenden Kanten, damit sie auf kurzen
# Kanten nicht ueber die halbe Strecke laeuft.
SLOT_TRANSITION_PX = 11.0
# Anteil einer Kante, den ein Spurwechsel hoechstens einnehmen darf (je Seite).
# Muss zur Pruefzone weiter unten passen, sonst reicht eine Rampe auf die
# freie Strecke und die Linien kommen sich dort naeher als einen Spurabstand.
RAMPEN_ANTEIL = 0.22
CHAIKIN_ITERATIONS = 1               # Glaettung NACH dem Versatz
MITER_LIMIT = 2.5                    # Begrenzung der Gehrung an spitzen Ecken (Faktor)
MAX_GEHRUNG_PX = 3.0                 # und zusaetzlich absolut, damit aeussere Spuren keine Zacken werfen
KNOTEN_ZIEHWEITE_PX = 40.0           # auf dieser Laenge werden Kantenenden zum gemeinsamen Knotenpunkt gezogen
MAX_MARKER_DICKE_PX = 0.9 * LINE_WIDTH_PX   # Obergrenze fuer die halbe Markerdicke an Sternknoten
ACHSEN_NACHBARSCHAFT_PX = 26.0       # in diesem Umkreis werden Markerachsen aneinander angeglichen
ACHSEN_MAX_DREHUNG_GRAD = 30.0       # hoechstens so weit darf ein Marker dabei gedreht werden

SEGMENT_TIE_TOLERANCE_M = 50.0       # identisch zu Phase 2

# Durchfahrt-Knoten: Ein Express haelt nicht an allen Halten seiner Strecke und
# haette dadurch voellig andere Kanten als der Regionalzug daneben - beide
# koennten nicht gebuendelt werden und wuerden sich gegenseitig verdecken
# (RE35X teilt mit RE35 nur 5 von 24 Kanten). Halte, die dicht an der Strecke
# einer Linie liegen, an denen sie aber nicht haelt, werden deshalb als reine
# Geometrieknoten in ihren Weg eingefuegt. Gezeichnet wird dort kein Halt.
PASSTHROUGH_TOL_M = 60.0
# Der Wert oben genuegt nur, wenn beide Linien exakt denselben Streckenverlauf
# in der KML haben. Zwei Linien auf demselben Korridor weichen aber oft ein paar
# hundert Meter voneinander ab (getrennte Gleispaare, unterschiedlich
# digitalisierte Trassen). Im Kartenmassstab ist das weniger als eine
# Linienbreite - sie laegen uebereinander, ohne je eine Kante zu teilen.
# Massgeblich ist deshalb der ZEICHNERISCHE Abstand: Alles, was naeher als
# PASSTHROUGH_BREITEN Linienbreiten an der Strecke liegt, wird als Knoten
# uebernommen und damit buendelbar.
PASSTHROUGH_BREITEN = 3.0
PASSTHROUGH_MAX_M = 400.0            # Obergrenze, damit die Hauptkarte nicht ganze Staedte verschmilzt
UMWEG_FAKTOR = 2.5                   # ab diesem Verhaeltnis Trassenlaenge/Luftlinie gilt eine Kante als unbrauchbar
EDGE_DEVIATION_WARN_PX = 12.0        # ab hier: Linien nehmen auf derselben Kante spuerbar andere Wege

# Zweite Kartenseite: Nordrhein-Westfalen ist mit Abstand am dichtesten
# befahren - im Netzmassstab liegen die Ruhrgebiets-Halte nur rund 7 px
# auseinander, lesbare Beschriftung ist dort unmoeglich. Die Landesflaeche
# kommt aus Phase 3; die drei S-Bahn-Linien erscheinen ausschliesslich hier.
# Auf der Hauptkarte markiert ein gestricheltes Rechteck den Bereich.
INSET_TITLE = "Nordrhein-Westfalen"
# Die zweite Seite hat einen voellig eigenen Massstab. Linien, Schrift und
# Marker sind auf beiden Seiten gleich gross (in Pixeln); eine groessere
# Zeichenflaeche zieht deshalb allein die Halte weiter auseinander - genau der
# Platz, den die Beschriftung im Ruhrgebiet braucht. 11000 px sind rund
# 42 px/km gegenueber 4,8 px/km auf der Hauptkarte, also knapp neunfach.
INSET_CANVAS_WIDTH = 11000.0
INSET_MARGIN_PX = 140.0
INSET_PAD_M = 9000.0                 # Puffer um die Landesgrenze herum (Meter)


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


def ramp_slots(pts, slots, max_transition_px, kanten_grenzen=None):
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
        # Hoechstens RAMPEN_ANTEIL je Seite. Das begrenzt den Spurwechsel auf
        # die unmittelbare Bahnhofsumgebung: Auf freier Strecke liegen die
        # Linien dadurch garantiert im vollen Spurabstand nebeneinander, und
        # benachbarte Rampen koennen sich nie ueberlappen.
        w = min(max_transition_px / 2.0,
                len_before * RAMPEN_ANTEIL, len_after * RAMPEN_ANTEIL)

        # Zusaetzlich an den ANGRENZENDEN KANTEN messen, nicht nur am Abschnitt
        # gleichen Slots: Der kann sich ueber mehrere Kanten erstrecken, dann
        # reichte die Rampe trotz der Begrenzung weit auf die freie Strecke.
        if kanten_grenzen:
            vorher = max((g for g in kanten_grenzen if g < boundary - 1e-6),
                         default=s[i0])
            nachher = min((g for g in kanten_grenzen if g > boundary + 1e-6),
                          default=s[j1])
            w = min(w, (boundary - vorher) * RAMPEN_ANTEIL,
                    (nachher - boundary) * RAMPEN_ANTEIL)
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
        # Zusaetzlich ABSOLUT begrenzen. Der reine Faktor reicht nicht: Bei einer
        # aeusseren Spur (bis 16 px Versatz) zieht schon der Faktor 2,5 die Ecke
        # 40 px weit heraus - im Bild eine schmale Zacke quer durch die
        # Nachbarlinien. Mit der Obergrenze bleibt an spitzen Ecken eine winzige
        # Kerbe, die die anschliessende Glaettung wegnimmt.
        versatz = offsets[i] * scale
        grenze = abs(offsets[i]) + MAX_GEHRUNG_PX
        versatz = max(-grenze, min(grenze, versatz))
        out.append((pts[i][0] + nx * versatz, pts[i][1] + ny * versatz))
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


def marker_mittelpunkt(start, geometrien, schritte=40):
    """
    Punkt suchen, der den groessten Abstand zu allen angegebenen Linien
    minimiert (1-Center-Problem, iterativ genaehert).

    Der Schwerpunkt allein genuegt nicht: Laeuft an einem Knoten eine Linie aus
    einer ganz anderen Richtung ein, zieht sie den Schwerpunkt zu sich und der
    Marker rutscht von den uebrigen herunter. Gesucht ist stattdessen der Punkt,
    der zu ALLEN dort haltenden Linien moeglichst nah liegt.
    """
    px, py = start
    for i in range(schritte):
        weit = None
        for g in geometrien:
            q = g.interpolate(g.project(Point(px, py)))
            d = math.hypot(q.x - px, q.y - py)
            if weit is None or d > weit[0]:
                weit = (d, q.x, q.y)
        if weit is None or weit[0] < 0.05:
            break
        t = 0.5 / (1.0 + i * 0.15)      # abnehmende Schrittweite
        px += (weit[1] - px) * t
        py += (weit[2] - py) * t
    return px, py


def knoten_zusammenziehen(edge_geom, ziehweite_px=KNOTEN_ZIEHWEITE_PX):
    """
    Kantenenden an einem Knoten auf einen gemeinsamen Punkt ziehen.

    Ein Bahnhof liegt in der KML nicht auf den Trassen, sondern daneben - und
    jede Linie projiziert ihn auf eine etwas andere Stelle ihrer eigenen
    Trasse. In Saarbruecken lagen die Enden zweier Kanten dadurch ueber 2 km
    auseinander: Die Linien passierten denselben Bahnhof an sichtbar
    verschiedenen Orten, und kein Haltemarker konnte auf allen liegen.

    Die Korrektur wird ueber die ersten bzw. letzten ziehweite_px der Kante
    ausgeschlichen, damit die Trasse dahinter unveraendert bleibt und kein Knick
    entsteht.
    """
    ziele = defaultdict(list)
    for key, geom in edge_geom.items():
        ziele[key[0]].append(geom[0])
        ziele[key[1]].append(geom[-1])
    ziel = {sid: (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))
            for sid, ps in ziele.items()}

    for key, geom in edge_geom.items():
        if len(geom) < 2:
            continue
        bogen = cumulative_arclen(geom)
        gesamt = bogen[-1]
        if gesamt < 1e-9:
            continue
        weite = min(ziehweite_px, gesamt * 0.45)
        neu = list(geom)
        for sid, idx, abstand in ((key[0], 0, bogen), (key[1], -1, [gesamt - b for b in bogen])):
            dx = ziel[sid][0] - geom[idx][0]
            dy = ziel[sid][1] - geom[idx][1]
            if math.hypot(dx, dy) < 1e-9:
                continue
            for i, s in enumerate(abstand):
                if s >= weite:
                    continue
                t = 1.0 - s / weite
                gewicht = t * t * (3.0 - 2.0 * t)      # Smoothstep, knickfreier Uebergang
                neu[i] = (neu[i][0] + dx * gewicht, neu[i][1] + dy * gewicht)
        edge_geom[key] = neu


def entdopple_folge(seq):
    """
    Mehrfach befahrene Kanten aus einer Knotenfolge entfernen.

    Einige Linienzuege enthalten Spitzkehren: Die S3 faehrt Essen Hbf - Steele -
    Steele Ost und denselben Weg wieder zurueck, bevor es nach Essen-Horst
    weitergeht. Gezeichnet wuerde dieser Abschnitt dann zweimal - einmal je
    Fahrtrichtung und damit auf gespiegelter Spur, also genau auf der Bahn der
    Nachbarlinie. Jede Kante wird deshalb nur bei ihrer ersten Befahrung
    gezeichnet; die Folge zerfaellt dabei in mehrere Teilwege, die als getrennte
    Polylinien derselben Linie ausgegeben werden.

    Echte Schleifen bleiben unangetastet: Die Achterschleife der S10 beruehrt
    Bochum Hbf zweimal, benutzt dabei aber jedes Mal andere Kanten.
    """
    gesehen = set()
    teile, aktuell = [], []
    for a, b in zip(seq, seq[1:]):
        k = tuple(sorted((a, b)))
        if k in gesehen:
            if len(aktuell) >= 2:
                teile.append(aktuell)
            aktuell = []
            continue
        gesehen.add(k)
        if aktuell and aktuell[-1] == a:
            aktuell.append(b)
        else:
            if len(aktuell) >= 2:
                teile.append(aktuell)
            aktuell = [a, b]
    if len(aktuell) >= 2:
        teile.append(aktuell)
    return teile


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
    edge_candidates = defaultdict(list)
    line_branches = {}
    umwege = []
    bediente_linien = defaultdict(list)   # stop_id -> Linien, die dort tatsaechlich halten

    # Durchfahrt-Toleranz in Metern, abgeleitet aus dem Massstab dieser Ansicht
    passthrough_tol = min(
        max(PASSTHROUGH_TOL_M, PASSTHROUGH_BREITEN * LINE_WIDTH_PX / scale_px_per_m),
        PASSTHROUGH_MAX_M,
    )
    if verbose:
        print(f"    Durchfahrt-Toleranz {passthrough_tol:.0f} m "
              f"({passthrough_tol * scale_px_per_m:.1f} px)")

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
                if seg is not None and seg.distance(p) <= passthrough_tol:
                    knoten_ids.add(sid)
                    break

        stops_xy = [(sid, stop_by_id[sid]["px_m"], stop_by_id[sid]["py_m"])
                    for sid in sorted(knoten_ids)]

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
                # Umweg-Notbremse: Legt die KML-Trasse zwischen zwei benachbarten
                # Halten ein Vielfaches der Luftlinie zurueck, ist sie dort nicht
                # zu gebrauchen (S3/S30 fahren zwischen Essen-Steele Ost und
                # Essen-Horst 13,5 km fuer 1,6 km Luftlinie - im Bild eine
                # Haarnadel quer durch alle Nachbarlinien). Dann wird die Kante
                # direkt verbunden.
                a_pt, b_pt = piece.coords[0], piece.coords[-1]
                luftlinie = math.dist(a_pt, b_pt)
                if luftlinie > 1.0 and piece.length > UMWEG_FAKTOR * luftlinie:
                    umwege.append((ln["code"], id_a, id_b, piece.length / luftlinie))
                    piece = LineString([a_pt, b_pt])
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
        line_branches[ln["line_id"]] = [teil for br in branches for teil in entdopple_folge(br)]

    if verbose and umwege:
        print(f"    {len(umwege)} Kanten mit unbrauchbarer Trasse direkt verbunden:")
        for code, a, b, f in sorted(umwege, key=lambda u: -u[3])[:8]:
            print(f"      {code}: {a} - {b} ({f:.1f}-facher Umweg)")

    # kanonische Geometrie je Kante: die detaillierteste Variante, damit alle
    # Linien des Buendels auf derselben Basislinie liegen
    edge_geom = {}
    deviations = []
    for key, candidates in edge_candidates.items():
        # Massgeblich ist zuerst die KUERZESTE Variante: Macht die Trasse einer
        # Linie auf dieser Kante einen Bogen, den die anderen nicht machen,
        # zoege die "detaillierteste" Variante das ganze Buendel mit hinaus.
        # Unter den nahezu gleich langen Varianten gewinnt dann die mit den
        # meisten Stuetzpunkten, damit keine grob vereinfachte Linie das
        # Buendel begradigt.
        laengen = [(lid, pts, LineString(dedup_consecutive(pts)).length
                    if len(dedup_consecutive(pts)) >= 2 else float("inf"))
                   for lid, pts in candidates]
        kuerzeste = min(l for _, _, l in laengen)
        best_line_id, best_pts, _ = max(
            (c for c in laengen if c[2] <= kuerzeste * 1.10),
            key=lambda c: len(c[1]),
        )
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

    knoten_zusammenziehen(edge_geom)

    # --- Kantenorientierung entlang der Korridore festlegen ------------------
    # Die Slots einer Kante werden in deren Orientierung vergeben. Waere die
    # Orientierung willkuerlich (etwa alphabetisch nach Halte-ID), spiegelte
    # sich das gesamte Buendel an jedem Knoten, an dem die Orientierung gegen
    # die Fahrtrichtung kippt: Die Linien tauschten dort ihre Seite, obwohl sie
    # weiter parallel verlaufen. Die Orientierung wird deshalb entlang der
    # Linienwege propagiert, sodass aufeinanderfolgende Kanten eines Korridors
    # immer in dieselbe Richtung zeigen.
    nachbarn = defaultdict(list)
    for branches in line_branches.values():
        for seq in branches:
            vorige = None
            for id_a, id_b in zip(seq, seq[1:]):
                key = tuple(sorted((id_a, id_b)))
                if key not in edge_geom:
                    vorige = None
                    continue
                if vorige is not None:
                    # id_a ist der gemeinsame Knoten beider Kanten
                    nachbarn[vorige].append((key, id_a))
                    nachbarn[key].append((vorige, id_a))
                vorige = key

    def knotenlage(key, knoten):
        """+1, wenn der Knoten das zweite Element der Kante ist, sonst -1."""
        return 1 if key[1] == knoten else -1

    # Ringe im Netz koennen die Bedingung nicht immer erfuellen (die Parität
    # entlang eines Zyklus kann nicht aufgehen). Damit die unvermeidbaren
    # Konflikte auf unwichtigen Kanten landen, werden stark befahrene Kanten
    # zuerst orientiert.
    def kantengewicht(key):
        return len({lid for lid, _ in edge_candidates[key]})

    orientierung = {}
    orient_konflikte = 0
    for start in sorted(sorted(edge_geom), key=lambda k: -kantengewicht(k)):
        if start in orientierung:
            continue
        orientierung[start] = 1
        warteschlange = [start]
        while warteschlange:
            warteschlange.sort(key=lambda k: kantengewicht(k))
            e1 = warteschlange.pop()
            for e2, knoten in nachbarn.get(e1, []):
                # beide Kanten sollen "gleich herum" durch den Knoten zeigen
                soll = -orientierung[e1] * knotenlage(e1, knoten) * knotenlage(e2, knoten)
                if e2 not in orientierung:
                    orientierung[e2] = soll
                    warteschlange.append(e2)
                elif orientierung[e2] != soll:
                    orient_konflikte += 1

    def kanten_anfang(key):
        """Startknoten der Kante in ihrer festgelegten Orientierung."""
        return key[0] if orientierung[key] > 0 else key[1]

    # globale Linienreihenfolge, aber Slots nur unter den Linien DIESER Ansicht
    view_lines = [ln for ln in sorted(lines_raw, key=natural_sort_key) if ln["line_id"] in line_ids]
    rank_by_line = {ln["line_id"]: i for i, ln in enumerate(view_lines)}

    # --- Slots vergeben: die Spur bleibt entlang des Korridors stehen --------
    # Bewusst NICHT je Kante neu auf die Streckenmitte zentriert. Sonst ruecken
    # alle Linien eines Buendels seitwaerts, sobald irgendwo eine Linie
    # dazukommt oder abzweigt - obwohl sie unveraendert parallel weiterlaufen.
    # Genau das sieht als Weben aus. Stattdessen behaelt jede Linie ihre Spur;
    # die Kante wird nur so weit verschoben, dass moeglichst viele gemeinsame
    # Linien exakt auf ihrer bisherigen Spur bleiben.
    edge_lines = {}
    for key in edge_geom:
        edge_lines[key] = sorted({lid for lid, _ in edge_candidates[key]},
                                 key=lambda lid: rank_by_line[lid])

    edge_slots = {}

    def wunsch_verschiebungen(kante):
        """Gewuenschte Verschiebung je bereits vergebener Nachbarkante."""
        wuensche = []
        for nachbar, _knoten in nachbarn.get(kante, []):
            if nachbar not in edge_slots:
                continue
            for lid in edge_lines[kante]:
                if lid in edge_slots[nachbar]:
                    wuensche.append(edge_slots[nachbar][lid] - edge_lines[kante].index(lid))
        return wuensche

    # Bewusst ueber SORTIERTE Listen: Die Reihenfolge, in der gleichwertige
    # Kanten drankommen, entscheidet ueber die Slot-Vergabe. Ueber eine Menge
    # iteriert haengt sie am Hash der Halte-IDs und damit an PYTHONHASHSEED -
    # zwei Laeufe ergaeben dann verschiedene Karten.
    offen = set(edge_geom)
    while offen:
        # mit der am staerksten befahrenen Kante beginnen
        start = max(sorted(offen), key=lambda k: len(edge_lines[k]))
        n = len(edge_lines[start])
        edge_slots[start] = {lid: i - (n - 1) / 2.0 for i, lid in enumerate(edge_lines[start])}
        offen.discard(start)

        # Rand der bereits vergebenen Flaeche schrittweise erweitern; immer die
        # Kante zuerst, die die meisten Linien mit dem Vergebenen teilt
        while True:
            rand = sorted(k for k in offen
                          if any(nb in edge_slots for nb, _ in nachbarn.get(k, [])))
            if not rand:
                break
            naechste = max(rand, key=lambda k: (len(wunsch_verschiebungen(k)), len(edge_lines[k])))
            wuensche = wunsch_verschiebungen(naechste)
            if wuensche:
                # haeufigster Wunsch: so bleiben die meisten Linien exakt auf ihrer Spur
                haeufigkeit = defaultdict(int)
                for w in wuensche:
                    haeufigkeit[w] += 1
                verschiebung = max(sorted(haeufigkeit), key=lambda w: (haeufigkeit[w], -abs(w)))
            else:
                n2 = len(edge_lines[naechste])
                verschiebung = -(n2 - 1) / 2.0
            edge_slots[naechste] = {lid: i + verschiebung
                                    for i, lid in enumerate(edge_lines[naechste])}
            offen.discard(naechste)

    max_bundle = max((len(v) for v in edge_slots.values()), default=0)
    max_versatz = max((abs(s) for slots in edge_slots.values() for s in slots.values()),
                      default=0.0)

    # --- Pruefgroesse: tauschen parallel laufende Linien ihre Seite? ---------
    # Zwei Linien, die zwei aufeinanderfolgende Kanten gemeinsam befahren,
    # muessen auf beiden Kanten dieselbe Seite zueinander behalten. Jeder
    # Wechsel ist ein sichtbarer Sprung im Buendel.
    def seite(key, lid, von_knoten):
        slot = edge_slots[key][lid]
        return slot if von_knoten == kanten_anfang(key) else -slot

    seitenwechsel = 0
    geprueft = 0
    for branches in line_branches.values():
        for seq in branches:
            paare = []
            for id_a, id_b in zip(seq, seq[1:]):
                key = tuple(sorted((id_a, id_b)))
                if key in edge_geom:
                    paare.append((key, id_a))
            for (k1, v1), (k2, v2) in zip(paare, paare[1:]):
                gemeinsam = set(edge_slots[k1]) & set(edge_slots[k2])
                for a in gemeinsam:
                    for b in gemeinsam:
                        if rank_by_line[a] >= rank_by_line[b]:
                            continue
                        geprueft += 1
                        d1 = seite(k1, a, v1) - seite(k1, b, v1)
                        d2 = seite(k2, a, v2) - seite(k2, b, v2)
                        if d1 * d2 < 0:
                            seitenwechsel += 1

    # Wege zusammensetzen, Slot-Rampen legen, versetzen, glaetten
    output_lines = []
    slot_change_count = 0
    debug_points = []
    versatz_pro_kante = defaultdict(dict)

    for ln in view_lines:
        branch_paths = []
        for seq in line_branches.get(ln["line_id"], []):
            pts, slots, vertex_edge, vertex_pos = [], [], [], []
            for id_a, id_b in zip(seq, seq[1:]):
                key = tuple(sorted((id_a, id_b)))
                if key not in edge_geom or ln["line_id"] not in edge_slots.get(key, {}):
                    # Kante ohne eigene Geometrie dieser Linie (zwei Knoten praktisch
                    # am selben Ort) - sie wurde nur von einer anderen Linie angelegt
                    continue
                # Geometrie in der festgelegten Orientierung der Kante
                geom = edge_geom[key] if orientierung[key] > 0 else edge_geom[key][::-1]
                forward = (id_a == kanten_anfang(key))
                seg_pts = geom if forward else geom[::-1]
                slot = edge_slots[key][ln["line_id"]]
                slot_signed = slot if forward else -slot
                if pts and slots and abs(slots[-1] - slot_signed) > 1e-9:
                    slot_change_count += 1
                start = 1 if pts else 0
                pts.extend(seg_pts[start:])
                slots.extend([slot_signed] * len(seg_pts[start:]))
                vertex_edge.extend([key] * len(seg_pts[start:]))
                # Index innerhalb der Kante, immer in kanonischer Zaehlrichtung,
                # damit sich die Stuetzpunkte verschiedener Linien vergleichen lassen
                n_seg = len(seg_pts)
                lauf = range(start, n_seg) if forward else range(n_seg - 1 - start, -1, -1)
                vertex_pos.extend(lauf)

            if len(pts) < 2:
                continue

            clean_pts, clean_slots, clean_edges, clean_pos = [], [], [], []
            for p, s, e, ip in zip(pts, slots, vertex_edge, vertex_pos):
                if not clean_pts or abs(p[0] - clean_pts[-1][0]) > 1e-6 or abs(p[1] - clean_pts[-1][1]) > 1e-6:
                    clean_pts.append(p)
                    clean_slots.append(s)
                    clean_edges.append(e)
                    clean_pos.append(ip)
            if len(clean_pts) < 2:
                continue

            # Arclaengen der Kantenwechsel, damit die Rampe an den echten
            # Kantengrenzen gemessen wird
            bogen = cumulative_arclen(clean_pts)
            kanten_grenzen = [bogen[0]]
            for i in range(1, len(clean_edges)):
                if clean_edges[i] != clean_edges[i - 1]:
                    kanten_grenzen.append(bogen[i])
            kanten_grenzen.append(bogen[-1])

            smoothed = ramp_slots(clean_pts, clean_slots, SLOT_TRANSITION_PX, kanten_grenzen)
            offsets = [s * SLOT_SPACING_PX for s in smoothed]
            offset_pts = offset_polyline(clean_pts, offsets)

            # fuer die Abstandspruefung: versetzte Lage je Kante und Stuetzpunkt
            for e, ip, op in zip(clean_edges, clean_pos, offset_pts):
                versatz_pro_kante[(e, ip)][ln["line_id"]] = op

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

    # --- Pruefung: liegen alle Linien einer Kante wirklich nebeneinander? ----
    # Fuer jede Kante mit mindestens zwei Linien wird an jedem Stuetzpunkt der
    # Abstand aller Linienpaare gemessen. Weniger als eine Linienbreite heisst
    # sichtbare Ueberlappung.
    # Ein Spurwechsel unmittelbar am Bahnhof ist zulaessig und ueblich - dort
    # verdeckt ihn der weisse Haltemarker. Geprueft wird deshalb die freie
    # Strecke: der mittlere Teil jeder Kante, ohne die Bereiche an den Enden.
    rand_anteil = RAMPEN_ANTEIL
    ueberlappungen = []
    min_abstand_gesamt = float("inf")
    for (kante, ip), lagen in versatz_pro_kante.items():
        if len(lagen) < 2:
            continue
        n_pts = len(edge_geom[kante])
        if n_pts > 2:
            rel = ip / (n_pts - 1)
            am_bahnhof = rel < rand_anteil or rel > 1.0 - rand_anteil
        else:
            am_bahnhof = True          # zwei Stuetzpunkte sind reine Endpunkte
        ids = sorted(lagen, key=lambda lid: rank_by_line[lid])
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pa, pb = lagen[ids[i]], lagen[ids[j]]
                d = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
                if am_bahnhof:
                    continue
                min_abstand_gesamt = min(min_abstand_gesamt, d)
                if d < LINE_WIDTH_PX:
                    ueberlappungen.append((kante, ids[i], ids[j], d))

    # je Kantenpaar nur den schlimmsten Fall melden
    schlimmste = {}
    for kante, a, b, d in ueberlappungen:
        schluessel = (kante, a, b)
        if schluessel not in schlimmste or d < schlimmste[schluessel]:
            schlimmste[schluessel] = d

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

    # Wo passieren die GEZEICHNETEN Linien den Knoten?
    # Der Marker lag bisher auf der geografischen Position des Halts. Die Linien
    # folgen aber der Trasse, und ein Halt liegt nicht exakt darauf - je nach
    # Datenlage ein paar hundert Meter daneben. Im Bild stand der Marker dann
    # neben seinen eigenen Linien. Massgeblich ist deshalb die versetzte Lage
    # der Linien am Knoten, die die Abstandspruefung ohnehin schon mitfuehrt.
    # Bewusst je Kante getrennt: An einem Sternknoten wie Hamburg Hbf laufen
    # Kanten aus vier Richtungen zusammen. Ueber alle gemittelt ergaebe das
    # einen Marker, der quer ueber leere Flaeche reicht. Massgeblich ist die
    # BREITESTE anliegende Kante - dort ist das Buendel wirklich ein Buendel.
    knotenlagen = defaultdict(dict)   # stop_id -> {kante: {line_id: (x, y)}}
    for key, geom in edge_geom.items():
        anfang = kanten_anfang(key)
        ende = key[1] if anfang == key[0] else key[0]
        for sid_k, idx in ((anfang, 0), (ende, len(geom) - 1)):
            lagen_k = versatz_pro_kante.get((key, idx))
            if lagen_k:
                knotenlagen[sid_k][key] = dict(lagen_k)

    view_line_ids = {l["line_id"] for l in output_lines}
    aeste_je_linie = defaultdict(list)
    for l in output_lines:
        for br in l["branches"]:
            if len(br) >= 2:
                aeste_je_linie[l["line_id"]].append(LineString(br))

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

        # Marker auf die Mitte des Buendels legen und genau so lang machen,
        # dass er alle dort verlaufenden Bahnen ueberdeckt - gemessen an der
        # Markerachse, also quer zur Fahrtrichtung.
        halb = (n_widest - 1) / 2.0 * SLOT_SPACING_PX
        halb_dick = 0.0
        je_kante = knotenlagen.get(sid, {})
        if je_kante:
            alle = [p for lagen_k in je_kante.values() for p in lagen_k.values()]
            x = sum(p[0] for p in alle) / len(alle)
            y = sum(p[1] for p in alle) / len(alle)

            # Vom Schwerpunkt aus den Punkt suchen, der zu ALLEN hier haltenden
            # Linien moeglichst nah liegt. Sonst rutscht der Marker von einem
            # Zulauf herunter, der aus einer anderen Richtung einlaeuft.
            eigene = []
            for lid in lines_here:
                kandidaten = aeste_je_linie.get(lid)
                if kandidaten:
                    eigene.append(min(kandidaten, key=lambda g: g.distance(Point(x, y))))
            if eigene:
                x, y = marker_mittelpunkt((x, y), eigene)
                for g in eigene:
                    q = g.interpolate(g.project(Point(x, y)))
                    alle.append((q.x, q.y))

            achse_rad = math.radians(achse + 90.0)
            ax, ay = math.cos(achse_rad), math.sin(achse_rad)
            # Ausdehnung des Punkthaufens laengs und quer zur Markerachse.
            # Beides nach oben begrenzt: sonst wird der Marker entweder zur
            # langen Nadel ueber leere Flaeche oder - an einem Sternknoten wie
            # Hamburg-Harburg - zu einem grossen weissen Klecks.
            halb = min(max(halb, max(abs((p[0] - x) * ax + (p[1] - y) * ay) for p in alle)),
                       halb + LINE_WIDTH_PX)
            halb_dick = min(max(abs(-(p[0] - x) * ay + (p[1] - y) * ax) for p in alle),
                            MAX_MARKER_DICKE_PX)

        output_stops.append({
            "stop_id": sid,
            "name": s["name"],
            "x": round(x, 1),
            "y": round(y, 1),
            "n_lines": len(lines_here),
            "lines": lines_here,
            "degree": len(incident),
            "bundle_angle_deg": round(achse, 1),
            "bundle_half_len": round(halb, 2),
            "bundle_half_thick": round(halb_dick, 2),
        })

    # --- Markerachsen benachbarter Halte angleichen -------------------------
    # In Ballungsraeumen liegen mehrere Bahnhoefe naeher beieinander als ein
    # Marker lang ist - in Hamburg sind Hbf und Dammtor 4 px auseinander. Stehen
    # ihre Marker dann auch noch in ganz verschiedenen Winkeln, wird daraus ein
    # Knaeuel. Benachbarte Achsen werden deshalb aneinander angeglichen (ueber
    # den doppelten Winkel, weil eine Strecke keine Richtung hat), begrenzt auf
    # eine maessige Drehung, damit kein Marker von seinem Buendel rutscht.
    geglaettet = {}
    for st in output_stops:
        sx2 = sy2 = 0.0
        for nb in output_stops:
            d = math.hypot(nb["x"] - st["x"], nb["y"] - st["y"])
            if d > ACHSEN_NACHBARSCHAFT_PX:
                continue
            gewicht = (nb["n_lines"] + nb["bundle_half_len"]) * (1.0 - d / ACHSEN_NACHBARSCHAFT_PX)
            w2 = 2 * math.radians(nb["bundle_angle_deg"])
            sx2 += gewicht * math.cos(w2)
            sy2 += gewicht * math.sin(w2)
        if abs(sx2) < 1e-12 and abs(sy2) < 1e-12:
            continue
        ziel = math.degrees(math.atan2(sy2, sx2)) / 2.0
        delta = (ziel - st["bundle_angle_deg"] + 90.0) % 180.0 - 90.0
        delta = max(-ACHSEN_MAX_DREHUNG_GRAD, min(ACHSEN_MAX_DREHUNG_GRAD, delta))
        geglaettet[st["stop_id"]] = round(st["bundle_angle_deg"] + delta, 1)
    for st in output_stops:
        if st["stop_id"] in geglaettet:
            st["bundle_angle_deg"] = geglaettet[st["stop_id"]]

    # Selbstpruefung: Sitzt jeder Marker auf seinen Linien?
    # Geprueft wird die tatsaechliche Markerflaeche: das gedrehte Rechteck aus
    # Laenge und Dicke. Nur den Abstand zum Mittelpunkt zu messen waere falsch -
    # eine Linie am Ende eines langen Markers liegt weit vom Mittelpunkt und
    # trotzdem sauber darauf.
    marker_abweichung = []
    for st in output_stops:
        a = math.radians(st["bundle_angle_deg"] + 90.0)
        ax, ay = math.cos(a), math.sin(a)
        hl = st["bundle_half_len"] + LINE_WIDTH_PX * 1.3      # wie in Phase 5
        ht = max(st["bundle_half_thick"] + LINE_WIDTH_PX * 0.6, LINE_WIDTH_PX * 1.05)
        ecken = [(st["x"] + ax * sl * hl - ay * st_ * ht,
                  st["y"] + ay * sl * hl + ax * st_ * ht)
                 for sl, st_ in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
        flaeche = Polygon(ecken)
        for lid in st["lines"]:
            d = min((g.distance(flaeche) for g in aeste_je_linie.get(lid, [])), default=None)
            if d is not None and d > LINE_WIDTH_PX / 2:
                marker_abweichung.append((round(d, 1), st["name"], lid))
    if verbose:
        if marker_abweichung:
            marker_abweichung.sort(reverse=True)
            print(f"    ACHTUNG: {len(marker_abweichung)} Marker liegen nicht auf einer ihrer Linien:")
            for d, nm, lid in marker_abweichung[:8]:
                print(f"      {nm} ({lid}): {d:.1f} px daneben")
        else:
            print(f"    Alle {len(output_stops)} Marker liegen auf ihren Linien")

    if verbose:
        print(f"  Ansicht '{name}': {len(output_lines)} Linien, {len(output_stops)} Halte, "
              f"{len(edge_geom)} Kanten, groesstes Buendel {max_bundle}, "
              f"{slot_change_count} Slot-Wechsel")
        print(f"    Seitenwechsel parallel laufender Linien: {seitenwechsel} von {geprueft} "
              f"geprueften Uebergaengen"
              + (f", {orient_konflikte} Orientierungskonflikte" if orient_konflikte else ""))
        print(f"    Groesster Seitenversatz: {max_versatz:.1f} Spuren "
              f"({max_versatz * SLOT_SPACING_PX:.0f} px von der Streckenmitte)")
        if schlimmste:
            print(f"    UEBERLAPPUNG auf {len(schlimmste)} Linienpaaren "
                  f"(Abstand < {LINE_WIDTH_PX:.0f} px Linienbreite):")
            code = {l["line_id"]: l["code"] for l in view_lines}
            for (kante, a, b), d in sorted(schlimmste.items(), key=lambda kv: kv[1])[:10]:
                n_a = stop_by_id[kante[0]]["name"]
                n_b = stop_by_id[kante[1]]["name"]
                print(f"      {code.get(a, a):6s} / {code.get(b, b):6s} "
                      f"{n_a[:24]:24s} - {n_b[:24]:24s} {d:5.2f} px")
        else:
            print(f"    Keine Ueberlappung: kleinster Abstand zweier Linien "
                  f"{min_abstand_gesamt:.2f} px bei {LINE_WIDTH_PX:.0f} px Linienbreite")
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

    # Bereich der zweiten Seite: die Landesflaeche aus Phase 3, grosszuegig gepuffert
    region_ringe = basemap["region"]["polygons"]
    region_flaeche = unary_union([Polygon(r) for r in region_ringe if len(r) >= 4])
    region_gepuffert = region_flaeche.buffer(INSET_PAD_M)
    ix0, iy0, ix1, iy1 = region_gepuffert.bounds

    inset_scale = (INSET_CANVAS_WIDTH - 2 * INSET_MARGIN_PX) / (ix1 - ix0)
    inset_height = (iy1 - iy0) * inset_scale + 2 * INSET_MARGIN_PX

    def to_px_inset(x, y):
        """EPSG:3034-Meter -> Pixel der zweiten Kartenseite (eigene Zeichenflaeche)."""
        return (INSET_MARGIN_PX + (x - ix0) * inset_scale,
                INSET_MARGIN_PX + (iy1 - y) * inset_scale)

    # alle Halte in der Region, und alle Linien, die dort mindestens zwei bedienen
    inset_stop_ids = {s["stop_id"] for s in graph["stops"]
                      if region_gepuffert.contains(Point(s["px_m"], s["py_m"]))}
    inset_line_ids = set()
    for g in graph["lines"]:
        n_inside = len({sid for seq in g["sequences"] for sid in seq} & inset_stop_ids)
        if n_inside >= 2:
            inset_line_ids.add(g["line_id"])

    print(f"Zweite Seite '{INSET_TITLE}': {INSET_CANVAS_WIDTH:.0f} x {inset_height:.0f} px, "
          f"{inset_scale * 1000:.1f} px/km (Hauptkarte {scale * 1000:.1f}), "
          f"{(ix1 - ix0) / 1000:.0f} x {(iy1 - iy0) / 1000:.0f} km, "
          f"{len(inset_stop_ids)} Halte, {len(inset_line_ids)} Linien")

    views = {
        "main": build_view("main", "Gesamtnetz", lines_raw, graph, stop_by_id,
                           main_line_ids, to_px, scale, debug_edge=debug_edge),
        "inset": build_view("inset", INSET_TITLE, lines_raw, graph, stop_by_id,
                            inset_line_ids, to_px_inset, inset_scale,
                            allowed_stop_ids=inset_stop_ids, debug_edge=debug_edge),
    }

    def basiskarte(transform, mit_namen=True, fenster=None, mit_region=False):
        """
        Laenderflaechen und Grenzlinien in die Pixel einer Ansicht umrechnen.

        fenster: optionales Rechteck in EPSG:3034-Metern. Die zweite Seite zeigt
        nur Nordrhein-Westfalen und seine unmittelbare Umgebung - ganz Europa
        mitzuliefern waere dort sinnlos und blaeht die Datei auf. Alles wird
        deshalb vorher auf dieses Fenster zugeschnitten.
        """
        kasten = box(*fenster) if fenster else None

        def ring_zu_px(ring):
            return [[round(v, 1) for v in transform(x, y)] for x, y in ring]

        def flaechen_zuschneiden(ringe):
            """Ringe auf das Fenster beschneiden und als Pixelringe zurueckgeben."""
            if kasten is None:
                return [ring_zu_px(r) for r in ringe]
            raus = []
            for ring in ringe:
                if len(ring) < 4:
                    continue
                poly = Polygon(ring)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                teil = poly.intersection(kasten)
                if teil.is_empty:
                    continue
                for g in (teil.geoms if hasattr(teil, "geoms") else [teil]):
                    if g.geom_type == "Polygon":
                        raus.append(ring_zu_px(list(g.exterior.coords)))
            return raus

        laender = []
        for c in basemap["countries"]:
            polys = flaechen_zuschneiden(c["polygons"])
            if not polys:
                continue
            eintrag = {"name": c["name"], "polygons": polys}
            if mit_namen:
                lx, ly = transform(c["label_x"], c["label_y"])
                eintrag["label_x"] = round(lx, 1)
                eintrag["label_y"] = round(ly, 1)
            laender.append(eintrag)

        def wege(schluessel):
            raus = []
            for weg in basemap.get(schluessel, []):
                if kasten is None:
                    raus.append(ring_zu_px(weg))
                    continue
                if len(weg) < 2:
                    continue
                teil = LineString(weg).intersection(kasten)
                if teil.is_empty:
                    continue
                for g in (teil.geoms if hasattr(teil, "geoms") else [teil]):
                    if g.geom_type == "LineString" and len(g.coords) >= 2:
                        raus.append(ring_zu_px(list(g.coords)))
            return raus

        ergebnis = {
            "countries": laender,
            "staatsgrenzen": wege("staatsgrenzen"),
            "bundeslaender": wege("bundeslaender"),
        }
        if mit_region:
            ergebnis["region"] = {
                "name": basemap["region"]["name"],
                "polygons": flaechen_zuschneiden(basemap["region"]["polygons"]),
            }
        return ergebnis

    # Rechteck auf der Hauptkarte, das den Bereich der zweiten Seite markiert
    src_x0, src_y0 = to_px(ix0, iy1)
    src_x1, src_y1 = to_px(ix1, iy0)

    output = {
        "meta": {
            "projected_crs": PROJECTED_CRS,
            "line_width_px": LINE_WIDTH_PX,
            "slot_spacing_px": SLOT_SPACING_PX,
            "simplify_tolerance_px": SIMPLIFY_TOLERANCE_PX,
            "slot_transition_px": SLOT_TRANSITION_PX,
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
            "inset": basiskarte(to_px_inset, mit_namen=False,
                                fenster=(ix0, iy0, ix1, iy1), mit_region=True),
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
