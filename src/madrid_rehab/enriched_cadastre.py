"""Selective, authenticated access to immutable session 18 pilot products."""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from . import demo

ROOT = Path("data/processed/cadastre/session_18_enriched_01")
ATTRIBUTES = {
    "current_use": "Uso declarado",
    "construction_begin": "Inicio constructivo declarado",
    "construction_end": "Fin constructivo declarado",
    "dwellings": "Viviendas declaradas",
    "building_units": "Unidades declaradas",
    "floors_above": "Plantas sobre rasante",
    "floors_below": "Plantas bajo rasante",
    "height_below": "Altura bajo rasante (m)",
    "height_above": "Altura sobre rasante (m)",
    "official_area": "Superficie bruta de plantas (m²)",
    "condition": "Condición catastral declarada",
}
SUMMARY_COLUMNS = ["building_id", "source_feature_type"] + [
    "recovered_" + key for key in ATTRIBUTES
]


def signature(code):
    directory = ROOT / code
    paths = [ROOT / "manifest.json", directory / "manifest.json"]
    paths += sorted(p for p in directory.iterdir() if p.is_file() and p.name != "manifest.json")
    source, relative = demo.cp_source(code)
    paths += [source / "manifest.json", source / relative]
    return tuple(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


@lru_cache(maxsize=8)
def _verify(code, token):
    collection = json.loads((ROOT / "manifest.json").read_text())
    directory = ROOT / code
    if (
        collection.get("version") != "cadastre-enriched-collection-v1"
        or collection.get("validation_status") != "validated"
    ):
        raise ValueError("Colección enriquecida no validada")
    if demo.digest(directory / "manifest.json") != collection["outputs"][code + "/manifest.json"]:
        raise ValueError("Manifiesto municipal alterado")
    meta = json.loads((directory / "manifest.json").read_text())
    if (
        meta.get("municipality_code") != code
        or meta.get("validation_status") != "validated"
        or meta.get("version") != "cadastre-enriched-v1"
    ):
        raise ValueError("Partición enriquecida incompatible")
    for name, sha in meta["outputs"].items():
        if demo.digest(directory / name) != sha:
            raise ValueError("Producto enriquecido alterado: " + name)
    source, relative = demo.cp_source(code)
    historical = json.loads((source / "manifest.json").read_text())
    expected = historical["outputs"][relative]
    if expected not in meta["inputs"].values() or demo.digest(source / relative) != expected:
        raise ValueError("CP incompatible con sesión 18")
    return meta


def metadata(code):
    from . import production_bundle as bundle

    if bundle.active():
        return bundle.metadata()
    return _verify(code, signature(code))


@lru_cache(maxsize=32)
def _query(code, token, name, field, values, columns):
    _verify(code, token)
    frame = pd.read_parquet(
        ROOT / code / name, filters=[(field, "in", list(values))], columns=columns
    )
    if "municipality_code" in frame and not frame.municipality_code.eq(code).all():
        raise ValueError("Cruce municipal incompatible")
    return frame


def query(code, name, field, values, columns=None):
    from . import production_bundle as bundle

    if bundle.active():
        return bundle.read(ROOT / code / name, [(field, "in", list(values))], columns)
    return _query(
        code, signature(code), name, field, tuple(values), tuple(columns) if columns else None
    ).copy(deep=True)


def links(code, identifier, kind="cp"):
    field = "cp_reference_normalized" if kind == "cp" else "building_id"
    return query(code, "cp_bu_documentary_links.parquet", field, [identifier])


def parcel_buildings(code, ref):
    relations = links(code, ref)
    accepted = relations[relations.link_class.eq("A") & relations.relation_validated]
    ids = tuple(accepted.building_id.drop_duplicates())
    if not ids:
        return pd.DataFrame(columns=SUMMARY_COLUMNS), relations[
            ~relations.link_class.eq("A")
        ].copy()
    records = query(
        code,
        "buildings_enriched.parquet",
        "building_id",
        ids,
        [*SUMMARY_COLUMNS, "municipality_code"],
    )
    if set(records.building_id) != set(ids) or records.building_id.duplicated().any():
        raise ValueError("Identidades BU incompatibles")
    return records.sort_values("building_id"), relations[~relations.link_class.eq("A")].copy()


def building(code, identifier):
    frame = query(code, "buildings_enriched.parquet", "building_id", [identifier])
    if (
        len(frame) != 1
        or not frame.iloc[0].usable_geometry
        or frame.iloc[0].selection_status != "accepted"
    ):
        raise ValueError("BU no único o no utilizable")
    return frame


def attribute_table(row):
    evidence = json.loads(row.attributes_json)
    return pd.DataFrame(
        [
            {
                "Atributo": label,
                "Valor": row.get("recovered_" + key),
                "Estado": row.get("recovered_" + key + "_state"),
                "Original y procedencia XML": json.dumps(evidence[key], ensure_ascii=False),
            }
            for key, label in ATTRIBUTES.items()
        ]
    )


def schemas(code):
    from . import production_bundle as bundle

    if bundle.active():
        bundle.metadata()
        return {
            name: pq.read_schema(bundle.resolve(ROOT / code / name)).names
            for name in ("buildings_enriched.parquet", "cp_bu_documentary_links.parquet")
        }
    metadata(code)
    return {
        name: pq.read_schema(ROOT / code / name).names
        for name in ("buildings_enriched.parquet", "cp_bu_documentary_links.parquet")
    }
