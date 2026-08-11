# Bahnsteiglängen-Konfliktliste

Vergleich der aus Wagenzahl/Kupplung errechneten Zuglänge gegen reale Bahnsteiglängen (OpenStreetMap/Overpass). SDO-Toleranz: 25 m — Überhang bis dahin gilt als unkritisch (Selective Door Opening bzw. bereits eingeplante Bahnsteigverlängerung), erst darüber als echter Prüffall.

- **59 kritisch, hohe Konfidenz** (Überhang > 25 m, ≥3 unabhängige OSM-Treffer)
- **65 kritisch, niedrige Konfidenz** (<3 Treffer — häufig OSM-Lücke statt echtes Problem)
- **36 gering** (SDO ausreichend)
- **234 unauffällig**
- **80 ohne Bahnsteigdaten** (OSM-Lücke, manuell zu prüfen)

> **Wichtiger Befund zur Datenqualität:** Stichproben an großen Umsteigeknoten (Köln Hbf, Düsseldorf Hbf, Dresden Hbf, Erfurt Hbf, Mainz Hbf) zeigen, dass OSM dort die realen Fernbahnsteige teils **gar nicht** als `railway=platform` erfasst — gefunden werden dann nur vereinzelte, unpassende Objekte in der Nähe (z.B. Straßenbahn-Haltestellen), was eine absurd kurze Länge liefert. Ausgerechnet an den wichtigsten Knoten ist die OSM-Abdeckung also am unzuverlässigsten. Die **niedrige Konfidenz** (<3 unabhängige Treffer) markiert genau dieses Muster. **Nur die hoch-konfidenten Kritisch-Einträge sind ein ernstzunehmender Anfangsverdacht** — die niedrig-konfidenten sind mit hoher Wahrscheinlichkeit OSM-Lücken, keine echten Bahnsteigprobleme. Vor jeder Maßnahme in jedem Fall gegen DB InfraGO-Daten (deutsche Stationen) bzw. Ortskenntnis gegenprüfen.

