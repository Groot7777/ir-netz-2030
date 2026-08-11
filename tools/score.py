#!/usr/bin/env python3
"""
Bewertungsmodul für den RE-Netz-2030-Fahrplan. Unabhängig vom Solver:
misst Knotengüte, Taktabstände auf Parallelabschnitten, Symmetrie,
Fahrzeug-/Abstellbedarf und Bahnsteig-Längenkonflikte am Ist-Zustand
(oder an jeder anderen lines.json). Dient als Abnahmegrundlage — vorher/
nachher-Vergleich, nicht nur einmaliger Report.

Nutzung:
    python3 tools/score.py --data data/lines.json --out data/ist_report.md
"""
import argparse
import collections
import itertools
import json
import math
import pathlib


# ---------------------------------------------------------------------------
# Grundfunktionen
# ---------------------------------------------------------------------------

def to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def stop_dep(s):
    return s["dep"] if s.get("dep") is not None else s["off"]


def stop_arr(s):
    return s["off"]


def effective_phase(variant):
    """Bildet generateBaseDepartures() aus der App exakt nach (Stand nach
    dem Phasen-Bugfix vom 2024: der 'start==end'-Zweig — konstanter Takt
    rund um die Uhr, z.B. S3/S30/RE71 — leitet seine Phase jetzt aus
    takt.start ab, statt sie auf 0 zu erzwingen; siehe app/…html,
    generateBaseDepartures()). Der 10-Min-Takt-Zweig (S10) bleibt bewusst
    auf Phase 0 verankert — die Bänder sind an echte Uhrzeiten (04/06/21 Uhr)
    gebunden, keine frei verschiebbare Taktphase."""
    t = variant["takt"]
    interval = t["interval"]
    if t.get("note") and "10-Min-Takt" in t["note"]:
        return 0, interval
    return to_min(t["start"]) % interval, interval


def is_sbahn(name):
    return name.startswith("S")


def circular_mean(values, modulus=60):
    """Mittelwert auf dem Minuten-Kreis (arithmetisches Mittel wäre bei
    Werten wie {58,59,0} irreführend: ergäbe ~39 statt ~59)."""
    sx = sum(math.cos(2 * math.pi * v / modulus) for v in values)
    sy = sum(math.sin(2 * math.pi * v / modulus) for v in values)
    ang = math.atan2(sy, sx)
    return (ang / (2 * math.pi) * modulus) % modulus


def circular_spread(values, modulus=60):
    """Kleinste Bogenlänge auf dem Minuten-Kreis, die alle Werte enthält —
    'max-min' wäre falsch, da z.B. 58/59/0 real nur 2 Minuten auseinander
    liegen, nicht 59 (Wraparound-Bug)."""
    uniq = sorted(set(values))
    if len(uniq) <= 1:
        return 0
    gaps = [(uniq[(i + 1) % len(uniq)] - uniq[i]) % modulus for i in range(len(uniq))]
    return modulus - max(gaps)


def variant_weight(variant):
    """Gewicht für Knoten-/Umsteigerelevanz: 10-Min-Takt-Linien (S10) tragen
    nichts bei (Wartezeit dort ist irrelevant für Taktknoten-Logik),
    30-Min-Takt zählt halb, 60-Min-Takt voll."""
    t = variant["takt"]
    if t.get("note") and "10-Min-Takt" in t["note"]:
        return 0.0
    return 1.0 if t["interval"] >= 60 else 0.5


def base_lines(data):
    """base line name -> Liste der Richtungsvarianten-Keys."""
    out = collections.defaultdict(list)
    for k, v in data.items():
        out[v["name"]].append(k)
    return out


# ---------------------------------------------------------------------------
# A) Datenqualität
# ---------------------------------------------------------------------------

