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


def build_conflicts(train_lengths, platform_lengths, sdo_tolerance_m):
    out = []
    for t in train_lengths:
        station = t["station"]
        pl = platform_lengths.get(station)
        available = pl["best_length_m"] if pl else None
        n_platforms = len(pl["platforms"]) if pl else 0
        severity, overhang = classify(t["max_length_m"], available, sdo_tolerance_m)
        out.append(
            {
                "station": station,
                "required_m": t["max_length_m"],
                "line": t["line"],
                "cars": t["cars"],
                "available_m": available,
                "n_platform_candidates": n_platforms,
                "overhang_m": round(overhang, 1) if overhang is not None else None,
                "severity": severity,
            }
        )
    return sorted(out, key=lambda r: (SEVERITY_ORDER[r["severity"]], -(r["overhang_m"] or 0)))


def render_markdown(conflicts, sdo_tolerance_m):
    by_sev = {"kritisch": [], "gering": [], "ok": [], "keine_daten": []}
    for c in conflicts:
        by_sev[c["severity"]].append(c)

    L = []
    L.append("# Bahnsteiglängen-Konfliktliste\n")
    L.append(
        f"Vergleich der aus Wagenzahl/Kupplung errechneten Zuglänge gegen reale "
        f"Bahnsteiglängen (OpenStreetMap/Overpass). SDO-Toleranz: {sdo_tolerance_m:.0f} m — "
        f"Überhang bis dahin gilt als unkritisch (Selective Door Opening bzw. bereits "
        f"eingeplante Bahnsteigverlängerung), erst darüber als echter Prüffall.\n"
    )
    L.append(
        f"- **{len(by_sev['kritisch'])} kritisch** (Überhang > {sdo_tolerance_m:.0f} m)\n"
        f"- **{len(by_sev['gering'])} gering** (SDO ausreichend)\n"
        f"- **{len(by_sev['ok'])} unauffällig**\n"
        f"- **{len(by_sev['keine_daten'])} ohne Bahnsteigdaten** (OSM-Lücke, manuell zu prüfen)\n"
    )
    L.append(
        "> **Hinweis zur Datenqualität:** OSM-Bahnsteig-Objekte sind crowd-"
        "gemappt und teils unvollständig — manche erfassen nur den überdachten "
        "Teil statt der vollen Bahnsteigkante, was eine kürzere Länge liefert "
        "als real vorhanden ist. Die Kritisch-Liste ist ein automatisierter "
        "Anfangsverdacht, kein belastbarer Befund — vor jeder Maßnahme gegen "
        "DB InfraGO-Daten (für deutsche Stationen) bzw. Ortskenntnis "
        "gegenprüfen.\n"
    )

    L.append("## Kritisch\n")
    if by_sev["kritisch"]:
        L.append("| Station | Linie | Wagen | benötigt | verfügbar | Überhang |")
        L.append("|---|---|---|---|---|---|")
        for c in by_sev["kritisch"]:
            L.append(
                f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m | "
                f"{c['available_m']:.0f} m | **+{c['overhang_m']:.0f} m** |"
            )
    else:
        L.append("Keine.")
    L.append("")

    L.append(f"## Gering (SDO/geplante Verlängerung ausreichend, ≤{sdo_tolerance_m:.0f} m)\n")
    if by_sev["gering"]:
        L.append("| Station | Linie | Wagen | benötigt | verfügbar | Überhang |")
        L.append("|---|---|---|---|---|---|")
        for c in by_sev["gering"]:
            L.append(
                f"| {c['station']} | {c['line']} | {c['cars']} | {c['required_m']:.0f} m | "
                f"{c['available_m']:.0f} m | +{c['overhang_m']:.0f} m |"
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
    ap.add_argument("--sdo-tolerance-m", type=float, default=25.0)
    ap.add_argument("--out", default="data/platform_conflicts.md")
    ap.add_argument("--json-out", default="data/platform_conflicts.json")
    args = ap.parse_args()

    train_lengths = json.loads(pathlib.Path(args.train_lengths).read_text(encoding="utf-8"))
    platform_lengths = json.loads(pathlib.Path(args.platform_lengths).read_text(encoding="utf-8"))

    conflicts = build_conflicts(train_lengths, platform_lengths, args.sdo_tolerance_m)

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