## Kritisch — hohe Konfidenz

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |
|---|---|---|---|---|---|---|
| Elmshorn | RE90b | 3+6 | 236 m | 24 m | **+212 m** | 4 |
| Sargans | RE80 | 8 | 210 m | 20 m | **+190 m** | 9 |
| Neustadt (Dosse) | RE46 | 4+4 | 210 m | 30 m | **+180 m** | 3 |
| Gdynia Główna | RE71 | 8 | 210 m | 32 m | **+178 m** | 7 |
| Freiberg (Sachs) | RE35X | 8 | 210 m | 36 m | **+174 m** | 7 |
| Brandenburg Hbf | RE71 | 8 | 210 m | 40 m | **+170 m** | 9 |
| Würzburg Hbf | RE28 | 8 | 210 m | 42 m | **+168 m** | 4 |
| Düsseldorf-Benrath | RE5 | 8 | 210 m | 61 m | **+149 m** | 4 |
| Erfurt Hbf | RE28 | 8 | 210 m | 67 m | **+143 m** | 11 |
| Kiel Hbf | RE90b | 3+6 | 236 m | 100 m | **+136 m** | 9 |
| Dinslaken | RE5 | 8 | 210 m | 74 m | **+136 m** | 4 |
| Lübeck Hbf | RE17 | 8 | 210 m | 78 m | **+132 m** | 3 |
| Berlin-Ostkreuz | RE11 | 7 | 184 m | 52 m | **+132 m** | 4 |
| Leipzig Hbf (oben) | RE28 | 8 | 210 m | 81 m | **+129 m** | 6 |
| Mainz Hbf | RE5 | 8 | 210 m | 83 m | **+127 m** | 10 |
| Neuss Hbf | RE32 | 8 | 210 m | 83 m | **+127 m** | 3 |
| Mülheim-Styrum | S10 Außenring | 6 | 156 m | 31 m | **+125 m** | 4 |
| Bochum-Kohlenstraße | S10 Außenring | 6 | 156 m | 34 m | **+122 m** | 4 |
| Bochum-Langendreer | S10 Außenring | 6 | 156 m | 35 m | **+121 m** | 5 |
| Mannheim Hbf | RE80 | 8 | 210 m | 89 m | **+121 m** | 18 |
| Potsdam Hbf | RE71 | 8 | 210 m | 91 m | **+119 m** | 10 |
| Kassel-Wilhelmshöhe | RE32 | 8 | 210 m | 94 m | **+116 m** | 13 |
| Fürth (Bay) Hbf | RE39 | 8 | 210 m | 94 m | **+116 m** | 4 |
| Chemnitz Hbf | RE35X | 8 | 210 m | 94 m | **+116 m** | 10 |
| Mülheim West | S10 Außenring | 6 | 156 m | 47 m | **+109 m** | 3 |
| Dresden-Neustadt | RE35X | 8 | 210 m | 101 m | **+109 m** | 13 |
| Zürich HB | RE94 | 7 | 184 m | 76 m | **+108 m** | 25 |
| Luxembourg | RE90 | 6 | 156 m | 54 m | **+102 m** | 4 |
| Essen-Höntrop | S10 Außenring | 6 | 156 m | 55 m | **+101 m** | 4 |
| Schwerin Hbf | RE91 | 3+3 | 160 m | 63 m | **+97 m** | 7 |
| Essen-Horst | S30 | 6 | 156 m | 60 m | **+96 m** | 5 |
| Bochum Hbf | RE32 | 8 | 210 m | 118 m | **+92 m** | 6 |
| Wanne-Eickel Hbf | S10 Außenring | 6 | 156 m | 68 m | **+88 m** | 10 |
| Witten Hbf | S10 Außenring | 6 | 156 m | 83 m | **+73 m** | 8 |
| Wuppertal-Vohwinkel | RB37 | 4 | 105 m | 36 m | **+69 m** | 4 |
| Duisburg Hbf | RE32 | 8 | 210 m | 141 m | **+69 m** | 5 |
| Wetter (Ruhr) | RE40 | 5 | 130 m | 62 m | **+68 m** | 10 |
| Düsseldorf Hbf | RE32 | 8 | 210 m | 146 m | **+64 m** | 19 |
| Berlin Alexanderplatz | RE11 | 7 | 184 m | 121 m | **+63 m** | 16 |
| Essen-Altenessen | S10 Außenring | 6 | 156 m | 94 m | **+62 m** | 3 |
| Trier Hbf | RE14 | 5 | 130 m | 70 m | **+60 m** | 5 |
| Wuppertal Hbf | RB37 | 4 | 105 m | 45 m | **+60 m** | 4 |
| Sigmaringen | RE57 | 6 | 156 m | 96 m | **+60 m** | 6 |
| Wuppertal-Oberbarmen | RB37 | 4 | 105 m | 47 m | **+58 m** | 8 |
| Halle (Saale) Hbf | RE28 | 8 | 210 m | 152 m | **+58 m** | 12 |
| Gdynia Wzgórze Św. Maksymiliana | RE71 | 8 | 210 m | 155 m | **+55 m** | 5 |
| Berlin Zoologischer Garten | RE11 | 7 | 184 m | 129 m | **+55 m** | 4 |
| Berlin Friedrichstraße | RE11 | 7 | 184 m | 130 m | **+54 m** | 9 |
| München Flughafen | RE57 | 6 | 156 m | 105 m | **+51 m** | 4 |
| Braunschweig Hbf | RE25 | 5 | 130 m | 80 m | **+50 m** | 8 |
| Dresden Hbf | RE35X | 8 | 210 m | 160 m | **+50 m** | 11 |
| Erkner | RE11 | 7 | 184 m | 135 m | **+49 m** | 6 |
| Chojnice | RE71 | 8 | 210 m | 164 m | **+46 m** | 10 |
| Rummenohl | S30 | 6 | 156 m | 110 m | **+46 m** | 3 |
| Gelsenkirchen Hbf | RE2 | 6 | 156 m | 115 m | **+41 m** | 3 |
| München Ost | RE57 | 6 | 156 m | 118 m | **+38 m** | 3 |
| Dortmund-Wickede | S10 Außenring | 6 | 156 m | 120 m | **+36 m** | 4 |
| Essen-Dellwig Ost | S10 Außenring | 6 | 156 m | 127 m | **+29 m** | 6 |
| Cloppenburg | RE17 | 6 | 156 m | 131 m | **+25 m** | 3 |

