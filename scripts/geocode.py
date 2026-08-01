#!/usr/bin/env python3
"""Geocode all stations across all line files via Photon, using a hard bbox
around the last known-good coordinate on the same line (progressively widened
until a match passes a distance-sanity check against the documented km-marker
delta). Manual overrides and per-line city anchors always win. Results cached
in cache/geocode_cache.json; rejected/low-confidence hits go to
cache/geocode_review.json for manual inspection.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES_DIR = os.path.join(ROOT, "data", "lines")
OVERRIDES_PATH = os.path.join(ROOT, "data", "overrides.json")
ANCHORS_PATH = os.path.join(ROOT, "data", "line_anchors.json")
CACHE_PATH = os.path.join(ROOT, "cache", "geocode_cache.json")
REVIEW_PATH = os.path.join(ROOT, "cache", "geocode_review.json")

PHOTON_URL = "https://photon.komoot.io/api/"

# progressively widened bbox half-widths in degrees (lon_delta, lat_delta)
BBOX_STEPS = [0.1, 0.25, 0.5, 1.0, None]  # None = no bbox (global, last resort)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def haversine_km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def photon_query(q, bbox=None, limit=8):
    params = {"q": q, "limit": str(limit), "lang": "de"}
    if bbox is not None:
        params["bbox"] = ",".join(str(x) for x in bbox)
    url = PHOTON_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ir-netz-2030-geocoder/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == 2:
                print(f"  ! Photon-Fehler fuer '{q}': {e}", file=sys.stderr)
                return {"features": []}
            time.sleep(1.5 * (attempt + 1))
    return {"features": []}


def geocode_near(q, anchor, max_km):
    """Try progressively wider bboxes around anchor=(lat,lon); within each,
    take the closest-to-anchor candidate that passes the max_km sanity check.
    Returns (feature_or_None, bbox_step_index_used, distance_km_or_None)."""
    if anchor is None:
        data = photon_query(q, bbox=None)
        feats = data.get("features", [])
        return (feats[0] if feats else None), len(BBOX_STEPS) - 1, None

    for i, half in enumerate(BBOX_STEPS):
        if half is None:
            data = photon_query(q, bbox=None)
        else:
            lat, lon = anchor
            bbox = (lon - half, lat - half, lon + half, lat + half)
            data = photon_query(q, bbox=bbox)
        feats = data.get("features", [])
        if not feats:
            continue
        # rank candidates by distance to anchor, pick closest that passes sanity check
        scored = []
        for f in feats:
            flon, flat = f["geometry"]["coordinates"]
            d = haversine_km(anchor, (flat, flon))
            scored.append((d, f))
        scored.sort(key=lambda t: t[0])
        best_d, best_f = scored[0]
        if best_d <= max_km:
            return best_f, i, best_d
        # nothing in this bbox passes; widen further
    # last resort: no bbox, take closest of top results regardless of sanity check, flagged low
    data = photon_query(q, bbox=None)
    feats = data.get("features", [])
    if feats:
        scored = sorted(((haversine_km(anchor, (f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0])), f) for f in feats), key=lambda t: t[0])
        return scored[0][1], len(BBOX_STEPS), scored[0][0]
    return None, len(BBOX_STEPS), None


def collect_all_stops():
    ordered = []
    for fn in sorted(os.listdir(LINES_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(LINES_DIR, fn)
        line = load_json(path, {})
        prev_km = 0.0
        for stop in line.get("stops", []):
            km = stop.get("km")
            delta = None
            if km is not None:
                delta = max(0.0, km - prev_km)
                prev_km = km
            ordered.append((line["id"], stop["key"], stop.get("display", stop["key"]), stop.get("note", ""), delta))
    return ordered


def main():
    overrides = load_json(OVERRIDES_PATH, {})
    anchors = load_json(ANCHORS_PATH, {})
    cache = load_json(CACHE_PATH, {})
    review = load_json(REVIEW_PATH, {})

    ordered = collect_all_stops()
    seen_keys = set()
    last_coord_by_line = {}

    for line_id, key, display, note, km_delta in ordered:
        if key in seen_keys:
            continue
        seen_keys.add(key)

        if key in overrides:
            ov = overrides[key]
            cache[key] = {"lat": ov["lat"], "lon": ov["lon"], "source": "override"}
            review.pop(key, None)
            last_coord_by_line[line_id] = (ov["lat"], ov["lon"])
            continue

        anchor = last_coord_by_line.get(line_id)
        if anchor is None and line_id in anchors:
            a = anchors[line_id]
            anchor = (a["lat"], a["lon"])

        if key in cache and cache[key].get("source") in ("photon", "override", "pdf_exact"):
            last_coord_by_line[line_id] = (cache[key]["lat"], cache[key]["lon"])
            continue

        # sanity-check radius: at least the km-delta * 2.5 (allows for curvy real routing),
        # but never below 15 km (local street-level moves) nor above 250 km (safety cap
        # for suspiciously large single hops, which get flagged instead of silently accepted)
        max_km = 250.0
        if km_delta is not None:
            max_km = min(250.0, max(15.0, km_delta * 2.5))

        feat, bbox_step, dist = geocode_near(display, anchor, max_km)
        if feat is None:
            print(f"  ?? Keine Treffer fuer '{display}' (Linie {line_id})")
            review[key] = {"display": display, "note": note, "line": line_id, "reason": "no_match"}
            continue

        lon, lat = feat["geometry"]["coordinates"]
        props = feat.get("properties", {})
        confidence = "high" if bbox_step <= 1 else ("medium" if bbox_step <= 3 else "low")
        cache[key] = {
            "lat": lat,
            "lon": lon,
            "source": "photon",
            "matched_name": props.get("name"),
            "osm_value": props.get("osm_value"),
            "city": props.get("city"),
            "confidence": confidence,
            "bbox_step": bbox_step,
            "dist_from_anchor_km": round(dist, 1) if dist is not None else None,
            "km_delta": km_delta,
        }
        last_coord_by_line[line_id] = (lat, lon)
        dist_str = f"{dist:.1f}km" if dist is not None else "n/a"
        flag = "" if confidence == "high" else f"  [{confidence.upper()}, step={bbox_step}, dist={dist_str}, kmDelta={km_delta}]"
        print(f"  OK {key!r:45s} -> {props.get('name')} ({props.get('osm_value')}) @ {lat:.4f},{lon:.4f}{flag}")
        if confidence != "high":
            review[key] = {"display": display, "note": note, "line": line_id, "reason": f"confidence_{confidence}_bbox_{bbox_step}",
                            "matched": props.get("name"), "lat": lat, "lon": lon, "dist_from_anchor_km": dist, "km_delta": km_delta}
        else:
            review.pop(key, None)
        time.sleep(0.25)

    save_json(CACHE_PATH, cache)
    save_json(REVIEW_PATH, review)
    print(f"\nFertig. {len(cache)} Stationen im Cache, {len(review)} zur manuellen Pruefung.")


if __name__ == "__main__":
    main()
