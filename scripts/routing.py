# -*- coding: utf-8 -*-
"""
Routing entlang echter Gleise via Overpass API + eigenem Dijkstra (kein networkx
noetig). Ergebnisse (volle Aufloesung) werden in cache/routes_cache.json unter
Key "StationA||StationB" gespeichert.
"""
import heapq
import json
import math
import os
import time

import requests

HEADERS = {"User-Agent": "ir-netz-2030-kml-builder/1.0 (fiktives Bahnliniennetz, privates Hobbyprojekt)"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "cache", "routes_cache.json")

# Paare, die KEINE reale Gleisverbindung haben (komplett fiktive Neubauten) ->
# direkt als Gerade behandeln, kein Overpass-Aufruf noetig.
FICTIONAL_STRAIGHT_LINE_PAIRS = {
    frozenset(["Schalksmuehle", "Luedenscheid Hbf"]),   # fiktive Tunnelkurve
    frozenset(["Bochum Hauptbahnhof", "Bochum-Bermuda3eck"]),  # neuer Hochbahnhof auf Viadukt
    frozenset(["Bochum-Bermuda3eck", "Bochum West"]),
    frozenset(["Hattingen Ruhr", "Hattingen Mitte"]),    # fiktiver City-Tunnelbahnhof
}

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bbox_for(lat1, lon1, lat2, lon2, pad_km=3.0, extra_frac=0.25, max_pad_km=15.0):
    span_km = max(haversine_km(lat1, lon1, lat2, lon2), 1.0)
    pad = min(max(pad_km, span_km * extra_frac), max_pad_km) / 111.0  # grobe Grad-Umrechnung
    lat_min, lat_max = sorted([lat1, lat2])
    lon_min, lon_max = sorted([lon1, lon2])
    # Breitengrad-Korrektur fuer Longitude-Padding
    lon_pad = pad / max(math.cos(math.radians((lat1 + lat2) / 2)), 0.2)
    return (lat_min - pad, lon_min - lon_pad, lat_max + pad, lon_max + lon_pad)


def overpass_query(bbox, railway_values, budget_s=150):
    s, w, n, e = bbox
    val_regex = "|".join(railway_values)
    q = f'[out:json][timeout:40];way["railway"~"^({val_regex})$"]({s},{w},{n},{e});out geom;'
    last_err = None
    t_start = time.time()
    for endpoint in ENDPOINTS:
        for attempt in range(2):
            if time.time() - t_start > budget_s:
                print(f"  Zeitbudget ({budget_s}s) ueberschritten, breche ab")
                return None
            try:
                t0 = time.time()
                resp = requests.post(endpoint, data={"data": q}, headers=HEADERS, timeout=45)
                dt = time.time() - t0
                if resp.status_code == 200:
                    return resp.json()
                last_err = f"HTTP {resp.status_code} von {endpoint} ({dt:.0f}s)"
                time.sleep(2 * (attempt + 1))
            except requests.RequestException as ex:
                last_err = f"{ex} ({endpoint})"
                time.sleep(2 * (attempt + 1))
    print(f"  Overpass fehlgeschlagen: {last_err}")
    return None


def round_coord(lat, lon, decimals):
    if decimals is None:
        return (lat, lon)
    return (round(lat, decimals), round(lon, decimals))


def build_graph(ways_json, decimals=None):
    graph = {}
    for el in ways_json.get("elements", []):
        if el.get("type") != "way" or "geometry" not in el:
            continue
        pts = [round_coord(pt["lat"], pt["lon"], decimals) for pt in el["geometry"]]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a == b:
                continue
            d = haversine_km(a[0], a[1], b[0], b[1])
            graph.setdefault(a, {})[b] = min(d, graph.get(a, {}).get(b, math.inf))
            graph.setdefault(b, {})[a] = min(d, graph.get(b, {}).get(a, math.inf))
    return graph


