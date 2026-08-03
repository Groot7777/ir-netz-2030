# -*- coding: utf-8 -*-
"""
Strukturierte Rohdaten der 5 neuen Linien, transkribiert aus den Master-Plan-PDFs.
Alle Zeiten sind bereits vollstaendig aufgeloest (beide Richtungen), damit das
Build-Skript keine Merge-/Mirror-Logik mehr braucht.

Stationsnamen hier sind ASCII-stabile Dictionary-Keys (siehe display_names.py fuer
die korrekten Anzeigenamen mit Umlauten/Diakritika).

Format eines Stops (Standardlinien, nicht Ring):
  (key, hin_an, hin_ab, rueck_an, rueck_ab, info)
  an/ab = "HH:MM" (absolute Beispielzeit UND Basis fuer Takt xx:MM) oder None am Linienende.

Wo im Original-PDF nur eine Richtung mit echten Uhrzeiten vorlag (RE71 Brandenburg-Hel;
RE30-Fluegelaeste in Rueckrichtung), wurde die Gegenrichtung durch Spiegelung der
Fahrzeit-/Aufenthaltsdauern hergeleitet (gleiche Dauer, umgekehrte Reihenfolge, siehe
Kommentare) - wie mit dem Nutzer abgestimmt ("Minutenwerte spiegeln").
"""

# ---------------------------------------------------------------------------
# LINIE RE71: Brandenburg Hbf - Hel (Korridor Brandenburg-Berlin-Polen)
# ---------------------------------------------------------------------------
# Richtung B (Brandenburg->Hel) = Original aus PDF (echte Uhrzeiten).
# Richtung Hel->Brandenburg = gespiegelt (gleiche Fahrzeiten/Aufenthalte, umgekehrte
# Reihenfolge, verankert an einer symbolischen Startzeit Hel ab 00:00; nur die
# Minute zaehlt fuer die Takt-Anzeige "xx:MM"). Kupplung/Fluegelung in Gdynia
# Glowna aendert den Fahrweg NICHT (kein eigener Ast noetig).

RE71_STOPS = [
    # key, hin_an, hin_ab, rueck_an, rueck_ab, info
    ("Brandenburg Hbf", None, "07:00", "09:14", None, "Taktstart als 5+3-Gesamtverband aus der Abstellung (278m Nutzlänge)"),
    ("Potsdam Hbf", "07:20", "07:22", "08:52", "08:54", "Regionalbahnsteige Gleis 6/7, Landeshauptstadt-Knoten (296m)"),
    ("Berlin-Wannsee", "07:30", "07:32", "08:42", "08:44", "Gleis 5/6, reichlich Puffer (340m)"),
    ("Berlin Hbf tief", "07:47", "07:53", "08:21", "08:27", "Kreuzungsfreie Durchfahrt ohne Kopfmachen, Gleis 1-8 (430m)"),
    ("Berlin Potsdamer Platz", "07:57", "07:59", "08:15", "08:17", "Nord-Süd-Tunnel, absolute Systemgrenze 210m"),
    ("Flughafen BER", "08:19", "08:22", "07:52", "07:55", "Aussenring-Zulauf, Fernbahngleise (405m)"),
    ("Bernau b Berlin", "08:52", "08:54", "07:20", "07:22", "Gleis 4/5, Punktlandung 211m"),
    ("Eberswalde Hbf", "09:08", "09:10", "07:04", "07:06", "Sichere Nutzlängen (294-330m)"),
    ("Angermuende", "09:23", "09:25", "06:49", "06:51", "Gleis 1/2, komfortabler Anschlussknoten (302m)"),
    ("Pasewalk", "10:00", "10:07", "06:07", "06:14", "Richtungswechsel: 7 Min Kopfmachen auf Grenzbahn nach Stettin (284/312m)"),
    ("Szczecin Glowny", "10:37", "10:42", "05:32", "05:37", "Polnischer Endknoten, Systemwechsel 15kV AC/3kV DC (>250m)"),
    ("Runowo Pomorskie", "11:12", "11:13", "05:01", "05:02", "Abzweig Ostbahn-Korridor, Punktlandung 210m (245/210m)"),
    ("Szczecinek", "11:53", "11:55", "04:19", "04:21", "Regionaler Knotenbahnhof (302/263m)"),
    ("Chojnice", "12:30", "12:32", "03:42", "03:44", "Peron 2 (198m) fällt durch, nur Peron 1/4 (284/225m)"),
    ("Starogard Gdanski", "13:12", "13:13", "03:01", "03:02", "Engpass: Peron 2 zu kurz (202m), bevorzugt Gleis 1 (215/202m)"),
    ("Tczew", "13:28", "13:36", "02:38", "02:46", "Richtungswechsel: 8 Min Kopfmachen auf Hauptstrecke 9 Richtung Danzig (300-380m)"),
    ("Gdansk Glowny", "13:56", "13:59", "02:15", "02:18", "Metropolen-Hauptknoten, Fernbahnsteige (300-420m)"),
    ("Gdansk Wrzeszcz", "14:05", "14:07", "02:07", "02:09", "Wichtiger Nahverkehrsknoten (300-420m)"),
    ("Gdansk Zaspa", "14:10", "14:11", "02:03", "02:04", "Engpass: SKM-Pendlerhalt, Nutzlänge nur 200m für 210m-Zug"),
    ("Gdynia Wzgorze Sw Maksyma", "14:23", "14:24", "01:50", "01:51", "Engpass: Regionalbahnsteige nur 200m, SDO-Einsatz"),
    ("Gdynia Glowna", "14:27", "14:40", "01:34", "01:47", "Flügelung: 13 Min Halt, 3-Teiler fährt weiter nach Hel, 5-Teiler bleibt in Gdynia (>300m)"),
    ("Gdynia Chylonia", "14:46", "14:47", "01:27", "01:28", "Ab hier grosser Puffer für Solo-3-Teiler (150-205m)"),
    ("Rumia Janowo", "14:51", "14:52", "01:20", "01:21", "Halt unkritisch (150-205m)"),
    ("Rumia", "14:55", "14:56", "01:16", "01:17", "Halt unkritisch (150-205m)"),
    ("Reda", "15:00", "15:02", "01:10", "01:12", "Abzweig auf eingleisige Stichstrecke Richtung Hel (150-205m)"),
    ("Mrzezino", "15:09", "15:10", "01:05", "01:06", "Halt unkritisch (150-205m)"),
    ("Zelistrzewo", "15:15", "15:16", "00:57", "00:58", "Halt unkritisch (150-205m)"),
    ("Puck", "15:21", "15:22", "00:51", "00:52", "Halt unkritisch (150-205m)"),
    ("Swarzewo", "15:27", "15:28", "00:45", "00:46", "Halt unkritisch (150-205m)"),
    ("Wladyslawowo", "15:33", "15:35", "00:38", "00:40", "Wichtiger regionaler Knotenpunkt auf der Halbinsel (150-205m)"),
    ("Wladyslawowo Port", "15:38", "15:39", "00:34", "00:35", "Halt unkritisch (150-205m)"),
    ("Chalupy", "15:44", "15:45", "00:28", "00:29", "Halt unkritisch (150-205m)"),
    ("Kuznica", "15:51", "15:52", "00:21", "00:22", "Halt unkritisch (150-205m)"),
    ("Jastarnia", "15:59", "16:00", "00:13", "00:14", "Halt unkritisch (150-205m)"),
    ("Jurata", "16:05", "16:06", "00:07", "00:08", "Halt unkritisch (150-205m)"),
    ("Hel", "16:13", None, None, "00:00", "Linien-Endpunkt: Übergang in Abstellung (150-205m)"),
]

