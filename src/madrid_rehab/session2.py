"""Auditoría e integración municipal sin red. Todas las confirmaciones declaran su nivel."""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import shapely as sh
from pyproj import Transformer
from shapely.ops import transform

from . import districts as district_source
from .ingest import digest, save_json
from .normalize import split_references

VERSION = "session2-v1"
CANDIDATES = ["07", "11", "12"]
URBAN = r"[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]"
RURAL = r"[0-9]{5}[A-Z][0-9]{8}"
STATES = ["confirmed", "candidate", "ambiguous", "unmatched"]


def normalize_reference(value):
    raw = "" if value is None or pd.isna(value) else str(value)
    value = re.sub(r"\s+", "", raw.upper())
    base = f"(?:{URBAN}|{RURAL})"
    valid = bool(re.fullmatch(base + r"(?:[0-9]{4}[A-Z]{2})?", value))
    return {
        "reference_raw": raw,
        "reference_normalized": value,
        "format_valid": valid,
        "reference_kind": "property"
        if valid and len(value) == 20
        else "parcel"
        if valid
        else "unsupported",
        "parcel_ref14": value[:14] if valid else None,
        "property_ref20": value if valid and len(value) == 20 else None,
        "checksum_status": "not_checked" if valid and len(value) == 20 else "not_applicable",
    }


def geometry_audit(frame):
    frame = frame.copy().reset_index(drop=True)
    geometry = sh.from_wkt(frame.geometry_wkt.fillna("").to_numpy(), on_invalid="ignore")
    frame["topology_valid"] = sh.is_valid(geometry)
    frame["geometry_problem"] = sh.is_valid_reason(geometry)
    box = sh.bounds(geometry)
    envelope = (
        (box[:, 0] > 350000) & (box[:, 2] < 500000) & (box[:, 1] > 4400000) & (box[:, 3] < 4550000)
    )
    frame["usable_geometry"] = (
        frame.topology_valid
        & ~sh.is_empty(geometry)
        & frame.geometry_crs.eq("EPSG:25830")
        & envelope
        & np.isin(sh.get_type_id(geometry), [3, 6])
    )
    frame["reference_key"] = (
        frame.parcel_ref14.fillna("").str.upper().str.replace(r"\s+", "", regex=True)
    )
    return frame, geometry


def combine_status(states):
    """Estado del certificado: todas las referencias deben confirmar para confirmar el conjunto."""
    states = list(states)
    if not states:
        return "unmatched"
    if "ambiguous" in states:
        return "ambiguous"
    if all(s == "confirmed" for s in states):
        return "confirmed"
    if any(s in ("confirmed", "candidate") for s in states):
        return "candidate"
    return "unmatched"


