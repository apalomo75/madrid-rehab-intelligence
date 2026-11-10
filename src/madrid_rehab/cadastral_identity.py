"""Stable cadastral identity resolution independent of map and navigation state."""

import os
import re
import logging

import pandas as pd

from . import demo


def object_source(code, kind):
    if kind == "cp":
        return demo.cp_source(code)
    if kind != "bu":
        raise ValueError("Tipo catastral desconocido")
    override = os.environ.get("MADRID_REHAB_CADASTRE_DIR")
    if override and code != "28079":
        return demo.Path(override) / code, "bu.parquet"
    return (
        (demo.CITY, "buildings_audited.parquet")
        if code == "28079"
        else (demo.CADASTRE, f"{code}/bu.parquet")
    )


def resolve_object(code, identifier, kind):
    """Resolve a municipal domain identity without collapsing ambiguity."""
    empty = pd.DataFrame()
    if kind not in {"cp", "bu"} or not isinstance(identifier, str) or not identifier:
        return "identificador inválido", empty
    if kind == "cp":
        identifier = identifier.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{14}", identifier):
            return "identificador inválido", empty
    try:
        root, relative = object_source(code, kind)
        field = "parcel_ref14" if kind == "cp" else "building_id"
        result = demo.read(root, relative, [(field, "==", identifier)])
        if result.empty:
            return "objeto no disponible", empty
        if len(result) != 1:
            return "referencia ambigua", empty
        row = result.iloc[0]
        if "municipality_code" in result and str(row.municipality_code) != code:
            return "incompatibilidad municipal", empty
        if not bool(row.usable_geometry) or (
            "selection_status" in result and row.selection_status != "accepted"
        ):
            return "objeto no utilizable", empty
        return "CP encontrada y aceptada" if kind == "cp" else "BU encontrado y utilizable", result
    except Exception:
        logging.getLogger(__name__).exception("Cadastral read failed: %s %s", code, kind)
        return "error de lectura", empty


def construction_records(code, cp, columns=None):
    """Expose existing Madrid BU attributes without creating pilot BU/CP relations."""
    if code != "28079":
        return pd.DataFrame()
    from pathlib import Path
    from .city_store import partition_manifest

    DEFAULT = Path(__file__).resolve().parents[2] / "data/processed/session_7_final"

    district = cp.iloc[0].get("district_code")
    if not isinstance(district, str) or len(district) != 2:
        return pd.DataFrame()
    root = Path(os.environ.get("MADRID_REHAB_SESSION7_DIR", str(DEFAULT)))
    metadata = partition_manifest(root, district)
    path = root / "districts" / district / "map_buildings.parquet"
    if demo.digest(path) != metadata["outputs"][path.name]:
        raise ValueError("Registros constructivos alterados")
    records = pd.read_parquet(
        path, filters=[("parcel_ref14", "==", cp.iloc[0].parcel_ref14)], columns=columns
    )
    return records
