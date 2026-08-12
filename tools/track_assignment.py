#!/usr/bin/env python3
"""
Netzweite Gleiszuweisung: jede Richtungsvariante bekommt an jedem Halt ein
festes Gleis. Zwei echte Prinzipien statt reinem Längen+Lastausgleich:

1. RICHTUNGS-KONSISTENZ: Alle Züge, die an einer Station von/zu DERSELBEN
   Nachbarstation fahren (= derselbe physische Streckenast), gehören zur
   selben "Richtungsgruppe" und bekommen dauerhaft dasselbe Gleis (oder
   bei Bedarf mehrere feste Gleise derselben Richtung) — nicht wie zuvor
   zufällig über die ganze Station verteilt nach reiner Lastauslastung.
   Richtung wird über die NACHBAR-Haltestelle(n) im Linienverlauf
   approximiert (Kopfgleis: nur ein Nachbar: durchgehender Halt: zwei
   Nachbarn = das Streckenpaar, auf dem der Zug fährt) — ein robuster
   Proxy für "welches physische Gleispaar", ohne dass wir echte
   Stellwerks-/Gleistopologie hätten.
2. ECHTE MINUTEN-KONFLIKTPRÜFUNG je Richtungsgruppe: Zwei Belegungen
   dürfen sich ein Gleis nur teilen, wenn zwischen Abfahrt der einen und
   Ankunft der nächsten mindestens PLATFORM_BUFFER_MIN Minuten liegen
   (zyklisch über die volle Taktstunde, inkl. 30-/10-Min-Takt mit
   mehreren Durchläufen pro Stunde). Die je Richtungsgruppe benötigte
   Mindest-Gleisanzahl ist die maximale Überlappungstiefe (klassisches
   Intervall-Scheduling, optimal per Greedy-"erstes freies Gleis").

Reicht die Zahl der an einer Station tatsächlich vorhandenen Gleise nicht
für alle Richtungsgruppen einzeln aus, werden die zwei "billigsten"
Gruppen (kleinster zusätzlicher Gleisbedarf beim Zusammenlegen) so lange
verschmolzen, bis es passt — bevorzugt Verschmelzungen, die gar keinen
neuen Konflikt erzeugen (unterschiedliche Richtungen, die zeitlich nie
kollidieren, teilen sich ein Gleis dann ohne Qualitätsverlust). Erst wenn
selbst eine einzige Gruppe für die ganze Station nicht mehr in die
vorhandene Gleiszahl passt, wird die Gleisanzahl hart gedeckelt (die
Station ist schlicht knapper bemessen, als der Fahrplan bräuchte) und
verbleibende Konflikte im Report als "geteiltes Gleis" ausgewiesen statt
stillschweigend verschwiegen.

Bahnsteiglängen weiterhin wie gehabt SDO-tolerant bewertet (25m Überhang
= unkritisch), Datenpriorität pro Station unverändert:
  1. data/manual_overrides.json  — fiktive RE-Netz-2030-Planung
  2. data/dbinfrago_platforms.json — amtliche DB InfraGO-Daten (353 dt. Bahnhöfe)
  3. data/foreign_platforms.json — amtliche Auslandsdaten
  4. data/platform_lengths.json  — OSM/Overpass (restliches Ausland + Rest-Lücken)
  5. Fallback 'geschaetzt': KEINE Quelle vorhanden — ein einzelnes Gleis
     wird auf die längste dort tatsächlich benötigte Zuglänge geschätzt.

Gekuppelte Flügelzug-Partner (coupling.partner) sind auf dem gemeinsamen
Abschnitt EIN physischer Zug — sie werden zu EINEM Besuch zusammengeführt
und bekommen zwangsläufig dasselbe Gleis, dieselbe Richtungsgruppe.

Nutzung:
    python3 tools/track_assignment.py --out data/track_assignment.json
"""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lengths import car_length, extra_cars_per_stop, stop_index  # noqa: E402
from score import effective_phase, stop_arr, stop_dep  # noqa: E402

PLATFORM_BUFFER_MIN = 4


