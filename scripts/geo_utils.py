#!/usr/bin/env python3
"""Shared geometry helpers: Douglas-Peucker simplification and geodetic great-circle
interpolation, used by the KML builder for both real-road segments (Overpass cache)
and ocean/tunnel crossings (no real infrastructure)."""
import math


def haversine_km(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def _perpendicular_distance_m(pt, line_start, line_end):
    """Approximate perpendicular distance in meters from pt to the line_start-line_end
    segment, using an equirectangular projection (fine at the ~10-20m tolerance scale)."""
    lat0 = math.radians((line_start[0] + line_end[0]) / 2.0)
    k = 111320.0  # meters per degree latitude, ~ok for longitude too with cos(lat0) scale

    def proj(p):
        return (p[1] * k * math.cos(lat0), p[0] * k)

    x0, y0 = proj(pt)
    x1, y1 = proj(line_start)
    x2, y2 = proj(line_end)
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x0 - x1, y0 - y1)
    t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    projx, projy = x1 + t * dx, y1 + t * dy
    return math.hypot(x0 - projx, y0 - projy)


def douglas_peucker(coords, tolerance_m=18.0):
    """coords: list of (lat, lon). Returns a simplified list preserving endpoints."""
    if len(coords) < 3:
        return list(coords)

    def rec(pts):
        if len(pts) < 3:
            return pts
        start, end = pts[0], pts[-1]
        max_dist = -1.0
        max_idx = -1
        for i in range(1, len(pts) - 1):
            d = _perpendicular_distance_m(pts[i], start, end)
            if d > max_dist:
                max_dist = d
                max_idx = i
        if max_dist > tolerance_m:
            left = rec(pts[:max_idx + 1])
            right = rec(pts[max_idx:])
            return left[:-1] + right
        return [start, end]

    return rec(coords)


def great_circle_points(a, b, n=32):
    """Geodetic great-circle interpolation between a=(lat,lon) and b=(lat,lon),
    returning n+1 points including both endpoints. Uses spherical slerp."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])

    def to_xyz(lat, lon):
        return (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))

    def to_latlon(x, y, z):
        lat = math.asin(max(-1.0, min(1.0, z)))
        lon = math.atan2(y, x)
        return (math.degrees(lat), math.degrees(lon))

    x1, y1, z1 = to_xyz(lat1, lon1)
    x2, y2, z2 = to_xyz(lat2, lon2)
    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    omega = math.acos(dot)
    if omega < 1e-9:
        return [a, b]
    pts = []
    for i in range(n + 1):
        t = i / n
        s1 = math.sin((1 - t) * omega) / math.sin(omega)
        s2 = math.sin(t * omega) / math.sin(omega)
        x = s1 * x1 + s2 * x2
        y = s1 * y1 + s2 * y2
        z = s1 * z1 + s2 * z2
        pts.append(to_latlon(x, y, z))
    return pts
