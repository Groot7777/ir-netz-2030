# -*- coding: utf-8 -*-
"""Batch-Routing aller Bahnhofspaare der 5 neuen Linien, sequentiell mit Pausen."""
import time

import lines_data as ld
import all_stations as ast
from routing import route_and_cache, load_cache, save_cache


def unique_pairs():
    seen = set()
    pairs = []
    for line in ld.ALL_LINES:
        for br in line["branches"]:
            stops = br["stops"]
            for i in range(len(stops) - 1):
                a, b = stops[i][0], stops[i + 1][0]
                k = tuple(sorted([a, b]))
                if k in seen:
                    continue
                seen.add(k)
                pairs.append((a, b))
    return pairs


def main():
    cache = load_cache()
    pairs = unique_pairs()
    print(f"{len(pairs)} eindeutige Paare, {len(cache)} bereits im Cache")
    todo = [(a, b) for a, b in pairs if f"{a}||{b}" not in cache and f"{b}||{a}" not in cache]
    print(f"{len(todo)} neu zu routen")
    ratio_warnings = []
    for i, (a, b) in enumerate(todo, 1):
        lat1, lon1 = ast.get_coord(a)
        lat2, lon2 = ast.get_coord(b)
        t0 = time.time()
        result = route_and_cache(a, b, lat1, lon1, lat2, lon2, cache)
        dt = time.time() - t0
        flag = ""
        if result["ratio"] > 1.6:
            flag = f"  <== VERDAECHTIG (Verhaeltnis {result['ratio']:.1f})"
            ratio_warnings.append((a, b, result["ratio"]))
        if "FALLBACK_GERADE" in result["method"]:
            flag = "  <== KEIN GLEIS GEFUNDEN, GERADE VERWENDET"
            ratio_warnings.append((a, b, result["ratio"]))
        print(f"[{i}/{len(todo)}] {a} <-> {b}: {result['length_km']:.1f}km "
              f"(Luftlinie {result['straight_km']:.1f}km, Verh. {result['ratio']:.2f}, "
              f"{result['method']}, {dt:.1f}s){flag}")
        if i % 5 == 0:
            save_cache(cache)
        time.sleep(1.5)
    save_cache(cache)
    print(f"\nFertig. {len(ratio_warnings)} auffaellige Segmente:")
    for a, b, r in ratio_warnings:
        print(f"  {a} <-> {b}: Verhaeltnis {r:.2f}")


if __name__ == "__main__":
    main()
