"""Auditoría reproducible del universo, enlaces, reconciliación y sesgos de cobertura."""

import pandas as pd

from .features import confirmed_energy, prepare_buildings
from .profiles import add_profiles, group_comparison


def audit_analysis(parcels, buildings, certificates, links, features, district="07"):
    cp = parcels[parcels.district_code.eq(district)]
    refs = set(cp.parcel_ref14.dropna())
    relevant_links = links[links.parcel_ref14.isin(refs)]
    cert = certificates[certificates.record_id.isin(relevant_links.certificate_id)]
    energy = confirmed_energy(parcels, certificates, links)
    energy = energy[energy.parcel_ref14.isin(refs)]
    bu = prepare_buildings(buildings)
    bu = bu[bu.parcel_ref14.isin(refs)]
    unique_energy = energy.drop_duplicates("record_id")
    grades = features[[f"ceee_grade_{g}" for g in "ABCDEFG"]].sum(axis=1)
    counts = (
        energy.groupby("parcel_ref14")
        .record_id.nunique()
        .reindex(features.parcel_ref14, fill_value=0)
    )
    expected_efg = features[[f"ceee_grade_{g}" for g in "EFG"]].sum(axis=1) / grades.replace(
        0, float("nan")
    )
    actual_share = features.ceee_efg_share_observed
    share_equal = (actual_share - expected_efg).abs().lt(1e-12) | (
        actual_share.isna() & expected_efg.isna()
    )
    checks = {
        "unique_parcel_rows": not features.parcel_ref14.duplicated().any(),
        "universe_preserved": set(features.parcel_ref14) == refs,
        "counts_reconciled_per_parcel": counts.tolist() == features.ceee_records_observed.tolist(),
        "grade_denominator_reconciled": grades.eq(features.ceee_valid_grade_count).all(),
        "efg_share_reconciled": share_equal.all(),
        "missing_energy_is_null_share": features.loc[
            features.ceee_valid_grade_count.eq(0), "ceee_efg_share_observed"
        ]
        .isna()
        .all(),
        "shares_in_range": features.ceee_efg_share_observed.dropna().between(0, 1).all(),
        "no_global_ipr": not features.global_ipr_eligible.any(),
    }
    code_counts = cert.edif_codreg.value_counts() if "edif_codreg" in cert else pd.Series(dtype=int)
    result = {
        "district_code": district,
        "checks": {k: bool(v) for k, v in checks.items()},
        "source_rows": {
            "cp_pilot": len(cp),
            "bu_by_parcel": len(bu),
            "ceee_linked_unique_records": cert.record_id.nunique(),
            "link_rows": len(relevant_links),
            "distinct_record_parcel_links": len(
                relevant_links[["certificate_id", "parcel_ref14"]].drop_duplicates()
            ),
            "repeated_administrative_codes": int(code_counts.gt(1).sum()),
            "ceee_confirmed_unique_records": energy.record_id.nunique(),
            "ceee_confirmed_record_parcel_pairs": len(energy),
            "excluded_linked_records": int((~cert.record_id.isin(energy.record_id)).sum()),
        },
        "link_states": relevant_links.parcel_status.value_counts().to_dict(),
        "certificate_scopes": unique_energy.certificate_scope.fillna("unknown")
        .value_counts()
        .to_dict(),
        "construction_invalid_intervals": int(bu.construction_interval_invalid.sum()),
        "cross_boundary_cp_rows": int(cp.crosses_district_boundary.sum())
        if "crosses_district_boundary" in cp
        else None,
        "unusable_cp_rows": int((~cp.usable_geometry).sum()) if "usable_geometry" in cp else None,
        "sparse_observation_parcels": int(features.ceee_valid_grade_count.between(1, 2).sum()),
        "multiple_scope_parcels": int(features.ceee_scope_count.gt(1).sum()),
        "year_counts": {
            str(int(k)): int(v)
            for k, v in unique_energy.year.dropna().value_counts().sort_index().items()
        },
        "invalid_or_missing_dates": int(unique_energy.date_parsed.isna().sum()),
        "certificate_dates_after_reference_year": int(unique_energy.year.gt(2026).sum()),
        "records_per_observed_parcel_quantiles": {
            str(k): float(v)
            for k, v in features.loc[features.energy_available, "ceee_records_observed"]
            .quantile([0.25, 0.5, 0.75, 0.95, 1])
            .dropna()
            .items()
        },
        "biases": [
            "Captura administrativa CEEE, no muestreo aleatorio ni censo completo",
            "Múltiples registros históricos pueden corresponder a un código administrativo",
            "Energía observada en vivienda/parte no describe edificio físico",
            "Fechas de certificado distintas del periodo de extracción",
            "Periodos y malla métrica no identifican efectos causales ni barrios oficiales",
        ],
    }
    if not all(checks.values()):
        raise ValueError(f"Auditoría analítica fallida: {checks}")
    comparisons = group_comparison(add_profiles(features), observations=energy)
    return result, comparisons
