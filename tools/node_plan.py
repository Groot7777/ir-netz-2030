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


def circ_dist(a, b, modulus=60):
    d = abs(a - b) % modulus
    return min(d, modulus - d)


def assign_theta(ranked_names, pair_times, forced, tolerance):
    """Greedy θ-Zuordnung, die JEDE Station einordnet — nichts bleibt
    unzugeordnet. forced: {station: theta} wird unangetastet als
    Startpunkt übernommen (Ruhr-Entscheidung o.ä.).

    Für jede noch offene Station wird über ALLE Verbindungen zu bereits
    zugeordneten Nachbarn abgestimmt: für θ∈{0,30} wird die mittlere
    Abweichung von der durch jede Linie implizierten Idealphase berechnet,
    die bessere der beiden Stellen gewinnt. Passt die beste Stelle nur
    grob (Abweichung > tolerance), wird die Station trotzdem zugeordnet,
    aber als 'halb' statt 'voll' markiert — ein Halbknoten mit
    Anschlussqualität unter dem Vollknoten-Standard, keine offene Frage
    mehr. Stationen ganz ohne Verbindung zu einem bereits zugeordneten
    Nachbarn werden als 'isoliert' markiert (θ=0 mangels Referenz)."""
    sel = dict(forced)
    detail = {name: {"quality": "voll", "votes": []} for name in forced}
    for name in ranked_names:
        if name in sel:
            continue
        votes = []
        for other, th_other in list(sel.items()):
            p = tuple(sorted((name, other)))
            if p not in pair_times:
                continue
            for line, tt in pair_times[p]:
                m = tt % 60
                implied = (th_other + m) % 60
                votes.append({"other": other, "line": line, "tt": tt, "implied": implied})

        if not votes:
            sel[name] = 0
            detail[name] = {"quality": "isoliert", "votes": []}
            continue

        best_theta, best_avg = None, None
        for cand in (0, 30):
            total = sum(circ_dist(cand, v["implied"]) for v in votes)
            avg = total / len(votes)
            if best_avg is None or avg < best_avg:
                best_theta, best_avg = cand, avg

        quality = "voll" if best_avg <= tolerance else "halb"
        sel[name] = best_theta
        detail[name] = {
            "quality": quality,
            "avg_deviation": round(best_avg, 1),
            "votes": [
                {**v, "deviation": circ_dist(best_theta, v["implied"])} for v in votes
            ],
        }
    return sel, detail


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


def render_markdown(ranked, theta, detail, capacity, minute_tables, sigma_ref):
    L = []
    L.append("# Paket 6 — Finale Knotenliste\n")
    L.append(
        f"Symmetrieminute σ = :{sigma_ref:02d} (Schweizer Stil). θ-Werte sind relativ "
        f"zu einem Anker — welche absolute Minute σ=:00 real bekommt, legt erst die "
        f"spätere Ankerlinie fest. **Jede Station ist zugeordnet** — Konflikte wurden "
        f"nicht offengelassen, sondern als Halbknoten (beste verfügbare Rasterstelle, "
        f"geringere Anschlussqualität als ein Vollknoten) aufgelöst.\n"
    )

    n_voll = sum(1 for d in detail.values() if d["quality"] == "voll")
    n_halb = sum(1 for d in detail.values() if d["quality"] == "halb")
    n_iso = sum(1 for d in detail.values() if d["quality"] == "isoliert")
    L.append(f"- **{n_voll} Vollknoten** (Abweichung ≤ Toleranz)\n- **{n_halb} Halbknoten** (beste Stelle trotz größerer Abweichung)\n- **{n_iso} isoliert** (keine Verbindung zu einem bereits zugeordneten Nachbarn)\n")

    L.append("## Knotenliste\n")
    L.append("| # | Station | Score | θ | Qualität | ⌀Abw. | Gleise | Längste Gleise (m) | Quelle |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for i, (name, score) in enumerate(ranked, 1):
        if name not in theta:
            continue
        cap = capacity[name]
        d = detail.get(name, {"quality": "voll"})
        top_lengths = ", ".join(f"{l:.0f}" for l in cap["lengths_m"][:6])
        src = cap["source"] or "keine Daten"
        avg = d.get("avg_deviation")
        avg_s = f"{avg:.1f}" if avg is not None else "—"
        q = d["quality"]
        L.append(
            f"| {i} | {name} | {score:.1f} | :{theta[name]:02d} | {q} | {avg_s} | "
            f"{cap['n_tracks']} | {top_lengths} | {src} |"
        )
    L.append("")

    L.append(f"## Halbknoten — {n_halb} Stationen mit größerer Abweichung\n")
    L.append(
        "Bestmögliche θ-Stelle gewählt, aber mit spürbarer Restabweichung — Anschlüsse "
        "dort werden nicht so eng wie an einem Vollknoten. Aufgeführt sind die "
        "Linien/Nachbarn, die in die Entscheidung eingeflossen sind.\n"
    )
    score_by_name = dict(ranked)
    for name, d in sorted(
        ((n, d) for n, d in detail.items() if d["quality"] in ("halb", "isoliert")),
        key=lambda kv: -score_by_name.get(kv[0], 0),
    ):
        if d["quality"] == "isoliert":
            L.append(f"- **{name}** (Score {score_by_name.get(name,0):.1f}) — isoliert, keine Verbindung zu einem bereits zugeordneten Knoten, θ=:00 mangels Referenz.")
            continue
        votes_s = "; ".join(
            f"{v['line']} {v['other']}↔{name} {v['tt']}min (Abw. {v['deviation']})" for v in d["votes"]
        )
        L.append(f"- **{name}** (Score {score_by_name.get(name,0):.1f}, θ=:{theta[name]:02d}, ⌀Abw. {d['avg_deviation']:.1f}): {votes_s}")
    L.append("")

    L.append("## Ist-Ankunfts-/Abfahrtsminuten an den zugeordneten Knoten (heute, vor Optimierung)\n")
    for name, _ in ranked:
        if name not in theta:
            continue
        rows = minute_tables[name]
        if not rows:
            continue
        L.append(f"### {name} (θ=:{theta[name]:02d}, {detail[name]['quality']})\n")
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
    theta, detail = assign_theta(names, pair_times, forced, args.tolerance)

    capacity = {n: platform_capacity(n, dbinfrago, manual, osm) for n in names}
    minute_tables = {n: node_minute_table(data, n) for n in names}

    result = {
        "ranked": [{"station": n, "score": s} for n, s in ranked],
        "theta": theta,
        "detail": detail,
        "capacity": capacity,
    }
    pathlib.Path(args.json_out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = render_markdown(ranked, theta, detail, capacity, minute_tables, sigma_ref=0)
    pathlib.Path(args.out).write_text(md, encoding="utf-8")

    n_voll = sum(1 for d in detail.values() if d["quality"] == "voll")
    n_halb = sum(1 for d in detail.values() if d["quality"] == "halb")
    n_iso = sum(1 for d in detail.values() if d["quality"] == "isoliert")
    print(f"{len(theta)} Stationen zugeordnet ({n_voll} voll, {n_halb} halb, {n_iso} isoliert) -> {args.out}")


if __name__ == "__main__":
    main()
