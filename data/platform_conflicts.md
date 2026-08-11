# Bahnsteiglängen-Konfliktliste

Vergleich der aus Wagenzahl/Kupplung errechneten Zuglänge gegen reale Bahnsteiglängen (DB InfraGO-Nettobaulänge wo vorhanden, sonst OpenStreetMap/Overpass). SDO-Toleranz: 25 m — Überhang bis dahin gilt als unkritisch (Selective Door Opening bzw. bereits eingeplante Bahnsteig-verlängerung), erst darüber als echter Prüffall.

- **0 kritisch, fiktive Planung** (RE-Netz-2030-eigener Ausbau, siehe data/manual_overrides.json)
- **15 kritisch, amtliche Daten** (DB InfraGO — ernstzunehmender Befund)
- **11 kritisch, hohe OSM-Konfidenz** (≥3 unabhängige OSM-Treffer, ungeprüft)
- **11 kritisch, niedrige OSM-Konfidenz** (<3 Treffer — meist OSM-Lücke statt echtes Problem)
- **28 gering** (SDO ausreichend)
- **392 unauffällig**
- **17 ohne Bahnsteigdaten** (manuell zu prüfen)

> **Befund zur Datenqualität:** Für 345 deutsche Stationen liegt jetzt die amtliche DB InfraGO-Nettobaulänge vor (tools/dbinfrago_platforms.py, gleisscharf in data/dbinfrago_platforms.json), für 128 weitere (v.a. die 101 ausländischen Stationen sowie einzelne kleine deutsche Halte ohne dbinfrago-Eintrag) nur die unsichere OSM-Schätzung. Mit amtlichen Daten bleiben **nur noch 15 echte Kritisch-Fälle** übrig — überwiegend kleine S-Bahn-Halte (S10-Ring, S30), deren Bahnsteige nie für 6-teilige Züge gebaut wurden. Das ist jetzt eher eine Entscheidung über Zuglänge/Kurzzug-Einsatz an diesen Halten als ein Datenproblem. Für Stationen ohne amtliche Bestätigung gilt weiterhin: OSM-Konfidenz 'niedrig' ist meist eine Datenlücke, kein echtes Bahnsteigproblem — auch 'hohe' OSM-Konfidenz war in Stichproben nicht durchgehend verlässlich (z.B. Mainz Hbf: 10 OSM-Treffer, dennoch nur 83 statt amtlich 210+ m). Vor jeder Maßnahme ohne amtliche Bestätigung gegenprüfen.

## Kritisch — fiktive RE-Netz-2030-Planung

Keine.

## Kritisch — amtliche DB-InfraGO-Daten

| Station | Linie | Wagen | benötigt | verfügbar | Überhang |
|---|---|---|---|---|---|
| Dahl | S30 | 6 | 156 m | 52 m | **+104 m** |
| Dalheim | RE32 | 8 | 210 m | 125 m | **+85 m** |
| Wegberg | RE32 | 8 | 210 m | 125 m | **+85 m** |
| Neustadt (Dosse) | RE46 | 4+4 | 210 m | 140 m | **+70 m** |
| Bochum-Riemke | S10 Außenring | 6 | 156 m | 90 m | **+66 m** |
| Bochum-Stahlhausen | S10 Außenring | 6 | 156 m | 110 m | **+46 m** |
| Schalksmühle | S30 | 6 | 156 m | 110 m | **+46 m** |
| Dahlerbrück | S30 | 6 | 156 m | 110 m | **+46 m** |
| Rummenohl | S30 | 6 | 156 m | 110 m | **+46 m** |
| Bremerhaven-Lehe | RE9 | 8 | 210 m | 170 m | **+40 m** |
| Unna West | S10 Außenring | 6 | 156 m | 119 m | **+37 m** |
| Hattingen (Ruhr) | S30 | 6 | 156 m | 120 m | **+36 m** |
| Essen-Horst | S30 | 6 | 156 m | 120 m | **+36 m** |
| Massen | S10 Außenring | 6 | 156 m | 121 m | **+35 m** |
| Essen-Dellwig Ost | S10 Außenring | 6 | 156 m | 124 m | **+32 m** |

## Kritisch — hohe OSM-Konfidenz (ungeprüft)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |
|---|---|---|---|---|---|---|
| Sargans | RE80 | 8 | 210 m | 20 m | +190 m | 9 |
| Gdynia Główna | RE71 | 8 | 210 m | 32 m | +178 m | 7 |
| Mülheim-Styrum | S10 Außenring | 6 | 156 m | 31 m | +125 m | 4 |
| Bochum-Kohlenstraße | S10 Außenring | 6 | 156 m | 34 m | +122 m | 4 |
| Mülheim West | S10 Außenring | 6 | 156 m | 47 m | +109 m | 3 |
| Zürich HB | RE94 | 7 | 184 m | 76 m | +108 m | 25 |
| Luxembourg | RE90 | 6 | 156 m | 54 m | +102 m | 4 |
| Essen-Höntrop | S10 Außenring | 6 | 156 m | 55 m | +101 m | 4 |
| Gdynia Wzgórze Św. Maksymiliana | RE71 | 8 | 210 m | 155 m | +55 m | 5 |
| München Flughafen | RE57 | 6 | 156 m | 105 m | +51 m | 4 |
| Chojnice | RE71 | 8 | 210 m | 164 m | +46 m | 10 |

