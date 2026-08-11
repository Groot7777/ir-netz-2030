#!/usr/bin/env python3
"""
Kombiniert Zuglängen (tools/lengths.py) mit realen Bahnsteiglängen
(tools/overpass_platforms.py) zu einer Konfliktliste.

Bewertung mit SDO-Toleranz: ein Zug, der etwas länger als der Bahnsteig
ist, ist im deutschen Regionalverkehr kein Show-Stopper — per Selective
Door Opening (SDO, Teilzugabfertigung) bleiben die Türen der über den
Bahnsteig hinausragenden Wagen einfach zu, oder eine bereits geplante
("fiktive") Bahnsteigverlängerung deckt die Differenz ab. Erst ein
größerer Überhang ist ein echter Prüf-/Baufall.

Nutzung:
    python3 tools/platform_conflicts.py \
        --train-lengths data/train_lengths.json \
        --platform-lengths data/platform_lengths.json \
        --sdo-tolerance-m 25 \
        --out data/platform_conflicts.md
"""
import argparse
import json
import pathlib

SEVERITY_ORDER = {"kritisch": 0, "gering": 1, "ok": 2, "keine_daten": 3}


def classify(required_m, available_m, sdo_tolerance_m):
    if available_m is None:
        return "keine_daten", None
    overhang = required_m - available_m
    if overhang <= 0:
        return "ok", overhang
    if overhang <= sdo_tolerance_m:
        return "gering", overhang
    return "kritisch", overhang


def build_conflicts(train_lengths, platform_lengths, sdo_tolerance_m, overrides=None, manual_overrides=None, min_confident_candidates=3):
    overrides = overrides or {}
    manual_overrides = manual_overrides or {}
    out = []
    for t in train_lengths:
        station = t["station"]
        manual = manual_overrides.get(station)
        override = overrides.get(station)
        if manual and manual.get("max_length_m") is not None:
            # Projekteigene Planung (RE-Netz 2030) schlägt sowohl OSM als auch
            # die heutige amtliche DB-InfraGO-Lage — z.B. fiktiver Ausbau, der
            # im heutigen Bestand noch nicht existiert. Siehe data/manual_overrides.json.
            available = manual["max_length_m"]
            n_plausible = len(manual.get("tracks") or [])
            confidence = "fiktiv"
        elif override and override.get("max_length_m") is not None:
            # Amtliche DB-InfraGO-Nettobaulänge schlägt OSM — deutlich
            # verlässlicher, siehe tools/dbinfrago_platforms.py. Trägt selbst
            # den Hinweis, dass Nettobaulänge != Bahnsteignutzlänge ist, aber
            # als Obergrenze für die Grobprüfung hier ausreichend belastbar.
            available = override["max_length_m"]
            n_plausible = len(override.get("tracks") or [])
            confidence = "amtlich"
        else:
            pl = platform_lengths.get(station)
            available = pl["best_length_m"] if pl else None
            n_plausible = sum(1 for p in pl["platforms"] if p["plausible"]) if pl else 0
            # Wenige unabhängige Treffer sind bei großen, komplexen Bahnhöfen
            # ein starkes Warnsignal für lückenhafte OSM-Erfassung, nicht für
            # einen kurzen Bahnsteig — siehe Köln/Düsseldorf/Dresden/Erfurt/
            # Mainz Hbf, wo die echten Fernbahnsteige in OSM fehlten und nur
            # vereinzelte, unpassende Objekte in der Nähe gefunden wurden.
            confidence = "hoch" if n_plausible >= min_confident_candidates else "niedrig"
        severity, overhang = classify(t["max_length_m"], available, sdo_tolerance_m)
        out.append(
            {
                "station": station,
                "required_m": t["max_length_m"],
                "line": t["line"],
                "cars": t["cars"],
                "available_m": available,
                "n_platform_candidates": n_plausible,
                "confidence": confidence,
                "overhang_m": round(overhang, 1) if overhang is not None else None,
                "severity": severity,
            }
        )
    return sorted(out, key=lambda r: (SEVERITY_ORDER[r["severity"]], -(r["overhang_m"] or 0)))


