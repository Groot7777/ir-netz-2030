# Paket 6 — Finale Knotenliste (zur Freigabe)

Symmetrieminute σ = :00 (Schweizer Stil). θ-Werte sind relativ zu einem Anker — welche absolute Minute σ=:00 real bekommt, legt erst die spätere Ankerlinie fest.

## Zugeordnete Knoten

| # | Station | Score | θ | Gleise | Längste verfügbare Gleise (m) | Quelle |
|---|---|---|---|---|---|---|
| 2 | Berlin Hbf | 42.0 | :00 | 15 | 430, 430, 430, 430, 430, 430 | amtlich |
| 3 | Rostock Hbf | 40.0 | :00 | 11 | 380, 372, 302, 302, 234, 216 | amtlich |
| 4 | Hamburg-Harburg | 38.0 | :00 | 8 | 492, 492, 463, 463, 455, 443 | amtlich |
| 6 | Essen Hbf | 32.0 | :00 | 13 | 667, 482, 481, 481, 445, 404 | amtlich |
| 7 | Bochum Hbf | 31.0 | :30 | 8 | 430, 430, 351, 343, 227, 180 | amtlich |
| 24 | Erfurt Hbf | 17.0 | :00 | 10 | 554, 552, 421, 420, 420, 419 | amtlich |
| 27 | Saarbrücken Hbf | 12.0 | :00 | 10 | 550, 415, 400, 400, 323, 280 | amtlich |
| 30 | Dortmund Hbf | 10.0 | :00 | 16 | 418, 417, 416, 416, 416, 406 | amtlich |

## Konflikte — 22 Stationen ohne widerspruchsfreie θ-Zuordnung

Diese Stationen lassen sich nicht widerspruchsfrei in das θ∈{0,30}-Raster einfügen (Fahrzeit zu einer bereits zugeordneten Station passt nicht auf ein Vielfaches von 30 Min, oder zwei Nachbarn verlangen widersprüchliche θ). **Das ist eine Entscheidung, keine Berechnung** — mögliche Auflösungen: Halbknoten statt Vollknoten, Fahrzeit-Streckung (Stufe 2), oder bewusst kein Taktknoten an dieser Station.

| Station | Score | Konflikt |
|---|---|---|
| Düsseldorf Hbf | 66.0 | RE32: Essen Hbf↔Düsseldorf Hbf 37 Min (Abw. 7 vom 30er-Raster) |
| Berlin Südkreuz | 38.0 | RE46: Berlin Hbf↔Berlin Südkreuz 10 Min (Abw. 10 vom 30er-Raster) |
| Mönchengladbach Hbf | 29.0 | RE32: Essen Hbf↔Mönchengladbach Hbf 67 Min (Abw. 7 vom 30er-Raster) |
| Hagen Hbf | 26.0 | RE40: Essen Hbf↔Hagen Hbf 46 Min (Abw. 14 vom 30er-Raster) |
| Lübeck Hbf | 24.0 | θ-Widerspruch über Hamburg-Harburg (RE45) |
| Duisburg Hbf | 24.0 | RE2: Essen Hbf↔Duisburg Hbf 11 Min (Abw. 11 vom 30er-Raster) |
| Pasewalk | 24.0 | RE71: Berlin Hbf↔Pasewalk 127 Min (Abw. 7 vom 30er-Raster) |
| Hamm (Westf) Hbf | 22.0 | RE32: Essen Hbf↔Hamm (Westf) Hbf 43 Min (Abw. 13 vom 30er-Raster) |
| Stralsund Hbf | 22.0 | RE35X: Rostock Hbf↔Stralsund Hbf 44 Min (Abw. 14 vom 30er-Raster) |
| Berlin-Spandau | 22.0 | RE46: Berlin Hbf↔Berlin-Spandau 10 Min (Abw. 10 vom 30er-Raster) |
| Kassel-Wilhelmshöhe | 20.0 | RE32: Essen Hbf↔Kassel-Wilhelmshöhe 163 Min (Abw. 13 vom 30er-Raster) |
| Münster (Westf) Hbf | 20.0 | RE2: Essen Hbf↔Münster (Westf) Hbf 50 Min (Abw. 10 vom 30er-Raster) |
| Eberswalde Hbf | 20.0 | RE71: Berlin Hbf↔Eberswalde Hbf 75 Min (Abw. 15 vom 30er-Raster) |
| Bremen Hbf | 20.0 | RE9: Dortmund Hbf↔Bremen Hbf 159 Min (Abw. 9 vom 30er-Raster) |
| Berlin Hbf (tief) | 18.0 | θ-Widerspruch über Rostock Hbf (RE35) |
| Hamburg-Elbbrücken | 18.0 | RE91: Rostock Hbf↔Hamburg-Elbbrücken 113 Min (Abw. 7 vom 30er-Raster) |
| Büchen | 18.0 | RE77: Berlin Hbf↔Büchen 108 Min (Abw. 12 vom 30er-Raster) |
| Osnabrück Hbf | 17.0 | RE17: Dortmund Hbf↔Osnabrück Hbf 101 Min (Abw. 11 vom 30er-Raster) |
| Hagenow Land | 16.0 | RE46: Berlin Hbf↔Hagenow Land 100 Min (Abw. 10 vom 30er-Raster) |
| Kiel Hbf | 14.0 | RE46: Berlin Hbf↔Kiel Hbf 227 Min (Abw. 13 vom 30er-Raster) |
| Zwickau Hbf | 12.0 | RE35X: Rostock Hbf↔Zwickau Hbf 346 Min (Abw. 14 vom 30er-Raster) |
| Frankfurt (Main) Hbf | 12.0 | RE40: Bochum Hbf↔Frankfurt (Main) Hbf 223 Min (Abw. 13 vom 30er-Raster) |

