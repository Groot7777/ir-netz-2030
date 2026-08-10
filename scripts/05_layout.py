#!/usr/bin/env python3
"""
Phase 5 - Darstellung: Layout berechnen.

Legt fest, WO alles gezeichnet wird (die eigentliche Zeichnung macht Phase 6):
- Einstufung der Halte: normaler Halt (Kapsel quer ueber das Buendel) oder
  Knotenbahnhof (groesseres Stadion mit fettem Namen)
- Kollisionsfreie Platzierung der Haltenamen: vier Himmelsrichtungen probieren,
  sonst protokollieren statt ueberlappen
- Liniennummern-Badges entlang der Strecke und kurz vor Verzweigungen
- Legendeneintraege mit Farbe, Nummer und Endpunkten

Bildsprache orientiert sich am NRW-Regionalverkehrsplan: weisse Kapseln quer
ueber das Buendel, grosse Knoten als weisses Stadion, Liniennummern in
abgerundeten Badges in Linienfarbe.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

BUNDLED_PATH = Path("data/04_bundled.json")
OUTPUT_PATH = Path("data/05_layout.json")

# --- Schriftgroessen und Marker (in Karten-Pixeln) --------------------------
LABEL_FONT_PX = 9.0            # normaler Haltename
NODE_FONT_PX = 12.5            # Knotenbahnhof
COUNTRY_FONT_PX = 34.0         # Laendername am Rand
BADGE_FONT_PX = 9.0

LABEL_GAP_PX = 3.0             # Abstand Marker -> Beschriftung
BADGE_PAD_X = 4.0              # Innenabstand im Badge
BADGE_HEIGHT_PX = 13.0

NODE_MIN_LINES = 3             # ab so vielen Linien gilt ein Halt als Knotenbahnhof

BADGE_INTERVAL_PX = 430.0      # Regelabstand der Liniennummern entlang der Strecke
BADGE_END_INSET_PX = 26.0      # Abstand vom Linienende fuer das Endbadge
BADGE_MIN_BRANCH_GAP = 90.0    # Mindestabstand zwischen zwei Badges derselben Linie

# Zoomstufen, ab denen eine Beschriftung eingeblendet wird (Phase 6 wertet das aus)
TIER_ALWAYS = 0                # Knotenbahnhoefe und Endpunkte
TIER_MEDIUM = 1                # Halte mit mehreren Linien
TIER_DETAIL = 2                # alle uebrigen

# Zeichenbreiten relativ zur Schriftgroesse, grob nach Buchstabenform gruppiert.
# Reicht fuer die Kollisionspruefung; eine echte Font-Metrik waere hier
# ueberdimensioniert, weil das Ergebnis ohnehin nur ~1 px genau sein muss.
_NARROW = set("iljtfr.,;:!|()[]{}'-I ")
_WIDE = set("mwMW@")
_UPPER = set("ABCDEFGHJKLNOPQRSTUVXYZÄÖÜ0123456789")


def display_name(name):
    """
    Kartenbeschriftung kuerzen.

    Auf Verkehrskarten steht durchweg "Hbf" statt "Hauptbahnhof" - das spart
    in dichten Bereichen erheblich Platz. Der volle Name bleibt fuer Suche und
    Infofeld erhalten.
    """
    return (name.replace("Hauptbahnhof", "Hbf")
                .replace("hauptbahnhof", "hbf"))


def estimate_text_width(text, font_px, bold=False):
    """Textbreite abschaetzen, ohne Font-Engine."""
    total = 0.0
    for ch in text:
        if ch in _NARROW:
            total += 0.30
        elif ch in _WIDE:
            total += 0.86
        elif ch in _UPPER:
            total += 0.62
        else:
            total += 0.52
    return total * font_px * (1.06 if bold else 1.0)


class CollisionGrid:
    """Einfaches Raster fuer schnelle Ueberlappungspruefung achsenparalleler Rechtecke."""

    def __init__(self, cell=40.0):
        self.cell = cell
        self.cells = defaultdict(list)

    def _keys(self, box):
        x0, y0, x1, y1 = box
        for gx in range(int(math.floor(x0 / self.cell)), int(math.floor(x1 / self.cell)) + 1):
            for gy in range(int(math.floor(y0 / self.cell)), int(math.floor(y1 / self.cell)) + 1):
                yield (gx, gy)

    def collides(self, box):
        x0, y0, x1, y1 = box
        for key in self._keys(box):
            for bx0, by0, bx1, by1 in self.cells[key]:
                if x0 < bx1 and bx0 < x1 and y0 < by1 and by0 < y1:
                    return True
        return False

    def add(self, box):
        for key in self._keys(box):
            self.cells[key].append(box)


def marker_geometry(stop, line_width):
    """
    Groesse des Haltemarkers.

    Der Marker liegt QUER ueber das Buendel: seine lange Achse steht senkrecht
    zur Fahrtrichtung und ueberdeckt alle parallelen Bahnen.
    """
    is_node = stop["n_lines"] >= NODE_MIN_LINES
    half = stop["bundle_half_len"]
    if is_node:
        length = 2 * half + line_width * 2.6
        thickness = line_width * 2.1
    else:
        length = 2 * half + line_width * 1.5
        thickness = line_width * 1.45
    # lange Achse steht senkrecht zur Buendelrichtung
    angle = stop["bundle_angle_deg"] + 90.0
    return {
        "is_node": is_node,
        "length": round(length, 2),
        "thickness": round(thickness, 2),
        "angle_deg": round(angle, 1),
    }


def marker_extent(marker):
    """Halbe Ausdehnung des gedrehten Markers in X und Y (fuer Kollision und Labelabstand)."""
    a = math.radians(marker["angle_deg"])
    hl, ht = marker["length"] / 2.0, marker["thickness"] / 2.0
    ex = abs(hl * math.cos(a)) + abs(ht * math.sin(a))
    ey = abs(hl * math.sin(a)) + abs(ht * math.cos(a))
    return ex, ey


# Acht Himmelsrichtungen, in der Reihenfolge ihrer Beliebtheit.
# Waagerecht zuerst (liest sich am besten), dann senkrecht, dann diagonal.
_DIRECTIONS = [
    ("E", 1, 0), ("W", -1, 0), ("N", 0, -1), ("S", 0, 1),
    ("NE", 1, -1), ("SE", 1, 1), ("NW", -1, -1), ("SW", -1, 1),
]
# Entfernungsstufen: erst dicht am Halt, dann weiter weg (dann mit Bezugslinie)
_DISTANCE_STEPS = [1.0, 2.0, 3.4, 5.0]


def label_candidates(x, y, ex, ey, text_w, text_h):
    """
    Kandidatenpositionen um einen Halt herum: acht Richtungen in mehreren
    Entfernungen. Erst werden alle Richtungen dicht am Halt probiert, danach
    dieselben Richtungen weiter aussen - dort bekommt die Beschriftung eine
    duenne Bezugslinie, damit die Zuordnung eindeutig bleibt.

    Rueckgabe je Kandidat: (Richtung, Anker, x, y, Box, Bezugslinie noetig).
    """
    half_h = text_h / 2.0
    for step_i, step in enumerate(_DISTANCE_STEPS):
        needs_leader = step_i > 0
        for name, sx, sy in _DIRECTIONS:
            ox = (ex + LABEL_GAP_PX) * step * sx
            oy = (ey + LABEL_GAP_PX) * step * sy

            if sx > 0:
                anchor, ax = "start", x + ox
                bx0, bx1 = ax, ax + text_w
            elif sx < 0:
                anchor, ax = "end", x + ox
                bx0, bx1 = ax - text_w, ax
            else:
                anchor, ax = "middle", x
                bx0, bx1 = x - text_w / 2, x + text_w / 2

            if sy == 0:
                ay = y + half_h * 0.72
                by0, by1 = y - half_h, y + half_h
            elif sy < 0:
                ay = y + oy
                by0, by1 = ay - text_h, ay
            else:
                ay = y + oy + text_h * 0.82
                by0, by1 = ay - text_h, ay

            yield (name, anchor, ax, ay, (bx0, by0, bx1, by1), needs_leader)


def importance(stop):
    """Reihenfolge der Beschriftung: wichtige Halte bekommen zuerst einen Platz."""
    score = stop["n_lines"] * 100
    if stop["degree"] <= 1:
        score += 60                      # Endbahnhof
    name = stop["name"]
    if "Hauptbahnhof" in name or "Hbf" in name:
        score += 25
    return -score, len(name), name


def tier_for(stop):
    if stop["n_lines"] >= NODE_MIN_LINES or stop["degree"] <= 1:
        return TIER_ALWAYS
    if stop["n_lines"] >= 2:
        return TIER_MEDIUM
    return TIER_DETAIL


def polyline_length(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def point_at_arclen(pts, target):
    """Punkt und Richtung an einer bestimmten Bogenlaenge der Polylinie."""
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg <= 1e-9:
            continue
        if acc + seg >= target:
            t = (target - acc) / seg
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        acc += seg
    return pts[-1]


def luminance(hex_color):
    """Wahrgenommene Helligkeit, um zwischen weisser und schwarzer Badge-Schrift zu waehlen."""
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def layout_view(view, line_width, grid_seed_boxes=None):
    """Marker, Beschriftungen und Badges einer Ansicht platzieren."""
    grid = CollisionGrid()
    for box in (grid_seed_boxes or []):
        grid.add(box)

    stops = sorted(view["stops"], key=importance)

    # 1. Alle Marker belegen zuerst Platz - Beschriftung darf nie einen Halt verdecken
    markers = {}
    for s in stops:
        m = marker_geometry(s, line_width)
        markers[s["stop_id"]] = m
        ex, ey = marker_extent(m)
        grid.add((s["x"] - ex, s["y"] - ey, s["x"] + ex, s["y"] + ey))

    # 2. Beschriftungen in Reihenfolge der Wichtigkeit platzieren
    placed_labels = []
    unplaced = []
    for s in stops:
        m = markers[s["stop_id"]]
        is_node = m["is_node"]
        font = NODE_FONT_PX if is_node else LABEL_FONT_PX
        text = display_name(s["name"])
        text_w = estimate_text_width(text, font, bold=is_node)
        text_h = font * 1.02
        ex, ey = marker_extent(m)

        chosen = None
        for direction, anchor, ax, ay, box, needs_leader in label_candidates(
                s["x"], s["y"], ex, ey, text_w, text_h):
            padded = (box[0] - 1.0, box[1] - 0.6, box[2] + 1.0, box[3] + 0.6)
            if not grid.collides(padded):
                grid.add(padded)
                chosen = (direction, anchor, ax, ay, box, needs_leader)
                break

        if chosen is None:
            unplaced.append(s["name"])
            continue

        direction, anchor, ax, ay, box, needs_leader = chosen
        entry = {
            "stop_id": s["stop_id"],
            "text": text,
            "x": round(ax, 1),
            "y": round(ay, 1),
            "anchor": anchor,
            "direction": direction,
            "font_px": font,
            "bold": is_node,
            "tier": tier_for(s),
        }
        if needs_leader:
            # Bezugslinie vom Halt zur naechstgelegenen Ecke/Kante des Textfeldes
            entry["leader"] = [
                round(min(max(s["x"], box[0]), box[2]), 1),
                round(min(max(s["y"], box[1]), box[3]), 1),
            ]
        placed_labels.append(entry)

    # 3. Liniennummern-Badges: regelmaessig entlang der Strecke und an den Enden
    badges = []
    for line in view["lines"]:
        text = line["code"]
        bw = estimate_text_width(text, BADGE_FONT_PX, bold=True) + 2 * BADGE_PAD_X
        text_fill = "#ffffff" if luminance(line["color"]) < 0.62 else "#1a1a1a"
        for branch in line["branches"]:
            total = polyline_length(branch)
            if total < 2 * BADGE_END_INSET_PX:
                continue
            # Enden zuerst: dort ist die Liniennummer am wichtigsten
            targets = [BADGE_END_INSET_PX, total - BADGE_END_INSET_PX]
            n_mid = int(total // BADGE_INTERVAL_PX)
            for k in range(1, n_mid + 1):
                targets.append(total * k / (n_mid + 1))
            targets.sort()

            last_placed = -1e9
            for t in targets:
                if t - last_placed < BADGE_MIN_BRANCH_GAP:
                    continue
                px, py = point_at_arclen(branch, t)
                box = (px - bw / 2 - 1, py - BADGE_HEIGHT_PX / 2 - 1,
                       px + bw / 2 + 1, py + BADGE_HEIGHT_PX / 2 + 1)
                if grid.collides(box):
                    continue
                grid.add(box)
                last_placed = t
                badges.append({
                    "line_id": line["line_id"],
                    "text": text,
                    "x": round(px, 1),
                    "y": round(py, 1),
                    "w": round(bw, 1),
                    "h": BADGE_HEIGHT_PX,
                    "fill": line["color"],
                    "text_fill": text_fill,
                })

    return {
        "markers": [{"stop_id": sid, **m} for sid, m in markers.items()],
        "labels": placed_labels,
        "badges": badges,
        "unplaced_labels": unplaced,
    }


def main():
    data = json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))
    line_width = data["meta"]["line_width_px"]
    inset = data["meta"]["inset"]

    # Ausschnittrahmen samt Titel und der Hinweis am markierten Quellbereich
    # duerfen von Beschriftungen der Hauptkarte nicht ueberdeckt werden.
    sx, sy, sw, _sh = inset["source_rect"]
    hint_w = estimate_text_width("vergrößert siehe Ausschnitt", 15.0)
    seed = [
        (inset["x"] - 6, inset["y"] - 34, inset["x"] + inset["width"] + 6,
         inset["y"] + inset["height"] + 6),
        (sx + sw / 2 - hint_w / 2 - 3, sy - 24, sx + sw / 2 + hint_w / 2 + 3, sy - 2),
    ]

    result = {"views": {}}
    for name, view in data["views"].items():
        seed_boxes = seed if name == "main" else None
        layout = layout_view(view, line_width, grid_seed_boxes=seed_boxes)
        result["views"][name] = layout
        n_nodes = sum(1 for m in layout["markers"] if m["is_node"])
        print(f"Ansicht '{name}': {len(layout['markers'])} Marker "
              f"({n_nodes} Knotenbahnhoefe), {len(layout['labels'])} Beschriftungen platziert, "
              f"{len(layout['badges'])} Liniennummern")
        if layout["unplaced_labels"]:
            print(f"  {len(layout['unplaced_labels'])} Halte ohne Platz fuer eine Beschriftung:")
            for nm in layout["unplaced_labels"]:
                print(f"    - {nm}")

    # Legende: alle Linien beider Ansichten, ohne Dopplung
    legend = []
    seen = set()
    for view in data["views"].values():
        for line in view["lines"]:
            if line["line_id"] in seen:
                continue
            seen.add(line["line_id"])
            # Der Name hat die Form "RE2 Duesseldorf-Osnabrueck" -> Endpunkte abtrennen
            endpoints = line["name"][len(line["code"]):].strip()
            legend.append({
                "line_id": line["line_id"],
                "code": line["code"],
                "color": line["color"],
                "endpoints": endpoints,
                "in_inset_only": line["code"].startswith("S"),
            })
    legend.sort(key=lambda l: (l["code"][0], int("".join(c for c in l["code"] if c.isdigit()) or 0),
                               l["code"]))
    result["legend"] = legend
    result["meta"] = {
        "label_font_px": LABEL_FONT_PX,
        "node_font_px": NODE_FONT_PX,
        "country_font_px": COUNTRY_FONT_PX,
        "badge_font_px": BADGE_FONT_PX,
        "node_min_lines": NODE_MIN_LINES,
    }

    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nLegende: {len(legend)} Linien")
    print(f"Ausgabe geschrieben nach {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