def check_data_quality(data):
    problems = []
    for k, v in data.items():
        sl = v["stops"]
        last = -1
        names_seen = collections.Counter(s["name"] for s in sl)
        for s in sl:
            dep = stop_dep(s)
            if s["off"] < last:
                problems.append(f"{k}: nicht-monotoner off-Wert bei {s['name']} ({s['off']} < {last})")
            if dep < s["off"]:
                problems.append(f"{k}: dep < off bei {s['name']}")
            last = max(last, dep)
        dupes = [n for n, c in names_seen.items() if c > 1]
        if dupes:
            problems.append(f"{k}: Haltename(n) mehrfach in derselben Linie (Ring): {dupes}")
    # bekannter Alias-Fehler: gleicher physischer Bahnhof unter zwei Namen
    names = {s["name"] for v in data.values() for s in v["stops"]}
    if "Bochum-Höntrop" in names and "Essen-Höntrop" in names:
        problems.append(
            "Alias-Konflikt: 'Bochum-Höntrop' (RE40) und 'Essen-Höntrop' (S10) sind "
            "derselbe physische Bahnhof, aber im Datensatz getrennt — kein Umstieg "
            "in der Routensuche, Korridorerkennung übersieht den Mischbetriebsabschnitt."
        )
    return problems


# ---------------------------------------------------------------------------
# B) Knotenranking (gewichtete Umsteigerelationen inkl. Endknoten-Bonus)
# ---------------------------------------------------------------------------

def hub_ranking(data, top_n=40):
    runs = collections.defaultdict(set)
    weight = {}
    for k, v in data.items():
        w = variant_weight(v)
        if w == 0:
            continue
        sl = v["stops"]
        for i, s in enumerate(sl):
            prev = sl[i - 1]["name"] if i > 0 else None
            nxt = sl[i + 1]["name"] if i < len(sl) - 1 else None
            runs[s["name"]].add((v["name"], prev, nxt))
            weight[(s["name"], v["name"])] = w

    score = {}
    for st, rs in runs.items():
        total = 0.0
        for a, b in itertools.combinations(rs, 2):
            if a[0] == b[0]:
                continue  # gleiche Basislinie = kein Umstieg
            for arriving, departing in ((a, b), (b, a)):
                if arriving[1] is None or departing[2] is None:
                    continue  # kann dort nicht ankommen / abfahren
                if departing[2] == arriving[1]:
                    continue  # fährt zurück, woher die andere kam
                w = min(weight[(st, a[0])], weight[(st, b[0])])
                if arriving[2] is None and departing[1] is None:
                    w *= 2.0  # beide enden/beginnen hier -> zwingender Umstieg
                elif arriving[2] is None or departing[1] is None:
                    w *= 1.5
                total += w
        if total:
            score[st] = total
    ranked = sorted(score.items(), key=lambda x: -x[1])[:top_n]
    lines_at = {st: sorted({r[0] for r in runs[st]}) for st, _ in ranked}
    return [{"station": st, "score": round(sc, 1), "lines": lines_at[st]} for st, sc in ranked]


# ---------------------------------------------------------------------------
# C) Knotengüte an ausgewählten Stationen (Ankunfts-/Abfahrtsminuten)
# ---------------------------------------------------------------------------

def node_minute_table(data, station):
    rows = []
    for k, v in data.items():
        phase, interval = effective_phase(v)
        for s in v["stops"]:
            if s["name"] != station:
                continue
            arr = (phase + stop_arr(s)) % (interval if interval < 60 else 60)
            dep = (phase + stop_dep(s)) % (interval if interval < 60 else 60)
            rows.append({"key": k, "line": v["name"], "interval": interval, "arr": arr, "dep": dep})
    return sorted(rows, key=lambda r: r["arr"])


# ---------------------------------------------------------------------------
# D) Parallelabschnitte (Korridore) und Taktabstände
# ---------------------------------------------------------------------------

