# RE-Netz 2030 — Ist-Report

68 Richtungsvarianten, 31 Basislinien, 474 Stationen.

## Datenqualität

- ⚠️ S10_A: Haltename(n) mehrfach in derselben Linie (Ring): ['Unna Hbf', 'Bochum-Langendreer', 'Bochum-Langendreer West', 'Bochum Hbf']
- ⚠️ S10_I: Haltename(n) mehrfach in derselben Linie (Ring): ['Unna Hbf', 'Bochum-Langendreer', 'Bochum-Langendreer West', 'Bochum Hbf']
- ⚠️ Alias-Konflikt: 'Bochum-Höntrop' (RE40) und 'Essen-Höntrop' (S10) sind derselbe physische Bahnhof, aber im Datensatz getrennt — kein Umstieg in der Routensuche, Korridorerkennung übersieht den Mischbetriebsabschnitt.

## Knotenranking (Top 25, gewichtete Umsteigerelationen inkl. Endknoten-Bonus)

| # | Score | Station | Linien |
|---|---|---|---|
| 1 | 66.0 | Düsseldorf Hbf | RB37, RE2, RE30, RE32, RE5, RE90 |
| 2 | 42.0 | Berlin Hbf | RE11, RE46, RE71, RE77 |
| 3 | 40.0 | Rostock Hbf | RE17, RE35, RE35X, RE91 |
| 4 | 38.0 | Hamburg-Harburg | RE25, RE45, RE90b, RE91 |
| 5 | 38.0 | Berlin Südkreuz | RE35, RE35X, RE45, RE46 |
| 6 | 32.0 | Essen Hbf | RE2, RE32, RE40, S3, S30 |
| 7 | 31.0 | Bochum Hbf | RB37, RE32, RE40, RE9 |
| 8 | 29.0 | Mönchengladbach Hbf | RB37, RE14, RE32, RE90 |
| 9 | 26.0 | Hagen Hbf | RB37, RE30, RE40, S30 |
| 10 | 24.0 | Lübeck Hbf | RE17, RE45, RE46 |
| 11 | 24.0 | Duisburg Hbf | RE2, RE32, RE5 |
| 12 | 24.0 | Pasewalk | RE35, RE35X, RE71 |
| 13 | 22.0 | Hamm (Westf) Hbf | RE17, RE30, RE32 |
| 14 | 22.0 | Stralsund Hbf | RE35, RE35X, RE91 |
| 15 | 22.0 | Berlin-Spandau | RE45, RE46, RE77 |
| 16 | 20.0 | Kassel-Wilhelmshöhe | RE24, RE32, RE7 |
| 17 | 20.0 | Münster (Westf) Hbf | RE2, RE30, RE9 |
| 18 | 20.0 | Eberswalde Hbf | RE35, RE35X, RE71 |
| 19 | 20.0 | Bremen Hbf | RE7, RE9, RE90b |
| 20 | 18.0 | Berlin Hbf (tief) | RE35, RE35X, RE45 |
| 21 | 18.0 | Hamburg-Elbbrücken | RE45, RE90b, RE91 |
| 22 | 18.0 | Büchen | RE46, RE77, RE91 |
| 23 | 17.0 | Osnabrück Hbf | RE17, RE2, RE9 |
| 24 | 17.0 | Erfurt Hbf | RE24, RE28, RE39 |
| 25 | 16.0 | Hagenow Land | RE46, RE77, RE91 |

## Parallelkorridore (≥2 Linien, Top 20 nach mittlerer Taktabweichung)

