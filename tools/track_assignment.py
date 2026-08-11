#!/usr/bin/env python3
"""
Netzweite Gleiszuweisung: jede Richtungsvariante bekommt an jedem Halt ein
festes Gleis (nicht zeitabhängig — realistisch für die meisten Regional-
linien, die an einer Station den ganzen Tag über dieselbe Bahnsteigkante
nutzen). KEINE minutengenaue Belegungsprüfung (das wäre echte Fahrdienst-
leitung/Stellwerkslogik und bräuchte reale Gleistopologie, die wir nicht
haben) — stattdessen ein deterministischer, dokumentierter Heuristik-
Algorithmus: längenpassend + Lastverteilung über die verfügbaren Gleise.

Datenpriorität pro Station (wie schon bei den Bahnsteiglängen etabliert):
  1. data/manual_overrides.json  — fiktive RE-Netz-2030-Planung
  2. data/dbinfrago_platforms.json — amtliche DB InfraGO-Daten (346 dt. Bahnhöfe)
  3. data/platform_lengths.json  — OSM/Overpass (Ausland + Rest-Lücken)
  4. Fallback: EIN geschätztes Gleis "1" (keine Quelle vorhanden — klar
     als 'geschätzt' markiert, nicht als Fakt ausgegeben)

Algorithmus je Station:
  - Kandidaten je Besuch (Variante×Halt): alle Gleise mit Länge >= benötigt
    (Kupplung/coupledSection bereits berücksichtigt, siehe lengths.py).
  - Reicht kein Gleis aus: längstes verfügbares nehmen, als Konflikt
    markieren (deckt sich mit tools/platform_conflicts.py).
  - Unter den Kandidaten das am wenigsten ausgelastete wählen (Lastver-
    teilung, damit nicht alles auf einem Gleis landet), bei Gleichstand
    das kürzeste ausreichende (kein unnötig langes Gleis verschwenden).

Nutzung:
    python3 tools/track_assignment.py --out data/track_assignment.json
"""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lengths import car_length, extra_cars_per_stop  # noqa: E402


def build_station_tracks(stations, manual, dbinfrago, osm):
    """Verfügbare Gleise je Station, mit Quelle — Prioritätskette wie in
    tools/platform_conflicts.py, hier zusätzlich mit Gleis-LABELN (nicht
    nur der längsten verfügbaren Länge)."""
    out = {}
    for st in stations:
        m = manual.get(st)
        if m and m.get("tracks"):
            out[st] = {"source": "fiktiv", "tracks": [(t["gleis"], t["length_m"]) for t in m["tracks"]]}
            continue
        d = dbinfrago.get(st)
        if d and d.get("tracks"):
            out[st] = {"source": "amtlich", "tracks": [(t["gleis"], t["length_m"]) for t in d["tracks"]]}
            continue
        o = osm.get(st)
        if o and o.get("platforms"):
            tracks = []
            for p in o["platforms"]:
                if not p["plausible"]:
                    continue
                label = p["ref"] or f"OSM{p['osm_id']}"
                tracks.append((label, p["length_m"]))
            if tracks:
                out[st] = {"source": "osm", "tracks": tracks}
                continue
        out[st] = {"source": "geschaetzt", "tracks": [("1", 0)]}
    return out


def assign_station(visits, tracks):
    """visits: [{key, required_length}]. tracks: [(label, length)].
    Gibt {key: {"track": label, "conflict": bool}} zurück."""
    tracks_sorted = sorted(tracks, key=lambda t: -t[1])
    used = collections.Counter()
    out = {}
    for v in sorted(visits, key=lambda v: -v["required_length"]):
        candidates = [t for t in tracks_sorted if t[1] >= v["required_length"]]
        conflict = False
        if not candidates:
            candidates = tracks_sorted
            conflict = True
        candidates = sorted(candidates, key=lambda t: (used[t[0]], t[1]))
        chosen = candidates[0]
        used[chosen[0]] += 1
        out[v["key"]] = {"track": chosen[0], "conflict": conflict}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--manual-overrides", default="data/manual_overrides.json")
    ap.add_argument("--dbinfrago", default="data/dbinfrago_platforms.json")
    ap.add_argument("--platform-lengths", default="data/platform_lengths.json")
    ap.add_argument("--out", default="data/track_assignment.json")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    manual = json.loads(pathlib.Path(args.manual_overrides).read_text(encoding="utf-8"))
    dbinfrago = json.loads(pathlib.Path(args.dbinfrago).read_text(encoding="utf-8"))
    osm = json.loads(pathlib.Path(args.platform_lengths).read_text(encoding="utf-8"))

    stations = sorted({s["name"] for v in data.values() for s in v["stops"]})
    station_tracks = build_station_tracks(stations, manual, dbinfrago, osm)

    visits_by_station = collections.defaultdict(list)
    for k, v in data.items():
        extra = extra_cars_per_stop(v)
        for i, s in enumerate(v["stops"]):
            length = car_length(v["cars"]) + (car_length(extra[i]) if extra[i] else 0)
            visits_by_station[s["name"]].append(
                {"key": f"{k}@{i}", "variant": k, "idx": i, "line": v["name"], "required_length": length}
            )

    result = {}
    n_conflict = 0
    n_by_source = collections.Counter()
    for st, visits in visits_by_station.items():
        info = station_tracks[st]
        assignment = assign_station(visits, info["tracks"])
        rows = []
        for v in visits:
            a = assignment[v["key"]]
            if a["conflict"]:
                n_conflict += 1
            rows.append(
                {
                    "variant": v["variant"], "idx": v["idx"], "line": v["line"],
                    "required_length_m": v["required_length"], "track": a["track"],
                    "conflict": a["conflict"],
                }
            )
        n_by_source[info["source"]] += 1
        result[st] = {
            "source": info["source"],
            "available_tracks": [{"gleis": g, "length_m": l} for g, l in info["tracks"]],
            "assignments": rows,
        }

    pathlib.Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        f"{len(result)} Stationen, {sum(len(v['assignments']) for v in result.values())} Zuweisungen "
        f"-> {args.out}"
    )
    print(f"Quellen: {dict(n_by_source)}")
    print(f"Längenkonflikte (kein Gleis lang genug): {n_conflict}")


if __name__ == "__main__":
    main()
