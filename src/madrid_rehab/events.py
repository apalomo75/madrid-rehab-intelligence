"""Contratos de eventos públicos. Sin scraping ni inferencias de estado administrativo."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from urllib.parse import urlsplit

from .ingest import digest
from .normalize import address_key
from .session2 import normalize_reference
from .territory import event_territories

COMMON = [
    "municipality_code",
    "event_id",
    "authority",
    "source_url",
    "extracted_at",
    "reference_raw",
    "address_raw",
    "administrative_id",
    "administrative_status",
    "quality_notes",
]
INSPECTION = ["inspection_type", "inspection_date", "result_raw", "remediation_date"]
GRANT = [
    "case_id",
    "program",
    "phase",
    "resolution_date",
    "amount",
    "currency",
    "location_role",
    "district_code",
    "neighborhood",
    "execution_evidence_url",
]
PHASES = {"call", "application", "award", "payment", "justification", "executed", "unknown"}


def normalize_events(frame, kind):
    """Entrada canónica explícita; columnas personales ajenas al contrato se descartan."""
    if kind not in {"inspection", "grant"}:
        raise ValueError("Tipo de evento no soportado")
    columns = COMMON + (INSPECTION if kind == "inspection" else GRANT)
    out = frame.reindex(columns=columns).astype(object)
    out = out.where(out.notna(), None)
    for name in ["event_id", "authority", "source_url", "extracted_at"]:
        if out[name].isna().any() or out[name].astype(str).str.strip().eq("").any():
            raise ValueError(f"Procedencia obligatoria: {name}")
    for name in ["event_id", "authority"]:
        out[name + "_raw"] = out[name]
        out[name] = out[name].astype(str).str.strip()
    valid_urls = out.source_url.map(lambda value: urlsplit(str(value)))
    if any(url.scheme not in {"http", "https"} or not url.netloc for url in valid_urls):
        raise ValueError("source_url debe ser URL HTTP(S) de procedencia")
    if pd.to_datetime(out.extracted_at, errors="coerce", utc=True, format="mixed").isna().any():
        raise ValueError("Fecha de extracción inválida")
    out = out.drop_duplicates()
    if out.duplicated(["authority", "event_id"]).any():
        raise ValueError("Identidad de evento repetida con contenido contradictorio")
    out["address_normalized"] = out.address_raw.map(lambda x: address_key(x) if x else None)
    out["parcel_ref14"] = out.reference_raw.map(lambda x: normalize_reference(x)["parcel_ref14"])
    if kind == "inspection":
        out["result_normalized"] = out.result_raw.map(
            lambda x: {"FAVORABLE": "favorable", "DESFAVORABLE": "unfavorable"}.get(
                str(x).strip().upper(), "unknown"
            )
        )
        date_columns = ["inspection_date", "remediation_date"]
    else:
        out["phase"] = out.phase.fillna("unknown")
        if not out.phase.isin(PHASES).all():
            raise ValueError("Fase no soportada; conservar literal en administrative_status")
        numeric = pd.to_numeric(out.amount, errors="coerce")
        if (out.amount.notna() & numeric.isna()).any() or (numeric.dropna() < 0).any():
            raise ValueError("Importe inválido; usar número decimal sin separadores de miles")
        if not np.isfinite(numeric.dropna().to_numpy(dtype=float)).all():
            raise ValueError("Importe no finito")
        out["amount_raw"] = out.amount
        out["amount"] = numeric
        evidence = out.execution_evidence_url.fillna("").astype(str).str.strip()
        if (out.phase.eq("executed") & ~evidence.str.match(r"^https?://[^/\s]+")).any():
            raise ValueError("Ejecución requiere evidencia explícita")
        date_columns = ["resolution_date"]
    for name in date_columns:
        parsed = pd.to_datetime(out[name], errors="coerce", utc=True)
        out[name + "_parsed"] = parsed
        out[name + "_invalid"] = out[name].notna() & parsed.isna()
    return out.reset_index(drop=True)


def match_events(events, parcels, kind):
    """Solo confirma RC contra una fila CP única; dirección sin padrón validado no confirma."""
    if kind not in {"inspection", "grant"}:
        raise ValueError("Tipo de evento no soportado")
    out = events.copy()
    counts = parcels.groupby("parcel_ref14").size()
    out["match_status"] = "unmatched"
    out["match_reason"] = "no_reference_in_snapshot"
    out["match_level"] = "none"
    for i, row in out.iterrows():
        if kind == "grant" and row.location_role != "subsidized_property":
            out.loc[i, "match_reason"] = "property_location_not_verified"
            continue
        count = counts.get(row.parcel_ref14, 0)
        if count:
            out.loc[i, ["match_status", "match_reason", "match_level"]] = [
                "confirmed" if count == 1 else "ambiguous",
                "explicit_reference_unique_cp" if count == 1 else "multiple_cp_rows",
                "parcel",
            ]
        elif row.address_normalized:
            out.loc[i, ["match_status", "match_reason"]] = [
                "candidate",
                "address_requires_official_validation",
            ]
    if kind == "grant":
        if out.empty:
            out["location_level"] = pd.Series(dtype="string", index=out.index)
            return event_territories(out, parcels)
        out["location_level"] = out.apply(
            lambda r: "A"
            if r.match_status == "confirmed"
            else "B"
            if (pd.notna(r.district_code) and str(r.district_code).strip())
            or (pd.notna(r.neighborhood) and str(r.neighborhood).strip())
            else "C",
            axis=1,
        )
    return event_territories(out, parcels)


def grant_summary(events):
    """Concesiones únicas verificables. Conflictos entre publicaciones no se suman."""
    awards = events[events.phase.eq("award")].copy()
    keys = ["authority", "program", "case_id"]
    valid_identity = awards[keys].notna().all(axis=1)
    for key in keys:
        valid_identity &= awards[key].fillna("").astype(str).str.strip().ne("")
    identified = awards[valid_identity]
    clean = []
    conflicts = 0
    for _, group in identified.groupby(keys):
        identity_fields = ["amount", "currency", "parcel_ref14", "location_role"]
        if "resolution_date" in group:
            identity_fields.append("resolution_date")
        values = group[identity_fields].drop_duplicates()
        if len(values) != 1:
            conflicts += 1
        else:
            clean.append(group.iloc[0])
    unique = pd.DataFrame(clean, columns=awards.columns)
    euros = unique[unique.currency.eq("EUR")].amount
    return {
        "award_publications": len(awards),
        "unique_consistent_awards": len(unique),
        "conflicting_cases_excluded": conflicts,
        "publications_without_case_identity": len(awards) - len(identified),
        "known_eur_amount": None if euros.notna().sum() == 0 else float(euros.sum(min_count=1)),
        "known_eur_amount_count": int(euros.notna().sum()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["inspection", "grant"])
    parser.add_argument("--input", type=Path, required=True, help="CSV canónico, nunca fixtures")
    parser.add_argument(
        "--parcels", type=Path, default=Path("data/processed/session_2/parcels_audited.parquet")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("Usar una salida nueva")
    input_hash, cp_hash = digest(args.input), digest(args.parcels)
    data = pd.read_csv(args.input, dtype=str)
    result = match_events(
        normalize_events(data, args.kind), pd.read_parquet(args.parcels), args.kind
    )
    if digest(args.input) != input_hash or digest(args.parcels) != cp_hash:
        raise ValueError("Entradas modificadas durante la importación")
    args.output_dir.mkdir(parents=True)
    target = args.output_dir / "events.parquet"
    result.to_parquet(target, index=False)
    manifest = {
        "kind": args.kind,
        "rows": len(result),
        "input_sha256": input_hash,
        "parcels_sha256": cp_hash,
        "output_sha256": digest(target),
        "matching": result.match_status.value_counts().to_dict(),
    }
    if args.kind == "grant":
        manifest["award_summary"] = grant_summary(result)
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