## Kritisch — niedrige Konfidenz (vermutlich OSM-Lücke, 65 Fälle)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |
|---|---|---|---|---|---|---|
| Boppard Hbf | RE5 | 8 | 210 m | 18 m | +192 m | 1 |
| Roermond (NL) | RE32 | 8 | 210 m | 22 m | +188 m | 1 |
| Berlin Hbf (tief) | RE35X | 8 | 210 m | 46 m | +164 m | 2 |
| Passau Hbf | RE39 | 8 | 210 m | 49 m | +161 m | 1 |
| Nienburg (Weser) | RE7 | 8 | 210 m | 51 m | +159 m | 1 |
| Köln Hbf | RE5 | 8 | 210 m | 54 m | +156 m | 1 |
| Ravensburg | RE94 | 7 | 184 m | 33 m | +151 m | 2 |
| Oberhausen Hbf | RE5 | 8 | 210 m | 60 m | +150 m | 2 |
| Greifswald | RE35X | 8 | 210 m | 61 m | +149 m | 1 |
| Gelnhausen | RE7 | 8 | 210 m | 62 m | +148 m | 1 |
| Oldenburg (Holst) | RE17 | 8 | 210 m | 68 m | +142 m | 1 |
| Essen-Steele Ost | S10 Außenring | 6 | 156 m | 15 m | +141 m | 1 |
| Leipzig Hbf | RE11 | 7 | 184 m | 46 m | +138 m | 2 |
| Frankfurt (Oder) | RE11 | 7 | 184 m | 47 m | +137 m | 2 |
| Herford | RE17 | 6 | 156 m | 21 m | +135 m | 1 |
| Dahl | S30 | 6 | 156 m | 22 m | +134 m | 1 |
| Flöha | RE35 | 6 | 156 m | 31 m | +125 m | 1 |
| Grevenbroich | RE14 | 5 | 130 m | 15 m | +115 m | 1 |
| Landshut (Bay) Hbf | RE57 | 6 | 156 m | 44 m | +112 m | 1 |
| Wengern | S10 Außenring | 6 | 156 m | 44 m | +112 m | 1 |
| Bebra | RE24 | 5 | 130 m | 20 m | +110 m | 2 |
| Rövershagen | RE91 | 3+3 | 160 m | 53 m | +107 m | 1 |
| Hamburg-Elbbrücken | RE90b | 3+6 | 236 m | 131 m | +105 m | 2 |
| Leipzig MDR | RE24 | 5 | 130 m | 27 m | +103 m | 1 |
| Landquart | RE80 | 8 | 210 m | 107 m | +103 m | 1 |
| Marktredwitz | RE94 | 7 | 184 m | 89 m | +95 m | 1 |
| Berlin-Spandau | RE46 | 4+4 | 210 m | 120 m | +90 m | 2 |
| Göttingen | RE7 | 8 | 210 m | 122 m | +88 m | 2 |
| Bad Bentheim | RE30 | 4+4 | 210 m | 123 m | +87 m | 1 |
| Władysławowo Port | RE71 | 8 | 210 m | 124 m | +86 m | 1 |
| Schwelm | RB37 | 4 | 105 m | 19 m | +86 m | 1 |
| Wegberg | RE32 | 8 | 210 m | 124 m | +86 m | 1 |
| Żelistrzewo | RE71 | 8 | 210 m | 125 m | +85 m | 1 |
| Mrzezino | RE71 | 8 | 210 m | 125 m | +85 m | 1 |
| Dalheim | RE32 | 8 | 210 m | 125 m | +85 m | 1 |
| Berlin Hbf | RE46 | 4+4 | 210 m | 126 m | +84 m | 1 |
| Swarzewo | RE71 | 8 | 210 m | 126 m | +84 m | 1 |
| Herbede | S30 | 6 | 156 m | 74 m | +82 m | 1 |
| Buxtehude | RE91 | 3+3 | 160 m | 80 m | +80 m | 1 |
| Lübben (Spreewald) | RE45 | 6 | 156 m | 76 m | +80 m | 1 |
| Münster (Westf) Hbf | RE30 | 4+4 | 210 m | 131 m | +79 m | 2 |
| Starogard Gdański | RE71 | 8 | 210 m | 133 m | +77 m | 2 |
| Stuttgart Flughafen | RE80 | 8 | 210 m | 134 m | +76 m | 1 |
| Berlin Gesundbrunnen | RE35X | 8 | 210 m | 134 m | +76 m | 1 |
| Ruine Hardenstein | S30 | 6 | 156 m | 82 m | +74 m | 1 |
| Bamberg | RE28 | 8 | 210 m | 136 m | +74 m | 1 |
| Haiger | RE40 | 5 | 130 m | 58 m | +72 m | 1 |
| Homburg (Saar) Hbf | RE80 | 8 | 210 m | 138 m | +72 m | 1 |
| Hofgeismar | RE32 | 8 | 210 m | 141 m | +69 m | 2 |
| Schwerte (Ruhr) | RE30 | 4+4 | 210 m | 141 m | +69 m | 2 |
| Hamburg Dammtor | RE77 | 6 | 156 m | 90 m | +66 m | 1 |
| Bochum-Riemke | S10 Außenring | 6 | 156 m | 91 m | +65 m | 2 |
| Memmingen | RE80 | 8 | 210 m | 145 m | +65 m | 1 |
| Köln Süd | RE14 | 5 | 130 m | 66 m | +64 m | 2 |
| Stade | RE25 | 5 | 130 m | 66 m | +64 m | 2 |
| Ingolstadt Hbf | RE94 | 7 | 184 m | 125 m | +59 m | 1 |
| Fulda | RE7 | 8 | 210 m | 156 m | +54 m | 2 |
| Potsdamer Platz | RE45 | 6 | 156 m | 105 m | +51 m | 2 |
| Dahlerbrück | S30 | 6 | 156 m | 110 m | +46 m | 1 |
| Berlin-Charlottenburg | RE11 | 7 | 184 m | 142 m | +42 m | 1 |
| Bremerhaven-Lehe | RE9 | 8 | 210 m | 171 m | +39 m | 1 |
| Unna West | S10 Außenring | 6 | 156 m | 120 m | +36 m | 1 |
| Massen | S10 Außenring | 6 | 156 m | 120 m | +36 m | 2 |
| Schalksmühle | S30 | 6 | 156 m | 122 m | +34 m | 1 |
| Bochum-Bermuda3eck | S10 Außenring | 6 | 156 m | 128 m | +28 m | 1 |

