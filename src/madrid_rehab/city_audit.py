"""Cobertura real, calidad por niveles y reconciliación municipal/distrital."""

import pandas as pd

from .features import confirmed_energy
from .territory import parcel_territories


def source_coverage(parcels, buildings, certificates, links, boundaries):
    owners = parcel_territories(parcels)
    result = {
        "rows": {
            "cp": len(parcels),
            "bu": len(buildings),
            "ceee": len(certificates),
            "links": len(links),
        },
        "unique_parcel_references": int(parcels.parcel_ref14.nunique()),
        "repeated_cp_references": int(owners.cp_rows.gt(1).sum()),
        "multi_district_references": int(
            owners.district_assignment.eq("ambiguous_reference_district").sum()
        ),
        "parcel_reference_unassigned": int(owners.district_code.isna().sum()),
        "districts_present_cp": int(parcels.district_code.nunique()),
        "districts_present_bu": int(buildings.district_code.nunique()),
        "certificate_states": certificates.parcel_status.value_counts().to_dict(),
        "capture_dates": {},
        "source_dates": {},
        "geometry": {},
        "scope": "Paquetes municipales; cobertura observada, no censo independiente de edificios o certificados",
        "boundaries": {
            "districts": len(boundaries),
            "source_url": boundaries.source_url.iloc[0],
            "captured_at": boundaries.captured_at.iloc[0],
        },
        "other_municipality_labels": {},
    }
    for name, frame in [("cp", parcels), ("bu", buildings), ("ceee", certificates)]:
        result["capture_dates"][name] = (
            sorted(frame.captured_at.dropna().unique().tolist()) if "captured_at" in frame else []
        )
        result["source_dates"][name] = (
            sorted(frame.source_date.dropna().unique().tolist()) if "source_date" in frame else []
        )
        if "municipality_code" in frame:
            other = frame[frame.municipality_code.ne("28079")]
            result["other_municipality_labels"][name] = len(other)
            if len(other):
                raise ValueError("Se encontraron etiquetas de otro municipio")
        if "geometry_crs" in frame:
            if not frame.geometry_crs.eq("EPSG:25830").all():
                raise ValueError("CRS heterogéneo/incompatible en Catastro")
            result["geometry"][name] = {
                "crs": "EPSG:25830",
                "usable": int(frame.usable_geometry.sum()),
                "unassigned_rows": int(frame.district_code.isna().sum()),
                "cross_boundary_rows": int(frame.crosses_district_boundary.sum()),
            }
    result["bu_without_cp_reference"] = int(
        (~buildings.parcel_ref14.isin(parcels.parcel_ref14)).sum()
    )
    return result


def quality_links(parcels, certificates, links):
    """Estados originales intactos y exclusión analítica explícita, sin promover candidatos."""
    energy = confirmed_energy(parcels, certificates, links)
    accepted = pd.MultiIndex.from_frame(energy[["certificate_id", "parcel_ref14"]])
    out = links.copy()
    if "district_code" in out:
        out = out.rename(columns={"district_code": "source_district_code"})
    owner = parcel_territories(parcels).set_index("parcel_ref14")
    out["district_code"] = out.parcel_ref14.map(owner.district_code)
    original = out.certificate_id.map(certificates.set_index("record_id").parcel_status)
    out["analytic_status"] = out.parcel_status
    out.loc[original.eq("candidate") & out.parcel_status.eq("confirmed"), "analytic_status"] = (
        "candidate"
    )
    out.loc[original.eq("ambiguous") & out.parcel_status.ne("unmatched"), "analytic_status"] = (
        "ambiguous"
    )
    pair = pd.MultiIndex.from_frame(out[["certificate_id", "parcel_ref14"]])
    eligible = pair.isin(accepted)
    inconsistent = out.analytic_status.eq("confirmed") & ~eligible
    out.loc[inconsistent, "analytic_status"] = "rejected"
    out["analytic_reason"] = out.get("parcel_reason", pd.Series("original_status", index=out.index))
    out.loc[inconsistent, "analytic_reason"] = "excluded_by_global_identity_or_cp_validation"
    return out, energy


