Quadrant 2076 – Fahrplanauskunft (Stufe 1 + 2)
=============================================

Aufbau
  index.html   die Seite (gleiches Aussehen wie die RE-Netz-2030-Auskunft)
  data/        alle Fahrplandaten als JSON (werden beim Öffnen nachgeladen, ca. 10 MB, übertragen ca. 2,5 MB)

Auf GitHub Pages stellen
  1. Ordner "index.html" + "data" in ein Repository kopieren (z. B. in einen Unterordner "quadrant-2076/").
  2. Pages aktivieren. Die Seite lädt die Daten selbst nach (Ladezeit je nach Handy 1–5 Sekunden).
  Hinweis: Die Seite muss über einen Webserver laufen. Als lokale Datei (file://) kann der Browser
  data/*.json nicht laden; dann erscheint eine Fehlermeldung.

Enthalten
  RE/RB/S/IR   alle 68 Richtungen der RE-Netz-2030-Auskunft + S2, S4, IR1–IR4
  Maglev 700   alle 19 Linien (Variante "mit Trägheitsdämpfer")
  Erde_2026    Maglev- und Vactrain-Linien
  Hochbahn     Maglev XF (Fernnetz), XE (Express)
  Metro        Raster, Ringe und Sterne der 10 Großstädte
  Metro-Außenlinien  7.712 Außenlinien (MA) und 764 Bahnhof-Zubringer (MB) der 32 Metropolen
  MetroX       5.892 Direktlinien (MD) und die MetroX-Variante aller Metro-Linien (Stadtnetze und Außenlinien)
  Zusammen etwa 22.000 Linien und 54.000 Haltestellen.

Annahmen
  - Takt 24/7. Musterzug 07:00 wird mit Tag- und Nachttakt fortgesetzt:
      Metro (Stadtnetze) 2 Min (05–23 Uhr), nachts 5/10 Min · XF 5 Min, nachts 10 · XE 10 Min, nachts 20
      Metro-Außenlinien und Zubringer 5 Min (05–23 Uhr), nachts 10 · MetroX 5 Min, nachts 10
      MetroX-Direktlinien 10 Min (05–23 Uhr), nachts 20 (nur der Tagtakt steht in den Quelldateien)
      IR stündlich, nachts alle 2 Std. · S2/S4 15 Min (06–21 Uhr), sonst 30 Min
      Maglev 700 Fernmagistralen 60 Min (CCS 120, LB/WBC/ML 30, Hub-Netzlinien 5) · Erde_2026 30 Min
    Die Original-RE/S-Linien behalten ihren Takt aus der Original-Seite.
  - Umstiege: Haltestellen mit gleichem Bahnhof (Bahnhofsspalte, höchstens 500 m) sind per Fußweg
    verbunden; gleiche Bahnhofsnamen ebenfalls. "Nur Direktverbindungen" schaltet Fußwege ab.
  - Quadrant-Netze haben keine Kosten: Verbindungen mit Maglev/Metro/MetroX/Erde zeigen "kostenlos".
  - Uhrzeiten bei Linien über mehrere Zeitzonen: Bezugszeit MEZ (Nordamerika: PT), wie in den PDFs.
  - Fahrzeiten sind auf ganze Minuten gerundet.

Bekannte Lücke in den Quelldaten
  Sieben kleine Teilnetze (zusammen 327 Halte, z. B. um Bonn-Todenfeld und Bielefeld-Rheda-Wiedenbrück)
  hängen in den Quelldateien an keiner anderen Linie und keinem Bahnhof. Von dort gibt es keine Verbindung ins restliche Netz.
