# RE-Netz 2030 — Netzkarte

Erzeugt aus einer KML-Datei mit 31 Zuglinien eine interaktive Netzkarte im Stil
des NRW-Regionalverkehrsplans: farbige Linienbündel, Halte als weiße Kapseln
quer über das Bündel, Knotenbahnhöfe als Stadion mit fettem Namen,
Liniennummern in abgerundeten Badges, Länderflächen mit Staats- und
Bundeslandgrenzen im Hintergrund. Zwei Kartenseiten, Hell- und Dunkelmodus,
bedienbar auf Rechner und Handy.

**Endprodukt:** `netzkarte.html` — eine einzelne, in sich geschlossene Datei
ohne externe Abhängigkeiten zur Laufzeit.

## Karte ansehen

`netzkarte.html` im Browser öffnen. Kein Server, kein Build-Schritt nötig.
Funktioniert auf Rechner und Handy.

**Am Rechner**

- **Zoom** per Mausrad (zentriert auf den Cursor), **Verschieben** per Ziehen
- **Hovern** über eine Linie hebt sie hervor und blendet die übrigen ab;
  **Klick** hält die Hervorhebung fest
- **Doppelklick** vergrößert um den angeklickten Punkt

**Auf dem Handy**

- **Zwei Finger** zum Zoomen, **ein Finger** zum Verschieben,
  **Doppeltipp** vergrößert
- Die Seitenleiste mit Suche und Legende klappt über den **☰-Knopf** aus und
  schließt sich nach der Auswahl wieder
- Das Infofeld liegt als Karte über der Karte, nicht in der Seitenleiste

**Überall**

- **Hell und Dunkel** über den ☾/☀-Knopf. Startwert kommt aus der
  Systemeinstellung und folgt ihr auch, wenn sie sich während der Sitzung
  ändert. Da localStorage ausgeschlossen ist, gilt eine manuelle Auswahl nur
  für die aktuelle Sitzung.
