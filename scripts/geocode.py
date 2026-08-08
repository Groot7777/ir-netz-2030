# -*- coding: utf-8 -*-
"""
Geocoding aller neuen Stationen via Photon API (photon.komoot.io), mit
Bias-Koordinaten pro Region zur Disambiguierung, Cache-Datei, und Fallback-
Kette: railway:station -> railway:halt -> freie Adress-/Ortssuche.
"""
import json
import math
import os
import time
import urllib.parse

import requests

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "cache", "stations_cache.json")
PHOTON_URL = "https://photon.komoot.io/api/"
HEADERS = {"User-Agent": "ir-netz-2030-kml-builder/1.0 (fiktives Bahnliniennetz, privates Hobbyprojekt)"}

# Regionale Bias-Anker (lat, lon) zur Disambiguierung mehrdeutiger Namen.
REGION = {
    "brandenburg_berlin": (52.5, 13.2),
    "pomerania_west": (53.5, 14.7),
    "pomerania_central": (53.7, 17.0),
    "gdansk_area": (54.37, 18.62),
    "hel_peninsula": (54.72, 18.45),
    "ruhrgebiet": (51.45, 7.3),
    "ruhrtal_volme": (51.35, 7.6),
    "denmark": (55.68, 12.57),
    "schleswig_holstein": (53.9, 10.9),
    "mecklenburg": (53.85, 11.9),
    "nl_north": (52.9, 6.1),
    "nl_twente": (52.27, 6.8),
    "muensterland": (51.9, 7.6),
    "sauerland": (51.25, 8.35),
    "bergisches_land": (51.25, 7.15),
    "franconia": (49.6, 11.1),
    "bavaria_danube": (48.95, 12.6),
    "alsace_baden": (47.85, 7.5),
    "black_forest": (47.9, 8.3),
    "swabia_danube": (47.95, 9.0),
    "allgaeu": (47.9, 10.2),
    "munich": (48.15, 11.6),
    "lower_bavaria": (48.6, 12.5),
}

