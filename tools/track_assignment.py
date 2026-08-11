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
  2. data/dbinfrago_platforms.json — amtliche DB InfraGO-Daten (353 dt. Bahnhöfe)
  3. data/platform_lengths.json  — OSM/Overpass (Ausland + Rest-Lücken)
  4. Fallback 'geschaetzt': KEINE Quelle vorhanden — ein einzelnes Gleis
     wird auf die längste dort tatsächlich benötigte Zuglänge geschätzt
     (nicht auf 0!), klar als 'geschätzt' markiert statt als Fakt
     ausgegeben. 0 wäre sachlich falsch — "keine Daten" heißt nicht
     "garantiert zu kurz".

Konflikt-Bewertung mit derselben SDO-Toleranz wie tools/platform_
conflicts.py (25m Überhang gilt als unkritisch, Selective Door Opening/
geplante Verlängerung deckt das ab) statt einem starren Ja/Nein.

Algorithmus je Station:
  - Kandidaten je Besuch (Variante×Halt): alle Gleise mit Länge >= benötigt
    (Kupplung/coupledSection bereits berücksichtigt, siehe lengths.py).
  - Reicht kein Gleis aus: längstes verfügbares nehmen, Überhang nach
    SDO-Toleranz klassifizieren (ok/gering/kritisch).
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


def dedup_max(tracks):
    """DB InfraGO listet manche Gleise mehrfach (unterschiedliche Bahnsteig-
    höhen-/Zugangs-Abschnitte derselben physischen Bahnsteigkante, z.B.
    Landstuhl Gleis 1: 24cm/43m UND 76cm/189m). Für die Zuglängen-Zuweisung
    zählt die tatsächliche nutzbare Länge -> pro Label die maximale Länge
    behalten, statt versehentlich die kurze Teilangabe zu erwischen."""
    best = {}
    order = []
    for label, length in tracks:
        if not str(label).strip():
            continue  # Scraping-Artefakt (vereinzelte Zeilen ohne Gleisnummer, z.B. Fußnoten)
        if label not in best:
            order.append(label)
        best[label] = max(best.get(label, 0), length)
    return [(label, best[label]) for label in order]


def build_station_tracks(stations, manual, dbinfrago, osm):
    """Verfügbare Gleise je Station, mit Quelle — Prioritätskette wie in
    tools/platform_conflicts.py, hier zusätzlich mit Gleis-LABELN (nicht
    nur der längsten verfügbaren Länge)."""
    out = {}
    for st in stations:
        m = manual.get(st)
        if m and m.get("tracks"):
            out[st] = {"source": "fiktiv", "tracks": dedup_max([(t["gleis"], t["length_m"]) for t in m["tracks"]])}
            continue
        d = dbinfrago.get(st)
        if d and d.get("tracks"):
            out[st] = {"source": "amtlich", "tracks": dedup_max([(t["gleis"], t["length_m"]) for t in d["tracks"]])}
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
                out[st] = {"source": "osm", "tracks": dedup_max(tracks)}
                continue
        out[st] = {"source": "geschaetzt", "tracks": []}  # Länge erst bekannt, wenn die Besuche vorliegen
    return out


def classify(overhang_m, sdo_tolerance_m=25):
    if overhang_m <= 0:
        return "ok"
    if overhang_m <= sdo_tolerance_m:
        return "gering"
    return "kritisch"


def assign_station(visits, tracks, source, sdo_tolerance_m=25):
    """visits: [{key, required_length}]. tracks: [(label, length)].
    Gibt {key: {"track": label, "severity": str, "overhang_m": float}} zurück.

    source=='geschaetzt' (keine Quelle): synthetisiert EIN Gleis, das exakt
    zur längsten dort benötigten Zuglänge passt — 'keine Daten' wird nicht
    stillschweigend als 'garantiert zu kurz' (Länge 0) interpretiert."""
    if source == "geschaetzt" and not tracks:
        est = max((v["required_length"] for v in visits), default=0)
        tracks = [("1 (geschätzt)", est)]

    tracks_sorted = sorted(tracks, key=lambda t: -t[1])
    used = collections.Counter()
    out = {}
    for v in sorted(visits, key=lambda v: -v["required_length"]):
        candidates = [t for t in tracks_sorted if t[1] >= v["required_length"]]
        if candidates:
            candidates = sorted(candidates, key=lambda t: (used[t[0]], t[1]))
        else:
            # Kein Gleis reicht aus: bestmöglich das LÄNGSTE nehmen (kleinster
            # Überhang zählt hier mehr als Lastverteilung), erst bei
            # gleicher Länge nach Auslastung ausgleichen.
            candidates = sorted(tracks_sorted, key=lambda t: (-t[1], used[t[0]]))
        chosen = candidates[0]
        used[chosen[0]] += 1
        overhang = round(v["required_length"] - chosen[1], 1)
        out[v["key"]] = {
            "track": chosen[0],
            "severity": classify(overhang, sdo_tolerance_m),
            "overhang_m": overhang,
        }
    return out, tracks