- **Klick/Tipp auf einen Halt** zeigt Name und die dort verkehrenden Linien
- **Suchfeld** springt zu einem Halt (findet sowohl „Köln Hauptbahnhof" als
  auch „Köln Hbf")
- Haltestellennamen erscheinen gestaffelt beim Hineinzoomen: erst
  Knotenbahnhöfe, dann Halte mehrerer Linien, zuletzt alle übrigen

## Pipeline neu rechnen

Jede Phase ist ein eigenständiges Skript und schreibt ihren Zwischenstand als
JSON nach `data/`. Einzelne Phasen lassen sich dadurch wiederholen, ohne alles
neu zu rechnen. Aus dem Projektverzeichnis heraus aufrufen:

```bash
python3 scripts/01_inventory.py    # KML analysieren        -> data/01_inventory.json
python3 scripts/02_graph.py        # Netzgraph bauen        -> data/02_graph.json
python3 scripts/03_basemap.py      # Grenzen laden          -> data/03_basemap.json
python3 scripts/04_bundling.py     # Linien bündeln         -> data/04_bundled.json
python3 scripts/05a_textmasse.py   # Textbreiten messen     -> data/05a_textmasse.json
python3 scripts/05_layout.py       # Beschriftung platzieren-> data/05_layout.json
python3 scripts/06_build_map.py    # Karte bauen            -> netzkarte.html
```

Abhängigkeiten: `shapely`, `pyproj`, `geopandas`, für Phase 5a zusätzlich
`playwright` (alles nur für die Skripte, nicht für die fertige Karte).
Phase 5a ist optional — fehlt die Datei, schätzt Phase 5 die Textbreiten und
meldet das; die Karte entsteht trotzdem, nur mit etwas mehr Überlappung.

### Nützliche Zusatzaufrufe

```bash
# Bündelabstände auf einer bestimmten Kante nachprüfen
python3 scripts/04_bundling.py --debug-edge essen_hauptbahnhof essen_steele

# Testrender einzelner Linien, zur Kontrolle der Bündelung
python3 scripts/04b_test_render.py RE40 S10 S3 S30 --center "Essen-Steele" --span 200 --zoom 6

# Unabhängige geometrische Abstandsprüfung der fertigen Linien
python3 scripts/04c_pruefe_abstaende.py

# Und zu jedem Befund die Ursache (geteilte Kante? eigener Korridor? Knotenfächer?)
python3 scripts/04d_ursachen.py
```

Die Prüfung in Phase 4 vergleicht nur Linien, die sich eine Kante teilen.
`04c` misst dagegen rein geometrisch: Es tastet jede Linie alle 3 px ab und
meldet jeden Abschnitt über 25 px, auf dem zwei Linien einander näher als eine
Linienbreite kommen. `04d` klassifiziert diese Befunde nach Ursache.

## Aufbau der Phasen

**Phase 1 — Bestandsaufnahme.** Liest die KML und berichtet Placemark-Typen,
Liniennamen, Ordnerstruktur, Farben und Bounding Box.

**Phase 2 — Netzgraph.** Halte werden dedupliziert (Haversine < 150 m *und*
ähnlicher Name), auf die Liniengeometrie gesnappt und zu geordneten Sequenzen
sortiert. Ergebnis: 465 Halte, 523 Kanten, 31 Linien.

**Phase 3 — Kartengrundlage.** Natural Earth Admin-0 (1:50 m), auf Deutschland
und alle neun Nachbarländer gefiltert, auf die gepufferte Bounding Box
geclippt, nach **EPSG:3034** projiziert (Lambert-konform, ETRS89-LCC Europe)
und mit Douglas-Peucker vereinfacht.

Grenzen kommen aus eigenen Liniendatensätzen statt aus den Polygonrändern —
ein Polygonrand zeichnet auch die Küstenlinie als „Grenze". Staatsgrenzen aus
`admin_0_boundary_lines_land` (1:50 m), Verwaltungsgrenzen aus
`admin_1_states_provinces_lines` in **1:10 m**, weil die 1:50-m-Fassung nur
neun Großstaaten enthält und Deutschland dort fehlt. Frankreich bleibt bei den
Verwaltungsgrenzen außen vor: Es liegt in diesem Datensatz auf
Départements-Ebene (299 Segmente) und wäre für eine Netzkarte viel zu unruhig.

*Warum nicht Web Mercator:* Die Karte ist ein statisches SVG, kein
Kachel-Webmap — der einzige Vorteil von Mercator entfällt. Über die
9 Breitengrade des Netzes (47°–56° N) wäre der Nordrand rund 20 % stärker
gestreckt als der Südrand, wodurch die in Pixeln berechneten Bündelabstände je
nach Kartenposition unterschiedlich breit wirken würden.

**Phase 4 — Bündelung.** Der kritische Teil. Fünf Kernpunkte:

1. *Gemeinsame Kantengeometrie.* Pro Kante wird **eine** kanonische Polylinie
   gewählt (die detaillierteste der beteiligten Linien). Behielte jede Linie
   ihre eigene KML-Geometrie, würden die Bahnen des Bündels sichtbar
   auseinanderdriften.
2. *Propagierte Kantenorientierung.* Slots werden in der Orientierung einer
   Kante vergeben; befährt eine Linie sie rückwärts, wird das Vorzeichen
   gespiegelt. Entscheidend ist, dass die Orientierung **entlang der Korridore
   propagiert** wird und nicht willkürlich (etwa alphabetisch) festliegt: Sonst
   spiegelt sich das gesamte Bündel an jedem Knoten, an dem die Orientierung
   gegen die Fahrtrichtung kippt — die Linien tauschen dort ihre Seite, obwohl
   sie weiter parallel verlaufen. Stark befahrene Kanten werden zuerst
   orientiert, damit die in Ringen unvermeidbaren Konflikte auf Nebenkanten
   landen. Messbar: **124 → 0** Seitenwechsel bei 192 geprüften Übergängen.
3. *Stabile Spuren.* Alle Linien werden einmal global sortiert; auf jeder
   Kante ordnen sich die dort verkehrenden Linien nach diesem Rang. Die Slots
   werden dabei **nicht** je Kante neu auf die Streckenmitte zentriert — sonst
   rücken alle Linien eines Bündels seitwärts, sobald irgendwo eine Linie
   dazukommt oder abzweigt, obwohl sie unverändert parallel weiterlaufen.
   Stattdessen behält jede Linie ihre Spur, und eine Kante wird nur so weit
   verschoben, dass möglichst viele gemeinsame Linien darauf stehenbleiben.
   Das senkte die Zahl der Spurwechsel von 109 auf 14.
4. *Spurwechsel nur am Bahnhof.* Wo eine Linie die Spur wechselt, geschieht
   das als kurze Rampe unmittelbar am Knoten — dort verdeckt sie der weiße
   Haltemarker, wie auf gedruckten Verkehrskarten. Die Rampe wird an den
   echten Kantengrenzen gemessen (nicht an den Abschnitten gleichen Slots, die
   sich über mehrere Kanten erstrecken können) und auf 22 % je Seite begrenzt,
   damit sie nie auf freie Strecke reicht.
5. *Durchfahrt-Knoten.* Ein Express hält nicht an allen Halten seiner Strecke
   und hätte dadurch völlig andere Kanten als der Regionalzug daneben — RE35X
   teilte mit RE35 nur 5 von 24 Kanten, beide lagen deshalb übereinander statt
   nebeneinander. Halte dicht an der Strecke einer Linie, an denen sie nicht
   hält, werden als reine Geometrieknoten in ihren Weg eingefügt; gezeichnet
   wird dort kein Bahnhof. Danach liegen RE35 und RE35X exakt 5,20 px
   auseinander.

Vereinfachen (Douglas-Peucker) vor, Glätten (Chaikin) nach dem Versatz.

**Das Skript prüft sein eigenes Ergebnis** und meldet für jede Ansicht:
Seitenwechsel parallel laufender Linien, größten Seitenversatz und den
kleinsten Abstand zweier Linien auf freier Strecke. Aktueller Stand: null
Seitenwechsel bei 192 bzw. 86 geprüften Übergängen, und der kleinste Abstand
zweier Linien beträgt auf beiden Seiten exakt 5,20 px — den vollen
Spurabstand bei 4 px Linienbreite, also nirgends eine Überlappung.

**Phase 5a — Textbreiten messen.** Rendert alle Haltenamen einmal echt im
Browser und misst sie mit `getComputedTextLength`. Eine Schätzung aus
Buchstabenbreiten liegt je nach Name einige Prozent daneben — genug, dass sich
Beschriftungen am Ende doch überlappen.

**Phase 5 — Darstellung.** Einstufung der Halte, kollisionsfreie Platzierung
der Namen (acht Himmelsrichtungen in vier Entfernungsstufen, weiter außen mit
Bezugslinie), Liniennummern-Badges, Legendeneinträge. Halte ohne Platz würden
auf der Konsole protokolliert statt überlappend gezeichnet — aktuell sitzen
alle 420 bzw. 149 Namen.

Zwei Kürzungen der Beschriftung, beide von Verkehrskarten übernommen:
„Hauptbahnhof" wird immer zu „Hbf", und Stadtteilbahnhöfe großer Städte
bekommen das Kürzel der Deutschen Bahn — „Düsseldorf-Bilk" wird zu „D-Bilk",
„Berlin-Spandau" zu „B-Spandau", „Bochum-Riemke" zu „BO-Riemke". Das betrifft
111 der 465 Halte und entlastet vor allem das Ruhrgebiet. Nicht gekürzt werden
der Hauptbahnhof selbst und Namen mit Klammerzusatz: „Frankfurt (Oder)" und
„Essen (Oldb)" sind eigene Städte, keine Stadtteile.

**Phase 6 — Interaktion.** Baut die fertige HTML-Datei mit eingebettetem SVG,
CSS und JavaScript. Kein localStorage.

Farben liegen als CSS-Variablen vor: jede Linie trägt ihre Hell- und
Dunkelfassung als `--c`/`--cd` im `style`-Attribut, das Umschalten ist dadurch
reines CSS. Ein Drittel der Liniennummern hat eine Helligkeit unter 0,45
(reines Blau liegt bei 0,11) und wäre auf dunklem Grund kaum zu erkennen —
für den Dunkelmodus wird deshalb über HSL die Helligkeit angehoben und die
Sättigung gedeckelt, der Farbton bleibt erhalten.

`color-scheme: light dark` ist wichtig: Ohne diese Angabe invertieren Browser
wie Brave die Seite selbsttätig und machen dabei die weißen Text-Halos der
Haltenamen unbrauchbar (weiße Schrift auf weißem Halo).

## Zwei Kartenseiten

Im Ruhrgebiet liegen die Halte im Netzmaßstab nur rund 7 px auseinander —
lesbare Beschriftung ist dort unmöglich. **Nordrhein-Westfalen** bekommt
deshalb eine eigene zweite Kartenseite: 149 Halte, 13 Linien, dreifacher
Maßstab (14,3 statt 4,8 px/km). Die Landesfläche kommt aus Natural Earth
Admin-1, die Halte werden per Punkt-in-Polygon-Test mit 9 km Puffer
ausgewählt. Die drei S-Bahn-Linien erscheinen ausschließlich hier. Auf der
Hauptkarte markiert ein gestricheltes, anklickbares Rechteck den Bereich.

*Grenze des Machbaren:* NRW ist 245 km breit, im Ruhrgebiet stehen die
Bahnhöfe 2 km auseinander. Beides gleichzeitig lesbar auf einen Bildschirm zu
bringen, geht rechnerisch nicht — bei einer Zeichenfläche, auf der alle Namen
kollisionsfrei Platz haben (3900 px), sind sie in der Gesamtansicht zu klein.
Die Seite zeigt deshalb zunächst die Netzstruktur; die Namen erscheinen beim
Hineinzoomen, dann aber überlappungsfrei.

Umgeschaltet wird über die Reiter in der Seitenleiste, den ⇄-Knopf oder einen
Klick auf das gestrichelte Rechteck. Jede Seite hat ihren eigenen Zoomzustand.
Die Suche wechselt bei Bedarf selbsttätig auf die Seite, die den gesuchten
Halt enthält.

Die Slot-Vergabe erfolgt **pro Ansicht**: Blendet die Hauptkarte die S-Bahnen
aus, dürfen deren Slots keine Lücken im RE-Bündel hinterlassen — die
verbleibenden Linien rücken zusammen und werden neu zentriert.

## Anmerkungen zu den Quelldaten

- **Zwei verschiedene Linien heißen RE17** (Dortmund–Wilhelmshaven und
  Østerport–Rostock). Als stabile Linien-ID dient deshalb die `styleUrl`, nicht
  die Liniennummer.
- **Korrigierte Koordinatenfehler.** Fünf Halte lagen in der Quell-KML an der
  falschen Stelle; alle fünf sind in `data/input/RENetz_2030_v3.kml` korrigiert:

  | Halt | KML | korrigiert | Fehler |
  |---|---|---|---|
  | Koblenz Hauptbahnhof | 7.8835 / 49.9688 | 7.5919 / 50.3606 | hatte exakt die Koordinaten von Bingen |
  | Essen-Horst | 6.9893 / 51.4375 | 7.1028 / 51.4312 | 8 km zu weit westlich |
  | Essen West | 7.0886 / 51.4442 | 6.9800 / 51.4542 | 7 km zu weit östlich, mitten im Steele-Korridor |
  | Bredstedt | 9.8242 / 53.9903 | 8.9699 / 54.6212 | 90 km zu weit südöstlich |
  | Dülken | 6.0145 / 51.9434 | 6.3363 / 51.2530 | lag in den Niederlanden bei Nijmegen |

  Phase 2 sucht solche Fälle inzwischen selbst: Ist der Weg über einen Halt
  mehr als `UMWEG_FAKTOR` mal so lang wie die Luftlinie seiner beiden Nachbarn,
  wird er als Verdachtsfall gemeldet.

- **Zurückgespulte Linienzüge.** Mehrere LineStrings befahren denselben
  Abschnitt mehrfach hin und zurück — die RE5 fährt die Rheinstrecke
  Koblenz–Bingen dreimal, die RB37 verdoppelt fast ihre halbe Länge. Solche
  Doppelungen legen die Linie zwangsläufig auf sich selbst und auf ihre
  Nachbarn; kein Bündelungsalgorithmus kann das nachträglich trennen.
  `kml_common.entwirre_segment()` entfernt sie beim Einlesen — aber nur, wenn
  die verbleibende Geometrie den entfernten Teil ohnehin abdeckt. Echte
  Schleifen wie die Achterschleife der S10 bleiben dadurch erhalten.

- **Rechtwinklige Platzhalter.** In den drei S-Bahn-Linien stecken im Raum
  Essen/Bochum 17 Stützpunkte auf glatten 0,01-Grad-Koordinaten, die
  kastenförmige Umwege quer durch die Nachbarlinien beschreiben. Sie werden
  beim Einlesen verworfen (`entferne_rasterpunkte`); echte Trassenpunkte
  treffen dieses Raster praktisch nie — 17 von 18811 im gesamten Netz.

- **Unbrauchbare Kantentrassen.** Legt die Trasse zwischen zwei benachbarten
  Halten mehr als das 2,5-fache der Luftlinie zurück (S3/S30 fahren zwischen
  Essen-Steele Ost und Essen-Horst 13,5 km für 1,6 km Luftlinie), verbindet
  Phase 4 die beiden Halte direkt.
- Halte liegen **nicht** exakt auf den Stützpunkten der LineStrings; sie werden
  per linearem Referenzieren auf die Strecke projiziert.
- Die Reihenfolge der Halte entlang einer Linie stammt aus der Geometrie, die
  Zuordnung Halt→Linie aus der `<description>` jedes Halte-Placemarks.

## Verzeichnisse

```
data/input/     Quell-KML (mit korrigierten Koordinaten) und NRW-Referenz-PDF
data/           Zwischenstände der Phasen als JSON
data/naturalearth/  Heruntergeladene Natural-Earth-Daten
scripts/        Die Phasen-Skripte und das gemeinsame Modul kml_common.py
netzkarte.html  Das Endprodukt
```