RE71 = {
    "number": "RE71",
    "route_name": "Brandenburg Hbf-Hel",
    "description": "Transnationaler Langlauf-Korridor Brandenburg-Berlin-Polen. Flügelungskonzept 5+3: Gdynia Główna-Brandenburg Hbf als 8-teiliger KISS-Verband (~210m), Gdynia Główna-Hel als Solo-3-Teiler (~80m). Kreuzungsfreie Durchfahrt Berlin Hbf (tief) ohne Kopfmachen, dafür Richtungswechsel in Pasewalk und Tczew. Rückfahrplan aus Fahrzeiten der Hinfahrt gespiegelt.",
    "kind": "linear",
    "branches": [
        {"branch_id": "main", "stops": RE71_STOPS, "line_label": "RE71"},
    ],
}

# ---------------------------------------------------------------------------
# LINIE S10: Ringbahn Ruhrgebiet (Achterschleife, Innenring/Aussenring)
# ---------------------------------------------------------------------------
# Physischer Ring in Achterschleifen-Form: Bochum Hbf, Bochum-Langendreer und
# Bochum-Langendreer West werden JE ZWEIMAL pro Umlauf durchfahren (Kreuzungspunkte
# der Acht). Kanonische Reihenfolge = Innenring (im Uhrzeigersinn); Aussenring ist
# exakt die umgekehrte Stationsfolge (gegen den Uhrzeigersinn), selbe Gleise.
# Format: (key, innen_an, innen_ab, innen_gleis, aussen_an, aussen_ab, aussen_gleis, info)