## Ist-Ankunfts-/Abfahrtsminuten an den zugeordneten Knoten (heute, vor Optimierung)

### Berlin Hbf (θ=:00)

| Linie | T | an | ab |
|---|---|---|---|
| RE46 | 60 | :04 | :07 |
| RE77 | 60 | :17 | :20 |
| RE11 | 60 | :19 | :22 |
| RE71 | 60 | :20 | :26 |
| RE11 | 60 | :38 | :41 |
| RE77 | 60 | :39 | :42 |
| RE71 | 60 | :47 | :53 |
| RE46 | 60 | :52 | :55 |

### Rostock Hbf (θ=:00)

| Linie | T | an | ab |
|---|---|---|---|
| RE17 | 60 | :04 | :04 |
| RE35 | 60 | :04 | :08 |
| RE35X | 60 | :18 | :22 |
| RE35 | 60 | :22 | :26 |
| RE91 | 60 | :26 | :32 |
| RE91 | 60 | :26 | :32 |
| RE91 | 60 | :32 | :38 |
| RE91 | 60 | :32 | :38 |
| RE17 | 60 | :43 | :43 |
| RE35X | 60 | :52 | :56 |

### Hamburg-Harburg (θ=:00)

| Linie | T | an | ab |
|---|---|---|---|
| RE45 | 60 | :10 | :12 |
| RE90b | 60 | :16 | :19 |
| RE91 | 60 | :19 | :22 |
| RE91 | 60 | :19 | :22 |
| RE90b | 60 | :22 | :25 |
| RE90b | 60 | :24 | :27 |
| RE90b | 60 | :39 | :42 |
| RE91 | 60 | :42 | :45 |
| RE91 | 60 | :42 | :45 |
| RE25 | 60 | :48 | :53 |
| RE45 | 60 | :49 | :51 |
| RE25 | 60 | :55 | :00 |

### Essen Hbf (θ=:00)

| Linie | T | an | ab |
|---|---|---|---|
| S30 | 30 | :00 | :00 |
| S30 | 30 | :00 | :00 |
| RE40 | 60 | :02 | :02 |
| S10 Außenring | 10 | :04 | :06 |
| S10 Innenring | 10 | :05 | :07 |
| S3 | 30 | :07 | :07 |
| RE32 | 60 | :15 | :17 |
| S3 | 30 | :15 | :15 |
| RE2 | 60 | :28 | :30 |
| RE2 | 60 | :28 | :30 |
| RE32 | 60 | :41 | :43 |
| RE40 | 60 | :58 | :58 |

### Bochum Hbf (θ=:30)

| Linie | T | an | ab |
|---|---|---|---|
| RE32 | 60 | :01 | :03 |
| S10 Außenring | 10 | :02 | :04 |
| S10 Außenring | 10 | :03 | :05 |
| RE9 | 60 | :04 | :06 |
| S10 Innenring | 10 | :07 | :09 |
| S10 Innenring | 10 | :07 | :09 |
| RB37 | 30 | :12 | :12 |
| RB37 | 30 | :17 | :17 |
| RE40 | 60 | :20 | :22 |
| RE40 | 60 | :38 | :40 |
| RE32 | 60 | :54 | :56 |
| RE9 | 60 | :54 | :56 |

### Erfurt Hbf (θ=:00)

| Linie | T | an | ab |
|---|---|---|---|
| RE39 | 60 | :10 | :10 |
| RE28 | 60 | :22 | :26 |
| RE28 | 60 | :36 | :40 |
| RE39 | 60 | :39 | :39 |
| RE24 | 60 | :55 | :58 |
| RE24 | 60 | :57 | :00 |

### Saarbrücken Hbf (θ=:00)

| Linie | T | an | ab |
|---|---|---|---|
| RE80 | 60 | :10 | :10 |
| RE14 | 60 | :24 | :24 |
| RE14 | 60 | :36 | :36 |
| RE80 | 60 | :45 | :45 |
| RE90 | 60 | :45 | :45 |
| RE90 | 60 | :57 | :57 |

### Dortmund Hbf (θ=:00)

| Linie | T | an | ab |
|---|---|---|---|
| RE9 | 60 | :04 | :04 |
| S10 Außenring | 10 | :04 | :06 |
| S10 Innenring | 10 | :06 | :08 |
| RE32 | 60 | :07 | :09 |
| RE17 | 60 | :16 | :16 |
| RE17 | 60 | :44 | :44 |
| RE32 | 60 | :49 | :51 |
| RE9 | 60 | :56 | :56 |
