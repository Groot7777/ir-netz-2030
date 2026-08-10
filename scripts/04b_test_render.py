#!/usr/bin/env python3
"""
Phase 4 - Testrender.

Zeichnet nur eine Handvoll Linien, damit sich die Buendelung pruefen laesst,
bevor alle 32 auf der Karte sind. Kein Feintuning der Darstellung - das ist
Phase 5. Hier zaehlt nur: Laufen die Linien sauber parallel? Sind die
Uebergaenge an den Knoten luecken- und zackenfrei?

Aufruf:
    python3 scripts/04b_test_render.py RE40 S10 S3 S30
    python3 scripts/04b_test_render.py RE32 RE90 RB37 --out data/test_duesseldorf.html
"""
import argparse
import json
from pathlib import Path

BUNDLED_PATH = Path("data/04_bundled.json")


def build_svg(data, codes, padding=80.0, center_name=None, span=None, zoom=1.0, view="inset"):
    ansicht = data["views"][view]
    lines = [l for l in ansicht["lines"] if l["code"] in codes]
    if not lines:
        raise SystemExit(f"Keine Linien gefunden fuer: {codes}")

    line_ids = {l["line_id"] for l in lines}
    stops = [s for s in ansicht["stops"] if any(lid in line_ids for lid in s["lines"])]

    if center_name:
        # Ausschnitt um einen bestimmten Halt herum, um die Buendelung im Detail zu pruefen
        match = [s for s in ansicht["stops"] if center_name.lower() in s["name"].lower()]
        if not match:
            raise SystemExit(f"Halt nicht gefunden: {center_name}")
        cx, cy = match[0]["x"], match[0]["y"]
        half = (span or 400.0) / 2.0
        min_x, max_x = cx - half, cx + half
        min_y, max_y = cy - half, cy + half
    else:
        xs = [p[0] for l in lines for b in l["branches"] for p in b]
        ys = [p[1] for l in lines for b in l["branches"] for p in b]
        min_x, max_x = min(xs) - padding, max(xs) + padding
        min_y, max_y = min(ys) - padding, max(ys) + padding
    vw, vh = max_x - min_x, max_y - min_y

    lw = data["meta"]["line_width_px"]

    parts = []

    # Laenderflaechen als zurueckhaltender Hintergrund
    for c in ansicht.get("countries", []):
        d_attr = "".join(
            "M " + " ".join(f"{x:.1f},{y:.1f}" for x, y in ring) + " Z "
            for ring in c["polygons"]
        )
        parts.append(f'<path d="{d_attr}" fill="#ececec" stroke="#ffffff" stroke-width="1.5"/>')

    # Linien
    for l in lines:
        for branch in l["branches"]:
            d_attr = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in branch)
            parts.append(
                f'<path d="{d_attr}" fill="none" stroke="{l["color"]}" stroke-width="{lw}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )

    # Schrift gegen den Zoom normieren, damit Beschriftung lesbar gross bleibt
    # und nicht die Geometrie ueberdeckt, die wir eigentlich pruefen wollen.
    fs = 9.0 / zoom
    lfs = 12.0 / zoom

    # Halte als weisse Kreise (Phase-5-Darstellung folgt spaeter)
    for s in stops:
        r = lw * 0.75
        parts.append(
            f'<circle cx="{s["x"]}" cy="{s["y"]}" r="{r:.1f}" fill="#ffffff" '
            f'stroke="#333333" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="{s["x"] + r + 3:.1f}" y="{s["y"] + fs * 0.35:.1f}" font-size="{fs:.2f}" '
            f'fill="#444" font-family="sans-serif">{s["name"]}</text>'
        )

    legend = []
    for i, l in enumerate(lines):
        ly = min_y + (14 + i * 14) / zoom
        legend.append(
            f'<line x1="{min_x + 10 / zoom:.1f}" y1="{ly:.1f}" x2="{min_x + 34 / zoom:.1f}" y2="{ly:.1f}" '
            f'stroke="{l["color"]}" stroke-width="{lw / zoom:.2f}" stroke-linecap="round"/>'
            f'<text x="{min_x + 40 / zoom:.1f}" y="{ly + lfs * 0.35:.1f}" font-size="{lfs:.2f}" '
            f'font-family="sans-serif" fill="#222">{l["code"]} — {l["name"]}</text>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x:.1f} {min_y:.1f} {vw:.1f} {vh:.1f}" '
        f'width="{vw * zoom:.0f}" height="{vh * zoom:.0f}" style="background:#f7f7f7">'
        + "".join(parts) + "".join(legend) + "</svg>"
    )
    return svg, len(lines), len(stops)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="+", help="Liniennummern, z.B. RE40 S10 S3 S30")
    ap.add_argument("--out", default="data/04_test_render.html")
    ap.add_argument("--center", help="Halt, um den herum gezoomt wird (Teilstring genuegt)")
    ap.add_argument("--span", type=float, default=400.0, help="Kantenlaenge des Ausschnitts in px")
    ap.add_argument("--zoom", type=float, default=1.0, help="Vergroesserungsfaktor der Darstellung")
    ap.add_argument("--view", default="inset", choices=["main", "inset"], help="Kartenansicht")
    args = ap.parse_args()

    data = json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))
    svg, n_lines, n_stops = build_svg(
        data, set(args.codes), center_name=args.center, span=args.span, zoom=args.zoom, view=args.view
    )

    html = (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        f"<title>Testrender {' '.join(args.codes)}</title></head>"
        '<body style="margin:0;background:#f7f7f7">' + svg + "</body></html>"
    )
    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    print(f"{n_lines} Linien, {n_stops} Halte -> {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
