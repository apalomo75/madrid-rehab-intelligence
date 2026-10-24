"""Integración CEEE regional offline: identidad de contenido y vínculos documentales."""

import argparse
import hashlib
import json
import resource
import zipfile
import time
from pathlib import Path

import pandas as pd

from .ingest import csv_encoding, digest, read_energy, save_json
from .normalize import reference, split_references, text_key

DEFAULT = Path("data/processed/energy/session_13_final_03")
PARTIAL = Path("data/processed/cadastre/session_12_2_partial_validated_01")
BOUNDARIES = Path("data/processed/territory/session_12_1_final_01")
GRANTS = Path("data/processed/grants/session_11_final_03")
ALIASES = {
    "Arganda de Rey": "28014",
    "Paracuellos del Jarama": "28104",
    "San Agustín de Guadalix": "28129",
    "San Lorenzo del Escorial": "28131",
    "Rivas Vaciamadrid": "28123",
    "Talamanca del Jarama": "28145",
    "Valdetorres del Jarama": "28164",
}
SCOPES = {
    "ViviendaIndividualEnBloque": "individual_unit",
    "ViviendaUnifamiliar": "individual_unit",
    "BloqueDeViviendaCompleto": "whole_building",
    "EdificioUsoTerciario": "whole_building",
    "LocalUsoTerciario": "commercial_unit",
}


def key(value):
    return " ".join(text_key(value).split())


def municipality(value, catalogue, official_code="", province=""):
    """Nombre completo exacto normalizado; nunca subcadenas o similitud difusa."""
    matches = catalogue.get(key(value), [])
    if matches and key(province) not in {"", "MADRID", "COMUNIDAD DE MADRID"}:
        return None, "municipality_conflicting"
    if official_code:
        valid_codes = {c for codes in catalogue.values() for c in codes}
        if official_code not in valid_codes or (matches and official_code not in matches):
            return None, "municipality_conflicting"
        return official_code, "municipality_verified"
    if len(matches) == 1:
        return matches[0], "municipality_verified"
    return None, "municipality_ambiguous" if matches else "municipality_unknown"