S10_RING = [
    ("Unna Hbf", None, "07:00", None, None, "09:42", None, "Zentraler Netzknoten und Abstellbahnhof"),
    ("Unna West", "07:02", "07:02", None, "09:40", "09:40", None, "Zulauf Strecke Dortmund-Soest"),
    ("Massen", "07:05", "07:05", None, "09:37", "09:37", None, "Bahnstrecke Welver-Sterkrade"),
    ("Dortmund-Wickede", "07:08", "07:08", None, "09:34", "09:34", None, "Bahnstrecke Welver-Sterkrade"),
    ("Dortmund-Brackel", "07:11", "07:11", None, "09:31", "09:31", None, "Bahnstrecke Welver-Sterkrade"),
    ("Dortmund Hauptbahnhof", "07:16", "07:18", None, "09:24", "09:26", None, "Einführung via fiktivem S-Bahn-Tunnel ab Brackel"),
    ("Dortmund-Dorstfeld", "07:21", "07:21", None, "09:21", "09:21", None, "S1-Stammstrecke"),
    ("Dortmund-Dorstfeld Sued", "07:23", "07:23", None, "09:19", "09:19", None, "S1-Stammstrecke"),
    ("Dortmund-Universitaet", "07:25", "07:25", None, "09:17", "09:17", None, "S1-Stammstrecke"),
    ("Dortmund-Oespel", "07:27", "07:27", None, "09:15", "09:15", None, "S1-Stammstrecke"),
    ("Dortmund-Kley", "07:29", "07:29", None, "09:13", "09:13", None, "S1-Stammstrecke"),
    ("Bochum-Langendreer", "07:32", "07:32", None, "09:10", "09:10", None, "S1-Stammstrecke (1. Durchfahrt)"),
    ("Bochum-Langendreer West", "07:34", "07:34", None, "09:08", "09:08", None, "S1-Stammstrecke (1. Durchfahrt)"),
    ("Bochum Hauptbahnhof", "07:37", "07:39", "Gleis 2", "07:42", "07:44", "Gleis 7", "Doppelter Kreuzungspunkt der Achterschleife (1. Durchfahrt)"),
    ("Bochum-Bermuda3eck", "07:41", "07:42", None, "09:00", "09:01", None, "Neuer Hochbahnhof auf verbreitertem Viadukt"),
    ("Bochum West", "07:44", "07:44", None, "08:58", "08:58", None, "Bahnstrecke Bochum-Gelsenkirchen (RB46)"),
    ("Bochum-Hamme", "07:46", "07:46", None, "08:56", "08:56", None, "Bahnstrecke Bochum-Gelsenkirchen (RB46)"),
    ("Bochum-Riemke", "07:49", "07:49", None, "08:53", "08:53", None, "Bahnstrecke Bochum-Gelsenkirchen (RB46)"),
    ("Wanne-Eickel Hbf", "07:53", "07:54", None, "08:47", "08:48", None, "Bahnstrecke Bochum-Gelsenkirchen (RB46)"),
    ("Gelsenkirchen Hbf", "07:58", "07:59", None, "08:42", "08:43", None, "Glückauf-Bahn Nullpunkt"),
    ("Gelsenkirchen-Zollverein Nord", "08:03", "08:03", None, "08:38", "08:38", None, "Köln-Mindener Emschertalbahn"),
    ("Essen-Altenessen", "08:06", "08:06", None, "08:35", "08:35", None, "Köln-Mindener Emschertalbahn"),
    ("Essen-Borbeck", "08:10", "08:10", None, "08:31", "08:31", None, "Köln-Mindener Emschertalbahn"),
    ("Essen-Dellwig Ost", "08:13", "08:13", None, "08:28", "08:28", None, "Köln-Mindener Emschertalbahn"),
    ("Oberhausen Hbf", "08:17", "08:18", None, "08:23", "08:24", None, "Westlicher Wendepunkt der Emscherschleife"),
    ("Muelheim-Styrum", "08:22", "08:22", None, "08:19", "08:19", None, "Hauptstrecke/S-Bahn-Gleise S1"),
    ("Muelheim West", "08:24", "08:24", None, "08:17", "08:17", None, "Hauptstrecke/S-Bahn-Gleise S1"),
    ("Muelheim Ruhr Hbf", "08:26", "08:27", None, "08:14", "08:15", None, "Hauptstrecke/S-Bahn-Gleise S1"),
    ("Essen-Frohnhausen", "08:30", "08:30", None, "08:11", "08:11", None, "Hauptstrecke/S-Bahn-Gleise S1"),
    ("Essen West", "08:32", "08:32", None, "08:09", "08:09", None, "Hauptstrecke/S-Bahn-Gleise S1"),
    ("Essen Hauptbahnhof", "08:35", "08:37", None, "08:04", "08:06", None, "S-Bahn-Stammstrecke"),
    ("Essen-Steele", "08:41", "08:41", None, "08:00", "08:00", None, "Bahnstrecke Witten/Dortmund-Oberhausen"),
    ("Essen-Steele Ost", "08:43", "08:43", None, "07:58", "07:58", None, "Bahnstrecke Witten/Dortmund-Oberhausen"),
    ("Essen-Eiberg", "08:46", "08:46", None, "07:55", "07:55", None, "Bahnstrecke Witten/Dortmund-Oberhausen"),
    ("Bochum-Hoentrop", "08:48", "08:48", None, "07:53", "07:53", None, "Bahnstrecke Witten/Dortmund-Oberhausen"),
    ("Bochum-Kohlenstrasse", "08:51", "08:51", None, "07:50", "07:50", None, "Neuer Dammbahnhof an S1-Bestandstrasse"),
    ("Bochum-Stahlhausen", "08:54", "08:54", None, "07:47", "07:47", None, "Neuer S-Bahn-Halt an S1-Bestandstrasse"),
    ("Bochum Hauptbahnhof", "08:57", "08:59", "Gleis 8", "09:03", "09:05", "Gleis 2", "Doppelter Kreuzungspunkt der Achterschleife (2. Durchfahrt)"),
    ("Bochum-Langendreer West", "09:02", "09:02", None, "09:08", "09:08", None, "S5-Trasse VzG 2140 (2. Durchfahrt)"),
    ("Bochum-Langendreer", "09:04", "09:04", None, "09:10", "09:10", None, "S5-Trasse VzG 2140 (2. Durchfahrt)"),
    ("Witten Hbf", "09:09", "09:10", None, "07:31", "07:32", None, "S5-Trasse VzG 2140"),
    ("Wengern", "09:15", "09:15", None, "07:26", "07:26", None, "Reaktivierte, zweigleisige Ruhrtalbahn-Achse"),
    ("Hagen-Vorhalle", "09:19", "09:19", None, "07:22", "07:22", None, "Hagen Hbf Bypass über Güterzug-Verbindungskurve"),
    ("Schwerte Ruhr", "09:27", "09:28", None, "07:13", "07:14", None, "Ruhrtalbahn/Obere Ruhrtalbahn"),
    ("Holzwickede", "09:35", "09:35", None, "07:06", "07:06", None, "Verbindungsstrecke Schwerte-Holzwickede"),
]

