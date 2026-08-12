#!/usr/bin/env python3
"""
Synchronisiert LINE_PATHS (Kartenlinien-Geometrie) in der App komplett aus
der aktuellen KML — die App-Geometrien waren durchgehend stark vereinfacht
(nur ca. 25-30% der KML-Punktdichte je Linie), nicht nur einzelne Linien.

Schlüssel-Mapping: die KML nutzt fuer manche Linien 'style_lineXXX' als
styleUrl, fuer andere nur 'lineXXX' (Uneinheitlichkeit im Original). Die
App verwendet je Linie IHRE EIGENE bestehende Schluessel-Konvention (von
JS-Code ueber BASE_TO_STYLE referenziert) — deshalb wird die KML-Geometrie
ueber den OHNE 'style_'-Praefix normalisierten Namen zugeordnet, aber
unter dem in der App bereits vorhandenen Schluessel gespeichert.

lineRE90b_groningen/_norddeich (App-eigene Ast-Varianten ohne KML-
Gegenstueck) bleiben unveraendert, da keine Quelle dafuer existiert.

Nutzung:
    python3 tools/sync_line_paths.py --kml <pfad>
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from htmldata import extract_const, replace_const  # noqa: E402


def norm_style(s):
    return s[len("style_") :] if s.startswith("style_") else s


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", default="app/RENetz2030_Fahrplanauskunft.html")
    ap.add_argument("--kml", required=True)
    args = ap.parse_args()

    html_path = pathlib.Path(args.html)
    html_text = html_path.read_text(encoding="utf-8")
    app_paths = extract_const(html_text, "LINE_PATHS")

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    placemark_pat = re.compile(r"<Placemark>(.*?)</Placemark>", re.DOTALL)
    style_pat = re.compile(r"<styleUrl>#(\w+)</styleUrl>")
    coords_pat = re.compile(r"<LineString>.*?<coordinates>(.*?)</coordinates>", re.DOTALL)

    kml_paths_by_norm = {}
    for block in placemark_pat.finditer(kml_text):
        b = block.group(1)
        cm = coords_pat.search(b)
        if not cm:
            continue
        sm = style_pat.search(b)
        if not sm:
            continue
        pts = []
        for c in cm.group(1).strip().split(" "):
            if not c:
                continue
            lon, lat, _alt = c.split(",")
            pts.append([round(float(lon), 5), round(float(lat), 5)])
        kml_paths_by_norm[norm_style(sm.group(1))] = pts

    app_by_norm = {norm_style(k): k for k in app_paths}

    updated, unchanged, no_source = [], [], []
    for norm_key, app_key in app_by_norm.items():
        if norm_key not in kml_paths_by_norm:
            no_source.append(app_key)
            continue
        new_pts = kml_paths_by_norm[norm_key]
        if app_paths[app_key] == new_pts:
            unchanged.append(app_key)
        else:
            old_n = len(app_paths[app_key])
            app_paths[app_key] = new_pts
            updated.append((app_key, old_n, len(new_pts)))

    new_html = replace_const(html_text, "LINE_PATHS", app_paths)
    html_path.write_text(new_html, encoding="utf-8")

    print(f"{len(updated)} Linien aktualisiert, {len(unchanged)} bereits identisch, {len(no_source)} ohne KML-Quelle (unveraendert)")
    for key, old_n, new_n in updated:
        print(f"  {key:22s} {old_n:5d} -> {new_n:5d} Punkte")
    if no_source:
        print("Ohne KML-Quelle:", no_source)


if __name__ == "__main__":
    main()