def district_summary(features, buildings, parcels, energy, quality, boundaries):
    rows = []
    for district in boundaries.itertuples():
        code = district.district_code
        f = features[features.district_code.eq(code)]
        bu = buildings[buildings.district_code.eq(code)]
        cp = parcels[parcels.district_code.eq(code)]
        e = energy[energy.parcel_ref14.isin(f.parcel_ref14)]
        records = e.drop_duplicates("record_id")
        localized = quality[
            quality.district_code.eq(code) & quality.analytic_status.ne("unmatched")
        ]
        n = len(f)
        row = {
            "district_code": code,
            "district_name": district.district_name,
            "parcels": n,
            "cp_spatial_rows": len(cp),
            "bu_spatial": len(bu),
            "bu_by_parcel": int(f.bu_count.sum()),
            "ceee_localized_records": int(localized.certificate_id.nunique()),
            "ceee_confirmed_records": int(records.record_id.nunique()),
            "record_parcel_pairs": len(e),
            "parcels_with_energy": int(f.energy_available.sum()),
            "observed_energy_coverage": float(f.energy_available.mean()) if n else None,
            "construction_available": int(f.construction_available.sum()),
            "median_oldest_year": float(f.construction_oldest_year.median())
            if f.construction_available.any()
            else None,
            "ambiguous_cp_references": int(f.cp_rows.gt(1).sum()),
            "sparse_observation_parcels": int(f.ceee_valid_grade_count.between(1, 2).sum()),
            "mixed_scope_parcels": int(f.ceee_scope_count.gt(1).sum()),
            "cross_boundary_cp_rows": int(cp.crosses_district_boundary.sum()),
            "usable_bu": int(bu.usable_geometry.sum()),
        }
        for state in ["confirmed", "candidate", "ambiguous", "unmatched", "rejected"]:
            row["link_" + state] = int(
                quality[quality.district_code.eq(code)].analytic_status.eq(state).sum()
            )
        for grade in "ABCDEFG":
            row["ceee_grade_" + grade] = int(records.cal_norenovglobal.eq(grade).sum())
        row["valid_grade_records"] = int(records.cal_norenovglobal.isin(list("ABCDEFG")).sum())
        for scope in ["dwelling", "building_part", "whole_building", "unknown"]:
            mask = (
                records.certificate_scope.eq(scope)
                if scope != "unknown"
                else ~records.certificate_scope.isin(
                    ["dwelling", "building_part", "whole_building"]
                )
            )
            row["ceee_scope_" + scope] = int(mask.sum())
        rows.append(row)
    return pd.DataFrame(rows)


def reconcile(features, buildings, parcels, energy, summary):
    residual = features.district_code.isna()
    checks = {
        "one_row_per_rc": features.parcel_ref14.is_unique,
        "municipal_references_preserved": set(features.parcel_ref14) == set(parcels.parcel_ref14),
        "parcels_additive_with_residual": int(summary.parcels.sum()) + int(residual.sum())
        == len(features),
        "cp_rows_additive_with_residual": int(summary.cp_spatial_rows.sum())
        + int(parcels.district_code.isna().sum())
        == len(parcels),
        "bu_spatial_additive_with_residual": int(summary.bu_spatial.sum())
        + int(buildings.district_code.isna().sum())
        == len(buildings),
        "record_parcel_pairs_additive": int(summary.record_parcel_pairs.sum())
        + int(energy.parcel_ref14.isin(features.loc[residual, "parcel_ref14"]).sum())
        == len(energy),
        "grades_sum_to_valid_denominator": summary[[f"ceee_grade_{g}" for g in "ABCDEFG"]]
        .sum(axis=1)
        .eq(summary.valid_grade_records)
        .all(),
        "parcels_with_energy_additive": int(summary.parcels_with_energy.sum())
        + int(features.loc[residual, "energy_available"].sum())
        == int(features.energy_available.sum()),
        "no_global_ipr": not features.global_ipr_eligible.any(),
    }
    if not all(checks.values()):
        raise ValueError(f"Totales sin reconciliar: {checks}")
    owner = features.set_index("parcel_ref14").district_code
    membership = energy[["record_id", "parcel_ref14"]].copy()
    membership["district_code"] = membership.parcel_ref14.map(owner)
    assigned_records = membership.loc[membership.district_code.notna(), "record_id"].nunique()
    extra = membership.dropna(subset=["district_code"]).drop_duplicates(
        ["record_id", "district_code"]
    )
    residual_only = int(energy.record_id.nunique() - assigned_records)
    return {
        "checks": {k: bool(v) for k, v in checks.items()},
        "municipal_unique_certificates": int(energy.record_id.nunique()),
        "district_certificate_memberships": int(summary.ceee_confirmed_records.sum()),
        "municipal_record_parcel_pairs": len(energy),
        "confirmed_records_only_without_district": residual_only,
        "extra_cross_district_record_memberships": int(len(extra) - assigned_records),
        "residual_record_parcel_pairs": int(membership.district_code.isna().sum()),
        "district_parcels_with_energy": int(summary.parcels_with_energy.sum()),
        "residual_parcels_with_energy": int(features.loc[residual, "energy_available"].sum()),
        "residual_parcel_references": int(residual.sum()),
        "non_additive": [
            "Certificados únicos pueden pertenecer a varios distritos",
            "Porcentajes, medianas y perfiles no se suman ni promedian sin denominadores",
            "BU espaciales y BU por contexto de parcela tienen distinta asignación",
        ],
    }