S10 = {
    "number": "S10",
    "route_name": "Ringbahn Ruhrgebiet",
    "description": "Kontinuierlich kreisende Achterschleife (24/7-Betrieb) durch das Kernrevier. Stadler FLIRT 3 XL in Doppeltraktion, ETCS Level 2, Zugfolgezeit unter 3 Minuten. Glückauf-Bahn und Ruhrtal-Achse zweigleisig ausgebaut, Hagen Hbf wird über Bypass in Hagen-Vorhalle umgangen. Innenring (im Uhrzeigersinn) und Außenring (gegen den Uhrzeigersinn) nutzen dieselben Gleise; Bochum Hbf, Bochum-Langendreer und Bochum-Langendreer West werden als Kreuzungspunkte der Achterschleife je zweimal pro Umlauf durchfahren.",
    "kind": "ring",
    "branches": [
        {"branch_id": "main", "stops": S10_RING, "line_label": "S10"},
    ],
}

# ---------------------------------------------------------------------------
# LINIEN S3 / S30: Ruhr-Volme-Netz (Fluegelzug in Hattingen)
# ---------------------------------------------------------------------------
# S3 und S30 sind KEIN gekuppelter/geflügelter Einzelzug, sondern zwei eigene
# Linien mit eigenem 15-Minuten-Takt-Offset auf der Stammstrecke (S30 ab :00,
# S3 ab :15). Beide Aeste bekommen daher ihre komplette eigene Stop-Zeitliste
# inkl. Stammstrecken-Anteil.

S3_STOPS = [
    # Ast A / Linie S3 Essen Hbf - Hattingen Mitte. Hin=4.2, Rueck=5.2 aus PDF.
    ("Essen Hauptbahnhof", None, "07:15", "07:37", None, "Start Stammstrecke VzG 2165"),
    ("Essen-Steele", "07:19", "07:19", "07:33", "07:33", "S-Bahn-Stammstrecke"),
    ("Essen-Steele Ost", "07:21", "07:22", "07:30", "07:31", "Trennungsbahnhof, Ausfädelung von S1/S10"),
    ("Essen-Horst", "07:25", "07:25", "07:27", "07:27", "Strecke nach Hattingen"),
    ("Bochum-Dahlhausen", "07:29", "07:30", "07:22", "07:23", "Liegt auf Bochumer Stadtgebiet"),
    ("Hattingen Ruhr", "07:33", "07:34", "07:18", "07:19", "Gabelungspunkt Ast A/Ast B"),
    ("Hattingen Mitte", "07:37", None, None, "07:15", "City-Tunnelbahnhof, Endpunkt Kurzläufer"),
]

