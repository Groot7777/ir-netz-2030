#!/usr/bin/env python3
"""
Paket 7 — Solver Stufe 1: reine Phasenoptimierung (nur takt.start/end und
extraTrips verschieben sich; Fahr-/Haltezeiten unangetastet). Simulated
Annealing über die freien Phasenvariablen, S10 bleibt unangetastet
(10-Min-Takt, kein Taktknoten-Bedarf).

Zielfunktion (Anschlussqualität klar vorrangig, wie besprochen):
  w1 · Knotenanschluss an den 30 Stationen aus Paket 6 (node_plan.json)
  w2 · Taktabstand auf den Parallelkorridoren (aus score.py-Logik)
  w3 · Taktgruppen-Referenzpunkt (S3/S30 @ Essen Hbf, RE35/RE35X @ Berlin Hbf (tief))
  w4 · Symmetrie (Tie-Breaker, niedriges Gewicht)
  w5 · Fahrzeugbedarf ggü. Baseline (Tie-Breaker, niedriges Gewicht)

Kupplungs-Gleichheiten (RE30/RE90b/RE91) werden VOR der Optimierung als
Variablenreduktion behandelt (gekuppelte Zugteile sind eine Variable,
kein separates Constraint), nicht als Penalty — sie können nicht verletzt
werden, weil es die verletzende Variable gar nicht gibt.

Nutzung:
    python3 tools/solver.py --iterations 40000 --seed 1 \
        --out data/optimized_phases.json
"""
import argparse
import collections
import json
import math
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score import (  # noqa: E402
    base_lines,
    is_sbahn,
    stop_arr,
    stop_dep,
    to_min,
    variant_weight,
)

REFERENCE_GROUPS = [
    # (Linie A, Linie B, Referenzstation, gewünschter Versatz in Minuten)
    ("S3", "S30", "Essen Hbf", 15),
    ("RE35", "RE35X", "Berlin Hbf (tief)", 30),
]


# ---------------------------------------------------------------------------
# Variablenreduktion: gekuppelte Zugteile sind eine Variable
# ---------------------------------------------------------------------------

def build_variable_groups(data):
    fixed = set()
    for k, v in data.items():
        t = v["takt"]
        if t.get("note") and "10-Min-Takt" in t["note"]:
            fixed.add(k)

    derived = {}  # key -> (base_key, delta)   phase[key] = (phase[base_key] + delta) % T[key]
    for k, v in data.items():
        if k in fixed or k in derived:
            continue
        cp = v.get("coupling")
        if not cp:
            continue
        other = cp["partner"]
        if other in derived or other == k or other in fixed:
            continue
        T = v["takt"]["interval"]
        meet = cp.get("coupledFrom")
        if meet is None:
            derived[other] = (k, 0)
        else:
            off_self = next(s["off"] for s in v["stops"] if s["name"] == meet)
            off_other = next(s["off"] for s in data[other]["stops"] if s["name"] == meet)
            delta = (off_self - off_other) % T
            derived[other] = (k, delta)

    free = [k for k in data if k not in fixed and k not in derived]
    return free, derived, fixed


def resolve_phase(key, phases, derived, base_phase):
    """Phase einer Variante — frei, gekuppelt-abgeleitet, oder fix (S10:
    unverändert aus der App übernommen, siehe base_phase)."""
    if key in phases:
        return phases[key]
    if key in derived:
        base_key, delta = derived[key]
        return (resolve_phase(base_key, phases, derived, base_phase) + delta) % 1440
    return base_phase[key]


# ---------------------------------------------------------------------------
# Vorbereitung: statische Strukturen, die sich während der Optimierung
# nicht ändern (nur einmal berechnet, nicht pro SA-Iteration)
# ---------------------------------------------------------------------------

def _coupling_group_id(k, v, edge_keys_present):
    cp = v.get("coupling")
    if cp and cp.get("partner") in edge_keys_present:
        return frozenset({k, cp["partner"]})
    return frozenset({k})


def prepare_corridors(data):
    """Wie score.py corridor_headways(), aber ohne Phase — liefert nur die
    Struktur (welche Variante an welcher Kante mit welchem off dep hat),
    die Auswertung mit tatsächlichen Phasen passiert pro SA-Iteration."""
    de = collections.defaultdict(list)
    for k, v in data.items():
        sl = v["stops"]
        for a, b in zip(sl, sl[1:]):
            de[(a["name"], b["name"])].append({"key": k, "line": v["name"], "off": stop_dep(a)})

    corridors = []
    for (a, b), rows in de.items():
        names = {r["line"] for r in rows}
        if len(names) < 2:
            continue
        keys_present = {r["key"] for r in rows}
        groups = collections.defaultdict(list)
        for r in rows:
            gid = _coupling_group_id(r["key"], data[r["key"]], keys_present)
            groups.setdefault(gid, []).append(r)
        merged = [{"key": grp[0]["key"], "off": grp[0]["off"]} for grp in groups.values()]
        if len(merged) < 2:
            continue
        corridors.append(merged)
    return corridors


