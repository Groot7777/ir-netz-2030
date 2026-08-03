# -*- coding: utf-8 -*-
"""Baut pro Linien-Ast die vollstaendige Koordinatenliste aus den geroutet Segmenten
zusammen und wendet Douglas-Peucker (Toleranz ~18m) an."""
import json
import os

import lines_data as ld
import all_stations as ast
from simplify import douglas_peucker

ROUTES_CACHE = os.path.join(os.path.dirname(__file__), "..", "cache", "routes_cache.json")


def load_routes():
    with open(ROUTES_CACHE, encoding="utf-8") as f:
        return json.load(f)


def segment_path(routes, a_key, b_key):
    fwd = f"{a_key}||{b_key}"
    rev = f"{b_key}||{a_key}"
    if fwd in routes:
        return [tuple(p) for p in routes[fwd]["path"]]
    if rev in routes:
        return [tuple(p) for p in reversed(routes[rev]["path"])]
    raise KeyError(f"Keine Route fuer {a_key} <-> {b_key}")


def full_branch_path(routes, stops):
    """stops: Liste von Row-Tupeln (erstes Element = key). Gibt volle (unvereinfachte)
    Koordinatenliste (lat, lon) fuer den gesamten Ast zurueck."""
    keys = [row[0] for row in stops]
    full = []
    for i in range(len(keys) - 1):
        seg = segment_path(routes, keys[i], keys[i + 1])
        if full and full[-1] == seg[0]:
            full.extend(seg[1:])
        else:
            full.extend(seg)
    return full


def simplified_branch_path(routes, stops, tolerance_m=18.0):
    full = full_branch_path(routes, stops)
    return douglas_peucker(full, tolerance_m=tolerance_m)


if __name__ == "__main__":
    routes = load_routes()
    total_full, total_simplified = 0, 0
    for line in ld.ALL_LINES:
        for br in line["branches"]:
            full = full_branch_path(routes, br["stops"])
            simp = douglas_peucker(full, tolerance_m=18.0)
            total_full += len(full)
            total_simplified += len(simp)
            print(f"{line['number']}/{br['branch_id']}: {len(full)} -> {len(simp)} Punkte "
                  f"({100 - 100*len(simp)/len(full):.0f}% Reduktion)")
    print(f"\nGesamt: {total_full} -> {total_simplified} Punkte")
