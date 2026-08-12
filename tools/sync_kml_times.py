#!/usr/bin/env python3
"""
Aktualisiert alle in der KML eingebetteten Beispielzeiten (Stations-
Placemarks: "Richtung X: an/ab xx:MM" Minutenmuster; Linien-Placemarks:
"Beispielzeit: an/ab HH:MM" absolute Zeiten) vom alten Baseline-Fahrplan
auf den optimierten Taktfahrplan (Solver Stufe 1 + Knotenkorrekturen).

Berechnet je Richtungsvariante die minimale Phasenverschiebung zwischen
der allerersten Baseline-HTML (git-Commit d45218b) und dem aktuellen
App-Stand (dieselbe Formel wie tools/apply_phases.py), und wendet sie
textuell auf die KML-Zeitangaben an:
  - "xx:MM" (Stationstext) -> Minute um den Shift verschieben, mod 60
    (die KML zeigt je Richtung nur EINE Beispielminute, auch bei 30-Min-
    Takt — konsistent mod 60, da Intervalle nur 30/60 sind).
  - "HH:MM" (Linien-Beispielzeit) -> volle Uhrzeit verschieben, mod 1440
    (Tagesumbruch), wie fmt()/apply_phases.py.

Zuordnung Text -> Variante:
  - Stationstext: "<b>LINIENNAME</b> ...<br/>Richtung ZIEL: ..." — ZIEL
    wird (nach Hbf/Hauptbahnhof-Normalisierung) gegen v['dest'] alle
    Varianten mit v['name']==LINIENNAME gematcht.
  - Linientext (Linien-Placemark mit LineString): "<b>URSPRUNG →
    ZIEL</b>" im Beschreibungskopf wird gegen stops[0].name/v['dest']
    aller Varianten mit passendem Linien-Namen (aus dem Placemark-Namen)
    gematcht.

Nutzung:
    python3 tools/sync_kml_times.py --kml <pfad> --out <ausgabe.kml>
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                         "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


def norm(s):
    s = s.translate(UMLAUT)
    s = re.sub(r"\bHbf\b", "Hauptbahnhof", s)
    s = re.sub(r"[^a-zA-Z0-9]+", "", s).lower()
    return s


def loose_norm(s):
    """norm() plus Entfernen von Klammerzusaetzen wie '(oben)'/'(NL)' —
    Fallback fuer Faelle, in denen die KML einen knapperen Stationsnamen
    nutzt als die App-Daten (z.B. 'Leipzig Hauptbahnhof' vs 'Leipzig Hbf
    (oben)', 'Roermond' vs 'Roermond (NL)')."""
    s = re.sub(r"\([^)]*\)", "", s)
    return norm(s)


def to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def minimal_shift(old_phase, new_phase, interval):
    raw = (new_phase - old_phase) % interval
    if raw > interval / 2:
        raw -= interval
    return raw


def build_variant_shifts(baseline, current):
    """{key: {"name", "dest", "stop0", "shift", "interval"}}"""
    out = {}
    for k, v in current.items():
        if k not in baseline:
            continue
        interval = v["takt"]["interval"]
        old_phase = to_min(baseline[k]["takt"]["start"]) % interval
        new_phase = to_min(v["takt"]["start"]) % interval
        shift = minimal_shift(old_phase, new_phase, interval)
        out[k] = {
            "name": v["name"], "dest": v["dest"],
            "stop0": v["stops"][0]["name"], "shift": shift, "interval": interval,
        }
    return out


def dest_shift_lookup(variant_shifts):
    """(norm(name), norm(dest)) -> shift, fuer Stations-Richtung-Matching.
    Bei Namenskollision (mehrere Varianten derselben Linie zum selben
    Ziel, z.B. Kupplungspartner) wird der erste Treffer verwendet — die
    Phase ist in solchen Faellen ohnehin meist identisch/gekoppelt."""
    lut = {}
    for k, info in variant_shifts.items():
        key = (norm(info["name"]), norm(info["dest"]))
        lut.setdefault(key, info["shift"])
        lut.setdefault((norm(info["name"]), loose_norm(info["dest"])), info["shift"])
    return lut


def route_shift_lookup(variant_shifts):
    """(norm(name), norm(stop0), norm(dest)) -> shift, fuer Linien-
    Placemark-Matching (eindeutiger als nur Ziel, da Linien-Placemarks
    eine feste Start->Ziel-Route zeigen)."""
    lut = {}
    for k, info in variant_shifts.items():
        key = (norm(info["name"]), norm(info["stop0"]), norm(info["dest"]))
        lut[key] = info["shift"]
        loose_key = (norm(info["name"]), loose_norm(info["stop0"]), loose_norm(info["dest"]))
        lut.setdefault(loose_key, info["shift"])
    return lut


STATION_BLOCK_RE = re.compile(
    r"<b>([^<]+)</b>\s*[^<]*?(?:<br/>|<br>)((?:(?!<br/><br/>|<b>).)*)", re.DOTALL
)
RICHTUNG_RE = re.compile(r"Richtung ([^:<]+):\s*([^<]*)")
XXMM_RE = re.compile(r"\bxx:(\d{2})\b")
HHMM_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")


def shift_xxmm(text, shift):
    def repl(m):
        minute = int(m.group(1))
        new_minute = (minute + shift) % 60
        return f"xx:{new_minute:02d}"
    return XXMM_RE.sub(repl, text)


def shift_hhmm(text, shift):
    def repl(m):
        total = (int(m.group(1)) * 60 + int(m.group(2)) + shift) % 1440
        return f"{total // 60:02d}:{total % 60:02d}"
    return HHMM_RE.sub(repl, text)


def update_station_description(desc, dest_lut):
    def block_repl(m):
        line_name = m.group(1).strip()
        rest = m.group(2)

        def richtung_repl(rm):
            ziel = rm.group(1).strip()
            times = rm.group(2)
            shift = dest_lut.get((norm(line_name), norm(ziel)))
            if shift is None:
                shift = dest_lut.get((norm(line_name), loose_norm(ziel)))
            if shift is None or shift == 0:
                return rm.group(0)
            new_times = shift_xxmm(times, shift)
            return f"Richtung {ziel}: {new_times}"

        new_rest = RICHTUNG_RE.sub(richtung_repl, rest)
        return m.group(0).replace(rest, new_rest, 1)

    return STATION_BLOCK_RE.sub(block_repl, desc)


HEADER_RE = re.compile(r"<b>([^<]+?)\s*→\s*([^<]+?)</b>")
BULLET_STOP_RE = re.compile(r"&#8226;&#160;<b>([^<]+)</b>")


def update_line_description(desc, placemark_line_name, route_lut):
    hm = HEADER_RE.search(desc)
    if hm:
        origin, dest = hm.group(1).strip(), hm.group(2).strip()
    else:
        # Manche Linien-Placemarks haben statt eines "A → B"-Kopfs nur
        # Fließtext (z.B. RE39) — dann Ursprung/Ziel aus dem ersten/
        # letzten Halte-Aufzaehlungspunkt der Bahnhofsliste ableiten.
        stops = BULLET_STOP_RE.findall(desc)
        if len(stops) < 2:
            return desc, None
        origin, dest = stops[0].strip(), stops[-1].strip()
    key = (norm(placemark_line_name), norm(origin), norm(dest))
    shift = route_lut.get(key)
    if shift is None:
        loose_key = (norm(placemark_line_name), loose_norm(origin), loose_norm(dest))
        shift = route_lut.get(loose_key)
    if shift is None or shift == 0:
        return desc, shift
    return shift_hhmm(desc, shift), shift


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kml", required=True)
    ap.add_argument("--html", default="app/RENetz2030_Fahrplanauskunft.html")
    ap.add_argument("--baseline-commit", default="d45218b")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    baseline_html = subprocess.run(
        ["git", "show", f"{args.baseline_commit}:app/RENetz2030_Fahrplanauskunft.html"],
        capture_output=True, text=True, check=True,
    ).stdout
    baseline = json.loads(re.search(r"const LINES = (\{.*\});", baseline_html).group(1))
    current_html = pathlib.Path(args.html).read_text(encoding="utf-8")
    current = json.loads(re.search(r"const LINES = (\{.*\});", current_html).group(1))

    variant_shifts = build_variant_shifts(baseline, current)
    dest_lut = dest_shift_lookup(variant_shifts)
    route_lut = route_shift_lookup(variant_shifts)

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    placemark_pat = re.compile(r"<Placemark>.*?</Placemark>", re.DOTALL)
    name_pat = re.compile(r"<name>(.*?)</name>")
    desc_pat = re.compile(r"(<description><!\[CDATA\[)(.*?)(\]\]></description>)", re.DOTALL)
    has_point = re.compile(r"<Point>")
    has_line = re.compile(r"<LineString>")

    n_station_updates = 0
    n_line_updates = 0
    unmatched_lines = []

    def placemark_repl(m):
        nonlocal n_station_updates, n_line_updates
        block = m.group(0)
        nm = name_pat.search(block)
        if not nm:
            return block
        pname = nm.group(1)
        dm = desc_pat.search(block)
        if not dm:
            return block
        desc = dm.group(2)

        if has_point.search(block):
            new_desc = update_station_description(desc, dest_lut)
            if new_desc != desc:
                n_station_updates += 1
            block = block[: dm.start()] + dm.group(1) + new_desc + dm.group(3) + block[dm.end() :]
        elif has_line.search(block):
            line_name = pname.split(" ")[0]
            new_desc, shift = update_line_description(desc, line_name, route_lut)
            if shift is None:
                unmatched_lines.append(pname)
            elif shift != 0:
                n_line_updates += 1
            block = block[: dm.start()] + dm.group(1) + new_desc + dm.group(3) + block[dm.end() :]
        return block

    new_kml = placemark_pat.sub(placemark_repl, kml_text)
    pathlib.Path(args.out).write_text(new_kml, encoding="utf-8")

    print(f"{n_station_updates} Stations-Placemarks mit geaenderten Zeiten")
    print(f"{n_line_updates} Linien-Placemarks mit geaenderten Zeiten")
    if unmatched_lines:
        print(f"{len(unmatched_lines)} Linien-Placemarks OHNE Varianten-Zuordnung (unveraendert):")
        for u in unmatched_lines:
            print("  ", u)


if __name__ == "__main__":
    main()
