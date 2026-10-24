"""Agregación por parcela con identidades explícitas y contratos comprobables."""

import pandas as pd

from .territory import parcel_territories

REFERENCE_YEAR = 2026
SCOPES = ("dwelling", "building_part", "whole_building", "unknown")


def require_columns(frame, columns, label):
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label}: faltan columnas {missing}")


def unique_entities(frame, key, fields, label):
    """No elige una versión arbitraria si una identidad tiene atributos contradictorios."""
    require_columns(frame, [key, *fields], label)
    if frame[key].isna().any() or frame[key].astype(str).str.strip().eq("").any():
        raise ValueError(f"{label}: identidad vacía {key}")
    relevant = list(dict.fromkeys([key, *fields]))
    variants = frame[relevant].drop_duplicates()
    if variants[key].duplicated().any():
        raise ValueError(f"{label}: identidad contradictoria {key}")
    return frame.drop_duplicates(key).copy()


def construction_years(buildings):
    out = buildings.copy()
    for field, raw in [
        ("construction_oldest_year", "construction_begin"),
        ("construction_newest_year", "construction_end"),
    ]:
        if field in out:
            years = pd.to_numeric(out[field], errors="coerce")
        else:
            require_columns(out, [raw], "BU")
            # Solo comienzo de fecha ISO, nunca cuatro dígitos dentro de un texto libre.
            years = pd.to_numeric(
                out[raw]
                .astype("string")
                .str.extract(r"^(\d{4})(?:-\d{2}-\d{2}(?:T.*)?|)$", expand=False),
                errors="coerce",
            )
        out[field] = years.where(years.between(1000, REFERENCE_YEAR) & years.mod(1).eq(0))
    out["construction_interval_invalid"] = out.construction_oldest_year.gt(
        out.construction_newest_year
    )
    out.loc[
        out.construction_interval_invalid, ["construction_oldest_year", "construction_newest_year"]
    ] = float("nan")
    return out


def prepare_buildings(buildings):
    fields = ["parcel_ref14", "current_use"]
    fields += [
        c
        for c in [
            "construction_begin",
            "construction_end",
            "construction_oldest_year",
            "construction_newest_year",
        ]
        if c in buildings
    ]
    return construction_years(unique_entities(buildings, "building_id", fields, "BU"))


def confirmed_energy(parcels, certificates, links):
    """Un par registro/parcela, con confirmación doble y CP única en toda la captura."""
    fields = ["parcel_status", "cal_norenovglobal", "certificate_date", "certificate_scope"]
    fields += [c for c in ["edif_codreg", "edif_refcat"] if c in certificates]
    cert = unique_entities(certificates, "record_id", fields, "CEEE")
    require_columns(links, ["certificate_id", "parcel_ref14", "parcel_status"], "Enlaces")
    if not links.certificate_id.isin(cert.record_id).all():
        raise ValueError("Enlaces: certificado inexistente")
    states = links.groupby(["certificate_id", "parcel_ref14"], dropna=False).parcel_status.nunique()
    if states.gt(1).any():
        raise ValueError("Enlaces: estados contradictorios para el mismo registro/parcela")
    cp_counts = parcels.groupby("parcel_ref14").size()
    usable = links[
        links.parcel_status.eq("confirmed")
        & links.certificate_id.isin(cert.loc[cert.parcel_status.eq("confirmed"), "record_id"])
    ].copy()
    # Los códigos administrativos repetidos con RC distintas no confirman identidad.
    if {"edif_codreg", "edif_refcat"}.issubset(cert.columns):
        codes = cert[cert.edif_codreg.notna() & cert.edif_codreg.ne("")]
        conflicts = codes.groupby("edif_codreg").edif_refcat.nunique().gt(1)
        usable = usable[
            ~usable.certificate_id.isin(
                codes.loc[codes.edif_codreg.isin(conflicts[conflicts].index), "record_id"]
            )
        ]
    usable = usable[usable.parcel_ref14.map(cp_counts).eq(1)]
    pairs = usable[["certificate_id", "parcel_ref14"]].drop_duplicates()
    energy = pairs.merge(
        cert, left_on="certificate_id", right_on="record_id", validate="many_to_one"
    )
    energy["valid_grade"] = energy.cal_norenovglobal.isin(list("ABCDEFG"))
    energy["efg"] = energy.cal_norenovglobal.isin(list("EFG"))
    energy["date_parsed"] = pd.to_datetime(
        energy.certificate_date, errors="coerce", format="mixed", utc=True
    )
    energy["year"] = energy.date_parsed.dt.year
    energy["missing_date"] = energy.date_parsed.isna()
    return energy


