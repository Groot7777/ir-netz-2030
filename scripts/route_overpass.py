#!/usr/bin/env python3
"""For each consecutive stop pair on each line, fetch real OSM ways (highway=motorway/
trunk for Maglev lines following Autobahnen, or railway=rail/construction for
conventional-rail lines) in a bounding box around both points via Overpass, build a
graph, and run Dijkstra shortest path between the nearest graph nodes to each stop.
Full-resolution coordinate lists are cached in cache/overpass_cache.json keyed
"StationA||StationB" (direction-independent, alphabetically sorted key so both
directions of a line share one cache entry). Pairs listed in data/ocean_crossings.json
are skipped entirely (handled separately as geodetic great-circle lines).

Runs a small thread pool (default 3 workers) rotating across Overpass endpoints to
parallelize network-bound routing, since a purely serial run is too slow for a
network this size.
"""
import concurrent.futures
import json
import math
import os
import sys
import threading
import time
import urllib.parse
import urllib.request

import networkx as nx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES_DIR = os.path.join(ROOT, "data", "lines")
CACHE_PATH = os.path.join(ROOT, "cache", "geocode_cache.json")
ROUTE_CACHE_PATH = os.path.join(ROOT, "cache", "overpass_cache.json")
CROSSINGS_PATH = os.path.join(ROOT, "data", "ocean_crossings.json")

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

MARGIN_DEG = 0.15  # padding around the two stops' bbox, in degrees
FILTERS = {
    "highway": '["highway"~"^(motorway|trunk|motorway_link|trunk_link)$"]',
    "railway": '["railway"~"^(rail|construction)$"]',
}

_endpoint_lock = threading.Lock()
_endpoint_rr = [0]
_cache_lock = threading.Lock()


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def haversine_km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def next_endpoint():
    with _endpoint_lock:
        ep = OVERPASS_ENDPOINTS[_endpoint_rr[0] % len(OVERPASS_ENDPOINTS)]
        _endpoint_rr[0] += 1
        return ep


def overpass_query(bbox, filter_key):
    south, west, north, east = bbox
    tag_filter = FILTERS[filter_key]
    q = f"""
[out:json][timeout:60];
way{tag_filter}({south},{west},{north},{east});
out body geom;
"""
    data = urllib.parse.urlencode({"data": q}).encode("utf-8")
    last_err = None
    endpoints = OVERPASS_ENDPOINTS[:]
    start = next_endpoint()
    ordered = [start] + [e for e in endpoints if e != start]
    for endpoint in ordered:
        for attempt in range(2):
            try:
                req = urllib.request.Request(endpoint, data=data,
                                              headers={"User-Agent": "ir-netz-2030-router/1.0"})
                with urllib.request.urlopen(req, timeout=90) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                last_err = e
                time.sleep(2 * (attempt + 1))
        print(f"  ! Endpoint {endpoint} fehlgeschlagen ({last_err}), naechster Fallback...", file=sys.stderr)
    raise RuntimeError(f"Alle Overpass-Endpoints fehlgeschlagen: {last_err}")


def build_graph(osm_data):
    g = nx.Graph()
    for el in osm_data.get("elements", []):
        if el.get("type") != "way":
            continue
        geom = el.get("geometry")
        if not geom:
            continue
        coords = [(pt["lat"], pt["lon"]) for pt in geom]
        for i in range(len(coords) - 1):
            a, b = coords[i], coords[i + 1]
            if a == b:
                continue
            d = haversine_km(a, b)
            if g.has_edge(a, b):
                if g[a][b]["weight"] <= d:
                    continue
            g.add_edge(a, b, weight=d)
    return g


def nearest_node(g, point, max_km=5.0):
    best = None
    best_d = None
    for n in g.nodes:
        d = haversine_km(point, n)
        if best_d is None or d < best_d:
            best_d = d
            best = n
    if best is None or best_d > max_km:
        return None, best_d
    return best, best_d


def route_pair(coord_a, coord_b, pair_label, filter_key):
    south = min(coord_a[0], coord_b[0]) - MARGIN_DEG
    north = max(coord_a[0], coord_b[0]) + MARGIN_DEG
    west = min(coord_a[1], coord_b[1]) - MARGIN_DEG
    east = max(coord_a[1], coord_b[1]) + MARGIN_DEG

    for expand in (1, 2, 4):
        bbox = (south - MARGIN_DEG * (expand - 1), west - MARGIN_DEG * (expand - 1),
                north + MARGIN_DEG * (expand - 1), east + MARGIN_DEG * (expand - 1))
        osm_data = overpass_query(bbox, filter_key)
        n_ways = len([e for e in osm_data.get("elements", []) if e.get("type") == "way"])
        if n_ways == 0:
            print(f"    (keine Ways in bbox, erweitere...) [{pair_label}]")
            continue
        g = build_graph(osm_data)
        na, da = nearest_node(g, coord_a, max_km=5.0 * expand)
        nb, db = nearest_node(g, coord_b, max_km=5.0 * expand)
        if na is None or nb is None:
            print(f"    (kein nahegelegener Graph-Knoten gefunden, erweitere...) [{pair_label}]")
            continue
        try:
            path = nx.shortest_path(g, na, nb, weight="weight")
            length = nx.shortest_path_length(g, na, nb, weight="weight")
            return path, length, expand
        except nx.NetworkXNoPath:
            print(f"    (kein Pfad im Graph, erweitere...) [{pair_label}]")
            continue
    return None, None, None