## Kritisch — niedrige OSM-Konfidenz (vermutlich OSM-Lücke, 11 Fälle)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |
|---|---|---|---|---|---|---|
| Roermond (NL) | RE32 | 8 | 210 m | 22 m | +188 m | 1 |
| Wengern | S10 Außenring | 6 | 156 m | 44 m | +112 m | 1 |
| Landquart | RE80 | 8 | 210 m | 107 m | +103 m | 1 |
| Władysławowo Port | RE71 | 8 | 210 m | 124 m | +86 m | 1 |
| Żelistrzewo | RE71 | 8 | 210 m | 125 m | +85 m | 1 |
| Mrzezino | RE71 | 8 | 210 m | 125 m | +85 m | 1 |
| Swarzewo | RE71 | 8 | 210 m | 126 m | +84 m | 1 |
| Herbede | S30 | 6 | 156 m | 74 m | +82 m | 1 |
| Starogard Gdański | RE71 | 8 | 210 m | 133 m | +77 m | 2 |
| Ruine Hardenstein | S30 | 6 | 156 m | 82 m | +74 m | 1 |
| Bochum-Bermuda3eck | S10 Außenring | 6 | 156 m | 128 m | +28 m | 1 |

## Gering (SDO/geplante Verlängerung ausreichend, ≤25 m)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Konfidenz |
|---|---|---|---|---|---|---|
| Drensteinfurt | RE30 | 4+4 | 210 m | 185 m | +25 m | amtlich |
| Bramsche | RE17 | 6 | 156 m | 131 m | +25 m | amtlich |
| Essen (Oldb) | RE17 | 6 | 156 m | 131 m | +25 m | amtlich |
| Cloppenburg | RE17 | 6 | 156 m | 131 m | +25 m | amtlich |
| Lüdenscheid Hbf | S30 | 6 | 156 m | 131 m | +25 m | amtlich |
| Zevenaar | RE5 | 8 | 210 m | 186 m | +24 m | hoch |
| Freital Hbf | RE35 | 6 | 156 m | 135 m | +21 m | hoch |
| Landstuhl | RE80 | 8 | 210 m | 190 m | +20 m | amtlich |
| Rövershagen | RE91 | 3+3 | 160 m | 140 m | +20 m | amtlich |
| Hengelo | RE30 | 4+4 | 210 m | 191 m | +19 m | hoch |
| Rotenburg (Wümme) | RE90b | 3+6 | 236 m | 220 m | +16 m | amtlich |
| Hagen-Vorhalle | S10 Außenring | 6 | 156 m | 140 m | +16 m | amtlich |
| Bochum-Hamme | S10 Außenring | 6 | 156 m | 140 m | +16 m | amtlich |
| Allersberg (Rothsee) | RE94 | 7 | 184 m | 170 m | +14 m | amtlich |
| Essen-Borbeck | S10 Außenring | 6 | 156 m | 142 m | +14 m | amtlich |
| Bochum West | S10 Außenring | 6 | 156 m | 144 m | +12 m | amtlich |
| Hagenow Land | RE46 | 4+4 | 210 m | 200 m | +10 m | amtlich |
| Hattingen Mitte | S3 | 6 | 156 m | 148 m | +8 m | hoch |
| København H | RE17 | 8 | 210 m | 203 m | +7 m | hoch |
| Zeche Nachtigall | S30 | 6 | 156 m | 150 m | +6 m | hoch |
| Haus Kemnade | S30 | 6 | 156 m | 150 m | +6 m | niedrig |
| Essen-Steele Ost | S10 Außenring | 6 | 156 m | 151 m | +5 m | amtlich |
| Heinrichshütte | S30 | 6 | 156 m | 152 m | +4 m | hoch |
| Gdańsk Zaspa | RE71 | 8 | 210 m | 206 m | +4 m | hoch |
| Blankenstein Burg | S30 | 6 | 156 m | 153 m | +3 m | niedrig |
| Tønder | RE46 | 4 | 105 m | 102 m | +3 m | niedrig |
| Dortmund-Brackel | S10 Außenring | 6 | 156 m | 154 m | +2 m | amtlich |
| Bochum-Dahlhausen | S30 | 6 | 156 m | 154 m | +2 m | amtlich |

## Ohne Bahnsteigdaten

| Station | Linie | Wagen | benötigt |
|---|---|---|---|
| Großenbrode/Heiligenhafen | RE17 | 8 | 210 m |
| Nykøbing F. | RE17 | 8 | 210 m |
| Ringsted | RE17 | 8 | 210 m |
| Nørreport | RE17 | 8 | 210 m |
| Frankfurt Flughafen Regiobf | RE5 | 8 | 210 m |
| Hannover-Messe/Laatzen | RE7 | 8 | 210 m |
| Buchs SG | RE80 | 8 | 210 m |
| Feldkirch | RE80 | 8 | 210 m |
| Dornbirn | RE80 | 8 | 210 m |
| Bregenz | RE80 | 8 | 210 m |
| Fredericia | RE77 | 6 | 156 m |
| Padborg | RE77 | 6 | 156 m |
| Bettembourg | RE90 | 6 | 156 m |
| Ettelbruck | RE90 | 6 | 156 m |
| Witten Bommern | S30 | 6 | 156 m |
| Steinhelle | RE30 | 4 | 105 m |
| Probsteierhagen | RE90b | 3 | 80 m |
