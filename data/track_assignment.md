# Netzweite Gleiszuweisung — RE-Netz 2030

Jede Richtungsvariante bekommt an jedem Halt ein festes, längenpassendes Gleis — konsistent nach physischem Streckenast (Nachbarhaltestelle als Richtungs-Proxy) und mit echter Minuten-Konfliktprüfung je Gleis (siehe Docstring in `tools/track_assignment.py`). Datengrundlage: DB InfraGO (amtlich, deutsche Bahnhöfe), OSM/Overpass (Ausland + Restlücken), Projekt-Fiktion (fiktiv, höchste Priorität), sonst eine dokumentierte Schätzung.

## Zusammenfassung

- 474 Stationen, 1317 Zuweisungen (Variante×Halt)
- Quellen: amtlich 341, amtlich-ausland 57, fiktiv 12, geschaetzt 11, osm 53
- Konfliktstufen (Bahnsteiglänge): gering 75, kritisch 47, ok 1195 (ok = passt, gering = ≤25 m Überhang/SDO ausreichend, kritisch = >25 m)
- 28 Zuweisungen auf einem Gleis, das sich zwei verschiedene Richtungen teilen (Gleiszahl der Station reicht nicht für volle Richtungstrennung) — überall sonst: eine Richtung = ein festes Gleis.

## Kritisch (>25 m Überhang)

| Station | Linie | Variante | Gleis | benötigt | Überhang | Quelle |
|---|---|---|---|---|---|---|
| Roermond (NL) | RE32 | RE32_N | 1 | 210 m | +188 m | osm |
| Roermond (NL) | RE32 | RE32_S | 1 | 210 m | +188 m | osm |
| Gdańsk Zaspa | RE71 | RE71_A | 1 | 210 m | +160 m | osm |
| Bochum-Kohlenstraße | S11 Außenring | S10_A | 2 | 156 m | +123 m | osm |
| Bochum-Kohlenstraße | S10 Innenring | S10_I | 2 | 156 m | +123 m | osm |
| Wengern | S11 Außenring | S10_A | 1 | 156 m | +112 m | osm |
| Wengern | S10 Innenring | S10_I | 1 | 156 m | +112 m | osm |
| Luxembourg | RE90 | RE90_A | 1 | 156 m | +102 m | osm |
| Luxembourg | RE90 | RE90_B | 1 | 156 m | +102 m | osm |
| Żelistrzewo | RE71 | RE71_A | 1 | 210 m | +85 m | osm |
| Żelistrzewo | RE71 | RE71_B | 1 | 210 m | +85 m | osm |
| Dalheim | RE32 | RE32_N | 1 | 210 m | +85 m | amtlich |
| Dalheim | RE32 | RE32_S | 1 | 210 m | +85 m | amtlich |
| Wegberg | RE32 | RE32_N | 1 | 210 m | +85 m | amtlich |
| Wegberg | RE32 | RE32_S | 1 | 210 m | +85 m | amtlich |
| Starogard Gdański | RE71 | RE71_A | 2 | 210 m | +85 m | amtlich-ausland |
| Starogard Gdański | RE71 | RE71_B | 2 | 210 m | +85 m | amtlich-ausland |
| Mrzezino | RE71 | RE71_A | 2 | 210 m | +85 m | amtlich-ausland |
| Mrzezino | RE71 | RE71_B | 1 | 210 m | +85 m | amtlich-ausland |
| Swarzewo | RE71 | RE71_A | 1 | 210 m | +85 m | amtlich-ausland |
| Swarzewo | RE71 | RE71_B | 1 | 210 m | +85 m | amtlich-ausland |
| Władysławowo Port | RE71 | RE71_A | 1 | 210 m | +85 m | amtlich-ausland |
| Władysławowo Port | RE71 | RE71_B | 1 | 210 m | +85 m | amtlich-ausland |
| Herbede | S30 | S30_N | 1 | 156 m | +82 m | osm |
| Herbede | S30 | S30_S | 1 | 156 m | +82 m | osm |
| Ruine Hardenstein | S30 | S30_N | 1 | 156 m | +74 m | osm |
| Ruine Hardenstein | S30 | S30_S | 1 | 156 m | +74 m | osm |
| Neustadt (Dosse) | RE46 | RE46_A | 1 | 210 m | +70 m | amtlich |
| Neustadt (Dosse) | RE46 | RE46_B | 1 | 210 m | +70 m | amtlich |
| Greifswald | RE35X | RE35X_N | 3 | 210 m | +68 m | amtlich |
| Greifswald | RE35X | RE35X_S | 3 | 210 m | +68 m | amtlich |
| Hagenow Land | RE91 | RE91_BO | 1b | 160 m | +55 m | amtlich |
| Hagenow Land | RE91 | RE91_BS | 1b | 160 m | +55 m | amtlich |
| Hagenow Land | RE91 | RE91_OB | 1b | 160 m | +55 m | amtlich |
| Hagenow Land | RE91 | RE91_SB | 1b | 160 m | +55 m | amtlich |
| Gdynia Wzgórze Św. Maksymiliana | RE71 | RE71_A | 101 | 210 m | +55 m | osm |
| Gdynia Wzgórze Św. Maksymiliana | RE71 | RE71_B | 101 | 210 m | +55 m | osm |
| Chojnice | RE71 | RE71_A | 12 | 210 m | +50 m | amtlich-ausland |
| Chojnice | RE71 | RE71_B | 12 | 210 m | +50 m | amtlich-ausland |
| Büchen | RE77 | RE77_A | 21 | 156 m | +44 m | amtlich |
| Büchen | RE77 | RE77_B | 21 | 156 m | +44 m | amtlich |
| Bremerhaven-Lehe | RE9 | RE9_A | 3 | 210 m | +40 m | amtlich |
| Bremerhaven-Lehe | RE9 | RE9_B | 3 | 210 m | +40 m | amtlich |
| Eberswalde Hbf | RE35X | RE35X_N | 2 | 210 m | +34 m | amtlich |
| Eberswalde Hbf | RE35X | RE35X_S | 2 | 210 m | +34 m | amtlich |
| Bochum-Bermuda3eck | S11 Außenring | S10_A | 1 | 156 m | +28 m | osm |
| Bochum-Bermuda3eck | S10 Innenring | S10_I | 1 | 156 m | +28 m | osm |