def parcel_features(parcels, buildings, certificates, links, district="07"):
    require_columns(parcels, ["parcel_ref14", "district_code"], "CP")
    universe = (
        parcels.copy()
        if district == "all"
        else parcels.loc[parcels.district_code.eq(district)].copy()
    )
    if (
        universe.parcel_ref14.isna().any()
        or universe.parcel_ref14.astype(str).str.strip().eq("").any()
    ):
        raise ValueError("CP del piloto: referencia vacía")
    # Ambigüedad global: no se oculta una segunda CP situada fuera del piloto.
    counts = parcels.groupby("parcel_ref14").size().rename("cp_rows")
    out = counts.reindex(sorted(universe.parcel_ref14.unique())).to_frame()
    if district == "all":
        owners = parcel_territories(parcels).set_index("parcel_ref14")
        out["district_code"] = owners.district_code.reindex(out.index)
        out["district_assignment"] = owners.district_assignment.reindex(out.index)
    else:
        out["district_code"] = district
    bu = prepare_buildings(buildings)
    bu = bu[bu.parcel_ref14.isin(out.index)]
    out["bu_count"] = (
        bu.groupby("parcel_ref14").building_id.nunique().reindex(out.index, fill_value=0)
    )
    for field, operation in [
        ("construction_oldest_year", "min"),
        ("construction_newest_year", "max"),
    ]:
        out[field] = bu.groupby("parcel_ref14")[field].agg(operation)
    out["construction_invalid_bu_count"] = (
        bu.groupby("parcel_ref14")
        .construction_interval_invalid.sum()
        .reindex(out.index, fill_value=0)
    )
    out["residential_bu_count"] = (
        bu[bu.current_use.eq("1_residential")]
        .groupby("parcel_ref14")
        .building_id.nunique()
        .reindex(out.index, fill_value=0)
    )
    energy = confirmed_energy(parcels, certificates, links)
    energy = energy[energy.parcel_ref14.isin(out.index)]
    grouped = energy.groupby("parcel_ref14")
    out["ceee_records_observed"] = grouped.record_id.nunique().reindex(out.index, fill_value=0)
    out["ceee_valid_grade_count"] = grouped.valid_grade.sum().reindex(out.index, fill_value=0)
    out["ceee_efg_share_observed"] = grouped.efg.sum() / grouped.valid_grade.sum().replace(
        0, float("nan")
    )
    for grade in "ABCDEFG":
        out["ceee_grade_" + grade] = (
            energy[energy.cal_norenovglobal.eq(grade)]
            .groupby("parcel_ref14")
            .record_id.nunique()
            .reindex(out.index, fill_value=0)
        )
    for year in sorted(energy.year.dropna().unique()):
        out[f"ceee_records_{int(year)}"] = (
            energy[energy.year.eq(year)]
            .groupby("parcel_ref14")
            .record_id.nunique()
            .reindex(out.index, fill_value=0)
        )
    out["ceee_first_date"] = grouped.date_parsed.min().dt.tz_localize(None)
    out["ceee_last_date"] = grouped.date_parsed.max().dt.tz_localize(None)
    out["ceee_missing_date_count"] = grouped.missing_date.sum().reindex(out.index, fill_value=0)
    out["ceee_unknown_grade_count"] = out.ceee_records_observed - out.ceee_valid_grade_count
    out["ceee_scope_count"] = grouped.certificate_scope.nunique().reindex(out.index, fill_value=0)
    for scope in SCOPES:
        subset = (
            energy[energy.certificate_scope.eq(scope)]
            if scope != "unknown"
            else energy[~energy.certificate_scope.isin(SCOPES[:-1])]
        )
        out["ceee_scope_" + scope] = (
            subset.groupby("parcel_ref14").record_id.nunique().reindex(out.index, fill_value=0)
        )
    if "edif_codreg" in energy:
        known = energy[energy.edif_codreg.notna() & energy.edif_codreg.ne("")]
        out["ceee_administrative_codes_observed"] = (
            known.groupby("parcel_ref14").edif_codreg.nunique().reindex(out.index, fill_value=0)
        )
    out["construction_available"] = out.construction_oldest_year.notna()
    out["energy_available"] = out.ceee_records_observed.gt(0)
    out["inspection_source_status"] = "not_integrated"
    out["grant_source_status"] = "not_integrated"
    out["observed_dimensions"] = out.construction_available.astype(
        int
    ) + out.energy_available.astype(int)
    out["global_ipr_eligible"] = False
    out["global_ipr_exclusion"] = (
        "No conservation evidence; energy observations do not cover physical buildings"
    )
    return out.reset_index()