| Von | Nach | Linien | Ist-Abfahrten (mod 60) | Lücken | Ideal | ⌀Abw. |
|---|---|---|---|---|---|---|
| Bochum Hbf | Dortmund Hbf | 2 | RE32:56, RE9:56 | [0, 0] | 30.0 | 30.0 |
| Berlin Gesundbrunnen | Berlin Hbf (tief) | 2 | RE35X:55, RE35:55 | [0, 0] | 30.0 | 30.0 |
| Essen-Steele Ost | Essen-Horst | 2 | S30:07, S3:07 | [0, 0] | 30.0 | 30.0 |
| Essen-Horst | Bochum-Dahlhausen | 2 | S30:10, S3:10 | [0, 0] | 30.0 | 30.0 |
| Bochum-Dahlhausen | Hattingen (Ruhr) | 2 | S30:15, S3:15 | [0, 0] | 30.0 | 30.0 |
| Berlin Hbf | Berlin Friedrichstraße | 2 | RE11:41, RE77:42 | [1, 59] | 30.0 | 29.0 |
| Berlin Friedrichstraße | Berlin Alexanderplatz | 2 | RE11:45, RE77:46 | [1, 59] | 30.0 | 29.0 |
| Berlin Alexanderplatz | Berlin Ostbahnhof | 2 | RE11:50, RE77:51 | [1, 59] | 30.0 | 29.0 |
| Wetter (Ruhr) | Witten Hbf | 2 | RE40:21, RB37:23 | [2, 58] | 30.0 | 28.0 |
| Witten Hbf | Bochum-Langendreer | 2 | RB37:30, S10 Außenring:32 | [2, 58] | 30.0 | 28.0 |
| Berlin Ostbahnhof | Berlin Alexanderplatz | 2 | RE77:04, RE11:06 | [2, 58] | 30.0 | 28.0 |
| Berlin Alexanderplatz | Berlin Friedrichstraße | 2 | RE77:09, RE11:11 | [2, 58] | 30.0 | 28.0 |
| Berlin Friedrichstraße | Berlin Hbf | 2 | RE77:14, RE11:16 | [2, 58] | 30.0 | 28.0 |
| Berlin-Wannsee | Potsdam Hbf | 2 | RE71:43, RE11:45 | [2, 58] | 30.0 | 28.0 |
| Hamm (Westf) Hbf | Kamen | 2 | RE17:25, RE32:27 | [2, 58] | 30.0 | 28.0 |
| Kamen | Dortmund Hbf | 2 | RE17:35, RE32:37 | [2, 58] | 30.0 | 28.0 |
| Dresden Hbf | Dresden-Neustadt | 2 | RE35:48, RE35X:50 | [2, 58] | 30.0 | 28.0 |
| Neu-Ulm | Ulm Hbf | 2 | RE80:41, RE94:43 | [2, 58] | 30.0 | 28.0 |
| Witten Hbf | Wetter (Ruhr) | 2 | RB37:29, RE40:32 | [3, 57] | 30.0 | 27.0 |
| Mönchengladbach Hbf | Viersen | 2 | RE14:53, RB37:56 | [3, 57] | 30.0 | 27.0 |

## Symmetrie je Linie (2·Symmetrieminute mod 60 an gemeinsamen Halten)

| Linie | n Halte | ⌀ 2σ | Spannweite |
|---|---|---|---|
| RE32 | 23 | 59.9 | 15 |
| RE57 | 21 | 57.0 | 7 |
| RE5 | 27 | 2.5 | 4 |
| S30 | 21 | 28.3 | 4 |
| RE2 | 7 | 59.4 | 3 |
| RE24 | 15 | 55.5 | 3 |
| RE25 | 15 | 47.9 | 3 |
| RE45 | 17 | 0.8 | 3 |
| RE90 | 20 | 40.9 | 3 |
| RB37 | 31 | 59.1 | 2 |
| RE14 | 17 | 0.1 | 2 |
| RE77 | 22 | 59.6 | 1 |
| RE11 | 16 | 0.0 | 0 |
| RE28 | 7 | 2.0 | 0 |
| RE35 | 25 | 30.0 | 0 |
| RE35X | 14 | 14.0 | 0 |
| RE39 | 12 | 49.0 | 0 |
| RE40 | 20 | 0.0 | 0 |
| RE46 | 22 | 59.0 | 0 |
| RE7 | 15 | 0.0 | 0 |
| RE71 | 36 | 13.0 | 0 |
| RE80 | 24 | 55.0 | 0 |
| RE9 | 7 | 0.0 | 0 |
| RE94 | 30 | 0.0 | 0 |
| S3 | 7 | 22.0 | 0 |

## Fahrzeugbedarf — heute vs. differenziertes Wendemodell (RE/RB ≥70, S-Bahn ≥20, +1 Reserve)

