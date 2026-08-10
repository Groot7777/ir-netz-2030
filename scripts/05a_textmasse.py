#!/usr/bin/env python3
"""
Phase 5a - Textbreiten im Browser messen.

Die Kollisionsvermeidung in Phase 5 braucht die Breite jedes Haltenamens. Eine
Schaetzung aus Buchstabenbreiten liegt je nach Name ein paar Prozent daneben -
genug, damit sich Beschriftungen wie "Gelsenkirchen Hbf" am Ende doch
ueberlappen. Dieses Skript rendert alle Namen einmal echt im Browser und misst
sie mit getComputedTextLength.

Optional: Ohne dieses Skript faellt Phase 5 auf die eingebaute Schaetzung
zurueck, die Karte entsteht dann trotzdem - nur mit etwas mehr Ueberlappung.
"""
import json
from pathlib import Path

BUNDLED_PATH = Path("data/04_bundled.json")
OUTPUT_PATH = Path("data/05a_textmasse.json")

# Muss zur Schriftangabe in Phase 6 passen
FONT_FAMILY = '"Helvetica Neue", Arial, sans-serif'


import sys
sys.path.insert(0, str(Path(__file__).parent))
from kml_common import anzeigenamen


def main():
    from playwright.sync_api import sync_playwright

    data = json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))

    # Alle vorkommenden Texte je Verwendungsart sammeln
    alle_namen = {s["name"] for v in data["views"].values() for s in v["stops"]}
    anzeige = anzeigenamen(sorted(alle_namen))

    aufgaben = set()
    for view in data["views"].values():
        for s in view["stops"]:
            aufgaben.add((anzeige[s["name"]], "halt"))
        for line in view["lines"]:
            aufgaben.add((line["code"], "badge"))
    for seite in data["meta"]["seiten"].values():
        aufgaben.add((seite["titel"], "titel"))
    aufgaben.add(("vergrößert siehe " + data["meta"]["seiten"]["main"]["verweis"], "hinweis"))

    liste = sorted(aufgaben)
    print(f"{len(liste)} zu messende Texte")

    html = (
        '<!doctype html><meta charset="utf-8">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" id="s" '
        f'style="font-family:{FONT_FAMILY}"></svg>'
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        page = browser.new_page()
        page.set_content(html)
        breiten = page.evaluate(
            """(liste) => {
                const svg = document.getElementById('s');
                const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                svg.appendChild(t);
                const out = {};
                for (const [text, art] of liste) {
                    // je Art die tatsaechlich verwendete Groesse und Staerke setzen;
                    // gemessen wird bei 100px und spaeter linear skaliert
                    t.setAttribute('font-size', '100');
                    t.setAttribute('font-weight', art === 'halt' ? '400' : '700');
                    t.textContent = text;
                    out[art + '|' + text] = t.getComputedTextLength() / 100;
                    if (art === 'halt') {
                        t.setAttribute('font-weight', '700');
                        out['halt_fett|' + text] = t.getComputedTextLength() / 100;
                    }
                }
                return out;
            }""",
            liste,
        )
        browser.close()

    OUTPUT_PATH.write_text(json.dumps(breiten, ensure_ascii=False, separators=(",", ":")),
                           encoding="utf-8")
    print(f"{len(breiten)} Messwerte geschrieben nach {OUTPUT_PATH} "
          f"({OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
