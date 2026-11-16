"""Authenticated catalogue queries; commercial membership never falls back to all CP."""

from contextlib import closing, contextmanager
from functools import lru_cache
import json
import os
from pathlib import Path
import sqlite3

import pandas as pd

from . import demo, address_search
from .commercial_catalog import DEFAULT, VERSION, PUBLIC_SOURCES
from .data_recovery_audit import CITY, ENERGY, CONSERVATION, PARTIAL
from .ingest import digest

INSUFFICIENT = "No hay información suficiente para ofrecer una ficha comercial de esta dirección."


def root_path():
    from . import production_bundle as bundle

    if bundle.active():
        return bundle.catalogue()
    return Path(os.environ.get("MADRID_REHAB_CATALOG_DIR", str(DEFAULT)))


def mode():
    return "local" if demo.private() else "public"


def signature(root):
    from . import production_bundle as bundle

    if bundle.active():
        return bundle.signature()
    meta = json.loads((root / "manifest.json").read_text())
    paths = [
        root / "manifest.json",
        *[root / n for n in meta["outputs"]],
        *map(Path, meta["inputs"]),
    ]
    return tuple(
        (str(p), p.stat().st_size, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in paths
    )


@lru_cache(maxsize=4)
def _verify(root, token):
    root = Path(root)
    meta = json.loads((root / "manifest.json").read_text())
    if meta.get("version") != VERSION or meta.get("validation_status") != "validated":
        raise ValueError("Catálogo incompatible")
    if meta["policy"]["publication_sources"] != PUBLIC_SOURCES:
        raise ValueError("Permisos públicos incompatibles")
    for name, expected in meta["inputs"].items():
        if digest(Path(name)) != expected:
            raise ValueError("Catálogo desactualizado: " + name)
    for name, expected in meta["outputs"].items():
        if digest(root / name) != expected:
            raise ValueError("Catálogo alterado: " + name)
    return meta


def metadata():
    from . import production_bundle as bundle

    if bundle.active():
        return bundle.metadata()
    root = root_path()
    meta = _verify(str(root), signature(root))
    expected_paths = {
        "MADRID_REHAB_SESSION7_DIR": CITY,
        "MADRID_REHAB_ENERGY_DIR": ENERGY,
        "MADRID_REHAB_CONSERVATION_DIR": CONSERVATION,
        "MADRID_REHAB_CADASTRE_DIR": PARTIAL,
        "MADRID_REHAB_ADDRESS_DIR": address_search.DEFAULT,
        "MADRID_REHAB_REHABILITA_DIR": Path("data/processed/plan_rehabilita/session_23_01"),
        "MADRID_REHAB_ADMIN_DIR": Path("data/processed/administrative_events/session_10_final_01"),
    }
    for variable, expected in expected_paths.items():
        if Path(os.environ.get(variable, str(expected))).resolve() != expected.resolve():
            raise ValueError("Captura activa incompatible con catálogo: " + variable)
    from .regional_view import regional_root_path

    if regional_root_path().resolve() != PARTIAL.resolve():
        raise ValueError("Captura regional incompatible")
    return meta


@contextmanager
def connect():
    metadata()
    db = sqlite3.connect(
        (root_path() / "catalogue.sqlite").resolve().as_uri() + "?mode=ro", uri=True
    )
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


def parcel(code, ref):
    if code not in address_search.NAMES:
        return None
    with connect() as db:
        row = db.execute(
            "SELECT * FROM parcels WHERE municipality_code=? AND parcel_ref14=? AND "
            + mode()
            + "_visible=1",
            (code, ref),
        ).fetchone()
    return dict(row) if row else None


def parcel_index(code, evidence=None):
    if code not in address_search.NAMES:
        raise ValueError("Municipio fuera del MVP")
    conditions = ["municipality_code=?", mode() + "_visible=1"]
    if evidence:
        if evidence not in {"construction", "energy", "administrative", "prtr", "rehabilita"}:
            raise ValueError("Filtro de evidencia inválido")
        # Authorization is checked separately from presence of a restricted source.
        if mode() == "public" and not PUBLIC_SOURCES[evidence]:
            return pd.DataFrame(columns=["parcel_ref14", "x", "y", "zone"])
        conditions.append(evidence + "=1")
    root = root_path()
    metadata()
    return _parcel_index(
        str(root), signature(root), code, mode(), tuple(conditions), evidence
    ).copy(deep=True)


@lru_cache(maxsize=12)
def _parcel_index(root, token, code, active_mode, conditions, evidence):
    columns = "parcel_ref14,x,y,zone,construction,energy,administrative,prtr,rehabilita,local_level,public_level"
    with closing(
        sqlite3.connect((Path(root) / "catalogue.sqlite").resolve().as_uri() + "?mode=ro", uri=True)
    ) as db:
        result = pd.read_sql_query(
            "SELECT "
            + columns
            + " FROM parcels WHERE "
            + " AND ".join(conditions)
            + " ORDER BY parcel_ref14",
            db,
            params=(code,),
        )
        from . import production_bundle as bundle

        if bundle.active():
            for column in ("zone", "local_level", "public_level"):
                result[column] = result[column].astype("category")
            for column in ("construction", "energy", "administrative", "prtr", "rehabilita"):
                result[column] = result[column].astype(bool)
        return result


def search(code, street, number="", complement="", limit=100, offset=0):
    alias, num, extra = address_search.parse_query(street, number, complement)
    if not alias or code != "28079":
        return [], 0, False
    conditions = ["s.municipality=?", "s.alias=?", "a.municipality=?"]
    params = [code, alias, code]
    if num:
        conditions.append("a.number_key=?")
        params.append(num)
    if extra:
        conditions.append("a.complement_key=?")
        params.append(extra)
    base = " FROM aliases s CROSS JOIN addresses a ON a.id=s.id WHERE " + " AND ".join(conditions)
    with connect() as db:
        found_original = bool(db.execute("SELECT 1" + base + " LIMIT 1", params).fetchone())
        selected = base + " AND a." + mode() + "_visible=1"
        total = db.execute("SELECT COUNT(DISTINCT a.id)" + selected, params).fetchone()[0]
        rows = db.execute(
            "SELECT DISTINCT a.*" + selected + " ORDER BY a.original,a.id LIMIT ? OFFSET ?",
            [*params, min(max(limit, 1), 100), max(offset, 0)],
        ).fetchall()
    result = []
    for row in rows:
        record = dict(row)
        record["original_refs"] = record["refs"]
        record["refs"] = record[mode() + "_refs"]
        result.append(record)
    return result, total, found_original


def suggest(code, street):
    key = address_search.street_key(street)
    if len(key) < 2 or code != "28079":
        return []
    with connect() as db:
        rows = db.execute(
            "SELECT DISTINCT s.alias FROM aliases s JOIN addresses a ON a.id=s.id WHERE s.municipality=? AND s.alias>=? AND s.alias<? AND a."
            + mode()
            + "_visible=1 ORDER BY s.alias LIMIT 20",
            (code, key, key + "\uffff"),
        ).fetchall()
    return [r[0] for r in rows]
