#!/usr/bin/env python3
"""
Extrahiert die LINES-Datenstruktur aus der HTML-App als eigenständige
lines.json-Datei, damit sie sich außerhalb der App (Scoring, Solver)
bearbeiten lässt.

Nutzung:
    python3 tools/extract_lines.py \
        --html app/RENetz2030_Fahrplanauskunft.html \
        --out  data/lines.json
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from htmldata import extract_lines_dict  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", default="app/RENetz2030_Fahrplanauskunft.html")
    ap.add_argument("--out", default="data/lines.json")
    args = ap.parse_args()

    html_path = pathlib.Path(args.html)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html_text = html_path.read_text(encoding="utf-8")
    data = extract_lines_dict(html_text)

    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{len(data)} Richtungsvarianten extrahiert -> {out_path}")


if __name__ == "__main__":
    main()
