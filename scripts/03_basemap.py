#!/usr/bin/env python3
"""
Phase 3 - Kartengrundlage.

Laedt Natural-Earth-Laenderflaechen (Admin-0, 1:50m), beschraenkt sie auf
Deutschland + alle Nachbarlaender, clippt grosszuegig auf die Bounding Box
aus Phase 1 und projiziert alles in eine gemeinsame, fuer diese Region
verzerrungsarme Projektion.

Projektionswahl: ETRS89 / LCC Europe (EPSG:3034), eine Lambert-konforme
Kegelprojektion mit Standardparallelen bei 35°N und 65°N, zentriert auf
Europa. Kein Web Mercator, weil:
- Die Karte ist ein einmalig berechnetes, statisches SVG, kein Kachel-
  Webmap-Betrieb -> die "quadratische Kachel"-Eigenschaft von Mercator
  bringt hier keinen Vorteil.
- Das Netz erstreckt sich ueber gut 9 Breitengrade (47°-56°N). Bei Web
  Mercator waechst der Maßstabsfaktor mit 1/cos(Breite): am Nordrand
  waere die Karte ca. 20% "gestreckter" als am Suedrand. Das wuerde die
  Linienbuendel-Abstaende (die in Phase 4 als konstante Pixelbreite
  berechnet werden) je nach Kartenposition unterschiedlich breit wirken
  lassen.
- Lambert-konforme Kegelprojektionen sind der De-facto-Standard fuer
  gedruckte/statische Landkarten dieses Massstabs (Deutschland +
  Nachbarlaender) und werden u.a. von europaeischen Kartenbehoerden
  genau dafuer verwendet (EPSG:3034 = "ETRS89-LCC Europe").
"""
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

INVENTORY_PATH = Path("data/01_inventory.json")
NE_SHP_PATH = Path("data/naturalearth/ne_50m_admin_0_countries.shp")
NE_BORDER_PATH = Path("data/naturalearth/ne_50m_admin_0_boundary_lines_land.shp")
NE_STATES_PATH = Path("data/naturalearth/ne_10m_admin_1_states_provinces_lines.shp")
OUTPUT_PATH = Path("data/03_basemap.json")

TARGET_COUNTRIES = [
    "Germany", "Denmark", "Netherlands", "Belgium", "Luxembourg",
    "France", "Switzerland", "Austria", "Czechia", "Poland",
]

# Verwaltungsgrenzen (Bundeslaender, Kantone, Woiwodschaften).
# Der 1:50m-Datensatz kennt nur neun Grossstaaten, Deutschland fehlt dort -
# deshalb die 1:10m-Fassung. Frankreich liegt darin auf Departements-Ebene
# (299 Segmente) und waere fuer eine Netzkarte viel zu unruhig, bleibt also
# aussen vor. Tschechien heisst in diesem Datensatz "Czech Republic".
STATE_COUNTRIES = [
    "Germany", "Denmark", "Netherlands", "Belgium", "Luxembourg",
    "Switzerland", "Austria", "Czech Republic", "Poland",
]

BUFFER_DEG = 1.5              # grosszuegiger Puffer um die Netz-Bounding-Box (Grad)
SIMPLIFY_TOLERANCE_M = 300.0  # Douglas-Peucker-Vereinfachung in Metern (nach Projektion)
PROJECTED_CRS = "EPSG:3034"   # ETRS89 / LCC Europe