S30_STOPS = [
    # Ast B / Linie S30 Essen Hbf - Luedenscheid Hbf. Hin=4.1, Rueck=5.1 aus PDF.
    ("Essen Hauptbahnhof", None, "07:00", "08:30", None, "Start Stammstrecke VzG 2165"),
    ("Essen-Steele", "07:04", "07:04", "08:26", "08:26", "S-Bahn-Stammstrecke"),
    ("Essen-Steele Ost", "07:06", "07:07", "08:23", "08:24", "Trennungsbahnhof, Ausfädelung von S1/S10"),
    ("Essen-Horst", "07:10", "07:10", "08:20", "08:20", "Strecke nach Hattingen"),
    ("Bochum-Dahlhausen", "07:14", "07:15", "08:15", "08:16", "Liegt auf Bochumer Stadtgebiet"),
    ("Hattingen Ruhr", "07:18", "07:19", "08:11", "08:12", "Gabelungspunkt Ast A/Ast B"),
    ("Heinrichshuette", "07:21", "07:21", "08:08", "08:08", "Beginn Mittlere Ruhrtalbahn VzG 2400"),
    ("Blankenstein Burg", "07:24", "07:24", "08:05", "08:05", "Reaktivierter Halt unterhalb der Burgruine"),
    ("Haus Kemnade", "07:27", "07:27", "08:02", "08:02", "Kultur- und Freizeithalt am Kemnader See"),
    ("Herbede", "07:31", "07:32", "07:57", "07:58", "Ehem. Bahnhof Witten-Herbede"),
    ("Ruine Hardenstein", "07:35", "07:35", "07:53", "07:53", "Reaktivierter Ausflugshalt im Ruhrtal"),
    ("Zeche Nachtigall", "07:38", "07:38", "07:50", "07:50", "Industriekultur-Halt im Muttental"),
    ("Witten Bommern", "07:41", "07:42", "07:46", "07:47", "Ehem. Halt Witten-Bommern Süd"),
    ("Wengern Ost", "07:46", "07:46", "07:42", "07:42", "Ende Strecke 2400, Verknüpfung mit S10"),
    ("Hagen-Vorhalle", "07:51", "07:51", "07:37", "07:37", "Einfädelung in Personenbahnhof"),
    ("Hagen Hauptbahnhof", "07:55", "07:57", "07:31", "07:33", "Knotenpunkt, Einstieg Volmetalbahn"),
    ("Dahl", "08:05", "08:05", "07:21", "07:21", "Volmetalbahn VzG 2810"),
    ("Rummenohl", "08:10", "08:10", "07:16", "07:16", "Volmetalbahn VzG 2810"),
    ("Dahlerbrueck", "08:14", "08:14", "07:12", "07:12", "Volmetalbahn VzG 2810"),
    ("Schalksmuehle", "08:18", "08:19", "07:07", "07:08", "Volmetalbahn VzG 2810"),
    ("Luedenscheid Hbf", "08:26", None, None, "07:00", "Endpunkt via fiktiver Tunnelkurve mit Tunnelbauwerk"),
]

# S3 und S30 sind ZWEI EIGENSTAENDIGE Linien (kein gekuppelter Fluegelzug, siehe oben),
# daher als zwei separate Line-Eintraege modelliert (kind="linear", je 1 Branch, eigene
# Placemarks/Farbe) statt als ein MultiGeometry-Fluegelzug-Paar.
S3 = {
    "number": "S3",
    "route_name": "Essen Hbf-Hattingen Mitte",
    "description": "Stadler FLIRT 3 XL in Doppeltraktion, ETCS Level 2. Kurzläufer der Stammstrecke Essen Hbf-Hattingen (Ruhr), Endpunkt im neuen City-Tunnelbahnhof Hattingen Mitte. Verkehrt versetzt zur S30 im 15-Minuten-Takt auf der gemeinsamen Stammstrecke.",
    "kind": "linear",
    "branches": [
        {"branch_id": "main", "stops": S3_STOPS, "line_label": "S3"},
    ],
}

S30 = {
    "number": "S30",
    "route_name": "Essen Hbf-Lüdenscheid Hbf",
    "description": "Stadler FLIRT 3 XL in Doppeltraktion, ETCS Level 2. Langläufer der Stammstrecke Essen Hbf-Hattingen (Ruhr), weiter über die reaktivierte Mittlere Ruhrtalbahn (Blankenstein Burg, Haus Kemnade, Ruine Hardenstein, Zeche Nachtigall) und die Volmetalbahn bis zum modernisierten Kopfbahnhof Lüdenscheid Hbf (fiktive Neubau-Tunnelkurve ab Schalksmühle).",
    "kind": "linear",
    "branches": [
        {"branch_id": "main", "stops": S30_STOPS, "line_label": "S30"},
    ],
}

# ---------------------------------------------------------------------------
# LINIE RE17: Oesterport - Rostock (transnational DK-DE)
# ---------------------------------------------------------------------------
# "Takt (04:04-20:04)"-Spalte liefert direkt xx:MM fuer beide Richtungen.
# Beispielzuglauf (echte Uhrzeiten) = Spalte F4 (einzige durchgehend gueltige,
# ohne Stabling-Abbruch): Nord->Sued Oesterport 03:04 -> Rostock 07:43;
# Sued->Nord Rostock 03:04 -> Oesterport 07:42.

