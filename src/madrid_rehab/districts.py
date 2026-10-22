"""Límites oficiales: captura acotada y asignación espacial conservadora en EPSG:25830."""

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shapely as sh
from pyproj import Transformer
from shapely.ops import transform

from .ingest import digest, save_json

SERVICE = (
    "https://sigma.madrid.es/hosted/rest/services/CARTOGRAFIA/LIMITES_ADMINISTRATIVOS/MapServer"
)
LAYER = SERVICE + "/26"
CATALOG = "https://datos.madrid.es/dataset/300497-0-distritos-municipales-madrid"
LIMIT = 8 * 1024**2


def capture(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    urls = {
        "service.json": SERVICE + "?f=json",
        "layer.json": LAYER + "?f=json",
        "districts.geojson": LAYER
        + "/query?"
        + urllib.parse.urlencode(
            {
                "where": "1=1",
                "outFields": "COD_DIS_TX,NOMBRE,FCH_ALTA,FCH_BAJA",
                "returnGeometry": "true",
                "outSR": "4326",
                "orderByFields": "COD_DIS_TX",
                "f": "geojson",
            }
        ),
    }
    for name, url in urls.items():
        path = root / name
        meta = root / (name + ".meta.json")
        if path.exists() and meta.exists():
            data = json.loads(meta.read_text())
            if data["url"] != url or data["sha256"] != digest(path):
                raise ValueError("Límite oficial o metadato de caché alterado")
            continue
        request = urllib.request.Request(
            url, headers={"User-Agent": "MadridRehab/0.2 official-districts"}
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            if urllib.parse.urlsplit(response.geturl()).hostname != "sigma.madrid.es":
                raise ValueError("Redirección fuera del origen oficial")
            body = response.read(LIMIT + 1)
            if len(body) > LIMIT:
                raise ValueError("Límites administrativos superan el tope de 8 MiB")
            payload = json.loads(body)
            if "error" in payload or payload.get("exceededTransferLimit"):
                raise ValueError("Respuesta municipal incompleta o con error")
            if name == "districts.geojson" and len(payload.get("features", [])) != 21:
                raise ValueError("Se esperaban los 21 distritos municipales")
            path.write_bytes(body)
            save_json(
                meta,
                {
                    "url": url,
                    "sha256": digest(path),
                    "bytes": len(body),
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "headers": dict(response.headers),
                    "catalog_url": CATALOG,
                    "attribution": "Ayuntamiento de Madrid, Departamento de Cartografía",
                    "license": "CC BY 4.0",
                    "crs": "EPSG:4326 (outSR explícito)",
                },
            )
        print(f"Capturado {name}: {len(body):,} bytes", flush=True)
    load(root)  # Validar antes de dar la captura por utilizable.


def load(root):
    root = Path(root)
    path = root / "districts.geojson"
    meta = json.loads((root / "districts.geojson.meta.json").read_text())
    if meta["sha256"] != digest(path):
        raise ValueError("SHA-256 de límites no coincide")
    payload = json.loads(path.read_bytes())
    if payload.get("type") != "FeatureCollection" or len(payload["features"]) != 21:
        raise ValueError("Límites oficiales incompletos")
    transformer = Transformer.from_crs(4326, 25830, always_xy=True)
    rows = []
    for f in payload["features"]:
        p = f["properties"]
        geometry = transform(transformer.transform, sh.geometry.shape(f["geometry"]))
        if (
            geometry.geom_type not in ("Polygon", "MultiPolygon")
            or not geometry.is_valid
            or geometry.is_empty
        ):
            raise ValueError("Polígono de distrito inválido")
        rows.append(
            {
                "district_code": str(p["COD_DIS_TX"]).zfill(2),
                "district_name": p["NOMBRE"],
                "geometry_wkt": geometry.wkt,
                "geometry_crs": "EPSG:25830",
                "source_url": meta["url"],
                "source_sha256": meta["sha256"],
                "captured_at": meta["captured_at"],
                "source_created_ms": p.get("FCH_ALTA"),
            }
        )
    frame = pd.DataFrame(rows).sort_values("district_code").reset_index(drop=True)
    if frame.district_code.nunique() != 21 or not set(["07", "11", "12"]) <= set(
        frame.district_code
    ):
        raise ValueError("Códigos distritales incompletos/duplicados")
    geometries = sh.from_wkt(frame.geometry_wkt.to_numpy())
    for i, g in enumerate(geometries):
        for other in geometries[i + 1 :]:
            if g.intersection(other).area > 0.01:
                raise ValueError("Distritos solapados en superficie")
    return frame, meta


def assign(geometries, districts, polygon=True):
    """Punto interior para asignar; cruces de superficie se conservan como indicador aparte."""
    areas = sh.from_wkt(districts.geometry_wkt.to_numpy())
    tree = sh.STRtree(areas)
    geometries = np.asarray(geometries, dtype=object)
    usable = sh.is_valid(geometries) & ~sh.is_empty(geometries)
    points = sh.point_on_surface(geometries) if polygon else geometries
    codes = [[] for _ in geometries]
    # intersects cuenta puntos sobre el límite en ambos lados: no elegir uno arbitrariamente.
    if usable.any():
        indices, matches = tree.query(points[usable], predicate="intersects")
        source_indices = np.flatnonzero(usable)
        for i, j in zip(source_indices[indices], matches):
            codes[i].append(str(districts.iloc[j].district_code))
    result = pd.DataFrame(
        {
            "district_code": [c[0] if len(c) == 1 else None for c in codes],
            "district_assignment": [
                "assigned" if len(c) == 1 else "boundary_ambiguous" if len(c) > 1 else "unassigned"
                for c in codes
            ],
        }
    )
    crossings = np.zeros(len(geometries), dtype=bool)
    if polygon:
        touched = [[] for _ in geometries]
        if usable.any():
            indices, matches = tree.query(geometries[usable], predicate="intersects")
            source_indices = np.flatnonzero(usable)
            for i, j in zip(source_indices[indices], matches):
                if geometries[i].intersection(areas[j]).area > 0.01:
                    touched[i].append(j)
        crossings = np.array([len(t) > 1 for t in touched])
    result["crosses_district_boundary"] = crossings
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default="data/raw/session_2/districts")
    args = parser.parse_args()
    capture(args.raw_dir)


if __name__ == "__main__":
    main()
