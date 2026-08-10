#!/usr/bin/env python3
"""
Phase 6 - Fertige Karte als eine einzelne HTML-Datei.

Baut aus den Ergebnissen der Phasen 4 und 5 ein in sich geschlossenes HTML mit
eingebettetem SVG: keine externen Dateien, kein CDN, kein Build-Schritt, kein
localStorage.

Die Karte hat zwei Seiten, zwischen denen umgeschaltet wird:
- "Gesamtnetz": alle RE/RB-Linien in Deutschland und den Nachbarlaendern
- "Nordrhein-Westfalen": die S-Bahnen und alle dortigen RE/RB-Linien, dreimal
  so gross, weil die Halte im Ruhrgebiet im Netzmassstab nur wenige Pixel
  auseinanderliegen

Interaktion: Zoom per Mausrad oder zwei Fingern, Verschieben per Ziehen,
Doppeltipp vergroessert, Hovern/Antippen hebt eine Linie hervor, Klick auf
einen Halt zeigt seine Linien, Suchfeld springt zum Halt. Hell und Dunkel
lassen sich umschalten.
"""
import argparse
import colorsys
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kml_common import anzeigenamen

BUNDLED_PATH = Path("data/04_bundled.json")
LAYOUT_PATH = Path("data/05_layout.json")
OUTPUT_PATH = Path("netzkarte.html")

LINE_HIT_WIDTH = 13.0     # unsichtbare, breitere Trefferflaeche fuer das Hovern


def esc(text):
    """Text fuer die Verwendung in XML/HTML entschaerfen."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def polyline(points):
    return " ".join(f"{x},{y}" for x, y in points)


def _rgb(hex_color):
    c = hex_color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def helligkeit(hex_color):
    """Wahrgenommene Helligkeit von 0 bis 1."""
    r, g, b = _rgb(hex_color)
    return 0.299 * r + 0.587 * g + 0.114 * b


def dunkel_variante(hex_color, min_l=0.58, max_s=0.88):
    """
    Linienfarbe fuer den Dunkelmodus aufhellen.

    Ein Drittel der Liniennummern hat eine Helligkeit unter 0,45 (reines Blau
    liegt bei 0,11) - auf dunklem Grund waeren diese Linien kaum zu erkennen.
    Farbton bleibt erhalten, nur die Helligkeit wird angehoben und die
    Saettigung leicht gedeckelt, damit nichts grell wirkt.
    """
    r, g, b = _rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(l, min_l)
    s = min(s, max_s)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def schrift_auf(hex_color):
    """Lesbare Schriftfarbe auf einer Flaeche dieser Farbe."""
    return "#ffffff" if helligkeit(hex_color) < 0.62 else "#1a1a1a"


def farb_variablen(hex_color):
    """style-Attribut mit Farbe fuer hell (--c/--t) und dunkel (--cd/--td)."""
    dunkel = dunkel_variante(hex_color)
    return (f"--c:{hex_color};--t:{schrift_auf(hex_color)};"
            f"--cd:{dunkel};--td:{schrift_auf(dunkel)}")


def build_svg(page, data, layout):
    """Das SVG einer Kartenseite zusammensetzen."""
    meta = data["meta"]
    seite = meta["seiten"][page]
    basis = data["basiskarte"][page]
    view = data["views"][page]
    lay = layout["views"][page]
    lmeta = layout["meta"]
    lw = meta["line_width_px"]
    W, H = seite["breite"], seite["hoehe"]

    out = [f'<svg class="karte" id="karte-{page}" data-seite="{page}" '
           f'data-breite="{W}" data-hoehe="{H}" '
           f'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
           '<g class="viewport">']

    # --- Hintergrund: Laenderflaechen und Grenzen ---------------------------
    out.append('<g class="laender">')
    for c in basis["countries"]:
        d_attr = "".join("M " + " ".join(f"{x},{y}" for x, y in ring) + " Z "
                         for ring in c["polygons"])
        out.append(f'<path d="{d_attr}"/>')
    out.append("</g>")

    # Verwaltungsgrenzen unter den Staatsgrenzen, damit diese oben liegen
    out.append('<g class="bundeslaender">')
    for weg in basis["bundeslaender"]:
        out.append(f'<polyline points="{polyline(weg)}"/>')
    out.append("</g>")
    out.append('<g class="staatsgrenzen">')
    for weg in basis["staatsgrenzen"]:
        out.append(f'<polyline points="{polyline(weg)}"/>')
    out.append("</g>")

    if page == "main":
        out.append('<g class="laendernamen">')
        for c in basis["countries"]:
            out.append(f'<text x="{c["label_x"]}" y="{c["label_y"]}" '
                       f'font-size="{lmeta["country_font_px"]}">{esc(c["name"])}</text>')
        out.append("</g>")

        # Markierung des Bereichs, den die zweite Seite zeigt - anklickbar
        sx, sy, sw, sh = seite["quellrechteck"]
        out.append(f'<g class="quellbereich" data-ziel="inset">'
                   f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}"/>'
                   f'<text x="{sx + sw / 2}" y="{sy - 8}" font-size="17">'
                   f'vergrößert siehe {esc(seite["verweis"])}</text></g>')

    # --- Linien --------------------------------------------------------------
    # Sichtbare Linien, darueber eine unsichtbare breitere Trefferflaeche,
    # damit sich die nur 4 px breiten Linien bequem treffen lassen.
    out.append('<g class="linien">')
    for line in view["lines"]:
        for branch in line["branches"]:
            out.append(f'<polyline class="linie" data-line="{line["line_id"]}" '
                       f'style="{farb_variablen(line["color"])}" stroke-width="{lw}" '
                       f'points="{polyline(branch)}"/>')
    out.append("</g>")
    out.append('<g class="linien-treffer">')
    for line in view["lines"]:
        for branch in line["branches"]:
            out.append(f'<polyline class="treffer" data-line="{line["line_id"]}" '
                       f'stroke-width="{LINE_HIT_WIDTH}" points="{polyline(branch)}"/>')
    out.append("</g>")

    # --- Haltemarker ---------------------------------------------------------
    markers = {m["stop_id"]: m for m in lay["markers"]}
    out.append('<g class="halte">')
    for s in view["stops"]:
        m = markers.get(s["stop_id"])
        if not m:
            continue
        w, h = m["length"], m["thickness"]
        x0, y0 = s["x"] - w / 2, s["y"] - h / 2
        cls = "halt knoten" if m["is_node"] else "halt"
        out.append(f'<rect class="{cls}" data-stop="{s["stop_id"]}" '
                   f'x="{round(x0, 1)}" y="{round(y0, 1)}" width="{round(w, 1)}" '
                   f'height="{round(h, 1)}" rx="{round(h / 2, 2)}" '
                   f'transform="rotate({m["angle_deg"]} {s["x"]} {s["y"]})"/>')
    out.append("</g>")

    # --- Liniennummern-Badges ------------------------------------------------
    out.append('<g class="badges">')
    for b in lay["badges"]:
        bx, by = b["x"] - b["w"] / 2, b["y"] - b["h"] / 2
        out.append(f'<g class="badge" data-line="{b["line_id"]}" '
                   f'style="{farb_variablen(b["fill"])}">'
                   f'<rect x="{round(bx, 1)}" y="{round(by, 1)}" width="{b["w"]}" '
                   f'height="{b["h"]}" rx="{b["h"] / 2}"/>'
                   f'<text x="{b["x"]}" y="{round(b["y"] + lmeta["badge_font_px"] * 0.35, 1)}" '
                   f'font-size="{lmeta["badge_font_px"]}">{esc(b["text"])}</text></g>')
    out.append("</g>")

    # --- Bezugslinien und Beschriftungen ------------------------------------
    stops = {s["stop_id"]: s for s in view["stops"]}
    out.append('<g class="bezugslinien">')
    for lb in lay["labels"]:
        if "leader" in lb:
            s = stops[lb["stop_id"]]
            out.append(f'<line x1="{s["x"]}" y1="{s["y"]}" '
                       f'x2="{lb["leader"][0]}" y2="{lb["leader"][1]}"/>')
    out.append("</g>")
    out.append('<g class="beschriftung">')
    for lb in lay["labels"]:
        cls = f'name tier{lb["tier"]}' + (" fett" if lb["bold"] else "")
        out.append(f'<text class="{cls}" data-stop="{lb["stop_id"]}" x="{lb["x"]}" y="{lb["y"]}" '
                   f'font-size="{lb["font_px"]}" text-anchor="{lb["anchor"]}">'
                   f'{esc(lb["text"])}</text>')
    out.append("</g>")

    out.append("</g></svg>")
    return "".join(out)


CSS = """
/* Farben liegen als Variablen vor, damit Hell und Dunkel dieselbe Struktur
   nutzen. color-scheme sagt dem Browser ausserdem, dass die Seite ihren
   Dunkelmodus selbst regelt - sonst invertiert z.B. Brave/Chromium die Seite
   automatisch und macht dabei die weissen Text-Halos unbrauchbar. */
