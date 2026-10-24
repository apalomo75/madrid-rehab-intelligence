"""Lectura verificable de productos locales. Nunca recalcula features ni usa red."""

import json
from pathlib import Path

import pandas as pd

from .ingest import digest
from .profiles import add_profiles

PRODUCTS = (
    "parcel_features.parquet",
    "coverage.json",
    "audit.json",
    "energy_observations.parquet",
    "sensitivity_summary.parquet",
)


def snapshot_signature(root):
    """Invalidación barata: metadatos de todos los archivos leídos, incluido manifiesto."""
    root = Path(root)
    paths = [root / "manifest.json"] + [root / name for name in PRODUCTS if (root / name).exists()]
    return tuple(
        (p.name, p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


def load_snapshot(root, signature):
    """Comprueba hashes al cargar/invalida caché si cambia archivo o manifiesto."""
    root = Path(root)
    if signature != snapshot_signature(root):
        raise ValueError("El producto cambió antes de la lectura; vuelve a cargar")
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("version") not in {"session6-v1", "session6-v2"}:
        raise ValueError("Versión analítica no soportada")
    required = ["parcel_features.parquet", "coverage.json"]
    if manifest["version"] == "session6-v2":
        required = list(PRODUCTS)
    result = {"manifest": manifest}
    for name in required:
        # Nombres constantes: nunca abrir rutas proporcionadas por el manifiesto.
        if digest(root / name) != manifest["outputs"][name]:
            raise ValueError(f"El perfil no coincide con su manifiesto: {name}")
        if name.endswith(".parquet"):
            result[name] = pd.read_parquet(root / name)
        else:
            result[name] = json.loads((root / name).read_text())
    if signature != snapshot_signature(root):
        raise ValueError("El producto cambió durante la lectura")
    result["parcel_features.parquet"] = add_profiles(result["parcel_features.parquet"])
    return result
