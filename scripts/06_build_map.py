#!/usr/bin/env python3
"""
Phase 6 - Fertige Karte als eine einzelne HTML-Datei.

Baut aus den Ergebnissen der Phasen 4 und 5 ein in sich geschlossenes HTML mit
eingebettetem SVG: keine externen Dateien, kein CDN, kein Build-Schritt, kein
localStorage.

Interaktion:
- Zoom per Mausrad (auf den Cursor zentriert), Verschieben per Ziehen
- Hovern ueber eine Linie hebt sie hervor und blendet die uebrigen ab
- Klick auf einen Halt zeigt Name und dort verkehrende Linien
- Suchfeld springt zu einem Halt
"""
import argparse
import json
from pathlib import Path

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


def build_svg(data, layout):
    """Das komplette SVG als String zusammensetzen."""
    meta = data["meta"]
    W, H = meta["svg_width"], meta["svg_height"]
    lw = meta["line_width_px"]
    inset = meta["inset"]
    lmeta = layout["meta"]

    out = []
    out.append(f'<svg id="karte" xmlns="http://www.w3.org/2000/svg" '
               f'viewBox="0 0 {W} {H}" class="zoom-0">')

    # Wurzelgruppe, auf die Zoom und Verschiebung angewendet werden
    out.append('<g id="viewport">')

    # --- Hintergrund: Laenderflaechen ---------------------------------------
    out.append('<g id="laender">')
    for c in data["countries"]:
        d_attr = "".join("M " + " ".join(f"{x},{y}" for x, y in ring) + " Z "
                         for ring in c["polygons"])
        out.append(f'<path d="{d_attr}"/>')
    out.append("</g>")
    out.append('<g id="laendernamen">')
    for c in data["countries"]:
        out.append(f'<text x="{c["label_x"]}" y="{c["label_y"]}" '
                   f'font-size="{lmeta["country_font_px"]}">{esc(c["name"])}</text>')
    out.append("</g>")

    # --- Markierung des vergroesserten Bereichs auf der Hauptkarte ----------
    sx, sy, sw, sh = inset["source_rect"]
    out.append(f'<g id="ausschnitt-quelle"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}"/>'
               f'<text x="{sx + sw / 2}" y="{sy - 8}" font-size="15">'
               f'vergrößert siehe Ausschnitt</text></g>')

    # --- Rahmen und Hintergrund des Ausschnitts -----------------------------
    out.append(f'<g id="ausschnitt-rahmen">'
               f'<rect x="{inset["x"]}" y="{inset["y"]}" '
               f'width="{inset["width"]}" height="{inset["height"]}"/>'
               f'<text x="{inset["x"]}" y="{inset["y"] - 12}" font-size="26">'
               f'{esc(inset["title"])} · {inset["magnification"]}fach vergrößert</text></g>')

    # --- Linien beider Ansichten --------------------------------------------
    # Sichtbare Linien und darueber eine unsichtbare, breitere Trefferflaeche,
    # damit sich die nur 4 px breiten Linien bequem mit der Maus treffen lassen.
    for view_name, view in data["views"].items():
        out.append(f'<g class="linien" data-view="{view_name}">')
        for line in view["lines"]:
            for branch in line["branches"]:
                out.append(f'<polyline class="linie" data-line="{line["line_id"]}" '
                           f'stroke="{line["color"]}" stroke-width="{lw}" '
                           f'points="{polyline(branch)}"/>')
        out.append("</g>")
    for view_name, view in data["views"].items():
        out.append(f'<g class="linien-treffer" data-view="{view_name}">')
        for line in view["lines"]:
            for branch in line["branches"]:
                out.append(f'<polyline class="treffer" data-line="{line["line_id"]}" '
                           f'stroke-width="{LINE_HIT_WIDTH}" points="{polyline(branch)}"/>')
        out.append("</g>")

    # --- Haltemarker ---------------------------------------------------------
    for view_name, view in data["views"].items():
        markers = {m["stop_id"]: m for m in layout["views"][view_name]["markers"]}
        out.append(f'<g class="halte" data-view="{view_name}">')
        for s in view["stops"]:
            m = markers.get(s["stop_id"])
            if not m:
                continue
            w, h = m["length"], m["thickness"]
            x0, y0 = s["x"] - w / 2, s["y"] - h / 2
            cls = "halt knoten" if m["is_node"] else "halt"
            out.append(f'<rect class="{cls}" data-stop="{s["stop_id"]}" data-view="{view_name}" '
                       f'x="{round(x0, 1)}" y="{round(y0, 1)}" width="{round(w, 1)}" '
                       f'height="{round(h, 1)}" rx="{round(h / 2, 2)}" '
                       f'transform="rotate({m["angle_deg"]} {s["x"]} {s["y"]})"/>')
        out.append("</g>")

    # --- Liniennummern-Badges ------------------------------------------------
    for view_name in data["views"]:
        out.append(f'<g class="badges" data-view="{view_name}">')
        for b in layout["views"][view_name]["badges"]:
            bx, by = b["x"] - b["w"] / 2, b["y"] - b["h"] / 2
            out.append(f'<g class="badge" data-line="{b["line_id"]}">'
                       f'<rect x="{round(bx, 1)}" y="{round(by, 1)}" width="{b["w"]}" '
                       f'height="{b["h"]}" rx="{b["h"] / 2}" fill="{b["fill"]}"/>'
                       f'<text x="{b["x"]}" y="{round(b["y"] + lmeta["badge_font_px"] * 0.35, 1)}" '
                       f'font-size="{lmeta["badge_font_px"]}" fill="{b["text_fill"]}">'
                       f'{esc(b["text"])}</text></g>')
        out.append("</g>")

    # --- Bezugslinien und Beschriftungen ------------------------------------
    for view_name, view in data["views"].items():
        stops = {s["stop_id"]: s for s in view["stops"]}
        lay = layout["views"][view_name]
        out.append(f'<g class="bezugslinien" data-view="{view_name}">')
        for lb in lay["labels"]:
            if "leader" in lb:
                s = stops[lb["stop_id"]]
                out.append(f'<line x1="{s["x"]}" y1="{s["y"]}" '
                           f'x2="{lb["leader"][0]}" y2="{lb["leader"][1]}"/>')
        out.append("</g>")
        out.append(f'<g class="beschriftung" data-view="{view_name}">')
        for lb in lay["labels"]:
            cls = f'name tier{lb["tier"]}' + (" fett" if lb["bold"] else "")
            out.append(f'<text class="{cls}" data-stop="{lb["stop_id"]}" x="{lb["x"]}" y="{lb["y"]}" '
                       f'font-size="{lb["font_px"]}" text-anchor="{lb["anchor"]}">'
                       f'{esc(lb["text"])}</text>')
        out.append("</g>")

    out.append("</g>")   # viewport
    out.append("</svg>")
    return "".join(out)


CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; font-family: "Helvetica Neue", Arial, sans-serif; }
body { display: flex; background: #ffffff; color: #1a1a1a; overflow: hidden; }
/* dvh beruecksichtigt die ein- und ausfahrende Browserleiste auf dem Handy */
@supports (height: 100dvh) { body { height: 100dvh; } }

#seitenleiste {
  width: 310px; flex: 0 0 310px; height: 100%; overflow-y: auto;
  border-right: 1px solid #d8d8d8; padding: 16px 14px; background: #fafafa;
}
#seitenleiste h1 { font-size: 17px; margin: 0 0 2px; }
#seitenleiste .untertitel { font-size: 11.5px; color: #666; margin-bottom: 14px; }
#seitenleiste h2 {
  font-size: 11px; text-transform: uppercase; letter-spacing: .07em;
  color: #777; margin: 18px 0 7px; font-weight: 600;
}

#suche { width: 100%; padding: 7px 9px; font-size: 13px;
         border: 1px solid #c8c8c8; border-radius: 5px; background: #fff; }
#treffer { list-style: none; margin: 5px 0 0; padding: 0; }
#treffer li { padding: 5px 7px; font-size: 12.5px; cursor: pointer; border-radius: 4px; }
#treffer li:hover { background: #e8e8e8; }
#treffer li .zeilen { color: #777; font-size: 11px; }