def prepare_knot_terms(data, node_plan, base_phase, derived, fixed, prefilter_min=15,
                        protect_weights=None):
    """Für jeden (Variante, Knoten)-Paar mit plausibler Ist-Nähe (<=
    prefilter_min Minuten zur Knotenzeit im Ist-Zustand) ein Objektiv-Element.
    Fixiert VOR der Optimierung, welche Linien an welchem Knoten mitspielen —
    weiche Variante des b[v,k]-Bindungsgedankens aus der Planung.

    protect_weights: {Station: Multiplikator} — Terme dieser Stationen werden
    zusätzlich hochgewichtet, für gezieltes Nachjustieren von Knoten, die in
    einem vorherigen Lauf schlechter wurden, ohne die übrige Zielfunktion neu
    abzustimmen. Pro Station individuell, weil ein einzelner Faktor für alle
    Knoten mit sehr unterschiedlichem Score (score_by-Gewicht fließt separat
    ein) nicht gleich stark wirkt."""
    protect_weights = protect_weights or {}
    theta = node_plan["theta"]
    score_by = {r["station"]: r["score"] for r in node_plan["ranked"]}
    terms = []
    for k, v in data.items():
        if k in fixed:
            continue
        w = variant_weight(v)
        if w == 0:
            continue
        T = v["takt"]["interval"]
        for s in v["stops"]:
            st = s["name"]
            if st not in theta:
                continue
            th = theta[st]
            arr0 = (base_phase.get(k, 0) + stop_arr(s)) % 60
            dep0 = (base_phase.get(k, 0) + stop_dep(s)) % 60
            dist0 = min(circ_dist(arr0, th), circ_dist(dep0, th))
            if dist0 > prefilter_min:
                continue
            mult = protect_weights.get(st, 1.0)
            terms.append(
                {
                    "key": k,
                    "station": st,
                    "off_arr": stop_arr(s),
                    "off_dep": stop_dep(s),
                    "T": T,
                    "theta": th,
                    "weight": w * (score_by.get(st, 1.0) ** 0.5) * mult,
                }
            )
    return terms


def circ_dist(a, b, modulus=60):
    d = abs(a - b) % modulus
    return min(d, modulus - d)


def prepare_symmetry_pairs(data):
    bl = base_lines(data)
    pairs = []
    for name, keys in bl.items():
        if len(keys) != 2:
            continue
        a, b = keys
        va, vb = data[a], data[b]
        if va["stops"][0]["name"] != vb["stops"][-1]["name"]:
            continue
        ta = {s["name"]: stop_arr(s) for s in va["stops"]}
        tb = {s["name"]: stop_dep(s) for s in vb["stops"]}
        common = [(ta[n], tb[n]) for n in ta if n in tb]
        if common:
            pairs.append({"a": a, "b": b, "common": common})
    return pairs


def prepare_fleet_lines(data):
    bl = base_lines(data)
    out = []
    for name, keys in bl.items():
        if len(keys) != 2:
            continue
        a, b = keys
        va, vb = data[a], data[b]
        if va["stops"][0]["name"] != vb["stops"][-1]["name"]:
            continue
        T = va["takt"]["interval"]
        Da, Db = va["stops"][-1]["off"], vb["stops"][-1]["off"]
        wmin = 20 if is_sbahn(name) else 70
        out.append({"a": a, "b": b, "T": T, "Da": Da, "Db": Db, "wmin": wmin})
    return out


# ---------------------------------------------------------------------------
# Zielfunktion
# ---------------------------------------------------------------------------