# key -> (query_text, region, osm_tag_preference[list], is_fictional_new_build)
# osm_tag_preference: Liste von osm_tag-Filtern, der Reihe nach probiert.
STATION_QUERIES = {
    "Brandenburg Hbf": ("Brandenburg Hbf", "brandenburg_berlin", ["railway:station"], False),

    "Szczecin Glowny": ("Szczecin Główny", "pomerania_west", ["railway:station"], False),
    "Runowo Pomorskie": ("Runowo Pomorskie", "pomerania_west", ["railway:station", "railway:halt"], False),
    "Szczecinek": ("Szczecinek", "pomerania_central", ["railway:station"], False),
    "Chojnice": ("Chojnice", "pomerania_central", ["railway:station"], False),
    "Starogard Gdanski": ("Starogard Gdański", "gdansk_area", ["railway:station"], False),
    "Tczew": ("Tczew", "gdansk_area", ["railway:station"], False),
    "Gdansk Glowny": ("Gdańsk Główny", "gdansk_area", ["railway:station"], False),
    "Gdansk Wrzeszcz": ("Gdańsk Wrzeszcz", "gdansk_area", ["railway:station", "railway:halt"], False),
    "Gdansk Zaspa": ("Gdańsk Zaspa", "gdansk_area", ["railway:halt", "railway:station"], False),
    "Gdynia Wzgorze Sw Maksyma": ("Gdynia Wzgórze Świętego Maksymiliana", "gdansk_area", ["railway:halt", "railway:station"], False),
    "Gdynia Glowna": ("Gdynia Główna", "gdansk_area", ["railway:station"], False),
    "Gdynia Chylonia": ("Gdynia Chylonia", "gdansk_area", ["railway:station", "railway:halt"], False),
    "Rumia Janowo": ("Rumia Janowo", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Rumia": ("Rumia", "hel_peninsula", ["railway:station"], False),
    "Reda": ("Reda", "hel_peninsula", ["railway:station"], False),
    "Mrzezino": ("Mrzezino", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Zelistrzewo": ("Żelistrzewo", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Puck": ("Puck", "hel_peninsula", ["railway:station"], False),
    "Swarzewo": ("Swarzewo", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Wladyslawowo": ("Władysławowo", "hel_peninsula", ["railway:station"], False),
    "Wladyslawowo Port": ("Władysławowo Port", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Chalupy": ("Chałupy", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Kuznica": ("Kuźnica", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Jastarnia": ("Jastarnia", "hel_peninsula", ["railway:station", "railway:halt"], False),
    "Jurata": ("Jurata", "hel_peninsula", ["railway:halt", "railway:station"], False),
    "Hel": ("Hel", "hel_peninsula", ["railway:station"], False),

    "Unna Hbf": ("Unna Bahnhof", "ruhrgebiet", ["railway:station"], False),
    "Unna West": ("Unna West", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Massen": ("Unna-Massen Bahnhof", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Dortmund-Wickede": ("Dortmund-Wickede", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Dortmund-Brackel": ("Dortmund-Brackel", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Dortmund-Dorstfeld": ("Dortmund-Dorstfeld", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Dortmund-Dorstfeld Sued": ("Dortmund-Dorstfeld Süd", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Dortmund-Universitaet": ("Dortmund Universität", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Dortmund-Oespel": ("Dortmund-Oespel", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Dortmund-Kley": ("Dortmund-Kley", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Bochum-Langendreer West": ("Bochum-Langendreer West", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Bochum-Bermuda3eck": ("Bermudadreieck Bochum", "ruhrgebiet", [], True),
    "Bochum West": ("Bochum West", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Bochum-Hamme": ("Bochum-Hamme", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Bochum-Riemke": ("Bochum-Riemke", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Wanne-Eickel Hbf": ("Wanne-Eickel Hauptbahnhof", "ruhrgebiet", ["railway:station"], False),
    "Gelsenkirchen-Zollverein Nord": ("Gelsenkirchen Zollverein Nord", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Essen-Altenessen": ("Essen-Altenessen Bahnhof", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Essen-Borbeck": ("Essen-Borbeck", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Essen-Dellwig Ost": ("Essen-Dellwig Ost", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Muelheim-Styrum": ("Mülheim-Styrum", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Muelheim West": ("Mülheim (Ruhr) West", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Muelheim Ruhr Hbf": ("Mülheim (Ruhr) Hauptbahnhof", "ruhrgebiet", ["railway:station"], False),
    "Essen-Frohnhausen": ("Essen-Frohnhausen", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Essen West": ("Essen West", "ruhrgebiet", ["railway:station", "railway:halt"], False),
    "Essen-Steele Ost": ("Essen-Steele Ost", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Essen-Eiberg": ("Essen-Eiberg", "ruhrgebiet", ["railway:halt", "railway:station"], False),
    "Bochum-Kohlenstrasse": ("Bochum Kohlenstraße", "ruhrgebiet", [], True),
    "Bochum-Stahlhausen": ("Bochum-Stahlhausen", "ruhrgebiet", ["railway:halt", "railway:station"], True),
    "Wengern": ("Wengern", "ruhrtal_volme", ["railway:halt", "railway:station"], False),
    "Hagen-Vorhalle": ("Hagen-Vorhalle", "ruhrtal_volme", ["railway:station", "railway:halt"], False),
    "Schwerte Ruhr": ("Schwerte (Ruhr) Bahnhof", "ruhrtal_volme", ["railway:station"], False),
    "Holzwickede": ("Holzwickede", "ruhrgebiet", ["railway:station", "railway:halt"], False),

    "Essen-Horst": ("Essen-Horst", "ruhrtal_volme", ["railway:station", "railway:halt"], False),
    "Bochum-Dahlhausen": ("Bochum-Dahlhausen", "ruhrtal_volme", ["railway:station", "railway:halt"], False),
    "Hattingen Ruhr": ("Hattingen (Ruhr) Bahnhof", "ruhrtal_volme", ["railway:station"], False),
    "Hattingen Mitte": ("Hattingen Mitte", "ruhrtal_volme", [], True),
    "Heinrichshuette": ("Heinrichshütte Hattingen", "ruhrtal_volme", ["railway:halt", "railway:station"], True),
    "Blankenstein Burg": ("Burg Blankenstein Hattingen", "ruhrtal_volme", [], True),
    "Haus Kemnade": ("Haus Kemnade", "ruhrtal_volme", [], True),
    "Herbede": ("Witten-Herbede Bahnhof", "ruhrtal_volme", ["railway:station", "railway:halt"], True),
    "Ruine Hardenstein": ("Burgruine Hardenstein", "ruhrtal_volme", [], True),
    "Zeche Nachtigall": ("Zeche Nachtigall Witten", "ruhrtal_volme", [], True),
    "Witten Bommern": ("Witten-Bommern", "ruhrtal_volme", ["railway:station", "railway:halt"], True),
    "Wengern Ost": ("Wengern Ost", "ruhrtal_volme", ["railway:halt", "railway:station"], False),
    "Dahl": ("Dahl (Volmetalbahn)", "ruhrtal_volme", ["railway:station", "railway:halt"], False),
    "Rummenohl": ("Rummenohl", "ruhrtal_volme", ["railway:station", "railway:halt"], False),
    "Dahlerbrueck": ("Dahlerbrück", "ruhrtal_volme", ["railway:station", "railway:halt"], False),
    "Schalksmuehle": ("Schalksmühle", "ruhrtal_volme", ["railway:station", "railway:halt"], False),
    "Luedenscheid Hbf": ("Lüdenscheid Bahnhof", "ruhrtal_volme", ["railway:station"], False),

    "Oesterport": ("Østerport Station", "denmark", ["railway:station"], False),
    "Koebenhavn H": ("København H", "denmark", ["railway:station"], False),
    "Ringsted": ("Ringsted Station", "denmark", ["railway:station"], False),
    "Nykoebing Falster": ("Nykøbing Falster Station", "denmark", ["railway:station"], False),
    "Roedby": ("Rødby Station", "denmark", ["railway:station", "railway:halt"], False),
    "Grossenbrode Heiligenhafen": ("Kreisstraße 42 Mittelhof Großenbrode", "schleswig_holstein", [], True),
    "Oldenburg in Holstein": ("Bahnhofstraße 22 Oldenburg in Holstein", "schleswig_holstein", ["railway:station"], False),
    "Scharbeutz": ("Bövelstredder Scharbeutz", "schleswig_holstein", [], True),
    "Timmendorfer Strand Ratekau": ("Bäderstraße Ratekau Timmendorfer Strand", "schleswig_holstein", [], True),
    "Bad Schwartau": ("Am Bahnhof 1 Bad Schwartau", "schleswig_holstein", ["railway:station"], False),
    "Buetzow": ("Bützow Bahnhof", "mecklenburg", ["railway:station"], False),

    "Leeuwarden": ("Leeuwarden Station", "nl_north", ["railway:station"], False),
    "Meppel": ("Meppel Station", "nl_north", ["railway:station"], False),
    "Zwolle": ("Zwolle Station", "nl_north", ["railway:station"], False),
    "Almelo": ("Almelo Station", "nl_twente", ["railway:station"], False),
    "Hengelo": ("Hengelo Station", "nl_twente", ["railway:station"], False),
    "Bad Bentheim": ("Bad Bentheim Bahnhof", "nl_twente", ["railway:station"], False),
    "Rheine": ("Rheine Bahnhof", "muensterland", ["railway:station"], False),
    "Drensteinfurt": ("Drensteinfurt Bahnhof", "muensterland", ["railway:station"], False),
    "Unna": ("Unna Bahnhof", "ruhrgebiet", ["railway:station"], False),
    "Froendenberg": ("Fröndenberg Bahnhof", "ruhrtal_volme", ["railway:station"], False),
    "Wickede Ruhr": ("Wickede (Ruhr) Bahnhof", "sauerland", ["railway:station"], False),
    "Arnsberg Westf": ("Arnsberg (Westf) Bahnhof", "sauerland", ["railway:station"], False),
    "Bestwig": ("Bestwig Bahnhof", "sauerland", ["railway:station"], False),
    "Bigge": ("Bigge Bahnhof Olsberg", "sauerland", ["railway:station", "railway:halt"], False),
    "Steinhelle": ("Steinhelle Bahnhof", "sauerland", ["railway:station", "railway:halt"], False),
    "Siedlinghausen": ("Siedlinghausen Bahnhof", "sauerland", ["railway:station", "railway:halt"], False),
    "Silbach": ("Silbach Bahnhof", "sauerland", ["railway:station", "railway:halt"], False),
    "Winterberg Westf": ("Winterberg (Westf) Bahnhof", "sauerland", ["railway:station"], False),

    # --- RE39 Erfurt Hbf-Passau Hbf ---
    "Forchheim Oberfr": ("Forchheim (Oberfr) Bahnhof", "franconia", ["railway:station"], False),
    "Erlangen": ("Erlangen Bahnhof", "franconia", ["railway:station"], False),
    "Fuerth Bay Hbf": ("Fürth (Bay) Hauptbahnhof", "franconia", ["railway:station"], False),
    "Neumarkt Oberpf": ("Neumarkt (Oberpf) Bahnhof", "franconia", ["railway:station"], False),
    "Regensburg Hbf": ("Regensburg Hauptbahnhof", "bavaria_danube", ["railway:station"], False),
    "Straubing": ("Straubing Bahnhof", "bavaria_danube", ["railway:station"], False),
    "Plattling": ("Plattling Bahnhof", "bavaria_danube", ["railway:station"], False),
    "Vilshofen Niederbay": ("Vilshofen (Niederbay) Bahnhof", "bavaria_danube", ["railway:station"], False),
    "Passau Hbf": ("Passau Hauptbahnhof", "bavaria_danube", ["railway:station"], False),

    # --- RE57 Mulhouse-Ville-Passau Hbf ---
    "Mulhouse-Ville": ("Mulhouse-Ville", "alsace_baden", ["railway:station"], False),
    "Muellheim Baden": ("Müllheim (Baden) Bahnhof", "alsace_baden", ["railway:station"], False),
    "Bad Krozingen": ("Bad Krozingen Bahnhof", "alsace_baden", ["railway:station"], False),
    "Freiburg Breisgau Hbf": ("Freiburg (Breisgau) Hauptbahnhof", "alsace_baden", ["railway:station"], False),
    "Titisee": ("Titisee Bahnhof", "black_forest", ["railway:station"], False),
    "Neustadt Schwarzw": ("Neustadt (Schwarzwald) Bahnhof", "black_forest", ["railway:station"], False),
    "Donaueschingen": ("Donaueschingen Bahnhof", "black_forest", ["railway:station"], False),
    "Immendingen": ("Immendingen Bahnhof", "swabia_danube", ["railway:station"], False),
    "Tuttlingen": ("Tuttlingen Bahnhof", "swabia_danube", ["railway:station"], False),
    "Sigmaringen": ("Sigmaringen Bahnhof", "swabia_danube", ["railway:station"], False),
    "Kisslegg": ("Kißlegg Bahnhof", "allgaeu", ["railway:station"], False),
    "Buchloe": ("Buchloe Bahnhof", "allgaeu", ["railway:station"], False),
    "Kaufering": ("Kaufering Bahnhof", "allgaeu", ["railway:station"], False),
    "Muenchen-Pasing": ("München-Pasing Bahnhof", "munich", ["railway:station"], False),
    "Muenchen Ost": ("München Ost Bahnhof", "munich", ["railway:station"], False),
    "Muenchen Flughafen": ("München Flughafen Bahnhof", "munich", ["railway:station"], False),
    "Landshut Bay Hbf": ("Landshut (Bay) Hauptbahnhof", "lower_bavaria", ["railway:station"], False),
}


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def photon_query(text, bias_lat, bias_lon, osm_tag=None, limit=5):
    params = {
        "q": text,
        "lat": bias_lat,
        "lon": bias_lon,
        "zoom": 12,
        "limit": limit,
        "lang": "default",
    }
    if osm_tag:
        params["osm_tag"] = osm_tag
    url = PHOTON_URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            time.sleep(2 * (attempt + 1))
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return None


def geocode_station(key):
    query, region, tag_prefs, is_fictional = STATION_QUERIES[key]
    bias_lat, bias_lon = REGION[region]
    attempts = list(tag_prefs) + [None]  # zuletzt ohne Tag-Filter (freie Adress-/POI-Suche)
    for tag in attempts:
        data = photon_query(query, bias_lat, bias_lon, osm_tag=tag)
        if not data or not data.get("features"):
            continue
        # Naechstgelegenes Ergebnis zum Bias-Punkt waehlen (Photon sortiert primaer nach
        # Textrelevanz, wir brechen Gleichstaende ueber Distanz).
        best = None
        best_dist = None
        for feat in data["features"]:
            lon, lat = feat["geometry"]["coordinates"]
            dist = haversine_km(bias_lat, bias_lon, lat, lon)
            if dist > 200:  # zu weit weg vom erwarteten Land/Region -> verwerfen
                continue
            if best is None or dist < best_dist:
                best = feat
                best_dist = dist
        if best:
            props = best["properties"]
            lon, lat = best["geometry"]["coordinates"]
            return {
                "lat": lat,
                "lon": lon,
                "osm_tag": f"{props.get('osm_key')}:{props.get('osm_value')}",
                "matched_name": props.get("name"),
                "query_used": query,
                "tag_used": tag,
                "distance_km": round(best_dist, 1),
                "estimated": tag is None,  # kein railway-Tag getroffen -> Adress-/POI-Fallback
            }
    return None


def main():
    cache = load_cache()
    todo = [k for k in STATION_QUERIES if k not in cache]
    print(f"{len(cache)} bereits im Cache, {len(todo)} neu zu geocodieren")
    failures = []
    for i, key in enumerate(todo, 1):
        result = geocode_station(key)
        if result is None:
            failures.append(key)
            print(f"[{i}/{len(todo)}] FEHLER: {key} ({STATION_QUERIES[key][0]}) - kein Treffer")
        else:
            cache[key] = result
            flag = " [GESCHAETZT]" if result["estimated"] else ""
            print(f"[{i}/{len(todo)}] {key} -> {result['lat']:.4f},{result['lon']:.4f} "
                  f"({result['osm_tag']}, {result['distance_km']}km vom Anker){flag}")
        if i % 10 == 0:
            save_cache(cache)
        time.sleep(0.3)
    save_cache(cache)
    print(f"\nFertig. {len(failures)} ohne Treffer:")
    for f in failures:
        print(" -", f, STATION_QUERIES[f][0])


if __name__ == "__main__":
    main()