def coupled_window(v, data):
    """(start_idx, end_idx, partner_key), wenn v.coupling einen echten
    Partner referenziert, der auch als eigene Variante existiert — sonst
    None. start/end sind die Halt-Indizes von v, auf denen der Zug mit dem
    Partner gemeinsam fährt (coupledFrom/coupledTo, wie in lengths.py)."""
    cp = v.get("coupling")
    if not cp or not cp.get("partner") or cp["partner"] not in data:
        return None
    sl = v["stops"]
    a = stop_index(v, cp["coupledFrom"]) if cp.get("coupledFrom") else 0
    b = stop_index(v, cp["coupledTo"]) if cp.get("coupledTo") else len(sl) - 1
    if a is None or b is None:
        return None
    return (a, b, cp["partner"])


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


def build_station_tracks(stations, manual, dbinfrago, foreign, osm):
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
        f = foreign.get(st)
        if f and f.get("tracks"):
            out[st] = {"source": "amtlich-ausland", "tracks": dedup_max([(t["gleis"], t["length_m"]) for t in f["tracks"]])}
            continue
        o = osm.get(st)
        if o and o.get("platforms"):
            tracks = []
            # Viele OSM-Bahnsteigobjekte (v.a. im Ausland/an kleinen Halten)
            # haben kein 'ref'-Tag, also keine erfasste Gleisnummer. Statt der
            # internen OSM-Objekt-ID (unleserlich, z.B. "OSM421169907") eine
            # schlichte fortlaufende Nummer vergeben — kollisionsfrei zu
            # echten, an derselben Station vorhandenen ref-Nummern.
            used_refs = {p["ref"] for p in o["platforms"] if p.get("ref")}
            synth = 1
            for p in o["platforms"]:
                if not p["plausible"]:
                    continue
                if p["ref"]:
                    label = p["ref"]
                else:
                    while str(synth) in used_refs:
                        synth += 1
                    label = str(synth)
                    used_refs.add(label)
                    synth += 1
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


# ---------------------------------------------------------------------------
# Richtungsgruppen: Nachbar-Haltestelle(n) als Proxy für "physischer Ast"
# ---------------------------------------------------------------------------

def direction_key(v, i):
    """Menge der im Linienverlauf direkt benachbarten Haltestellen — der
    Proxy für 'welcher physische Streckenast'. Ein Kopfgleis-Halt (Anfang
    oder Ende der Variante) hat nur EINEN Nachbarn; ein Durchgangshalt
    zwei. Zwei Besuche mit identischer Nachbarmenge nutzen mit hoher
    Wahrscheinlichkeit dasselbe Gleispaar in der Realität — unabhängig
    davon, welche Linie sie bedient."""
    stops = v["stops"]
    neighbors = []
    if i > 0:
        neighbors.append(stops[i - 1]["name"])
    if i < len(stops) - 1:
        neighbors.append(stops[i + 1]["name"])
    return frozenset(neighbors)


def visit_occurrences(v, i):
    """Liste von (start_min, end_min) im 60-Min-Zyklus (start in [0,60),
    end = start+Standzeit, kann >=60 sein) — bei Takt <60 Min mehrere
    Durchläufe pro Stunde (z.B. 30-Min-Takt: 2, 10-Min-Takt: 6)."""
    phase, interval = effective_phase(v)
    s = v["stops"][i]
    arr_raw = phase + stop_arr(s)
    dep_raw = phase + stop_dep(s)
    dwell = max(0, dep_raw - arr_raw)
    base_start = arr_raw % 60
    n_per_hour = 60 // interval if interval and 60 % interval == 0 else 1
    return [((base_start + k * interval) % 60, (base_start + k * interval) % 60 + dwell)
            for k in range(n_per_hour)]


def schedule_lanes(occurrences, buffer_min=PLATFORM_BUFFER_MIN):
    """occurrences: [(start,end), ...] im 60-Min-Zyklus. Greedy-Intervall-
    Partitionierung (nach Startzeit, erstes freies 'Gleis-Lane') liefert
    die MINIMALE Lane-Anzahl (= maximale Überlappungstiefe) — klassisches,
    optimales Ergebnis für Intervall-Graph-Färbung. Zwei Durchläufe (die
    Zeitachse bei +60 min verdoppelt) lösen den Zyklus-Umbruch sauber auf;
    die Lane-Zuordnung wird aus dem zweiten (eingeschwungenen) Durchlauf
    übernommen.
    Gibt (n_lanes, [lane_index pro occurrences-Eintrag in Originalreihenfolge]) zurück."""
    n = len(occurrences)
    if n == 0:
        return 0, []
    events = []
    for idx, (s, e) in enumerate(occurrences):
        events.append((s, e, idx, 0))
        events.append((s + 60, e + 60, idx, 1))
    events.sort(key=lambda x: (x[0], x[2]))
    lane_free_at = []
    lane_of = {}
    for s, e, idx, cyc in events:
        chosen = None
        for li, free_at in enumerate(lane_free_at):
            if free_at + buffer_min <= s:
                chosen = li
                break
        if chosen is None:
            chosen = len(lane_free_at)
            lane_free_at.append(-10**9)
        lane_free_at[chosen] = e
        lane_of[(idx, cyc)] = chosen
    return len(lane_free_at), [lane_of[(idx, 1)] for idx in range(n)]