def link(certificates, parcels, buildings):
    """Sin evidencia documental de cobertura no existe una confirmación de edificio físico."""
    parcels = parcels.sort_values("record_id").reset_index(drop=True)
    buildings = buildings.sort_values("building_id").reset_index(drop=True)
    pindex = {
        key: list(indices)
        for key, indices in parcels.groupby("reference_key", sort=True).groups.items()
        if key
    }
    bindex = {
        key: list(indices)
        for key, indices in buildings.groupby("reference_key", sort=True).groups.items()
        if key
    }
    # Códigos repetidos con referencias distintas: conflicto de identidad, nunca resolver con una fila arbitraria.
    code_refs = (
        certificates[certificates.edif_codreg.ne("")].groupby("edif_codreg").edif_refcat.nunique()
    )
    conflicting_codes = set(code_refs[code_refs > 1].index)
    rows = []
    for c in certificates.itertuples(index=False):
        raw_refs = split_references(c.edif_refcat)
        for position, raw in enumerate(raw_refs):
            ref = normalize_reference(raw)
            ps = pindex.get(ref["parcel_ref14"], []) if ref["format_valid"] else []
            bs = bindex.get(ref["parcel_ref14"], []) if ref["format_valid"] else []
            parcel_status = (
                "ambiguous" if len(ps) > 1 else "confirmed" if len(ps) == 1 else "unmatched"
            )
            parcel_reason = (
                "multiple_source_parcel_rows"
                if len(ps) > 1
                else "exact_authority_reference"
                if ps
                else "invalid_or_unsupported_reference"
                if not ref["format_valid"]
                else "reference_not_in_snapshot"
            )
            if c.edif_codreg in conflicting_codes and ps:
                parcel_status, parcel_reason = "ambiguous", "certificate_code_identity_conflict"
            # Inmueble RC20 no está enumerado en CP/BU. El sufijo no es evidencia de su existencia.
            property_status = "candidate" if ref["property_ref20"] and ps else "unmatched"
            property_reason = (
                "rc20_declared_not_verified_by_property_register"
                if ref["property_ref20"]
                else "no_rc20_declared"
            )
            if ref["property_ref20"] and parcel_status == "ambiguous":
                property_status = "ambiguous"
            if len(bs) > 1 or (bs and parcel_status == "ambiguous"):
                physical_status, physical_reason = (
                    "ambiguous",
                    "multiple_bu_or_parcel_identity_conflict",
                )
            elif len(bs) == 1 and ps:
                physical_status = "candidate"
                physical_reason = (
                    "invalid_bu_geometry"
                    if not buildings.iloc[bs[0]].usable_geometry
                    else "individual_scope_does_not_cover_bu"
                    if c.certificate_scope in ("dwelling", "building_part")
                    else "declared_whole_scope_without_physical_coverage_evidence"
                    if c.certificate_scope == "whole_building"
                    else "unknown_certificate_scope"
                )
            elif bs:
                physical_status, physical_reason = (
                    "candidate",
                    "bu_reference_without_confirmed_parcel",
                )
            else:
                physical_status, physical_reason = "unmatched", "no_bu_for_reference"
            located = []
            for i in ps:
                p = parcels.iloc[i]
                if p.usable_geometry and isinstance(p.district_code, str):
                    located.append(p.district_code)
            district = (
                located[0]
                if located and len(located) == len(ps) and len(set(located)) == 1
                else None
            )
            rows.append(
                {
                    "certificate_id": c.record_id,
                    "reference_position": position,
                    **ref,
                    "certificate_scope": c.certificate_scope,
                    "parcel_status": parcel_status,
                    "parcel_reason": parcel_reason,
                    "property_status": property_status,
                    "property_reason": property_reason,
                    "physical_status": physical_status,
                    "physical_reason": physical_reason,
                    "parcel_record_ids": [parcels.iloc[i].record_id for i in ps],
                    "candidate_building_ids": sorted(buildings.iloc[bs].building_id.tolist())
                    if bs
                    else [],
                    "confirmed_physical_building_id": None,
                    "district_code": district,
                    "district_location_quality": "confirmed_parcel"
                    if district and parcel_status == "confirmed"
                    else "candidate"
                    if district
                    else "unlocated",
                }
            )
    links = pd.DataFrame(rows)
    summaries = []
    for cid, group in links.groupby("certificate_id", sort=True):
        candidates = sorted({v for ids in group.candidate_building_ids for v in ids})
        physical_status = combine_status(group.physical_status)
        if len(candidates) > 1:
            physical_status = "ambiguous"
        codes = group.district_code.dropna().unique()
        code = codes[0] if len(codes) == 1 and group.district_code.notna().all() else None
        parcel_status = combine_status(group.parcel_status)
        summaries.append(
            {
                "record_id": cid,
                "reference_count": len(group),
                "valid_reference_count": int(group.format_valid.sum()),
                "all_references_format_valid": bool(group.format_valid.all()),
                "parcel_status": parcel_status,
                "property_status": combine_status(group.property_status),
                "physical_status": physical_status,
                "candidate_building_ids": candidates,
                "confirmed_physical_building_id": None,
                "district_code": code,
                "district_location_quality": "confirmed_parcel"
                if code and parcel_status == "confirmed"
                else "candidate"
                if code
                else "unlocated",
            }
        )
    columns = [
        "record_id",
        "edif_codreg",
        "edif_refcat",
        "edif_tipo",
        "certificate_scope",
        "certificate_date",
        "edif_fecha",
        "cal_norenovglobal",
        "cal_co2global",
        "edif_superf_numeric",
        "norenov_global_numeric",
        "norenov_co2global_numeric",
        "source_url",
        "source_urls",
        "source_years",
        "source_sha256",
        "captured_at",
    ]
    result = certificates[[c for c in columns if c in certificates]].merge(
        pd.DataFrame(summaries), on="record_id", validate="one_to_one"
    )
    return links.sort_values(["certificate_id", "reference_position"]).reset_index(
        drop=True
    ), result.sort_values("record_id").reset_index(drop=True)