RE17_STOPS = [
    # key, hin_an(F4), hin_ab(F4/Takt), rueck_an(F4), rueck_ab(F4/Takt), info
    #
    # Die 6 folgenden Stationen (Grossenbrode/Heiligenhafen bis Buetzow) stehen NICHT in der
    # Fahrplan-Tabelle der PDF (nur in der Infrastruktur-Beschreibung mit Adressen), wurden
    # aber auf Nutzerwunsch als echte Fahrgasthalte ergaenzt. Zeiten linear/proportional aus
    # den amtlichen Segment-Distanzen (Kapitel 1 der PDF) in die Zeitluecken der Original-
    # Tabelle interpoliert (siehe Kommentare je Segment).
    ("Oesterport", None, "03:04", "07:42", None, "Boulevardbanen TIB10, viergleisig, 25kV/50Hz AC, Takt ab xx:04"),
    ("Koebenhavn H", "03:16", "03:16", "07:34", "07:34", "Schnellfahrstrecke TIB6, bis 250 km/h, Takt xx:16/xx:34"),
    ("Ringsted", "03:47", "03:47", "07:01", "07:01", "Sydbanen TIB2, Takt xx:47/xx:01"),
    ("Nykoebing Falster", "04:37", "04:37", "06:11", "06:11", "Sydbanen, Takt xx:37/xx:11"),
    ("Roedby", "04:56", "04:56", "05:52", "05:52", "Vor Fehmarnbelttunnel-Neubaustrecke, Takt xx:56/xx:52"),
    # -- Segment Roedby-Luebeck (interpoliert aus VzG1120/1105/1100-Distanzen) --
    ("Grossenbrode Heiligenhafen", "05:17", "05:19", "05:31", "05:33", "Neubaustation an K42, Grenze Grossenbrode/Heiligenhafen, VzG1120"),
    ("Oldenburg in Holstein", "05:31", "05:33", "05:18", "05:20", "Bestand/Ausbau, Bahnhofstrasse 22, VzG1105"),
    ("Scharbeutz", "05:46", "05:48", "05:04", "05:06", "Neubaustation an A1 AS16 Scharbeutz, Bövelstredder"),
    ("Timmendorfer Strand Ratekau", "05:55", "05:57", "04:56", "04:58", "Neubaustation an L181/A1 AS17, Gemeindegebiet Ratekau"),
    ("Bad Schwartau", "06:06", "06:07", "04:46", "04:48", "Bestand/Ausbau, Am Bahnhof 1, Beton-Lärmschutztrog VzG1100"),
    ("Luebeck Hbf", "06:12", "06:12", "04:42", "04:42", "Ausbaustrecke Lübeck-Puttgarden, vor eingleisigem Nadelöhr, Takt xx:12/xx:42"),
    ("Bad Kleinen", "06:55", "06:55", "03:54", "03:54", "Batteriebetrieb endet/beginnt, Nachladung über Oberleitung VzG1123, Takt xx:55/xx:54"),
    # -- Segment Bad Kleinen-Rostock (interpoliert aus VzG1123/6446-Distanzen, Summe exakt 48 Min) --
    ("Buetzow", "07:18", "07:19", "03:29", "03:31", "Systemhalt VzG1123/6446, Ausweichgleis 2 (210m Nutzlänge)"),
    ("Rostock Hauptbahnhof", "07:43", None, None, "03:04", "Endknoten Hauptstrecke VzG6446, Takt an xx:43/ab xx:04"),
]

RE17 = {
    "number": "RE17",
    "route_name": "Østerport-Rostock",
    "description": "Transnationale Regional-Express-Linie via Kopenhagen und Fehmarnbelttunnel. Stadler KISS B (8-teilig, Mehrsystem 25kV/15kV AC) mit Traktionsbatterien für den 61,4 km oberleitungsfreien Abschnitt Lübeck Hbf-Bad Kleinen (VzG 1122). Bahnsteiglänge 210m, Doppeltraktion im Regelbetrieb ausgeschlossen. Teilt sich die Liniennummer RE17 bewusst mit der bestehenden Linie RE17 Dortmund-Wilhelmshaven (regional getrennte Netze, wie im deutschen Regionalverkehr üblich).",
    "kind": "linear",
    "branches": [
        {"branch_id": "main", "stops": RE17_STOPS, "line_label": "RE17"},
    ],
}

# ---------------------------------------------------------------------------
# LINIE RE30: Leeuwarden - Winterberg (Westf) / Duesseldorf Hbf (Fluegelzug Schwerte)
# ---------------------------------------------------------------------------
# Stammstrecke Leeuwarden-Schwerte: Hin=Phase2 Musterzug, Rueck=Phase2 Rueckfahrplan
# (beide mit echten Uhrzeiten im PDF). Fluegelaeste hin = Phase2 Aufspaltungstabelle.
# Fluegelaeste rueck = nur Start/Ziel im PDF gegeben -> Zwischenzeiten aus den
# Hinfahrt-Aesten gespiegelt (gleiche Fahrzeiten/Aufenthalte, umgekehrte Reihenfolge),
# exakt auf die gegebenen Ankunftszeiten in Schwerte einjustiert.