## Gering (≤25 m Überhang, SDO/geplante Verlängerung deckt es ab)

| Station | Linie | Variante | Gleis | benötigt | Überhang | Quelle |
|---|---|---|---|---|---|---|
| Bramsche | RE17 | RE17DW_A | 1 | 156 m | +25 m | amtlich |
| Bramsche | RE17 | RE17DW_B | 1 | 156 m | +25 m | amtlich |
| Essen (Oldb) | RE17 | RE17DW_A | 1 | 156 m | +25 m | amtlich |
| Essen (Oldb) | RE17 | RE17DW_B | 1 | 156 m | +25 m | amtlich |
| Cloppenburg | RE17 | RE17DW_A | 1 | 156 m | +25 m | amtlich |
| Cloppenburg | RE17 | RE17DW_B | 1 | 156 m | +25 m | amtlich |
| Drensteinfurt | RE30 | RE30_DL | 2 | 210 m | +25 m | amtlich |
| Drensteinfurt | RE30 | RE30_LD | 2 | 210 m | +25 m | amtlich |
| Drensteinfurt | RE30 | RE30_LW | 2 | 210 m | +25 m | amtlich |
| Drensteinfurt | RE30 | RE30_WL | 2 | 210 m | +25 m | amtlich |
| Lüdenscheid Hbf | S30 | S30_N | 1 | 156 m | +25 m | amtlich |
| Lüdenscheid Hbf | S30 | S30_S | 1 | 156 m | +25 m | amtlich |
| Zevenaar | RE5 | RE5_A | 3 | 210 m | +24 m | osm |
| Zevenaar | RE5 | RE5_B | 3 | 210 m | +24 m | osm |
| Freital Hbf | RE35 | RE35_N | 3 | 156 m | +21 m | osm |
| Freital Hbf | RE35 | RE35_S | 3 | 156 m | +21 m | osm |
| Landstuhl | RE80 | RE80_A | 2 | 210 m | +20 m | amtlich |
| Landstuhl | RE80 | RE80_B | 2 | 210 m | +20 m | amtlich |
| Rövershagen | RE91 | RE91_BO | 1 | 160 m | +20 m | amtlich |
| Rövershagen | RE91 | RE91_BS | 1 | 160 m | +20 m | amtlich |
| Rövershagen | RE91 | RE91_OB | 1 | 160 m | +20 m | amtlich |
| Rövershagen | RE91 | RE91_SB | 1 | 160 m | +20 m | amtlich |
| Hengelo | RE30 | RE30_DL | 2a | 210 m | +19 m | osm |
| Hengelo | RE30 | RE30_LD | 2a | 210 m | +19 m | osm |
| Hengelo | RE30 | RE30_LW | 2a | 210 m | +19 m | osm |
| Hengelo | RE30 | RE30_WL | 2a | 210 m | +19 m | osm |
| Rotenburg (Wümme) | RE90b | RE90b_GS | 4 | 236 m | +16 m | amtlich |
| Rotenburg (Wümme) | RE90b | RE90b_KN | 4 | 236 m | +16 m | amtlich |
| Rotenburg (Wümme) | RE90b | RE90b_NK | 4 | 236 m | +16 m | amtlich |
| Rotenburg (Wümme) | RE90b | RE90b_SG | 4 | 236 m | +16 m | amtlich |
| Hagen-Vorhalle | S11 Außenring | S10_A | 2 | 156 m | +16 m | amtlich |
| Hagen-Vorhalle | S10 Innenring | S10_I | 2 | 156 m | +16 m | amtlich |
| Hagen-Vorhalle | S30 | S30_N | 2 | 156 m | +16 m | amtlich |
| Hagen-Vorhalle | S30 | S30_S | 2 | 156 m | +16 m | amtlich |
| Bochum-Hamme | S11 Außenring | S10_A | 1 | 156 m | +16 m | amtlich |
| Bochum-Hamme | S10 Innenring | S10_I | 1 | 156 m | +16 m | amtlich |
| Allersberg (Rothsee) | RE94 | RE94_A | 1 | 184 m | +14 m | amtlich |
| Allersberg (Rothsee) | RE94 | RE94_B | 1 | 184 m | +14 m | amtlich |
| Essen-Borbeck | S11 Außenring | S10_A | 2 | 156 m | +14 m | amtlich |
| Essen-Borbeck | S10 Innenring | S10_I | 2 | 156 m | +14 m | amtlich |
| Bochum West | S11 Außenring | S10_A | 1 | 156 m | +12 m | amtlich |
| Bochum West | S10 Innenring | S10_I | 1 | 156 m | +12 m | amtlich |
| Hagenow Land | RE46 | RE46_A | 3 | 210 m | +10 m | amtlich |
| Hagenow Land | RE46 | RE46_B | 2 | 210 m | +10 m | amtlich |
| Nørreport | RE17 | RE17OR_N | 1 | 210 m | +7 m | amtlich-ausland |
| Nørreport | RE17 | RE17OR_S | 2 | 210 m | +7 m | amtlich-ausland |
| Essen-Steele Ost | S11 Außenring | S10_A | 1 | 156 m | +7 m | amtlich |
| Essen-Steele Ost | S10 Innenring | S10_I | 1 | 156 m | +7 m | amtlich |
| Zeche Nachtigall | S30 | S30_N | 1 | 156 m | +6 m | osm |
| Zeche Nachtigall | S30 | S30_S | 1 | 156 m | +6 m | osm |
| Haus Kemnade | S30 | S30_N | 1 | 156 m | +6 m | osm |
| Haus Kemnade | S30 | S30_S | 1 | 156 m | +6 m | osm |
| Hattingen Mitte | S3 | S3_N | 1 | 156 m | +6 m | amtlich |
| Hattingen Mitte | S3 | S3_S | 1 | 156 m | +6 m | amtlich |
| Essen-Steele Ost | S30 | S30_N | 2 | 156 m | +5 m | amtlich |
| Essen-Steele Ost | S30 | S30_S | 2 | 156 m | +5 m | amtlich |
| Essen-Steele Ost | S3 | S3_N | 2 | 156 m | +5 m | amtlich |
| Essen-Steele Ost | S3 | S3_S | 2 | 156 m | +5 m | amtlich |
| Heinrichshütte | S30 | S30_N | 1 | 156 m | +4 m | osm |
| Heinrichshütte | S30 | S30_S | 1 | 156 m | +4 m | osm |
| Gdańsk Zaspa | RE71 | RE71_B | 501;502 | 210 m | +4 m | osm |
| Almelo | RE30 | RE30_DL | 4a | 210 m | +4 m | osm |
| Almelo | RE30 | RE30_WL | 4a | 210 m | +4 m | osm |
| Blankenstein Burg | S30 | S30_N | 1 | 156 m | +3 m | osm |
| Blankenstein Burg | S30 | S30_S | 1 | 156 m | +3 m | osm |
| Tønder | RE46 | RE46_A | 1 | 105 m | +2 m | amtlich-ausland |
| Tønder | RE46 | RE46_B | 2 | 105 m | +2 m | amtlich-ausland |
| Dortmund-Brackel | S11 Außenring | S10_A | 1 | 156 m | +2 m | amtlich |
| Dortmund-Brackel | S10 Innenring | S10_I | 1 | 156 m | +2 m | amtlich |
| Bochum-Dahlhausen | S30 | S30_N | 1 | 156 m | +2 m | amtlich |
| Bochum-Dahlhausen | S30 | S30_S | 1 | 156 m | +2 m | amtlich |
| Bochum-Dahlhausen | S3 | S3_N | 1 | 156 m | +2 m | amtlich |
| Bochum-Dahlhausen | S3 | S3_S | 1 | 156 m | +2 m | amtlich |
| Mülheim-Styrum | S11 Außenring | S10_A | 2 | 156 m | +1 m | amtlich |
| Mülheim-Styrum | S10 Innenring | S10_I | 2 | 156 m | +1 m | amtlich |

## Stationen mit geteilten Gleisen (Richtungstrennung nicht möglich)

| Station | Betroffene Zuweisungen |
|---|---|
| Bochum Hbf | 8 |
| Witten Hbf | 6 |
| Bochum-Langendreer | 6 |
| Hagen-Vorhalle | 4 |
| Hattingen (Ruhr) | 4 |

## Stationen mit geschätzten Gleisen (keine Quelle vorhanden)

Bettembourg, Bregenz, Dornbirn, Ettelbruck, Feldkirch, Frankfurt Flughafen Regiobf, Großenbrode/Heiligenhafen, Hannover-Messe/Laatzen, Probsteierhagen, Steinhelle, Witten Bommern