## Gering (SDO/geplante Verlängerung ausreichend, ≤25 m)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Konfidenz |
|---|---|---|---|---|---|---|
| Drensteinfurt | RE30 | 4+4 | 210 m | 185 m | +25 m | niedrig |
| Hamburg-Harburg | RE90b | 3+6 | 236 m | 212 m | +24 m | niedrig |
| Zevenaar | RE5 | 8 | 210 m | 186 m | +24 m | hoch |
| Essen (Oldb) | RE17 | 6 | 156 m | 132 m | +24 m | niedrig |
| Bramsche | RE17 | 6 | 156 m | 132 m | +24 m | niedrig |
| Schweinfurt Hbf | RE28 | 8 | 210 m | 187 m | +23 m | hoch |
| Freital Hbf | RE35 | 6 | 156 m | 135 m | +21 m | hoch |
| Hagen-Vorhalle | S10 Außenring | 6 | 156 m | 137 m | +19 m | hoch |
| Hengelo | RE30 | 4+4 | 210 m | 191 m | +19 m | hoch |
| Bonn Hbf | RE5 | 8 | 210 m | 193 m | +17 m | hoch |
| Rotenburg (Wümme) | RE90b | 3+6 | 236 m | 220 m | +16 m | hoch |
| Bochum-Hamme | S10 Außenring | 6 | 156 m | 140 m | +16 m | hoch |
| Allersberg (Rothsee) | RE94 | 7 | 184 m | 169 m | +15 m | hoch |
| Konstanz | RE94 | 7 | 184 m | 173 m | +11 m | niedrig |
| Hagen Hbf | S30 | 6 | 156 m | 145 m | +11 m | hoch |
| Bochum West | S10 Außenring | 6 | 156 m | 146 m | +10 m | hoch |
| Dortmund Hbf | RE32 | 8 | 210 m | 200 m | +10 m | hoch |
| Hattingen Mitte | S3 | 6 | 156 m | 148 m | +8 m | hoch |
| Magdeburg Hbf | RE25 | 5 | 130 m | 122 m | +8 m | hoch |
| København H | RE17 | 8 | 210 m | 203 m | +7 m | hoch |
| Holzwickede | RE30 | 4+4 | 210 m | 203 m | +7 m | hoch |
| Essen West | S10 Außenring | 6 | 156 m | 149 m | +7 m | niedrig |
| Zeche Nachtigall | S30 | 6 | 156 m | 150 m | +6 m | hoch |
| Haus Kemnade | S30 | 6 | 156 m | 150 m | +6 m | niedrig |
| Regensburg Hbf | RE39 | 8 | 210 m | 205 m | +5 m | niedrig |
| Hannover Hbf | RE7 | 8 | 210 m | 205 m | +5 m | hoch |
| Kreuztal | RE40 | 5 | 130 m | 125 m | +5 m | niedrig |
| Heinrichshütte | S30 | 6 | 156 m | 152 m | +4 m | hoch |
| Gdańsk Zaspa | RE71 | 8 | 210 m | 206 m | +4 m | hoch |
| Kaiserslautern Hbf | RE80 | 8 | 210 m | 206 m | +4 m | hoch |
| Zossen | RE35 | 6 | 156 m | 153 m | +3 m | niedrig |
| Blankenstein Burg | S30 | 6 | 156 m | 153 m | +3 m | niedrig |
| Tønder | RE46 | 4 | 105 m | 102 m | +3 m | niedrig |
| Bochum-Dahlhausen | S30 | 6 | 156 m | 155 m | +1 m | hoch |
| Offenbach (Main) Hbf | RE7 | 8 | 210 m | 210 m | +0 m | niedrig |
| Forchheim (Oberfr) | RE39 | 8 | 210 m | 210 m | +0 m | niedrig |

