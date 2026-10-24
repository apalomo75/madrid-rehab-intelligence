"""Importación SQLite/OGC del GeoPackage IDEM, sin atribuir comunidades compartidas."""

import argparse
import json
import math
import sqlite3
import struct
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import shapely as sh

from .ingest import digest, save_json
from .normalize import text_key
from .regional import load_official_boundaries

SOURCE = Path("data/raw/territory/madrid/unidades_administrativas.gpkg")
DEFAULT = Path("data/processed/territory/session_12_1_final_01")
SOURCE_URL = "https://idem.comunidad.madrid/geoidem/UnidadesAdministrativas/ows"
LAYER = "IDEM_CM_UNID_ADMIN"


def decode_gpkg(blob, expected_srs=25830):
    """OGC GeoPackageBinary v0: flags, endian, SRS, envelope y WKB estándar."""
    if not isinstance(blob, bytes) or len(blob) < 9 or blob[:2] != b"GP" or blob[2] != 0:
        raise ValueError("Cabecera GeoPackage inválida")
    flags = blob[3]
    envelope = (flags >> 1) & 7
    if flags & 0xE0 or flags & 0x10 or envelope > 4:
        raise ValueError("Geometría extendida, vacía o flags reservados")
    endian = "<" if flags & 1 else ">"
    srs = struct.unpack(endian + "i", blob[4:8])[0]
    if srs != expected_srs:
        raise ValueError("SRS del blob incompatible")
    count = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}[envelope]
    offset = 8 + count * 8
    if len(blob) <= offset or blob[offset] not in (0, 1):
        raise ValueError("Envelope truncado o WKB inválido")
    values = struct.unpack(endian + "d" * count, blob[8:offset]) if count else ()
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Envelope no finito")
    if any(values[i] > values[i + 1] for i in range(0, count, 2)):
        raise ValueError("Envelope invertido")
    try:
        geom = sh.from_wkb(blob[offset:])
    except sh.errors.GEOSException as exc:
        raise ValueError("WKB inválido") from exc
    if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Geometría vacía, inválida o no poligonal")
    if values:
        minx, miny, maxx, maxy = geom.bounds
        if not all(abs(a - b) <= 1e-6 for a, b in zip(values[:4], (minx, maxx, miny, maxy))):
            raise ValueError("Envelope contradice WKB")
    return geom


def read_entities(source):
    source = Path(source)
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("SQLite corrupto")
        content = dict(
            conn.execute("SELECT * FROM gpkg_contents WHERE table_name=?", (LAYER,)).fetchone()
        )
        column = dict(
            conn.execute(
                "SELECT * FROM gpkg_geometry_columns WHERE table_name=?", (LAYER,)
            ).fetchone()
        )
        if (
            column["srs_id"] != 25830
            or column["column_name"] != "GEOMETRY1"
            or column["z"]
            or column["m"]
        ):
            raise ValueError("Contrato de capa/CRS no reconocido")
        rows = []
        for record in conn.execute("SELECT * FROM IDEM_CM_UNID_ADMIN ORDER BY fid"):
            row = dict(record)
            geom = decode_gpkg(row.pop("GEOMETRY1"))
            minx, miny, maxx, maxy = geom.bounds
            if not (300000 < minx < maxx < 520000 and 4400000 < miny < maxy < 4600000):
                raise ValueError("Posición incompatible con CRS/región")
            description = text_key(row["DS_DESCRIPCION"])
            kind = (
                "municipality"
                if description == "TERMINO MUNICIPAL"
                else "enclave"
                if description == "ENCLAVE"
                else "joint_jurisdiction"
                if description.startswith("COMUNIDAD JURISDICCIONAL")
                else None
            )
            if kind is None:
                raise ValueError("Tipo administrativo desconocido")
            row.update(
                entity_kind=kind,
                geometry_wkt=geom.wkt,
                geometry_crs="EPSG:25830",
                area_km2=geom.area / 1e6,
                geometry_type=geom.geom_type,
                validation_status="validated",
            )
            rows.append(row)
    frame = pd.DataFrame(rows)
    terms = frame[frame.entity_kind.eq("municipality")]
    if (
        len(frame) != 194
        or frame.CD_INE.nunique() != 179
        or len(terms) != 179
        or not terms.CD_INE.is_unique
    ):
        raise ValueError("Captura inesperada: revisar recuentos e identidad")
    if frame.entity_kind.value_counts().to_dict() != {
        "municipality": 179,
        "enclave": 13,
        "joint_jurisdiction": 2,
    }:
        raise ValueError("Distribución administrativa inesperada")
    return frame, {"contents": content, "geometry_column": column}