/* Infofeld schwebt ueber der Karte, damit es auch dann sichtbar ist,
   wenn die Seitenleiste auf schmalen Bildschirmen eingeklappt ist. */
#infofeld {
  display: none; position: absolute; left: 12px; bottom: 12px; z-index: 5;
  max-width: 290px; padding: 11px 12px; background: #fff;
  border: 1px solid #d0d0d0; border-radius: 8px;
  box-shadow: 0 3px 14px rgba(0,0,0,.16);
  /* Knotenbahnhoefe fuehren bis zu sechs Linien - dann lieber scrollen */
  max-height: 45vh; overflow-y: auto;
}
#infofeld .titel { font-weight: 700; font-size: 14px; margin-bottom: 8px; padding-right: 22px; }
#infofeld .zeile { display: flex; align-items: center; gap: 8px; font-size: 12.5px; padding: 3px 0; }
#infofeld .schliessen {
  position: absolute; top: 4px; right: 8px; cursor: pointer; color: #888;
  font-size: 22px; line-height: 1; padding: 2px 6px;
}

.legende { list-style: none; margin: 0; padding: 0; }
.legende li { display: flex; align-items: baseline; gap: 8px; padding: 3px 4px;
              font-size: 12px; cursor: pointer; border-radius: 4px; }
.legende li:hover { background: #e8e8e8; }
.legende .nummer { flex: 0 0 42px; font-weight: 700; font-size: 10.5px; color: #fff;
                   text-align: center; border-radius: 7px; padding: 2px 3px; }
.legende .strecke { color: #444; line-height: 1.25; }
.legende .hinweis { color: #888; font-size: 10.5px; }

#kartenbereich { flex: 1; position: relative; height: 100%; overflow: hidden; }
#karte { width: 100%; height: 100%; display: block; background: #f4f4f2;
         cursor: grab; touch-action: none; }
#karte.greift { cursor: grabbing; }

#bedienung { position: absolute; top: 12px; right: 12px; display: flex; gap: 6px; z-index: 4; }
#bedienung button {
  width: 40px; height: 40px; font-size: 18px; cursor: pointer;
  border: 1px solid #ccc; background: #fff; border-radius: 7px; color: #333;
  -webkit-tap-highlight-color: transparent;
}
#bedienung button:hover { background: #f0f0f0; }
#bedienung button.weit { width: auto; padding: 0 13px; font-size: 13px; }

#menuKnopf {
  display: none; position: absolute; top: 12px; left: 12px; z-index: 6;
  width: 40px; height: 40px; font-size: 19px; cursor: pointer;
  border: 1px solid #ccc; background: #fff; border-radius: 7px; color: #333;
  -webkit-tap-highlight-color: transparent;
}
#hintergrund {
  display: none; position: fixed; inset: 0; z-index: 8; background: rgba(0,0,0,.35);
}
#hintergrund.sichtbar { display: block; }

#hinweis { position: absolute; bottom: 12px; right: 12px; font-size: 11.5px;
           color: #777; background: rgba(255,255,255,.88); padding: 5px 9px;
           border-radius: 4px; pointer-events: none; }
#hinweis .nurBreit { display: inline; }
#hinweis .nurSchmal { display: none; }

/* --- Kartenelemente --- */
#laender path { fill: #e6e6e4; stroke: #ffffff; stroke-width: 1.6; }
#laendernamen text { fill: #b9b9b5; text-anchor: middle; font-weight: 600;
                     letter-spacing: .12em; pointer-events: none; }

#ausschnitt-quelle rect { fill: none; stroke: #9a9a9a; stroke-width: 2.5; stroke-dasharray: 9 6; }
#ausschnitt-quelle text { fill: #8a8a8a; text-anchor: middle; pointer-events: none; }

#ausschnitt-rahmen rect { fill: #ffffff; stroke: #b0b0b0; stroke-width: 2.5; }
#ausschnitt-rahmen text { fill: #555; font-weight: 700; pointer-events: none; }

.linie { fill: none; stroke-linecap: round; stroke-linejoin: round; transition: opacity .12s; }
.treffer { fill: none; stroke: transparent; stroke-linecap: round;
           stroke-linejoin: round; pointer-events: stroke; cursor: pointer; }

