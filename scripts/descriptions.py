# -*- coding: utf-8 -*-
"""
Erzeugt pro Station die HTML-Bloecke ("<b>Linie</b> Route<br/>Richtung...<br/>...<br/><i>Info</i>")
sowie pro Linie die vollstaendige Linienuebersicht (Beispielzeiten + Haltestellenliste).
"""
import lines_data as ld
from display_names import DISPLAY_NAMES


def disp(key):
    return DISPLAY_NAMES[key]


def takt(hhmm):
    """'07:22' -> 'xx:22'"""
    if hhmm is None:
        return None
    return "xx" + hhmm[2:]


def direction_line(target_disp, an, ab, use_takt=True):
    a = takt(an) if use_takt else an
    b = takt(ab) if use_takt else ab
    if a and b:
        return f"Richtung {target_disp}: an {a} / ab {b}"
    if b:
        return f"Richtung {target_disp}: ab {b}"
    if a:
        return f"Richtung {target_disp}: an {a}"
    return f"Richtung {target_disp}: --"


def station_block(line_label, route_name, direction_lines, info):
    lines_html = "<br/>".join(direction_lines)
    return f"<b>{line_label}</b> {route_name}<br/>{lines_html}<br/><i>{info}</i>"


def _common_stem_len(stops_a, stops_b):
    n = 0
    for ra, rb in zip(stops_a, stops_b):
        if ra[0] != rb[0]:
            break
        n += 1
    return n


def build_station_blocks():
    """key(ascii) -> Liste von HTML-Bloecken (ein Block pro Linie/Ast-Erwaehnung)."""
    blocks = {}

    def add(key, html):
        blocks.setdefault(key, []).append(html)

    for line in ld.ALL_LINES:
        route_name = line["route_name"]

        if line["kind"] == "ring":
            br = line["branches"][0]
            stops = br["stops"]
            n = len(stops)
            for i, row in enumerate(stops):
                key, innen_an, innen_ab, innen_gleis, aussen_an, aussen_ab, aussen_gleis, info = row
                innen_label = "Innenring" + (f" (Gleis {innen_gleis.split()[-1]})" if innen_gleis else "")
                aussen_label = "Außenring" + (f" (Gleis {aussen_gleis.split()[-1]})" if aussen_gleis else "")
                dlines = [
                    direction_line(innen_label, innen_an, innen_ab),
                    direction_line(aussen_label, aussen_an, aussen_ab),
                ]
                add(key, station_block(line["number"], route_name, dlines, info))
            continue

        if line["kind"] == "flügelzug":
            branches = line["branches"]
            stem_len = _common_stem_len(branches[0]["stops"], branches[1]["stops"])
            termini = [disp(br["terminus"]) for br in branches]
            combined_target = "/".join(termini)
            # Stammstrecke: kombinierter Richtungseintrag (ein physischer Zug bis Schwerte)
            origin_disp = disp(branches[0]["stops"][0][0])
            for i in range(stem_len):
                row = branches[0]["stops"][i]
                key, hin_an, hin_ab, rueck_an, rueck_ab, info = row
                dlines = [
                    direction_line(combined_target, hin_an, hin_ab),
                    direction_line(origin_disp, rueck_an, rueck_ab),
                ]
                add(key, station_block(line["number"], route_name, dlines, info))
            # Astspezifische Stationen (ab Schwerte)
            for br in branches:
                stops = br["stops"]
                own_terminus = disp(br["terminus"])
                origin_disp = disp(stops[0][0])
                for i in range(stem_len, len(stops)):
                    key, hin_an, hin_ab, rueck_an, rueck_ab, info = stops[i]
                    dlines = [
                        direction_line(own_terminus, hin_an, hin_ab),
                        direction_line(origin_disp, rueck_an, rueck_ab),
                    ]
                    add(key, station_block(line["number"], route_name, dlines, info))
            continue

        # kind == "linear": ein oder mehrere unabhaengige Aeste (S3/S30 je 1 Branch,
        # RE71/RE17 je 1 Branch)
        for br in line["branches"]:
            stops = br["stops"]
            origin_disp = disp(stops[0][0])
            terminus_disp = disp(stops[-1][0])
            for row in stops:
                key, hin_an, hin_ab, rueck_an, rueck_ab, info = row
                dlines = [
                    direction_line(terminus_disp, hin_an, hin_ab),
                    direction_line(origin_disp, rueck_an, rueck_ab),
                ]
                add(key, station_block(line["number"], route_name, dlines, info))

    return blocks


def build_line_overview_html(line):
    """Beschreibung + vollstaendige Haltestellenliste mit Beispielzeiten fuer die
    Linienuebersicht (Popup beim Klick auf die Linie selbst)."""
    parts = [f"<b>{line['number']}</b> {line['route_name']}<br/><br/>{line['description']}<br/><br/>"]

    if line["kind"] == "ring":
        br = line["branches"][0]
        parts.append("<b>Bahnhöfe Innenring (Beispielzeiten)</b><br/><br/>")
        for row in br["stops"]:
            key, innen_an, innen_ab, innen_gleis, aussen_an, aussen_ab, aussen_gleis, info = row
            t = direction_line("", innen_an, innen_ab, use_takt=False).replace("Richtung : ", "Beispielzeit: ")
            parts.append(f"&#8226;&#160;<b>{disp(key)}</b><br/>{t}<br/><i>{info}</i><br/>")
        return "".join(parts)

    if line["kind"] == "flügelzug":
        for br in line["branches"]:
            own_terminus = disp(br["terminus"])
            origin_disp = disp(br["stops"][0][0])
            parts.append(f"<b>Ast {br['branch_id']}: {origin_disp}-{own_terminus}</b> (Beispielzeiten)<br/><br/>")
            for row in br["stops"]:
                key, hin_an, hin_ab, rueck_an, rueck_ab, info = row
                t = direction_line("", hin_an, hin_ab, use_takt=False).replace("Richtung : ", "Beispielzeit: ")
                parts.append(f"&#8226;&#160;<b>{disp(key)}</b><br/>{t}<br/><i>{info}</i><br/>")
            parts.append("<br/>")
        return "".join(parts)

    for br in line["branches"]:
        stops = br["stops"]
        parts.append(f"<b>Bahnhöfe ({len(stops)} Halte)</b> — Beispielzeiten eines Musterzugs:<br/><br/>")
        for row in stops:
            key, hin_an, hin_ab, rueck_an, rueck_ab, info = row
            t = direction_line("", hin_an, hin_ab, use_takt=False).replace("Richtung : ", "Beispielzeit: ")
            parts.append(f"&#8226;&#160;<b>{disp(key)}</b><br/>{t}<br/><i>{info}</i><br/>")
    return "".join(parts)


if __name__ == "__main__":
    blocks = build_station_blocks()
    print(f"{len(blocks)} Stationen mit Bloecken")
    # Stichprobe: Stationen mit mehreren Bloecken (Knoten)
    multi = {k: v for k, v in blocks.items() if len(v) > 1}
    print(f"{len(multi)} Stationen mit >1 Block (Knotenpunkte)")
    for k in list(multi)[:5]:
        print("---", k, "---")
        for b in multi[k]:
            print(" ", b[:120])
