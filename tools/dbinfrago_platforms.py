#!/usr/bin/env python3
"""
Holt Bahnsteig-Nettobaulängen von dbinfrago.com für eine feste Liste
wichtiger Knotenbahnhöfe, bei denen die OSM/Overpass-Daten unzuverlässig
oder fehlend waren (siehe data/platform_conflicts.md).

WICHTIG: dbinfrago.com weist selbst darauf hin, dass die "Nettobaulänge"
NICHT für die Zugplanung geeignet ist -- maßgeblich ist die "Bahnsteig-
nutzlänge" (abhängig von Signalstandorten, separat beim Betreiber zu
erfragen). Die hier geholten Werte sind trotzdem eine sehr viel
verlässlichere Obergrenze als die OSM-Schätzung und werden als
"amtliche Obergrenze, keine exakte Nutzlänge" gekennzeichnet.

Nutzung:
    python3 tools/dbinfrago_platforms.py --out data/dbinfrago_platforms.json
"""
import argparse
import json
import pathlib
import re
import subprocess
import time

STATIONS = {
    "Berlin Hbf": "Berlin-Hauptbahnhof-12669788",
    "Berlin Hbf (tief)": "Berlin-Hauptbahnhof-12669788",
    "Bochum Hbf": "Bochum-Hbf-12675848",
    "Lübeck Hbf": "Luebeck-Hbf-12670852",
    "Duisburg Hbf": "Duisburg-Hbf-12667688",
    "Kassel-Wilhelmshöhe": "Kassel-Wilhelmshoehe-12672286",
    "Erfurt Hbf": "Erfurt-Hbf-12677056",
    "Kiel Hbf": "Kiel-Hbf-12673586",
    "Neuss Hbf": "Neuss-Hbf-12668648",
    "Freiberg (Sachs)": "Freiberg-Sachs--12668092",
    "Chemnitz Hbf": "Chemnitz-Hbf-12673382",
    "Berlin Südkreuz": "Berlin-Suedkreuz-12668128",
    "Hamburg-Elbbrücken": "Elbbruecken-12671036",
    "Hamburg-Harburg": "Hamburg-Harburg-12668078",
    "Berlin-Spandau": "Berlin-Spandau-12668216",
    "Münster (Westf) Hbf": "Muenster-Westf-Hbf-12668946",
    "Osnabrück Hbf": "Osnabrueck-Hbf-12668138",
    "Pasewalk": "Pasewalk-12677978",
    "Eberswalde Hbf": "Eberswalde-Hbf-12668622",
    "Hagenow Land": "Hagenow-Land-12675542",
    "Zwickau Hbf": "Zwickau-Sachs-Hbf-12677206",
    "Bad Kleinen": "Bad-Kleinen-12675404",
    "Plattling": "Plattling-12671320",
    "Oldenburg (Oldb) Hbf": "Oldenburg-Oldb-Hbf-12668824",
    # bereits per WebFetch geprüft, hier zur Vollständigkeit mit aufgenommen:
    "Düsseldorf Hbf": "Duesseldorf-Hbf-12668428",
}

BASE = "https://www.dbinfrago.com/web/bahnhoefe/leistungen/stationsnutzung/stationshalt/stationsausstattung/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

ROW_RE = re.compile(
    r"Bahnsteigabschnittsmarkierungen\s*\|.*?<p>(.*?)</p>", re.S
)


def fetch_html(slug):
    r = subprocess.run(
        ["curl", "-sS", "-A", UA, "--max-time", "30", BASE + slug],
        capture_output=True, text=True,
    )
    return r.stdout


def parse_tracks(html):
    m = ROW_RE.search(html)
    if not m:
        return None
    rows_raw = m.group(1).split("<br>")
    tracks = []
    for row in rows_raw:
        cells = [c.strip() for c in row.split("|")]
        if len(cells) < 3:
            continue
        gleis = cells[0]
        height = cells[1]
        length_raw = cells[2]
        lm = re.search(r"([\d.,]+)\s*m", length_raw)
        if not lm:
            continue
        length_m = float(lm.group(1).replace(",", "."))
        tracks.append({"gleis": gleis, "height": height, "length_m": length_m})
    return tracks or None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/dbinfrago_platforms.json")
    args = ap.parse_args()

    out = {}
    for name, slug in STATIONS.items():
        print(f"  {name} ({slug}) ...")
        html = fetch_html(slug)
        tracks = parse_tracks(html)
        if tracks:
            best = max(t["length_m"] for t in tracks)
            out[name] = {"source_slug": slug, "tracks": tracks, "max_length_m": best}
            print(f"    -> {len(tracks)} Gleise, längster: {best:.0f} m")
        else:
            out[name] = {"source_slug": slug, "tracks": None, "max_length_m": None}
            print("    -> KEINE Tabelle gefunden")
        time.sleep(1.5)

    pathlib.Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    n_ok = sum(1 for v in out.values() if v["max_length_m"] is not None)
    print(f"\n{args.out}: {n_ok}/{len(out)} Stationen mit Daten")


if __name__ == "__main__":
    main()
