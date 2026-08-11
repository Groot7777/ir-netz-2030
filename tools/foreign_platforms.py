#!/usr/bin/env python3
"""
Amtliche Bahnsteig-/Gleislängen fürs Ausland, analog zu tools/dbinfrago_
platforms.py für Deutschland. Quelle: offizielle Open-Data-Portale bzw.
Netzzugangsdokumente der jeweiligen Infrastrukturbetreiber (vom Nutzer
recherchiert, hier maschinell abgerufen und geparst):

  CH  SBB Open Data, Datensatz "perron" (Perron-Nutzlänge je Gleis)
      https://data.sbb.ch/explore/dataset/perron/
  PL  PKP PLK, Regulamin sieci 2025/2026, Anlage 2.18 "Wykaz peronów"
      (amtliche XLSX-Tabelle, Teil des Netzzugangsdokuments)
  FR  SNCF Réseau Open Data, Datensatz "liste-des-quais"
      https://ressources.data.sncf.com/explore/dataset/liste-des-quais/
  DK  Banedanmark Netredegørelse 2026, Bilag 3.6 "Perronlængder og -højder"
      (amtliche PDF-Tabelle, Teil des Netzzugangsdokuments)

Rohdaten liegen in data/foreign_cache/ (per curl/WebSearch abgerufen,
siehe Docstring der jeweiligen fetch_*-Funktion für die genaue URL).
Stationsnamen werden explizit auf unsere App-Namen gemappt (kein
Fuzzy-Matching wie bei DB InfraGO — bei nur ~60 betroffenen Stationen ist
eine harte Zuordnungstabelle sicherer und nachvollziehbarer).

Andere recherchierte Länder (AT/ÖBB, NL/ProRail, LU/CFL, CZ/Správa
železnic, BE/Infrabel) hatten keine in vertretbarem Aufwand erreichbare
strukturierte Bahnsteiglängen-Tabelle (JS-Portale ohne API, oder nur als
mehrhundertseitiges PDF ohne klar auffindbare Anlage) — diese Stationen
bleiben auf OSM/Overpass als Quelle.

Nutzung:
    python3 tools/foreign_platforms.py --out data/foreign_platforms.json
"""
import argparse
import collections
import json
import pathlib
import re

CACHE = pathlib.Path(__file__).resolve().parent.parent / "data" / "foreign_cache"

# App-Stationsname -> Name im jeweiligen amtlichen Datensatz
CH_NAME_MAP = {
    "Buchs SG": "Buchs SG",
    "Chur": "Chur",
    "Frauenfeld": "Frauenfeld",
    "Kreuzlingen": "Kreuzlingen",
    "Landquart": "Landquart",
    "Sargans": "Sargans",
    "Weinfelden": "Weinfelden",
    "Winterthur": "Winterthur",
    "Zürich Flughafen": "Zurich Flughafen",
    "Zürich HB": "Zurich HB",
}

PL_NAME_MAP = {
    "Chałupy": "Chałupy",
    "Chojnice": "Chojnice",
    "Gdańsk Główny": "Gdańsk Główny",
    "Gdańsk Wrzeszcz": "Gdańsk Wrzeszcz",
    "Gdynia Chylonia": "Gdynia Chylonia",
    "Gdynia Główna": "Gdynia Główna",
    "Hel": "Hel",
    "Jastarnia": "Jastarnia",
    "Jurata": "Jurata",
    "Kuźnica": "Kuźnica (Hel)",
    "Mrzezino": "Mrzezino",
    "Puck": "Puck",
    "Reda": "Reda",
    "Rumia": "Rumia",
    "Runowo Pomorskie": "Runowo Pomorskie",
    "Starogard Gdański": "Starogard Gdański",
    "Swarzewo": "Swarzewo",
    "Szczecin Główny": "Szczecin Główny",
    "Szczecinek": "Szczecinek",
    "Tczew": "Tczew",
    "Władysławowo": "Władysławowo",
    "Władysławowo Port": "Władysławowo Port",
    # Gdańsk Zaspa, Gdynia Wzgórze Św. Maksymiliana, Rumia Janowo: nicht im
    # PLK-Bahnsteigverzeichnis (kleine Vorortshalte) -> bleiben bei OSM.
}

FR_NAME_MAP = {
    "Béning": "Béning",
    "Forbach": "Forbach",
    "Hagondange": "Hagondange",
    "Metz-Ville": "Metz-Ville",
    "Mulhouse-Ville": "Mulhouse-Ville",
    "Saint-Avold": "St-Avold",
    "Thionville": "Thionville",
}

DK_NAME_MAP = {
    "Bramming": "Bramming",
    "Esbjerg": "Esbjerg",
    "Fredericia": "Fredericia",
    "Kolding": "Kolding",
    "København H": "København H",
    "Køge Nord": "Køge Nord",
    "Lunderskov": "Lunderskov",
    "Nykøbing F.": "Nykøbing F",
    "Næstved": "Næstved",
    "Nørreport": "Nørreport",
    "Padborg": "Padborg",
    "Ribe": "Ribe",
    "Ringsted": "Ringsted",
    "Rødby": "Rødby Færge",
    "Tønder": "Tønder",
    "Vamdrup": "Vamdrup",
    "Vojens": "Vojens",
    "Vordingborg": "Vordingborg",
}


