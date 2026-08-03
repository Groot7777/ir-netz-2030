# -*- coding: utf-8 -*-
"""
Netzweite Verhaeltnis-Pruefung (reale Weglaenge / Luftlinie) mit automatischem
Fix-Versuch fuer auffaellige Segmente: lokal begrenzter Graph mit gerundeten
Koordinaten (4 dann 3 Nachkommastellen), um knapp benachbarte, nicht offiziell
verbundene Gleis-Knoten zu verschmelzen.
"""
import json
import time

from routing import (
    load_cache, save_cache, cache_key, haversine_km, route_pair,
    FICTIONAL_STRAIGHT_LINE_PAIRS,
)


def flag_suspicious(cache, threshold=1.7):
    flagged = []
    for key, entry in cache.items():
        a, b = key.split("||")
        if frozenset([a, b]) in FICTIONAL_STRAIGHT_LINE_PAIRS:
            continue
        ratio = entry.get("ratio", 1.0)
        if ratio > threshold or "FALLBACK_GERADE" in entry.get("method", ""):
            flagged.append((key, entry))
    return flagged


def try_local_fix(a_key, b_key, lat1, lon1, lat2, lon2, straight_km):
    """Versucht mit gerundeten Koordinaten (Knoten-Verschmelzung) einen kuerzeren,
    plausibleren Pfad zu finden."""
    for decimals in (4, 3):
        for tag_values in (["rail"], ["rail", "construction"], ["rail", "construction", "disused", "abandoned"]):
            r = route_pair(lat1, lon1, lat2, lon2, decimals=decimals, tag_values=tag_values,
                            pad_km=4.0, extra_frac=0.3, max_pad_km=20.0, budget_s=120)
            if r:
                path, length = r
                ratio = length / straight_km if straight_km > 0.01 else 1.0
                if ratio < 1.8:
                    return {"path": [[p[0], p[1]] for p in path], "length_km": length,
                            "straight_km": straight_km, "ratio": ratio,
                            "method": f"lokalfix_rund{decimals}:{'+'.join(tag_values)}"}
            time.sleep(1.0)
    return None


def main():
    cache = load_cache()
    flagged = flag_suspicious(cache)
    print(f"{len(cache)} Segmente im Cache, {len(flagged)} auffaellig (Verhaeltnis > 1.7 oder kein Gleis gefunden):")
    for key, entry in flagged:
        print(f"  {key}: {entry.get('ratio', 0):.2f} ({entry.get('method')}, "
              f"{entry.get('length_km', 0):.1f}km vs Luftlinie {entry.get('straight_km', 0):.1f}km)")

    fixed_count = 0
    still_bad = []
    for key, entry in flagged:
        a, b = key.split("||")
        straight_km = entry["straight_km"]
        path = entry["path"]
        lat1, lon1 = path[0]
        lat2, lon2 = path[-1]
        print(f"\nVersuche Lokalfix fuer {key} (aktuell {entry.get('ratio', 0):.2f})...")
        fix = try_local_fix(a, b, lat1, lon1, lat2, lon2, straight_km)
        if fix:
            print(f"  -> Verbessert: {fix['ratio']:.2f} ({fix['method']})")
            cache[key] = fix
            fixed_count += 1
        else:
            print(f"  -> Kein besserer Pfad gefunden, bleibt bei {entry.get('ratio', 0):.2f}")
            still_bad.append((key, entry))

    save_cache(cache)
    print(f"\n{fixed_count} Segmente verbessert, {len(still_bad)} bleiben auffaellig:")
    for key, entry in still_bad:
        print(f"  {key}: {entry.get('ratio', 0):.2f} ({entry.get('method')})")


if __name__ == "__main__":
    main()
