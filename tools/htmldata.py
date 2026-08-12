"""
Gemeinsame Helfer zum Lesen/Schreiben der LINES-Datenstruktur in der
Single-File-HTML-App (app/RENetz2030_Fahrplanauskunft.html).

Die App speichert ihr komplettes Fahrplanmodell in einer einzigen
JS-Zeile der Form:

    const LINES = {...};

Diese Module suchen die Zeile über ein Präfix/Suffix-Muster (nicht über
eine feste Zeilennummer, falls sich die Datei mal verschiebt) und können
sie verlustfrei durch neu berechnete Daten ersetzen, ohne den Rest der
Datei anzufassen.
"""
import json
import re

VAR_NAME = "LINES"
_PATTERN = re.compile(
    r"^(const " + VAR_NAME + r" = )(\{.*\})(;)\s*$",
    re.MULTILINE,
)


def find_lines_match(html_text):
    """Findet die 'const LINES = {...};'-Zeile. Wirft ValueError, wenn nicht
    genau ein Treffer existiert (schützt vor stillem Falscheingriff)."""
    matches = list(_PATTERN.finditer(html_text))
    if len(matches) != 1:
        raise ValueError(
            f"Erwartet genau 1 Treffer für 'const {VAR_NAME} = {{...}};', "
            f"gefunden: {len(matches)}"
        )
    return matches[0]


def extract_lines_dict(html_text):
    m = find_lines_match(html_text)
    return json.loads(m.group(2))


def dump_lines_json(data):
    """Kompaktes JSON exakt im Stil der Originaldatei (keine Leerzeichen
    nach , und :), damit ein unveränderter Round-Trip byte-identisch ist."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def replace_lines_dict(html_text, data):
    m = find_lines_match(html_text)
    new_json = dump_lines_json(data)
    new_line = m.group(1) + new_json + m.group(3)
    return html_text[: m.start()] + new_line + html_text[m.end() :]


def extract_const(html_text, var_name):
    """Liest schreibgeschützt eine beliebige andere 'const NAME = {...};'
    (oder '[...]') Zeile aus der App, z.B. STATION_COORDS/STATION_REGIONS.
    Anders als die LINES-Funktionen oben nur zum Lesen gedacht — diese
    Konstanten werden vom Solver nicht zurückgeschrieben."""
    pattern = re.compile(
        r"^const " + re.escape(var_name) + r" = (\{.*\}|\[.*\]);\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(html_text))
    if len(matches) != 1:
        raise ValueError(
            f"Erwartet genau 1 Treffer für 'const {var_name} = ...;', "
            f"gefunden: {len(matches)}"
        )
    return json.loads(matches[0].group(1))


def replace_const(html_text, var_name, data):
    """Schreibendes Gegenstück zu extract_const() — ersetzt verlustfrei nur
    diese eine 'const NAME = ...;'-Zeile, im selben kompakten JSON-Stil wie
    dump_lines_json() (fuer byte-identischen Round-Trip bei unveraenderten
    Daten)."""
    pattern = re.compile(
        r"^(const " + re.escape(var_name) + r" = )(\{.*\}|\[.*\])(;)\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(html_text))
    if len(matches) != 1:
        raise ValueError(
            f"Erwartet genau 1 Treffer für 'const {var_name} = ...;', "
            f"gefunden: {len(matches)}"
        )
    m = matches[0]
    new_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    new_line = m.group(1) + new_json + m.group(3)
    return html_text[: m.start()] + new_line + html_text[m.end() :]
