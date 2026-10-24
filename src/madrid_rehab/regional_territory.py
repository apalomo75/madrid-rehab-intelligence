"""Importación de catálogo INE y límites oficiales con correspondencias explícitas."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import shapely as sh
from pyproj import Transformer
from shapely.ops import transform

from .ingest import digest, save_json
from .regional import load_official_boundaries

OFFICIAL_HOSTS = {
    "www.ign.es",
    "api-features.ign.es",
    "centrodedescargas.cnig.es",
    "idem.comunidad.madrid",
    "www.madrid.org",
    "www.ine.es",
    "ine.es",
}


def validate_catalogue(frame):
    required = {"municipality_code", "name", "boundary_source_id"}
    if not required <= set(frame) or len(frame) != 179:
        raise ValueError("Se requieren 179 municipios INE y su identificador de límite")
    for field in required:
        if (
            frame[field].isna().any()
            or frame[field].str.strip().eq("").any()
            or not frame[field].is_unique
        ):
            raise ValueError("Catálogo incompleto o duplicado")
    if not frame.municipality_code.str.fullmatch(r"28\d{3}").all():
        raise ValueError("Códigos INE incompatibles")
    if "28079" not in set(frame.municipality_code):
        raise ValueError("Falta Madrid capital")
    return frame.sort_values("municipality_code").reset_index(drop=True)


def normalize_boundaries(document, catalogue, id_property, source_crs):
    """Identidad mediante tabla revisada, sin deducción por texto o últimos dígitos."""
    catalogue = validate_catalogue(catalogue)
    if (
        document.get("type") != "FeatureCollection"
        or document.get("links")
        and any(link.get("rel") == "next" for link in document["links"])
    ):
        raise ValueError("Colección incompleta o paginada: aportar captura completa")
    if source_crs not in {"OGC:CRS84", "EPSG:4326", "EPSG:25830"}:
        raise ValueError("CRS o ejes no revisados")
    declared = document.get("crs", {}).get("properties", {}).get("name")
    compatible = {None, source_crs}
    if source_crs in {"EPSG:4326", "OGC:CRS84"}:
        compatible |= {"urn:ogc:def:crs:OGC:1.3:CRS84"}
    if declared not in compatible:
        raise ValueError("CRS declarado contradice la configuración")
    features = document["features"]
    selected = {}
    ids = set(catalogue.boundary_source_id)
    for feature in features:
        key = str(feature["properties"].get(id_property, ""))
        if key in ids:
            if key in selected:
                raise ValueError("Identificador geométrico duplicado")
            selected[key] = feature
    if set(selected) != ids:
        raise ValueError("Faltan límites para el catálogo")
    projection = Transformer.from_crs(source_crs, 25830, always_xy=True).transform
    rows = []
    for row in catalogue.itertuples():
        geom = sh.geometry.shape(selected[row.boundary_source_id]["geometry"])
        if source_crs != "EPSG:25830":
            geom = transform(projection, geom)
        if geom.geom_type not in {"Polygon", "MultiPolygon"} or not geom.is_valid or geom.is_empty:
            raise ValueError("Límite inválido; no se repara silenciosamente")
        point = geom.representative_point()
        longitude, latitude = Transformer.from_crs(25830, 4326, always_xy=True).transform(
            point.x, point.y
        )
        rows.append(
            dict(
                municipality_code=row.municipality_code,
                name=row.name,
                boundary_source_id=row.boundary_source_id,
                geometry_wkt=geom.wkt,
                geometry_crs="EPSG:25830",
                area_km2=geom.area / 1e6,
                longitude=longitude,
                latitude=latitude,
                multipart=geom.geom_type == "MultiPolygon",
                province="Madrid",
                autonomous_community="Comunidad de Madrid",
                validation_status="validated",
            )
        )
    return pd.DataFrame(rows)


def run(catalogue_path, geojson_path, provenance_path, output, id_property, source_crs):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Usar salida nueva")
    provenance = json.loads(Path(provenance_path).read_text())
    for field in [
        "source_url",
        "catalogue_source_url",
        "publisher",
        "license",
        "source_date",
        "identity_mapping_review",
    ]:
        if not provenance.get(field):
            raise ValueError("Falta procedencia/licencia/fecha/revisión de identidad")
    for field in ["source_url", "catalogue_source_url"]:
        url = urlsplit(provenance[field])
        if url.scheme != "https" or url.hostname not in OFFICIAL_HOSTS:
            raise ValueError("Se requiere origen oficial verificado")
    inputs = {str(Path(p)): digest(p) for p in [catalogue_path, geojson_path, provenance_path]}
    catalogue = pd.read_csv(catalogue_path, dtype=str, keep_default_na=False)
    frame = normalize_boundaries(
        json.loads(Path(geojson_path).read_text()), catalogue, id_property, source_crs
    )
    # Validación antes de publicar el directorio final.
    import tempfile

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "municipality_boundaries.parquet"
        frame.to_parquet(path, index=False)
        manifest = {**provenance, "sha256": digest(path)}
        save_json(Path(temp) / "manifest.json", manifest)
        load_official_boundaries(path, Path(temp) / "manifest.json")
    union = sh.union_all(sh.from_wkt(frame.geometry_wkt.to_numpy()))
    rings = [ring for polygon in sh.get_parts(union) for ring in polygon.interiors]
    quality = dict(
        municipalities=len(frame),
        invalid=0,
        multipart=int(frame.multipart.sum()),
        union_area_km2=union.area / 1e6,
        interior_holes=len(rings),
        interior_holes_km2=sum(sh.Polygon(r).area for r in rings) / 1e6,
        regional_completeness="requires_independent_province_boundary_comparison",
    )
    output.mkdir(parents=True)
    frame.to_parquet(output / "municipality_boundaries.parquet", index=False)
    frame.drop(columns="geometry_wkt").to_parquet(output / "municipalities.parquet", index=False)
    save_json(
        output / "municipality_catalog.json", frame.drop(columns="geometry_wkt").to_dict("records")
    )
    save_json(output / "quality.json", quality)
    save_json(
        output / "manifest.json",
        {
            **manifest,
            "version": "regional-territory-v1",
            "inputs": inputs,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_crs": source_crs,
            "outputs": {p.name: digest(p) for p in output.iterdir() if p.is_file()},
        },
    )
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ["catalogue", "geojson", "provenance", "output-dir"]:
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--id-property", required=True)
    parser.add_argument("--source-crs", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.catalogue,
                args.geojson,
                args.provenance,
                args.output_dir,
                args.id_property,
                args.source_crs,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
