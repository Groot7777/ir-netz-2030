#!/usr/bin/env python3
"""
Phase 4d - Ursachensuche zu den Befunden aus 04c.

04c meldet, DASS sich zwei Linien ueberlappen. Dieses Skript sagt, WARUM:
Es sucht zu jedem ueberlappenden Abschnitt die beiden naechstgelegenen Halte
und prueft, ob die beiden Linien dort ueberhaupt dieselbe Graphkante befahren.

  "Kante geteilt"   -> Slot-Vergabe oder Rampe ist schuld
  "Kante ohne beide"-> die Kante gehoert nur einer der beiden Linien
  "KEINE Kante"     -> beide fahren denselben Korridor auf getrennten Kanten
  "SELBE STATION"   -> Ein- und Auslauffaecher an einem Knoten
"""
import json
from pathlib import Path

from shapely.geometry import LineString, Point

BUNDLED_PATH = Path("data/04_bundled.json")
GRAPH_PATH = Path("data/02_graph.json")

ABTASTUNG_PX = 3.0
MIN_UEBERLAPPUNG_PX = 25.0


def main():
    b = json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))
    g = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    lw = b["meta"]["line_width_px"]
    kanten = {frozenset((e["stop_a"], e["stop_b"])): set(e["lines"]) for e in g["edges"]}
    lid2code = {l["line_id"]: l["code"] for l in g["lines"]}

    for seite, v in b["views"].items():
        code = {l["line_id"]: l["code"] for l in v["lines"]}
        halte = [(s["stop_id"], s["name"], Point(s["x"], s["y"])) for s in v["stops"]]
        codes = sorted(set(code.values()))

        def aeste(c):
            return [LineString(br) for l in v["lines"] if code[l["line_id"]] == c
                    for br in l["branches"] if len(br) >= 2]

        print(f"=== Ansicht '{seite}' ===")
        for i, a_code in enumerate(codes):
            for b_code in codes[i + 1:]:
                for ga in aeste(a_code):
                    for gb in aeste(b_code):
                        n = max(int(ga.length / ABTASTUNG_PX), 1)
                        lauf = []
                        for k in range(n + 1):
                            p = ga.interpolate(k * ga.length / n)
                            if gb.distance(p) < lw:
                                lauf.append(p)
                            else:
                                melde(a_code, b_code, lauf, halte, kanten, lid2code)
                                lauf = []
                        melde(a_code, b_code, lauf, halte, kanten, lid2code)


def melde(a_code, b_code, lauf, halte, kanten, lid2code):
    laenge = len(lauf) * ABTASTUNG_PX
    if laenge <= MIN_UEBERLAPPUNG_PX:
        return
    s1 = min(halte, key=lambda h: h[2].distance(lauf[0]))
    s2 = min(halte, key=lambda h: h[2].distance(lauf[-1]))
    ls = kanten.get(frozenset((s1[0], s2[0])))
    if s1[0] == s2[0]:
        grund = "SELBE STATION (Faecher am Knoten)"
    elif ls is None:
        grund = "KEINE Kante"
    elif {a_code, b_code} <= {lid2code.get(x, x) for x in ls}:
        grund = "Kante geteilt"
    else:
        grund = "Kante ohne beide: " + ",".join(sorted(lid2code.get(x, x) for x in ls))
    print(f"  {a_code:6s}/{b_code:6s} {laenge:5.0f}px  {s1[1]} -> {s2[1]}   [{grund}]")


if __name__ == "__main__":
    main()