def shared_corridors(data):
    """Gerichtete Kanten mit >=2 Linien, gebündelt zu zusammenhängenden
    Korridoren mit identischer Linienmenge."""
    edge_lines = collections.defaultdict(set)
    for k, v in data.items():
        sl = v["stops"]
        for a, b in zip(sl, sl[1:]):
            edge_lines[(a["name"], b["name"])].add(v["name"])

    undirected = collections.defaultdict(set)
    for (a, b), ls in edge_lines.items():
        undirected[tuple(sorted((a, b)))] |= ls

    groups = collections.defaultdict(list)
    for e, ls in undirected.items():
        if len(ls) >= 2:
            groups[frozenset(ls)].append(e)

    def chains(edges):
        adj = collections.defaultdict(list)
        for a, b in edges:
            adj[a].append(b)
            adj[b].append(a)
        edge_set = set(edges)
        seen = set()
        out = []
        for e in edges:
            if e in seen:
                continue
            comp = {e}
            stack = [e]
            seen.add(e)
            while stack:
                x = stack.pop()
                for node in x:
                    for nb in adj[node]:
                        f = tuple(sorted((node, nb)))
                        if f not in seen and f in edge_set:
                            seen.add(f)
                            comp.add(f)
                            stack.append(f)
            nodes = set()
            for a, b in comp:
                nodes.add(a)
                nodes.add(b)
            deg = collections.Counter()
            for a, b in comp:
                deg[a] += 1
                deg[b] += 1
            ends = sorted(n for n in nodes if deg[n] == 1) or sorted(nodes)[:2]
            out.append({"edges": len(comp), "ends": ends, "nodes": sorted(nodes)})
        return out

    corridors = []
    for ls, edges in groups.items():
        for c in chains(edges):
            corridors.append({"lines": sorted(ls), "n_lines": len(ls), **c})
    return sorted(corridors, key=lambda c: (-c["n_lines"], -c["edges"]))


def _coupling_group_id(k, v, edge_keys_present):
    """Physische Zugidentität für Headway-Zwecke: gekuppelte Partner (C7 —
    z.B. RE30_WL+RE30_DL nach Schwerte) sind auf dem gemeinsamen Abschnitt
    EIN Zug, kein Konflikt zwischen zwei Fahrten. Ohne diese Zusammenführung
    würde die Taktabstands-Bewertung dort fälschlich eine 0-Minuten-Lücke
    (oder nach Modulo-Korrektur eine volle 60er-Lücke) sehen."""
    cp = v.get("coupling")
    if cp and cp.get("partner") in edge_keys_present:
        return frozenset({k, cp["partner"]})
    return frozenset({k})


def corridor_headways(data):
    """Für jede gerichtete Kante mit >=2 (physisch unterscheidbaren) Linien:
    Abfahrtsminuten am Abschnittsanfang (Phase berücksichtigt), Lücken ggü.
    idealer Gleichverteilung. Gekuppelte Zugteile werden zu einem
    physischen Zug zusammengeführt (siehe _coupling_group_id)."""
    de = collections.defaultdict(list)
    for k, v in data.items():
        phase, interval = effective_phase(v)
        sl = v["stops"]
        for a, b in zip(sl, sl[1:]):
            dep = phase + stop_dep(a)
            de[(a["name"], b["name"])].append(
                {"line": v["name"], "key": k, "interval": interval, "dep_mod60": dep % 60}
            )

    out = []
    for (a, b), rows in de.items():
        keys_present = {r["key"] for r in rows}
        groups = {}
        for r in rows:
            gid = _coupling_group_id(r["key"], data[r["key"]], keys_present)
            groups.setdefault(gid, []).append(r)
        merged = []
        for gid, grp in groups.items():
            labels = "+".join(sorted({g["line"] for g in grp}))
            merged.append({"line": labels, "dep_mod60": grp[0]["dep_mod60"]})

        names = {r["line"] for r in rows}
        if len(names) < 2 or len(merged) < 2:
            continue
        mins = sorted(m["dep_mod60"] for m in merged)
        n = len(mins)
        if n == 1:
            # Modulo-Artefakt: 1 physischer Zug "trifft sich selbst" nach
            # einer vollen Stunde wieder -- kein echter 0-Minuten-Konflikt.
            gaps = [60]
        else:
            # Echte 0-Minuten-Lücken (zwei verschiedene physische Züge zur
            # exakt selben Minute) sind ein realer Taktfehler und bleiben
            # als 0 stehen, statt beschönigt zu werden.
            gaps = [(mins[(i + 1) % n] - mins[i]) % 60 for i in range(n)]
        ideal = 60 / n
        deviation = sum(abs(g - ideal) for g in gaps) / n
        out.append(
            {
                "from": a,
                "to": b,
                "lines": sorted(names),
                "departures": sorted(merged, key=lambda r: r["dep_mod60"]),
                "gaps": gaps,
                "ideal_gap": round(ideal, 1),
                "mean_deviation": round(deviation, 1),
            }
        )
    return sorted(out, key=lambda c: -c["mean_deviation"])


