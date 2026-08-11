#!/usr/bin/env python3
"""
Prüft die Stationssymbol-Positionen in der vom Nutzer bereitgestellten KML
(RENetz_2030_v3.kml) gegen echte OpenStreetMap/Overpass-Bahnhofsknoten:
manche Placemark-Koordinaten sitzen nicht exakt auf dem echten Bahnhof
(Verschiebung durch manuelle Erfassung). Findet den nächstgelegenen
namensähnlichen OSM-Bahnhofsknoten je KML-Station und meldet die
Abweichung; ab --threshold-m gilt sie als Korrekturkandidat.

Nominatim (OSM-Geocoding) wurde verworfen: es priorisiert bei knappen
Ortsnamen wie "Allensbach" die Gemeinde-/Ortskern-Koordinate über den
tatsächlichen railway=halt-Knoten, was in Stichproben falsche "weit
daneben"-Befunde lieferte (Allensbach z.B. 251m "Abweichung", obwohl die
KML-Position exakt auf dem echten OSM-Halt lag). Overpass liest die
railway=station/halt-Tags direkt und ist daher robuster für diese Aufgabe
— auch wenn es in dieser Umgebung zeitweise durch Rate-Limiting komplett
blockiert war; nach einer Wartezeit ohne weitere Anfragen war es wieder
erreichbar.

Batches: je Station ein "around"-Filter in einer gemeinsamen Anfrage
(kleine Batches + Pausen, um das Rate-Limit nicht erneut auszulösen),
Named-Matching danach lokal in Python (die Overpass-Antwort verrät nicht,
welcher Treffer zu welcher Abfrage-Station gehört — Zuordnung über
Namensähnlichkeit + kürzeste Distanz).

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
RADIUS_M = 4000
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CACHE_DIR = pathlib.Path("data/kml_work/osm_station_cache")
MAX_RETRIES = 5
RETRY_BACKOFF_S = 20
BATCH_PAUSE_S = 5.0  # zusaetzlich zu wait_for_slot() als Mindestabstand

UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                         "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})
ABBREV = [
    (re.compile(r"\bHbf\b"), "Hauptbahnhof"),
    (re.compile(r"\bBf\b"), "Bahnhof"),
    (re.compile(r"\bHst\b"), "Haltestelle"),
]
# Generische Bestandteile von Bahnhofsnamen — ein gemeinsames "Hauptbahnhof"
# oder ein gemeinsamer Stadtname ALLEIN ist KEIN Beleg fuer denselben
# Bahnhof (z.B. sonst "Lüdenscheid Hbf" == "Mainz Hauptbahnhof", weil beide
# nur "Hauptbahnhof" teilen; oder "Bochum-Kohlenstraße" == "Bochum-
# Ehrenfeld", weil beide "Bochum" teilen). Muessen beim Namensvergleich
# ignoriert werden, damit nur die UNTERSCHEIDENDEN Woerter zaehlen.
GENERIC_WORDS = {
    "hauptbahnhof", "bahnhof", "hbf", "bf", "hst", "haltestelle", "bahnhst",
    "ost", "west", "nord", "sued", "sud", "mitte", "tief", "gleis", "hp",
}


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
    kw, ow = norm_words(kml_name) - GENERIC_WORDS, norm_words(osm_name) - GENERIC_WORDS
    if not kw or not ow:
        # Nur generische Woerter uebrig (z.B. Name bestand nur aus
        # "Hauptbahnhof") -> kein verlaesslicher Fuzzy-Match moeglich.
        return False
    # Die kleinere (unterscheidende) Wortmenge muss (fast) vollstaendig in
    # der anderen enthalten sein — wie bei der DB-InfraGO-Namensabgleichung
    # etabliert, nicht nur ein loser Ueberlappungs-Anteil.
    inter = kw & ow
    smaller = min(len(kw), len(ow))
    return len(inter) >= smaller and len(inter) / max(len(kw), len(ow)) >= 0.5


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
        clauses.append(f'node["public_transport"="station"]["train"="yes"](around:{RADIUS_M},{lat},{lon});')
    return f'[out:json][timeout:90];({"".join(clauses)});out body;'


def batch_cache_key(batch):
    raw = json.dumps(batch, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def wait_for_slot():
    """Fragt /api/status, wartet bis ein Slot frei ist, statt blind eine
    feste Pause zu verstreichen — vermeidet erneutes Rate-Limiting robuster
    als ein starres time.sleep()."""
    try:
        proc = subprocess.run(
            ["curl", "-sS", "--max-time", "20", "-A", "RENetz2030-Taktoptimierung/1.0", "https://overpass-api.de/api/status"],
            capture_output=True, text=True, timeout=25,
        )
        m = re.search(r"Slot available after: [^,]+, in (-?\d+) seconds", proc.stdout)
        if m:
            secs = max(0, int(m.group(1)))
            if secs > 0:
                print(f"    warte auf freien Overpass-Slot: {secs}s", file=sys.stderr)
                time.sleep(min(secs, 90) + 2)
    except (subprocess.TimeoutExpired, OSError):
        pass  # Statusabfrage selbst fehlgeschlagen -> einfach mit fester Pause weiter


def fetch_batch(batch, force=False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = batch_cache_key(batch)
    cache_path = CACHE_DIR / f"{key}.json"
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    wait_for_slot()
    query = build_query(batch)
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            proc = subprocess.run(
                [
                    "curl", "-sS", "--max-time", "100", "-X", "POST",
                    "-A", "RENetz2030-Taktoptimierung/1.0 (KML-Stationsabgleich; +https://github.com/Groot7777/ir-netz-2030)",
                    "--data-urlencode", f"data={query}",
                    OVERPASS_URL,
                ],
                capture_output=True, text=True, timeout=110,
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
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()

    kml_text = pathlib.Path(args.kml).read_text(encoding="utf-8")
    pattern = re.compile(
        r"<Placemark>\s*<name>(.*?)</name>.*?<Point><coordinates>([\d.\-]+),([\d.\-]+),\d+</coordinates></Point>\s*</Placemark>",
        re.DOTALL,
    )
    stations = [(m.group(1), float(m.group(2)), float(m.group(3))) for m in pattern.finditer(kml_text)]
    stations = stations[args.start :]
    if args.limit:
        stations = stations[: args.limit]
    print(f"{len(stations)} KML-Stationen (ab Index {args.start})")

    out_path = pathlib.Path(args.out)
    results = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() and not args.force else {}

    batches = [stations[i : i + BATCH_SIZE] for i in range(0, len(stations), BATCH_SIZE)]
    for bi, batch in enumerate(batches, 1):
        batch = [b for b in batch if b[0] not in results or args.force]
        if not batch:
            continue
        print(f"  Batch {bi}/{len(batches)} ({batch[0][0]} ... {batch[-1][0]})")
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
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(BATCH_PAUSE_S)

    n_ok = sum(1 for r in results.values() if r["distance_m"] is not None and r["distance_m"] <= args.threshold_m)
    n_off = sum(1 for r in results.values() if r["distance_m"] is not None and r["distance_m"] > args.threshold_m)
    n_none = sum(1 for r in results.values() if r["distance_m"] is None)
    print(f"\n{len(results)} Stationen -> {out_path}")
    print(f"ok (<= {args.threshold_m:.0f}m): {n_ok}   auffaellig (> {args.threshold_m:.0f}m): {n_off}   kein OSM-Treffer: {n_none}")


if __name__ == "__main__":
    main()
