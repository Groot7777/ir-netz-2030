#!/usr/bin/env python3
"""
Phase 4c - Unabhaengige Abstandspruefung der fertigen Liniengeometrie.

Die Pruefung in 04_bundling.py vergleicht Linien nur, wenn sie sich dieselbe
Kante teilen. Befahren zwei Linien denselben Streckenabschnitt mit
unterschiedlicher Kantenaufteilung - etwa weil eine von ihnen an einem Halt
nicht haelt und dort keinen Knoten hat - sieht sie das nicht.

Dieses Skript prueft deshalb rein geometrisch: Es tastet jede Linie dicht ab
und misst den Abstand zu jeder anderen Linie. Laengere Abschnitte unterhalb
einer Linienbreite sind Ueberlappungen; ein einzelner Beruehrpunkt ist eine
normale Kreuzung und wird nicht gemeldet.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

BUNDLED_PATH = Path("data/04_bundled.json")

ABTASTUNG_PX = 3.0        # Schrittweite beim Abtasten einer Linie
MIN_UEBERLAPPUNG_PX = 25.0  # kuerzere Beruehrungen gelten als Kreuzung, nicht als Ueberlappung


def abtasten(pts, schritt):
    """Polylinie in gleichmaessigen Abstaenden abtasten."""
    ls = LineString(pts)
    n = max(int(ls.length / schritt), 1)
    return [ls.interpolate(i * ls.length / n) for i in range(n + 1)], ls.length / n


def main():
    data = json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))
    lw = data["meta"]["line_width_px"]
    spur = data["meta"]["slot_spacing_px"]

    print(f"Linienbreite {lw} px, Spurabstand {spur} px")
    print(f"Gemeldet werden Ueberlappungen laenger als {MIN_UEBERLAPPUNG_PX:.0f} px\n")

    gesamt_treffer = 0
    for seite, view in data["views"].items():
        code = {l["line_id"]: l["code"] for l in view["lines"]}
        # jede Ast-Polylinie einzeln, mit Zuordnung zur Linie
        aeste = []
        for l in view["lines"]:
            for br in l["branches"]:
                if len(br) >= 2:
                    aeste.append((l["line_id"], LineString(br)))

        baum = STRtree([g for _, g in aeste])
        besitzer = [lid for lid, _ in aeste]

        befunde = defaultdict(float)   # (LinieA, LinieB) -> laengste Ueberlappung
        stellen = {}

        for idx_a, (lid_a, geom_a) in enumerate(aeste):
            punkte, schrittlaenge = abtasten(list(geom_a.coords), ABTASTUNG_PX)
            # Kandidaten in der Naehe
            nah = baum.query(geom_a.buffer(lw))
            for idx_b in nah:
                lid_b = besitzer[idx_b]
                if lid_b == lid_a:
                    continue
                if (code.get(lid_a, lid_a), code.get(lid_b, lid_b)) > (code.get(lid_b, lid_b), code.get(lid_a, lid_a)):
                    continue   # jedes Paar nur einmal
                geom_b = aeste[idx_b][1]
                lauf = 0.0
                bester_lauf = 0.0
                beste_stelle = None
                for p in punkte:
                    if geom_b.distance(p) < lw:
                        lauf += schrittlaenge
                        if lauf > bester_lauf:
                            bester_lauf = lauf
                            beste_stelle = p
                    else:
                        lauf = 0.0
                if bester_lauf > MIN_UEBERLAPPUNG_PX:
                    schluessel = (code.get(lid_a, lid_a), code.get(lid_b, lid_b))
                    if bester_lauf > befunde[schluessel]:
                        befunde[schluessel] = bester_lauf
                        stellen[schluessel] = beste_stelle

        # Halte fuer die Ortsangabe
        halte = [(s["name"], Point(s["x"], s["y"])) for s in view["stops"]]

        def naechster_halt(p):
            return min(halte, key=lambda h: h[1].distance(p))[0]

        print(f"--- Ansicht '{seite}' ---")
        if not befunde:
            print("  Keine Ueberlappung gefunden.\n")
            continue
        gesamt_treffer += len(befunde)
        for (a, b), laenge in sorted(befunde.items(), key=lambda kv: -kv[1]):
            ort = naechster_halt(stellen[(a, b)])
            print(f"  {a:6s} / {b:6s} ueberlappen auf {laenge:6.0f} px  bei {ort}")
        print()

    print(f"Summe: {gesamt_treffer} ueberlappende Linienpaare")


if __name__ == "__main__":
    main()
