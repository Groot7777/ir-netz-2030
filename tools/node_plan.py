#!/usr/bin/env python3
"""
Paket 6: Finale Knotenliste für die Taktoptimierung — Ranking (mit
Endknoten-Bonus, aus score.py), θ-Zuordnung (Symmetrie-Anker 0/30 Min,
Schweizer Stil) und Gleiskapazität (aus amtlichen DB-InfraGO-Daten wo
vorhanden) in einem Report, zur Freigabe durch den Nutzer VOR dem Solver.

θ-Zuordnung: greedy, beginnend bei den höchst-gerankten Stationen. Ein
Knotenpaar ist kompatibel, wenn ihre direkte Fahrzeit (entlang einer sie
verbindenden Linie) nahe an einem Vielfachen von 30 Minuten liegt
(Toleranz konfigurierbar). Stationen, die sich nicht widerspruchsfrei
einfügen lassen, werden NICHT automatisch entschieden, sondern als
Konflikt ausgewiesen — das ist eine Aussage, die der Nutzer treffen muss,
kein Automatismus.

Nutzung:
    python3 tools/node_plan.py --top-n 30 --tolerance 6 \
        --force "Essen Hbf=0,Dortmund Hbf=0" \
        --out data/node_plan.md
"""
import argparse
import collections
import itertools
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import (  # noqa: E402
    hub_ranking,
    node_minute_table,
    stop_dep,
    variant_weight,
)


def pairwise_hub_travel_times(data, candidates):
    """Direkte Fahrzeit (Minuten) zwischen je zwei Kandidaten-Hubs entlang
    jeder Linie, die beide bedient (S10 ausgenommen, siehe variant_weight)."""
    cs = set(candidates)
    pair_times = collections.defaultdict(list)
    for k, v in data.items():
        if variant_weight(v) == 0:
            continue
        idx = [(i, s) for i, s in enumerate(v["stops"]) if s["name"] in cs]
        for (i1, s1), (i2, s2) in itertools.combinations(idx, 2):
            if s1["name"] == s2["name"]:
                continue
            tt = s2["off"] - stop_dep(s1)
            if tt <= 0:
                continue
            pair_times[tuple(sorted((s1["name"], s2["name"])))].append((v["name"], tt))
    return pair_times


def assign_theta(ranked_names, pair_times, forced, tolerance):
    """Greedy θ-Zuordnung. forced: {station: theta} wird unangetastet als
    Startpunkt übernommen (Ruhr-Entscheidung o.ä.), auch wenn die direkte
    Fahrzeit zwischen zwei forcierten Stationen selbst nicht ideal passt —
    das ist eine bewusste Nutzerentscheidung, kein Rechenergebnis."""
    sel = dict(forced)
    conflicts = []
    for name in ranked_names:
        if name in sel:
            continue
        theta = None
        reason = None
        for other, th_other in list(sel.items()):
            p = tuple(sorted((name, other)))
            if p not in pair_times:
                continue
            for line, tt in pair_times[p]:
                m = tt % 60
                dev = min(m, abs(m - 30), 60 - m)
                if dev > tolerance:
                    reason = f"{line}: {other}↔{name} {tt} Min (Abw. {dev} vom 30er-Raster)"
                    break
                delta = 0 if min(m, 60 - m) < abs(m - 30) else 30
                want = (th_other + delta) % 60
                if theta is None:
                    theta = want
                elif theta != want:
                    reason = f"θ-Widerspruch über {other} ({line})"
                    break
            if reason:
                break
        if reason:
            conflicts.append({"station": name, "reason": reason})
        else:
            sel[name] = theta if theta is not None else 0
    return sel, conflicts


def platform_capacity(station, dbinfrago, manual, osm):
    """Gleiskapazität aus derselben Prioritätskette wie platform_conflicts.py:
    fiktive Planung > amtliche DB-InfraGO-Daten > OSM-Schätzung."""
    for source_name, source in (("fiktiv", manual), ("amtlich", dbinfrago)):
        entry = source.get(station)
        if entry and entry.get("tracks"):
            lengths = sorted((t["length_m"] for t in entry["tracks"]), reverse=True)
            return {"source": source_name, "n_tracks": len(lengths), "lengths_m": lengths}
    entry = osm.get(station)
    if entry and entry.get("platforms"):
        lengths = sorted(
            (p["length_m"] for p in entry["platforms"] if p["plausible"]), reverse=True
        )
        if lengths:
            return {"source": "osm", "n_tracks": len(lengths), "lengths_m": lengths}
    return {"source": None, "n_tracks": 0, "lengths_m": []}


