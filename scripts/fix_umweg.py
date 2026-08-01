#!/usr/bin/env python3
"""Post-process fix for the 'Umweg-Bug': at large junctions, disconnected parallel
carriageways in OSM data cause Dijkstra to take absurd detours (ratio = routed_km /
straight_km far above ~1.6-2.0). Fix: rebuild a LOCAL graph from a tight bounding box
around just the two stations, with coordinates rounded to 4 decimals (~11m) to merge
near-but-disconnected nodes (e.g. opposite carriageways of a divided highway that OSM
models as separate ways). If still stuck, retry rounded to 3 decimals (~111m).
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

import networkx as nx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES_DIR = os.path.join(ROOT, "data", "lines")
CACHE_PATH = os.path.join(ROOT, "cache", "geocode_cache.json")
ROUTE_CACHE_PATH = os.path.join(ROOT, "cache", "overpass_cache.json")

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
FILTERS = {
    "highway": '["highway"~"^(motorway|trunk|motorway_link|trunk_link)$"]',
    "highway_local": '["highway"~"^(motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link)$"]',
    "railway": '["railway"~"^(rail|construction)$"]',
}
RATIO_THRESHOLD = 1.6
TIGHT_MARGIN_DEG = 0.03  # ~3km padding, tight box around just the two stations


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
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


def overpass_query(bbox, filter_key):
    south, west, north, east = bbox
    q = f"[out:json][timeout:45];\nway{FILTERS[filter_key]}({south},{west},{north},{east});\nout body geom;\n"
    data = urllib.parse.urlencode({"data": q}).encode("utf-8")
    last_err = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            req = urllib.request.Request(endpoint, data=data, headers={"User-Agent": "ir-netz-2030-fixer/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"Alle Endpoints fehlgeschlagen: {last_err}")


def build_graph_rounded(osm_data, decimals):
    g = nx.Graph()

    def rnd(pt):
        return (round(pt[0], decimals), round(pt[1], decimals))

    for el in osm_data.get("elements", []):
        if el.get("type") != "way":
            continue
        geom = el.get("geometry")
        if not geom:
            continue
        coords = [rnd((pt["lat"], pt["lon"])) for pt in geom]
        for i in range(len(coords) - 1):
            a, b = coords[i], coords[i + 1]
            if a == b:
                continue
            d = haversine_km(a, b)
            if g.has_edge(a, b) and g[a][b]["weight"] <= d:
                continue
            g.add_edge(a, b, weight=d)
    return g


def nearest_node(g, point, max_km):
    best, best_d = None, None
    for n in g.nodes:
        d = haversine_km(point, n)
        if best_d is None or d < best_d:
            best_d, best = d, n
    if best is None or best_d > max_km:
        return None, best_d
    return best, best_d


def try_fix(ca, cb, filter_key, label):
    south = min(ca[0], cb[0]) - TIGHT_MARGIN_DEG
    north = max(ca[0], cb[0]) + TIGHT_MARGIN_DEG
    west = min(ca[1], cb[1]) - TIGHT_MARGIN_DEG
    east = max(ca[1], cb[1]) + TIGHT_MARGIN_DEG
    osm_data = overpass_query((south, west, north, east), filter_key)
    if not osm_data.get("elements"):
        return None
    for decimals in (4, 3):
        g = build_graph_rounded(osm_data, decimals)
        na, da = nearest_node(g, ca, max_km=3.0)
        nb, db = nearest_node(g, cb, max_km=3.0)
        if na is None or nb is None:
            continue
        try:
            path = nx.shortest_path(g, na, nb, weight="weight")
            length = nx.shortest_path_length(g, na, nb, weight="weight")
            return path, length, decimals
        except nx.NetworkXNoPath:
            continue
    return None


def main():
    geocode_cache = load_json(CACHE_PATH, {})
    route_cache = load_json(ROUTE_CACHE_PATH, {})
    lines_by_id = {}
    for fn in sorted(os.listdir(LINES_DIR)):
        if fn.endswith(".json"):
            line = load_json(os.path.join(LINES_DIR, fn), {})
            lines_by_id[line["id"]] = line

    flagged = [(k, v) for k, v in route_cache.items() if v.get("status") == "ok" and v.get("ratio", 0) > RATIO_THRESHOLD]
    print(f"{len(flagged)} Segmente mit Umweg-Verdacht (Ratio > {RATIO_THRESHOLD}) gefunden.")

    fixed, unfixed = 0, 0
    for cache_key, entry in flagged:
        ka, kb = cache_key.split("||")
        if ka not in geocode_cache or kb not in geocode_cache:
            continue
        ca = (geocode_cache[ka]["lat"], geocode_cache[ka]["lon"])
        cb = (geocode_cache[kb]["lat"], geocode_cache[kb]["lon"])
        straight = entry.get("straight_km") or haversine_km(ca, cb)
        # find which line(s) this pair belongs to, to get the right filter
        filter_key = "highway"
        for line in lines_by_id.values():
            stops = [s["key"] for s in line["stops"]]
            for i in range(len(stops) - 1):
                if "||".join(sorted([stops[i], stops[i + 1]])) == cache_key:
                    filter_key = line.get("geometry_source", "highway")
                    break
        label = f"{ka} -> {kb}"
        print(f"Versuche Fix: {label} (aktuell Ratio {entry['ratio']:.2f})...")
        try:
            result = try_fix(ca, cb, filter_key, label)
        except Exception as e:
            print(f"  FEHLER: {e}", file=sys.stderr)
            result = None
        if result is None:
            print(f"  -- kein besserer Pfad gefunden, behalte alten Wert (Ratio {entry['ratio']:.2f})")
            unfixed += 1
            continue
        path, length, decimals = result
        new_ratio = length / straight if straight > 0 else 1.0
        if new_ratio < entry["ratio"]:
            print(f"  OK: neue Ratio {new_ratio:.2f} (rounding={decimals}), {len(path)} Punkte, {length:.2f} km")
            route_cache[cache_key] = {
                "status": "ok", "straight_km": straight, "path_km": length,
                "ratio": new_ratio, "bbox_expand": 0, "fixed_rounding": decimals,
                "coords": [list(p) for p in path],
            }
            save_json(ROUTE_CACHE_PATH, route_cache)
            fixed += 1
        else:
            print(f"  -- neuer Versuch nicht besser ({new_ratio:.2f} >= {entry['ratio']:.2f}), behalte alten Wert")
            unfixed += 1
        time.sleep(1.0)

    print(f"Fertig. {fixed} behoben, {unfixed} weiterhin verdaechtig.")


if __name__ == "__main__":
    main()