## Ohne Bahnsteigdaten

| Station | Linie | Wagen | benötigt |
|---|---|---|---|
| Neumünster | RE90b | 3+6 | 236 m |
| Bad Kleinen | RE17 | 8 | 210 m |
| Großenbrode/Heiligenhafen | RE17 | 8 | 210 m |
| Nykøbing F. | RE17 | 8 | 210 m |
| Ringsted | RE17 | 8 | 210 m |
| Nørreport | RE17 | 8 | 210 m |
| Zwickau Hbf | RE35X | 8 | 210 m |
| Recklinghausen Hbf | RE9 | 8 | 210 m |
| Unna | RE30 | 4+4 | 210 m |
| Düsseldorf Flughafen Bf | RE32 | 8 | 210 m |
| Wattenscheid Bf | RE32 | 8 | 210 m |
| Soest Bf | RE32 | 8 | 210 m |
| Warburg (Westf) | RE32 | 8 | 210 m |
| Pasewalk | RE35X | 8 | 210 m |
| Eberswalde Hbf | RE35X | 8 | 210 m |
| Berlin Südkreuz | RE35X | 8 | 210 m |
| Angermünde | RE71 | 8 | 210 m |
| Bernau (b Berlin) | RE71 | 8 | 210 m |
| Vilshofen (Niederbay) | RE39 | 8 | 210 m |
| Plattling | RE39 | 8 | 210 m |
| Straubing | RE39 | 8 | 210 m |
| Neumarkt (Oberpf) | RE39 | 8 | 210 m |
| Erlangen | RE39 | 8 | 210 m |
| Flughafen BER | RE71 | 8 | 210 m |
| Hagenow Land | RE46 | 4+4 | 210 m |
| Berlin Potsdamer Platz | RE46 | 4+4 | 210 m |
| Wesel | RE5 | 8 | 210 m |
| Brühl | RE5 | 8 | 210 m |
| Koblenz Hbf | RE5 | 8 | 210 m |
| Bingen (Rhein) Hbf | RE5 | 8 | 210 m |
| Ingelheim | RE5 | 8 | 210 m |
| Frankfurt Flughafen Regiobf | RE5 | 8 | 210 m |
| Hanau Hbf | RE7 | 8 | 210 m |
| Hannover-Messe/Laatzen | RE7 | 8 | 210 m |
| Verden (Aller) | RE7 | 8 | 210 m |
| Buchs SG | RE80 | 8 | 210 m |
| Feldkirch | RE80 | 8 | 210 m |
| Dornbirn | RE80 | 8 | 210 m |
| Bregenz | RE80 | 8 | 210 m |
| Neunkirchen (Saar) Hbf | RE80 | 8 | 210 m |
| Fürstenwalde (Spree) | RE11 | 7 | 184 m |
| Berlin Ostbahnhof | RE11 | 7 | 184 m |
| Ludwigsfelde | RE11 | 7 | 184 m |
| Jüterbog | RE11 | 7 | 184 m |
| Pegnitz | RE94 | 7 | 184 m |
| Bremerhaven Hbf | RE91 | 3+3 | 160 m |
| Bergen auf Rügen | RE91 | 3+3 | 160 m |
| Bünde (Westf) | RE17 | 6 | 156 m |
| Varel (Oldb) | RE17 | 6 | 156 m |
| Prenzlau | RE35 | 6 | 156 m |
| Glauchau (Sachs) | RE35 | 6 | 156 m |
| Stendal Hbf | RE45 | 6 | 156 m |
| Salzwedel | RE45 | 6 | 156 m |
| Fredericia | RE77 | 6 | 156 m |
| Padborg | RE77 | 6 | 156 m |
| Flensburg | RE77 | 6 | 156 m |
| Bettembourg | RE90 | 6 | 156 m |
| Ettelbruck | RE90 | 6 | 156 m |
| Bochum-Stahlhausen | S10 Außenring | 6 | 156 m |
| Dortmund-Kley | S10 Außenring | 6 | 156 m |
| Dortmund-Oespel | S10 Außenring | 6 | 156 m |
| Dortmund-Brackel | S10 Außenring | 6 | 156 m |
| Lüdenscheid Hbf | S30 | 6 | 156 m |
| Witten Bommern | S30 | 6 | 156 m |
| Viersen | RE14 | 5 | 130 m |
| Rommerskirchen | RE14 | 5 | 130 m |
| Völklingen | RE14 | 5 | 130 m |
| Gößnitz | RE24 | 5 | 130 m |
| Altenburg | RE24 | 5 | 130 m |
| Böhlen (b Leipzig) | RE24 | 5 | 130 m |
| Leipzig Hbf (tief) | RE24 | 5 | 130 m |
| Eisenach | RE24 | 5 | 130 m |
| Friedberg (Hess) | RE40 | 5 | 130 m |
| Dillenburg | RE40 | 5 | 130 m |
| Siegen Hbf | RE40 | 5 | 130 m |
| Altena (Westf) | RE40 | 5 | 130 m |
| Letmathe | RE40 | 5 | 130 m |
| Steinhelle | RE30 | 4 | 105 m |
| Schönkirchen | RE90b | 3 | 80 m |
| Probsteierhagen | RE90b | 3 | 80 m |
