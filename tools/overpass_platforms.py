#!/usr/bin/env python3
"""
Reale Bahnsteiglängen aus OpenStreetMap/Overpass — Abgleich gegen die aus
lines.json errechneten Zuglängen (tools/lengths.py). Deckt auch die 101
ausländischen Stationen ab (NL/PL/DK/CH/FR/LU/CZ/AT/BE), die DB InfraGO
nicht führt.

Fragt Bahnsteig-Objekte (railway=platform, public_transport=platform) in
Batches von je BATCH_SIZE Stationen über 'around'-Filter ab (ein HTTP-
Request pro Batch statt 474 Einzelabfragen), cached jede Rohantwort
lokal und ordnet gefundene Bahnsteige anschließend GLOBAL der nächst-
gelegenen Station zu (nicht nur innerhalb des Batches, da 'around' keine
Zuordnung liefert, welcher Treffer zu welcher Abfrage-Station gehört).

Nutzung:
    python3 tools/overpass_platforms.py \
        --stations data/stations.json \
        --out data/platform_lengths.json \
        [--force]   # Cache ignorieren, alles neu abfragen
"""
import argparse
import hashlib
import json
import math
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BATCH_SIZE = 15
RADIUS_M = 550
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CACHE_DIR = pathlib.Path("data/osm_cache")
MAX_RETRIES = 4
RETRY_BACKOFF_S = 6

PLAUSIBLE_MIN_M = 15
PLAUSIBLE_MAX_M = 450


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geometry_length_m(geometry):
    """Größte Punkt-zu-Punkt-Distanz in der Geometrie. Bahnsteig-Ways in OSM
    sind oft als GESCHLOSSENE Polygone (Grundriss-Umriss) erfasst, nicht als
    Mittellinie — eine Kantensummen-Länge würde dann den Umfang liefern
    (~2×Länge+2×Breite) statt der tatsächlichen Länge. Die größte Distanz
    zwischen zwei Eckpunkten (≈ Diagonale) approximiert die reale Länge
    sowohl für Polygone als auch für einfache Linien-Ways robust."""
    if len(geometry) < 2:
        return 0.0
    best = 0.0
    for i, a in enumerate(geometry):
        for b in geometry[i + 1 :]:
            d = haversine_m(a["lat"], a["lon"], b["lat"], b["lon"])
            if d > best:
                best = d
    return best


def build_query(batch):
    clauses = []
    for name, lat, lon in batch:
        clauses.append(f'way["railway"="platform"](around:{RADIUS_M},{lat},{lon});')
        clauses.append(f'way["public_transport"="platform"](around:{RADIUS_M},{lat},{lon});')
        clauses.append(f'node["railway"="platform"](around:{RADIUS_M},{lat},{lon});')
    return f'[out:json][timeout:60];({"".join(clauses)});out tags geom;'


