"""Selección basada en calidad de una muestra; nunca en subvenciones."""

import importlib.util

from .normalize import text_key


def evaluate_pilot(frame, config):
    path = config.get("district_boundaries")
    if not path or not importlib.util.find_spec("geopandas"):
        return {"status": "pending_validation", "selected": None, "candidates": config["district_candidates"],
                "reason": "Faltan límites oficiales locales y/o GeoPandas; no hay cobertura distrital medida."}
    import geopandas as gpd

    boundaries = gpd.read_file(path)
    if boundaries.crs is None or not boundaries.geometry.is_valid.all():
        raise ValueError("Límites distritales sin CRS o con geometría inválida")
    field = config["district_name_field"]
    boundaries = boundaries.to_crs(25830)
    boundaries["district_name"] = boundaries[field].map(lambda value: text_key(value).strip())
    eligible = frame[(frame.match_status == "matched") & frame.x.notna()].copy()
    if eligible.empty:
        return {"status": "pending_validation", "selected": None, "reason": "Sin puntos confirmados"}
    points = gpd.GeoDataFrame(eligible, geometry=gpd.points_from_xy(eligible.x, eligible.y), crs=25830)
    joined = gpd.sjoin(points, boundaries[["district_name", "geometry"]], predicate="within", how="left")
    # Los límites deben ser disjuntos. No escoger arbitrariamente una duplicación espacial.
    if joined.index.duplicated().any():
        raise ValueError("Un punto pertenece a varios distritos; revisar límites")
    selected = joined[joined.district_name.isin(config["district_candidates"])]
    counts = selected.groupby("district_name").certificate_row_id.nunique().to_dict()
    ordered = sorted(counts, key=lambda key: (-counts[key], key))
    return {"status": "sample_only" if ordered else "pending_validation",
            "selected": ordered[0] if ordered else None,
            "confirmed_source_rows_by_district": counts,
            "reason": "Mayor disponibilidad de identidades geolocalizadas en muestra; no cobertura poblacional.",
            "limitations": "Muestra ordenada por _id; ubicación de parcela, no bloque. Comparación exploratoria."}