def indicator(count, denominator):
    return {
        "count": int(count),
        "denominator": int(denominator),
        "percent": round(100 * count / denominator, 4) if denominator else None,
    }


def metrics_for_certificates(certificates):
    n = len(certificates)
    return {
        "total": n,
        "all_references_format_valid": indicator(certificates.all_references_format_valid.sum(), n),
        "any_reference_format_valid": indicator(certificates.valid_reference_count.gt(0).sum(), n),
        "parcel_states": {s: indicator(certificates.parcel_status.eq(s).sum(), n) for s in STATES},
        "property_states": {
            s: indicator(certificates.property_status.eq(s).sum(), n) for s in STATES
        },
        "physical_states": {
            s: indicator(certificates.physical_status.eq(s).sum(), n) for s in STATES
        },
        "district_localized": indicator(certificates.district_code.notna().sum(), n),
        "district_localized_by_quality": {
            quality: indicator(certificates.district_location_quality.eq(quality).sum(), n)
            for quality in ["confirmed_parcel", "candidate", "unlocated"]
        },
    }


def compare_districts(certificates, parcels, buildings, districts):
    rows = []
    for d in districts[districts.district_code.isin(CANDIDATES)].itertuples():
        c = certificates[certificates.district_code.eq(d.district_code)]
        p = parcels[parcels.district_code.eq(d.district_code)]
        b = buildings[buildings.district_code.eq(d.district_code)]
        linked_refs = set()
        # Medida de disponibilidad: referencias de certificados con identidad de parcela confirmada.
        for value in c.loc[c.parcel_status.eq("confirmed"), "edif_refcat"]:
            linked_refs.update(
                normalize_reference(v)["parcel_ref14"] for v in split_references(value)
            )
        mapped = b.usable_geometry
        covered = b.reference_key.isin(linked_refs) & mapped
        rows.append(
            {
                "district_code": d.district_code,
                "district_name": d.district_name,
                "parcel_rows": len(p),
                "parcel_unique_references": p.reference_key.nunique(),
                "building_objects": len(b),
                "residential_bu": int(b.current_use.eq("1_residential").sum()),
                "valid_building_geometries": int(mapped.sum()),
                "valid_geometry_percent": round(100 * mapped.mean(), 4) if len(b) else None,
                "certificates_localized": len(c),
                "confirmed_parcel_certificates": int(c.parcel_status.eq("confirmed").sum()),
                "confirmed_parcel_percent": round(100 * c.parcel_status.eq("confirmed").mean(), 4)
                if len(c)
                else None,
                "ambiguous_parcel_certificates": int(c.parcel_status.eq("ambiguous").sum()),
                "ambiguous_physical_certificates": int(c.physical_status.eq("ambiguous").sum()),
                "confirmed_physical_certificates": int(c.physical_status.eq("confirmed").sum()),
                "bu_with_parcel_energy_context": int(covered.sum()),
                "bu_parcel_context_coverage_percent": round(100 * covered.sum() / mapped.sum(), 4)
                if mapped.any()
                else None,
                "cross_boundary_bu": int(b.crosses_district_boundary.sum()),
                "cross_boundary_parcels": int(p.crosses_district_boundary.sum()),
            }
        )
    comparison = pd.DataFrame(rows)
    # Criterio fijado antes de conocer resultados: precisión de localización, geometría y carga de revisión.
    eligible = comparison[
        (comparison.certificates_localized >= 100) & (comparison.valid_geometry_percent >= 99)
    ]
    ordered = eligible.sort_values(
        ["confirmed_parcel_percent", "valid_geometry_percent", "building_objects", "district_code"],
        ascending=[False, False, True, True],
    )
    if ordered.empty:
        return comparison, {
            "status": "blocked",
            "district_code": None,
            "reason": "Ningún distrito alcanza 100 certificados localizados y 99% de geometrías válidas.",
        }
    best = ordered.iloc[0]
    return comparison, {
        "status": "selected",
        "district_code": best.district_code,
        "district_name": best.district_name,
        "method": ">=100 certificados, >=99% geometría válida; ordenar por proporción confirmada a parcela, validez geométrica, menor número de BU y código",
        "interpretation": "Calidad de localización y facilidad de revisión; no necesidad de rehabilitación ni cobertura física de certificados.",
    }