def process_one(idx, total, ka, kb, cache_key, ca, cb, filter_key, route_cache):
    straight = haversine_km(ca, cb)
    label = f"{ka} -> {kb}"
    print(f"[{idx}/{total}] Route {label} (Luftlinie {straight:.2f} km, {filter_key})...")
    try:
        path, length, expand = route_pair(ca, cb, label, filter_key)
    except Exception as e:
        print(f"    FEHLER: {e}", file=sys.stderr)
        entry = {"status": "error", "error": str(e), "straight_km": straight}
        with _cache_lock:
            route_cache[cache_key] = entry
            save_json(ROUTE_CACHE_PATH, route_cache)
        return

    if path is None:
        print(f"    !! Kein Pfad gefunden fuer {label}, speichere als 'no_path' (Fallback: Gerade).")
        entry = {"status": "no_path", "straight_km": straight, "coords": [list(ca), list(cb)]}
    else:
        ratio = length / straight if straight > 0 else 1.0
        flag = " [[UMWEG-VERDACHT]]" if ratio > 1.6 else ""
        print(f"    OK: {len(path)} Punkte, {length:.2f} km (Ratio {ratio:.2f}, bbox-expand={expand}){flag} [{label}]")
        entry = {
            "status": "ok",
            "straight_km": straight,
            "path_km": length,
            "ratio": ratio,
            "bbox_expand": expand,
            "coords": [list(p) for p in path],
        }
    with _cache_lock:
        route_cache[cache_key] = entry
        save_json(ROUTE_CACHE_PATH, route_cache)


def main():
    geocode_cache = load_json(CACHE_PATH, {})
    route_cache = load_json(ROUTE_CACHE_PATH, {})
    crossings = load_json(CROSSINGS_PATH, {"crossings": []})
    crossing_keys = {"||".join(sorted([c["a"], c["b"]])) for c in crossings.get("crossings", [])}

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    workers = 3
    for a in sys.argv[1:]:
        if a.startswith("--workers="):
            workers = int(a.split("=", 1)[1])
    only_lines = args if args else None

    pairs = []
    seen_pairs = set()
    for fn in sorted(os.listdir(LINES_DIR)):
        if not fn.endswith(".json"):
            continue
        line = load_json(os.path.join(LINES_DIR, fn), {})
        if only_lines and line.get("id") not in only_lines:
            continue
        filter_key = line.get("geometry_source", "highway")
        stops = line.get("stops", [])
        for i in range(len(stops) - 1):
            ka, kb = stops[i]["key"], stops[i + 1]["key"]
            cache_key = "||".join(sorted([ka, kb]))
            if cache_key in seen_pairs or cache_key in crossing_keys:
                continue
            seen_pairs.add(cache_key)
            pairs.append((ka, kb, cache_key, filter_key))

    todo = []
    for ka, kb, cache_key, filter_key in pairs:
        if cache_key in route_cache and route_cache[cache_key].get("status") == "ok":
            continue
        if ka not in geocode_cache or kb not in geocode_cache:
            print(f"UEBERSPRINGE {ka} -> {kb}: fehlende Geokoordinaten")
            continue
        ca = (geocode_cache[ka]["lat"], geocode_cache[ka]["lon"])
        cb = (geocode_cache[kb]["lat"], geocode_cache[kb]["lon"])
        todo.append((ka, kb, cache_key, ca, cb, filter_key))

    print(f"{len(pairs)} eindeutige Streckenabschnitte gesamt, {len(todo)} noch zu routen, {workers} Worker.")

    total = len(todo)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        for idx, (ka, kb, cache_key, ca, cb, filter_key) in enumerate(todo, 1):
            futures.append(pool.submit(process_one, idx, total, ka, kb, cache_key, ca, cb, filter_key, route_cache))
            time.sleep(0.3)
        for f in concurrent.futures.as_completed(futures):
            f.result()

    print("Fertig.")


if __name__ == "__main__":
    main()