def render_markdown(ranked, theta, conflicts, capacity, minute_tables, sigma_ref):
    L = []
    L.append("# Paket 6 — Finale Knotenliste (zur Freigabe)\n")
    L.append(
        f"Symmetrieminute σ = :{sigma_ref:02d} (Schweizer Stil). θ-Werte sind relativ "
        f"zu einem Anker — welche absolute Minute σ=:00 real bekommt, legt erst die "
        f"spätere Ankerlinie fest.\n"
    )

    L.append("## Zugeordnete Knoten\n")
    L.append("| # | Station | Score | θ | Gleise | Längste verfügbare Gleise (m) | Quelle |")
    L.append("|---|---|---|---|---|---|---|")
    for i, (name, score) in enumerate(ranked, 1):
        if name not in theta:
            continue
        cap = capacity[name]
        top_lengths = ", ".join(f"{l:.0f}" for l in cap["lengths_m"][:6])
        src = cap["source"] or "keine Daten"
        L.append(f"| {i} | {name} | {score:.1f} | :{theta[name]:02d} | {cap['n_tracks']} | {top_lengths} | {src} |")
    L.append("")

    L.append(f"## Konflikte — {len(conflicts)} Stationen ohne widerspruchsfreie θ-Zuordnung\n")
    L.append(
        "Diese Stationen lassen sich nicht widerspruchsfrei in das θ∈{0,30}-Raster "
        "einfügen (Fahrzeit zu einer bereits zugeordneten Station passt nicht auf "
        "ein Vielfaches von 30 Min, oder zwei Nachbarn verlangen widersprüchliche θ). "
        "**Das ist eine Entscheidung, keine Berechnung** — mögliche Auflösungen: "
        "Halbknoten statt Vollknoten, Fahrzeit-Streckung (Stufe 2), oder bewusst "
        "kein Taktknoten an dieser Station.\n"
    )
    if conflicts:
        L.append("| Station | Score | Konflikt |")
        L.append("|---|---|---|")
        score_by_name = dict(ranked)
        for c in conflicts:
            L.append(f"| {c['station']} | {score_by_name.get(c['station'], 0):.1f} | {c['reason']} |")
    else:
        L.append("Keine.")
    L.append("")

    L.append("## Ist-Ankunfts-/Abfahrtsminuten an den zugeordneten Knoten (heute, vor Optimierung)\n")
    for name, _ in ranked:
        if name not in theta:
            continue
        rows = minute_tables[name]
        if not rows:
            continue
        L.append(f"### {name} (θ=:{theta[name]:02d})\n")
        L.append("| Linie | T | an | ab |")
        L.append("|---|---|---|---|")
        for r in rows:
            L.append(f"| {r['line']} | {r['interval']} | :{r['arr']:02d} | :{r['dep']:02d} |")
        L.append("")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--dbinfrago", default="data/dbinfrago_platforms.json")
    ap.add_argument("--manual-overrides", default="data/manual_overrides.json")
    ap.add_argument("--platform-lengths", default="data/platform_lengths.json")
    ap.add_argument("--top-n", type=int, default=30)
    ap.add_argument("--tolerance", type=int, default=6, help="max. Minuten Abweichung vom 30er-Raster")
    ap.add_argument(
        "--force",
        default="Essen Hbf=0,Dortmund Hbf=0",
        help="Komma-getrennt 'Station=theta', wird ungeprüft als Startpunkt übernommen",
    )
    ap.add_argument("--out", default="data/node_plan.md")
    ap.add_argument("--json-out", default="data/node_plan.json")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    dbinfrago = json.loads(pathlib.Path(args.dbinfrago).read_text(encoding="utf-8"))
    manual = json.loads(pathlib.Path(args.manual_overrides).read_text(encoding="utf-8"))
    osm = json.loads(pathlib.Path(args.platform_lengths).read_text(encoding="utf-8"))

    hubs = hub_ranking(data, top_n=args.top_n)
    ranked = [(h["station"], h["score"]) for h in hubs]
    names = [n for n, _ in ranked]

    forced = {}
    for pair in args.force.split(","):
        pair = pair.strip()
        if not pair:
            continue
        st, th = pair.rsplit("=", 1)
        forced[st.strip()] = int(th)

    pair_times = pairwise_hub_travel_times(data, names)
    theta, conflicts = assign_theta(names, pair_times, forced, args.tolerance)

    capacity = {n: platform_capacity(n, dbinfrago, manual, osm) for n in names}
    minute_tables = {n: node_minute_table(data, n) for n in names}

    result = {
        "ranked": [{"station": n, "score": s} for n, s in ranked],
        "theta": theta,
        "conflicts": conflicts,
        "capacity": capacity,
    }
    pathlib.Path(args.json_out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = render_markdown(ranked, theta, conflicts, capacity, minute_tables, sigma_ref=0)
    pathlib.Path(args.out).write_text(md, encoding="utf-8")

    print(f"{len(theta)} Stationen zugeordnet, {len(conflicts)} Konflikte -> {args.out}")


if __name__ == "__main__":
    main()