def map_objects(buildings, pilot_code):
    frame = buildings[buildings.district_code.eq(pilot_code)].copy()
    geometry = sh.from_wkt(frame.geometry_wkt.to_numpy(), on_invalid="ignore")
    frame = frame[frame.usable_geometry].copy()
    geometry = geometry[
        buildings[buildings.district_code.eq(pilot_code)].usable_geometry.to_numpy()
    ]
    simplified = sh.simplify(geometry, 0.25, preserve_topology=True)
    relative_change = np.abs(sh.area(simplified) - sh.area(geometry)) / sh.area(geometry)
    fallback = ~sh.is_valid(simplified) | sh.is_empty(simplified) | (relative_change > 0.01)
    simplified[fallback] = geometry[fallback]
    frame["display_area_change_percent"] = (
        100 * np.abs(sh.area(simplified) - sh.area(geometry)) / sh.area(geometry)
    )
    transformer = Transformer.from_crs(25830, 4326, always_xy=True)
    frame["geometry_geojson"] = [
        json.dumps(sh.geometry.mapping(transform(transformer.transform, g)), separators=(",", ":"))
        for g in simplified
    ]
    for src, target in [
        ("construction_begin", "construction_oldest_year"),
        ("construction_end", "construction_newest_year"),
    ]:
        year = pd.to_numeric(frame[src].fillna("").str.strip().str[:4], errors="coerce")
        frame[target] = year.where(year.between(1000, 2026)).astype("Int64")
    return frame.reset_index(drop=True)


def audit_table(frame, identity):
    return {
        "rows": len(frame),
        "schema": {c: str(t) for c, t in frame.dtypes.items()},
        "null_counts": {c: int(v) for c, v in frame.isna().sum().items()},
        "unique_record_ids": int(frame.record_id.nunique()),
        "distinct_official_identifiers": int(frame[identity].nunique()),
        "rows_with_duplicate_official_identifier": int(
            frame[identity].duplicated(keep=False).sum()
        ),
    }


