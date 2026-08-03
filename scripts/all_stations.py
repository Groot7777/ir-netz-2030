# -*- coding: utf-8 -*-
"""Zusammengefuehrter Zugriff auf Stationskoordinaten (bestehende KML + neu geocodierte)."""
import json
import os
from display_names import DISPLAY_NAMES

_HERE = os.path.dirname(__file__)
with open(os.path.join(_HERE, "..", "cache", "existing_stations.json"), encoding="utf-8") as _f:
    _EXISTING = json.load(_f)
with open(os.path.join(_HERE, "..", "cache", "stations_cache.json"), encoding="utf-8") as _f:
    _NEW = json.load(_f)


def get_coord(key):
    """Gibt (lat, lon) fuer einen ASCII-Stationskey zurueck."""
    disp = DISPLAY_NAMES[key]
    if disp in _EXISTING:
        e = _EXISTING[disp]
        return e["lat"], e["lon"]
    if key in _NEW:
        e = _NEW[key]
        return e["lat"], e["lon"]
    raise KeyError(f"Keine Koordinate fuer {key} ({disp})")


def is_preexisting(key):
    return DISPLAY_NAMES[key] in _EXISTING