def objective(phases, derived, base_phase, corridors, knot_terms, ref_groups_resolved,
              symmetry_pairs, fleet_lines, weights):
    def ph(k):
        return resolve_phase(k, phases, derived, base_phase)

    cost = 0.0

    # C2 — Knotenanschluss
    knot_cost = 0.0
    for t in knot_terms:
        p = ph(t["key"])
        arr = (p + t["off_arr"]) % t["T"]
        dep = (p + t["off_dep"]) % t["T"]
        x = (t["theta"] - arr) % t["T"]  # Minuten vor der Knotenzeit
        y = (dep - t["theta"]) % t["T"]  # Minuten nach der Knotenzeit
        pen = max(0, x - 4) ** 2 + max(0, 1 - y) ** 2 + max(0, y - 4) ** 2
        knot_cost += t["weight"] * pen
    cost += weights["knot"] * knot_cost

    # C4 — Taktabstand auf Parallelkorridoren
    corridor_cost = 0.0
    for corridor in corridors:
        mins = sorted((ph(m["key"]) + m["off"]) % 60 for m in corridor)
        n = len(mins)
        ideal = 60 / n
        gaps = [(mins[(i + 1) % n] - mins[i]) % 60 for i in range(n)]
        corridor_cost += sum((g - ideal) ** 2 for g in gaps) / n
    cost += weights["corridor"] * corridor_cost

    # C12 — Taktgruppen-Referenzpunkt
    ref_cost = 0.0
    for g in ref_groups_resolved:
        pa = (ph(g["a"]) + g["off_a"]) % g["T"]
        pb = (ph(g["b"]) + g["off_b"]) % g["T"]
        actual = (pb - pa) % g["T"]
        ref_cost += circ_dist(actual, g["want"], g["T"]) ** 2
    cost += weights["reference"] * ref_cost

    # C3 — Symmetrie (Tie-Breaker)
    sym_cost = 0.0
    for pair in symmetry_pairs:
        pa, pb = ph(pair["a"]), ph(pair["b"])
        vals = [((pa + a) + (pb + b)) % 60 for a, b in pair["common"]]
        sym_cost += sum(circ_dist(v, 0) ** 2 for v in vals) / len(vals)
    cost += weights["symmetry"] * sym_cost

    # w5 — Fahrzeugbedarf ggü. Baseline (Tie-Breaker)
    fleet_cost = 0.0
    for f in fleet_lines:
        sa, sb = ph(f["a"]), ph(f["b"])
        T = f["T"]
        old = (f["Da"] + f["Db"] + (sb - sa - f["Da"]) % T + (sa - sb - f["Db"]) % T) // T
        k = math.ceil((f["Da"] + f["Db"] + 2 * f["wmin"]) / T)
        fleet_cost += max(0, k - old)
    cost += weights["fleet"] * fleet_cost

    return cost, {
        "knot": knot_cost, "corridor": corridor_cost, "reference": ref_cost,
        "symmetry": sym_cost, "fleet": fleet_cost,
    }


def resolve_reference_groups(data):
    out = []
    for name_a, name_b, station, want in REFERENCE_GROUPS:
        ka = next(k for k, v in data.items() if v["name"] == name_a and station in {s["name"] for s in v["stops"]})
        kb = next(k for k, v in data.items() if v["name"] == name_b and station in {s["name"] for s in v["stops"]})
        off_a = next(s["dep"] if s.get("dep") is not None else s["off"] for s in data[ka]["stops"] if s["name"] == station)
        off_b = next(s["dep"] if s.get("dep") is not None else s["off"] for s in data[kb]["stops"] if s["name"] == station)
        T = data[ka]["takt"]["interval"]
        out.append({"a": ka, "b": kb, "off_a": off_a, "off_b": off_b, "T": T, "want": want})
    return out


# ---------------------------------------------------------------------------
# Simulated Annealing
# ---------------------------------------------------------------------------

