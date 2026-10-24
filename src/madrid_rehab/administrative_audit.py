"""Auditoría reproducible y perfiles descriptivos de la captura administrativa."""

import argparse
import json
from pathlib import Path

import pandas as pd

from .administrative import DEFAULT, VERSION, json_write
from .ingest import digest


def run(root, output, report):
    if output.exists() or report.exists():
        raise FileExistsError("Usar salidas nuevas para perfil y auditoría")
    metadata = json.loads((root / "manifest.json").read_text())
    if metadata["version"] != VERSION:
        raise ValueError("Versión no soportada")
    for name in ["events.parquet", "ndp_bridge.parquet", "parcel_profiles.parquet"]:
        if digest(root / name) != metadata["outputs"][name]:
            raise ValueError(f"Producto alterado: {name}")
    output.mkdir(parents=True)
    report.mkdir(parents=True)
    events = pd.read_parquet(root / "events.parquet")
    bridge = pd.read_parquet(root / "ndp_bridge.parquet")
    linked = events[events.match_status.eq("confirmed")]
    profiles = pd.read_parquet(root / "parcel_profiles.parquet")
    for typ in ["order", "license", "declaration", "ite_pending", "iee_pending"]:
        g = linked[linked.event_type.eq(typ)]
        count = g.groupby("parcel_ref14").event_id.nunique()
        dates = g.groupby("parcel_ref14").date.max()
        profiles[typ + "_events_observed"] = profiles.parcel_ref14.map(count).fillna(0).astype(int)
        profiles[typ + "_last_date_observed"] = profiles.parcel_ref14.map(dates).fillna("")
    profiles["residential_before_1980_with_registered_order"] = (
        profiles.residential_bu_count.gt(0)
        & profiles.construction_oldest_year.lt(1980)
        & profiles.order_events_observed.gt(0)
    )
    profiles["efg_certificates_observed"] = (
        profiles[["ceee_grade_E", "ceee_grade_F", "ceee_grade_G"]].sum(axis=1).gt(0)
    )
    profiles["urban_activity_since_2024_observed"] = profiles.license_last_date_observed.ge(
        "2024"
    ) | profiles.declaration_last_date_observed.ge("2024")
    profiles["multiple_administrative_events_observed"] = (
        profiles.administrative_events_observed.gt(1)
    )
    profiles["pending_obligation_observed"] = profiles.ite_pending_events_observed.gt(
        0
    ) | profiles.iee_pending_events_observed.gt(0)
    profiles["pending_query_date"] = "2026-10-24"
    profiles["evidence_note"] = (
        "Solo registros de esta captura; parcela CP; no ejecución, diagnóstico ni oportunidad comercial"
    )
    profiles.to_parquet(output / "descriptive_profiles.parquet", index=False)
    for district, g in profiles.groupby("district_code", dropna=False):
        p = output / "districts" / str(district or "unknown")
        p.mkdir(parents=True)
        g.to_parquet(p / "profiles.parquet", index=False)
    summary = (
        events.groupby(["district_code", "event_type", "match_status"])
        .agg(
            events=("event_id", "nunique"),
            versions=("event_version_id", "nunique"),
            parcel_candidates=("candidate_refs", lambda s: int(s.ne("").sum())),
        )
        .reset_index()
    )
    summary.to_csv(report / "district_source_matching.csv", index=False)
    parcel_count = linked.groupby("district_code").parcel_ref14.nunique()
    territorial = (
        events.groupby("district_code").event_id.nunique().rename("observed_events").to_frame()
    )
    territorial["confirmed_events"] = linked.groupby("district_code").event_id.nunique()
    territorial["confirmed_parcels"] = parcel_count
    territorial = territorial.fillna(0).astype(int)
    territorial["unconfirmed_events"] = territorial.observed_events - territorial.confirmed_events
    territorial.to_csv(report / "district_coverage.csv")
    measures = {
        "multi_portal_parcels": int(
            bridge[bridge.parcel_candidate.notna()]
            .groupby("parcel_candidate")
            .ndp.nunique()
            .gt(1)
            .sum()
        ),
        "multi_parcel_addresses": int(
            bridge[bridge.address_key.ne("")]
            .groupby("address_key")
            .parcel_candidate.nunique()
            .gt(1)
            .sum()
        ),
        "confirmed_parcels": int(linked.parcel_ref14.nunique()),
        "unconfirmed_with_district": int(
            (events.match_status.ne("confirmed") & events.district_code.ne("")).sum()
        ),
        "without_district": int(events.district_code.eq("").sum()),
        "ndp_address_disagreement": int(events.quality_flags.str.contains("ndp_address").sum()),
        "order_records_by_year": events[events.event_type.eq("order")]
        .year.value_counts()
        .sort_index()
        .to_dict(),
        "order_reasons": events[events.event_type.eq("order")].description.value_counts().to_dict(),
        "events_by_source": events.event_type.value_counts().to_dict(),
        "limits": "Distrito de un puente contradictorio es candidato territorial, no territorio confirmado; no identifica edificio físico.",
    }
    json_write(report / "supplementary_audit.json", measures)
    examples = events[events.quality_flags.str.contains("ndp_address")].head(100).copy()
    portal = bridge[
        ["ndp", "street", "number_raw", "qualifier_raw", "parcel_candidate", "distance_to_cp_m"]
    ].rename(
        columns={
            "street": "official_street",
            "number_raw": "official_number",
            "qualifier_raw": "official_qualifier",
        }
    )
    examples.merge(portal, on="ndp", how="left").to_parquet(
        report / "ndp_address_disagreements.parquet", index=False
    )
    json_write(
        output / "manifest.json",
        {
            "version": "administrative-profiles-v1",
            "input_manifest_sha256": digest(root / "manifest.json"),
            "cp_sha256": metadata["cp_sha256"],
            "events_sha256": digest(root / "events.parquet"),
            "rules": {
                "old_residential": "BU residencial declarado y año más antiguo <1980; no toda la parcela necesariamente anterior",
                "recent_urban": "Fecha observada desde 2024; no ejecución",
                "low_energy": "Al menos un CEEE E/F/G observado; no letra del edificio",
                "pending": "Pendiente según consulta 24/10/2026",
            },
            "outputs": {str(p.relative_to(output)): digest(p) for p in output.rglob("*.parquet")},
        },
    )
    return measures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, default=DEFAULT)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--report-dir", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(a.input_dir, a.output_dir, a.report_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