def nearest_node(graph, lat, lon, max_km=2.0):
    best, best_d = None, None
    for node in graph:
        d = haversine_km(lat, lon, node[0], node[1])
        if best is None or d < best_d:
            best, best_d = node, d
    if best is not None and best_d <= max_km:
        return best, best_d
    return None, best_d


def dijkstra(graph, start, end):
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    visited = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u == end:
            break
        for v, w in graph.get(u, {}).items():
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if end not in dist:
        return None
    path = [end]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def route_pair(lat1, lon1, lat2, lon2, decimals=None, pad_km=3.0, extra_frac=0.25,
                max_pad_km=15.0, tag_values=None, budget_s=150):
    """Ein Routing-Versuch. Gibt (path_latlon_list, path_length_km) oder None zurueck."""
    bbox = bbox_for(lat1, lon1, lat2, lon2, pad_km=pad_km, extra_frac=extra_frac, max_pad_km=max_pad_km)
    data = overpass_query(bbox, tag_values or ["rail"], budget_s=budget_s)
    if data is None:
        return None
    graph = build_graph(data, decimals=decimals)
    if not graph:
        return None
    n1, d1 = nearest_node(graph, lat1, lon1)
    n2, d2 = nearest_node(graph, lat2, lon2)
    if n1 is None or n2 is None:
        return None
    path = dijkstra(graph, n1, n2)
    if path is None:
        return None
    length = sum(haversine_km(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1]) for i in range(len(path) - 1))
    full_path = [(lat1, lon1)] + path + [(lat2, lon2)]
    return full_path, length


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=0)


def cache_key(a_key, b_key):
    return f"{a_key}||{b_key}"


def route_and_cache(a_key, b_key, lat1, lon1, lat2, lon2, cache, force=False):
    key = cache_key(a_key, b_key)
    rev_key = cache_key(b_key, a_key)
    if not force:
        if key in cache:
            return cache[key]
        if rev_key in cache:
            rev = cache[rev_key]
            fwd = {**rev, "path": list(reversed(rev["path"]))}
            cache[key] = fwd
            return fwd

    straight_km = haversine_km(lat1, lon1, lat2, lon2)

    if frozenset([a_key, b_key]) in FICTIONAL_STRAIGHT_LINE_PAIRS:
        result = {"path": [[lat1, lon1], [lat2, lon2]], "length_km": straight_km,
                  "straight_km": straight_km, "ratio": 1.0, "method": "fiktiv_gerade"}
        cache[key] = result
        return result

    # (tag_set, pad_km, extra_frac, max_pad_km, budget_s) - eskaliert von klein/schnell
    # zu gross/grosszuegig, damit dichte Grossstadt-Bboxen nicht sofort riesig werden.
    escalation = [
        (["rail"], 2.0, 0.12, 8.0, 90),
        (["rail"], 4.0, 0.20, 15.0, 90),
        (["rail", "construction"], 4.0, 0.20, 15.0, 90),
        (["rail", "construction", "disused", "abandoned"], 4.0, 0.25, 20.0, 90),
    ]
    for tag_set, pad_km, extra_frac, max_pad_km, budget_s in escalation:
        r = route_pair(lat1, lon1, lat2, lon2, decimals=None, tag_values=tag_set,
                        pad_km=pad_km, extra_frac=extra_frac, max_pad_km=max_pad_km, budget_s=budget_s)
        if r:
            path, length = r
            ratio = length / straight_km if straight_km > 0.01 else 1.0
            result = {"path": [[p[0], p[1]] for p in path], "length_km": length,
                      "straight_km": straight_km, "ratio": ratio,
                      "method": f"overpass:{'+'.join(tag_set)}"}
            cache[key] = result
            return result
        time.sleep(1.0)

    # Nichts gefunden -> Gerade als Notloesung, deutlich markiert
    result = {"path": [[lat1, lon1], [lat2, lon2]], "length_km": straight_km,
              "straight_km": straight_km, "ratio": 1.0, "method": "FALLBACK_GERADE_KEIN_GLEIS_GEFUNDEN"}
    cache[key] = result
    return result