def best_merge(groups):
    """Sucht das Gruppenpaar, dessen Zusammenlegung am wenigsten zusätzliche
    Lanes kostet (0 = 'kostenlos', die beiden Richtungen kollidieren
    zeitlich nie) — Tie-Break: kleinste Gruppen zuerst verschmelzen. Gibt
    (i, j, merged_lanes) zurück."""
    best = None
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            a, b = groups[i], groups[j]
            merged_lanes, _ = schedule_lanes(a["occurrences"] + b["occurrences"])
            extra = merged_lanes - max(a["lanes"], b["lanes"])
            key = (extra, a["lanes"] + b["lanes"])
            if best is None or key < best[0]:
                best = (key, i, j, merged_lanes)
    return best[1], best[2], best[3]


def assign_station_directional(station_groups, tracks, source, sdo_tolerance_m=25):
    """station_groups: [{'direction_keys' (frozenset), 'members' (list of
    dict mit key, required_length), 'occurrences', 'lanes'}]. tracks:
    [(label, length)]. Reduziert Gruppen per Verschmelzung, bis die
    Lane-Summe in die vorhandene Gleiszahl passt (oder — falls selbst EINE
    Gruppe nicht mehr passt — auf die Gleiszahl gedeckelt wird), verteilt
    dann echte Gleis-Label pro Gruppe/Lane und je Besuch dessen Lane-Gleis.
    Gibt (assignment: {key: {track, severity, overhang_m, shared}},
    resolved_tracks, n_shared) zurück; n_shared zählt Besuche auf einem mit
    einer ANDEREN Richtungsgruppe geteilten Gleis (Kapazitätsengpass,
    transparent ausgewiesen statt verschwiegen)."""
    if source == "geschaetzt" and not tracks:
        est = max((m["required_length"] for g in station_groups for m in g["members"]), default=0)
        tracks = [("1 (geschätzt)", est)]

    n_tracks = max(1, len(tracks))
    groups = [dict(g) for g in station_groups]

    while len(groups) > 1 and sum(g["lanes"] for g in groups) > n_tracks:
        i, j, merged_lanes = best_merge(groups)
        gi, gj = groups[i], groups[j]
        groups = [g for k, g in enumerate(groups) if k not in (i, j)] + [{
            "direction_keys": gi["direction_keys"] | gj["direction_keys"],
            "members": gi["members"] + gj["members"],
            "occurrences": gi["occurrences"] + gj["occurrences"],
            "lanes": merged_lanes,
        }]

    for g in groups:
        _, assign = schedule_lanes(g["occurrences"])
        if g["lanes"] > n_tracks:
            # Selbst maximal verschmolzen passt eine einzelne Gruppe nicht
            # in die vorhandene Gleiszahl (Station schlicht zu klein fuer
            # den Fahrplan) — hart deckeln statt eine Lane zu erfinden, die
            # es nicht gibt.
            g["lanes"] = n_tracks
            assign = [min(a, n_tracks - 1) for a in assign]
        g["_lane_assign"] = assign

    # Gleis-Label je (Gruppe, Lane) vergeben: groesste Gruppen zuerst,
    # laengste benoetigte Laenge zuerst — dabei je Lane das KUERZESTE noch
    # ausreichende Gleis waehlen (kein unnoetig langes Gleis fuer eine kurze
    # Richtung verschwenden).
    tracks_sorted = sorted(tracks, key=lambda t: -t[1])
    used_labels = set()
    group_lane_track = {}  # (group_idx, lane) -> (label, length)
    groups_order = sorted(range(len(groups)),
                           key=lambda gi: (-groups[gi]["lanes"],
                                            -max((m["required_length"] for m in groups[gi]["members"]), default=0)))
    for gi in groups_order:
        g = groups[gi]
        need = max((m["required_length"] for m in g["members"]), default=0)
        for lane in range(g["lanes"]):
            sufficient = [t for t in tracks_sorted if t[0] not in used_labels and t[1] >= need]
            if sufficient:
                # Reicht mindestens ein freies Gleis: das kuerzeste davon
                # nehmen (kein unnoetig langes Gleis fuer eine kurze
                # Richtung verschwenden).
                chosen = min(sufficient, key=lambda t: t[1])
            else:
                unused = [t for t in tracks_sorted if t[0] not in used_labels]
                # Nichts Freies reicht aus: das LAENGSTE nehmen (minimiert
                # den Ueberhang) — Notfall-Wiederverwendung des laengsten
                # Gleises ueberhaupt, falls sogar die unbenutzten alle
                # bereits vergeben sind (Lanes > physische Gleise durch
                # Rundung bei mehreren gedeckelten Gruppen).
                pool = unused or tracks_sorted
                chosen = max(pool, key=lambda t: t[1])
            used_labels.add(chosen[0])
            group_lane_track[(gi, lane)] = chosen

    n_shared = 0
    assignment = {}
    for gi, g in enumerate(groups):
        is_mixed = len(g["direction_keys"]) > 1
        for member, lane in zip(g["members"], g["_lane_assign"]):
            label, length = group_lane_track[(gi, min(lane, g["lanes"] - 1))]
            overhang = round(member["required_length"] - length, 1)
            assignment[member["key"]] = {
                "track": label,
                "severity": classify(overhang, sdo_tolerance_m),
                "overhang_m": overhang,
                "shared": is_mixed,
            }
            if is_mixed:
                n_shared += 1
    return assignment, tracks, n_shared