RE30_STAMM_HIN = [
    ("Leeuwarden", None, "07:02", "Startbahnhof Stammstrecke, Staatslijn A, 1,5kV DC"),
    ("Meppel", "07:34", "07:36", "Staatslijn A"),
    ("Zwolle", "07:51", "07:59", "Richtungswechsel (Kopfmachen), Spoorlijn Zwolle-Almelo"),
    ("Almelo", "08:31", "08:33", "Spoorlijn Zwolle-Almelo"),
    ("Hengelo", "08:44", "08:46", "Spoorlijn Almelo-Salzbergen"),
    ("Bad Bentheim", "09:07", "09:12", "Systemwechsel 1,5kV DC -> 15kV AC"),
    ("Rheine", "09:26", "09:28", "DB-Strecke 2026, Wiehengebirgsbahn"),
    ("Muenster Westf Hbf", "09:55", "09:58", "Zentraler Systemknoten"),
    ("Drensteinfurt", "10:10", "10:11", "Grenzwertige Nutzlänge, Doppeltraktion passt"),
    ("Hamm Westf Hbf", "10:23", "10:26", "Grosser Taktknoten"),
    ("Unna", "10:38", "10:40", "Halt mit selektiver Türsteuerung SDO wegen kurzer Bahnsteiglänge"),
    ("Holzwickede", "10:46", "10:47", "DB-Strecke 2840"),
]

RE30_SCHWERTE_HIN = ("Schwerte Ruhr", "10:55", None, "Richtungswechsel und Flügelung, 8 Min Halt in Doppeltraktion (~210m)")
RE30_SCHWERTE_RUECK = ("Schwerte Ruhr", None, "08:24", "Zusammenführung Flügeläste und Richtungswechsel")

RE30_STAMM_RUECK = [
    ("Holzwickede", "08:31", "08:32", "DB-Strecke 2840"),
    ("Unna", "08:38", "08:40", "Halt mit selektiver Türsteuerung SDO"),
    ("Hamm Westf Hbf", "08:52", "08:55", "Grosser Taktknoten"),
    ("Drensteinfurt", "09:07", "09:08", "DB-Strecke 2931"),
    ("Muenster Westf Hbf", "09:20", "09:23", "Zentraler Systemknoten"),
    ("Rheine", "09:50", "09:52", "DB-Strecke 2026"),
    ("Bad Bentheim", "10:06", "10:11", "Systemwechsel 15kV AC -> 1,5kV DC"),
    ("Hengelo", "10:32", "10:34", "Spoorlijn Almelo-Salzbergen"),
    ("Almelo", "10:45", "10:47", "Spoorlijn Zwolle-Almelo"),
    ("Zwolle", "11:19", "11:27", "Richtungswechsel (Kopfmachen)"),
    ("Meppel", "11:42", "11:44", "Staatslijn A"),
    ("Leeuwarden", "12:16", None, "Endbahnhof Stammstrecke"),
]

# Ast A: Schwerte - Winterberg (Westf), Obere Ruhrtalbahn + Nuttetalbahn, Akkubetrieb.
# Hin aus PDF Phase2-Aufspaltungstabelle; Rueck gespiegelt (Anker: Winterberg ab 06:39,
# Schwerte an 08:15 laut Phase3-Kaskadentabelle - Spiegelung trifft den Anker exakt).
RE30_A_HIN = [
    ("Froendenberg", "11:12", "11:14", "Obere Ruhrtalbahn, Akkubetrieb ab Schwerte"),
    ("Wickede Ruhr", "11:21", "11:22", "Obere Ruhrtalbahn"),
    ("Arnsberg Westf", "11:36", "11:38", "Obere Ruhrtalbahn"),
    ("Bestwig", "11:57", "11:59", "Obere Ruhrtalbahn"),
    ("Bigge", "12:07", "12:08", "Nuttetalbahn, eingleisig, Vmax 60-80 km/h"),
    ("Steinhelle", "12:13", "12:14", "Nuttetalbahn"),
    ("Siedlinghausen", "12:21", "12:23", "Zugkreuzung"),
    ("Silbach", "12:30", "12:31", "Nadelöhr, Nutzlänge nur 115m, passt exakt für Solo-Einheit"),
    ("Winterberg Westf", "12:39", None, "Endbahnhof, Static-Fast-Charging für Traktionsbatterien"),
]
RE30_A_RUECK = [
    ("Winterberg Westf", None, "06:39", "Startbahnhof Ast A, Takt ab xx:39"),
    ("Silbach", "06:47", "06:48", "Nadelöhr, Nutzlänge nur 115m"),
    ("Siedlinghausen", "06:55", "06:57", "Zugkreuzung"),
    ("Steinhelle", "07:04", "07:05", "Nuttetalbahn"),
    ("Bigge", "07:10", "07:11", "Nuttetalbahn, eingleisig"),
    ("Bestwig", "07:19", "07:21", "Obere Ruhrtalbahn"),
    ("Arnsberg Westf", "07:40", "07:42", "Obere Ruhrtalbahn"),
    ("Wickede Ruhr", "07:56", "07:57", "Obere Ruhrtalbahn"),
    ("Froendenberg", "08:04", "08:06", "Obere Ruhrtalbahn"),
]