def render_markdown(conflicts, sdo_tolerance_m):
    by_sev = {"kritisch": [], "gering": [], "ok": [], "keine_daten": []}
    for c in conflicts:
        by_sev[c["severity"]].append(c)
    kritisch_fiktiv = [c for c in by_sev["kritisch"] if c["confidence"] == "fiktiv"]
    kritisch_amtlich = [c for c in by_sev["kritisch"] if c["confidence"] == "amtlich"]
    kritisch_hoch = [c for c in by_sev["kritisch"] if c["confidence"] == "hoch"]
    kritisch_niedrig = [c for c in by_sev["kritisch"] if c["confidence"] == "niedrig"]

    L = []
    L.append("# Bahnsteiglängen-Konfliktliste\n")
    L.append(
        f"Vergleich der aus Wagenzahl/Kupplung errechneten Zuglänge gegen reale "
        f"Bahnsteiglängen (DB InfraGO-Nettobaulänge wo vorhanden, sonst OpenStreetMap/"
        f"Overpass). SDO-Toleranz: {sdo_tolerance_m:.0f} m — Überhang bis dahin gilt als "
        f"unkritisch (Selective Door Opening bzw. bereits eingeplante Bahnsteig-"
        f"verlängerung), erst darüber als echter Prüffall.\n"
    )
    L.append(
        f"- **{len(kritisch_fiktiv)} kritisch, fiktive Planung** (RE-Netz-2030-eigener Ausbau, siehe data/manual_overrides.json)\n"
        f"- **{len(kritisch_amtlich)} kritisch, amtliche Daten** (DB InfraGO — ernstzunehmender Befund)\n"
        f"- **{len(kritisch_hoch)} kritisch, hohe OSM-Konfidenz** (≥3 unabhängige OSM-Treffer, ungeprüft)\n"
        f"- **{len(kritisch_niedrig)} kritisch, niedrige OSM-Konfidenz** (<3 Treffer — meist OSM-Lücke statt echtes Problem)\n"
        f"- **{len(by_sev['gering'])} gering** (SDO ausreichend)\n"
        f"- **{len(by_sev['ok'])} unauffällig**\n"
        f"- **{len(by_sev['keine_daten'])} ohne Bahnsteigdaten** (manuell zu prüfen)\n"
    )
    n_amtlich_total = sum(1 for c in conflicts if c["confidence"] == "amtlich")
    n_osm_only = sum(1 for c in conflicts if c["confidence"] in ("hoch", "niedrig"))
    L.append(
        f"> **Befund zur Datenqualität:** Für {n_amtlich_total} deutsche Stationen liegt "
        f"jetzt die amtliche DB InfraGO-Nettobaulänge vor (tools/dbinfrago_platforms.py, "
        f"gleisscharf in data/dbinfrago_platforms.json), für {n_osm_only} weitere "
        f"(v.a. die 101 ausländischen Stationen sowie einzelne kleine deutsche Halte "
        f"ohne dbinfrago-Eintrag) nur die unsichere OSM-Schätzung. Mit amtlichen Daten "
        f"bleiben **nur noch {len(kritisch_amtlich)} echte Kritisch-Fälle** übrig — "
        f"überwiegend kleine S-Bahn-Halte (S10-Ring, S30), deren Bahnsteige nie für "
        f"6-teilige Züge gebaut wurden. Das ist jetzt eher eine Entscheidung über "
        f"Zuglänge/Kurzzug-Einsatz an diesen Halten als ein Datenproblem. Für "
        f"Stationen ohne amtliche Bestätigung gilt weiterhin: OSM-Konfidenz "
        f"'niedrig' ist meist eine Datenlücke, kein echtes Bahnsteigproblem — "
        f"auch 'hohe' OSM-Konfidenz war in Stichproben nicht durchgehend verlässlich "
        f"(z.B. Mainz Hbf: 10 OSM-Treffer, dennoch nur 83 statt amtlich 210+ m). "
        f"Vor jeder Maßnahme ohne amtliche Bestätigung gegenprüfen.\n"
    )

    L.append("## Kritisch — fiktive RE-Netz-2030-Planung\n")
    if kritisch_fiktiv:
        L.append("| Station | Linie | Wagen | benötigt | verfügbar | Überhang |")
        L.append("|---|---|---|---|---|---|")
        for c in kritisch_fiktiv:
            L.append(
                f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m | "
                f"{c['available_m']:.0f} m | **+{c['overhang_m']:.0f} m** |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append("## Kritisch — amtliche DB-InfraGO-Daten\n")
    if kritisch_amtlich:
        L.append("| Station | Linie | Wagen | benötigt | verfügbar | Überhang |")
        L.append("|---|---|---|---|---|---|")
        for c in kritisch_amtlich:
            L.append(
                f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m | "
                f"{c['available_m']:.0f} m | **+{c['overhang_m']:.0f} m** |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append("## Kritisch — hohe OSM-Konfidenz (ungeprüft)\n")
    if kritisch_hoch:
        L.append("| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |")
        L.append("|---|---|---|---|---|---|---|")
        for c in kritisch_hoch:
            L.append(
                f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m | "
                f"{c['available_m']:.0f} m | +{c['overhang_m']:.0f} m | {c['n_platform_candidates']} |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append(f"## Kritisch — niedrige OSM-Konfidenz (vermutlich OSM-Lücke, {len(kritisch_niedrig)} Fälle)\n")
    if kritisch_niedrig:
        L.append("| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |")
        L.append("|---|---|---|---|---|---|---|")
        for c in kritisch_niedrig:
            L.append(
                f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m | "
                f"{c['available_m']:.0f} m | +{c['overhang_m']:.0f} m | {c['n_platform_candidates']} |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append(f"## Gering (SDO/geplante Verlängerung ausreichend, ≤{sdo_tolerance_m:.0f} m)\n")
    if by_sev["gering"]:
        L.append("| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Konfidenz |")
        L.append("|---|---|---|---|---|---|---|")
        for c in by_sev["gering"]:
            L.append(
                f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m | "
                f"{c['available_m']:.0f} m | +{c['overhang_m']:.0f} m | {c['confidence']} |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append("## Ohne Bahnsteigdaten\n")
    if by_sev["keine_daten"]:
        L.append("| Station | Linie | Wagen | benötigt |")
        L.append("|---|---|---|---|")
        for c in by_sev["keine_daten"]:
            L.append(f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m |")
    else:
        L.append("Keine.")
    L.append("")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-lengths", default="data/train_lengths.json")
    ap.add_argument("--platform-lengths", default="data/platform_lengths.json")
    ap.add_argument(
        "--overrides",
        default="data/dbinfrago_platforms.json",
        help="amtliche Daten (tools/dbinfrago_platforms.py), schlagen OSM wo vorhanden. Leer/fehlend = nur OSM.",
    )
    ap.add_argument(
        "--manual-overrides",
        default="data/manual_overrides.json",
        help="projekteigene Planung (fiktiver Ausbau u.ä.), schlägt alles andere. Leer/fehlend = keine.",
    )
    ap.add_argument("--sdo-tolerance-m", type=float, default=25.0)
    ap.add_argument("--out", default="data/platform_conflicts.md")
    ap.add_argument("--json-out", default="data/platform_conflicts.json")
    args = ap.parse_args()

    train_lengths = json.loads(pathlib.Path(args.train_lengths).read_text(encoding="utf-8"))
    platform_lengths = json.loads(pathlib.Path(args.platform_lengths).read_text(encoding="utf-8"))
    overrides_path = pathlib.Path(args.overrides)
    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else {}
    manual_path = pathlib.Path(args.manual_overrides)
    manual_overrides = json.loads(manual_path.read_text(encoding="utf-8")) if manual_path.exists() else {}

    conflicts = build_conflicts(
        train_lengths, platform_lengths, args.sdo_tolerance_m,
        overrides=overrides, manual_overrides=manual_overrides,
    )

    pathlib.Path(args.json_out).write_text(
        json.dumps(conflicts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = render_markdown(conflicts, args.sdo_tolerance_m)
    pathlib.Path(args.out).write_text(md, encoding="utf-8")

    counts = {}
    for c in conflicts:
        counts[c["severity"]] = counts.get(c["severity"], 0) + 1
    print(f"{args.out} geschrieben: {counts}")


if __name__ == "__main__":
    main()