| Linie | T | Fahrzeit A/B | heute | neu | Δ | Wende A/B |
|---|---|---|---|---|---|---|
| RB37 | 30 | 205/205 | 14 | 20 | +6 | 80/80 |
| RE11 | 60 | 192/192 | 7 | 10 | +3 | 78/78 |
| RE14 | 60 | 331/331 | 12 | 15 | +3 | 89/89 |
| RE2 | 60 | 117/118 | 4 | 8 | +4 | 92/93 |
| RE24 | 60 | 205/204 | 8 | 11 | +3 | 95/96 |
| RE25 | 60 | 305/308 | 11 | 14 | +3 | 83/84 |
| RE28 | 60 | 162/162 | 6 | 9 | +3 | 78/78 |
| RE32 | 60 | 286/286 | 10 | 13 | +3 | 74/74 |
| RE35 | 60 | 436/436 | 16 | 18 | +2 | 74/74 |
| RE35X | 60 | 360/360 | 13 | 16 | +3 | 90/90 |
| RE39 | 60 | 219/219 | 8 | 11 | +3 | 81/81 |
| RE40 | 60 | 243/243 | 9 | 12 | +3 | 87/87 |
| RE45 | 60 | 320/322 | 12 | 15 | +3 | 99/99 |
| RE46 | 60 | 435/435 | 15 | 18 | +3 | 75/75 |
| RE5 | 60 | 289/289 | 11 | 13 | +2 | 71/71 |
| RE57 | 60 | 479/473 | 16 | 20 | +4 | 94/94 |
| RE7 | 60 | 265/265 | 9 | 13 | +4 | 95/95 |
| RE71 | 60 | 553/553 | 20 | 22 | +2 | 77/77 |
| RE77 | 60 | 376/377 | 13 | 16 | +3 | 73/74 |
| RE80 | 60 | 393/393 | 14 | 17 | +3 | 87/87 |
| RE9 | 60 | 214/214 | 8 | 11 | +3 | 86/86 |
| RE90 | 60 | 324/326 | 12 | 15 | +3 | 95/95 |
| RE94 | 60 | 592/592 | 20 | 24 | +4 | 98/98 |
| S3 | 30 | 22/22 | 2 | 4 | +2 | 23/23 |
| S30 | 30 | 90/86 | 6 | 9 | +3 | 32/32 |

**Summe: 276 → 354 (+78)**

## Abstellbedarf an Endbahnhöfen (Top 15)

| Bahnhof | Linien | Plätze | Gesamtlänge |
|---|---|---|---|
| Essen Hbf | 3 | 11 | 1638 m |
| Saarbrücken Hbf | 3 | 9 | 1488 m |
| Zwickau Hbf | 3 | 9 | 1488 m |
| Düsseldorf Hbf | 3 | 9 | 1251 m |
| Frankfurt (Main) Hbf | 3 | 9 | 1650 m |
| Arnhem Centraal | 2 | 7 | 1050 m |
| Dortmund Hbf | 2 | 6 | 1098 m |
| Warnemünde | 2 | 6 | 1098 m |
| Passau Hbf | 2 | 6 | 1098 m |
| Bremerhaven-Lehe | 2 | 6 | 870 m |
| Bochum Hbf | 1 | 4 | 420 m |
| Lüdenscheid Hbf | 1 | 4 | 624 m |
| Hattingen Mitte | 1 | 4 | 624 m |
| Leipzig Hbf | 1 | 3 | 552 m |
| Frankfurt (Oder) | 1 | 3 | 552 m |

## Bahnsteig-Mindestlängen (Top 15 + Verteilung)

Verteilung: 210m×186, 156m×130, 130m×52, 184m×40, 105m×37, 80m×12, 236m×10, 160m×7

| Station | Mindestlänge | Linie | Wagen |
|---|---|---|---|
| Oldenburg (Oldb) Hbf | 236 m | RE90b | 3+6 |
| Hamburg-Harburg | 236 m | RE90b | 3+6 |
| Buchholz (Nordheide) | 236 m | RE90b | 3+6 |
| Hamburg-Elbbrücken | 236 m | RE90b | 3+6 |
| Kiel Hbf | 236 m | RE90b | 3+6 |
| Neumünster | 236 m | RE90b | 3+6 |
| Elmshorn | 236 m | RE90b | 3+6 |
| Bremen Hbf | 236 m | RE90b | 3+6 |
| Leer (Ostfriesl) | 236 m | RE90b | 3+6 |
| Rotenburg (Wümme) | 236 m | RE90b | 3+6 |
| Arnhem Centraal | 210 m | RE5 | 8 |
| Mönchengladbach Hbf | 210 m | RE32 | 8 |
| Neuss Hbf | 210 m | RE32 | 8 |
| Düsseldorf-Bilk | 210 m | RE32 | 8 |
| Düsseldorf Hbf | 210 m | RE32 | 8 |
