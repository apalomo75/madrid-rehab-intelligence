"""Registro municipal reutilizable: solo identidades y límites oficiales aportados."""

import json
import re
from pathlib import Path

import pandas as pd
import shapely as sh
from pyproj import Transformer

from .ingest import digest

IDEM_WFS = "https://idem.comunidad.madrid/geoidem/UnidadesAdministrativas/wfs"
DATA_SOURCES = ("cp", "bu", "ceee", "prtr", "municipal_events")


def municipality_config(code, name, paths=None):
    if not re.fullmatch(r"28[0-9]{3}", str(code)) or not str(name).strip():
        raise ValueError("Se requiere código INE de Madrid y nombre oficial")
    paths = paths or {}
    if set(paths) - set(DATA_SOURCES):
        raise ValueError("Fuente no soportada")
    return dict(
        municipality_code=code,
        name=name,
        province="Madrid",
        autonomous_community="Comunidad de Madrid",
        paths=paths,
        sources={
            k: {
                "available": k in paths,
                "processed": False,
                "updated_at": None,
                "coverage": "unknown",
                "quality": "unreviewed",
            }
            for k in DATA_SOURCES
        },
    )


def load_official_boundaries(path, manifest_path):
    """Contrato canónico, después de revisar metadatos y transformar la fuente oficial."""
    manifest = json.loads(Path(manifest_path).read_text())
    required = ["source_url", "publisher", "license", "source_date", "sha256"]
    if any(not manifest.get(k) for k in required) or digest(path) != manifest["sha256"]:
        raise ValueError("Procedencia, licencia, fecha o hash sin verificar")
    frame = pd.read_parquet(path)
    if len(frame) != 179 or not frame.municipality_code.is_unique:
        raise ValueError("Catálogo regional debe contener 179 municipios únicos")
    if frame.name.isna().any() or frame.name.str.strip().eq("").any() or not frame.name.is_unique:
        raise ValueError("Nombres municipales ausentes o duplicados")
    if not frame.municipality_code.str.fullmatch("28[0-9]{3}").all():
        raise ValueError("Identificadores oficiales incompatibles")
    if not frame.geometry_crs.eq("EPSG:25830").all():
        raise ValueError("Normalizar CRS a EPSG:25830")
    shapes = sh.from_wkt(frame.geometry_wkt)
    boxes = sh.bounds(shapes)
    if not (
        (boxes[:, 0] > 300000)
        & (boxes[:, 2] < 520000)
        & (boxes[:, 1] > 4400000)
        & (boxes[:, 3] < 4600000)
    ).all():
        raise ValueError("Límites fuera del sobre regional; revisar CRS y ejes")
    if not (
        sh.is_valid(shapes) & ~sh.is_empty(shapes) & pd.Series(sh.get_type_id(shapes)).isin([3, 6])
    ).all():
        raise ValueError("Recintos inválidos")
    tree = sh.STRtree(shapes)
    for i, geom in enumerate(shapes):
        for j in tree.query(geom, predicate="intersects"):
            if j > i and geom.intersection(shapes[j]).area > 1:
                raise ValueError("Solapamiento de municipios")
    frame["area_km2"] = sh.area(shapes) / 1e6
    return frame


def spatial_municipalities(grants, municipalities):
    """Cero o varias intersecciones nunca se convierten en municipio confirmado."""
    shapes = sh.from_wkt(municipalities.geometry_wkt)
    tree = sh.STRtree(shapes)
    transform = Transformer.from_crs(4326, 25830, always_xy=True)
    results = []
    for row in grants.itertuples():
        hits = (
            tree.query(
                sh.Point(*transform.transform(row.longitude, row.latitude)), predicate="intersects"
            )
            if row.geometry_valid
            else []
        )
        results.append(
            dict(
                expediente_id=row.expediente_id,
                municipality_code=municipalities.iloc[hits[0]].municipality_code
                if len(hits) == 1
                else None,
                territorial_quality="spatial_confirmed"
                if len(hits) == 1
                else "contradictory"
                if len(hits) > 1
                else "unassigned",
            )
        )
    return pd.DataFrame(results)


def reconcile_municipalities(grants, links, municipalities):
    """Contrasta límites, texto y CP sin reemplazar referencias por proximidad."""
    from .normalize import text_key

    spatial = spatial_municipalities(grants, municipalities).set_index("expediente_id")
    names = municipalities.set_index("municipality_code")["name"].to_dict()
    result = grants.copy()
    for idx, row in result.iterrows():
        candidate = spatial.loc[row.expediente_id]
        code = candidate.municipality_code
        result.at[idx, "municipality_candidate"] = code
        if candidate.territorial_quality != "spatial_confirmed":
            # CP matching remains independently usable when no boundary hit exists.
            if row.territorial_quality != "madrid_confirmed":
                result.at[idx, "territorial_quality"] = candidate.territorial_quality
            continue
        cp_madrid = links.expediente_id.eq(row.expediente_id) & links.match_status.eq("confirmed")
        literal = text_key(row.direccion or "")
        expected = text_key(names[code]) + " (MADRID)"
        conflict = (cp_madrid.any() and code != "28079") or (
            bool(literal) and not literal.endswith(expected)
        )
        result.at[idx, "territorial_quality"] = (
            "contradictory"
            if conflict
            else "madrid_confirmed"
            if code == "28079"
            else "other_municipality_confirmed"
        )
        result.at[idx, "municipality_code"] = None if conflict else code
        result.at[idx, "municipio"] = None if conflict else names[code]
    return result
