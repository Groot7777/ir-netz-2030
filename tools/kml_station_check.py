#!/usr/bin/env python3
"""
Prüft die Stationssymbol-Positionen in der vom Nutzer bereitgestellten KML
(RENetz_2030_v3.kml) gegen echte OpenStreetMap/Overpass-Bahnhofsknoten:
manche Placemark-Koordinaten sitzen nicht exakt auf dem echten Bahnhof
(Verschiebung durch manuelle Erfassung). Findet den nächstgelegenen
namensähnlichen OSM-Bahnhofsknoten je KML-Station und meldet die
Abweichung; ab --threshold-m gilt sie als Korrekturkandidat.

Batches wie tools/overpass_platforms.py: je Station ein "around"-Filter
in einer gemeinsamen Anfrage, Named-Matching danach lokal in Python (die
Overpass-Antwort verrät nicht, welcher Treffer zu welcher Abfrage-Station
gehört — Zuordnung über Namensähnlichkeit + kürzeste Distanz).

Nutzung:
    python3 tools/kml_station_check.py --kml <pfad> --out data/kml_work/kml_check.json
"""
import argparse
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys
import time

BATCH_SIZE = 20
RADIUS_M = 6000
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CACHE_DIR = pathlib.Path("data/kml_work/osm_station_cache")
MAX_RETRIES = 5
RETRY_BACKOFF_S = 6

UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                         "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})
ABBREV = [
    (re.compile(r"\bHbf\b"), "Hauptbahnhof"),
    (re.compile(r"\bBf\b"), "Bahnhof"),
    (re.compile(r"\bHst\b"), "Haltestelle"),
]


def norm(s):
    s = s.translate(UMLAUT)
    for pat, repl in ABBREV:
        s = pat.sub(repl, s)
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s).lower().strip()
    return s


def norm_words(s):
    return set(norm(s).split())


def name_match(kml_name, osm_name):
    if not osm_name:
        return False
    if norm(kml_name) == norm(osm_name):
        return True
    kw, ow = norm_words(kml_name), norm_words(osm_name)
    if not kw or not ow:
        return False
    # eine Namensmenge muss (fast) vollstaendig in der anderen enthalten sein
    inter = kw & ow
    return len(inter) >= max(1, min(len(kw), len(ow)) - 1) and len(inter) / max(len(kw), len(ow)) >= 0.5


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def build_query(batch):
    clauses = []
    for _name, lon, lat in batch:
        clauses.append(f'node["railway"~"^(station|halt)$"](around:{RADIUS_M},{lat},{lon});')
        clauses.append(f'node["public_transport"="station"]["railway"](around:{RADIUS_M},{lat},{lon});')
        clauses.append(f'node["public_transport"="station"]["train"="yes"](around:{RADIUS_M},{lat},{lon});')
    return f'[out:json][timeout:120];({"".join(clauses)});out body;'


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
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            proc = subprocess.run(
                [
                    "curl", "-sS", "--max-time", "150", "-X", "POST",
                    "-A", "RENetz2030-Taktoptimierung/1.0 (KML-Stationsabgleich; +https://github.com/Groot7777/ir-netz-2030)",
                    "--data-urlencode", f"data={query}",
                    OVERPASS_URL,
                ],
                capture_output=True, text=True, timeout=160,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"curl exit {proc.returncode}: {proc.stderr.strip()[:300]}")
            result = json.loads(proc.stdout)
            cache_path.write_text(json.dumps(result), encoding="utf-8")
            return result
        except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as e:
            last_err = e
            wait = RETRY_BACKOFF_S * attempt
            print(f"    Versuch {attempt}/{MAX_RETRIES} fehlgeschlagen ({e}) — warte {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"    Batch endgueltig fehlgeschlagen ({last_err}) — uebersprungen", file=sys.stderr)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kml", required=True)
    ap.add_argument("--out", default="data/kml_work/kml_check.json")
    ap.add_argument("--threshold-m", type=float, default=150.0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    pattern = re.compile(
        r"<Placemark>\s*<name>(.*?)</name>.*?<Point><coordinates>([\d.\-]+),([\d.\-]+),\d+</coordinates></Point>\s*</Placemark>",
        re.DOTALL,
    )
    stations = [(m.group(1), float(m.group(2)), float(m.group(3))) for m in pattern.finditer(kml_text)]
    if args.limit:
        stations = stations[: args.limit]
    print(f"{len(stations)} KML-Stationen gefunden")

    batches = [stations[i : i + BATCH_SIZE] for i in range(0, len(stations), BATCH_SIZE)]
    results = {}
    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}/{len(batches)} ({batch[0][0]} ... {batch[-1][0]})")
        resp = fetch_batch(batch, force=args.force)
        elements = resp.get("elements", []) if resp else []
        for name, lon, lat in batch:
            candidates = []
            for el in elements:
                osm_name = el.get("tags", {}).get("name")
                if not name_match(name, osm_name):
                    continue
                d = haversine_m(lat, lon, el["lat"], el["lon"])
                candidates.append((d, el["lat"], el["lon"], osm_name, el["type"], el["id"]))
            candidates.sort(key=lambda c: c[0])
            if candidates:
                d, olat, olon, osm_name, etype, eid = candidates[0]
                results[name] = {
                    "kml_lon": lon, "kml_lat": lat,
                    "osm_lon": round(olon, 7), "osm_lat": round(olat, 7),
                    "osm_name": osm_name, "distance_m": round(d, 1),
                    "osm_ref": f"{etype}/{eid}", "n_candidates": len(candidates),
                }
            else:
                results[name] = {
                    "kml_lon": lon, "kml_lat": lat,
                    "osm_lon": None, "osm_lat": None,
                    "osm_name": None, "distance_m": None,
                    "osm_ref": None, "n_candidates": 0,
                }
        time.sleep(1.5)

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    n_ok = sum(1 for r in results.values() if r["distance_m"] is not None and r["distance_m"] <= args.threshold_m)
    n_off = sum(1 for r in results.values() if r["distance_m"] is not None and r["distance_m"] > args.threshold_m)
    n_none = sum(1 for r in results.values() if r["distance_m"] is None)
    print(f"\n{len(results)} Stationen -> {args.out}")
    print(f"ok (<= {args.threshold_m:.0f}m): {n_ok}   auffaellig (> {args.threshold_m:.0f}m): {n_off}   kein OSM-Treffer: {n_none}")


if __name__ == "__main__":
    main()