def render_markdown(result, n_by_source, n_by_severity, n_shared_total):
    L = ["# Netzweite Gleiszuweisung — RE-Netz 2030", ""]
    L.append(
        "Jede Richtungsvariante bekommt an jedem Halt ein festes, längenpassendes "
        "Gleis — konsistent nach physischem Streckenast (Nachbarhaltestelle als "
        "Richtungs-Proxy) und mit echter Minuten-Konfliktprüfung je Gleis (siehe "
        "Docstring in `tools/track_assignment.py`). Datengrundlage: DB InfraGO "
        "(amtlich, deutsche Bahnhöfe), OSM/Overpass (Ausland + Restlücken), "
        "Projekt-Fiktion (fiktiv, höchste Priorität), sonst eine dokumentierte "
        "Schätzung."
    )
    L.append("")
    L.append("## Zusammenfassung")
    L.append("")
    total = sum(n_by_severity.values())
    L.append(f"- {len(result)} Stationen, {total} Zuweisungen (Variante×Halt)")
    L.append(f"- Quellen: " + ", ".join(f"{k} {v}" for k, v in sorted(n_by_source.items())))
    L.append(
        "- Konfliktstufen (Bahnsteiglänge): "
        + ", ".join(f"{k} {v}" for k, v in sorted(n_by_severity.items()))
        + " (ok = passt, gering = ≤25 m Überhang/SDO ausreichend, kritisch = >25 m)"
    )
    L.append(
        f"- {n_shared_total} Zuweisungen auf einem Gleis, das sich zwei verschiedene "
        "Richtungen teilen (Gleiszahl der Station reicht nicht für volle "
        "Richtungstrennung) — überall sonst: eine Richtung = ein festes Gleis."
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

    L.append("## Stationen mit geteilten Gleisen (Richtungstrennung nicht möglich)\n")
    shared_stations = []
    for st, info in result.items():
        n = sum(1 for a in info["assignments"] if a.get("shared"))
        if n:
            shared_stations.append((st, n))
    shared_stations.sort(key=lambda x: -x[1])
    if shared_stations:
        L.append("| Station | Betroffene Zuweisungen |")
        L.append("|---|---|")
        for st, n in shared_stations:
            L.append(f"| {st} | {n} |")
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
    ap.add_argument("--foreign", default="data/foreign_platforms.json")
    ap.add_argument("--platform-lengths", default="data/platform_lengths.json")
    ap.add_argument("--out", default="data/track_assignment.json")
    ap.add_argument("--md-out", default="data/track_assignment.md")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    manual = json.loads(pathlib.Path(args.manual_overrides).read_text(encoding="utf-8"))
    dbinfrago = json.loads(pathlib.Path(args.dbinfrago).read_text(encoding="utf-8"))
    foreign_path = pathlib.Path(args.foreign)
    foreign = json.loads(foreign_path.read_text(encoding="utf-8")) if foreign_path.exists() else {}
    osm = json.loads(pathlib.Path(args.platform_lengths).read_text(encoding="utf-8"))

    stations = sorted({s["name"] for v in data.values() for s in v["stops"]})
    station_tracks = build_station_tracks(stations, manual, dbinfrago, foreign, osm)

    # Gekuppelte Flügelzug-Partner an jedem Halt im gemeinsamen Abschnitt zu
    # EINEM Besuch (= einem physischen Zug = einem Gleis) zusammenführen.
    windows = {k: coupled_window(v, data) for k, v in data.items()}
    members_by_group = collections.defaultdict(list)  # group_key -> [(k, i)]
    for k, v in data.items():
        win = windows[k]
        for i, s in enumerate(v["stops"]):
            if win and win[0] <= i <= win[1]:
                gk = (s["name"], frozenset({k, win[2]}))
            else:
                gk = (k, i)
            members_by_group[gk].append((k, i))

    group_station = {}
    group_required_length = {}
    group_members_detail = collections.defaultdict(list)  # group_key -> [{variant, idx, line, required_length}]
    group_repr = {}  # group_key -> (variant, idx) repraesentativ fuer Richtung/Zeit
    for k, v in data.items():
        extra = extra_cars_per_stop(v)
        win = windows[k]
        for i, s in enumerate(v["stops"]):
            length = car_length(v["cars"]) + (car_length(extra[i]) if extra[i] else 0)
            gk = (s["name"], frozenset({k, win[2]})) if (win and win[0] <= i <= win[1]) else (k, i)
            group_members_detail[gk].append(
                {"variant": k, "idx": i, "line": v["name"], "required_length": length}
            )
            if gk not in group_station:
                group_station[gk] = s["name"]
                group_required_length[gk] = length
                group_repr[gk] = (k, i)
            else:
                group_required_length[gk] = max(group_required_length[gk], length)

    # Je Station: physische Besuche (gk) zu Richtungsgruppen buendeln.
    station_direction_groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for gk, st in group_station.items():
        rep_k, rep_i = group_repr[gk]
        dkey = direction_key(data[rep_k], rep_i)
        station_direction_groups[st][dkey].append(gk)

    result = {}
    n_by_severity = collections.Counter()
    n_by_source = collections.Counter()
    n_shared_total = 0
    for st, dgroups in station_direction_groups.items():
        info = station_tracks[st]
        groups_input = []
        for dkey, gks in dgroups.items():
            occurrences = []
            members = []
            for gk in gks:
                rep_k, rep_i = group_repr[gk]
                occurrences.extend(visit_occurrences(data[rep_k], rep_i))
                members.append({"key": gk, "required_length": group_required_length[gk]})
            lanes, _ = schedule_lanes(occurrences)
            groups_input.append({
                "direction_keys": frozenset({dkey}), "members": members,
                "occurrences": occurrences, "lanes": lanes,
            })
        assignment, resolved_tracks, n_shared = assign_station_directional(
            groups_input, info["tracks"], info["source"],
        )
        n_shared_total += n_shared

        rows = []
        for gk, a in assignment.items():
            for m in group_members_detail[gk]:
                n_by_severity[a["severity"]] += 1
                rows.append(
                    {
                        "variant": m["variant"], "idx": m["idx"], "line": m["line"],
                        "required_length_m": m["required_length"], "track": a["track"],
                        "severity": a["severity"], "overhang_m": a["overhang_m"],
                        "shared": a["shared"],
                    }
                )
        rows.sort(key=lambda r: (r["variant"], r["idx"]))
        n_by_source[info["source"]] += 1
        result[st] = {
            "source": info["source"],
            "available_tracks": [{"gleis": g, "length_m": l} for g, l in resolved_tracks],
            "assignments": rows,
        }

    pathlib.Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    md = render_markdown(result, n_by_source, n_by_severity, n_shared_total)
    pathlib.Path(args.md_out).write_text(md, encoding="utf-8")
    print(
        f"{len(result)} Stationen, {sum(len(v['assignments']) for v in result.values())} Zuweisungen "
        f"-> {args.out}, {args.md_out}"
    )
    print(f"Quellen: {dict(n_by_source)}")
    print(f"Severity: {dict(n_by_severity)}")
    print(f"Geteilte Gleise (Richtungstrennung nicht moeglich): {n_shared_total}")


if __name__ == "__main__":
    main()
