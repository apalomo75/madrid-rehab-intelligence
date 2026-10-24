"""Lectura de productos municipales pequeños y de un solo distrito, con integridad."""

import json
from pathlib import Path

import pandas as pd

from .ingest import digest
from .territory import CODES

OVERVIEW = (
    "district_summary.parquet",
    "districts.parquet",
    "source_coverage.json",
    "reconciliation.json",
)
DETAIL = (
    "map_buildings.parquet",
    "map_parcels.parquet",
    "certificates.parquet",
    "contexts.parquet",
    "links.parquet",
)


def checked_code(code):
    if code not in CODES:
        raise ValueError("Código distrital no admitido")
    return code


def signature(root, code=None):
    root = Path(root)
    paths = [root / "manifest.json"]
    if code is None:
        paths += [root / name for name in OVERVIEW]
    else:
        partition = root / "districts" / checked_code(code)
        paths += [partition / "manifest.json"] + [partition / name for name in DETAIL]
    return tuple(
        (
            str(path.relative_to(root)),
            path.stat().st_size,
            path.stat().st_mtime_ns,
            path.stat().st_ctime_ns,
        )
        for path in paths
    )


def read_manifest(root):
    metadata = json.loads((Path(root) / "manifest.json").read_text())
    if metadata.get("version") != "session7-v1" or metadata.get("city") != "madrid":
        raise ValueError("Producto municipal no soportado")
    return metadata


def partition_manifest(root, code):
    root = Path(root)
    metadata = read_manifest(root)
    if checked_code(code) not in metadata["available_districts"]:
        raise ValueError("Distrito no generado en esta captura")
    partition = root / "districts" / code
    if digest(partition / "manifest.json") != metadata["district_manifests"][code]:
        raise ValueError("Manifiesto distrital no coincide con captura municipal")
    declared = json.loads((partition / "manifest.json").read_text())
    if declared["district_code"] != code or declared["city_version"] != "session7-v1":
        raise ValueError("Producto de otro distrito o versión")
    return declared


def load_overview(root, token):
    root = Path(root)
    if token != signature(root):
        raise ValueError("Captura cambiada antes de leer")
    metadata = read_manifest(root)
    result = {"manifest": metadata}
    for name in OVERVIEW:
        path = root / name
        if digest(path) != metadata["outputs"][name]:
            raise ValueError(f"Producto municipal alterado: {name}")
        result[name] = (
            pd.read_parquet(path) if name.endswith(".parquet") else json.loads(path.read_text())
        )
    if token != signature(root):
        raise ValueError("Captura cambió durante lectura")
    return result


def load_district(root, code, token):
    root = Path(root)
    if token != signature(root, code):
        raise ValueError("Distrito cambiado antes de lectura")
    metadata = partition_manifest(root, code)
    result = {"manifest": metadata}
    for name in DETAIL:
        path = root / "districts" / code / name
        if digest(path) != metadata["outputs"][name]:
            raise ValueError(f"Producto distrital alterado: {name}")
        result[name] = pd.read_parquet(path)
    if token != signature(root, code):
        raise ValueError("Distrito cambió durante lectura")
    return result
