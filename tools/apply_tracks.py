#!/usr/bin/env python3
"""
Schreibt die in data/track_assignment.json berechnete Gleiszuweisung als
"track"-Feld in jeden Halt (stops[i]) einer Kopie der Fahrplandaten.

Wie apply_phases.py: schreibt NUR eine JSON-Datei (Vergleichsgrundlage),
fasst NICHT die App-HTML an. Das Zurückschreiben in die App erfolgt danach
separat über inject_lines.py --data <out> --write.

Nutzung:
    python3 tools/apply_tracks.py \
        --data data/lines.json --tracks data/track_assignment.json \
        --out data/lines_with_tracks.json
"""
import argparse
import json
import pathlib


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--tracks", default="data/track_assignment.json")
    ap.add_argument("--out", default="data/lines_with_tracks.json")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    tracks = json.loads(pathlib.Path(args.tracks).read_text(encoding="utf-8"))

    by_variant_idx = {}
    for st, info in tracks.items():
        for a in info["assignments"]:
            by_variant_idx[(a["variant"], a["idx"])] = a["track"]

    out = json.loads(json.dumps(data))  # deep copy
    n_set = 0
    n_missing = 0
    for k, v in out.items():
        for i, s in enumerate(v["stops"]):
            track = by_variant_idx.get((k, i))
            if track is None:
                n_missing += 1
                continue
            s["track"] = track
            n_set += 1

    pathlib.Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"{n_set} Halte mit Gleis versehen, {n_missing} ohne Zuordnung -> {args.out}")


if __name__ == "__main__":
    main()