# ---------------------------------------------------------------------------
# E) Symmetrie je Linie (Hin-/Rückrichtung)
# ---------------------------------------------------------------------------

def symmetry_stats(data):
    bl = base_lines(data)
    out = []
    for name, keys in sorted(bl.items()):
        if len(keys) != 2:
            continue
        a, b = keys
        va, vb = data[a], data[b]
        if va["stops"][0]["name"] != vb["stops"][-1]["name"]:
            continue  # keine spiegelbildlichen Endpunkte -> kein einfaches Paar
        pa, ia = effective_phase(va)
        pb, ib = effective_phase(vb)
        ta = {s["name"]: pa + stop_arr(s) for s in va["stops"]}
        tb = {s["name"]: pb + stop_dep(s) for s in vb["stops"]}
        vals = [((ta[n] + tb[n]) % 60) for n in ta if n in tb]
        if not vals:
            continue
        c = collections.Counter(vals)
        out.append(
            {
                "line": name,
                "n_common_stops": len(vals),
                "sigma2_distribution": dict(sorted(c.items())),
                "spread": circular_spread(vals),
                "mean_sigma2": round(circular_mean(vals), 1),
            }
        )
    return out


# ---------------------------------------------------------------------------
# F) Fahrzeugbedarf — differenziertes Wendemodell
# ---------------------------------------------------------------------------

def fleet_requirements(data, wende_re_rb=70, wende_sbahn=20, reserve_per_line=1):
    bl = base_lines(data)
    out = []
    for name, keys in sorted(bl.items()):
        if len(keys) != 2:
            continue
        a, b = keys
        va, vb = data[a], data[b]
        if va["stops"][0]["name"] != vb["stops"][-1]["name"]:
            continue
        pa, T = effective_phase(va)
        pb, Tb = effective_phase(vb)
        if T != Tb or T >= 60 and va["takt"]["interval"] != vb["takt"]["interval"]:
            T = va["takt"]["interval"]
        Da = va["stops"][-1]["off"]
        Db = vb["stops"][-1]["off"]
        sa, sb = to_min(va["takt"]["start"]), to_min(vb["takt"]["start"])
        old = (Da + Db + (sb - sa - Da) % T + (sa - sb - Db) % T) // T

        wmin = wende_sbahn if is_sbahn(name) else wende_re_rb
        k = math.ceil((Da + Db + 2 * wmin) / T)
        cyc = k * T
        rest = cyc - Da - Db
        wa, wb = rest // 2, rest - rest // 2
        new_fleet = k + reserve_per_line

        out.append(
            {
                "line": name,
                "interval": T,
                "duration_A": Da,
                "duration_B": Db,
                "fleet_today": old,
                "fleet_new_incl_reserve": new_fleet,
                "delta": new_fleet - old,
                "turnaround_A_min": wa,
                "turnaround_B_min": wb,
            }
        )
    return out


# ---------------------------------------------------------------------------
# G) Abstellbedarf an Endbahnhöfen
# ---------------------------------------------------------------------------

CAR_LENGTH_M = {3: 80, 4: 105, 5: 130, 6: 156, 7: 184, 8: 210}


def car_length(n_cars):
    return CAR_LENGTH_M.get(n_cars, round(n_cars * 26.2))