def _dedup_max(tracks):
    best = {}
    order = []
    for label, length in tracks:
        label = str(label).strip()
        if not label:
            continue
        if label not in best:
            order.append(label)
        best[label] = max(best.get(label, 0), length)
    return [{"gleis": label, "length_m": best[label]} for label in order]


def parse_ch():
    """SBB Open Data, Datensatz 'perron': p_nr = Gleis-/Perronnummer,
    p_lange = Nutzlänge in Metern, bps_name = Stationsname (ASCII, ohne
    Umlaute -> CH_NAME_MAP übersetzt zurück auf unsere App-Namen)."""
    raw = json.loads((CACHE / "ch_sbb_perron_raw.json").read_text(encoding="utf-8"))
    by_dataset_name = collections.defaultdict(list)
    for r in raw:
        if r.get("p_lange") is None:
            continue
        by_dataset_name[r["bps_name"]].append((r["p_nr"], r["p_lange"]))

    out = {}
    for app_name, ds_name in CH_NAME_MAP.items():
        tracks = by_dataset_name.get(ds_name)
        if tracks:
            out[app_name] = {
                "source": "SBB Open Data (data.sbb.ch, Datensatz 'perron')",
                "tracks": _dedup_max(tracks),
            }
    return out


def parse_pl():
    """PKP PLK Anlage 2.18 'Wykaz peronów': Nr toru = Gleisnummer, Długość
    entweder eine Zahl oder 'N: x \\nP: y' (Nutzlänge je nach Fahrtrichtung
    unterschiedlich) -> konservativ das Minimum verwenden."""
    import openpyxl

    wb = openpyxl.load_workbook(CACHE / "pl_plk_perony.xlsx", data_only=True)
    ws = wb["Załącznik 2.18 dane"]
    by_dataset_name = collections.defaultdict(list)
    for row in ws.iter_rows(min_row=8, values_only=True):
        name, _wyroznik, _zaklad, _peron, tor, _wysokosc, dlugosc = row[:7]
        if not name or tor is None or dlugosc is None:
            continue
        nums = [float(x) for x in re.findall(r"[\d.]+", str(dlugosc))]
        if not nums:
            continue
        by_dataset_name[name].append((str(tor), min(nums)))

    out = {}
    for app_name, ds_name in PL_NAME_MAP.items():
        tracks = by_dataset_name.get(ds_name)
        if tracks:
            out[app_name] = {
                "source": "PKP PLK, Regulamin sieci 2025/2026, Anlage 2.18 'Wykaz peronów'",
                "tracks": _dedup_max(tracks),
            }
    return out


def parse_fr():
    """SNCF Réseau Open Data, Datensatz 'liste-des-quais': libelle = Gleis-/
    Quai-Bezeichnung, longueur = Länge in Metern."""
    raw = json.loads((CACHE / "fr_sncf_quais_raw.json").read_text(encoding="utf-8"))
    by_dataset_name = collections.defaultdict(list)
    for r in raw:
        if r.get("longueur") is None or not r.get("lib_gare"):
            continue
        label = r.get("libelle") or r.get("code_voie") or "?"
        by_dataset_name[r["lib_gare"]].append((label, r["longueur"]))

    out = {}
    for app_name, ds_name in FR_NAME_MAP.items():
        tracks = by_dataset_name.get(ds_name)
        if tracks:
            out[app_name] = {
                "source": "SNCF Réseau Open Data (ressources.data.sncf.com, Datensatz 'liste-des-quais')",
                "tracks": _dedup_max(tracks),
            }
    return out


def parse_dk():
    """Banedanmark Netredegørelse 2026, Bilag 3.6: Spornummer = Gleis-
    nummer, Perron-længde i meter = Länge. data/foreign_cache/dk_parsed.json
    ist bereits vorverarbeitet (pdfplumber-Extraktion, siehe
    fetch_dk_notes.txt), Zeilen als (TIB, Stationsnavn, Perronnr, Spornr,
    Længde, Højde)."""
    rows = json.loads((CACHE / "dk_parsed.json").read_text(encoding="utf-8"))
    by_dataset_name = collections.defaultdict(list)
    for _tib, name, _perron, spor, laengde, _hoejde in rows:
        by_dataset_name[name].append((spor, float(laengde)))

    out = {}
    for app_name, ds_name in DK_NAME_MAP.items():
        tracks = by_dataset_name.get(ds_name)
        if tracks:
            out[app_name] = {
                "source": "Banedanmark Netredegørelse 2026, Bilag 3.6 'Perronlængder og -højder'",
                "tracks": _dedup_max(tracks),
            }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/foreign_platforms.json")
    args = ap.parse_args()

    result = {}
    counts = {}
    for label, fn in [("CH", parse_ch), ("PL", parse_pl), ("FR", parse_fr), ("DK", parse_dk)]:
        part = fn()
        counts[label] = len(part)
        for st, info in part.items():
            info["max_length_m"] = max((t["length_m"] for t in info["tracks"]), default=0)
        result.update(part)

    pathlib.Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"{len(result)} Stationen -> {args.out}")
    print("Je Land:", counts)


if __name__ == "__main__":
    main()