:root {
  color-scheme: light dark;
  --panel-bg: #fafafa;   --panel-rand: #d8d8d8;
  --text: #1a1a1a;       --text-schwach: #666;   --text-leise: #888;
  --karte-bg: #f4f4f2;
  --land-fill: #e6e6e4;  --land-text: #b9b9b5;
  --grenze-staat: #b0b0a8; --grenze-land: #d2d2cb;
  --halt-fill: #ffffff;  --halt-rand: #2a2a2a;
  --name-text: #222222;  --name-fett: #000000;   --name-halo: #ffffff;
  --bezug: #999999;
  --quelle-rand: #9a9a9a; --quelle-text: #8a8a8a;
  --knopf-bg: #ffffff;   --knopf-rand: #cccccc;  --knopf-text: #333333;
  --knopf-hover: #f0f0f0; --knopf-aktiv: #e2e2e2;
  --feld-bg: #ffffff;    --hover-bg: #e8e8e8;
  --hinweis-bg: rgba(255,255,255,.88);
}

[data-thema="dunkel"] {
  color-scheme: dark;
  --panel-bg: #171a1f;   --panel-rand: #2a2f36;
  --text: #e6e8ea;       --text-schwach: #9aa0a8; --text-leise: #7d848d;
  --karte-bg: #0d0f12;
  --land-fill: #1e222a;  --land-text: #3f4650;
  --grenze-staat: #49515d; --grenze-land: #2b313a;
  --halt-fill: #f2f4f6;  --halt-rand: #0d0f12;
  --name-text: #dfe3e8;  --name-fett: #ffffff;   --name-halo: #0d0f12;
  --bezug: #6b7480;
  --quelle-rand: #4a525d; --quelle-text: #79818c;
  --knopf-bg: #1c2026;   --knopf-rand: #333a43;  --knopf-text: #dfe3e8;
  --knopf-hover: #262c34; --knopf-aktiv: #313944;
  --feld-bg: #171a1f;    --hover-bg: #232830;
  --hinweis-bg: rgba(13,15,18,.88);
}

* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; font-family: "Helvetica Neue", Arial, sans-serif; }
body { display: flex; background: var(--panel-bg); color: var(--text); overflow: hidden; }
/* dvh beruecksichtigt die ein- und ausfahrende Browserleiste auf dem Handy */
@supports (height: 100dvh) { body { height: 100dvh; } }

#seitenleiste {
  width: 310px; flex: 0 0 310px; height: 100%; overflow-y: auto;
  border-right: 1px solid var(--panel-rand); padding: 16px 14px; background: var(--panel-bg);
}
#seitenleiste h1 { font-size: 17px; margin: 0 0 2px; }
#seitenleiste .untertitel { font-size: 11.5px; color: var(--text-schwach); margin-bottom: 14px; }
#seitenleiste h2 {
  font-size: 11px; text-transform: uppercase; letter-spacing: .07em;
  color: var(--text-schwach); margin: 18px 0 7px; font-weight: 600;
}

#seitenwahl { display: flex; gap: 5px; margin-bottom: 4px; }
#seitenwahl button {
  flex: 1; padding: 8px 6px; font-size: 12px; cursor: pointer; color: var(--knopf-text);
  border: 1px solid var(--knopf-rand); background: var(--knopf-bg); border-radius: 6px;
}
#seitenwahl button.aktiv { background: var(--knopf-aktiv); font-weight: 700; }

#suche {
  width: 100%; padding: 7px 9px; font-size: 13px; color: var(--text);
  border: 1px solid var(--panel-rand); border-radius: 5px; background: var(--feld-bg);
}
#treffer { list-style: none; margin: 5px 0 0; padding: 0; }
#treffer li { padding: 5px 7px; font-size: 12.5px; cursor: pointer; border-radius: 4px; }
#treffer li:hover { background: var(--hover-bg); }
#treffer li .zeilen { color: var(--text-schwach); font-size: 11px; }

/* Infofeld schwebt ueber der Karte, damit es auch dann sichtbar ist,
   wenn die Seitenleiste auf schmalen Bildschirmen eingeklappt ist. */
#infofeld {
  display: none; position: absolute; left: 12px; bottom: 12px; z-index: 5;
  max-width: 290px; padding: 11px 12px; background: var(--feld-bg);
  border: 1px solid var(--panel-rand); border-radius: 8px;
  box-shadow: 0 3px 14px rgba(0,0,0,.16);
  max-height: 45vh; overflow-y: auto;
}
#infofeld .titel { font-weight: 700; font-size: 14px; margin-bottom: 8px; padding-right: 22px; }
#infofeld .zeile { display: flex; align-items: center; gap: 8px; font-size: 12.5px; padding: 3px 0; }
#infofeld .schliessen {
  position: absolute; top: 4px; right: 8px; cursor: pointer; color: var(--text-leise);
  font-size: 22px; line-height: 1; padding: 2px 6px;
}

.legende { list-style: none; margin: 0; padding: 0; }
.legende li { display: flex; align-items: baseline; gap: 8px; padding: 3px 4px;
              font-size: 12px; cursor: pointer; border-radius: 4px; }
.legende li:hover { background: var(--hover-bg); }
.nummer { flex: 0 0 42px; font-weight: 700; font-size: 10.5px;
          text-align: center; border-radius: 7px; padding: 2px 3px;
          background: var(--c); color: var(--t); }
.legende .strecke { color: var(--text-schwach); line-height: 1.25; }
.legende .hinweis { color: var(--text-leise); font-size: 10.5px; }
[data-thema="dunkel"] .nummer { background: var(--cd); color: var(--td); }

#kartenbereich { flex: 1; position: relative; height: 100%; overflow: hidden; }
.karte { display: none; width: 100%; height: 100%; background: var(--karte-bg);
         cursor: grab; touch-action: none; }
.karte.aktiv { display: block; }
.karte.greift { cursor: grabbing; }

#bedienung { position: absolute; top: 12px; right: 12px; display: flex; gap: 6px; z-index: 4; }
#bedienung button, #menuKnopf {
  height: 40px; min-width: 40px; font-size: 18px; cursor: pointer;
  border: 1px solid var(--knopf-rand); background: var(--knopf-bg);
  border-radius: 7px; color: var(--knopf-text);
  -webkit-tap-highlight-color: transparent;
}
#bedienung button:hover, #menuKnopf:hover { background: var(--knopf-hover); }
#bedienung button.weit { padding: 0 13px; font-size: 13px; }

#menuKnopf { display: none; position: absolute; top: 12px; left: 12px; z-index: 6;
             width: 40px; font-size: 19px; }
#hintergrund { display: none; position: fixed; inset: 0; z-index: 8; background: rgba(0,0,0,.45); }
#hintergrund.sichtbar { display: block; }