def stabling_demand(data, cleaning_min=80, reserve_per_line=1):
    end = collections.defaultdict(list)
    for k, v in data.items():
        t = v["takt"]
        if t.get("note") and "10-Min-Takt" in t["note"]:
            continue
        end[v["stops"][-1]["name"]].append(
            {"name": v["name"], "interval": t["interval"], "cars": v["cars"]}
        )

    out = []
    for st, entries in end.items():
        by_line = {}
        for e in entries:
            by_line[e["name"]] = e  # beide Richtungen enden ggf. an derselben Station
        slots = 0
        length_m = 0
        detail = []
        for name, e in by_line.items():
            s = math.ceil(cleaning_min / e["interval"]) + reserve_per_line
            L = car_length(e["cars"])
            slots += s
            length_m += s * L
            detail.append({"line": name, "slots": s, "car_length_m": L})
        if len(by_line) >= 1:
            out.append(
                {
                    "station": st,
                    "n_lines": len(by_line),
                    "slots": slots,
                    "total_length_m": length_m,
                    "detail": detail,
                }
            )
    return sorted(out, key=lambda r: (-r["n_lines"], -r["slots"]))


# ---------------------------------------------------------------------------
# H) Zuglänge je Halt (inkl. Kupplung/coupledSection) -> Bahnsteig-Mindestlänge
# ---------------------------------------------------------------------------

def _stop_index(variant, name):
    for i, s in enumerate(variant["stops"]):
        if s["name"] == name:
            return i
    return None


def train_length_per_stop(data):
    max_len = collections.defaultdict(int)
    who = collections.defaultdict(list)
    for k, v in data.items():
        sl = v["stops"]
        n = len(sl)
        extra_cars = [0] * n
        cp = v.get("coupling")
        if cp:
            a = _stop_index(v, cp["coupledFrom"]) if cp.get("coupledFrom") else 0
            b = _stop_index(v, cp["coupledTo"]) if cp.get("coupledTo") else n - 1
            if a is not None and b is not None:
                for i in range(a, b + 1):
                    extra_cars[i] = cp["partnerCars"]
        cs = v.get("coupledSection")
        if cs:
            a = _stop_index(v, cs["from"]) if cs.get("from") else 0
            b = _stop_index(v, cs["to"]) if cs.get("to") else n - 1
            if a is not None and b is not None:
                for i in range(a, b + 1):
                    extra_cars[i] = cs["extraCars"]

        for i, s in enumerate(sl):
            if extra_cars[i]:
                length = car_length(v["cars"]) + car_length(extra_cars[i])
                cars_desc = f"{v['cars']}+{extra_cars[i]}"
            else:
                length = car_length(v["cars"])
                cars_desc = str(v["cars"])
            if length > max_len[s["name"]]:
                max_len[s["name"]] = length
            who[s["name"]].append((v["name"], cars_desc, length))

    out = []
    for st, L in max_len.items():
        top = sorted(who[st], key=lambda x: -x[2])[0]
        out.append({"station": st, "max_length_m": L, "line": top[0], "cars": top[1]})
    return sorted(out, key=lambda r: -r["max_length_m"])


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(data):
    return {
        "n_variants": len(data),
        "n_base_lines": len(base_lines(data)),
        "n_stations": len({s["name"] for v in data.values() for s in v["stops"]}),
        "data_quality": check_data_quality(data),
        "hub_ranking": hub_ranking(data),
        "corridors": shared_corridors(data),
        "corridor_headways": corridor_headways(data),
        "symmetry": symmetry_stats(data),
        "fleet": fleet_requirements(data),
        "stabling": stabling_demand(data),
        "train_lengths": train_length_per_stop(data),
    }


