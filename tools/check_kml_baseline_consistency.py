#!/usr/bin/env python3
"""
Prüft, ob die ORIGINAL-KML-Zeiten (vor jeder Optimierung) tatsächlich mit
der Baseline-App (Commit d45218b) übereinstimmten — deckt Datenfehler auf,
die schon vor der Taktfahrplan-Optimierung zwischen KML und App bestanden
und die tools/sync_kml_times.py als reine Delta-Verschiebung unverändert
mitgeschleppt hat (siehe Düsseldorf Hbf/RE30-Fall).

Nutzung:
    python3 tools/check_kml_baseline_consistency.py --kml <original.kml>
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sync_kml_times import (  # noqa: E402
    norm, loose_norm, STATION_BLOCK_RE, RICHTUNG_RE, XXMM_RE,
)


def to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def build_ground_truth(data):
    """(norm(line_name), norm(dest)) -> [(station_name, expected_xxmm_list)]
    je Halt jeder Variante, direkt aus der Baseline-App berechnet."""
    truth = {}
    for k, v in data.items():
        interval = v["takt"]["interval"]
        phase = to_min(v["takt"]["start"]) % interval
        key = (norm(v["name"]), norm(v["dest"]))
        per_station = {}
        n = len(v["stops"])
        for i, s in enumerate(v["stops"]):
            an = (phase + s["off"]) % 60
            ab = (phase + s.get("dep", s["off"])) % 60
            if i == 0:
                vals = {"ab": ab}
            elif i == n - 1:
                vals = {"an": an}
            else:
                vals = {"an": an, "ab": ab}
            per_station[norm(s["name"])] = (s["name"], vals)
        truth.setdefault(key, []).append(per_station)
    return truth


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kml", required=True)
    ap.add_argument("--baseline-commit", default="d45218b")
    args = ap.parse_args()

    baseline_html = subprocess.run(
        ["git", "show", f"{args.baseline_commit}:app/RENetz2030_Fahrplanauskunft.html"],
        capture_output=True, text=True, check=True,
    ).stdout
    baseline = json.loads(re.search(r"const LINES = (\{.*\});", baseline_html).group(1))
    truth = build_ground_truth(baseline)

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    placemark_pat = re.compile(r"<Placemark>(.*?)</Placemark>", re.DOTALL)
    name_pat = re.compile(r"<name>(.*?)</name>")
    desc_pat = re.compile(r"<description><!\[CDATA\[(.*?)\]\]></description>", re.DOTALL)
    has_point = re.compile(r"<Point>")

    mismatches = []
    checked = 0
    for m in placemark_pat.finditer(kml_text):
        block = m.group(0)
        if not has_point.search(block):
            continue
        nm = name_pat.search(block)
        dm = desc_pat.search(block)
        if not nm or not dm:
            continue
        station_name = nm.group(1)
        desc = dm.group(1)

        for bm in STATION_BLOCK_RE.finditer(desc):
            line_name = bm.group(1).strip()
            rest = bm.group(2)
            for rm in RICHTUNG_RE.finditer(rest):
                ziel = rm.group(1).strip()
                times_text = rm.group(2)
                key = (norm(line_name), norm(ziel))
                variants = truth.get(key) or truth.get((norm(line_name), loose_norm(ziel)))
                if not variants:
                    continue
                per_station = None
                for cand in variants:
                    if norm(station_name) in cand:
                        per_station = cand[norm(station_name)]
                        break
                if per_station is None:
                    continue
                _real_name, expected = per_station
                found = {int(x) for x in XXMM_RE.findall(times_text)}
                checked += 1
                exp_vals = set(expected.values())
                if not (found & exp_vals):
                    mismatches.append(
                        (station_name, line_name, ziel, times_text.strip(), expected)
                    )

    print(f"{checked} Richtungs-Eintraege geprueft, {len(mismatches)} Abweichungen von der Baseline-App gefunden:\n")
    for station, line, ziel, kml_times, expected in mismatches:
        print(f"  {station} | {line} Richtung {ziel}: KML={kml_times!r}  erwartet={expected}")


if __name__ == "__main__":
    main()