#hinweis { position: absolute; bottom: 12px; right: 12px; font-size: 11.5px;
           color: var(--text-schwach); background: var(--hinweis-bg); padding: 5px 9px;
           border-radius: 4px; pointer-events: none; }
#hinweis .nurBreit { display: inline; }
#hinweis .nurSchmal { display: none; }

/* --- Kartenelemente --- */
/* Kein Rand an den Flaechen: Kuestenlinien entstehen aus dem Farbunterschied
   zum Hintergrund, Landgrenzen kommen aus den eigenen Grenzdatensaetzen. */
.laender path { fill: var(--land-fill); stroke: none; }
.bundeslaender polyline { fill: none; stroke: var(--grenze-land); stroke-width: 1.1; }
.staatsgrenzen polyline { fill: none; stroke: var(--grenze-staat); stroke-width: 1.9; }
.laendernamen text { fill: var(--land-text); text-anchor: middle; font-weight: 600;
                     letter-spacing: .12em; pointer-events: none; }

.quellbereich { cursor: pointer; }
.quellbereich rect { fill: none; stroke: var(--quelle-rand); stroke-width: 2.5;
                     stroke-dasharray: 9 6; }
.quellbereich text { fill: var(--quelle-text); text-anchor: middle; font-weight: 700;
                     pointer-events: none; }

/* Linienfarbe steckt als --c (hell) und --cd (dunkel) im style-Attribut */
.linie { fill: none; stroke: var(--c); stroke-linecap: round; stroke-linejoin: round;
         transition: opacity .12s; }
[data-thema="dunkel"] .linie { stroke: var(--cd); }
.treffer { fill: none; stroke: transparent; stroke-linecap: round;
           stroke-linejoin: round; pointer-events: stroke; cursor: pointer; }

.halt { fill: var(--halt-fill); stroke: var(--halt-rand); stroke-width: 1.3; cursor: pointer; }
.halt.knoten { stroke-width: 2.1; }
.halt.hervor { stroke: #d40000; stroke-width: 3; }

.name { fill: var(--name-text); pointer-events: none; paint-order: stroke;
        stroke: var(--name-halo); stroke-width: 2.6; stroke-linejoin: round; }
.name.fett { font-weight: 700; fill: var(--name-fett); stroke-width: 3.4; }
.bezugslinien line { stroke: var(--bezug); stroke-width: .7; pointer-events: none; }

.badge rect { fill: var(--c); pointer-events: none; }
.badge text { fill: var(--t); text-anchor: middle; font-weight: 700; pointer-events: none; }
[data-thema="dunkel"] .badge rect { fill: var(--cd); }
[data-thema="dunkel"] .badge text { fill: var(--td); }

/* --- Sichtbarkeit nach Zoomstufe --------------------------------------- */
/* In der Gesamtansicht waeren 465 Namen ohnehin nicht lesbar, deshalb
   erscheinen sie gestaffelt: erst Knotenbahnhoefe, dann Umsteigehalte, zuletzt
   alle uebrigen. Die Ruhrgebietsseite ist die Detailseite und zeigt von
   Anfang an alles - dafuer ist sie da. */
.zoom-0 .beschriftung, .zoom-0 .bezugslinien, .zoom-0 .badges { display: none; }
.karte[data-seite="main"].zoom-1 .tier1,
.karte[data-seite="main"].zoom-1 .tier2 { display: none; }
.karte[data-seite="main"].zoom-2 .tier2 { display: none; }

/* --- Hervorhebung einer Linie --- */
.karte.abgeblendet .linie { opacity: .12; }
.karte.abgeblendet .linie.hervor { opacity: 1; }
.karte.abgeblendet .badge { opacity: .12; }
.karte.abgeblendet .badge.hervor { opacity: 1; }
.karte.abgeblendet .halte, .karte.abgeblendet .beschriftung { opacity: .22; }

/* --- Schmale Bildschirme: Seitenleiste wird zum ausklappbaren Panel ------ */
@media (max-width: 820px) {
  #seitenleiste {
    position: fixed; top: 0; left: 0; bottom: 0; z-index: 9;
    width: 84%; max-width: 330px; flex-basis: auto;
    transform: translateX(-102%); transition: transform .22s ease;
    box-shadow: 2px 0 16px rgba(0,0,0,.28);
    padding-top: 56px;
    -webkit-overflow-scrolling: touch;
  }
  #seitenleiste.offen { transform: translateX(0); }
  #seitenleiste .schliessenPanel {
    display: block; position: absolute; top: 10px; right: 12px;
    font-size: 26px; line-height: 1; color: var(--text-leise); cursor: pointer; padding: 2px 8px;
  }
  #menuKnopf { display: block; }
  #kartenbereich { width: 100%; }

  /* groessere Treffer- und Bedienflaechen fuer den Finger */
  #suche { padding: 11px 11px; font-size: 16px; }   /* 16px verhindert das Auto-Zoom in iOS */
  #treffer li { padding: 11px 9px; font-size: 14px; }
  .legende li { padding: 8px 5px; font-size: 13.5px; }
  .legende .nummer { flex-basis: 46px; font-size: 11.5px; padding: 3px 4px; }

  #infofeld { left: 10px; right: 10px; bottom: 10px; max-width: none; }
  #hinweis { left: 10px; right: auto; bottom: auto; top: 62px; font-size: 11px; }
  #hinweis .nurBreit { display: none; }
  #hinweis .nurSchmal { display: inline; }
  #bedienung button.weit { display: none; }   /* Platz sparen, Gesamtansicht liegt im Panel */
}