# Ast B: Schwerte - Duesseldorf Hbf, unteres Ruhrtal + Ballungsraum-Korridor, Oberleitung.
RE30_B_HIN = [
    ("Hagen Hauptbahnhof", "11:13", "11:16", "DB-Strecke 2840, unteres Ruhrtal, 15kV AC"),
    ("Schwelm", "11:26", "11:27", "Stammstrecke Elberfeld-Dortmund"),
    ("Wuppertal-Oberbarmen", "11:32", "11:34", "Ballungsraum-Korridor, mehrgleisig"),
    ("Wuppertal Hauptbahnhof", "11:39", "11:42", "Ballungsraum-Korridor"),
    ("Wuppertal-Vohwinkel", "11:48", "11:49", "Vor Steilrampe Erkrath-Hochdahl"),
    ("Duesseldorf Hauptbahnhof", "12:04", None, "Endbahnhof, viergleisige Hauptabfuhrstrecke"),
]
RE30_B_RUECK = [
    ("Duesseldorf Hauptbahnhof", None, "07:14", "Startbahnhof Ast B, Takt ab xx:14"),
    ("Wuppertal-Vohwinkel", "07:29", "07:30", "Steilrampe Erkrath-Hochdahl"),
    ("Wuppertal Hauptbahnhof", "07:36", "07:39", "Ballungsraum-Korridor"),
    ("Wuppertal-Oberbarmen", "07:44", "07:46", "Ballungsraum-Korridor, mehrgleisig"),
    ("Schwelm", "07:51", "07:52", "Stammstrecke Elberfeld-Dortmund"),
    ("Hagen Hauptbahnhof", "08:02", "08:04", "DB-Strecke 2840, unteres Ruhrtal"),
]


def _build_re30_branch(ast_hin, ast_rueck):
    """Fuegt Stammstrecke + Schwerte-Knoten + Fluegelast zu einer vollen Stopliste zusammen."""
    stops = []
    for i, (key, hin_an, hin_ab, info) in enumerate(RE30_STAMM_HIN):
        rueck_an, rueck_ab = None, None
        # RE30_STAMM_RUECK ist in umgekehrter Reihenfolge (Rueckfahrt Richtung Leeuwarden)
        for rkey, ran, rab, rinfo in RE30_STAMM_RUECK:
            if rkey == key:
                rueck_an, rueck_ab = ran, rab
                break
        stops.append((key, hin_an, hin_ab, rueck_an, rueck_ab, info))
    # Schwerte (Ruhr): Fluegelungsknoten
    stops.append(("Schwerte Ruhr", RE30_SCHWERTE_HIN[1], RE30_SCHWERTE_HIN[2], RE30_SCHWERTE_RUECK[1], RE30_SCHWERTE_RUECK[2], RE30_SCHWERTE_HIN[3]))
    # ast_rueck ist in umgekehrter Stationsreihenfolge (faengt am Fluegel-Endpunkt an) ->
    # per Key nachschlagen statt per Listenposition zu zippen.
    rueck_by_key = {rkey: (ran, rab) for rkey, ran, rab, rinfo in ast_rueck}
    for key, hin_an, hin_ab, info in ast_hin:
        rueck_an, rueck_ab = rueck_by_key.get(key, (None, None))
        stops.append((key, hin_an, hin_ab, rueck_an, rueck_ab, info))
    return stops


RE30_A_STOPS = _build_re30_branch(RE30_A_HIN, RE30_A_RUECK)
RE30_B_STOPS = _build_re30_branch(RE30_B_HIN, RE30_B_RUECK)

RE30 = {
    "number": "RE30",
    "route_name": "Leeuwarden-Winterberg/Düsseldorf",
    "description": "Internationales Flaggschiff-Projekt. Stadler KISS B (4-Teiler, batterieelektrisch, 200 km/h, Mehrsystem) in Doppeltraktion (~210m) auf der Stammstrecke Leeuwarden-Schwerte (Ruhr). In Schwerte Kopfmachen und Flügelung: Zugteil A solo im Akkubetrieb ins Sauerland bis Winterberg, Zugteil B solo unter Oberleitung ins Rheinland bis Düsseldorf Hbf.",
    "kind": "flügelzug",  # physisch gekuppelter Zug, der sich in Schwerte (Ruhr) trennt
    "branches": [
        {"branch_id": "A", "stops": RE30_A_STOPS, "line_label": "RE30", "terminus": "Winterberg Westf"},
        {"branch_id": "B", "stops": RE30_B_STOPS, "line_label": "RE30", "terminus": "Duesseldorf Hauptbahnhof"},
    ],
}

ALL_LINES = [RE71, S10, S3, S30, RE17, RE30]

if __name__ == "__main__":
    for line in ALL_LINES:
        for br in line["branches"]:
            print(line["number"], br["branch_id"], len(br["stops"]), "stops")
