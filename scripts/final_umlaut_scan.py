# -*- coding: utf-8 -*-
"""Letzter Scan der fertigen KML nach ue/oe/ae/ss-Mustern in sichtbaren Texten
(name/description), mit Ausnahmeliste fuer echte Woerter. Nur zur Kontrolle,
ersetzt nichts automatisch."""
import re
import sys

SAFE_WORDS = [
    "Sauerland", "Engpass", "Anschluss", "Massen", "Neuer", "Neuen", "Neues", "Neue",
    "Straße", "Strasse", "Trasse", "muss", "dass", "Ausschuss", "wusste",
    "Soest", "Reisegeschwindigkeit", "Feuer", "steuerung", "Steuerung", "Streue",
    "aus", "auer", "euer", "Preußen", "grossen", "grosser", "grosse", "gross",
]

PATTERNS = ["ue", "oe", "ae"]


def scan(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Nur sichtbare Texte: <name>...</name> und CDATA-Inhalte
    visible_chunks = re.findall(r"<name>(.*?)</name>", content, re.DOTALL)
    visible_chunks += re.findall(r"<!\[CDATA\[(.*?)\]\]>", content, re.DOTALL)

    hits = []
    for chunk in visible_chunks:
        # Ausnahmewoerter maskieren
        masked = chunk
        for w in SAFE_WORDS:
            for variant in (w, w.lower(), w.capitalize()):
                masked = masked.replace(variant, "\x00" * len(variant))
        for pat in PATTERNS:
            for m in re.finditer(pat, masked):
                start = max(0, m.start() - 25)
                end = min(len(chunk), m.end() + 25)
                hits.append((pat, chunk[start:end]))

    print(f"{len(hits)} moegliche unkorrigierte Umlaut-Stellen gefunden:")
    seen = set()
    for pat, ctx in hits:
        key = (pat, ctx)
        if key in seen:
            continue
        seen.add(key)
        print(f"  [{pat}] ...{ctx}...")
    return len(hits)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../output/RENetz_2030_v3.kml"
    n = scan(path)
    sys.exit(1 if n else 0)