def render_markdown(result, n_by_source, n_by_severity):
    L = ["# Netzweite Gleiszuweisung — RE-Netz 2030", ""]
    L.append(
        "Jede Richtungsvariante bekommt an jedem Halt ein festes, längenpassendes "
        "Gleis. Datengrundlage: DB InfraGO (amtlich, deutsche Bahnhöfe), OSM/Overpass "
        "(Ausland + Restlücken), Projekt-Fiktion (fiktiv, höchste Priorität), sonst "
        "eine dokumentierte Schätzung. Details siehe Docstring in "
        "`tools/track_assignment.py`."
    )
    L.append("")
    L.append("## Zusammenfassung")
    L.append("")
    total = sum(n_by_severity.values())
    L.append(f"- {len(result)} Stationen, {total} Zuweisungen (Variante×Halt)")
    L.append(f"- Quellen: " + ", ".join(f"{k} {v}" for k, v in sorted(n_by_source.items())))
    L.append(
        "- Konfliktstufen: "
        + ", ".join(f"{k} {v}" for k, v in sorted(n_by_severity.items()))
        + " (ok = passt, gering = ≤25 m Überhang/SDO ausreichend, kritisch = >25 m)"
    )
    L.append("")

    L.append("## Kritisch (>25 m Überhang)\n")
    kritisch = []
    for st, info in result.items():
        for a in info["assignments"]:
            if a["severity"] == "kritisch":
                kritisch.append({**a, "station": st, "source": info["source"]})
    kritisch.sort(key=lambda c: -c["overhang_m"])
    if kritisch:
        L.append("| Station | Linie | Variante | Gleis | benötigt | Überhang | Quelle |")
        L.append("|---|---|---|---|---|---|---|")
        for c in kritisch:
            L.append(
                f"| {c['station']} | {c['line']} | {c['variant']} | {c['track']} | "
                f"{c['required_length_m']:.0f} m | +{c['overhang_m']:.0f} m | {c['source']} |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append("## Gering (≤25 m Überhang, SDO/geplante Verlängerung deckt es ab)\n")
    gering = []
    for st, info in result.items():
        for a in info["assignments"]:
            if a["severity"] == "gering":
                gering.append({**a, "station": st, "source": info["source"]})
    gering.sort(key=lambda c: -c["overhang_m"])
    if gering:
        L.append("| Station | Linie | Variante | Gleis | benötigt | Überhang | Quelle |")
        L.append("|---|---|---|---|---|---|---|")
        for c in gering:
            L.append(
                f"| {c['station']} | {c['line']} | {c['variant']} | {c['track']} | "
                f"{c['required_length_m']:.0f} m | +{c['overhang_m']:.0f} m | {c['source']} |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append("## Stationen mit geschätzten Gleisen (keine Quelle vorhanden)\n")
    geschaetzt = sorted(st for st, info in result.items() if info["source"] == "geschaetzt")
    if geschaetzt:
        L.append(", ".join(geschaetzt))
    else:
        L.append("Keine.")
    L.append("")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--manual-overrides", default="data/manual_overrides.json")
    ap.add_argument("--dbinfrago", default="data/dbinfrago_platforms.json")
    ap.add_argument("--platform-lengths", default="data/platform_lengths.json")
    ap.add_argument("--out", default="data/track_assignment.json")
    ap.add_argument("--md-out", default="data/track_assignment.md")
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
    n_by_severity = collections.Counter()
    n_by_source = collections.Counter()
    for st, visits in visits_by_station.items():
        info = station_tracks[st]
        assignment, resolved_tracks = assign_station(visits, info["tracks"], info["source"])
        rows = []
        for v in visits:
            a = assignment[v["key"]]
            n_by_severity[a["severity"]] += 1
            rows.append(
                {
                    "variant": v["variant"], "idx": v["idx"], "line": v["line"],
                    "required_length_m": v["required_length"], "track": a["track"],
                    "severity": a["severity"], "overhang_m": a["overhang_m"],
                }
            )
        n_by_source[info["source"]] += 1
        result[st] = {
            "source": info["source"],
            "available_tracks": [{"gleis": g, "length_m": l} for g, l in resolved_tracks],
            "assignments": rows,
        }

    pathlib.Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    md = render_markdown(result, n_by_source, n_by_severity)
    pathlib.Path(args.md_out).write_text(md, encoding="utf-8")
    print(
        f"{len(result)} Stationen, {sum(len(v['assignments']) for v in result.values())} Zuweisungen "
        f"-> {args.out}, {args.md_out}"
    )
    print(f"Quellen: {dict(n_by_source)}")
    print(f"Severity: {dict(n_by_severity)}")


if __name__ == "__main__":
    main()
