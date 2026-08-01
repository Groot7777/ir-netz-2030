#!/usr/bin/env python3
"""One-off: add known-good real-world coordinates for major real cities across all
lines, to stop them being mis-geocoded via fuzzy Photon matches (short/common place
names like 'Turku' or 'Twer' were matching unrelated local businesses and poisoning
the anchor-chain for every subsequent stop on the same line)."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERRIDES_PATH = os.path.join(ROOT, "data", "overrides.json")

# key -> (lat, lon, note)
CITIES = {
    # arktis_afrika.json
    "Honningsvaag": (70.9821, 25.9704, "Honningsvåg (real Stadtzentrum)"),
    "Inari": (68.9061, 27.0276, "Inari (real Ortszentrum)"),
    "Rovaniemi": (66.5039, 25.7294, "Rovaniemi (real Bahnhof/Zentrum)"),
    "Oulu": (65.0121, 25.4651, "Oulu (real Zentrum)"),
    "Tampere": (61.4978, 23.7610, "Tampere (real Bahnhof)"),
    "Turku": (60.4518, 22.2666, "Turku (real Zentrum); Photon verwechselte 'Turku' mit dem Geschaeft 'Turkisliike' in Tampere"),
    "Helsinki": (60.1699, 24.9384, "Helsinki (real Zentrum)"),
    "Wyborg": (60.7097, 28.7519, "Wyborg/Vyborg (real Zentrum, deutscher Exonym beibehalten)"),
    "St Petersburg": (59.9311, 30.3609, "St. Petersburg (real Zentrum)"),
    "Twer": (56.8587, 35.9006, "Twer/Tver (real Zentrum, deutscher Exonym beibehalten); Photon fand faelschlich einen Pub 'Tower' in St. Petersburg"),
    "Moskau": (55.7558, 37.6173, "Moskau/Moskva (real Zentrum, deutscher Exonym beibehalten); Photon fand faelschlich ein Restaurant in St. Petersburg"),
    "Kyiv": (50.4501, 30.5234, "Kyiv (real Zentrum)"),
    "Odesa": (46.4825, 30.7233, "Odesa (real Zentrum); Photon fand faelschlich ein Restaurant in Kyiv"),
    "Istanbul": (41.0082, 28.9784, "Istanbul (real Zentrum); Photon fand faelschlich einen Deli in Kyiv"),
    "Athens": (37.9838, 23.7275, "Athens/Athen (real Zentrum); Photon fand faelschlich eine Ruine in der Tuerkei"),
    "Siracusa": (37.0755, 15.2866, "Siracusa (real Zentrum); Photon fand faelschlich einen Berg in der Tuerkei"),
    "Palermo": (38.1157, 13.3615, "Palermo (real Zentrum); Photon fand faelschlich ein Geschaeft in der Tuerkei"),
    "Tunis": (36.8065, 10.1815, "Tunis (real Zentrum); Photon fand faelschlich ein Geschaeft in der Tuerkei"),
    "Algiers": (36.7538, 3.0588, "Algiers/Alger (real Zentrum)"),
    "Casablanca": (33.5731, -7.5898, "Casablanca (real Zentrum); Photon fand faelschlich ein Hotel in Algier"),

    # brandenburg_hel.json
    "Brandenburg Hbf": (52.4090, 12.5453, "Brandenburg Hbf (real)"),
    "Potsdam Hbf": (52.3906, 13.0645, "Potsdam Hbf (real)"),
    "Berlin-Wannsee": (52.4229, 13.1789, "Berlin-Wannsee (real Bahnhof)"),
    "Berlin Hbf tief": (52.5250, 13.3694, "Berlin Hbf (real, Bezug fuer fiktive Tieflage)"),
    "Berlin Potsdamer Platz": (52.5096, 13.3759, "Berlin Potsdamer Platz (real)"),
    "Flughafen BER": (52.3667, 13.5033, "Flughafen BER (real)"),
    "Bernau b Berlin": (52.6797, 13.5892, "Bernau bei Berlin (real Zentrum)"),
    "Eberswalde Hbf": (52.8339, 13.8115, "Eberswalde Hbf (real)"),
    "Angermuende": (53.0219, 13.9967, "Angermünde (real Zentrum)"),
    "Pasewalk": (53.5039, 14.0000, "Pasewalk (real Zentrum)"),
    "Szczecin Glowny": (53.4257, 14.5518, "Szczecin Główny (real Bahnhof)"),
    "Szczecinek": (53.7061, 16.6994, "Szczecinek (real Zentrum)"),
    "Chojnice": (53.6966, 17.5578, "Chojnice (real Zentrum)"),
    "Starogard Gdanski": (53.9689, 18.5308, "Starogard Gdański (real Zentrum)"),
    "Tczew": (54.0924, 18.7997, "Tczew (real Bahnhof)"),
    "Gdansk Glowny": (54.3559, 18.6466, "Gdańsk Główny (real Bahnhof)"),
    "Gdansk Wrzeszcz": (54.3733, 18.6183, "Gdańsk Wrzeszcz (real Bahnhof)"),
    "Gdynia Glowna": (54.5189, 18.5314, "Gdynia Główna (real Bahnhof)"),
    "Rumia": (54.5719, 18.3900, "Rumia (real Zentrum)"),
    "Reda": (54.6011, 18.3486, "Reda (real Zentrum)"),
    "Puck": (54.7189, 18.4083, "Puck (real Zentrum)"),
    "Wladyslawowo": (54.7889, 18.4083, "Władysławowo (real Zentrum)"),
    "Jastarnia": (54.6978, 18.6844, "Jastarnia (real Zentrum, Halbinsel Hel)"),
    "Hel": (54.6083, 18.8014, "Hel (real Zentrum, Halbinselspitze)"),

    # weltachse1.json / rheinruhrkrim.json (Western/Central European real cities)
    "Bielefeld": (52.0302, 8.5325, "Bielefeld (real Zentrum)"),
    "Hannover Wuelferode Ost": (52.3667, 9.8500, "Hannover Ost/Wülferode (real, östlich der Stadt)"),
    "Poznan Wschod": (52.4064, 16.9772, "Poznań (real Zentrum, Bezug für östl. Autobahnknoten)"),
    "Lodz Polnoc": (51.8500, 19.4500, "Łódź Nord (real, nördlich der Stadt bei Stryków)"),
    "Warszawa Konotopa": (52.2100, 20.8700, "Warszawa Konotopa (real, westl. Autobahnknoten A2/S2)"),
    "Kyiv E40": (50.4501, 30.5234, "Kyiv (real Zentrum, westlicher Autobahnring E40)"),
    "Odessa": (46.4825, 30.7233, "Odessa/Odesa (real Zentrum)"),
    "Sevastopol": (44.6054, 33.5220, "Sevastopol/Sewastopol (real Zentrum)"),
    "Essen": (51.4556, 7.0116, "Essen Hbf (real)"),
    "Duisburg": (51.4344, 6.7623, "Duisburg Hbf (real)"),
    "Duesseldorf": (51.2277, 6.7735, "Düsseldorf Hbf (real)"),
    "Koeln": (50.9413, 6.9583, "Köln Hbf (real)"),
    "Koblenz": (50.3569, 7.5886, "Koblenz Hbf (real)"),
    "Frankfurt Flughafen": (50.0500, 8.5706, "Frankfurt Flughafen (real)"),
    "Mannheim": (49.4796, 8.4692, "Mannheim Hbf (real)"),
    "Stuttgart": (48.7842, 9.1817, "Stuttgart Hbf (real)"),
    "Ulm": (48.3984, 9.9825, "Ulm Hbf (real)"),
    "Augsburg": (48.3653, 10.8858, "Augsburg Hbf (real)"),
    "Muenchen": (48.1402, 11.5581, "München Hbf (real)"),
    "Rosenheim": (47.8506, 12.1183, "Rosenheim Hbf (real)"),
    "Salzburg": (47.8129, 13.0450, "Salzburg Hbf (real)"),
    "Linz": (48.2900, 14.2938, "Linz Hbf (real)"),
    "St Poelten": (48.2081, 15.6247, "St. Pölten Hbf (real)"),
    "Wien": (48.2082, 16.3738, "Wien (real Zentrum)"),
    "Bratislava": (48.1486, 17.1077, "Bratislava (real Zentrum)"),
    "Budapest": (47.4979, 19.0402, "Budapest (real Zentrum)"),
    "Kosice": (48.7164, 21.2611, "Košice (real Zentrum)"),
    "Lviv": (49.8397, 24.0297, "Lviv (real Zentrum)"),

    # ncams.json / nha.json / pcms.json / pnw_mae.json (shared North America hubs)
    "Surrey Vancouver": (49.1913, -122.8490, "Surrey/Vancouver (real Stadtgebiet, Bezug für Highway-1-Knoten)"),
    "Seattle Tukwila Hub": (47.4740, -122.2610, "Seattle/Tukwila (real, Kreuz I-5/I-405)"),
    "Portland Salmon Creek": (45.6987, -122.6650, "Portland/Salmon Creek (real, Kreuz I-5/I-205, Vancouver WA)"),
    "Spokane West Hub": (47.6588, -117.4260, "Spokane (real Stadtgebiet)"),
    "Billings North Bypass": (45.7833, -108.5007, "Billings (real Stadtgebiet)"),
    "Bismarck East Gate": (46.8083, -100.7837, "Bismarck (real Stadtgebiet)"),
    "Fargo West Hub": (46.8772, -96.8000, "Fargo (real Stadtgebiet, westl. Zufahrt)"),
    "Minneapolis Maple Grove": (45.0941, -93.4560, "Minneapolis/Maple Grove (real Vorort)"),
    "Milwaukee Oak Creek Hub": (42.8858, -87.8848, "Milwaukee/Oak Creek (real Vorort)"),
    "Chicago Joliet Mega-Hub": (41.5250, -88.0817, "Chicago/Joliet (real Stadtgebiet)"),
    "Indianapolis South Hub": (39.6500, -86.1500, "Indianapolis (real, südl. Autobahnring)"),
    "Columbus West Hub": (39.9700, -83.1300, "Columbus (real, westl. Autobahnring)"),
    "Pittsburgh Monroeville": (40.4302, -79.7889, "Pittsburgh/Monroeville (real Vorort)"),
    "Washington Greenbelt": (39.0000, -76.8800, "Washington/Greenbelt (real Vorort)"),
    "Baltimore White Marsh": (39.3900, -76.4500, "Baltimore/White Marsh (real Vorort)"),
    "Philadelphia Northeast": (40.0800, -75.0100, "Philadelphia Northeast (real Stadtteil)"),
    "NYC Penn Deep": (40.7506, -73.9935, "New York Penn Station (real)"),
    "Hartford North Hub": (41.7900, -72.6900, "Hartford (real, nördl. Stadtgebiet)"),
    "Boston West Route 128": (42.3600, -71.2900, "Boston/Weston (real, Kreuz I-90/I-95 Route 128)"),
    "Portland West Hub Maine": (43.6800, -70.3500, "Portland Maine (real, westl. Stadtgebiet)"),
    "Bangor Hermon Hub": (44.8100, -68.9200, "Bangor/Hermon (real Vorort)"),
    "St Stephen Border Gate": (45.1970, -67.2830, "St. Stephen NB (real, Grenzstadt)"),
    "Saint John Bypass": (45.3000, -66.0800, "Saint John NB (real Stadtgebiet)"),
    "Moncton Maritime Hub": (46.0878, -64.7782, "Moncton (real Stadtgebiet)"),
    "Halifax Dartmouth": (44.6820, -63.5750, "Halifax/Dartmouth (real Stadtgebiet)"),
    "Las Vegas South Gateway": (36.0397, -115.1550, "Las Vegas South (real, Kreuz I-15/CC-215)"),
    "Albuquerque West Bypass": (35.1056, -106.7100, "Albuquerque (real, westl. Peripherie I-40/Coors Blvd)"),
    "Denver Northeast Hub": (39.8600, -104.7400, "Denver Northeast (real, nahe DIA)"),
    "Omaha West Gateway": (41.1400, -96.2400, "Omaha West/Gretna (real Vorort)"),
    "Des Moines West Hub": (41.6100, -93.8900, "Des Moines West/Waukee (real Vorort)"),
    "Detroit Romulus Hub": (42.2280, -83.3760, "Detroit/Romulus (real, Flughafenumfeld)"),
    "Niagara Falls North Hub": (43.1200, -79.0400, "Niagara Falls NY (real, US-Seite)"),
    "Rochester South Hub": (43.0700, -77.6200, "Rochester/Henrietta (real Vorort)"),
    "Albany West Hub": (42.6800, -73.9500, "Albany West/Guilderland (real Vorort)"),
    "Oklahoma City West Gate": (35.5100, -97.6800, "Oklahoma City West (real Stadtgebiet)"),
    "Conway North": (35.1000, -92.4600, "Conway AR North (real Vorort)"),
    "West Memphis Hub": (35.1465, -90.1848, "West Memphis AR (real Stadtgebiet)"),
    "Nashville Briley East": (36.1900, -86.6600, "Nashville/Briley Parkway East (real)"),
    "Pigeon Mountain": (35.7700, -83.5600, "Sevierville/Pigeon Forge (real Gebiet)"),
    "Charlotte NE Loop": (35.3200, -80.7300, "Charlotte NE (real, I-85/I-485)"),
    "Richmond North Gate": (37.6600, -77.4800, "Richmond North/Glen Allen (real Vorort)"),
    "West Ocean City": (38.3400, -75.1300, "West Ocean City MD (real)"),
    "Atlantic City Egg Harbor": (39.3800, -74.5900, "Egg Harbor Township NJ (real)"),
}


def main():
    with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
        overrides = json.load(f)
    added, skipped = 0, 0
    for key, (lat, lon, note) in CITIES.items():
        if key in overrides:
            skipped += 1
            continue
        overrides[key] = {"lat": lat, "lon": lon, "note": note}
        added += 1
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"added={added} skipped={skipped} total={len(overrides)}")


if __name__ == "__main__":
    main()
