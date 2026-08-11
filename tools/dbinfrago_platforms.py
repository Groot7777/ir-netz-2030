#!/usr/bin/env python3
"""
Holt Bahnsteig-Nettobaulängen von dbinfrago.com für alle deutschen
Stationen im Netz (Zuordnung Name -> Slug in data/de_station_slugs.json,
per Abgleich der HTML-Stationssuche mit den Stationsnamen aus der App
ermittelt — siehe Kommentar unten für die Herleitung).

WICHTIG: dbinfrago.com weist selbst darauf hin, dass die "Nettobaulänge"
NICHT für die Zugplanung geeignet ist -- maßgeblich ist die "Bahnsteig-
nutzlänge" (abhängig von Signalstandorten, separat beim Betreiber zu
erfragen). Die hier geholten Werte sind trotzdem eine sehr viel
verlässlichere Obergrenze als die OSM-Schätzung.

Speichert pro Station ALLE Gleise mit ihrer individuellen Länge (nicht
nur das Maximum), damit z.B. "Gleis 5: 200m, Gleis 7: 400m" abrufbar
bleibt für eine spätere gleisscharfe Prüfung.

Cached jede Rohantwort unter data/dbinfrago_cache/<slug>.html, damit ein
Abbruch mitten im Lauf (346 Stationen, ~10min) ohne Neuabfrage der schon
erledigten Stationen fortsetzbar ist.

Nutzung:
    python3 tools/dbinfrago_platforms.py \
        --slugs data/de_station_slugs.json \
        --out data/dbinfrago_platforms.json
"""
import argparse
import json
import pathlib
import re
import subprocess
import time

BASE = "https://www.dbinfrago.com/web/bahnhoefe/leistungen/stationsnutzung/stationshalt/stationsausstattung/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
CACHE_DIR = pathlib.Path("data/dbinfrago_cache")

ROW_RE = re.compile(r"Bahnsteigabschnittsmarkierungen\s*\|.*?<p>(.*?)</p>", re.S)


def fetch_html(slug, force=False, max_retries=3):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{slug}.html"
    if cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    for attempt in range(1, max_retries + 1):
        r = subprocess.run(
            ["curl", "-sS", "-A", UA, "--max-time", "30", BASE + slug],
            capture_output=True, text=True,
        )
        if r.stdout and "Nettobaulänge" in r.stdout:
            cache_path.write_text(r.stdout, encoding="utf-8")
            return r.stdout
        time.sleep(3 * attempt)
    return r.stdout or ""


def parse_tracks(html):
    m = ROW_RE.search(html)
    if not m:
        return None
    rows_raw = m.group(1).split("<br>")
    tracks = []
    for row in rows_raw:
        cells = [c.strip() for c in row.split("|")]
        if len(cells) < 3:
            continue
        gleis = cells[0]
        height = cells[1]
        length_raw = cells[2]
        lm = re.search(r"([\d.,]+)\s*m", length_raw)
        if not lm:
            continue
        length_m = float(lm.group(1).replace(",", "."))
        tracks.append({"gleis": gleis, "height": height, "length_m": length_m})
    return tracks or None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slugs", default="data/de_station_slugs.json")
    ap.add_argument("--out", default="data/dbinfrago_platforms.json")
    ap.add_argument("--limit", type=int, default=None, help="nur die ersten N Stationen (Test)")
    ap.add_argument("--force", action="store_true", help="Cache ignorieren, alles neu abfragen")
    args = ap.parse_args()

    stations = json.loads(pathlib.Path(args.slugs).read_text(encoding="utf-8"))
    items = list(stations.items())
    if args.limit:
        items = items[: args.limit]

    out = {}
    n_ok = n_fail = 0
    for i, (name, slug) in enumerate(items, 1):
        html = fetch_html(slug, force=args.force)
        tracks = parse_tracks(html)
        if tracks:
            best = max(t["length_m"] for t in tracks)
            out[name] = {"source_slug": slug, "tracks": tracks, "max_length_m": best}
            n_ok += 1
            print(f"  [{i}/{len(items)}] {name}: {len(tracks)} Gleise, längster {best:.0f} m")
        else:
            out[name] = {"source_slug": slug, "tracks": None, "max_length_m": None}
            n_fail += 1
            print(f"  [{i}/{len(items)}] {name}: KEINE Tabelle gefunden")
        if not (CACHE_DIR / f"{slug}.html").exists() or args.force:
            time.sleep(1.2)

    pathlib.Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"\n{args.out}: {n_ok} mit Daten, {n_fail} ohne Tabelle, von {len(items)} Stationen")


if __name__ == "__main__":
    main()
