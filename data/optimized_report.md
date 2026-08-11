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
| Dortmund Hbf | Bochum Hbf | 2 | RE9:00, RE32:02 | [2, 58] | 30.0 | 28.0 |
| Mönchengladbach Hbf | Viersen | 2 | RB37:00, RE14:03 | [3, 57] | 30.0 | 27.0 |
| Bamberg | Erfurt Hbf | 2 | RE28:41, RE39:45 | [4, 56] | 30.0 | 26.0 |
| Schwerte (Ruhr) | Holzwickede | 2 | S10 Innenring:28, RE30:32 | [4, 56] | 30.0 | 26.0 |
| Schleswig | Rendsburg | 2 | RE77:32, RE46:36 | [4, 56] | 30.0 | 26.0 |
| Rendsburg | Schleswig | 2 | RE46:07, RE77:11 | [4, 56] | 30.0 | 26.0 |
| Wetter (Ruhr) | Hagen Hbf | 2 | RE40:35, RB37:40 | [5, 55] | 30.0 | 25.0 |
| Hamburg-Harburg | Buxtehude | 2 | RE91:00, RE25:05 | [5, 55] | 30.0 | 25.0 |
| Bochum Hbf | Dortmund Hbf | 2 | RE32:47, RE9:52 | [5, 55] | 30.0 | 25.0 |
| Schleswig | Jübek | 2 | RE46:26, RE77:31 | [5, 55] | 30.0 | 25.0 |
| Bochum-Langendreer | Bochum-Langendreer West | 2 | S10 Innenring:32, S10 Außenring:37 | [5, 55] | 30.0 | 25.0 |
| Bochum-Langendreer West | Bochum Hbf | 2 | S10 Innenring:34, S10 Außenring:39 | [5, 55] | 30.0 | 25.0 |
| Düsseldorf Hbf | Wuppertal-Vohwinkel | 2 | RB37:16, RE30:22 | [6, 54] | 30.0 | 24.0 |
| Wuppertal-Vohwinkel | Wuppertal Hbf | 2 | RB37:32, RE30:38 | [6, 54] | 30.0 | 24.0 |
| Witten Hbf | Wetter (Ruhr) | 2 | RE40:27, RB37:33 | [6, 54] | 30.0 | 24.0 |
| Warnemünde | Rostock Hbf | 2 | RE35:04, RE35X:58 | [54, 6] | 30.0 | 24.0 |
| Dresden-Neustadt | Dresden Hbf | 2 | RE35:28, RE35X:34 | [6, 54] | 30.0 | 24.0 |
| Jübek | Schleswig | 2 | RE77:21, RE46:27 | [6, 54] | 30.0 | 24.0 |
| Bochum Hbf | Bochum-Langendreer West | 2 | S10 Außenring:05, S10 Innenring:59 | [54, 6] | 30.0 | 24.0 |
| Bochum-Langendreer West | Bochum-Langendreer | 2 | S10 Innenring:02, S10 Außenring:08 | [6, 54] | 30.0 | 24.0 |

## Symmetrie je Linie (2·Symmetrieminute mod 60 an gemeinsamen Halten)

| Linie | n Halte | ⌀ 2σ | Spannweite |
|---|---|---|---|
| RE32 | 23 | 1.9 | 15 |
| RE57 | 21 | 60.0 | 7 |
| RE5 | 27 | 1.5 | 4 |
| S30 | 21 | 46.3 | 4 |
| RE2 | 7 | 59.4 | 3 |
| RE24 | 15 | 58.5 | 3 |
| RE25 | 15 | 0.9 | 3 |
| RE45 | 17 | 59.8 | 3 |
| RE90 | 20 | 25.9 | 3 |
| RB37 | 31 | 47.1 | 2 |
| RE14 | 17 | 3.1 | 2 |
| RE77 | 22 | 0.6 | 1 |
| RE11 | 16 | 48.0 | 0 |
| RE28 | 7 | 0.0 | 0 |
| RE35 | 25 | 32.0 | 0 |
| RE35X | 14 | 9.0 | 0 |
| RE39 | 12 | 36.0 | 0 |
| RE40 | 20 | 0.0 | 0 |
| RE46 | 22 | 0.0 | 0 |
| RE7 | 15 | 0.0 | 0 |
| RE71 | 36 | 13.0 | 0 |
| RE80 | 24 | 0.0 | 0 |
| RE9 | 7 | 0.0 | 0 |
| RE94 | 30 | 0.0 | 0 |
| S3 | 7 | 43.0 | 0 |

## Fahrzeugbedarf — heute vs. differenziertes Wendemodell (RE/RB ≥70, S-Bahn ≥20, +1 Reserve)

| Linie | T | Fahrzeit A/B | heute | neu | Δ | Wende A/B |
|---|---|---|---|---|---|---|
| RB37 | 30 | 205/205 | 15 | 20 | +5 | 80/80 |
| RE11 | 60 | 192/192 | 8 | 10 | +2 | 78/78 |
| RE14 | 60 | 331/331 | 12 | 15 | +3 | 89/89 |
| RE2 | 60 | 117/118 | 5 | 8 | +3 | 92/93 |
| RE24 | 60 | 205/204 | 7 | 11 | +4 | 95/96 |
| RE25 | 60 | 305/308 | 11 | 14 | +3 | 83/84 |
| RE28 | 60 | 162/162 | 6 | 9 | +3 | 78/78 |
| RE32 | 60 | 286/286 | 10 | 13 | +3 | 74/74 |
| RE35 | 60 | 436/436 | 16 | 18 | +2 | 74/74 |
| RE35X | 60 | 360/360 | 13 | 16 | +3 | 90/90 |
| RE39 | 60 | 219/219 | 8 | 11 | +3 | 81/81 |
| RE40 | 60 | 243/243 | 9 | 12 | +3 | 87/87 |
| RE45 | 60 | 320/322 | 11 | 15 | +4 | 99/99 |
| RE46 | 60 | 435/435 | 15 | 18 | +3 | 75/75 |
| RE5 | 60 | 289/289 | 10 | 13 | +3 | 71/71 |
| RE57 | 60 | 479/473 | 17 | 20 | +3 | 94/94 |
| RE7 | 60 | 265/265 | 9 | 13 | +4 | 95/95 |
| RE71 | 60 | 553/553 | 19 | 22 | +3 | 77/77 |
| RE77 | 60 | 376/377 | 14 | 16 | +2 | 73/74 |
| RE80 | 60 | 393/393 | 14 | 17 | +3 | 87/87 |
| RE9 | 60 | 214/214 | 8 | 11 | +3 | 86/86 |
| RE90 | 60 | 324/326 | 12 | 15 | +3 | 95/95 |
| RE94 | 60 | 592/592 | 21 | 24 | +3 | 98/98 |
| S3 | 30 | 22/22 | 3 | 4 | +1 | 23/23 |
| S30 | 30 | 90/86 | 7 | 9 | +2 | 32/32 |

**Summe: 280 → 354 (+74)**

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
