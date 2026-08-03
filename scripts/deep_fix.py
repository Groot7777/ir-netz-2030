# -*- coding: utf-8 -*-
"""Zweite, aggressivere Fix-Runde fuer die letzten hartnaeckigen Segmente:
groessere Bounding-Box, mehr Rundungsstufen, hoeheres Zeitbudget."""
import time

from routing import load_cache, save_cache, route_pair, haversine_km
import all_stations as ast

TARGETS = [
    ("Essen-Altenessen", "Essen-Borbeck"),
    ("Essen-Steele", "Essen-Steele Ost"),
    ("Essen-Steele Ost", "Essen-Eiberg"),
    ("Bochum-Dahlhausen", "Hattingen Ruhr"),
    ("Ringsted", "Nykoebing Falster"),
    ("Nykoebing Falster", "Roedby"),
]


def main():
    cache = load_cache()
    for a, b in TARGETS:
        lat1, lon1 = ast.get_coord(a)
        lat2, lon2 = ast.get_coord(b)
        straight_km = haversine_km(lat1, lon1, lat2, lon2)
        key = f"{a}||{b}"
        current = cache.get(key, {})
        print(f"\n=== {a} <-> {b} (aktuell Verh. {current.get('ratio', '?')}, Luftlinie {straight_km:.1f}km) ===")
        best = None
        for decimals in (4, 3, 2):
            for tags in (["rail"], ["rail", "construction", "disused", "abandoned"]):
                r = route_pair(lat1, lon1, lat2, lon2, decimals=decimals, tag_values=tags,
                                pad_km=6.0, extra_frac=0.4, max_pad_km=30.0, budget_s=100)
                if r:
                    path, length = r
                    ratio = length / straight_km if straight_km > 0.01 else 1.0
                    print(f"  Rundung {decimals}, Tags {tags}: {length:.1f}km, Verh. {ratio:.2f}")
                    if best is None or ratio < best[0]:
                        best = (ratio, path, length, decimals, tags)
                    if ratio < 1.5:
                        break
                time.sleep(1.0)
            if best and best[0] < 1.5:
                break
        if best:
            ratio, path, length, decimals, tags = best
            print(f"  -> Beste gefundene Option: Verh. {ratio:.2f} (Rundung {decimals}, {tags})")
            cache[key] = {"path": [[p[0], p[1]] for p in path], "length_km": length,
                          "straight_km": straight_km, "ratio": ratio,
                          "method": f"deepfix_rund{decimals}:{'+'.join(tags)}"}
        else:
            print("  -> Keine Verbesserung gefunden, bleibt unveraendert")
    save_cache(cache)
    print("\ngespeichert")


if __name__ == "__main__":
    main()