def quality_report(metrics):
    q = metrics["certificates"]
    lines = [
        "# Calidad de integración Catastro–CEEE — sesión 2",
        "",
        f"Denominador: **{q['total']:,} versiones de registros CEEE**, no certificados administrativos únicos.",
        "",
        "| Nivel | Confirmed | Candidate | Ambiguous | Unmatched |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for level, label in [
        ("parcel_states", "Parcela"),
        ("property_states", "Inmueble RC20"),
        ("physical_states", "Edificio físico"),
    ]:
        values = q[level]
        lines.append(
            "| "
            + label
            + " | "
            + " | ".join(f"{values[s]['count']:,} ({values[s]['percent']:.2f}%)" for s in STATES)
            + " |"
        )
    lines.extend(
        [
            "",
            "Confirmed acredita únicamente el nivel indicado. Formato válido no verifica caracteres de control ni existencia de RC20. Una vivienda no presta su letra al BU. No hay documentación de cobertura física de los certificados en estas tablas; un único BU por parcela sigue siendo candidato.",
            "",
            "La localización distrital procede del punto interior de la geometría de parcela; las parcelas repetidas solo permiten distrito candidato cuando todas las filas coinciden en un mismo distrito. Las geometrías que cruzan límites conservan la geometría entera y un indicador de cruce. No se duplican al contar distritos.",
            "",
            "Unmatched significa ausente de esta captura o referencia no admitida, no inexistencia en Catastro. Una geometría inválida queda en la auditoría y se excluye del mapa, sin reparar el original.",
            "",
            "## Comparación distrital",
            "",
            metrics["district_comparison_markdown"],
            "",
            "## Selección",
            "",
            json.dumps(metrics["pilot"], ensure_ascii=False, indent=2),
            "",
            "## Resultados por ámbito y auditoría completa",
            "",
            "```json",
            json.dumps(metrics, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def markdown_table(frame):
    return (
        "| "
        + " | ".join(frame.columns)
        + " |\n| "
        + " | ".join(["---"] * len(frame.columns))
        + " |\n"
        + "\n".join(
            "| " + " | ".join(str(v) for v in row) + " |"
            for row in frame.itertuples(index=False, name=None)
        )
    )


def run(input_dir, output_dir, boundary_dir):
    source, out = Path(input_dir), Path(output_dir)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Salida no vacía: use otro directorio de sesión 2")
    # Impedir por construcción cualquier salida sobre la sesión de origen.
    if out.resolve() == source.resolve() or source.resolve() in out.resolve().parents:
        raise ValueError("La salida debe estar fuera del directorio de sesión 1")
    out.mkdir(parents=True, exist_ok=True)
    inputs = {k: source / f"{k}_madrid.parquet" for k in ["certificados", "parcelas", "edificios"]}
    hashes = {str(p): digest(p) for p in inputs.values()}
    original_metrics = source / "ingestion_metrics.json"
    if original_metrics.exists():
        declared = json.loads(original_metrics.read_text())["outputs"]
        for path in inputs.values():
            if declared[path.name]["sha256"] != hashes[str(path)]:
                raise ValueError("Entrada de sesión 1 alterada")
    cert, raw_p, raw_b = (
        pd.read_parquet(inputs[k]) for k in ["certificados", "parcelas", "edificios"]
    )
    if any(
        f.record_id.isna().any() or f.record_id.duplicated().any() for f in [cert, raw_p, raw_b]
    ):
        raise ValueError("record_id de origen nulo o repetido")
    boundaries, boundary_meta = district_source.load(boundary_dir)
    parcels, pg = geometry_audit(raw_p)
    buildings, bg = geometry_audit(raw_b)
    for frame, geom in [(parcels, pg), (buildings, bg)]:
        assignment = district_source.assign(geom, boundaries)
        for col in assignment:
            frame[col] = assignment[col]
    print("Geometrías auditadas y asignadas a distritos", flush=True)
    links, integrated = link(cert, parcels, buildings)
    comparison, pilot = compare_districts(integrated, parcels, buildings, boundaries)
    print(f"Cruces calculados. Piloto: {pilot.get('district_name', 'bloqueado')}", flush=True)
    if pilot["status"] != "selected":
        raise ValueError("Sin distrito elegible; revisar comparación antes de preparar mapa")
    display = map_objects(buildings, pilot["district_code"])
    contexts = []
    for row in links.itertuples():
        for bid in row.candidate_building_ids:
            contexts.append(
                {
                    "certificate_id": row.certificate_id,
                    "building_id": bid,
                    "parcel_status": row.parcel_status,
                    "physical_status": row.physical_status,
                    "reference_position": row.reference_position,
                }
            )
    contexts = pd.DataFrame(contexts).drop_duplicates(
        ["certificate_id", "building_id", "reference_position"]
    )
    district_summary = comparison[
        [
            "district_name",
            "building_objects",
            "certificates_localized",
            "confirmed_parcel_certificates",
            "confirmed_parcel_percent",
            "ambiguous_parcel_certificates",
            "valid_geometry_percent",
        ]
    ]
    metrics = {
        "integration_version": VERSION,
        "input_sha256": hashes,
        "normalization": {
            "urban_pattern": URBAN,
            "rural_pattern": RURAL,
            "checksum": "not_checked",
        },
        "boundaries": boundary_meta,
        "certificates": metrics_for_certificates(integrated),
        "by_scope": {
            s: metrics_for_certificates(f) for s, f in integrated.groupby("certificate_scope")
        },
        "audit": {
            k: audit_table(f, identity)
            for k, f, identity in [
                ("certificados", cert, "edif_codreg"),
                ("parcelas", raw_p, "parcel_id"),
                ("edificios", raw_b, "building_id"),
            ]
        },
        "relationships": {
            "reference_rows": len(links),
            "multi_reference_certificates": int(integrated.reference_count.gt(1).sum()),
            "parcel_reference_groups_repeated": int(
                parcels.groupby("reference_key").record_id.size().gt(1).sum()
            ),
            "repeated_parcel_references_different_geometries": int(
                parcels.groupby("reference_key").geometry_wkt.nunique().gt(1).sum()
            ),
            "bu_multiple_polygon_members": int((sh.get_num_geometries(bg) > 1).sum()),
            "parcels_multiple_bu": int(
                buildings.groupby("reference_key").building_id.nunique().gt(1).sum()
            ),
            "multiple_certificates_same_rc": int(
                cert.groupby("edif_refcat").record_id.nunique().gt(1).sum()
            ),
            "raw_scope_counts": cert.edif_tipo.value_counts().to_dict(),
            "reference_kind_counts": links.reference_kind.value_counts().to_dict(),
            "invalid_energy_grades": int(
                (
                    ~cert.cal_norenovglobal.isin(list("ABCDEFG")) & cert.cal_norenovglobal.ne("")
                ).sum()
            ),
        },
        "geometry": {
            k: {
                "rows": len(f),
                "valid_topology": int(f.topology_valid.sum()),
                "usable": int(f.usable_geometry.sum()),
                "invalid_record_ids": f.loc[~f.usable_geometry, "record_id"].tolist(),
                "district_unassigned": int(f.district_code.isna().sum()),
                "crosses_district_boundary": int(f.crosses_district_boundary.sum()),
            }
            for k, f in [("parcelas", parcels), ("edificios", buildings)]
        },
        "districts": comparison.to_dict("records"),
        "district_comparison_markdown": markdown_table(district_summary),
        "pilot": pilot,
        "display": {
            "objects": len(display),
            "simplification_meters": 0.25,
            "preserve_topology": True,
            "relative_area_change_limit_percent": 1.0,
            "max_area_change_percent": float(display.display_area_change_percent.max()),
            "external_basemap": False,
        },
        "physical_evidence": "CP/BU provide parcel identity only; no certificate-to-physical-block coverage evidence supplied.",
    }
    outputs = {
        "certificate_reference_links": links,
        "certificates_integrated": integrated,
        "parcels_audited": parcels,
        "buildings_audited": buildings,
        "districts": boundaries,
        "district_comparison": comparison,
        "building_certificate_contexts": contexts,
        "pilot_buildings": display,
        "pilot_certificates": integrated[
            integrated.record_id.isin(
                contexts.loc[contexts.building_id.isin(display.building_id), "certificate_id"]
            )
        ],
    }
    output_hashes = {}
    for name, frame in outputs.items():
        path = out / f"{name}.parquet"
        frame.to_parquet(path, index=False)
        if len(pd.read_parquet(path)) != len(frame):
            raise ValueError("Roundtrip Parquet fallido")
        output_hashes[path.name] = {"sha256": digest(path), "rows": len(frame)}
    metrics["outputs"] = output_hashes
    metrics["code_sha256"] = {
        str(p): digest(p) for p in [Path(__file__), Path(district_source.__file__)]
    }
    # Los originales se comprueban de nuevo después del trabajo completo.
    if hashes != {str(p): digest(p) for p in inputs.values()}:
        raise ValueError("Entrada modificada durante la ejecución")
    save_json(out / "quality_metrics.json", metrics)
    (out / "informe_calidad.md").write_text(quality_report(metrics))
    save_json(
        out / "run_config.json",
        {
            "input_dir": str(source),
            "boundary_dir": str(boundary_dir),
            "integration_version": VERSION,
        },
    )
    print(
        json.dumps(
            {"certificates": metrics["certificates"], "pilot": pilot}, ensure_ascii=False, indent=2
        ),
        flush=True,
    )
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="data/processed/session_1")
    parser.add_argument("--output-dir", default="data/processed/session_2")
    parser.add_argument("--boundary-dir", default="data/raw/session_2/districts")
    args = parser.parse_args()
    run(args.input_dir, args.output_dir, args.boundary_dir)


if __name__ == "__main__":
    main()
