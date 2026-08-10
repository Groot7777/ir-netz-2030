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
```

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
2. *Kanonische Richtung.* Slots werden entlang einer festen Kantenrichtung
   vergeben; befährt eine Linie die Kante rückwärts, wird ihr Slot-Vorzeichen
   gespiegelt. Dadurch liegen alle Linien physisch an derselben Stelle,
   unabhängig von der Fahrtrichtung.
3. *Globale Slot-Reihenfolge.* Alle Linien werden einmal global sortiert; auf
   jeder Kante ordnen sich die dort verkehrenden Linien nach diesem Rang.
   Slots verschieben sich nur dort, wo Linien dazukommen oder abzweigen.
4. *Längenadaptive Slot-Rampen.* Ein Slot-Wechsel wird als Rampe ausgeführt,
   deren Länge sich nach den angrenzenden Kanten richtet (höchstens 45 % je
   Seite). Ein festes Glättungsfenster hatte die Slots im dichten Ruhrgebiet
   über mehrere Kanten hinweg auf null verschmiert — das Bündel lief dann
   deckungsgleich statt parallel.
5. *Durchfahrt-Knoten.* Ein Express hält nicht an allen Halten seiner Strecke
   und hätte dadurch völlig andere Kanten als der Regionalzug daneben — RE35X
   teilte mit RE35 nur 5 von 24 Kanten, beide lagen deshalb übereinander statt
   nebeneinander. Halte dicht an der Strecke einer Linie, an denen sie nicht
   hält, werden als reine Geometrieknoten in ihren Weg eingefügt; gezeichnet
   wird dort kein Bahnhof. Danach liegen RE35 und RE35X exakt 5,20 px
   auseinander.

Vereinfachen (Douglas-Peucker) vor, Glätten (Chaikin) nach dem Versatz. Die
Länge eines Slot-Wechsels ist in Kilometern angegeben, nicht in Pixeln: Die
beiden Kartenseiten haben sehr verschiedene Maßstäbe (4,8 gegenüber 19 px/km),
und ein fester Pixelwert ließe die Linien auf der Ruhrgebietsseite dauerhaft
weben statt kurz zu versetzen.

**Phase 5a — Textbreiten messen.** Rendert alle Haltenamen einmal echt im
Browser und misst sie mit `getComputedTextLength`. Eine Schätzung aus
Buchstabenbreiten liegt je nach Name einige Prozent daneben — genug, dass sich
Beschriftungen am Ende doch überlappen.

**Phase 5 — Darstellung.** Einstufung der Halte, kollisionsfreie Platzierung
der Namen (acht Himmelsrichtungen in vier Entfernungsstufen, weiter außen mit
Bezugslinie), Liniennummern-Badges, Legendeneinträge. Halte ohne Platz werden
auf der Konsole protokolliert statt überlappend gezeichnet — aktuell ist das
genau einer (Berlin-Ostkreuz).

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
lesbare Beschriftung ist dort unmöglich. Die drei S-Bahn-Linien liegen deshalb
auf einer **eigenen zweiten Kartenseite**, die den Ballungsraum
bildschirmfüllend und rund viermal so groß zeigt (19 statt 4,8 px/km). Dort
sind alle 74 Haltenamen kollisionsfrei untergebracht. Auf der Hauptkarte
markiert ein gestricheltes, anklickbares Rechteck den Bereich.

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
- **Korrigierter Koordinatenfehler:** `Koblenz Hauptbahnhof` hatte in der
  Quell-KML exakt die Koordinaten von `Bingen (Rhein) Hbf`. Korrigiert in
  `data/input/RENetz_2030_v3.kml` auf 7.5919 / 50.3606.
- Halte liegen **nicht** exakt auf den Stützpunkten der LineStrings; sie werden
  per linearem Referenzieren auf die Strecke projiziert.
- Die Reihenfolge der Halte entlang einer Linie stammt aus der Geometrie, die
  Zuordnung Halt→Linie aus der `<description>` jedes Halte-Placemarks.

## Verzeichnisse

```
data/input/     Quell-KML (mit korrigierter Koblenz-Koordinate) und NRW-Referenz-PDF
data/           Zwischenstände der Phasen als JSON
data/naturalearth/  Heruntergeladene Natural-Earth-Daten
scripts/        Die Phasen-Skripte und das gemeinsame Modul kml_common.py
netzkarte.html  Das Endprodukt
```