.halt { fill: #ffffff; stroke: #2a2a2a; stroke-width: 1.3; cursor: pointer; }
.halt.knoten { stroke-width: 2.1; }
.halt.hervor { stroke: #d40000; stroke-width: 3; }

.name { fill: #222; pointer-events: none; paint-order: stroke;
        stroke: #ffffff; stroke-width: 2.6; stroke-linejoin: round; }
.name.fett { font-weight: 700; fill: #000; stroke-width: 3.4; }
.bezugslinien line { stroke: #999; stroke-width: .7; pointer-events: none; }

.badge text { text-anchor: middle; font-weight: 700; pointer-events: none; }
.badge rect { pointer-events: none; }

/* --- Sichtbarkeit nach Zoomstufe: erst Knoten, dann immer mehr Details --- */
.zoom-0 .beschriftung, .zoom-0 .bezugslinien, .zoom-0 .badges { display: none; }
.zoom-1 .tier1, .zoom-1 .tier2 { display: none; }
.zoom-2 .tier2 { display: none; }

/* --- Hervorhebung einer Linie --- */
#karte.abgeblendet .linie { opacity: .12; }
#karte.abgeblendet .linie.hervor { opacity: 1; }
#karte.abgeblendet .badge { opacity: .12; }
#karte.abgeblendet .badge.hervor { opacity: 1; }
#karte.abgeblendet .halte, #karte.abgeblendet .beschriftung { opacity: .22; }

/* --- Schmale Bildschirme: Seitenleiste wird zum ausklappbaren Panel ------ */
@media (max-width: 820px) {
  #seitenleiste {
    position: fixed; top: 0; left: 0; bottom: 0; z-index: 9;
    width: 84%; max-width: 330px; flex-basis: auto;
    transform: translateX(-102%); transition: transform .22s ease;
    box-shadow: 2px 0 16px rgba(0,0,0,.18);
    padding-top: 56px;
    -webkit-overflow-scrolling: touch;
  }
  #seitenleiste.offen { transform: translateX(0); }
  #seitenleiste .schliessenPanel {
    display: block; position: absolute; top: 10px; right: 12px;
    font-size: 26px; line-height: 1; color: #888; cursor: pointer; padding: 2px 8px;
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
}

.schliessenPanel { display: none; }
"""


JS = """
(function () {
  "use strict";

  var daten = __DATEN__;
  var svg = document.getElementById("karte");
  var viewport = document.getElementById("viewport");
  var kartenbereich = document.getElementById("kartenbereich");

  // --- Zoom und Verschiebung ------------------------------------------------
  // k = Massstab, tx/ty = Verschiebung, beides in viewBox-Einheiten und als
  // transform auf der Wurzelgruppe. Das SVG selbst behaelt seine viewBox.
  var k = 1, tx = 0, ty = 0;
  var MIN_K = 0.5, MAX_K = 40;

  // Das SVG passt seine viewBox mit "meet" in das Element ein. Dieser Faktor
  // rechnet zwischen Bildschirm-Pixeln und viewBox-Einheiten um.
  function einpassung() {
    var r = svg.getBoundingClientRect();
    return Math.min(r.width / daten.breite, r.height / daten.hoehe);
  }

  function anwenden() {
    viewport.setAttribute("transform", "translate(" + tx + "," + ty + ") scale(" + k + ")");
    // Wie gross erscheint eine viewBox-Einheit tatsaechlich auf dem Bildschirm?
    var wirksam = k * einpassung();
    var stufe = wirksam < 0.42 ? 0 : wirksam < 0.72 ? 1 : wirksam < 1.15 ? 2 : 3;
    svg.classList.remove("zoom-0", "zoom-1", "zoom-2", "zoom-3");
    svg.classList.add("zoom-" + stufe);
  }

  function gesamtansicht() {
    // Bei k=1 zeigt die viewBox bereits das gesamte Netz.
    k = 1; tx = 0; ty = 0;
    anwenden();
  }

  // Bildschirmkoordinaten -> viewBox-Koordinaten (Zentrierung durch "meet" beachten)
  function zuViewBox(clientX, clientY) {
    var r = svg.getBoundingClientRect();
    var s = einpassung();
    return {
      x: (clientX - r.left - (r.width - daten.breite * s) / 2) / s,
      y: (clientY - r.top - (r.height - daten.hoehe * s) / 2) / s
    };
  }

  svg.addEventListener("wheel", function (e) {
    e.preventDefault();
    var pt = zuViewBox(e.clientX, e.clientY);
    var neu = Math.min(MAX_K, Math.max(MIN_K, k * Math.exp(-e.deltaY * 0.0016)));
    // Der Punkt unter dem Cursor bleibt beim Zoomen an Ort und Stelle
    tx = pt.x - (pt.x - tx) * (neu / k);
    ty = pt.y - (pt.y - ty) * (neu / k);
    k = neu;
    anwenden();
  }, { passive: false });

  // --- Ziehen, Zwei-Finger-Zoom und Doppeltipp ------------------------------
  // Alle Zeiger werden mitgefuehrt: ein Zeiger verschiebt, zwei Zeiger zoomen
  // und verschieben gleichzeitig (wie auf einer Kartenapp gewohnt).
  var zeiger = new Map();
  var zieht = false, startX = 0, startY = 0, startTx = 0, startTy = 0, bewegt = false;
  var kneifen = null;   // {abstand, inhaltX, inhaltY, k}

  function zeigerListe() {
    var l = [];
    zeiger.forEach(function (v) { l.push(v); });
    return l;
  }

  function panStart(p) {
    zieht = true;
    startX = p.x; startY = p.y; startTx = tx; startTy = ty;
  }

  function kneifStart() {
    var l = zeigerListe();
    var mitteBild = zuViewBox((l[0].x + l[1].x) / 2, (l[0].y + l[1].y) / 2);
    kneifen = {
      abstand: Math.hypot(l[0].x - l[1].x, l[0].y - l[1].y) || 1,
      // Punkt im Karteninhalt, der unter der Fingermitte liegt und dort bleiben soll
      inhaltX: (mitteBild.x - tx) / k,
      inhaltY: (mitteBild.y - ty) / k,
      k: k
    };
    zieht = false;
  }

  svg.addEventListener("pointerdown", function (e) {
    svg.setPointerCapture(e.pointerId);
    zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });
    bewegt = false;
    if (zeiger.size === 1) {
      panStart({ x: e.clientX, y: e.clientY });
      svg.classList.add("greift");
    } else if (zeiger.size === 2) {
      kneifStart();
    }
  });

  svg.addEventListener("pointermove", function (e) {
    if (!zeiger.has(e.pointerId)) return;
    zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (zeiger.size >= 2 && kneifen) {
      var l = zeigerListe();
      var abstand = Math.hypot(l[0].x - l[1].x, l[0].y - l[1].y) || 1;
      var neu = Math.min(MAX_K, Math.max(MIN_K, kneifen.k * (abstand / kneifen.abstand)));
      var mitte = zuViewBox((l[0].x + l[1].x) / 2, (l[0].y + l[1].y) / 2);
      k = neu;
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
    if (zeiger.size === 1) {
      // ein Finger bleibt liegen: von dort aus normal weiterschieben
      panStart(zeigerListe()[0]);
    } else if (zeiger.size === 0) {
      zieht = false;
      svg.classList.remove("greift");
    }
  }
  svg.addEventListener("pointerup", zeigerEnde);
  svg.addEventListener("pointercancel", zeigerEnde);

  // Doppeltipp bzw. Doppelklick vergroessert um den getippten Punkt
  var letzterTipp = 0, letzterTippX = 0, letzterTippY = 0;
  svg.addEventListener("pointerup", function (e) {
    var jetzt = Date.now();
    var nah = Math.abs(e.clientX - letzterTippX) < 34 && Math.abs(e.clientY - letzterTippY) < 34;
    if (jetzt - letzterTipp < 320 && nah && !bewegt) {
      var pt = zuViewBox(e.clientX, e.clientY);
      var neu = Math.min(MAX_K, k * 2);
      tx = pt.x - (pt.x - tx) * (neu / k);
      ty = pt.y - (pt.y - ty) * (neu / k);
      k = neu;
      anwenden();
      bewegt = true;          // den folgenden Klick nicht als Auswahl werten
      letzterTipp = 0;
      return;
    }
    letzterTipp = jetzt; letzterTippX = e.clientX; letzterTippY = e.clientY;
  });

  // Der Mittelpunkt der sichtbaren Flaeche liegt bei "meet" immer auf der
  // Mitte der viewBox - deshalb genuegt diese Rechnung fuer beide Achsen.
  function springeZu(x, y) {
    var ziel = 1.35 / einpassung();          // so weit, dass alle Namen sichtbar sind
    k = Math.min(MAX_K, Math.max(k, ziel));
    tx = daten.breite / 2 - x * k;
    ty = daten.hoehe / 2 - y * k;
    anwenden();
  }

  // --- Linien hervorheben ---------------------------------------------------
  var fixiert = null;

  function hervorheben(lineId) {
    var alle = svg.querySelectorAll(".linie, .badge");
    for (var i = 0; i < alle.length; i++) {
      alle[i].classList.toggle("hervor", alle[i].getAttribute("data-line") === lineId);
    }
    svg.classList.add("abgeblendet");
    var eintraege = document.querySelectorAll(".legende li");
    for (var j = 0; j < eintraege.length; j++) {
      eintraege[j].style.background = eintraege[j].getAttribute("data-line") === lineId ? "#e0e0e0" : "";
    }
  }

  function zuruecksetzenHervorhebung() {
    if (fixiert) return;
    svg.classList.remove("abgeblendet");
    var eintraege = document.querySelectorAll(".legende li");
    for (var j = 0; j < eintraege.length; j++) eintraege[j].style.background = "";
  }

  svg.addEventListener("mouseover", function (e) {
    var t = e.target.closest("[data-line]");
    if (t && !fixiert) hervorheben(t.getAttribute("data-line"));
  });
  svg.addEventListener("mouseout", function (e) {
    if (e.target.closest("[data-line]")) zuruecksetzenHervorhebung();
  });

  // --- Halt anklicken -------------------------------------------------------
  var infofeld = document.getElementById("infofeld");

  function zeigeHalt(stopId) {
    var halt = daten.halte[stopId];
    if (!halt) return;
    var html = '<span class="schliessen" id="infoZu">×</span><div class="titel">' +
               entschaerfen(halt.name) + "</div>";
    halt.linien.forEach(function (lid) {
      var l = daten.linien[lid];
      if (!l) return;
      html += '<div class="zeile"><span class="nummer" style="background:' + l.farbe +
              ';color:' + l.schrift + '">' + entschaerfen(l.code) + "</span><span>" +
              entschaerfen(l.strecke) + "</span></div>";
    });
    infofeld.innerHTML = html;
    infofeld.style.display = "block";
    document.getElementById("infoZu").onclick = function () {
      infofeld.style.display = "none";
      markiereHalt(null);
    };
    markiereHalt(stopId);
  }

  function markiereHalt(stopId) {
    var alle = svg.querySelectorAll(".halt");
    for (var i = 0; i < alle.length; i++) {
      alle[i].classList.toggle("hervor", stopId !== null && alle[i].getAttribute("data-stop") === stopId);
    }
  }

  svg.addEventListener("click", function (e) {
    if (bewegt) return;
    var h = e.target.closest("[data-stop]");
    if (h) { zeigeHalt(h.getAttribute("data-stop")); return; }
    var l = e.target.closest("[data-line]");
    if (l) {
      var id = l.getAttribute("data-line");
      fixiert = (fixiert === id) ? null : id;
      if (fixiert) hervorheben(fixiert); else zuruecksetzenHervorhebung();
      return;
    }
    fixiert = null;
    zuruecksetzenHervorhebung();
  });

  // --- Suche ----------------------------------------------------------------
  var suche = document.getElementById("suche");
  var treffer = document.getElementById("treffer");

  function entschaerfen(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

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
      li.onclick = function () {
        springeZu(h.x, h.y);
        zeigeHalt(id);
        panelSchliessen();     // auf dem Handy gibt das die Karte wieder frei
      };
      treffer.appendChild(li);
    });
  });

  // --- Legende --------------------------------------------------------------
  document.querySelectorAll(".legende li").forEach(function (li) {
    var id = li.getAttribute("data-line");
    li.addEventListener("mouseenter", function () { if (!fixiert) hervorheben(id); });
    li.addEventListener("mouseleave", zuruecksetzenHervorhebung);
    li.addEventListener("click", function () {
      fixiert = (fixiert === id) ? null : id;
      if (fixiert) hervorheben(fixiert); else zuruecksetzenHervorhebung();
      panelSchliessen();     // sonst verdeckt das Panel die hervorgehobene Linie
    });
  });

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

  // --- Bedienknoepfe --------------------------------------------------------
  document.getElementById("zoomEin").onclick = function () {
    k = Math.min(MAX_K, k * 1.45); anwenden();
  };
  document.getElementById("zoomAus").onclick = function () {
    k = Math.max(MIN_K, k / 1.45); anwenden();
  };
  document.getElementById("zuruecksetzen").onclick = function () {
    fixiert = null; zuruecksetzenHervorhebung();
    infofeld.style.display = "none"; markiereHalt(null);
    gesamtansicht();
  };

  window.addEventListener("resize", anwenden);
  gesamtansicht();
})();
"""


def build_html(data, layout):
    meta = data["meta"]

    # Kompakte Daten fuer die Interaktion (Suche, Infofeld, Legende)
    linien_js = {}
    for entry in layout["legend"]:
        linien_js[entry["line_id"]] = {
            "code": entry["code"],
            "farbe": entry["color"],
            "strecke": entry["endpoints"],
            "schrift": "#ffffff" if _dunkel(entry["color"]) else "#1a1a1a",
        }

    halte_js = {}
    for view_name, view in data["views"].items():
        for s in view["stops"]:
            # Ein Halt kann in beiden Ansichten vorkommen; die Hauptkarte gewinnt,
            # damit die Suche dorthin springt, wo der Halt im Gesamtnetz liegt.
            if s["stop_id"] in halte_js and view_name != "main":
                continue
            halte_js[s["stop_id"]] = {
                "name": s["name"],
                # zusaetzlich die gekuerzte Form, damit die Suche auch auf "Hbf" anspringt
                "kurz": s["name"].replace("Hauptbahnhof", "Hbf"),
                "x": s["x"],
                "y": s["y"],
                "linien": s["lines"],
            }

    js_daten = {
        "breite": meta["svg_width"],
        "hoehe": meta["svg_height"],
        "linien": linien_js,
        "halte": halte_js,
    }

    legende_html = []
    for entry in layout["legend"]:
        schrift = "#ffffff" if _dunkel(entry["color"]) else "#1a1a1a"
        hinweis = ('<span class="hinweis"> · nur im Ausschnitt</span>'
                   if entry["in_inset_only"] else "")
        legende_html.append(
            f'<li data-line="{entry["line_id"]}">'
            f'<span class="nummer" style="background:{entry["color"]};color:{schrift}">'
            f'{esc(entry["code"])}</span>'
            f'<span class="strecke">{esc(entry["endpoints"])}{hinweis}</span></li>'
        )

    n_lines = len(layout["legend"])
    n_stops = len(halte_js)

    svg = build_svg(data, layout)
    js = JS.replace("__DATEN__", json.dumps(js_daten, ensure_ascii=False, separators=(",", ":")))

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RE-Netz 2030 — Streckennetz</title>
<style>{CSS}</style>
</head>
<body>
<aside id="seitenleiste">
  <span class="schliessenPanel" id="panelZu" role="button" aria-label="Menü schließen">×</span>
  <h1>RE-Netz 2030</h1>
  <div class="untertitel">{n_lines} Linien · {n_stops} Halte · Deutschland und Nachbarländer</div>

  <h2>Haltestelle suchen</h2>
  <input id="suche" type="text" placeholder="Name eingeben …" autocomplete="off">
  <ul id="treffer"></ul>

  <h2>Linien</h2>
  <ul class="legende">{"".join(legende_html)}</ul>
</aside>
<div id="hintergrund"></div>

<div id="kartenbereich">
  <button id="menuKnopf" aria-label="Menü öffnen">☰</button>
  {svg}
  <div id="bedienung">
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


def _dunkel(hex_color):
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 < 0.62


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
