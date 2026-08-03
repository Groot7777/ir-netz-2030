# -*- coding: utf-8 -*-
"""Douglas-Peucker-Vereinfachung fuer Koordinatenlisten (lat, lon), Toleranz in Metern."""
import math


def _perp_distance_m(pt, start, end):
    """Senkrechter Abstand von pt zur Linie start-end, in Metern (equirectangular Näherung,
    ausreichend genau für die kurzen Distanzen einzelner Liniensegmente)."""
    lat0 = math.radians((start[0] + end[0]) / 2.0)
    kx = 111320.0 * math.cos(lat0)
    ky = 110540.0

    def to_xy(p):
        return (p[1] * kx, p[0] * ky)

    x, y = to_xy(pt)
    x1, y1 = to_xy(start)
    x2, y2 = to_xy(end)

    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x, proj_y = x1 + t * dx, y1 + t * dy
    return math.hypot(x - proj_x, y - proj_y)


def douglas_peucker(points, tolerance_m=18.0):
    """points: Liste von (lat, lon). Gibt vereinfachte Liste zurueck (Endpunkte bleiben erhalten)."""
    if len(points) < 3:
        return list(points)

    def rec(pts):
        if len(pts) < 3:
            return pts
        start, end = pts[0], pts[-1]
        max_d, max_i = -1.0, -1
        for i in range(1, len(pts) - 1):
            d = _perp_distance_m(pts[i], start, end)
            if d > max_d:
                max_d, max_i = d, i
        if max_d > tolerance_m:
            left = rec(pts[:max_i + 1])
            right = rec(pts[max_i:])
            return left[:-1] + right
        return [start, end]

    return rec(list(points))


if __name__ == "__main__":
    # Kleiner Selbsttest
    line = [(51.0, 7.0), (51.0001, 7.0005), (51.0005, 7.001), (51.05, 7.05), (51.0505, 7.0505), (51.1, 7.1)]
    simplified = douglas_peucker(line, tolerance_m=18.0)
    print(f"{len(line)} -> {len(simplified)} Punkte")
    print(simplified)