def anneal(free, derived, base_phase, T_by_key, corridors, knot_terms, ref_groups,
           symmetry_pairs, fleet_lines, weights, iterations, seed):
    rng = random.Random(seed)
    phases = {k: base_phase.get(k, 0) % T_by_key[k] for k in free}
    cost, _ = objective(phases, derived, base_phase, corridors, knot_terms, ref_groups,
                         symmetry_pairs, fleet_lines, weights)
    best_phases, best_cost = dict(phases), cost

    t0, t1 = 8.0, 0.02
    for i in range(iterations):
        frac = i / max(1, iterations - 1)
        temp = t0 * (t1 / t0) ** frac

        k = rng.choice(free)
        old_val = phases[k]
        T = T_by_key[k]
        if rng.random() < 0.5:
            phases[k] = rng.randrange(T)
        else:
            phases[k] = (old_val + rng.choice([-2, -1, 1, 2])) % T

        new_cost, _ = objective(phases, derived, base_phase, corridors, knot_terms, ref_groups,
                                 symmetry_pairs, fleet_lines, weights)
        delta = new_cost - cost
        if delta <= 0 or rng.random() < math.exp(-delta / max(temp, 1e-9)):
            cost = new_cost
            if cost < best_cost:
                best_cost, best_phases = cost, dict(phases)
        else:
            phases[k] = old_val

    return best_phases, best_cost


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--node-plan", default="data/node_plan.json")
    ap.add_argument("--iterations", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="data/optimized_phases.json")
    ap.add_argument("--w-knot", type=float, default=1.0)
    ap.add_argument("--w-corridor", type=float, default=0.6)
    ap.add_argument("--w-reference", type=float, default=1.0)
    ap.add_argument("--w-symmetry", type=float, default=0.05)
    ap.add_argument("--w-fleet", type=float, default=0.2)
    ap.add_argument(
        "--protect", default="",
        help=(
            "Komma-getrennt 'Station' oder 'Station=Faktor' (Faktor optional, "
            "sonst --protect-multiplier) — Knoten-Terme dieser Stationen werden "
            "zusätzlich hochgewichtet."
        ),
    )
    ap.add_argument("--protect-multiplier", type=float, default=4.0)
    ap.add_argument(
        "--fix-phase", default="",
        help=(
            "Komma-getrennt 'Variantenschlüssel=Phase' — diese Varianten werden "
            "auf die angegebene Phase hart fixiert (nicht optimiert), z.B. um "
            "eine hypothetische Zielsituation zu testen und zu sehen, was sich "
            "im Rest des Netzes dadurch verschiebt."
        ),
    )
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    node_plan = json.loads(pathlib.Path(args.node_plan).read_text(encoding="utf-8"))

    free, derived, fixed = build_variable_groups(data)
    base_phase = {k: to_min(v["takt"]["start"]) % v["takt"]["interval"] for k, v in data.items()}
    T_by_key = {k: v["takt"]["interval"] for k, v in data.items()}

    fix_phase = {}
    for item in args.fix_phase.split(","):
        item = item.strip()
        if not item:
            continue
        k, val = item.rsplit("=", 1)
        fix_phase[k.strip()] = int(val)
    opt_base_phase = dict(base_phase)
    for k, val in fix_phase.items():
        opt_base_phase[k] = val
        if k in free:
            free.remove(k)
        fixed.add(k)
    if fix_phase:
        print(f"Hart fixierte Varianten: {fix_phase}")

    corridors = prepare_corridors(data)
    protect_weights = {}
    for item in args.protect.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            st, mult = item.rsplit("=", 1)
            protect_weights[st.strip()] = float(mult)
        else:
            protect_weights[item] = args.protect_multiplier
    knot_terms = prepare_knot_terms(
        data, node_plan, opt_base_phase, derived, fixed, protect_weights=protect_weights,
    )
    if protect_weights:
        print(f"Geschützte Stationen: {protect_weights}")
    ref_groups = resolve_reference_groups(data)
    symmetry_pairs = prepare_symmetry_pairs(data)
    fleet_lines = prepare_fleet_lines(data)

    weights = {
        "knot": args.w_knot, "corridor": args.w_corridor, "reference": args.w_reference,
        "symmetry": args.w_symmetry, "fleet": args.w_fleet,
    }

    print(f"{len(free)} freie Variablen, {len(derived)} gekuppelt-abgeleitet, {len(fixed)} fix (S10)")
    print(f"{len(corridors)} Korridore, {len(knot_terms)} Knoten-Terme, {len(ref_groups)} Referenzgruppen, "
          f"{len(symmetry_pairs)} Symmetrie-Paare, {len(fleet_lines)} Flotten-Linien")

    base_cost, base_breakdown = objective(
        {k: opt_base_phase[k] for k in free}, derived, opt_base_phase, corridors, knot_terms,
        ref_groups, symmetry_pairs, fleet_lines, weights,
    )
    print(f"Ist-Kosten: {base_cost:.1f} {base_breakdown}")

    best_phases, best_cost = anneal(
        free, derived, opt_base_phase, T_by_key, corridors, knot_terms, ref_groups,
        symmetry_pairs, fleet_lines, weights, args.iterations, args.seed,
    )
    _, best_breakdown = objective(best_phases, derived, opt_base_phase, corridors, knot_terms,
                                   ref_groups, symmetry_pairs, fleet_lines, weights)
    print(f"Optimiert: {best_cost:.1f} {best_breakdown}  (Δ {best_cost - base_cost:+.1f}, "
          f"{(1 - best_cost / base_cost) * 100 if base_cost else 0:.0f}% besser)")

    all_phases = {}
    for k in data:
        if k in fixed:
            continue
        all_phases[k] = resolve_phase(k, best_phases, derived, opt_base_phase)
    for k, val in fix_phase.items():
        all_phases[k] = val

    pathlib.Path(args.out).write_text(
        json.dumps({"phases": all_phases, "base_phase": base_phase, "fixed": sorted(fixed)},
                    ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
