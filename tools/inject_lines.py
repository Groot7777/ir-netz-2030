#!/usr/bin/env python3
"""
Schreibt eine (bearbeitete) lines.json zurück in die HTML-App. Ersetzt
ausschließlich die 'const LINES = {...};'-Zeile, der Rest der Datei bleibt
byte-identisch.

Nutzung:
    python3 tools/inject_lines.py \
        --html app/RENetz2030_Fahrplanauskunft.html \
        --data data/lines.json \
        --dry-run          # nur Diff-Zusammenfassung anzeigen

    python3 tools/inject_lines.py \
        --html app/RENetz2030_Fahrplanauskunft.html \
        --data data/lines.json \
        --write            # tatsächlich schreiben
"""
import argparse
import difflib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from htmldata import extract_lines_dict, replace_lines_dict  # noqa: E402


def summarize_takt_diff(old, new):
    """Menschenlesbare Zusammenfassung: welche Linie hat sich wie verschoben."""
    lines = []
    keys = sorted(set(old) | set(new))
    for k in keys:
        if k not in old:
            lines.append(f"  + {k}: NEU")
            continue
        if k not in new:
            lines.append(f"  - {k}: ENTFERNT")
            continue
        ot, nt = old[k].get("takt", {}), new[k].get("takt", {})
        if ot.get("start") != nt.get("start") or ot.get("end") != nt.get("end"):
            lines.append(
                f"  ~ {k}: takt.start {ot.get('start')} -> {nt.get('start')}, "
                f"takt.end {ot.get('end')} -> {nt.get('end')}"
            )
        oe, ne = old[k].get("extraTrips", []), new[k].get("extraTrips", [])
        if oe != ne:
            lines.append(f"  ~ {k}: extraTrips geändert ({len(oe)} -> {len(ne)} Einträge)")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", default="app/RENetz2030_Fahrplanauskunft.html")
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--write", action="store_true", help="tatsächlich in --html schreiben")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, nicht schreiben (Default)")
    args = ap.parse_args()

    html_path = pathlib.Path(args.html)
    data_path = pathlib.Path(args.data)

    html_text = html_path.read_text(encoding="utf-8")
    old_data = extract_lines_dict(html_text)
    new_data = json.loads(data_path.read_text(encoding="utf-8"))

    new_html = replace_lines_dict(html_text, new_data)

    diff_lines = summarize_takt_diff(old_data, new_data)
    print(f"{len(diff_lines)} Richtungsvarianten mit Änderungen:")
    for l in diff_lines:
        print(l)

    byte_diff = sum(
        1
        for _ in difflib.unified_diff(
            html_text.splitlines(), new_html.splitlines(), lineterm=""
        )
    )
    print(f"\nGeänderte Zeilen in der HTML insgesamt: {byte_diff} Diff-Zeilen (inkl. Header)")

    if args.write:
        html_path.write_text(new_html, encoding="utf-8")
        print(f"\nGeschrieben: {html_path}")
    else:
        print("\n(Dry-Run — nichts geschrieben. --write zum tatsächlichen Anwenden.)")


if __name__ == "__main__":
    main()
