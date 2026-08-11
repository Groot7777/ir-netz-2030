# Bahnsteiglängen-Konfliktliste

Vergleich der aus Wagenzahl/Kupplung errechneten Zuglänge gegen reale Bahnsteiglängen (DB InfraGO-Nettobaulänge wo vorhanden, sonst OpenStreetMap/Overpass). SDO-Toleranz: 25 m — Überhang bis dahin gilt als unkritisch (Selective Door Opening bzw. bereits eingeplante Bahnsteig-verlängerung), erst darüber als echter Prüffall.

- **0 kritisch, fiktive Planung** (RE-Netz-2030-eigener Ausbau, siehe data/manual_overrides.json)
- **4 kritisch, amtliche Daten** (DB InfraGO — ernstzunehmender Befund)
- **5 kritisch, amtliche Auslandsdaten** (CH/PL/FR/DK — ernstzunehmender Befund)
- **3 kritisch, hohe OSM-Konfidenz** (≥3 unabhängige OSM-Treffer, ungeprüft)
- **6 kritisch, niedrige OSM-Konfidenz** (<3 Treffer — meist OSM-Lücke statt echtes Problem)
- **28 gering** (SDO ausreichend)
- **417 unauffällig**
- **11 ohne Bahnsteigdaten** (manuell zu prüfen)

> **Befund zur Datenqualität:** Für 341 deutsche Stationen liegt jetzt die amtliche DB InfraGO-Nettobaulänge vor (tools/dbinfrago_platforms.py, gleisscharf in data/dbinfrago_platforms.json), für 64 weitere (v.a. die 101 ausländischen Stationen sowie einzelne kleine deutsche Halte ohne dbinfrago-Eintrag) nur die unsichere OSM-Schätzung. Mit amtlichen Daten bleiben **nur noch 4 echte Kritisch-Fälle** übrig — überwiegend kleine S-Bahn-Halte (S10-Ring, S30), deren Bahnsteige nie für 6-teilige Züge gebaut wurden. Das ist jetzt eher eine Entscheidung über Zuglänge/Kurzzug-Einsatz an diesen Halten als ein Datenproblem. Für Stationen ohne amtliche Bestätigung gilt weiterhin: OSM-Konfidenz 'niedrig' ist meist eine Datenlücke, kein echtes Bahnsteigproblem — auch 'hohe' OSM-Konfidenz war in Stichproben nicht durchgehend verlässlich (z.B. Mainz Hbf: 10 OSM-Treffer, dennoch nur 83 statt amtlich 210+ m). Vor jeder Maßnahme ohne amtliche Bestätigung gegenprüfen.

## Kritisch — fiktive RE-Netz-2030-Planung

Keine.

## Kritisch — amtliche DB-InfraGO-Daten

| Station | Linie | Wagen | benötigt | verfügbar | Überhang |
|---|---|---|---|---|---|
| Dalheim | RE32 | 8 | 210 m | 125 m | **+85 m** |
| Wegberg | RE32 | 8 | 210 m | 125 m | **+85 m** |
| Neustadt (Dosse) | RE46 | 4+4 | 210 m | 140 m | **+70 m** |
| Bremerhaven-Lehe | RE9 | 8 | 210 m | 170 m | **+40 m** |

## Kritisch — amtliche Auslandsdaten (CH/PL/FR/DK)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang |
|---|---|---|---|---|---|
| Starogard Gdański | RE71 | 8 | 210 m | 125 m | **+85 m** |
| Mrzezino | RE71 | 8 | 210 m | 125 m | **+85 m** |
| Swarzewo | RE71 | 8 | 210 m | 125 m | **+85 m** |
| Władysławowo Port | RE71 | 8 | 210 m | 125 m | **+85 m** |
| Chojnice | RE71 | 8 | 210 m | 160 m | **+50 m** |

## Kritisch — hohe OSM-Konfidenz (ungeprüft)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |
|---|---|---|---|---|---|---|
| Bochum-Kohlenstraße | S10 Außenring | 6 | 156 m | 34 m | +122 m | 4 |
| Luxembourg | RE90 | 6 | 156 m | 54 m | +102 m | 4 |
| Gdynia Wzgórze Św. Maksymiliana | RE71 | 8 | 210 m | 155 m | +55 m | 5 |

## Kritisch — niedrige OSM-Konfidenz (vermutlich OSM-Lücke, 6 Fälle)

| Station | Linie | Wagen | benötigt | verfügbar | Überhang | Treffer |
|---|---|---|---|---|---|---|
| Roermond (NL) | RE32 | 8 | 210 m | 22 m | +188 m | 1 |
| Wengern | S10 Außenring | 6 | 156 m | 44 m | +112 m | 1 |
| Żelistrzewo | RE71 | 8 | 210 m | 125 m | +85 m | 1 |
| Herbede | S30 | 6 | 156 m | 74 m | +82 m | 1 |
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
| Nørreport | RE17 | 8 | 210 m | 203 m | +7 m | amtlich-ausland |
| Zeche Nachtigall | S30 | 6 | 156 m | 150 m | +6 m | hoch |
| Haus Kemnade | S30 | 6 | 156 m | 150 m | +6 m | niedrig |
| Hattingen Mitte | S3 | 6 | 156 m | 150 m | +6 m | amtlich |
| Essen-Steele Ost | S10 Außenring | 6 | 156 m | 151 m | +5 m | amtlich |
| Heinrichshütte | S30 | 6 | 156 m | 152 m | +4 m | hoch |
| Gdańsk Zaspa | RE71 | 8 | 210 m | 206 m | +4 m | hoch |
| Blankenstein Burg | S30 | 6 | 156 m | 153 m | +3 m | niedrig |
| Dortmund-Brackel | S10 Außenring | 6 | 156 m | 154 m | +2 m | amtlich |
| Bochum-Dahlhausen | S30 | 6 | 156 m | 154 m | +2 m | amtlich |
| Tønder | RE46 | 4 | 105 m | 103 m | +2 m | amtlich-ausland |

## Ohne Bahnsteigdaten

| Station | Linie | Wagen | benötigt |
|---|---|---|---|
| Großenbrode/Heiligenhafen | RE17 | 8 | 210 m |
| Frankfurt Flughafen Regiobf | RE5 | 8 | 210 m |
| Hannover-Messe/Laatzen | RE7 | 8 | 210 m |
| Feldkirch | RE80 | 8 | 210 m |
| Dornbirn | RE80 | 8 | 210 m |
| Bregenz | RE80 | 8 | 210 m |
| Bettembourg | RE90 | 6 | 156 m |
| Ettelbruck | RE90 | 6 | 156 m |
| Witten Bommern | S30 | 6 | 156 m |
| Steinhelle | RE30 | 4 | 105 m |
| Probsteierhagen | RE90b | 3 | 80 m |