def main():
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    bbox = inventory["bounding_box"]

    # Bounding Box grosszuegig puffern (in Grad, da Quelldaten in EPSG:4326 vorliegen)
    padded_box = box(
        bbox["min_lon"] - BUFFER_DEG, bbox["min_lat"] - BUFFER_DEG,
        bbox["max_lon"] + BUFFER_DEG, bbox["max_lat"] + BUFFER_DEG,
    )

    print(f"Netz-Bounding-Box: {bbox}")
    print(f"Gepuffert um {BUFFER_DEG}°: "
          f"lon [{padded_box.bounds[0]:.2f}, {padded_box.bounds[2]:.2f}], "
          f"lat [{padded_box.bounds[1]:.2f}, {padded_box.bounds[3]:.2f}]")

    gdf = gpd.read_file(NE_SHP_PATH)
    # NAME_DE liefert die deutschen Laendernamen direkt mit, die Karte ist deutsch beschriftet
    gdf = gdf[gdf["ADMIN"].isin(TARGET_COUNTRIES)][["ADMIN", "NAME_DE", "geometry"]].copy()
    print(f"Laender aus Natural Earth geladen: {sorted(gdf['NAME_DE'].tolist())}")

    # Auf die gepufferte Bounding Box clippen (noch in EPSG:4326)
    gdf["geometry"] = gdf.geometry.intersection(padded_box)
    gdf = gdf[~gdf.geometry.is_empty]

    n_verts_before = sum(len(g.exterior.coords) if g.geom_type == "Polygon" else
                          sum(len(p.exterior.coords) for p in g.geoms)
                          for g in gdf.geometry)

    # Projizieren, dann vereinfachen (Toleranz in Metern ist in der projizierten CRS sinnvoll)
    gdf = gdf.to_crs(PROJECTED_CRS)
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE_M, preserve_topology=True)

    n_verts_after = sum(len(g.exterior.coords) if g.geom_type == "Polygon" else
                         sum(len(p.exterior.coords) for p in g.geoms)
                         for g in gdf.geometry)

    # Fuer Randbeschriftung: Label-Ankerpunkt je Land = Schwerpunkt der (geclippten) Flaeche,
    # das reicht fuer "Ländernamen an den Rändern" (die Flaechen sind ja meist abgeschnitten,
    # der Schwerpunkt der Restflaeche liegt dadurch automatisch eher am sichtbaren Rand).
    countries = []
    for _, row in gdf.iterrows():
        centroid = row.geometry.centroid
        geom = row.geometry
        if geom.geom_type == "Polygon":
            polygons = [list(geom.exterior.coords)]
        else:
            polygons = [list(p.exterior.coords) for p in geom.geoms]
        countries.append({
            "name": row["NAME_DE"],
            "label_x": centroid.x,
            "label_y": centroid.y,
            "polygons": polygons,  # Liste von Ringen, je Ring Liste von (x,y) in Metern (EPSG:3034)
        })

    # --- Grenzlinien --------------------------------------------------------
    # Bewusst eigene Datensaetze statt der Polygonumrisse: Ein Polygonrand
    # zeichnet auch die Kuestenlinie als "Grenze". Die Linien-Datensaetze
    # enthalten nur echte Landgrenzen bzw. die inneren Verwaltungsgrenzen.
    def linien_laden(pfad, filter_fn=None, toleranz=SIMPLIFY_TOLERANCE_M):
        gdf_l = gpd.read_file(pfad)
        if filter_fn is not None:
            gdf_l = gdf_l[filter_fn(gdf_l)]
        gdf_l = gdf_l[["geometry"]].copy()
        gdf_l["geometry"] = gdf_l.geometry.intersection(padded_box)
        gdf_l = gdf_l[~gdf_l.geometry.is_empty]
        gdf_l = gdf_l.to_crs(PROJECTED_CRS)
        # zusammenhaengende Zuege bilden, bevor vereinfacht wird - der
        # 1:10m-Datensatz besteht aus sehr vielen kurzen Einzelsegmenten
        verschmolzen = gdf_l.geometry.union_all()
        gdf_l = gpd.GeoDataFrame(geometry=[verschmolzen], crs=PROJECTED_CRS)
        gdf_l["geometry"] = gdf_l.geometry.simplify(toleranz, preserve_topology=False)
        wege = []
        for geom in gdf_l.geometry:
            teile = geom.geoms if geom.geom_type.startswith("Multi") else [geom]
            for t in teile:
                if t.geom_type == "LineString" and len(t.coords) >= 2:
                    wege.append([[round(x, 1), round(y, 1)] for x, y in t.coords])
        return wege

    staatsgrenzen = linien_laden(NE_BORDER_PATH)

    def nach_land(gdf_l):
        # Spaltenname variiert zwischen den Natural-Earth-Ausgaben
        spalte = "adm0_name" if "adm0_name" in gdf_l.columns else "ADM0_NAME"
        return gdf_l[spalte].isin(STATE_COUNTRIES)

    # Verwaltungsgrenzen sind reine Hintergrundinformation und duerfen
    # deutlich grober sein als die Staatsgrenzen
    bundeslaender = linien_laden(NE_STATES_PATH, nach_land, toleranz=1200.0)
    print(f"Staatsgrenzen: {len(staatsgrenzen)} Linienzuege")
    print(f"Verwaltungsgrenzen (Bundeslaender u.ae.): {len(bundeslaender)} Linienzuege")

    output = {
        "meta": {
            "projected_crs": PROJECTED_CRS,
            "projection_name": "ETRS89 / LCC Europe (Lambert-konforme Kegelprojektion)",
            "source": "Natural Earth Admin-0 Countries, 1:50m",
            "buffer_deg": BUFFER_DEG,
            "simplify_tolerance_m": SIMPLIFY_TOLERANCE_M,
            "clip_bbox_wgs84": {
                "min_lon": padded_box.bounds[0], "min_lat": padded_box.bounds[1],
                "max_lon": padded_box.bounds[2], "max_lat": padded_box.bounds[3],
            },
        },
        "countries": countries,
        "staatsgrenzen": staatsgrenzen,
        "bundeslaender": bundeslaender,
    }

    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nVereinfachung: {n_verts_before} -> {n_verts_after} Stuetzpunkte "
          f"(Toleranz {SIMPLIFY_TOLERANCE_M:.0f} m)")
    print(f"Laender im Ergebnis: {len(countries)}")
    print(f"Ausgabe geschrieben nach {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