def batch_cache_key(batch):
    raw = json.dumps(batch, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def fetch_batch(batch, force=False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = batch_cache_key(batch)
    cache_path = CACHE_DIR / f"{key}.json"
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    query = build_query(batch)
    data_bytes = urllib.parse.urlencode({"data": query}).encode()
    headers = {
        # Overpass weist Requests ohne aussagekräftigen User-Agent mit 406 ab.
        "User-Agent": "RENetz2030-Taktoptimierung/1.0 (Bahnsteiglaengen-Abgleich; +https://github.com/Groot7777/ir-netz-2030)",
    }
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(OVERPASS_URL, data=data_bytes, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read())
            cache_path.write_text(json.dumps(result), encoding="utf-8")
            return result
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            wait = RETRY_BACKOFF_S * attempt
            print(f"    Versuch {attempt}/{MAX_RETRIES} fehlgeschlagen ({e}) — warte {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"    Batch endgültig fehlgeschlagen ({last_err}) — übersprungen", file=sys.stderr)
    return None


def is_rail_platform(tags):
    """Schließt Straßenbahn-/Bus-Bahnsteige aus, die an multimodalen Knoten
    fälschlich mitgefangen werden. Beispiel Köln Hbf: die dortigen KVB-
    Stadtbahn-Bahnsteige ('Dom/Hbf', 'Breslauer Platz/Hbf') tragen ebenfalls
    railway=platform, sind aber explizit mit train=no, tram=yes von den
    DB-Bahnsteigen abgegrenzt — ohne diesen Filter liefert Köln Hbf eine
    absurd kurze 'Bahnsteiglänge' von 90m aus einer U-Bahn-Haltestelle statt
    der tatsächlichen, deutlich längeren Fernbahnsteige."""
    if tags.get("train") == "no":
        return False
    if tags.get("railway") == "platform":
        return True
    if tags.get("tram") == "yes" or tags.get("bus") == "yes":
        return False
    return True


def parse_platform_length(tags, geometry):
    raw = tags.get("length")
    if raw:
        try:
            val = float(str(raw).split()[0].replace(",", "."))
            return val, "tag"
        except ValueError:
            pass
    if geometry and len(geometry) >= 2:
        return geometry_length_m(geometry), "geometry"
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stations", default="data/stations.json")
    ap.add_argument("--out", default="data/platform_lengths.json")
    ap.add_argument("--force", action="store_true", help="Cache ignorieren, alles neu abfragen")
    ap.add_argument("--limit", type=int, default=None, help="nur die ersten N Stationen (Test)")
    args = ap.parse_args()

    stations = json.loads(pathlib.Path(args.stations).read_text(encoding="utf-8"))
    items = [(name, v["lat"], v["lon"]) for name, v in stations.items()]
    if args.limit:
        items = items[: args.limit]

    batches = [items[i : i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    print(f"{len(items)} Stationen in {len(batches)} Batches (je bis {BATCH_SIZE}, Radius {RADIUS_M}m)")

    all_elements = {}  # (type,id) -> element, global dedupe über alle Batches
    failed_batches = 0
    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}/{len(batches)} ({batch[0][0]} … {batch[-1][0]})")
        result = fetch_batch(batch, force=args.force)
        if result is None:
            failed_batches += 1
            continue
        for el in result.get("elements", []):
            all_elements[(el["type"], el["id"])] = el
        time.sleep(1.5)  # Rate-Limit-Höflichkeit zwischen Requests

    print(f"{len(all_elements)} eindeutige Bahnsteig-Objekte gefunden, {failed_batches} Batches fehlgeschlagen")

    # Globale Zuordnung: jedes Objekt zur nächstgelegenen Station im GESAMTEN
    # Datensatz (nicht nur dem Batch, der es gefunden hat).
    platforms_by_station = {name: [] for name, _, _ in items}
    unmatched = 0
    n_excluded_nonrail = 0
    for (etype, eid), el in all_elements.items():
        tags = el.get("tags", {})
        if not is_rail_platform(tags):
            n_excluded_nonrail += 1
            continue
        geometry = el.get("geometry")
        if etype == "node":
            lat, lon = el.get("lat"), el.get("lon")
        elif geometry:
            lat = sum(p["lat"] for p in geometry) / len(geometry)
            lon = sum(p["lon"] for p in geometry) / len(geometry)
        else:
            continue

        best_name, best_dist = None, float("inf")
        for name, slat, slon in items:
            d = haversine_m(lat, lon, slat, slon)
            if d < best_dist:
                best_dist, best_name = d, name
        if best_dist > RADIUS_M:
            unmatched += 1
            continue

        length_m, source = parse_platform_length(tags, geometry)
        plausible = length_m is not None and PLAUSIBLE_MIN_M <= length_m <= PLAUSIBLE_MAX_M
        platforms_by_station[best_name].append(
            {
                "osm_type": etype,
                "osm_id": eid,
                "ref": tags.get("ref") or tags.get("local_ref"),
                "name": tags.get("name"),
                "length_m": round(length_m, 1) if length_m is not None else None,
                "length_source": source,
                "plausible": plausible,
                "distance_to_station_m": round(best_dist, 1),
            }
        )

    out = {}
    n_with_data = n_without_data = 0
    for name, plats in platforms_by_station.items():
        plausible_lengths = [p["length_m"] for p in plats if p["plausible"]]
        best = max(plausible_lengths) if plausible_lengths else None
        if best is not None:
            n_with_data += 1
        else:
            n_without_data += 1
        out[name] = {"best_length_m": best, "platforms": sorted(plats, key=lambda p: -(p["length_m"] or 0))}

    pathlib.Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        f"\n{args.out} geschrieben: {n_with_data} Stationen mit plausibler Bahnsteiglänge, "
        f"{n_without_data} ohne Daten. {unmatched} Objekte ohne Station im Radius verworfen, "
        f"{n_excluded_nonrail} als Tram/Bus ausgeschlossen."
    )


if __name__ == "__main__":
    main()