.schliessenPanel { display: none; }
"""


JS = """
(function () {
  "use strict";

  var daten = __DATEN__;

  function entschaerfen(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // --- Eine Kartenseite mit Zoom und Verschiebung ausstatten ----------------
  // Jede Seite hat ihre eigene Zeichenflaeche und ihren eigenen Zoomzustand.
  function karteEinrichten(svg) {
    var breite = parseFloat(svg.dataset.breite);
    var hoehe = parseFloat(svg.dataset.hoehe);
    var viewport = svg.querySelector(".viewport");
    var k = 1, tx = 0, ty = 0;
    var MIN_K = 0.5, MAX_K = 40;

    // Das SVG passt seine viewBox mit "meet" in das Element ein. Dieser Faktor
    // rechnet zwischen Bildschirm-Pixeln und viewBox-Einheiten um.
    function einpassung() {
      var r = svg.getBoundingClientRect();
      if (!r.width || !r.height) return 1;
      return Math.min(r.width / breite, r.height / hoehe);
    }

    function anwenden() {
      viewport.setAttribute("transform", "translate(" + tx + "," + ty + ") scale(" + k + ")");
      var wirksam = k * einpassung();
      var stufe = wirksam < 0.42 ? 0 : wirksam < 0.72 ? 1 : wirksam < 1.15 ? 2 : 3;
      svg.classList.remove("zoom-0", "zoom-1", "zoom-2", "zoom-3");
      svg.classList.add("zoom-" + stufe);
    }

    function gesamtansicht() { k = 1; tx = 0; ty = 0; anwenden(); }

    // Bildschirmkoordinaten -> viewBox-Koordinaten (Zentrierung durch "meet" beachten)
    function zuViewBox(clientX, clientY) {
      var r = svg.getBoundingClientRect();
      var s = einpassung();
      return {
        x: (clientX - r.left - (r.width - breite * s) / 2) / s,
        y: (clientY - r.top - (r.height - hoehe * s) / 2) / s
      };
    }

    svg.addEventListener("wheel", function (e) {
      e.preventDefault();
      var pt = zuViewBox(e.clientX, e.clientY);
      var neu = Math.min(MAX_K, Math.max(MIN_K, k * Math.exp(-e.deltaY * 0.0016)));
      tx = pt.x - (pt.x - tx) * (neu / k);
      ty = pt.y - (pt.y - ty) * (neu / k);
      k = neu;
      anwenden();
    }, { passive: false });

    // Ziehen, Zwei-Finger-Zoom und Doppeltipp: alle Zeiger werden mitgefuehrt,
    // ein Zeiger verschiebt, zwei zoomen und verschieben um ihren Mittelpunkt.
    var zeiger = new Map();
    var zieht = false, startX = 0, startY = 0, startTx = 0, startTy = 0;
    var bewegt = false, kneifen = null;

    function zeigerListe() {
      var l = [];
      zeiger.forEach(function (v) { l.push(v); });
      return l;
    }
    function panStart(p) { zieht = true; startX = p.x; startY = p.y; startTx = tx; startTy = ty; }
    function kneifStart() {
      var l = zeigerListe();
      var mitte = zuViewBox((l[0].x + l[1].x) / 2, (l[0].y + l[1].y) / 2);
      kneifen = {
        abstand: Math.hypot(l[0].x - l[1].x, l[0].y - l[1].y) || 1,
        inhaltX: (mitte.x - tx) / k, inhaltY: (mitte.y - ty) / k, k: k
      };
      zieht = false;
    }

    svg.addEventListener("pointerdown", function (e) {
      svg.setPointerCapture(e.pointerId);
      zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });
      bewegt = false;
      if (zeiger.size === 1) { panStart({ x: e.clientX, y: e.clientY }); svg.classList.add("greift"); }
      else if (zeiger.size === 2) { kneifStart(); }
    });

    svg.addEventListener("pointermove", function (e) {
      if (!zeiger.has(e.pointerId)) return;
      zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (zeiger.size >= 2 && kneifen) {
        var l = zeigerListe();
        var abstand = Math.hypot(l[0].x - l[1].x, l[0].y - l[1].y) || 1;
        k = Math.min(MAX_K, Math.max(MIN_K, kneifen.k * (abstand / kneifen.abstand)));
        var mitte = zuViewBox((l[0].x + l[1].x) / 2, (l[0].y + l[1].y) / 2);
        tx = mitte.x - kneifen.inhaltX * k;
        ty = mitte.y - kneifen.inhaltY * k;
        bewegt = true;
        anwenden();
        return;
      }
      if (!zieht) return;
      var dx = e.clientX - startX, dy = e.clientY - startY;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) bewegt = true;
      var s = einpassung();
      tx = startTx + dx / s; ty = startTy + dy / s;
      anwenden();
    });

    function zeigerEnde(e) {
      zeiger.delete(e.pointerId);
      if (zeiger.size < 2) kneifen = null;
      if (zeiger.size === 1) panStart(zeigerListe()[0]);
      else if (zeiger.size === 0) { zieht = false; svg.classList.remove("greift"); }
    }
    svg.addEventListener("pointerup", zeigerEnde);
    svg.addEventListener("pointercancel", zeigerEnde);

    var letzterTipp = 0, letzterX = 0, letzterY = 0;
    svg.addEventListener("pointerup", function (e) {
      var jetzt = Date.now();
      var nah = Math.abs(e.clientX - letzterX) < 34 && Math.abs(e.clientY - letzterY) < 34;
      if (jetzt - letzterTipp < 320 && nah && !bewegt) {
        var pt = zuViewBox(e.clientX, e.clientY);
        var neu = Math.min(MAX_K, k * 2);
        tx = pt.x - (pt.x - tx) * (neu / k);
        ty = pt.y - (pt.y - ty) * (neu / k);
        k = neu;
        anwenden();
        bewegt = true;
        letzterTipp = 0;
        return;
      }
      letzterTipp = jetzt; letzterX = e.clientX; letzterY = e.clientY;
    });

    svg.addEventListener("click", function (e) {
      if (bewegt) return;
      var ziel = e.target.closest("[data-ziel]");
      if (ziel) { seiteWechseln(ziel.getAttribute("data-ziel")); return; }
      var h = e.target.closest("[data-stop]");
      if (h) { zeigeHalt(h.getAttribute("data-stop")); return; }
      var l = e.target.closest("[data-line]");
      if (l) { linieFesthalten(l.getAttribute("data-line")); return; }
      fixiert = null;
      hervorhebungLoesen();
    });

    svg.addEventListener("mouseover", function (e) {
      var t = e.target.closest("[data-line]");
      if (t && !fixiert) hervorheben(t.getAttribute("data-line"));
    });
    svg.addEventListener("mouseout", function (e) {
      if (e.target.closest("[data-line]")) hervorhebungLoesen();
    });

    // Der Mittelpunkt der sichtbaren Flaeche liegt bei "meet" immer auf der
    // Mitte der viewBox - deshalb genuegt diese Rechnung fuer beide Achsen.
    function springeZu(x, y) {
      var ziel = 1.35 / einpassung();
      k = Math.min(MAX_K, Math.max(k, ziel));
      tx = breite / 2 - x * k;
      ty = hoehe / 2 - y * k;
      anwenden();
    }

    function zoomStufe(faktor) {
      k = Math.min(MAX_K, Math.max(MIN_K, k * faktor));
      anwenden();
    }

    return { svg: svg, springeZu: springeZu, gesamtansicht: gesamtansicht,
             zoomStufe: zoomStufe, anwenden: anwenden };
  }

  var karten = {};
  Array.prototype.forEach.call(document.querySelectorAll(".karte"), function (svg) {
    karten[svg.dataset.seite] = karteEinrichten(svg);
  });

  // --- Seitenwechsel --------------------------------------------------------
  var aktiv = "main";

  function seiteWechseln(name) {
    if (!karten[name]) return;
    aktiv = name;
    Object.keys(karten).forEach(function (n) {
      karten[n].svg.classList.toggle("aktiv", n === name);
    });
    Array.prototype.forEach.call(document.querySelectorAll("#seitenwahl button"), function (b) {
      b.classList.toggle("aktiv", b.dataset.seite === name);
    });
    // Erst nach dem Einblenden ist die Groesse bekannt, dann Zoomstufe neu setzen
    karten[name].anwenden();
    panelSchliessen();
  }

  // --- Linien hervorheben ---------------------------------------------------
  var fixiert = null;

  function hervorheben(lineId) {
    Array.prototype.forEach.call(document.querySelectorAll(".linie, .badge"), function (el) {
      el.classList.toggle("hervor", el.getAttribute("data-line") === lineId);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".karte"), function (s) {
      s.classList.add("abgeblendet");
    });
    Array.prototype.forEach.call(document.querySelectorAll(".legende li"), function (li) {
      li.style.background = li.getAttribute("data-line") === lineId ? "var(--hover-bg)" : "";
    });
  }

  function hervorhebungLoesen() {
    if (fixiert) return;
    Array.prototype.forEach.call(document.querySelectorAll(".karte"), function (s) {
      s.classList.remove("abgeblendet");
    });
    Array.prototype.forEach.call(document.querySelectorAll(".legende li"), function (li) {
      li.style.background = "";
    });
  }

  function linieFesthalten(id) {
    fixiert = (fixiert === id) ? null : id;
    if (fixiert) hervorheben(fixiert); else hervorhebungLoesen();
  }

  // --- Halt anzeigen --------------------------------------------------------
  var infofeld = document.getElementById("infofeld");

  function markiereHalt(stopId) {
    Array.prototype.forEach.call(document.querySelectorAll(".halt"), function (el) {
      el.classList.toggle("hervor", stopId !== null && el.getAttribute("data-stop") === stopId);
    });
  }

  function zeigeHalt(stopId) {
    var halt = daten.halte[stopId];
    if (!halt) return;
    var html = '<span class="schliessen" id="infoZu">×</span><div class="titel">' +
               entschaerfen(halt.name) + "</div>";
    halt.linien.forEach(function (lid) {
      var l = daten.linien[lid];
      if (!l) return;
      html += '<div class="zeile"><span class="nummer" style="' + l.vars + '">' +
              entschaerfen(l.code) + "</span><span>" + entschaerfen(l.strecke) + "</span></div>";
    });
    infofeld.innerHTML = html;
    infofeld.style.display = "block";
    document.getElementById("infoZu").onclick = function () {
      infofeld.style.display = "none";
      markiereHalt(null);
    };
    markiereHalt(stopId);
  }

  function zuHalt(stopId) {
    var halt = daten.halte[stopId];
    if (!halt) return;
    // Auf der aktuellen Seite bleiben, wenn der Halt dort vorkommt
    var seite = halt.orte[aktiv] ? aktiv : Object.keys(halt.orte)[0];
    if (seite !== aktiv) seiteWechseln(seite);
    karten[seite].springeZu(halt.orte[seite][0], halt.orte[seite][1]);
    zeigeHalt(stopId);
  }

  // --- Suche ----------------------------------------------------------------
  var suche = document.getElementById("suche");
  var treffer = document.getElementById("treffer");

  suche.addEventListener("input", function () {
    var q = suche.value.trim().toLowerCase();
    treffer.innerHTML = "";
    if (q.length < 2) return;
    var ids = Object.keys(daten.halte), gefunden = [];
    for (var i = 0; i < ids.length && gefunden.length < 12; i++) {
      var h = daten.halte[ids[i]];
      // sowohl "Koeln Hauptbahnhof" als auch "Koeln Hbf" sollen treffen
      if (h.name.toLowerCase().indexOf(q) !== -1 || h.kurz.toLowerCase().indexOf(q) !== -1) {
        gefunden.push(ids[i]);
      }
    }
    gefunden.forEach(function (id) {
      var h = daten.halte[id];
      var li = document.createElement("li");
      var codes = h.linien.map(function (lid) {
        return daten.linien[lid] ? daten.linien[lid].code : "";
      }).join(", ");
      li.innerHTML = entschaerfen(h.name) + '<br><span class="zeilen">' + entschaerfen(codes) + "</span>";
      li.onclick = function () { zuHalt(id); };
      treffer.appendChild(li);
    });
  });

  // --- Legende --------------------------------------------------------------
  Array.prototype.forEach.call(document.querySelectorAll(".legende li"), function (li) {
    var id = li.getAttribute("data-line");
    li.addEventListener("mouseenter", function () { if (!fixiert) hervorheben(id); });
    li.addEventListener("mouseleave", hervorhebungLoesen);
    li.addEventListener("click", function () {
      linieFesthalten(id);
      // liegt die Linie nur auf der anderen Seite, dorthin wechseln
      if (fixiert && daten.linien[id] && !daten.linien[id].seiten[aktiv]) {
        var ziel = Object.keys(daten.linien[id].seiten)[0];
        if (ziel) seiteWechseln(ziel);
      }
      panelSchliessen();
    });
  });

  // --- Hell und Dunkel ------------------------------------------------------
  // Startwert kommt aus der Systemeinstellung. Ohne localStorage kann die
  // Auswahl nicht gespeichert werden, sie gilt also nur fuer diese Sitzung.
  var systemDunkel = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
  var themaKnopf = document.getElementById("thema");

  function themaSetzen(dunkel) {
    document.documentElement.setAttribute("data-thema", dunkel ? "dunkel" : "hell");
    themaKnopf.textContent = dunkel ? "☀" : "☾";
    themaKnopf.setAttribute("aria-pressed", dunkel ? "true" : "false");
  }
  themaSetzen(!!(systemDunkel && systemDunkel.matches));
  themaKnopf.onclick = function () {
    themaSetzen(document.documentElement.getAttribute("data-thema") !== "dunkel");
  };
  if (systemDunkel && systemDunkel.addEventListener) {
    systemDunkel.addEventListener("change", function (e) { themaSetzen(e.matches); });
  }

  // --- Ausklappbare Seitenleiste auf schmalen Bildschirmen -----------------
  var seitenleiste = document.getElementById("seitenleiste");
  var hintergrund = document.getElementById("hintergrund");

  function panelOeffnen() {
    seitenleiste.classList.add("offen");
    hintergrund.classList.add("sichtbar");
  }
  function panelSchliessen() {
    seitenleiste.classList.remove("offen");
    hintergrund.classList.remove("sichtbar");
  }
  document.getElementById("menuKnopf").onclick = panelOeffnen;
  document.getElementById("panelZu").onclick = panelSchliessen;
  hintergrund.onclick = panelSchliessen;

  Array.prototype.forEach.call(document.querySelectorAll("#seitenwahl button"), function (b) {
    b.onclick = function () { seiteWechseln(b.dataset.seite); };
  });

  // --- Bedienknoepfe --------------------------------------------------------
  document.getElementById("zoomEin").onclick = function () { karten[aktiv].zoomStufe(1.45); };
  document.getElementById("zoomAus").onclick = function () { karten[aktiv].zoomStufe(1 / 1.45); };
  document.getElementById("zuruecksetzen").onclick = function () {
    fixiert = null;
    hervorhebungLoesen();
    infofeld.style.display = "none";
    markiereHalt(null);
    karten[aktiv].gesamtansicht();
  };
  document.getElementById("seiteUm").onclick = function () {
    seiteWechseln(aktiv === "main" ? "inset" : "main");
  };

  window.addEventListener("resize", function () {
    Object.keys(karten).forEach(function (n) { karten[n].anwenden(); });
  });

  seiteWechseln("main");
  karten.main.gesamtansicht();
})();
"""


def build_html(data, layout):
    meta = data["meta"]
    seiten = meta["seiten"]

    # Auf welchen Seiten kommt eine Linie vor?
    seiten_je_linie = {}
    for name, view in data["views"].items():
        for line in view["lines"]:
            seiten_je_linie.setdefault(line["line_id"], {})[name] = True

    linien_js = {}
    for entry in layout["legend"]:
        linien_js[entry["line_id"]] = {
            "code": entry["code"],
            "strecke": entry["endpoints"],
            # Farbpaar hell/dunkel; Infofeld und Legende setzen sie als CSS-Variablen
            "vars": farb_variablen(entry["color"]),
            "seiten": seiten_je_linie.get(entry["line_id"], {}),
        }

    # Halte mit ihren Koordinaten je Seite; die Linienliste ist die Vereinigung
    # beider Seiten, damit z.B. Essen Hbf auch seine S-Bahnen zeigt.
    # Kartenbeschriftung mitgeben, damit die Suche auch auf das anspringt, was
    # auf der Karte steht ("E-Steele", "D-Bilk") und nicht nur auf den vollen Namen
    alle_namen = {s["name"] for v in data["views"].values() for s in v["stops"]}
    anzeige = anzeigenamen(sorted(alle_namen))

    halte_js = {}
    for name, view in data["views"].items():
        for s in view["stops"]:
            eintrag = halte_js.setdefault(s["stop_id"], {
                "name": s["name"],
                "kurz": anzeige.get(s["name"], s["name"]),
                "linien": [],
                "orte": {},
            })
            eintrag["orte"][name] = [s["x"], s["y"]]
            for lid in s["lines"]:
                if lid not in eintrag["linien"]:
                    eintrag["linien"].append(lid)

    rang = {e["line_id"]: i for i, e in enumerate(layout["legend"])}
    for eintrag in halte_js.values():
        eintrag["linien"].sort(key=lambda lid: rang.get(lid, 999))

    js_daten = {"linien": linien_js, "halte": halte_js}

    legende_html = []
    for entry in layout["legend"]:
        nur_ruhr = list(seiten_je_linie.get(entry["line_id"], {})) == ["inset"]
        hinweis = (f'<span class="hinweis"> · nur {esc(seiten["inset"]["titel"])}</span>'
                   if nur_ruhr else "")
        legende_html.append(
            f'<li data-line="{entry["line_id"]}">'
            f'<span class="nummer" style="{farb_variablen(entry["color"])}">'
            f'{esc(entry["code"])}</span>'
            f'<span class="strecke">{esc(entry["endpoints"])}{hinweis}</span></li>'
        )

    n_lines = len(layout["legend"])
    n_stops = len(halte_js)
    svgs = "".join(build_svg(name, data, layout) for name in ("main", "inset"))
    js = JS.replace("__DATEN__", json.dumps(js_daten, ensure_ascii=False, separators=(",", ":")))

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>RE-Netz 2030 — Streckennetz</title>
<style>{CSS}</style>
</head>
<body>
<aside id="seitenleiste">
  <span class="schliessenPanel" id="panelZu" role="button" aria-label="Menü schließen">×</span>
  <h1>RE-Netz 2030</h1>
  <div class="untertitel">{n_lines} Linien · {n_stops} Halte · Deutschland und Nachbarländer</div>

  <h2>Kartenseite</h2>
  <div id="seitenwahl">
    <button data-seite="main" class="aktiv">{esc(seiten["main"]["titel"])}</button>
    <button data-seite="inset">{esc(seiten["inset"]["titel"])}</button>
  </div>

  <h2>Haltestelle suchen</h2>
  <input id="suche" type="text" placeholder="Name eingeben …" autocomplete="off">
  <ul id="treffer"></ul>

  <h2>Linien</h2>
  <ul class="legende">{"".join(legende_html)}</ul>
</aside>
<div id="hintergrund"></div>

<div id="kartenbereich">
  <button id="menuKnopf" aria-label="Menü öffnen">☰</button>
  {svgs}
  <div id="bedienung">
    <button id="seiteUm" aria-label="Kartenseite wechseln">⇄</button>
    <button id="thema" aria-label="Zwischen hell und dunkel wechseln">☾</button>
    <button id="zoomEin" aria-label="Vergrößern">+</button>
    <button id="zoomAus" aria-label="Verkleinern">−</button>
    <button id="zuruecksetzen" class="weit" aria-label="Gesamtansicht">Gesamt</button>
  </div>
  <div id="infofeld"></div>
  <div id="hinweis">
    <span class="nurBreit">Mausrad zum Zoomen · Ziehen zum Verschieben · Linie anklicken zum
      Festhalten · Haltestellennamen erscheinen beim Hineinzoomen</span>
    <span class="nurSchmal">Zwei Finger zum Zoomen · Namen erscheinen beim Hineinzoomen</span>
  </div>
</div>

<script>{js}</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Phase 6 - fertige HTML-Karte bauen")
    ap.add_argument("--out", default=str(OUTPUT_PATH))
    args = ap.parse_args()

    data = json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))
    layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))

    html = build_html(data, layout)
    out = Path(args.out)
    out.write_text(html, encoding="utf-8")
    print(f"Karte geschrieben nach {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