def content_ids(frame):
    columns = sorted(frame.columns)
    return frame[columns].apply(
        lambda row: hashlib.sha256(
            json.dumps(row.tolist(), ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest(),
        axis=1,
    )


def identity(frame):
    """No se colapsa contenido distinto de una misma inscripción."""
    result = frame.drop_duplicates("certificate_id").copy()
    counts = result.groupby("edif_codreg").certificate_id.nunique()
    result["identity_status"] = result.edif_codreg.map(
        lambda code: "identity_insufficient"
        if not code.strip()
        else ("identity_conflicting" if counts[code] > 1 else "unique_registration_content")
    )
    occurrences = frame.groupby("certificate_id").size()
    result["occurrence_count"] = result.certificate_id.map(occurrences)
    return result


def rating(value):
    value = str(value).strip().upper()
    return value if value in list("ABCDEFG") else None


def numeric(value):
    raw = str(value).strip()
    try:
        number = float(raw.replace(",", "."))
    except ValueError:
        return None, "missing" if not raw else "unknown_or_not_numeric"
    if not pd.notna(number) or abs(number) == float("inf"):
        return None, "non_finite"
    return number, "suspect" if number < 0 or number >= 99999 else "observed"


def parcel_links(certificates, indexes):
    rows = []
    for row in certificates.itertuples():
        refs = [reference(v) for v in split_references(row.edif_refcat)]
        valid = {r["parcel_ref14"] for r in refs if r["parcel_ref14"]}
        invalid = any(not r["reference_format_valid"] for r in refs)
        code = row.municipality_code
        index = indexes.get(code)
        for r in refs:
            ref = r["parcel_ref14"]
            reason, status = "no_documentary_identity", "E"
            if row.municipality_status != "municipality_verified":
                reason = "municipality_not_verified"
            elif getattr(row, "schema_suspect", False):
                status, reason = "D", "suspect_source_column_alignment"
            elif index is None:
                reason = "no_integrated_cp_coverage"
            elif len(valid) > 1 or (valid and invalid):
                status, reason = "D", "multiple_or_mixed_references"
            elif ref and ref in index["quarantine"]:
                status, reason = "D", "quarantined_cp"
            elif ref and index["accepted"].get(ref, 0) > 1:
                status, reason = "D", "multiple_cp_rows"
            elif ref and index["accepted"].get(ref) == 1:
                status, reason = "A", "documentary_reference_and_municipality"
            rows.append(
                {
                    "certificate_id": row.certificate_id,
                    "municipality_code": code,
                    **r,
                    "link_level": status,
                    "link_reason": reason,
                    "reference_transformation": "validated_urban_structure_prefix14"
                    if r["property_ref20"]
                    else "no_prefix_conversion",
                }
            )
    return pd.DataFrame(rows).drop_duplicates()


def combined_summary(energy_links, grant_links, grants):
    """Una fila por municipio/parcela; importes solo en tabla separada por expediente."""
    ec = (
        energy_links[energy_links.link_level.eq("A")]
        .groupby(["municipality_code", "parcel_ref14"])
        .certificate_id.nunique()
        .rename("certificate_count")
    )
    gl = grant_links[
        grant_links.match_status.isin(["confirmed", "confirmed_historical_madrid"])
    ].copy()
    gl["municipality_code"] = gl.geographic_municipality_code
    gl = gl.drop_duplicates(["expediente_id", "municipality_code", "parcel_ref14"])
    gc = (
        gl.groupby(["municipality_code", "parcel_ref14"])
        .expediente_id.nunique()
        .rename("grant_case_count")
    )
    summary = pd.concat([ec, gc], axis=1).fillna(0).astype(int).reset_index()
    summary["observation"] = summary.apply(
        lambda r: "energy_and_prtr"
        if r.certificate_count and r.grant_case_count
        else ("energy_only_in_sources" if r.certificate_count else "prtr_only_in_sources"),
        axis=1,
    )
    overlap = summary[summary.observation.eq("energy_and_prtr")][
        ["municipality_code", "parcel_ref14"]
    ]
    cases = gl.merge(overlap).expediente_id.unique()
    unique_cases = grants[grants.expediente_id.isin(cases)].drop_duplicates("expediente_id")
    return summary, unique_cases[
        ["expediente_id", "programa", "importe_centimos", "fecha_concesion", "fecha_disponible"]
    ]


def run(output, raw_dir=Path("data/raw")):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    started = time.perf_counter()
    paths = sorted(
        p
        for p in Path(raw_dir).rglob("*")
        if p.is_file() and "certific" in p.name.lower() and p.suffix in {".csv", ".zip"}
    )
    if not paths:
        raise ValueError("No hay fuentes energéticas locales")
    inputs, inventory, frames = {}, [], []

    def track(path):
        inputs[str(path)] = digest(path)
        return path

    boundaries = pd.read_parquet(track(BOUNDARIES / "municipality_boundaries.parquet"))
    catalogue = {}
    for row in boundaries.itertuples():
        catalogue.setdefault(key(row.name), []).append(row.municipality_code)
    # Variantes oficiales con artículo al final, presentes en la fuente energética.
    for row in boundaries.itertuples():
        parts = row.name.split(" ", 1)
        if parts[0] in {"El", "La", "Los", "Las"}:
            catalogue.setdefault(key(parts[1] + ", " + parts[0]), []).append(row.municipality_code)
    for alias, code in ALIASES.items():
        if code not in set(boundaries.municipality_code):
            raise ValueError("Alias sin municipio oficial")
        catalogue[key(alias)] = [code]
    catalog_path = track(Path("data/raw/session_1/catalog.json"))
    source_catalog = json.loads(catalog_path.read_text())["result"]
    for path in paths:
        source_start = time.perf_counter()
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                member = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
                with archive.open(member) as stream:
                    encoding = csv_encoding(stream)
        else:
            member = None
            with path.open("rb") as stream:
                encoding = csv_encoding(stream)
        frame = pd.concat(read_energy(track(path)), ignore_index=True).fillna("")
        meta_path = path.with_suffix(path.suffix + ".json")
        meta = json.loads(track(meta_path).read_text()) if meta_path.exists() else {}
        frame["certificate_id"] = content_ids(frame)
        frame["source_id"] = path.name
        frame["source_row"] = range(1, len(frame) + 1)
        inventory.append(
            {
                "path": str(path),
                "format": path.suffix,
                "bytes": path.stat().st_size,
                "sha256": inputs[str(path)],
                "records": len(frame),
                "captured_at": meta.get("captured_at"),
                "official_url": meta.get("url"),
                "file_last_modified": meta.get("headers", {}).get("Last-Modified"),
                "encoding": encoding,
                "zip_member": member,
                "municipality_classification": frame.apply(
                    lambda row: municipality(row.edif_muni, catalogue, province=row.edif_prov)[1],
                    axis=1,
                )
                .value_counts()
                .to_dict(),
                "madrid_records": int(
                    frame.apply(
                        lambda row: municipality(row.edif_muni, catalogue, province=row.edif_prov)[
                            0
                        ],
                        axis=1,
                    )
                    .eq("28079")
                    .sum()
                ),
                "municipalities_verified": int(
                    frame.apply(
                        lambda row: municipality(row.edif_muni, catalogue, province=row.edif_prov)[
                            0
                        ],
                        axis=1,
                    ).nunique()
                ),
                "publication_date": None,
                "province_literals": frame.edif_prov.value_counts().to_dict(),
                "catalog_resource": next(
                    (r for r in source_catalog["resources"] if r["url"] == meta.get("url")), None
                ),
                "columns": {
                    c: {
                        "missing": int(frame[c].eq("").sum()),
                        "missing_pct": float(frame[c].eq("").mean() * 100),
                        "distinct": int(frame[c].nunique()),
                    }
                    for c in frame.columns
                    if c not in {"certificate_id", "source_row"}
                },
                "categories": {
                    c: frame[c].value_counts().to_dict()
                    for c in [
                        "edif_muni",
                        "edif_tipo",
                        "edif_tiporeg",
                        "cal_norenovglobal",
                        "cal_co2global",
                    ]
                },
                "read_and_hash_seconds": time.perf_counter() - source_start,
            }
        )
        frames.append(frame)
    records = pd.concat(frames, ignore_index=True)
    certificates = identity(records)
    assigned = certificates.apply(
        lambda row: municipality(row.edif_muni, catalogue, province=row.edif_prov), axis=1
    )
    certificates["municipality_code"] = assigned.map(lambda x: x[0])
    certificates["municipality_status"] = assigned.map(lambda x: x[1])
    certificates["scope"] = certificates.edif_tipo.map(SCOPES).fillna("unknown")
    certificates["observation_date"] = pd.to_datetime(
        certificates.edif_fecha, format="%d/%m/%Y", errors="coerce"
    )
    certificates["date_semantics"] = "edif_fecha_source_meaning_unverified"
    certificates["consumption_rating"] = certificates.cal_norenovglobal.map(rating)
    certificates["emissions_rating"] = certificates.cal_co2global.map(rating)
    for source, target in [
        ("norenov_global", "consumption"),
        ("norenov_co2global", "emissions"),
        ("edif_superf", "area"),
    ]:
        numbers = certificates[source].map(numeric)
        certificates[target + "_value"] = numbers.map(lambda x: x[0])
        certificates[target + "_status"] = numbers.map(lambda x: x[1])
        certificates[target + "_unit"] = "not_verified_in_local_schema"
    certificates["date_after_capture"] = certificates.observation_date.gt(
        pd.Timestamp("2026-10-22")
    )
    certificates["schema_suspect"] = certificates.edif_tipo.isin(
        ["ElectricidadPeninsular", "21/11/2025", "18/12/2024"]
    )
    normalization_seconds = time.perf_counter() - started
    indexes = {}
    madrid_path = track(Path("data/processed/session_1/parcelas_madrid.parquet"))
    cp = pd.read_parquet(madrid_path, columns=["parcel_ref14", "geometry_valid"])
    indexes["28079"] = {
        "accepted": cp[cp.geometry_valid].parcel_ref14.value_counts().to_dict(),
        "quarantine": set(cp.loc[~cp.geometry_valid, "parcel_ref14"]),
    }
    for part in sorted(PARTIAL.glob("28*")):
        path = track(part / "cp_all.parquet")
        cp = pd.read_parquet(
            path, columns=["parcel_ref14", "reference_original", "selection_status"]
        )
        indexes[part.name] = {
            "accepted": cp.loc[cp.selection_status.eq("accepted"), "parcel_ref14"]
            .value_counts()
            .to_dict(),
            "quarantine": set(
                cp.loc[~cp.selection_status.eq("accepted"), "reference_original"].dropna()
            ),
        }
    match_start = time.perf_counter()
    links = parcel_links(certificates, indexes)
    matching_seconds = time.perf_counter() - match_start
    grants = pd.read_parquet(track(GRANTS / "grants.parquet"))
    grant_links = pd.read_parquet(track(PARTIAL / "grant_parcel_links.parquet"))
    joint, cases = combined_summary(links, grant_links, grants)
    municipalities = []
    record_muni = records.apply(
        lambda row: municipality(row.edif_muni, catalogue, province=row.edif_prov)[0], axis=1
    )
    for b in boundaries.itertuples():
        f = certificates[certificates.municipality_code.eq(b.municipality_code)]
        municipal_links = links[links.municipality_code.eq(b.municipality_code)]
        municipalities.append(
            {
                "municipality_code": b.municipality_code,
                "name": b.name,
                "source_records": int(record_muni.eq(b.municipality_code).sum()),
                "canonical_certificates": len(f),
                "exact_duplicate_occurrences": int(f.occurrence_count.sum() - len(f)),
                "conflicting_certificates": int(f.identity_status.eq("identity_conflicting").sum()),
                "valid_reference_certificates": int(
                    municipal_links.loc[
                        municipal_links.reference_format_valid, "certificate_id"
                    ].nunique()
                ),
                "confirmed_cp_certificates": int(
                    municipal_links.loc[
                        municipal_links.link_level.eq("A"), "certificate_id"
                    ].nunique()
                ),
                "ambiguous_cp_certificates": int(
                    municipal_links.loc[
                        municipal_links.link_level.eq("D"), "certificate_id"
                    ].nunique()
                ),
                "quarantine_cp_certificates": int(
                    municipal_links.loc[
                        municipal_links.link_reason.eq("quarantined_cp"), "certificate_id"
                    ].nunique()
                ),
                "no_cp_link_certificates": int(
                    municipal_links.loc[
                        municipal_links.link_level.eq("E"), "certificate_id"
                    ].nunique()
                ),
                "confirmed_bu_certificates": 0,
                "cp_integrated": b.municipality_code in indexes,
                "date_min": f.observation_date.min(),
                "date_max": f.observation_date.max(),
                **{
                    s + "_count": int(f.scope.eq(s).sum())
                    for s in ["whole_building", "individual_unit", "commercial_unit", "unknown"]
                },
                **{
                    prefix + "_" + r: int(f[column].eq(r).sum())
                    for prefix, column in [
                        ("consumption", "consumption_rating"),
                        ("emissions", "emissions_rating"),
                    ]
                    for r in "ABCDEFG"
                },
            }
        )
    summary = pd.DataFrame(municipalities)
    unknown = (
        certificates[certificates.municipality_code.isna()]
        .groupby("edif_muni")
        .size()
        .rename("records")
        .reset_index()
    )
    quality = {
        "source_files": len(paths),
        "source_records": len(records),
        "canonical_certificates": len(certificates),
        "exact_duplicate_occurrences": len(records) - len(certificates),
        "cross_capture_exact_contents": int(
            records.groupby("certificate_id").source_id.nunique().gt(1).sum()
        ),
        "identity_status": certificates.identity_status.value_counts().to_dict(),
        "conflicting_registration_ids": int(
            certificates.loc[
                certificates.identity_status.eq("identity_conflicting"), "edif_codreg"
            ].nunique()
        ),
        "municipality_status": certificates.municipality_status.value_counts().to_dict(),
        "municipalities_with_energy": int(summary.canonical_certificates.gt(0).sum()),
        "link_counts_distinct_certificates": {
            s: int(links.loc[links.link_level.eq(s), "certificate_id"].nunique()) for s in "ABCDE"
        },
        "link_reasons": links.link_reason.value_counts().to_dict(),
        "scope_counts": certificates.scope.value_counts().to_dict(),
        "missing_or_invalid_consumption_rating": int(certificates.consumption_rating.isna().sum()),
        "missing_or_invalid_emissions_rating": int(certificates.emissions_rating.isna().sum()),
        "invalid_dates": int(certificates.observation_date.isna().sum()),
        "confirmed_bu": 0,
        "confirmed_temporal_pairs": 0,
        "documented_versions": 0,
        "parcel_categories": joint.observation.value_counts().to_dict(),
        "parcels_with_energy": int(joint.certificate_count.gt(0).sum()),
        "overlap_unique_grants": len(cases),
        "overlap_unique_grants_cents": int(cases.importe_centimos.sum()),
        "normalization_including_read_seconds": normalization_seconds,
        "matching_seconds": matching_seconds,
        "omitted_products": {
            "energy_building_links": "No shared BU identity or reliable certificate geometry",
            "energy_temporal_pairs": "No verified persistent physical-unit identity and date semantics",
        },
        "public_exposure": False,
        "energy_license": {
            k: source_catalog.get(k) for k in ["license_id", "license_title", "license_url"]
        },
        "future_dates_after_capture": int(certificates.date_after_capture.sum()),
        "suspect_column_alignment": int(certificates.schema_suspect.sum()),
        "reference_format_valid_certificates": int(
            links.loc[links.reference_format_valid, "certificate_id"].nunique()
        ),
        "reference_invalid_or_missing_certificates": int(
            links.loc[~links.reference_format_valid, "certificate_id"].nunique()
        ),
        "prtr_license": "not_verified",
    }
    output.mkdir(parents=True)
    tables = {
        "energy_source_records": records,
        "energy_certificates": certificates,
        "energy_municipality_links": certificates[
            ["certificate_id", "edif_muni", "municipality_code", "municipality_status"]
        ],
        "energy_parcel_links": links,
        "energy_municipality_summary": summary,
        "energy_grants_summary": joint,
        "energy_grant_cases": cases,
        "energy_unresolved_municipalities": unknown,
        "energy_identity_conflicts": certificates[
            certificates.identity_status.ne("unique_registration_content")
        ],
        "energy_capture_overlap": records.groupby("certificate_id")
        .agg(
            occurrences=("source_id", "size"),
            captures=("source_id", lambda s: "|".join(sorted(set(s)))),
        )
        .reset_index(),
    }
    for name, frame in tables.items():
        frame.to_parquet(output / (name + ".parquet"), index=False)
    # Particiones sin geometrías para navegación por municipio/parcela.
    for code, f in certificates.dropna(subset=["municipality_code"]).groupby("municipality_code"):
        part = output / "municipalities" / code
        part.mkdir(parents=True)
        f.to_parquet(part / "certificates.parquet", index=False)
        links[links.municipality_code.eq(code)].to_parquet(part / "links.parquet", index=False)
    save_json(output / "source_inventory.json", inventory)
    quality["total_seconds"] = time.perf_counter() - started
    quality["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    save_json(output / "energy_quality.json", quality)
    # Verifica que ninguna entrada haya cambiado durante la ejecución.
    for path, sha in inputs.items():
        if digest(Path(path)) != sha:
            raise ValueError("Entrada cambiada: " + path)
    outputs = {
        str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    save_json(
        output / "manifest.json",
        {
            "policy": "regional-energy-conservative-v1",
            "inputs": inputs,
            "outputs": outputs,
            "scope_map": SCOPES,
            "municipality_aliases": ALIASES,
            "code_sha256": digest(Path(__file__)),
            "public_exposure": False,
        },
    )
    print(json.dumps(quality, ensure_ascii=False, indent=2))
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    run(args.output_dir, args.raw_dir)


if __name__ == "__main__":
    main()
