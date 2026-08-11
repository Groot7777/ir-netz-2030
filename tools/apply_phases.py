#!/usr/bin/env python3
"""
Wendet vom Solver gefundene Phasen (data/optimized_phases.json) auf eine
Kopie der Fahrplandaten an — verschiebt takt.start/end und extraTrips.dep
um den minimal nötigen Betrag, damit takt.start % interval == neue Phase
gilt, OHNE die Betriebsspanne (Früh-/Spätfahrten) künstlich zu verschieben.

Schreibt NUR data/optimized_lines.json (Vergleichsgrundlage für
tools/score.py) — fasst NICHT die App-HTML an. Das Zurückschreiben in
die App ist ein eigener, separater Schritt (Paket 8) nach Freigabe.

Nutzung:
    python3 tools/apply_phases.py \
        --data data/lines.json --phases data/optimized_phases.json \
        --out data/optimized_lines.json
"""
import argparse
import json
import pathlib
import re

TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")


def to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def fmt(total_min):
    total_min %= 1440
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def shift_note_times(note, shift):
    """Verschiebt jede HH:MM-Uhrzeit in einem takt.note-Freitext um denselben
    Betrag wie takt.start/end — sonst werden Angaben wie 'Spätfahrten bis
    00:49' nach der Optimierung falsch, weil sie sich auf die ALTE Phase
    beziehen. Reine Zeitangaben mit Doppelpunkt (h:mm), keine Prosa-
    Doppelpunkte, daher \\b-Grenzen und volles Uhrzeit-Muster."""
    if not note or not shift:
        return note

    def repl(m):
        total = int(m.group(1)) * 60 + int(m.group(2))
        return fmt(total + shift)

    return TIME_RE.sub(repl, note)


def minimal_shift(old_phase, new_phase, interval):
    """Kleinster (positiver oder negativer) Betrag, um den start/end/
    extraTrips verschoben werden müssen, damit die neue Phase erreicht
    wird — zentriert um 0, damit z.B. eine 1-Minuten-Korrektur nicht als
    +59 Minuten umgesetzt wird."""
    raw = (new_phase - old_phase) % interval
    if raw > interval / 2:
        raw -= interval
    return raw


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--phases", default="data/optimized_phases.json")
    ap.add_argument("--out", default="data/optimized_lines.json")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    solved = json.loads(pathlib.Path(args.phases).read_text(encoding="utf-8"))
    new_phases = solved["phases"]
    base_phase = solved["base_phase"]

    out = json.loads(json.dumps(data))  # deep copy
    shifts = {}
    for k, new_p in new_phases.items():
        v = out[k]
        interval = v["takt"]["interval"]
        old_p = base_phase[k]
        shift = minimal_shift(old_p, new_p, interval)
        if shift == 0:
            continue
        shifts[k] = shift
        v["takt"]["start"] = fmt(to_min(v["takt"]["start"]) + shift)
        v["takt"]["end"] = fmt(to_min(v["takt"]["end"]) + shift)
        if v["takt"].get("note"):
            v["takt"]["note"] = shift_note_times(v["takt"]["note"], shift)
        for trip in v.get("extraTrips", []):
            if "dep" in trip:
                trip["dep"] = fmt(to_min(trip["dep"]) + shift)

    pathlib.Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    moved = sum(1 for s in shifts.values() if s != 0)
    print(f"{moved} von {len(new_phases)} Varianten verschoben (⌀ |Δ|={sum(abs(s) for s in shifts.values())/max(1,moved):.1f} Min) -> {args.out}")


if __name__ == "__main__":
    main()
