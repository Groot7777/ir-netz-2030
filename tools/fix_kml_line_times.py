#!/usr/bin/env python3
"""
Ersetzt fuer bestimmte Linien (--lines) ALLE eingebetteten Zeiten in der
KML durch direkt aus der AKTUELLEN App berechnete Werte — statt sie per
Delta-Verschiebung von der (fehlerhaften) KML-Baseline abzuleiten. Fuer
RE30/RE71 hat tools/check_kml_baseline_consistency.py gezeigt, dass die
Original-KML dort schon vor jeder Optimierung 1-2 Minuten von der Baseline-
App abwich (RE30: durchgehend -2min, RE71: einzelne Halte -1min) — die
reine Delta-Verschiebung von tools/sync_kml_times.py schleppt so einen
Fehler unveraendert mit, statt ihn zu beheben.

Nutzung:
    python3 tools/fix_kml_line_times.py --kml <bereits synchronisierte.kml> \
        --lines RE30,RE71 --out <ausgabe.kml>
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sync_kml_times import norm, loose_norm, STATION_BLOCK_RE, RICHTUNG_RE, XXMM_RE, HHMM_RE, BULLET_STOP_RE  # noqa: E402


def to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def fmt_hhmm(total):
    total %= 1440
    return f"{total // 60:02d}:{total % 60:02d}"


def build_ground_truth(data, line_names_norm):
    """(norm(name), norm(dest)) -> [{station_norm: (real_name, {'an':m,'ab':m})}]
    je Variante der gewuenschten Linien, direkt aus aktuellen App-Daten."""
    truth = {}
    abs_truth = {}  # key -> [(idx, station_name, abs_minute_of_day, is_first, is_last)]
    for k, v in data.items():
        if norm(v["name"]) not in line_names_norm:
            continue
        interval = v["takt"]["interval"]
        start = to_min(v["takt"]["start"])
        phase = start % interval
        key = (norm(v["name"]), norm(v["dest"]))
        per_station = {}
        n = len(v["stops"])
        abs_list = []
        for i, s in enumerate(v["stops"]):
            an_abs = start + s["off"]
            ab_abs = start + s.get("dep", s["off"])
            an = (phase + s["off"]) % 60
            ab = (phase + s.get("dep", s["off"])) % 60
            if i == 0:
                vals = {"ab": ab}
            elif i == n - 1:
                vals = {"an": an}
            else:
                vals = {"an": an, "ab": ab}
            per_station[norm(s["name"])] = (s["name"], vals)
            abs_list.append((i, s["name"], an_abs, ab_abs, i == 0, i == n - 1))
        truth.setdefault(key, []).append(per_station)
        abs_truth[key] = abs_list
    return truth, abs_truth


def fix_station_placemark(desc, station_name, truth, line_names_norm):
    def block_repl(m):
        line_name = m.group(1).strip()
        if norm(line_name) not in line_names_norm:
            return m.group(0)
        rest = m.group(2)

        def richtung_repl(rm):
            ziel = rm.group(1).strip()
            key = (norm(line_name), norm(ziel))
            variants = truth.get(key) or truth.get((norm(line_name), loose_norm(ziel)))
            if not variants:
                return rm.group(0)
            per_station = None
            for cand in variants:
                if norm(station_name) in cand:
                    per_station = cand[norm(station_name)]
                    break
            if per_station is None:
                return rm.group(0)
            _real, vals = per_station
            parts = []
            if "an" in vals:
                parts.append(f"an xx:{vals['an']:02d}")
            if "ab" in vals:
                parts.append(f"ab xx:{vals['ab']:02d}")
            return f"Richtung {ziel}: " + " / ".join(parts)

        return m.group(0).replace(rest, RICHTUNG_RE.sub(richtung_repl, rest), 1)

    return STATION_BLOCK_RE.sub(block_repl, desc)


HEADER_RE = re.compile(r"<b>([^<]+?)\s*→\s*([^<]+?)</b>")
AST_RE = re.compile(r"<u>Ast \d+:\s*([^<→]+?)\s*→\s*([^<]+?)</u>")
BULLET_TIME_RE = re.compile(
    r"(&#8226;&#160;<b>([^<]+)</b><br/>Beispielzeit: )([^<]+)"
)


def fix_line_placemark(desc, placemark_line_name, abs_truth, line_names_norm):
    if norm(placemark_line_name) not in line_names_norm:
        return desc, False

    # Ursprung/Ziel bestimmen (Kopf oder Bullet-Fallback), wie sync_kml_times.py
    hm = HEADER_RE.search(desc)
    if hm:
        origin, dest = hm.group(1).strip(), hm.group(2).strip()
    else:
        stops = BULLET_STOP_RE.findall(desc)
        if len(stops) < 2:
            return desc, False
        origin, dest = stops[0].strip(), stops[-1].strip()

    key = (norm(placemark_line_name), norm(dest))
    abs_list = abs_truth.get(key) or abs_truth.get((norm(placemark_line_name), loose_norm(dest)))
    if not abs_list:
        return desc, False

    by_station = {}
    for i, name, an_abs, ab_abs, is_first, is_last in abs_list:
        by_station.setdefault(norm(name), []).append((an_abs, ab_abs, is_first, is_last))

    changed = False

    def bullet_repl(m):
        nonlocal changed
        prefix, stop_name, _old = m.group(1), m.group(2), m.group(3)
        cands = by_station.get(norm(stop_name))
        if not cands:
            return m.group(0)
        an_abs, ab_abs, is_first, is_last = cands[0]
        if is_first:
            new = f"ab {fmt_hhmm(ab_abs)}"
        elif is_last:
            new = f"an {fmt_hhmm(an_abs)}"
        else:
            new = f"an {fmt_hhmm(an_abs)} / ab {fmt_hhmm(ab_abs)}"
        changed = True
        return prefix + new

    new_desc = BULLET_TIME_RE.sub(bullet_repl, desc)
    return new_desc, changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kml", required=True)
    ap.add_argument("--html", default="app/RENetz2030_Fahrplanauskunft.html")
    ap.add_argument("--lines", required=True, help="Kommagetrennt, z.B. RE30,RE71")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    current_html = pathlib.Path(args.html).read_text(encoding="utf-8")
    current = json.loads(re.search(r"const LINES = (\{.*\});", current_html).group(1))
    line_names_norm = {norm(x.strip()) for x in args.lines.split(",")}
    truth, abs_truth = build_ground_truth(current, line_names_norm)

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    placemark_pat = re.compile(r"<Placemark>.*?</Placemark>", re.DOTALL)
    name_pat = re.compile(r"<name>(.*?)</name>")
    desc_pat = re.compile(r"(<description><!\[CDATA\[)(.*?)(\]\]></description>)", re.DOTALL)
    has_point = re.compile(r"<Point>")
    has_line = re.compile(r"<LineString>")

    n_station = 0
    n_line = 0

    def repl(m):
        nonlocal n_station, n_line
        block = m.group(0)
        nm = name_pat.search(block)
        dm = desc_pat.search(block)
        if not nm or not dm:
            return block
        pname = nm.group(1)
        desc = dm.group(2)
        if has_point.search(block):
            new_desc = fix_station_placemark(desc, pname, truth, line_names_norm)
            if new_desc != desc:
                n_station += 1
            block = block[: dm.start()] + dm.group(1) + new_desc + dm.group(3) + block[dm.end():]
        elif has_line.search(block):
            line_name = pname.split(" ")[0]
            new_desc, changed = fix_line_placemark(desc, line_name, abs_truth, line_names_norm)
            if changed:
                n_line += 1
            block = block[: dm.start()] + dm.group(1) + new_desc + dm.group(3) + block[dm.end():]
        return block

    new_kml = placemark_pat.sub(repl, kml_text)
    pathlib.Path(args.out).write_text(new_kml, encoding="utf-8")
    print(f"{n_station} Stations-Placemarks, {n_line} Linien-Placemarks direkt korrigiert (Linien: {args.lines})")


if __name__ == "__main__":
    main()