def render_markdown(report):
    L = []
    L.append("# RE-Netz 2030 — Ist-Report\n")
    L.append(
        f"{report['n_variants']} Richtungsvarianten, {report['n_base_lines']} Basislinien, "
        f"{report['n_stations']} Stationen.\n"
    )

    L.append("## Datenqualität\n")
    if report["data_quality"]:
        for p in report["data_quality"]:
            L.append(f"- ⚠️ {p}")
    else:
        L.append("Keine Auffälligkeiten.")
    L.append("")

    L.append("## Knotenranking (Top 25, gewichtete Umsteigerelationen inkl. Endknoten-Bonus)\n")
    L.append("| # | Score | Station | Linien |")
    L.append("|---|---|---|---|")
    for i, h in enumerate(report["hub_ranking"][:25], 1):
        L.append(f"| {i} | {h['score']} | {h['station']} | {', '.join(h['lines'])} |")
    L.append("")

    L.append("## Parallelkorridore (≥2 Linien, Top 20 nach mittlerer Taktabweichung)\n")
    L.append("| Von | Nach | Linien | Ist-Abfahrten (mod 60) | Lücken | Ideal | ⌀Abw. |")
    L.append("|---|---|---|---|---|---|---|")
    for c in report["corridor_headways"][:20]:
        deps = ", ".join(f"{d['line']}:{d['dep_mod60']:02d}" for d in c["departures"])
        L.append(
            f"| {c['from']} | {c['to']} | {len(c['lines'])} | {deps} | "
            f"{c['gaps']} | {c['ideal_gap']} | {c['mean_deviation']} |"
        )
    L.append("")

    L.append("## Symmetrie je Linie (2·Symmetrieminute mod 60 an gemeinsamen Halten)\n")
    L.append("| Linie | n Halte | ⌀ 2σ | Spannweite |")
    L.append("|---|---|---|---|")
    for s in sorted(report["symmetry"], key=lambda x: -x["spread"]):
        L.append(f"| {s['line']} | {s['n_common_stops']} | {s['mean_sigma2']} | {s['spread']} |")
    L.append("")

    L.append("## Fahrzeugbedarf — heute vs. differenziertes Wendemodell (RE/RB ≥70, S-Bahn ≥20, +1 Reserve)\n")
    L.append("| Linie | T | Fahrzeit A/B | heute | neu | Δ | Wende A/B |")
    L.append("|---|---|---|---|---|---|---|")
    tot_old = tot_new = 0
    for f in report["fleet"]:
        tot_old += f["fleet_today"]
        tot_new += f["fleet_new_incl_reserve"]
        L.append(
            f"| {f['line']} | {f['interval']} | {f['duration_A']}/{f['duration_B']} | "
            f"{f['fleet_today']} | {f['fleet_new_incl_reserve']} | {f['delta']:+d} | "
            f"{f['turnaround_A_min']}/{f['turnaround_B_min']} |"
        )
    L.append(f"\n**Summe: {tot_old} → {tot_new} ({tot_new - tot_old:+d})**\n")

    L.append("## Abstellbedarf an Endbahnhöfen (Top 15)\n")
    L.append("| Bahnhof | Linien | Plätze | Gesamtlänge |")
    L.append("|---|---|---|---|")
    for s in report["stabling"][:15]:
        L.append(f"| {s['station']} | {s['n_lines']} | {s['slots']} | {s['total_length_m']} m |")
    L.append("")

    L.append("## Bahnsteig-Mindestlängen (Top 15 + Verteilung)\n")
    dist = collections.Counter(t["max_length_m"] for t in report["train_lengths"])
    L.append("Verteilung: " + ", ".join(f"{L_}m×{n}" for L_, n in sorted(dist.items(), key=lambda x: -x[1])))
    L.append("")
    L.append("| Station | Mindestlänge | Linie | Wagen |")
    L.append("|---|---|---|---|")
    for t in report["train_lengths"][:15]:
        L.append(f"| {t['station']} | {t['max_length_m']} m | {t['line']} | {t['cars']} |")
    L.append("")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="data/lines.json")
    ap.add_argument("--out", default="data/ist_report.md")
    ap.add_argument("--json-out", default="data/ist_report.json")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    report = build_report(data)

    pathlib.Path(args.json_out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = render_markdown(report)
    pathlib.Path(args.out).write_text(md, encoding="utf-8")
    print(f"Report geschrieben: {args.out} / {args.json_out}")


if __name__ == "__main__":
    main()