def overlap_report(frame):
    geometries = sh.from_wkt(frame.geometry_wkt.to_numpy())
    tree = sh.STRtree(geometries)
    result = []
    for i, geom in enumerate(geometries):
        for j in tree.query(geom, predicate="intersects"):
            if j > i:
                area = geom.intersection(geometries[j]).area
                if area > 0.001:
                    result.append(
                        dict(
                            fid_a=int(frame.iloc[i].fid), fid_b=int(frame.iloc[j].fid), area_m2=area
                        )
                    )
    return result


def normalize(source=SOURCE, output=DEFAULT):
    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError("Usar salida nueva")
    entities, metadata = read_entities(source)
    overlaps = overlap_report(entities)
    if overlaps:
        raise ValueError("Solapamientos: requieren revisión antes de clasificar")
    terms = entities[entities.entity_kind.eq("municipality")]
    shared = entities[entities.entity_kind.eq("joint_jurisdiction")]
    rows = []
    for term in terms.itertuples():
        selected = entities[
            entities.CD_INE.eq(term.CD_INE) & ~entities.entity_kind.eq("joint_jurisdiction")
        ]
        # Solo anexar enclaves con atribución explícita CD_INE en la fuente.
        if (
            not selected.DS_NOMBRE.map(text_key).eq(text_key(term.DS_NOMBRE)).all()
            or selected.CD_INE_1.notna().any()
        ):
            raise ValueError("Atribución de enclave no resuelta")
        geom = sh.union_all(sh.from_wkt(selected.geometry_wkt.to_numpy()))
        rows.append(
            dict(
                municipality_code=term.CD_INE,
                name=term.DS_NOMBRE,
                geometry_wkt=geom.wkt,
                geometry_crs="EPSG:25830",
                area_km2=geom.area / 1e6,
                source_fids=json.dumps(selected.fid.tolist()),
                validation_status="validated_excluding_joint_jurisdictions",
                source_sha256=digest(source),
            )
        )
    municipalities = pd.DataFrame(rows).sort_values("municipality_code").reset_index(drop=True)
    inventory_path = Path("data/processed/territory/session_12_final_01/cadastre_resources.parquet")
    resources = pd.read_parquet(inventory_path)
    # Comparación informativa por nombre completo; no autoriza importación catastral.
    comparisons = []
    for r in municipalities.itertuples():
        matches = resources[resources.cadastre_name.map(text_key).eq(text_key(r.name))]
        comparisons.append(
            dict(
                municipality_code=r.municipality_code,
                name=r.name,
                cadastre_candidates=json.dumps(matches.cadastre_code.tolist()),
                status="exact_name_candidate_requires_identity_review"
                if len(matches) == 1
                else "requires_review",
                import_authorized=False,
            )
        )
    output.mkdir(parents=True)
    tables = {
        "administrative_entities": entities,
        "joint_jurisdictions": shared,
        "municipality_boundaries": municipalities,
        "municipalities": municipalities.drop(columns="geometry_wkt"),
        "cadastre_comparison": pd.DataFrame(comparisons),
    }
    for name, frame in tables.items():
        frame.to_parquet(output / f"{name}.parquet", index=False)
    quality = dict(
        entities=len(entities),
        municipalities=len(terms),
        enclaves=13,
        joint_jurisdictions=2,
        valid_geometries=194,
        overlaps=overlaps,
        municipality_area_km2=float(municipalities.area_km2.sum()),
        shared_area_km2=float(shared.area_km2.sum()),
        completeness="No independent regional boundary comparison; joint jurisdictions excluded from municipal assignment",
    )
    save_json(output / "quality.json", quality)
    manifest = dict(
        version="idem-gpkg-v1",
        source_url=SOURCE_URL,
        layer="UnidadesAdministrativas:" + LAYER,
        publisher="Comunidad de Madrid · IDEM",
        license="unverified_local_only",
        redistribution_verified=False,
        source_date="unknown",
        capture_date_evidence="User supplied capture; GeoPackage last_change is container metadata, not source date",
        container_last_change=metadata["contents"]["last_change"],
        filesystem_mtime_utc=datetime.fromtimestamp(
            source.stat().st_mtime, timezone.utc
        ).isoformat(),
        source_size=source.stat().st_size,
        source_sha256=digest(source),
        metadata=metadata,
        sha256=digest(output / "municipality_boundaries.parquet"),
        inputs={str(source): digest(source), str(inventory_path): digest(inventory_path)},
        outputs={p.name: digest(p) for p in output.iterdir() if p.is_file()},
    )
    save_json(output / "manifest.json", manifest)
    load_official_boundaries(output / "municipality_boundaries.parquet", output / "manifest.json")
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(normalize(args.source, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
