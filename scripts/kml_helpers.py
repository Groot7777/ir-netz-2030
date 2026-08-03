# -*- coding: utf-8 -*-
"""Kleine Bausteine fuer die KML-Erzeugung: LookAt-Berechnung, Farbtabelle,
XML-Escaping fuer Namen, CDATA-Wrapper mit Dark-Mode-Snippet."""
import math

DARK_MODE_SNIPPET = (
    '<style>@media (prefers-color-scheme: dark) {html,body,.kmldesc{'
    'background:#1b1b1b !important;color:#e8e8e8 !important;}'
    '.kmldesc a{color:#8ab4f8 !important;}}</style>'
)

LINE_COLORS = {
    # Per Max-Min-RGB-Distanz-Suche gegen alle 23 bestehenden Linienfarben neu bestimmt,
    # damit keine Linie (v.a. auf gemeinsam befahrenen Abschnitten im Ruhrgebiet/Ostsee-
    # Raum) mit einer bestehenden oder anderen neuen Linie verwechselbar ist.
    "RE71": "ffff0000",  # Reines Blau
    "S10": "ffff00ee",   # Magenta
    "S3": "ff87ff00",    # Fruehlingsgruen
    "S30": "ff2fbfb5",   # Oliv-Tuerkis
    "RE17": "ff00ff00",  # Reines Gruen
    "RE30": "ffffff00",  # Cyan
}


def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def cdata_description(inner_html):
    return f"<description><![CDATA[<div class=\"kmldesc\">{inner_html}</div>{DARK_MODE_SNIPPET}]]></description>"


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def station_lookat(lat, lon, range_m=2500):
    return (f"<LookAt><longitude>{lon}</longitude><latitude>{lat}</latitude>"
            f"<altitude>0</altitude><heading>0</heading><tilt>0</tilt>"
            f"<range>{range_m}</range><altitudeMode>clampToGround</altitudeMode></LookAt>")


def line_lookat_from_points(all_points):
    """all_points: Liste von (lat, lon). Range aus Bounding-Box-Diagonale, 4-400km gedeckelt."""
    lats = [p[0] for p in all_points]
    lons = [p[1] for p in all_points]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    mid_lat = (lat_min + lat_max) / 2
    mid_lon = (lon_min + lon_max) / 2
    diag_km = haversine_km(lat_min, lon_min, lat_max, lon_max)
    range_m = min(max(diag_km * 1000 * 1.3, 4000), 400000)
    return (f"<LookAt><longitude>{mid_lon}</longitude><latitude>{mid_lat}</latitude>"
            f"<altitude>0</altitude><heading>0</heading><tilt>0</tilt>"
            f"<range>{range_m:.1f}</range><altitudeMode>clampToGround</altitudeMode></LookAt>")


def coords_kml(points):
    """points: Liste von (lat, lon) -> KML 'lon,lat,0 lon,lat,0 ...'"""
    return " ".join(f"{lon:.7f},{lat:.7f},0" for lat, lon in points)
